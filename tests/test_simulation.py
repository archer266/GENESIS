from dataclasses import asdict, replace
import random
import unittest

from genesis.simulation import Config, SimulationClock, Traits, World, energy_rate


def empty_world(**overrides):
    config = replace(Config(), initial_population=0, initial_food=0, food_per_second=0, **overrides)
    return World(42, config)


def snapshot(world):
    return (world.ticks, world.births, world.deaths,
            [asdict(o) for o in world.organisms.values()],
            [asdict(f) for f in world.food.values()], world.rng.getstate(), world._food_credit)


class EcosystemTests(unittest.TestCase):
    def test_energy_consumption_and_trait_costs(self):
        world = empty_world()
        organism = world.add_organism(500, 350)
        initial = organism.energy
        for _ in range(30):
            world.step()
        self.assertAlmostEqual(organism.energy, initial - energy_rate(organism.traits))
        baseline = energy_rate(Traits())
        for trait in (Traits(speed=60), Traits(sense=140), Traits(size=8)):
            self.assertGreater(energy_rate(trait), baseline)

    def test_eating_restores_energy_and_removes_food(self):
        world = empty_world()
        organism = world.add_organism(500, 350, energy=60)
        food = world.add_food(500, 350)
        world.step()
        self.assertAlmostEqual(organism.energy, 60 + world.config.food_energy - energy_rate(organism.traits) / 30)
        self.assertNotIn(food.id, world.food)
        self.assertIsNone(world.nearest_food(organism))

    def test_food_cannot_be_eaten_twice_and_energy_is_capped(self):
        world = empty_world()
        a = world.add_organism(500, 350, energy=179)
        b = world.add_organism(500, 350, energy=179)
        world.add_food(500, 350)
        world.step()
        energies = sorted((a.energy, b.energy))
        self.assertEqual(energies[1], 180)
        self.assertLess(energies[0], 179)

    def test_reproduction_transfers_energy_and_records_lineage(self):
        world = empty_world()
        parent = world.add_organism(500, 350, energy=160, age=10, generation=3)
        world.step()
        self.assertEqual(len(world.organisms), 2)
        child = world.organisms[2]
        self.assertEqual(child.parent_id, parent.id)
        self.assertEqual(child.generation, 4)
        self.assertEqual(child.age, 0)
        self.assertEqual(child.energy, world.config.offspring_energy)
        expected = 160 - energy_rate(parent.traits) / 30 - world.config.reproduction_cost
        self.assertAlmostEqual(parent.energy + child.energy, expected)
        self.assertEqual(world.births, 1)
        self.assertGreater(parent.cooldown, 0)

    def test_reproduction_requires_energy_maturity_cooldown_and_capacity(self):
        for kwargs in ({"energy": 100, "age": 10}, {"energy": 160, "age": 0},
                       {"energy": 160, "age": 10, "cooldown": 2}):
            world = empty_world()
            world.add_organism(500, 350, **kwargs)
            world.step()
            self.assertEqual(world.births, 0)
        world = empty_world(population_cap=1)
        parent = world.add_organism(500, 350, energy=160, age=10)
        world.step()
        self.assertEqual(world.births, 0)
        self.assertAlmostEqual(parent.energy, 160 - energy_rate(parent.traits) / 30)

    def test_inheritance_and_bounded_mutations(self):
        rng = random.Random(111)
        parent = Traits()
        for _ in range(1000):
            child = parent.mutated(rng)
            for name, (low, high) in Traits.BOUNDS.items():
                self.assertGreaterEqual(getattr(child, name), low)
                self.assertLessEqual(getattr(child, name), high)
                self.assertLessEqual(abs(getattr(child, name) / getattr(parent, name) - 1), Traits.MUTATION + 1e-12)
            parent = child
        for endpoint in (0, 1):
            parent = Traits(**{name: bounds[endpoint] for name, bounds in Traits.BOUNDS.items()})
            for _ in range(100):
                child = parent.mutated(rng)
                for name, (low, high) in Traits.BOUNDS.items():
                    self.assertTrue(low <= getattr(child, name) <= high)
        world = empty_world()
        parent = world.add_organism(500, 350, Traits(60, 140, 8), energy=160, age=10)
        world.step()
        child = world.organisms[2]
        for name in Traits.BOUNDS:
            self.assertLessEqual(abs(getattr(child.traits, name) / getattr(parent.traits, name) - 1), 0.06)

    def test_death_by_energy_and_age(self):
        for kwargs in ({"energy": 0.01}, {"age": 180 - 1 / 60}):
            world = empty_world()
            organism = world.add_organism(500, 350, **kwargs)
            world.add_food(500, 350)
            world.step()
            self.assertNotIn(organism.id, world.organisms)
            self.assertEqual(world.deaths, 1)
            self.assertEqual(world.births, 0)

    def test_sensing_is_local_and_steering_targets_food(self):
        world = empty_world()
        organism = world.add_organism(500, 350)
        world.add_food(650, 350)
        self.assertIsNone(world.nearest_food(organism))
        food = world.add_food(540, 350)
        self.assertEqual(world.nearest_food(organism), food)
        organism.heading = 0.5
        world.step()
        self.assertLess(organism.heading, 0.5)
        self.assertGreater(organism.x, 500)

    def test_wandering_and_world_boundaries(self):
        world = empty_world()
        organism = world.add_organism(5, 5)
        organism.heading = -2.4
        world.step()
        self.assertGreater(organism.wander_timer, 0)
        for _ in range(300):
            world.step()
            self.assertTrue(organism.traits.size <= organism.x <= world.config.width - organism.traits.size)
            self.assertTrue(organism.traits.size <= organism.y <= world.config.height - organism.traits.size)

    def test_food_renewal_and_cap(self):
        world = empty_world(food_cap=7)
        world.config = replace(world.config, food_per_second=3)
        for _ in range(30):
            world.step()
        self.assertEqual(len(world.food), 3)
        for _ in range(90):
            world.step()
        self.assertEqual(len(world.food), 7)

    def test_seed_reproducibility_and_reset(self):
        a, b = World(17), World(17)
        for _ in range(600):
            a.step()
            b.step()
        self.assertEqual(snapshot(a), snapshot(b))
        self.assertEqual(snapshot(World(17)), snapshot(World(17)))
        self.assertNotEqual(snapshot(World(17)), snapshot(World(18)))

    def test_speed_changes_preserve_exact_simulation_rules(self):
        snapshots = []
        for speed in (1, 2, 4):
            clock = SimulationClock(World(77))
            clock.speed = speed
            for _ in range(1200 // speed):
                clock.advance(1 / 60)
            self.assertEqual(clock.world.ticks, 600)
            snapshots.append(snapshot(clock.world))
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[0], snapshots[2])
        mixed = SimulationClock(World(77))
        for speed, frames in ((1, 240), (2, 240), (4, 120)):
            mixed.speed = speed
            for _ in range(frames):
                mixed.advance(1 / 60)
        self.assertEqual(snapshot(mixed.world), snapshots[0])

    def test_pause_and_extinction_stop_clock(self):
        clock = SimulationClock(World())
        before = snapshot(clock.world)
        clock.paused = True
        self.assertEqual(clock.advance(10), 0)
        self.assertEqual(snapshot(clock.world), before)
        clock = SimulationClock(empty_world())
        self.assertEqual(clock.advance(10), 0)


if __name__ == "__main__":
    unittest.main()
