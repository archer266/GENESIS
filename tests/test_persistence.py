from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.observatory import ExperimentSettings, History
from genesis.persistence import MAX_BYTES, SaveError, document, load_world, restore, save_world
from genesis.presets import PRESETS, preset_name
from genesis.simulation import SimulationClock, World


def experiment(settings=None, capacity=3601):
    settings = settings or ExperimentSettings()
    world = World(settings.seed, settings.config())
    history = History(world, settings, capacity=capacity)
    return world, SimulationClock(world, history.on_step), history


def comparable(world, clock, history, selected=None):
    data = document(world, clock, history, selected)
    data["clock"]["paused"] = True  # The one intentional load-time difference.
    return data


class PersistenceTests(unittest.TestCase):
    def test_round_trip_preserves_every_model_field_and_loads_paused(self):
        world, clock, history = experiment(ExperimentSettings(seed=28, food_per_second=11.25, mutation_strength=0.12))
        clock.speed = 4
        clock.advance(3.083)
        self.assertGreater(clock.accumulator, 0)
        selection = next(iter(world.organisms))
        before = document(world, clock, history, selection)
        with tempfile.TemporaryDirectory() as directory:
            path = save_world(Path(directory) / "world.json", world, clock, history, selection)
            loaded = load_world(path)
            raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(raw["version"], 7)
        self.assertNotIn("effects", raw)
        self.assertEqual(document(world, clock, history, selection), before)
        self.assertTrue(loaded.clock.paused)
        self.assertEqual(loaded.selected_id, selection)
        self.assertEqual(comparable(world, clock, history, selection),
                         comparable(loaded.world, loaded.clock, loaded.history, selection))
        self.assertEqual(loaded.clock.advance(10), 0)

    def test_exact_future_continuation_including_births_mutations_and_history(self):
        world, clock, history = experiment()
        clock.speed = 4
        clock.advance(3.083)
        checkpoint_births = world.births
        checkpoint_id = world._next_organism_id
        # Exercise the JSON path, not just an in-memory copy of RNG tuples.
        with tempfile.TemporaryDirectory() as directory:
            path = save_world(Path(directory) / "world.json", world, clock, history)
            loaded = load_world(path)
            loaded.clock.paused = False
            for index in range(600):
                speed = (1, 2, 4)[index // 200]
                clock.speed = loaded.clock.speed = speed
                elapsed = (1 / 60, 1 / 120, 0.047)[index % 3]
                clock.advance(elapsed)
                loaded.clock.advance(elapsed)
                if index % 100 == 0:
                    self.assertEqual(comparable(world, clock, history), comparable(loaded.world, loaded.clock, loaded.history))
            self.assertGreater(world.births, checkpoint_births)
            offspring = [o for o in world.organisms.values() if o.id >= checkpoint_id and o.parent_id in world.organisms]
            self.assertTrue(offspring)
            self.assertTrue(any(o.traits != world.organisms[o.parent_id].traits for o in offspring))
            self.assertEqual(comparable(world, clock, history), comparable(loaded.world, loaded.clock, loaded.history))
            # A second checkpoint must preserve the same trajectory again.
            save_world(path, loaded.world, loaded.clock, loaded.history)
            loaded = load_world(path)
            loaded.clock.paused = False
            clock.advance(5.013)
            loaded.clock.advance(5.013)
            self.assertEqual(comparable(world, clock, history), comparable(loaded.world, loaded.clock, loaded.history))

    def test_retained_buffer_founders_and_sampling_phase_survive(self):
        world, clock, history = experiment(capacity=3)
        clock.advance(5.017)
        loaded = restore(document(world, clock, history))
        self.assertEqual(loaded.history.samples.maxlen, 3)
        self.assertEqual(loaded.history.baseline, history.baseline)
        self.assertEqual(loaded.history.dropped_samples, 3)
        self.assertEqual(list(loaded.history.samples), list(history.samples))
        loaded.clock.paused = False
        loaded.clock.advance(1)
        clock.advance(1)
        self.assertEqual(comparable(world, clock, history), comparable(loaded.world, loaded.clock, loaded.history))

    def test_extinction_round_trip_and_absent_selection(self):
        world, clock, history = experiment(ExperimentSettings(initial_population=1))
        world.organisms[1].energy = 0.001
        # Start diagnostics after this test-only energy injection.
        from genesis.diagnostics import Diagnostics
        world.diagnostics = Diagnostics.observe_existing(world)
        clock.advance(1 / 30)
        data = document(world, clock, history)
        data["selection"] = 1
        loaded = restore(data)
        self.assertIsNone(loaded.selected_id)
        self.assertFalse(loaded.world.organisms)
        self.assertEqual(list(loaded.history.samples), list(history.samples))
        self.assertEqual(loaded.clock.advance(100), 0)

    def test_initial_and_paused_worlds_round_trip(self):
        world, clock, history = experiment()
        for paused in (False, True):
            clock.paused = paused
            loaded = restore(document(world, clock, history))
            self.assertEqual(comparable(world, clock, history), comparable(loaded.world, loaded.clock, loaded.history))

    def test_schema_validation_rejects_corrupt_state(self):
        world, clock, history = experiment()
        clock.advance(12.013)
        original = document(world, clock, history)
        changes = [
            lambda d: d.update(version=99),
            lambda d: d.update(version=True),
            lambda d: d.update(format="other"),
            lambda d: d["config"].update(timestep=0.01),
            lambda d: d["settings"].update(seed=True),
            lambda d: d.update(preset="Scarcity"),
            lambda d: d["world"].update(next_organism_id=1),
            lambda d: d["world"].update(food_credit=1),
            lambda d: d["world"].update(rng_state=[3, [0], None]),
            lambda d: d["world"].update(rng_state=[3, [0] * 624 + [625], None]),
            lambda d: d["world"]["organisms"][0].update(energy=float("nan")),
            lambda d: d["world"]["organisms"][0].update(age=180),
            lambda d: d["world"]["organisms"][0].update(x=-1),
            lambda d: d["world"]["organisms"][0]["traits"].update(speed=100),
            lambda d: d["world"]["organisms"].append(d["world"]["organisms"][0]),
            lambda d: d["world"]["food"].append(d["world"]["food"][0]),
            lambda d: d["clock"].update(speed=3),
            lambda d: d["clock"].update(accumulator=1),
            lambda d: d["clock"].update(paused=1),
            lambda d: d["history"].update(capacity=999999),
            lambda d: d["history"].update(last_seen_tick=0),
            lambda d: d["history"].update(revision=1),
            lambda d: d["history"]["samples"][-1].update(tick=1),
            lambda d: d["history"]["baseline"].update(average_speed=50),
            lambda d: d["history"]["samples"][-1]["stats"].update(average_size=None),
            lambda d: d.update(selection="1"),
        ]
        for index, change in enumerate(changes):
            with self.subTest(case=index):
                bad = deepcopy(original)
                change(bad)
                with self.assertRaises(SaveError):
                    restore(bad)

    def test_malformed_missing_duplicate_oversized_and_unsupported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for content in (b"{bad", b"[]", b"\xff", b'{"format":"genesis-world","version":99}',
                            b'{"format":"genesis-world","format":"genesis-world"}', b" " * (MAX_BYTES + 1)):
                path.write_bytes(content)
                with self.assertRaises(SaveError):
                    load_world(path)
            with self.assertRaisesRegex(SaveError, "Unsupported save version"):
                path.write_text('{"format":"genesis-world","version":99}', encoding="utf-8")
                load_world(path)
            with self.assertRaises(SaveError):
                load_world(Path(directory) / "missing.json")

    def test_failed_atomic_writes_preserve_existing_save_and_leave_no_temp_files(self):
        world, clock, history = experiment()
        with tempfile.TemporaryDirectory() as directory:
            path = save_world(Path(directory) / "world.json", world, clock, history)
            previous = path.read_bytes()
            clock.advance(1.01)
            before = document(world, clock, history)
            for operation in ("os.replace", "os.fsync", "tempfile.NamedTemporaryFile"):
                with self.subTest(operation=operation):
                    with patch(f"genesis.persistence.{operation}", side_effect=OSError("injected write failure")):
                        with self.assertRaisesRegex(SaveError, "injected write failure"):
                            save_world(path, world, clock, history)
                    self.assertEqual(path.read_bytes(), previous)
                    self.assertEqual(list(Path(directory).iterdir()), [path])
                    self.assertEqual(document(world, clock, history), before)
            save_world(path, world, clock, history)
            self.assertNotEqual(path.read_bytes(), previous)

    def test_presets_have_expected_settings_and_reproduce(self):
        self.assertEqual([p.name for p in PRESETS], ["Balanced", "Abundance", "Scarcity", "Rapid Mutation", PRESETS[4].name, PRESETS[5].name, "Changing Seasons", "Coexistence", "Living Ecosystem", "Living Seasons"])
        self.assertEqual(PRESETS[0].settings, ExperimentSettings())
        self.assertGreater(PRESETS[1].settings.food_per_second, 20)
        self.assertLess(PRESETS[2].settings.food_per_second, 20)
        self.assertGreater(PRESETS[3].settings.mutation_strength, 0.06)
        for preset in PRESETS:
            self.assertEqual(preset_name(preset.settings), preset.name)
            self.assertEqual(preset_name(replace(preset.settings, seed=9)), preset.name)
            a, ca, ha = experiment(preset.settings)
            b, cb, hb = experiment(preset.settings)
            ca.advance(12)
            cb.advance(12)
            self.assertEqual(document(a, ca, ha), document(b, cb, hb))
            self.assertEqual(asdict(preset.settings.config())["max_age"], 180)
        self.assertEqual(preset_name(ExperimentSettings(initial_population=22)), "Custom")
