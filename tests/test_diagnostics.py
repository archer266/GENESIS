import csv
from copy import deepcopy
from dataclasses import asdict
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from genesis.diagnostics import Diagnostics, LIMIT
from genesis.observatory import ExperimentSettings, History
from genesis.persistence import document, restore, load_world, SaveError
from genesis.simulation import World, Config, Traits, SimulationClock


def experiment(seed=12):
    s=ExperimentSettings(seed=seed,predator_enabled=True,initial_predators=8,habitat_enabled=True,
                         seasons_enabled=True,droughts_enabled=True,season_length=40,drought_interval=30,drought_duration=5)
    w=World(seed,s.config()); h=History(w,s); c=SimulationClock(w,h.on_step)
    return w,h,c


class DiagnosticTests(unittest.TestCase):
    def test_coexistence_is_opt_in_existing_settings_only(self):
        from genesis.presets import PRESETS, preset_name
        s=next(p.settings for p in PRESETS if p.name=='Coexistence')
        self.assertEqual(preset_name(s),'Coexistence')
        self.assertEqual((s.seed,s.map_seed),(101,101))
        self.assertEqual((s.initial_population,s.initial_predators,s.food_per_second,s.mutation_strength),(160,4,24,.005))
        self.assertTrue(s.habitat_enabled and s.seasons_enabled and s.droughts_enabled)
        self.assertEqual((s.season_length,s.drought_duration,s.drought_interval),(300,5,300))
        self.assertEqual(ExperimentSettings.from_text(s.text_values()),s)
        self.assertEqual(PRESETS[0].settings,ExperimentSettings())
        self.assertEqual((s.config().predator_energy_multiplier,s.config().catch_efficiency,s.config().reproduction_cost),(2.5,.65,6))

    def test_old_custom_recipe_still_loads_after_preset_is_named(self):
        from genesis.presets import PRESETS
        s=next(p.settings for p in PRESETS if p.name=='Coexistence')
        w=World(s.seed,s.config());h=History(w,s);c=SimulationClock(w,h.on_step)
        old=document(w,c,h);old['version']=5;old['preset']='Custom';del old['diagnostics']
        old.pop("ecology",None)
        old["settings"].pop("rules_version",None)
        old["config"].pop("rules_version",None)
        loaded=restore(old)
        self.assertEqual(loaded.settings,s)
        self.assertTrue(loaded.world.diagnostics.legacy)

    def test_cap_deferrals_are_observations_without_energy_or_rng_cost(self):
        w=World(1,Config(initial_population=0,initial_food=0,population_cap=2,predator_enabled=True,predator_cap=1))
        a=w.add_organism(100,100,energy=160,age=10,species='predator')
        before=w.rng.getstate()
        self.assertIsNone(w._reproduce(a))
        self.assertEqual(w.diagnostics.totals['predator']['predator_cap_blocks'],1)
        self.assertEqual(a.energy,160);self.assertEqual(w.rng.getstate(),before)
        w.add_organism(400,400)
        before=w.rng.getstate()
        self.assertIsNone(w._reproduce(a))
        self.assertEqual(w.diagnostics.totals['predator']['population_cap_blocks'],1)
        self.assertEqual(a.energy,160);self.assertEqual(w.rng.getstate(),before)

    def test_founders_birth_transfer_and_energy_ledger(self):
        w=World(1,Config(initial_population=1,initial_food=0,food_per_second=0))
        o=next(iter(w.organisms.values()));o.energy=160;o.age=10
        w.diagnostics=Diagnostics.observe_existing(w)
        before=sum(o.energy for o in w.organisms.values())
        child=w._reproduce(o)
        self.assertIsNotNone(child)
        t=w.diagnostics.totals['prey']
        self.assertEqual(t['births'],1);self.assertEqual(t['offspring_transferred'],65)
        self.assertEqual(t['reproduction_spent'],6)
        self.assertEqual(before-sum(o.energy for o in w.organisms.values()),6)
        self.assertEqual(w.diagnostics.totals['predator']['births'],0)

    def test_feeding_overflow_and_catch_once(self):
        w=World(2,Config(initial_population=0,initial_food=0,predator_enabled=True))
        prey=w.add_organism(100,100,energy=170)
        w._eat(prey,w.add_food(100,100))
        self.assertEqual(w.diagnostics.totals['prey']['feeding_gained'],10)
        self.assertEqual(w.diagnostics.totals['prey']['feeding_overflow'],17)
        a=w.add_organism(100,100,energy=175,species='predator')
        b=w.add_organism(100,100,species='predator')
        w.resolve_catches();w.resolve_catches()
        self.assertEqual(w.catches,1)
        self.assertEqual(w.diagnostics.totals['predator']['feeding_gained'],5)
        self.assertAlmostEqual(w.diagnostics.totals['predator']['feeding_overflow'],112)
        self.assertEqual(w.diagnostics.living_catches,{str(a.id):1,str(b.id):0})
        self.assertEqual(w.diagnostics.totals['prey']['deaths_caught'],1)

    def test_death_causes_and_metabolic_energy(self):
        w=World(1,Config(initial_population=0,initial_food=0,food_per_second=0,predator_enabled=True))
        a=w.add_organism(100,100,energy=.001)
        b=w.add_organism(800,700,species='predator');b.age=w.config.max_age
        w.step()
        self.assertFalse(w.organisms)
        self.assertEqual(w.diagnostics.totals['prey']['deaths_energy'],1)
        self.assertEqual(w.diagnostics.totals['predator']['deaths_age'],1)
        self.assertEqual(w.diagnostics.dead_predators,1)
        for t in w.diagnostics.totals.values():
            self.assertAlmostEqual(t['initial_energy']-t['metabolism_spent']-t['death_energy_removed'],0)

    def test_rng_and_full_phase8_trajectory_unchanged(self):
        spec=importlib.util.spec_from_file_location('phase8_reference',Path(__file__).parent/'fixtures/phase8_simulation.py')
        old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        w,h,c=experiment()
        reference=old.World(w.seed,old.Config(**{k:v for k,v in asdict(w.config).items() if k in old.Config.__dataclass_fields__}))
        for _ in range(1200):
            w.step();reference.step()
        self.assertEqual([asdict(o) for o in w.organisms.values()],[asdict(o) for o in reference.organisms.values()])
        self.assertEqual([asdict(f) for f in w.food.values()],[asdict(f) for f in reference.food.values()])
        self.assertEqual(w.rng.getstate(),reference.rng.getstate())
        self.assertEqual(w.environment.document(),reference.environment.document())
        self.assertEqual((w.births,w.deaths,w.catches),(reference.births,reference.deaths,reference.catches))

    def test_bounded_samples_recent_rates_and_document_copy(self):
        w,h,c=experiment();c.advance(65.5)
        self.assertEqual(len(w.diagnostics.samples),LIMIT)
        seconds,rates=w.diagnostics.recent(w)
        self.assertGreater(seconds,59);self.assertLessEqual(seconds,60)
        self.assertGreaterEqual(rates['predator_catches'],0)
        doc=w.diagnostics.document();doc['samples'][0]['tick']=-1
        self.assertGreaterEqual(w.diagnostics.samples[0]['tick'],0)
        self.assertEqual(Diagnostics.restore(w.diagnostics.document(),w).document(),w.diagnostics.document())

    def test_speeds_and_reproducibility(self):
        results=[]
        for speed in (1,2,4):
            w,h,c=experiment();c.speed=speed
            for _ in range(1200//speed):c.advance(1/30)
            results.append((w.diagnostics.document(),w.rng.getstate(),w.environment.document()))
        self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

    def test_save_continuation_and_no_save_side_effects(self):
        w,h,c=experiment();c.advance(39.4)
        rng=w.rng.getstate();erng=w.environment.rng.getstate();before=w.diagnostics.document()
        doc=document(w,c,h);loaded=restore(doc);loaded.clock.paused=False
        self.assertEqual(before,w.diagnostics.document());self.assertEqual(w.rng.getstate(),rng);self.assertEqual(w.environment.rng.getstate(),erng)
        c.advance(45);loaded.clock.advance(45)
        self.assertEqual(document(w,c,h),document(loaded.world,loaded.clock,loaded.history))

    def test_legacy_versions_mark_unknown_and_resume(self):
        for file in ('phase3_world_v1.json','phase4_world_v2.json','phase6_world_v3.json','phase7_world_v4.json','phase8_world_v5.json'):
            loaded=load_world(Path(__file__).parent/'fixtures'/file)
            d=loaded.world.diagnostics
            self.assertTrue(d.legacy);self.assertEqual(d.since_tick,loaded.world.ticks)
            self.assertEqual(sum(t['births'] for t in d.totals.values()),0)
            loaded.clock.paused=False;loaded.clock.advance(2)
            resumed=restore(document(loaded.world,loaded.clock,loaded.history))
            self.assertEqual(resumed.world.diagnostics.document(),d.document())

    def test_invalid_state_rejected(self):
        w,h,c=experiment();c.advance(2);doc=document(w,c,h)
        mutations=[lambda d:d['totals']['predator'].__setitem__('catches',999),
                   lambda d:d['totals']['prey'].__setitem__('feeding_gained',float('nan')),
                   lambda d:d['totals']['prey'].__setitem__('metabolism_spent',0),
                   lambda d:d['living_catches'].__setitem__('999999',0),
                   lambda d:d['samples'].pop(0), lambda d:d.__setitem__('since_tick',100000),
                   lambda d:d.__setitem__('capacity',100000)]
        for mutate in mutations:
            bad=deepcopy(doc);mutate(bad['diagnostics'])
            with self.assertRaises(SaveError):restore(bad)

    def test_csv_energy_and_origin_without_rng_effects(self):
        w,h,c=experiment();c.advance(2.2);before=document(w,c,h)
        with tempfile.TemporaryDirectory() as folder:
            path=w.diagnostics.export_csv(Path(folder)/'d.csv',w,h.settings)
            with path.open() as f: rows=list(csv.DictReader(f))
            self.assertEqual(float(rows[-1]['simulation_seconds']),w.time)
            self.assertEqual(float(rows[-1]['predator_catches']),w.catches)
            self.assertEqual(rows[-1]['legacy_partial'],'False')
            self.assertIn('predator_metabolism_spent',rows[-1])
            with self.assertRaises(FileExistsError):w.diagnostics.export_csv(path,w,h.settings)
        self.assertEqual(before,document(w,c,h))

if __name__=='__main__':unittest.main()
