"""Optimized queries must be observationally identical to the frozen old queries."""
from dataclasses import asdict
import importlib.util
from pathlib import Path
import sys
import unittest

from genesis.simulation import Config, Traits, World

spec = importlib.util.spec_from_file_location("spatial_reference", Path(__file__).parent / "fixtures/phase4_simulation.py")
legacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = legacy
spec.loader.exec_module(legacy)


class ReferenceWorld(World):
    # These three methods were unchanged between Phase 4 and Phase 5.
    resolve_catches = legacy.World.resolve_catches
    nearest_animal = legacy.World.nearest_animal
    _reproduce = legacy.World._reproduce


def state(world):
    return ([asdict(o) for o in world.organisms.values()], [asdict(f) for f in world.food.values()],
            [asdict(e) for e in world.events], world.rng.getstate(), world.ticks,
            world.births, world.deaths, world.catches, world._food_credit,
            world._next_organism_id, world._next_food_id)


class SpatialEquivalenceTests(unittest.TestCase):
    def test_exact_trajectory_against_previous_queries_in_habitat_and_uniform_worlds(self):
        for habitats in (False, True):
            for seed in (7, 42, 2026):
                config = Config(initial_population=260, predator_enabled=True, initial_predators=40,
                                habitat_enabled=habitats, map_seed=seed, food_per_second=80)
                actual, expected = World(seed, config), ReferenceWorld(seed, config)
                for tick in range(360):
                    actual.step()
                    expected.step()
                    if tick % 60 == 0:
                        self.assertEqual(state(actual), state(expected))
                self.assertEqual(state(actual), state(expected))
                self.assertGreater(actual.catches, 0)
                self.assertGreater(actual.births, 0)

    def test_grid_boundaries_equal_distance_ties_and_competing_hunters(self):
        config = Config(initial_population=0, initial_food=0, food_per_second=0, predator_enabled=True)
        actual, expected = World(3, config), ReferenceWorld(3, config)
        for world in (actual, expected):
            # Contacts across grid boundaries, largest allowed bodies, exact tangency,
            # two predators contesting prey, and prey IDs out of spatial order.
            for x in (71, 80, 151, 160, 1082):
                world.add_organism(x, 80, Traits(60, 120, 9), energy=20, species="predator")
                world.add_organism(x+18, 80, Traits(40, 90, 9))
                world.add_organism(x-18, 80, Traits(40, 90, 9))
            # Insertion order may not be ID order after externally constructed worlds.
            world.organisms = dict(reversed(list(world.organisms.items())))
            world.resolve_catches()
        self.assertEqual(state(actual), state(expected))
        self.assertGreater(actual.catches, 0)
