"""Phase 4 mechanics and compatibility against the frozen Phase 3 model."""
import csv
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest

from genesis.observatory import ExperimentSettings, History, distributions, statistics
from genesis.persistence import document, load_world, restore, SaveError, save_world
from genesis.simulation import Config, SimulationClock, Traits, World, energy_rate

spec = importlib.util.spec_from_file_location("phase3", Path(__file__).parent / "fixtures/phase3_simulation.py")
legacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = legacy
spec.loader.exec_module(legacy)


def snapshot(world):
    organisms = [asdict(o) for o in world.organisms.values()]
    for o in organisms:
        o.pop("species", None)
    return (organisms, [asdict(f) for f in world.food.values()], world.rng.getstate(),
            world.ticks, world.births, world.deaths, world._food_credit,
            world._next_organism_id, world._next_food_id)


class PredatorTests(unittest.TestCase):
    def empty(self, **kwargs):
        return World(42, Config(initial_population=0, initial_food=0, food_per_second=0,
                                predator_enabled=True, **kwargs))

    def test_disabled_matches_frozen_phase3_through_births_mutations_and_deaths(self):
        for seed in (42, 7):
            a, b = World(seed), legacy.World(seed)
            for tick in range(3000):
                a.step()
                b.step()
                if tick % 100 == 0:
                    self.assertEqual(snapshot(a), snapshot(b))
            self.assertGreater(a.births, 0)
            self.assertGreater(a.deaths, 0)
            self.assertEqual(snapshot(a), snapshot(b))

    def test_hunting_fleeing_and_food_seeking(self):
        w = self.empty()
        hunter = w.add_organism(100, 100, Traits(60, 120, 6), species="predator")
        prey = w.add_organism(160, 100)
        hunter.heading = math.pi / 2
        prey.heading = math.pi / 2
        w.add_food(160, 130)
        w.step()
        self.assertLess(hunter.heading, math.pi / 2)  # Pursue to the right.
        self.assertLess(prey.heading, math.pi / 2)  # Flee to the right, even with food below.
        del w.organisms[hunter.id]
        prey.heading = 0
        w.step()
        self.assertGreater(prey.heading, 0)  # Resume steering toward food.

    def test_out_of_range_wandering_is_seeded(self):
        a, b = self.empty(), self.empty()
        for world in (a, b):
            world.add_organism(100, 100, species="predator")
            world.add_organism(900, 600)
            world.step()
        self.assertEqual(snapshot(a), snapshot(b))
        self.assertGreater(a.organisms[1].wander_timer, 0)

    def test_contact_caught_once_deterministic_ties_and_energy_transfer(self):
        w = self.empty()
        p1 = w.add_organism(100, 100, energy=50, species="predator")
        p2 = w.add_organism(100, 100, energy=50, species="predator")
        victim = w.add_organism(100, 100, energy=40)
        w.resolve_catches()
        self.assertNotIn(victim.id, w.organisms)
        self.assertEqual((p1.energy, p2.energy), (76, 50))
        self.assertEqual((w.catches, w.deaths), (1, 1))
        self.assertEqual([e.kind for e in w.events], ["catch"])
        w.resolve_catches()
        self.assertEqual(w.catches, 1)
        # Two equidistant prey: lower prey ID wins; each hunter catches at most one.
        del w.organisms[p2.id]
        a = w.add_organism(101, 100)
        b = w.add_organism(99, 100)
        w.resolve_catches()
        self.assertNotIn(a.id, w.organisms)
        self.assertIn(b.id, w.organisms)

    def test_contact_required_energy_capped_predators_do_not_eat_food(self):
        w = self.empty()
        p = w.add_organism(100, 100, energy=179, species="predator")
        prey = w.add_organism(112, 100, energy=100)
        w.resolve_catches()
        self.assertEqual(w.catches, 0)
        prey.x = 109
        w.resolve_catches()
        self.assertEqual(p.energy, 180)
        w.add_food(p.x, p.y)
        w.step()
        self.assertEqual(len(w.food), 1)
        self.assertAlmostEqual(p.energy, 180 - energy_rate(p.traits) * w.config.predator_energy_multiplier / 30)

    def test_reproduction_inherits_species_bounded_traits_and_spends_energy(self):
        w = self.empty(mutation_strength=.2)
        p = w.add_organism(200, 200, Traits(75, 160, 9), energy=145, age=9, species="predator")
        total = p.energy
        child = w._reproduce(p)
        self.assertEqual(child.species, "predator")
        self.assertEqual((child.parent_id, child.generation), (p.id, 1))
        self.assertAlmostEqual(p.energy + child.energy, total - 6)
        self.assertIsNone(w._reproduce(p))
        for name, (low, high) in Traits.BOUNDS.items():
            self.assertTrue(low <= getattr(child.traits, name) <= high)
        for _ in range(6000):
            w.step()
            if not w.organisms:
                break
        self.assertFalse(w.organisms)  # Without prey, there is no free energy supply.
        self.assertEqual(w.births, 1)

    def test_species_and_combined_caps_defer_reproduction_without_cost(self):
        for kwargs in ({"population_cap": 1}, {"predator_cap": 1}):
            w = self.empty(**kwargs)
            p = w.add_organism(100, 100, energy=180, age=9, species="predator")
            rng = w.rng.getstate()
            self.assertIsNone(w._reproduce(p))
            self.assertEqual(p.energy, 180)
            self.assertEqual(w.rng.getstate(), rng)

    def test_species_extinction_does_not_respawn_or_stop_survivors(self):
        w = self.empty()
        w.add_organism(100, 100, energy=.001, species="predator")
        prey = w.add_organism(900, 600)
        clock = SimulationClock(w)
        clock.advance(1)
        self.assertEqual(w.ticks, 30)
        self.assertEqual(set(w.organisms), {prey.id})
        stats = statistics(w)
        self.assertEqual(stats.predator_population, 0)
        self.assertIsNone(stats.predator_average_speed)
        self.assertEqual(sum(distributions(w, species="predator")["speed"]), 0)

    def test_predator_age_death_and_prey_extinction_leave_no_automatic_respawn(self):
        w = self.empty()
        hunter = w.add_organism(100, 100, age=180 - 1 / 60, species="predator")
        w.step()
        self.assertNotIn(hunter.id, w.organisms)
        self.assertEqual((w.deaths, w.catches), (1, 0))
        hunter = w.add_organism(200, 200, energy=50, species="predator")
        w.add_organism(200, 200, energy=40)
        w.step()
        self.assertEqual(statistics(w).prey_population, 0)
        self.assertEqual(statistics(w).predator_population, 1)
        for _ in range(600):
            w.step()
        self.assertFalse(w.organisms)
        self.assertEqual(w.births, 0)

    def test_predator_effects_and_sprite_cache_do_not_touch_model_or_rng(self):
        import pygame
        from genesis.visuals import VisualState, predator_sprite
        w = self.empty()
        w.add_organism(100, 100, species="predator")
        w.add_organism(100, 100)
        visuals = VisualState(w)
        w.step()
        before = snapshot(w)
        visuals.on_step(w)
        self.assertEqual([e.kind for e in visuals.effects], ["catch"])
        self.assertNotIn(2, visuals.current)
        visuals.advance(.1)
        visuals.toggle()
        for index in range(5):
            for radius in range(4, 21):
                for pulse in range(-2, 3):
                    predator_sprite(index, radius, pulse, True)
        self.assertLessEqual(predator_sprite.cache_info().currsize, 384)
        self.assertEqual(snapshot(w), before)

    def test_predator_settings_validation(self):
        for kwargs in ({"predator_enabled": 1}, {"initial_predators": 1},
                       {"predator_enabled": True, "initial_predators": 41},
                       {"predator_enabled": True, "initial_predators": 1.5},
                       {"predator_enabled": True, "initial_predators": 10, "initial_population": 300}):
            with self.assertRaises(ValueError):
                ExperimentSettings(**kwargs)
        settings = ExperimentSettings(predator_enabled=True, initial_predators=8)
        self.assertEqual(ExperimentSettings.from_text(settings.text_values()), settings)

    def test_same_seed_and_all_speeds_have_identical_model_and_history(self):
        settings = ExperimentSettings(seed=7, predator_enabled=True, initial_predators=8)
        results = []
        for speed in (1, 2, 4):
            w = World(settings.seed, settings.config())
            history = History(w, settings)
            clock = SimulationClock(w, history.on_step)
            clock.speed = speed
            for _ in range(600 // speed):
                clock.advance(1 / 30)
            results.append((snapshot(w), w.catches, list(history.samples)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertGreater(results[0][1], 0)

    def test_new_save_exact_continuation_saving_is_observational_and_csv(self):
        settings = ExperimentSettings(predator_enabled=True, initial_predators=8)
        w = World(settings.seed, settings.config())
        h = History(w, settings)
        clock = SimulationClock(w, h.on_step)
        clock.advance(5.013)
        before = document(w, clock, h)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "world.json"
            save_world(path, w, clock, h)
            self.assertEqual(document(w, clock, h), before)
            loaded = load_world(path)
            self.assertTrue(loaded.clock.paused)
            loaded.clock.paused = False
            for _ in range(600):
                clock.advance(1 / 30)
                loaded.clock.advance(1 / 30)
            self.assertEqual(document(w, clock, h), document(loaded.world, loaded.clock, loaded.history))
            self.assertGreater(w.births, before["world"]["births"])
            self.assertGreater(w.catches, before["world"]["catches"])
            self.assertTrue(any(o.species == "predator" and o.generation > 0 for o in w.organisms.values()))
            self.assertTrue(any(o.species == "predator" and o.parent_id in w.organisms
                                and o.traits != w.organisms[o.parent_id].traits for o in w.organisms.values()))
            with h.export_csv(Path(folder) / "stats.csv").open(newline="", encoding="utf-8") as handle:
                row = list(csv.DictReader(handle))[-1]
            self.assertEqual(row["config_predator_enabled"], "True")
            self.assertEqual(row["config_initial_predators"], "8")
            self.assertEqual(int(row["catches"]), h.samples[-1].stats.catches)

    def test_real_v1_save_migrates_and_continues_on_original_trajectory(self):
        loaded = load_world(Path(__file__).parent / "fixtures/phase3_world_v1.json")
        self.assertFalse(loaded.settings.predator_enabled)
        self.assertEqual(loaded.world.catches, 0)
        old = legacy.World(loaded.settings.seed)
        for _ in range(loaded.world.ticks):
            old.step()
        self.assertEqual(snapshot(old), snapshot(loaded.world))
        for _ in range(600):
            loaded.world.step()
            old.step()
        self.assertEqual(snapshot(old), snapshot(loaded.world))

    def test_new_and_legacy_invalid_species_settings_and_counts_rejected(self):
        s = ExperimentSettings(predator_enabled=True, initial_predators=8)
        w = World(s.seed, s.config())
        data = document(w, SimulationClock(w), History(w, s))
        for mutate in (lambda d: d["world"]["organisms"][0].update(species="dragon"),
                       lambda d: d["world"].update(catches=1),
                       lambda d: d["history"]["baseline"].update(predator_population=9),
                       lambda d: d["settings"].update(predator_enabled=False)):
            bad = deepcopy(data)
            mutate(bad)
            with self.assertRaises(SaveError):
                restore(bad)
        import json
        old = json.loads((Path(__file__).parent / "fixtures/phase3_world_v1.json").read_text())
        old["world"]["organisms"][0]["species"] = "predator"
        with self.assertRaises(SaveError):
            restore(old)


if __name__ == "__main__":
    unittest.main()
