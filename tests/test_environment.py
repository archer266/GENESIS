from copy import deepcopy
from dataclasses import asdict, replace
import csv
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

from genesis.environment import Environment, DEFAULTS, HISTORY_LIMIT
from genesis.observatory import ExperimentSettings, History
from genesis.persistence import document, restore, load_world, read_environment, SaveError
from genesis.simulation import World, Config, SimulationClock

spec = importlib.util.spec_from_file_location("phase7_frozen", Path(__file__).parent/"fixtures/phase7_simulation.py")
legacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = legacy
spec.loader.exec_module(legacy)


def settings(**kwargs):
    return ExperimentSettings(**dict(dict(seasons_enabled=True, droughts_enabled=True,
        season_length=40, drought_duration=5, drought_interval=30), **kwargs))


def experiment(s=None):
    s = s or settings()
    w = World(s.seed, s.config())
    h = History(w, s)
    return w, SimulationClock(w, h.on_step), h


class EnvironmentTests(unittest.TestCase):
    def test_settings_defaults_bounds_roundtrip_and_presets(self):
        from genesis.presets import PRESETS, preset_name
        self.assertFalse(ExperimentSettings().seasons_enabled)
        self.assertFalse(ExperimentSettings().droughts_enabled)
        for key, value in (("season_length", 39), ("season_length", 601), ("season_length", 40.5),
                           ("drought_duration", 4), ("drought_duration", 61), ("drought_interval", 29),
                           ("drought_interval", 301), ("seasons_enabled", 1), ("droughts_enabled", "yes")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                settings(**{key: value})
        s = settings(season_length=41)
        self.assertEqual(ExperimentSettings.from_text(s.text_values()), s)
        self.assertEqual(preset_name(next(p.settings for p in PRESETS if p.name == 'Changing Seasons')), "Changing Seasons")
        self.assertTrue(next(p.settings for p in PRESETS if p.name == 'Changing Seasons').habitat_enabled and next(p.settings for p in PRESETS if p.name == 'Changing Seasons').predator_enabled)

    def test_cycle_boundaries_smoothness_and_bounded_multipliers(self):
        env = Environment(42, settings(droughts_enabled=False).config())
        self.assertEqual((env.season, env.multiplier, env.next_transition), ("Spring", 1, 300))
        previous = env.multiplier
        for tick in range(1, 2401):
            env.advance()
            self.assertLess(abs(env.multiplier-previous), .003)
            self.assertTrue(.5 <= env.multiplier <= 1.5)
            previous = env.multiplier
            if tick % 300 == 0:
                self.assertAlmostEqual(env.multiplier, (1, 1.5, 1, .5)[(tick//300)%4])
                self.assertEqual(env.next_transition, tick+300)
        self.assertEqual(env.cycle_position, 0)
        self.assertEqual([e.tick for e in env.history], list(range(0, 2401, 300)))

    def test_drought_duration_gap_and_reproducible_environment_rng(self):
        a = Environment(9, settings(seasons_enabled=False).config())
        b = Environment(9, settings(seasons_enabled=False).config())
        initial = a.next_drought
        self.assertTrue(900 <= initial <= 1800)
        for _ in range(initial-1):
            a.advance(); b.advance()
        self.assertEqual(a.multiplier, 1)
        a.advance(); b.advance()
        self.assertEqual((a.multiplier, a.drought_start, a.drought_end), (.25, initial, initial+150))
        for _ in range(149):
            a.advance(); b.advance()
        self.assertEqual(a.multiplier, .25)
        a.advance(); b.advance()
        self.assertEqual(a.multiplier, 1)
        self.assertTrue(900 <= a.next_drought-a.ticks <= 1800)
        self.assertEqual(a.document(), b.document())

    def test_combined_regeneration_with_habitats_and_food_credit(self):
        c = replace(settings().config(), initial_population=0, initial_food=0, food_cap=10000, habitat_enabled=True)
        w = World(7, c)
        expected = 0
        for _ in range(2000):
            w.step()
            factor = w.environment.multiplier
            self.assertTrue(.125 <= factor <= 1.5)
            expected += c.food_per_second*w.habitats.mean_food_multiplier*factor*c.timestep
        self.assertEqual(len(w.food), math.floor(expected+1e-9))
        self.assertAlmostEqual(w._food_credit, expected-len(w.food), places=8)

    def test_no_direct_organism_effects_and_separate_rng(self):
        a = World(7, settings(food_per_second=0).config())
        b = World(7, ExperimentSettings(food_per_second=0).config())
        a.environment.next_drought = 1  # Isolated transition, no food input.
        for _ in range(180):
            a.step(); b.step()
        self.assertEqual([asdict(o) for o in a.organisms.values()], [asdict(o) for o in b.organisms.values()])
        self.assertEqual(a.rng.getstate(), b.rng.getstate())
        self.assertNotEqual(a.environment.rng.getstate(), b.environment.rng.getstate())

    def test_disabled_matches_frozen_phase7_through_births_and_catches(self):
        for habitats, predators in ((False, False), (True, True)):
            c = Config(habitat_enabled=habitats, predator_enabled=predators, initial_predators=8 if predators else 0)
            a = World(7, c)
            b = legacy.World(7, legacy.Config(**{k: v for k, v in asdict(c).items() if k in legacy.Config.__dataclass_fields__}))
            for _ in range(900):
                a.step(); b.step()
            for name in ("organisms", "food"):
                self.assertEqual([asdict(o) for o in getattr(a, name).values()], [asdict(o) for o in getattr(b, name).values()])
            self.assertEqual(a.rng.getstate(), b.rng.getstate())
            self.assertEqual((a.births, a.deaths, a.catches, a._food_credit), (b.births, b.deaths, b.catches, b._food_credit))

    def test_bounded_history_validates_and_continues_after_pruning(self):
        c = settings().config()
        env = Environment(42, c)
        for _ in range(90000):
            env.advance()
        self.assertEqual(len(env.history), HISTORY_LIMIT)
        self.assertGreater(env.total_events, HISTORY_LIMIT)
        w = SimpleNamespace(seed=42, config=c, ticks=env.ticks)
        loaded = read_environment(env.document(), w)
        for _ in range(3000):
            env.advance(); loaded.advance()
        self.assertEqual(env.document(), loaded.document())

    def test_saving_and_exact_continuation_through_future_transitions(self):
        w, c, h = experiment(settings(habitat_enabled=True, predator_enabled=True, initial_predators=8))
        for _ in range(w.environment.next_drought-1):
            c.advance(1/30)
        before = document(w, c, h)
        loaded = restore(deepcopy(before))
        self.assertEqual(document(w, c, h), before)
        self.assertTrue(loaded.clock.paused)
        loaded.clock.paused = False
        for _ in range(2100):
            c.advance(1/30); loaded.clock.advance(1/30)
        self.assertEqual(document(w, c, h), document(loaded.world, loaded.clock, loaded.history))
        self.assertGreater(w.environment.drought_count, 1)

    def test_speed_equivalence_and_extinction_stops_events_without_respawn(self):
        results = []
        for speed in (1, 2, 4):
            w, c, h = experiment()
            c.speed = speed
            for _ in range(2400//speed):
                c.advance(1/30)
            c.speed = 1
            self.assertAlmostEqual(c.accumulator, 0, places=15)
            data = document(w, c, h)
            data["clock"]["accumulator"] = 0  # Wall-time adapter rounding, not simulation state.
            results.append(data)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])
        w, c, h = experiment(settings(initial_population=1))
        w.organisms[1].energy = .001
        c.advance(1)
        before = w.environment.document()
        c.advance(1000)
        self.assertFalse(w.organisms)
        self.assertEqual(w.environment.document(), before)

    def test_all_old_save_versions_migrate_to_disabled_environment(self):
        for filename in ("phase3_world_v1.json", "phase4_world_v2.json", "phase6_world_v3.json", "phase7_world_v4.json"):
            loaded = load_world(Path(__file__).parent/"fixtures"/filename)
            self.assertFalse(loaded.world.environment.enabled)
            self.assertEqual(loaded.world.environment.ticks, loaded.world.ticks)
            self.assertEqual(loaded.world.environment.multiplier, 1)
            self.assertEqual(len(loaded.world.environment.history), 0)
            again = restore(document(loaded.world, loaded.clock, loaded.history))
            self.assertEqual(again.world.environment.document(), loaded.world.environment.document())

    def test_invalid_environment_state_rejected(self):
        w, c, h = experiment()
        c.advance(70)
        data = document(w, c, h)
        bad_values = dict(seed=0, ticks=w.ticks+1, cycle_position=-1, next_season=0,
                          drought_end=-1, next_drought=w.ticks, history_limit=999999,
                          total_events=0, drought_count=99999, rng_state=[3, [0], None])
        for key, value in bad_values.items():
            bad = deepcopy(data)
            bad["environment"][key] = value
            with self.subTest(key=key), self.assertRaises(SaveError):
                restore(bad)
        for key, value in (("tick", -1), ("multiplier", float("nan")), ("kind", "kill"), ("season", "Summer"), ("drought", "yes")):
            bad = deepcopy(data)
            bad["environment"]["history"][0][key] = value
            with self.subTest(key=key), self.assertRaises(SaveError):
                restore(bad)

    def test_csv_exports_sampled_environment_and_settings(self):
        w, c, h = experiment()
        c.advance(70)
        with tempfile.TemporaryDirectory() as root:
            path = h.export_csv(Path(root)/"stats.csv")
            with path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["config_seasons_enabled"], "True")
        self.assertEqual(rows[0]["config_drought_interval"], "30")
        self.assertTrue(any(float(r["drought_multiplier"]) == .25 for r in rows))
        for row in rows:
            self.assertEqual(float(row["environment_multiplier"]), float(row["season_multiplier"])*float(row["drought_multiplier"]))
