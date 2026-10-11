import math
import os
import unittest
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from genesis.simulation import Config, SimulationClock, World
from test_observatory import state

try:
    import pygame
    from genesis.visuals import VisualState, cell_sprite, food_sprite
except ImportError:
    pygame = None


@unittest.skipIf(pygame is None, "Pygame is not installed")
class VisualTests(unittest.TestCase):
    def test_effects_observe_real_events_only(self):
        world = World(42, replace(Config(), initial_population=0, initial_food=0, food_per_second=0))
        parent = world.add_organism(200, 200, energy=160, age=10)
        dying = world.add_organism(500, 500, energy=0.001)
        world.add_food(200, 200)
        visuals = VisualState(world)
        self.assertFalse(visuals.effects)
        SimulationClock(world, visuals.on_step).advance(1 / 30)
        self.assertEqual({e.kind for e in world.events}, {"eat", "birth", "death"})
        self.assertEqual({e.kind for e in visuals.effects}, {"eat", "birth", "death"})
        self.assertNotIn(dying.id, visuals.current)
        self.assertNotIn(dying.id, visuals.previous)
        self.assertNotIn(dying.id, visuals.trails)
        child = next(o for o in world.organisms.values() if o.id != parent.id)
        for alpha in (0, 0.5, 1):
            pose = visuals.pose(child, alpha)
            self.assertEqual((pose.x, pose.y), (child.x, child.y))
        world.step()
        self.assertFalse(world.events)

    def test_interpolation_endpoints_midpoint_and_heading_wrap(self):
        world = World(42, replace(Config(), initial_population=0, initial_food=0, food_per_second=0))
        organism = world.add_organism(300, 300)
        organism.heading = math.pi - 0.1
        visuals = VisualState(world)
        organism.x += 10
        organism.y += 6
        organism.heading = -math.pi + 0.1
        visuals.on_step(world)
        self.assertEqual((visuals.pose(organism, 0).x, visuals.pose(organism, 0).y), (300, 300))
        mid = visuals.pose(organism, 0.5)
        self.assertEqual((mid.x, mid.y), (305, 303))
        self.assertAlmostEqual(mid.heading, math.pi)
        self.assertEqual(visuals.pose(organism, 1).x, 310)

    def test_enabled_disabled_and_toggled_effects_cannot_change_simulation(self):
        baseline = World(42)
        watched = World(42)
        visuals = VisualState(watched)
        a, b = SimulationClock(baseline), SimulationClock(watched, visuals.on_step)
        for index in range(1200):
            if index % 137 == 0:
                visuals.toggle()
            visuals.advance(1 / 60)
            a.advance(1 / 60)
            b.advance(1 / 60)
            for organism in list(watched.organisms.values())[:2]:
                visuals.pose(organism, b.accumulator / watched.config.timestep)
        self.assertEqual(state(baseline), state(watched))

    def test_effect_trail_and_sprite_caches_are_bounded(self):
        world = World(42)
        visuals = VisualState(world)
        clock = SimulationClock(world, visuals.on_step)
        # No presentation aging: stress hard bounds even when events accumulate.
        clock.advance(30)
        self.assertLessEqual(len(visuals.effects), visuals.MAX_EFFECTS)
        self.assertLessEqual(len(visuals.trails), world.config.population_cap)
        self.assertTrue(all(len(points) <= visuals.TRAIL_POINTS for points in visuals.trails.values()))
        for i in range(5):
            for radius in range(4, 21):
                for pulse in range(-2, 3):
                    cell_sprite(i, radius, pulse, True)
        self.assertLessEqual(cell_sprite.cache_info().currsize, 384)
        for size in range(2, 6):
            food_sprite(size, True)
        self.assertLessEqual(food_sprite.cache_info().currsize, 16)
        visuals.advance(2)
        self.assertFalse(visuals.effects)
        self.assertTrue(all(not points for points in visuals.trails.values()))
        visuals.toggle()
        self.assertFalse(visuals.trails)
