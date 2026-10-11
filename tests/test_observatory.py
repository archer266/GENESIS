import csv
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest

from genesis.observatory import ExperimentSettings, History, distributions, statistics
from genesis.simulation import Config, SimulationClock, Traits, World


def state(world):
    return ([asdict(o) for o in world.organisms.values()], [asdict(f) for f in world.food.values()],
            world.rng.getstate(), world.ticks, world.births, world.deaths)


class ObservatoryTests(unittest.TestCase):
    def test_defaults_preserve_phase_one_configuration(self):
        self.assertEqual(ExperimentSettings().config(), Config())
        self.assertEqual(state(World(42)), state(World(42, ExperimentSettings().config())))

    def test_settings_parse_and_boundary_limits(self):
        for seed, population, food, mutation in ((0, 1, 0, 0), (4294967295, 300, 80, 20)):
            settings = ExperimentSettings.from_text({"seed": str(seed), "initial_population": str(population),
                                                     "food_per_second": str(food), "mutation_percent": str(mutation)})
            self.assertEqual(settings.seed, seed)
            self.assertEqual(settings.config().initial_population, population)
            self.assertEqual(settings.mutation_strength, mutation / 100)
            self.assertEqual(ExperimentSettings.from_text(settings.text_values()), settings)

    def test_invalid_settings_rejected(self):
        for key, values in {"seed": ("", "abc", "1.5", "-1", "4294967296"),
                            "initial_population": ("0", "301", "100.1"),
                            "food_per_second": ("nan", "inf", "-1", "80.1"),
                            "mutation_percent": ("nan", "-0.1", "20.1")}.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    fields = ExperimentSettings().text_values()
                    fields[key] = value
                    with self.assertRaises(ValueError):
                        ExperimentSettings.from_text(fields)
        for kwargs in ({"seed": True}, {"initial_population": 3.5}, {"mutation_strength": float("nan")}, {"food_per_second": True}):
            with self.assertRaises(ValueError):
                ExperimentSettings(**kwargs)

    def test_zero_mutation_and_configured_mutation_bounds(self):
        for strength in (0, 0.2):
            world = World(5, replace(Config(), initial_population=0, initial_food=0, mutation_strength=strength))
            parent = world.add_organism(100, 100, Traits(), energy=160, age=10)
            world.step()
            child = world.organisms[2]
            for name in Traits.BOUNDS:
                self.assertLessEqual(abs(getattr(child.traits, name) / getattr(parent.traits, name) - 1), strength + 1e-12)
            if strength == 0:
                self.assertEqual(parent.traits, child.traits)

    def test_statistics_and_histogram_endpoints(self):
        world = World(1, replace(Config(), initial_population=0, initial_food=0))
        world.add_organism(100, 100, Traits(18, 35, 3), generation=2)
        world.add_organism(200, 200, Traits(75, 160, 9), generation=8)
        stats = statistics(world)
        self.assertEqual((stats.population, stats.average_speed, stats.average_sense, stats.average_size, stats.highest_generation),
                         (2, 46.5, 97.5, 6, 8))
        for counts in distributions(world).values():
            self.assertEqual(sum(counts), 2)
            self.assertEqual(counts[0], 1)
            self.assertEqual(counts[-1], 1)
        world.organisms.clear()
        stats = statistics(world)
        self.assertEqual(stats.population, 0)
        self.assertIsNone(stats.average_speed)
        self.assertIsNone(stats.highest_generation)
        self.assertTrue(all(sum(counts) == 0 for counts in distributions(world).values()))

    def test_sampling_uses_ticks_not_frames_and_pause_adds_nothing(self):
        settings = ExperimentSettings()
        world = World(settings.seed, settings.config())
        history = History(world, settings)
        clock = SimulationClock(world, history.on_step)
        for _ in range(300):
            clock.advance(1 / 120)
        self.assertEqual([s.tick for s in history.samples], [0, 30, 60])
        self.assertEqual([s.simulation_seconds for s in history.samples], [0, 1, 2])
        clock.paused = True
        before = list(history.samples)
        clock.advance(20)
        history.on_step(world)
        self.assertEqual(list(history.samples), before)

    def test_history_is_bounded_and_keeps_founder_baseline(self):
        settings = ExperimentSettings()
        world = World(42)
        history = History(world, settings, capacity=3)
        baseline = history.baseline
        clock = SimulationClock(world, history.on_step)
        clock.advance(5)
        self.assertEqual([s.tick for s in history.samples], [90, 120, 150])
        self.assertEqual(history.dropped_samples, 3)
        self.assertEqual(history.baseline, baseline)
        with self.assertRaises(ValueError):
            History(world, settings, capacity=0)

    def test_extinction_adds_one_explicit_terminal_sample(self):
        settings = ExperimentSettings(initial_population=1, food_per_second=0)
        world = World(settings.seed, settings.config())
        next(iter(world.organisms.values())).energy = 0.001
        history = History(world, settings)
        clock = SimulationClock(world, history.on_step)
        clock.advance(1)
        self.assertEqual([s.tick for s in history.samples], [0, 1])
        self.assertEqual(history.samples[-1].sample_kind, "extinction")
        self.assertEqual(history.samples[-1].stats.population, 0)
        self.assertIsNone(history.samples[-1].stats.average_size)
        clock.advance(10)
        self.assertEqual(len(history.samples), 2)

    def test_identical_experiments_and_speeds_reproduce_states_and_samples(self):
        settings = ExperimentSettings(seed=831, initial_population=63, food_per_second=11.5, mutation_strength=0.12)
        results = []
        for speed in (1, 2, 4, 1):
            world = World(settings.seed, settings.config())
            history = History(world, settings)
            clock = SimulationClock(world, history.on_step)
            clock.speed = speed
            for _ in range(1200 // speed):
                clock.advance(1 / 60)
            self.assertEqual(world.ticks, 600)
            results.append((state(world), list(history.samples)))
        self.assertTrue(all(result == results[0] for result in results))

    def test_csv_round_trip_settings_metadata_and_no_overwrite(self):
        settings = ExperimentSettings(seed=67, initial_population=23, food_per_second=7.25, mutation_strength=0.15)
        world = World(settings.seed, settings.config())
        history = History(world, settings, capacity=3)
        SimulationClock(world, history.on_step).advance(5)
        with tempfile.TemporaryDirectory() as directory:
            path = history.export_csv(Path(directory) / "nested" / "experiment.csv")
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual([float(row["simulation_seconds"]) for row in rows], [3, 4, 5])
            self.assertEqual(rows[0]["seed"], "67")
            self.assertEqual(rows[0]["config_initial_population"], "23")
            self.assertEqual(rows[0]["config_food_per_second"], "7.25")
            self.assertEqual(rows[0]["config_mutation_strength"], "0.15")
            self.assertEqual(rows[0]["dropped_samples"], "3")
            self.assertEqual(float(rows[0]["starting_average_speed"]), history.baseline.average_speed)
            self.assertEqual(float(rows[-1]["average_speed"]), history.samples[-1].stats.average_speed)
            with self.assertRaises(FileExistsError):
                history.export_csv(path)
            with self.assertRaises(OSError):
                history.export_csv(directory)

    def test_extinct_csv_uses_blanks_for_undefined_traits(self):
        settings = ExperimentSettings(initial_population=1)
        world = World(42, settings.config())
        history = History(world, settings)
        next(iter(world.organisms.values())).energy = 0
        SimulationClock(world, history.on_step).advance(1)
        with tempfile.TemporaryDirectory() as directory:
            path = history.export_csv(Path(directory) / "extinct.csv")
            with path.open(newline="", encoding="utf-8") as handle:
                final = list(csv.DictReader(handle))[-1]
            self.assertEqual(final["population"], "0")
            self.assertEqual(final["average_speed"], "")
            self.assertEqual(final["highest_generation"], "")
