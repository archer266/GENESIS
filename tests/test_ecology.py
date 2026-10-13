"""Rules-2 mechanics, observation isolation, persistence and Classic comparison."""
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import math
from pathlib import Path
import random
import sys
import unittest

from genesis import ecology
from genesis.observatory import ExperimentSettings, History
from genesis.persistence import document, restore, SaveError, load_world
from genesis.simulation import World, Config, Traits, SimulationClock


def empty(**kwargs):
    config=replace(ecology.recommended_settings().config(),initial_population=0,initial_predators=0,
                   initial_food=0,food_per_second=0,**kwargs)
    return World(211,config)


class EcologyTests(unittest.TestCase):
    def test_fast_cell_arrives_instead_of_orbiting(self):
        for rules,remaining in ((1,1),(2,0)):
            w=empty(rules_version=rules,maturity_age=1000,max_age=1000,predator_enabled=False,habitat_enabled=False)
            o=w.add_organism(568.75,380,Traits(75,90,3),energy=180)
            o.heading=math.pi/2;w.add_food(550,380)
            for _ in range(900):w.step()
            self.assertEqual(len(w.food),remaining)

    def test_particle_specialists_and_energy_bounds(self):
        w=empty()
        foods=[w.add_food(500,350) for _ in range(3)]
        for kind,size in enumerate(ecology.PARTICLE_SIZES):
            o=w.add_organism(500,350,Traits(40,90,size))
            values=[ecology.feeding_value(o,f,w.config) for f in foods]
            self.assertEqual(max(range(3),key=values.__getitem__),kind)
            self.assertTrue(all(0<v<=w.config.food_energy*1.4 for v in values))

    def test_incompatible_food_cannot_be_depleted_by_other_specialists(self):
        w=empty();small=w.add_organism(500,350,Traits(40,90,3.75))
        foods=[w.add_food(500,350) for _ in range(3)]
        w._remove_food(foods[0])
        self.assertIsNone(ecology.nearest_food(w,small))
        large=w.add_organism(500,350,Traits(40,90,8))
        self.assertEqual(ecology.nearest_food(w,large),foods[2])
        for size in (3,4,5,6,7,8,9):
            self.assertGreaterEqual(max(ecology.efficiencies(size)),.25)

    def test_unused_food_resource_does_not_block_other_resources(self):
        w=empty(food_cap=6)
        ecology.regenerate_food(w,60)
        self.assertEqual(len(w.food),6)
        self.assertEqual([sum((f.id-1)%3==k for f in w.food.values()) for k in range(3)],[2,2,2])
        for food in list(w.food.values()):
            if (food.id-1)%3==0:w._remove_food(food)
        ecology.regenerate_food(w,6)
        self.assertEqual(len(w.food),6)
        self.assertEqual(sum((f.id-1)%3==0 for f in w.food.values()),2)

    def test_speed_sense_body_cost_and_dense_effort(self):
        w=empty();o=w.add_organism(500,350)
        baseline=ecology.energy_rate(o,40)
        self.assertGreater(ecology.energy_rate(o,60),baseline)
        self.assertAlmostEqual(ecology.energy_rate(o,24,.6),baseline)
        resting=ecology.energy_rate(o,0)
        o.traits=replace(o.traits,speed=75)
        self.assertGreater(ecology.energy_rate(o,0),resting)
        for key,value in (('sense',150),('size',8)):
            o.traits=replace(Traits(),**{key:value})
            self.assertGreater(ecology.energy_rate(o,40),baseline)

    def test_reflection_has_no_clipped_point_mass(self):
        rng=random.Random(211)
        for edge in (0,1):
            parent=Traits(*(v[edge] for v in Traits.BOUNDS.values()))
            for _ in range(500):
                child=ecology.mutate(parent,rng,.2)
                for key,(low,high) in Traits.BOUNDS.items():
                    self.assertLess(low,getattr(child,key));self.assertLess(getattr(child,key),high)

    def test_mutation_inheritance_zero_strength_and_rng_count(self):
        a=random.Random(8);b=random.Random(8)
        self.assertEqual(ecology.mutate(Traits(),a,0),Traits())
        for _ in range(3):b.uniform(0,0)
        self.assertEqual(a.getstate(),b.getstate())

    def test_hunters_pay_local_interference_not_global_population(self):
        w=empty();a=w.add_organism(200,200,species='predator')
        b=w.add_organism(200,200,species='predator')
        def grid(x,y):w._animal_grid={w._cell(x,y):[(b.id,x,y,b.species)]}
        grid(200,200);self.assertAlmostEqual(ecology.interference(w,a),1.5)
        grid(1000,700);self.assertEqual(ecology.interference(w,a),0)
        grid(280,200);self.assertAlmostEqual(ecology.interference(w,a),.75)

    def test_catches_once_seeded_order_and_handling(self):
        for reversed_order in (False,True):
            w=empty();prey=w.add_organism(500,350,energy=100)
            a=w.add_organism(500,350,energy=50,species='predator')
            b=w.add_organism(500,350,energy=50,species='predator')
            order=[a.id,b.id][::(-1 if reversed_order else 1)]
            ecology.catches(w,order)
            winner=w.organisms[order[0]]
            self.assertEqual(w.catches,1);self.assertNotIn(prey.id,w.organisms)
            self.assertAlmostEqual(winner.energy,115)
            self.assertIn(winner.id,w.handling)
            other=w.add_organism(500,350,energy=100)
            ecology.catches(w,[winner.id])
            self.assertIn(other.id,w.organisms)

    def test_body_size_benefit_in_hunting(self):
        w=empty();victim=w.add_organism(500,350,Traits(size=9),energy=100)
        hunter=w.add_organism(500,350,Traits(size=3),energy=50,species='predator')
        ecology.catches(w,[hunter.id]);self.assertIn(victim.id,w.organisms)
        hunter.traits=replace(hunter.traits,size=6)
        ecology.catches(w,[hunter.id]);self.assertIn(victim.id,w.organisms)
        hunter.traits=replace(hunter.traits,size=8)
        ecology.catches(w,[hunter.id]);self.assertNotIn(victim.id,w.organisms)

    def test_small_prey_detection_and_sensing_benefit(self):
        w=empty()
        hunter=w.add_organism(500,350,Traits(55,100,8),species='predator')
        prey=w.add_organism(570,350,Traits(40,90,3.75))
        w._animal_grid={w._cell(prey.x,prey.y):[(prey.id,prey.x,prey.y,prey.species)]}
        self.assertIsNone(ecology.nearest_animal(w,hunter))
        hunter.traits=replace(hunter.traits,sense=160)
        self.assertEqual(ecology.nearest_animal(w,hunter)[0],prey.id)
        hunter.traits=replace(hunter.traits,sense=100)
        prey.traits=replace(prey.traits,size=7)
        self.assertEqual(ecology.nearest_animal(w,hunter)[0],prey.id)

    def test_prey_flee_and_hunters_pursue(self):
        w=empty(habitat_enabled=False)
        prey=w.add_organism(550,350,Traits(40,90,5),energy=100)
        hunter=w.add_organism(500,350,Traits(55,100,7),energy=100,species='predator')
        prey.heading=hunter.heading=0
        w.step()
        self.assertGreater(prey.x,550)
        self.assertGreater(hunter.x,500)
        self.assertLess(prey.x-hunter.x,50)

    def test_digesting_hunter_stationary_with_positive_cost(self):
        w=empty();o=w.add_organism(500,350,energy=100,species='predator')
        w.handling[o.id]=5
        w.step()
        self.assertEqual((o.x,o.y),(500,350));self.assertLess(o.energy,100)
        self.assertAlmostEqual(w.handling[o.id],5-w.config.timestep)

    def test_species_reproduction_is_funded_and_limited(self):
        for species,energy,age,transfer,cooldown in (('prey',150,10,65,12),('predator',170,25,80,45)):
            w=empty();parent=w.add_organism(500,350,energy=energy,age=age,species=species)
            child=w._reproduce(parent)
            self.assertIsNotNone(child)
            self.assertEqual(child.energy,transfer)
            self.assertEqual(parent.energy+child.energy,energy-w.config.reproduction_cost)
            self.assertEqual(parent.cooldown,cooldown)
            self.assertIsNone(w._reproduce(parent))
            self.assertEqual(child.parent_id,parent.id)

    def test_population_cap_and_handling_cleanup(self):
        w=empty(population_cap=1)
        o=w.add_organism(500,350,energy=170,age=25,species='predator')
        self.assertIsNone(w._reproduce(o));w.handling[o.id]=4;o.energy=.0001
        w.step();self.assertFalse(w.organisms);self.assertFalse(w.handling)

    def test_no_food_leads_to_extinction_without_respawn(self):
        w=empty();w.add_organism(500,350,energy=.001);w.step()
        for _ in range(90):w.step()
        self.assertFalse(w.organisms)

    def test_species_lifespans_still_require_energy(self):
        w=empty()
        prey=w.add_organism(100,100,age=179.99,energy=100)
        predator=w.add_organism(900,600,age=179.99,energy=100,species='predator')
        w.step()
        self.assertNotIn(prey.id,w.organisms)
        self.assertIn(predator.id,w.organisms)
        self.assertLess(predator.energy,100)
        predator.age=359.99
        w.step()
        self.assertNotIn(predator.id,w.organisms)

    def test_ecology_presentation_cannot_change_world_or_rng(self):
        from genesis.visuals import VisualState, organism_color
        settings=ecology.recommended_settings()
        a,b=World(211,settings.config()),World(211,settings.config())
        visuals=VisualState(b)
        for tick in range(1200):
            a.step();b.step();visuals.on_step(b);visuals.advance(1/30)
            if tick%53==0:visuals.toggle()
            for o in b.organisms.values():organism_color(o);visuals.pose(o,.5)
        self.assertEqual(a.organisms,b.organisms)
        self.assertEqual(a.food,b.food)
        self.assertEqual(a.handling,b.handling)
        self.assertEqual(a.rng.getstate(),b.rng.getstate())

    def test_same_seed_and_speed_equivalence(self):
        results=[]
        settings=ecology.recommended_settings(stress=True)
        for speed in (1,2,4):
            w=World(211,settings.config());h=History(w,replace(settings,seed=211))
            clock=SimulationClock(w,h.on_step);clock.speed=speed
            for _ in range(1800//speed):clock.advance(1/30)
            self.assertGreater(w.births,0)
            self.assertGreater(w.catches,0)
            self.assertGreater(w.diagnostics.totals['predator']['births'],0)
            data=document(w,clock,h);data['clock']['speed']=1
            self.assertAlmostEqual(data['clock']['accumulator'],0,places=12)
            data['clock']['accumulator']=0
            results.append(data)
        self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])

    def test_exact_continuation_including_handling_and_mutations(self):
        settings=replace(ecology.recommended_settings(stress=True),seed=211)
        w=World(settings.seed,settings.config());h=History(w,settings);clock=SimulationClock(w,h.on_step)
        clock.advance(25)
        before=document(w,clock,h)
        self.assertTrue(before['ecology']['handling'])
        loaded=restore(before);loaded.clock.paused=False
        self.assertEqual(document(w,clock,h),before)
        for _ in range(900):clock.advance(1/30);loaded.clock.advance(1/30)
        self.assertEqual(document(w,clock,h),document(loaded.world,loaded.clock,loaded.history))
        self.assertGreater(w.births,0);self.assertGreater(w.catches,0)

    def test_invalid_rules_and_handling_rejected(self):
        settings=ecology.recommended_settings();w=World(42,settings.config());h=History(w,settings);clock=SimulationClock(w,h.on_step)
        original=document(w,clock,h)
        for edit in (lambda d:d['settings'].update(rules_version=3),
                     lambda d:d['config'].update(rules_version=True),
                     lambda d:d['ecology']['handling'].update({'1':1}),
                     lambda d:d['ecology']['handling'].update({'161':11}),
                     lambda d:d['ecology']['handling'].update({'999999':1})):
            candidate=deepcopy(original);edit(candidate)
            with self.assertRaises(SaveError):restore(candidate)

    def test_continuation_across_drought_and_season_transitions(self):
        settings=replace(ecology.recommended_settings(stress=True),seed=211,
                         season_length=40,drought_interval=30,drought_duration=5)
        w=World(settings.seed,settings.config());h=History(w,settings)
        clock=SimulationClock(w,h.on_step)
        for _ in range(w.environment.next_drought-1):clock.advance(1/30)
        before=document(w,clock,h)
        loaded=restore(before);loaded.clock.paused=False
        for _ in range(900):clock.advance(1/30);loaded.clock.advance(1/30)
        self.assertGreater(w.environment.drought_count,before['environment']['drought_count'])
        self.assertNotEqual(w.environment.rng.getstate(),before['environment']['rng_state'])
        self.assertEqual(document(w,clock,h),document(loaded.world,loaded.clock,loaded.history))

    def test_invalid_resource_capacity_rejected(self):
        settings=ecology.recommended_settings()
        w=World(settings.seed,settings.config());h=History(w,settings)
        data=document(w,SimulationClock(w),h)
        for index,item in enumerate(data['world']['food']):item['id']=3*(index+1)
        data['world']['next_food_id']=3*len(w.food)+1
        with self.assertRaisesRegex(SaveError,'resource capacity'):restore(data)

    def test_classic_matches_original_rules_and_rng(self):
        spec=importlib.util.spec_from_file_location('phase10_reference',Path(__file__).parent/'fixtures/phase10_simulation.py')
        old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        settings=ExperimentSettings(predator_enabled=True,initial_predators=8,habitat_enabled=True,seasons_enabled=True,droughts_enabled=True)
        current=World(42,settings.config())
        reference=old.World(42,old.Config(**{k:v for k,v in asdict(current.config).items() if k!='rules_version'}))
        for _ in range(900):current.step();reference.step()
        self.assertEqual([asdict(o) for o in current.organisms.values()],[asdict(o) for o in reference.organisms.values()])
        self.assertEqual(current.rng.getstate(),reference.rng.getstate())
        self.assertEqual(current.diagnostics.document(),reference.diagnostics.document())

    def test_body_color_range_and_rendering_rng_isolation(self):
        from genesis.visuals import trait_color
        colors=[trait_color(Traits(size=s)) for s in (3,4,5,6,7,8,9)]
        self.assertEqual(len(set(colors)),len(colors))
        w=World(42,ecology.recommended_settings().config());state=w.rng.getstate()
        for o in w.organisms.values():trait_color(o.traits)
        self.assertEqual(w.rng.getstate(),state)
