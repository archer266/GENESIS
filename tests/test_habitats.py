"""Spatial rules, immutable maps, legacy compatibility and checkpoint tests."""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, replace
import csv
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest

from genesis.habitats import HabitatMap, REGIONS, occupancy
from genesis.observatory import ExperimentSettings, History, statistics
from genesis.persistence import document, load_world, restore, save_world, SaveError
from genesis.simulation import Config, SimulationClock, Traits, World, energy_rate, habitat_energy_rate

spec = importlib.util.spec_from_file_location("phase4", Path(__file__).parent / "fixtures/phase4_simulation.py")
legacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = legacy
spec.loader.exec_module(legacy)


def state(world):
    return ([asdict(o) for o in world.organisms.values()], [asdict(f) for f in world.food.values()],
            world.rng.getstate(), world.ticks, world.births, world.deaths, world.catches,
            world._next_organism_id, world._next_food_id, world._food_credit)


def experiment(seed=42, map_seed=42):
    settings = ExperimentSettings(seed=seed, predator_enabled=True, initial_predators=8,
                                  habitat_enabled=True, map_seed=map_seed)
    world = World(seed, settings.config())
    history = History(world, settings)
    return settings, world, history, SimulationClock(world, history.on_step)


class HabitatTests(unittest.TestCase):
    def test_seeded_maps_are_broad_connected_and_do_not_consume_global_rng(self):
        before = random.getstate()
        unique = set()
        for seed in range(20):
            m = HabitatMap.generate(1100, 760, True, seed)
            self.assertEqual(m, HabitatMap.generate(1100, 760, True, seed))
            unique.add(m.cells)
            for region in range(3):
                indices = {i for i, value in enumerate(m.cells) if value == region}
                self.assertGreater(len(indices), len(m.cells) * .2)
                seen, todo = set(), [min(indices)]
                while todo:
                    i = todo.pop()
                    if i in seen:
                        continue
                    seen.add(i)
                    x, y = i % m.columns, i // m.columns
                    for nx, ny in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
                        neighbor = ny * m.columns + nx
                        if 0 <= nx < m.columns and 0 <= ny < m.rows and neighbor in indices and neighbor not in seen:
                            todo.append(neighbor)
                self.assertEqual(seen, indices)
        self.assertGreater(len(unique), 15)
        self.assertEqual(random.getstate(), before)

    def test_map_seed_is_independent_and_uniform_rng_matches_phase4(self):
        for predators in (False, True):
            c = Config(predator_enabled=predators, initial_predators=8 if predators else 0, map_seed=99)
            old_config = legacy.Config(**{k: v for k, v in asdict(c).items() if k in legacy.Config.__dataclass_fields__})
            current, previous = World(7, c), legacy.World(7, old_config)
            self.assertEqual(state(current), state(previous))
            for tick in range(1200):
                current.step()
                previous.step()
                if tick % 100 == 0:
                    self.assertEqual(state(current), state(previous))
            self.assertEqual(state(current), state(previous))
        a = World(1, Config(habitat_enabled=True, map_seed=16))
        b = World(2, Config(habitat_enabled=True, map_seed=16))
        self.assertEqual(a.habitats, b.habitats)

    def test_food_spawning_is_area_weighted_and_regeneration_rate_is_local(self):
        m = HabitatMap.generate(1100, 760, True, 42)
        areas = Counter(m.cells)
        counts = Counter()
        rng = random.Random(5)
        for _ in range(12000):
            x, y = m.food_position(rng)
            self.assertTrue(0 <= x < 1100 and 0 <= y < 760)
            counts[m.region_at(x, y)] += 1
        density = {r: counts[r] / areas[r] for r in areas}
        self.assertAlmostEqual(density[1] / density[0], 2, delta=.12)
        self.assertAlmostEqual(density[2] / density[0], 1, delta=.1)
        w = World(5, Config(initial_population=0, initial_food=0, food_cap=10000,
                            food_per_second=20, habitat_enabled=True))
        for _ in range(900):
            w.step()
        self.assertEqual(len(w.food), math.floor(20 * 30 * m.mean_food_multiplier + 1e-9))
        capped = World(5, Config(initial_population=0, initial_food=2, food_cap=2, habitat_enabled=True))
        for _ in range(60):
            capped.step()
        self.assertEqual(len(capped.food), 2)
        self.assertTrue(0 <= capped._food_credit < 1)

    def test_dense_movement_and_costs_for_both_species(self):
        for species in ("prey", "predator"):
            for region, expected in ((0, 1), (1, 1), (2, .6)):
                w = World(9, Config(initial_population=0, initial_food=0, food_per_second=0,
                                    predator_enabled=True, habitat_enabled=True))
                index = next(i for i, r in enumerate(w.habitats.cells) if r == region and i // 55 == 19)
                x, y = (index % 55 + .5) * 20, 390
                o = w.add_organism(x, y, Traits(40, 90, 5), energy=85, species=species)
                o.heading, o.wander_turn, o.wander_timer = 0, 0, 1
                w.step()
                self.assertAlmostEqual(o.x - x, 40 / 30 * expected)
                self.assertAlmostEqual(o.y, y)
                cost = energy_rate(o.traits) / 30 * (2.5 if species == "predator" else 1)
                self.assertAlmostEqual(85 - o.energy, cost)
                self.assertGreaterEqual(habitat_energy_rate(o.traits, expected), energy_rate(o.traits))

    def test_boundaries_are_traversable_and_world_edges_do_not_wrap(self):
        w = World(2, Config(initial_population=0, initial_food=0, food_per_second=0, habitat_enabled=True))
        m = w.habitats
        self.assertEqual(m.region_at(1100, 760), m.cells[-1])
        self.assertEqual(m.region_at(-1, -1), m.cells[0])
        self.assertEqual(m.region_at(1200, 800), m.cells[-1])
        row = 19
        boundary = next(col for col in range(1, 55) if m.cells[row*55+col] != m.cells[row*55+col-1]) * 20
        o = w.add_organism(boundary - .1, 390)
        o.heading, o.wander_timer = 0, 1
        w.step()
        self.assertGreater(o.x, boundary)
        o.x, o.heading = 1100 - o.traits.size - .1, 0
        w.step()
        self.assertEqual(o.x, 1100 - o.traits.size)
        self.assertTrue(-math.pi <= o.heading <= math.pi)

    def test_occupancy_and_csv_have_consistent_counts_and_settings(self):
        settings, w, h, clock = experiment()
        clock.advance(2)
        counts = occupancy(w)
        stats = statistics(w)
        for kind, total in (("prey", stats.prey_population), ("predator", stats.predator_population), ("food", len(w.food))):
            self.assertEqual(sum(counts[f"{r}_{kind}"] for r in REGIONS), total)
        with tempfile.TemporaryDirectory() as folder:
            path = h.export_csv(Path(folder) / "habitats.csv")
            with path.open(newline="", encoding="utf-8") as handle:
                row = list(csv.DictReader(handle))[-1]
            for name, value in counts.items():
                self.assertEqual(int(row[name]), value)
            self.assertEqual(row["config_habitat_enabled"], "True")
            self.assertEqual(row["config_map_seed"], "42")
            self.assertEqual(row["habitat_garden_food_multiplier"], "2.0")
        w.organisms.clear()
        w.food.clear()
        self.assertFalse(any(occupancy(w).values()))

    def test_settings_validation_and_text_roundtrip(self):
        s = ExperimentSettings(habitat_enabled=True, map_seed=4294967295)
        self.assertEqual(ExperimentSettings.from_text(s.text_values()), s)
        for kwargs in ({"habitat_enabled": 1}, {"map_seed": -1}, {"map_seed": 2**32}, {"map_seed": True}, {"map_seed": 1.5}):
            with self.assertRaises(ValueError):
                ExperimentSettings(**kwargs)
        values = s.text_values()
        values["habitat_enabled"] = "2"
        with self.assertRaises(ValueError):
            ExperimentSettings.from_text(values)

    def test_all_speeds_produce_identical_habitat_worlds_and_history(self):
        results = []
        for speed in (1, 2, 4):
            _, w, h, clock = experiment(seed=7, map_seed=2026)
            clock.speed = speed
            for _ in range(600 // speed):
                clock.advance(1 / 30)
            results.append((state(w), w.habitats, list(h.samples)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])

    def test_authoritative_map_and_exact_save_continuation(self):
        settings, w, h, clock = experiment()
        # A valid stored map is authoritative even if generation changes later.
        different_map = HabitatMap.generate(1100, 760, True, 17)
        w = World(42, settings.config(), habitats=different_map)
        h = History(w, settings)
        clock = SimulationClock(w, h.on_step)
        clock.advance(5.013)
        before = document(w, clock, h)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "world.json"
            save_world(path, w, clock, h)
            loaded = load_world(path)
        self.assertEqual(before, document(w, clock, h))
        self.assertEqual(loaded.world.habitats, different_map)
        self.assertTrue(loaded.clock.paused)
        loaded.clock.paused = False
        for _ in range(600):
            clock.advance(1 / 30)
            loaded.clock.advance(1 / 30)
        self.assertEqual(document(w, clock, h), document(loaded.world, loaded.clock, loaded.history))
        self.assertGreater(w.births, before["world"]["births"])
        self.assertGreater(w.catches, before["world"]["catches"])

    def test_real_v2_migration_continues_phase4_trajectory(self):
        loaded = load_world(Path(__file__).parent / "fixtures/phase4_world_v2.json")
        self.assertFalse(loaded.settings.habitat_enabled)
        self.assertEqual(loaded.world.habitats.cells, (0,))
        old_settings = {k: v for k, v in asdict(loaded.world.config).items() if k in legacy.Config.__dataclass_fields__}
        previous = legacy.World(loaded.settings.seed, legacy.Config(**old_settings))
        for _ in range(loaded.world.ticks):
            previous.step()
        self.assertEqual(state(loaded.world), state(previous))
        for _ in range(300):
            previous.step()
            loaded.world.step()
        self.assertEqual(state(loaded.world), state(previous))

    def test_invalid_dimensions_region_values_multipliers_and_occupancy_rejected(self):
        _, w, h, clock = experiment()
        data = document(w, clock, h)
        for field, value in (("width", 999), ("width", float("nan")), ("columns", 56),
                             ("rows", True), ("cells", [0]), ("cells", [True] * 2090),
                             ("cells", [3] * 2090), ("food_multipliers", [1, float("inf"), 1]),
                             ("food_multipliers", [1, 3, 1]), ("movement_multipliers", [1, 1, 0]),
                             ("movement_multipliers", [1, 1, 1.5])):
            bad = deepcopy(data)
            bad["habitats"][field] = value
            with self.subTest(field=field), self.assertRaises(SaveError):
                restore(bad)
        bad = deepcopy(data)
        bad["history"]["baseline"]["garden_prey"] += 1
        with self.assertRaises(SaveError):
            restore(bad)
        old = json.loads((Path(__file__).parent / "fixtures/phase4_world_v2.json").read_text())
        old["settings"]["habitat_enabled"] = True
        with self.assertRaises(SaveError):
            restore(old)


if __name__ == "__main__":
    unittest.main()
