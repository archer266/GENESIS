import csv
from copy import deepcopy
from dataclasses import asdict, FrozenInstanceError
from pathlib import Path
import tempfile
import unittest

from genesis.lineage import LineageArchive
from genesis.observatory import ExperimentSettings, History
from genesis.persistence import document, restore, load_world, SaveError
from genesis.simulation import World, Config, Traits, SimulationClock


def experiment(settings=None):
    settings = settings or ExperimentSettings()
    world = World(settings.seed, settings.config())
    history = History(world, settings)
    return world, SimulationClock(world, history.on_step), history


class LineageTests(unittest.TestCase):
    def test_founders_and_birth_snapshots_are_immutable(self):
        world = World(8)
        for oid, organism in world.organisms.items():
            record = world.lineage.records[oid]
            self.assertEqual((record.id, record.species, record.parent_id, record.generation, record.birth_time),
                             (oid, "prey", None, 0, 0))
            self.assertEqual(record.traits, organism.traits)
        record = world.lineage.records[1]
        with self.assertRaises(FrozenInstanceError):
            record.generation = 7
        with self.assertRaises(FrozenInstanceError):
            record.traits.speed = 20
        with self.assertRaises(TypeError):
            world.lineage.records[1] = record
        with self.assertRaises(ValueError):
            world.lineage.record_birth(world.organisms[1], 2)

    def test_real_birth_relationships_times_and_signed_changes(self):
        w = World(9, Config(initial_population=1, initial_food=0, food_per_second=0))
        parent = w.organisms[1]
        parent.energy, parent.age = 180, 8
        w.step()
        child = next(o for o in w.organisms.values() if o.parent_id == 1)
        record = w.lineage.records[child.id]
        self.assertEqual(record.birth_time, w.time)
        self.assertEqual((record.parent_id, record.generation), (1, 1))
        self.assertEqual([oid for oid, _ in w.lineage.ancestry(child.id)], [child.id, 1])
        self.assertEqual(w.lineage.offspring(1), [record])
        self.assertEqual(w.lineage.changes(child.id), {key: getattr(child.traits, key)-getattr(parent.traits, key) for key in Traits.BOUNDS})
        self.assertIsNone(w.lineage.changes(1))

    def test_death_causes_and_once_only_lifecycle(self):
        for cause in ("energy", "age"):
            w = World(1, Config(initial_population=1, initial_food=0))
            old = w.lineage.records[1]
            if cause == "energy":
                w.organisms[1].energy = .001
            else:
                w.organisms[1].age = w.config.max_age
            w.step()
            record = w.lineage.records[1]
            self.assertEqual((record.death_time, record.death_cause), (w.time, cause))
            self.assertIsNone(old.death_time)
            self.assertEqual(record.traits, old.traits)
            w.lineage.record_death(1, 5, "caught")
            self.assertEqual(w.lineage.records[1], record)
        w = World(1, Config(initial_population=1, initial_predators=1, predator_enabled=True))
        prey, predator = w.organisms.values()
        predator.x, predator.y = prey.x, prey.y
        w.resolve_catches()
        self.assertEqual(w.lineage.records[prey.id].death_cause, "caught")
        self.assertIsNone(w.lineage.records[predator.id].death_time)

    def test_pruning_keeps_living_and_newest_dead_marks_missing(self):
        w, c, h = experiment(ExperimentSettings(initial_population=1))
        w.lineage.capacity = 300
        for _ in range(330):
            for oid, o in w.organisms.items():
                o.energy = 180 if oid == 1 else .001
                if oid == 1:
                    o.age, o.cooldown = 8, 0
            c.advance(1/30)
        self.assertEqual(len(w.lineage.records), 300)
        self.assertGreater(w.lineage.pruned_count, 0)
        self.assertIn(1, w.lineage.records)
        self.assertNotIn(2, w.lineage.records)
        self.assertEqual(w.lineage.ancestry(2), [(2, None)])
        self.assertIsNone(w.lineage.changes(2))
        # This fixture directly injects/removes energy; start observation after those interventions.
        from genesis.diagnostics import Diagnostics
        w.diagnostics = Diagnostics.observe_existing(w)
        loaded = restore(document(w, c, h))
        self.assertEqual(loaded.world.lineage.document(), w.lineage.document())
        loaded.clock.paused = False
        for _ in range(40):
            c.advance(1/30)
            loaded.clock.advance(1/30)
        self.assertEqual(document(w, c, h), document(loaded.world, loaded.clock, loaded.history))

    def test_tracking_and_queries_consume_no_rng_or_change_trajectory(self):
        settings = ExperimentSettings(predator_enabled=True, initial_predators=8, habitat_enabled=True)
        a = World(settings.seed, settings.config())
        b = World(settings.seed, settings.config())
        b.lineage.record_birth = lambda *args, **kwargs: None
        b.lineage.record_death = lambda *args, **kwargs: None
        for _ in range(600):
            a.step()
            b.step()
            a.lineage.ancestry(1)
            a.lineage.offspring(1)
            a.lineage.changes(1)
        for name in ("organisms", "food", "ticks", "births", "deaths", "catches", "_food_credit"):
            self.assertEqual(getattr(a, name), getattr(b, name))
        self.assertEqual(a.rng.getstate(), b.rng.getstate())
        self.assertGreater(a.births, 0)
        self.assertGreater(a.catches, 0)

    def test_old_versions_preserve_only_observed_information(self):
        w, c, h = experiment()
        c.advance(16)
        v3 = document(w, c, h)
        v3["version"] = 3
        del v3["lineage"]
        from genesis.environment import DEFAULTS, STAT_DEFAULTS
        del v3["environment"]
        del v3["diagnostics"]
        for key in DEFAULTS:
            del v3["settings"][key]
            del v3["config"][key]
        for row in [v3["history"]["baseline"]]+[s["stats"] for s in v3["history"]["samples"]]:
            for key in STAT_DEFAULTS:
                del row[key]
        v3.pop("ecology",None)
        v3["settings"].pop("rules_version",None)
        v3["config"].pop("rules_version",None)
        worlds = [restore(v3)] + [load_world(Path(__file__).parent/"fixtures"/name) for name in ("phase3_world_v1.json", "phase4_world_v2.json", "phase6_world_v3.json")]
        for loaded in worlds:
            archive = loaded.world.lineage
            self.assertEqual(set(archive.records), set(loaded.world.organisms))
            self.assertEqual(archive.legacy_unavailable, loaded.world.deaths)
            for record in archive.records.values():
                self.assertIsNone(record.birth_time)
                self.assertEqual(record.origin, "legacy_snapshot")
                self.assertEqual(record.recorded_time, loaded.world.time)
                self.assertIsNone(archive.changes(record.id))
            again = restore(document(loaded.world, loaded.clock, loaded.history))
            self.assertEqual(archive.document(), again.world.lineage.document())
        resumed = worlds[0]
        resumed.clock.paused = False
        for _ in range(150):
            c.advance(1/30)
            resumed.clock.advance(1/30)
        self.assertEqual(w.organisms, resumed.world.organisms)
        self.assertEqual(w.rng.getstate(), resumed.world.rng.getstate())
        self.assertTrue(any(r.origin == "birth" for r in resumed.world.lineage.records.values()))

    def test_v4_future_birth_mutation_death_and_speed_equivalence(self):
        settings = ExperimentSettings(predator_enabled=True, initial_predators=8, habitat_enabled=True)
        w, c, h = experiment(settings)
        c.advance(10.01)
        data = document(w, c, h)
        snapshots = []
        for speed in (1, 2, 4):
            loaded = restore(deepcopy(data))
            loaded.clock.paused = False
            loaded.clock.speed = speed
            for _ in range(240//speed):
                loaded.clock.advance(1/30)
            loaded.clock.speed = 1
            snapshots.append(document(loaded.world, loaded.clock, loaded.history))
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])
        for _ in range(240):
            c.advance(1/30)
        self.assertEqual(snapshots[0], document(w, c, h))
        self.assertGreater(w.births, data["world"]["births"])
        self.assertGreater(w.deaths, data["world"]["deaths"])

    def test_invalid_archive_records_references_and_lifecycle_rejected(self):
        w, c, h = experiment()
        c.advance(15)
        data = document(w, c, h)
        child_index = next(i for i, r in enumerate(data["lineage"]["records"]) if r["parent_id"] is not None)
        mutations = [lambda d: d["lineage"].update(capacity=999999),
                     lambda d: d["lineage"].update(pruned_count=999),
                     lambda d: d["lineage"]["records"].pop(),
                     lambda d: d["lineage"]["records"][1].update(id=1),
                     lambda d: d["lineage"]["records"][0].update(birth_time=-1),
                     lambda d: d["lineage"]["records"][0].update(death_time=0, death_cause="unknown"),
                     lambda d: d["lineage"]["records"][0]["traits"].update(speed=float("nan")),
                     lambda d: d["lineage"]["records"][child_index].update(parent_id=999999),
                     lambda d: d["lineage"]["records"][child_index].update(generation=0),
                     lambda d: d["lineage"]["records"][child_index].update(species="predator"),
                     lambda d: d["lineage"]["records"][0].update(origin="legacy_snapshot")]
        for mutate in mutations:
            bad = deepcopy(data)
            mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(SaveError):
                restore(bad)

    def test_csv_lifecycle_relationships_metadata_blanks_and_no_overwrite(self):
        w, c, h = experiment()
        c.advance(15)
        before = document(w, c, h)
        with tempfile.TemporaryDirectory() as root:
            path = w.lineage.export_csv(Path(root)/"lineage.csv", h.settings)
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(w.lineage.records))
            self.assertEqual(rows[0]["seed"], "42")
            self.assertEqual(rows[0]["parent_id"], "")
            self.assertEqual(rows[0]["delta_speed"], "")
            child = next(r for r in rows if r["parent_id"])
            self.assertEqual(float(child["delta_speed"]), w.lineage.changes(int(child["id"]))["speed"])
            with self.assertRaises(FileExistsError):
                w.lineage.export_csv(path, h.settings)
        self.assertEqual(document(w, c, h), before)
