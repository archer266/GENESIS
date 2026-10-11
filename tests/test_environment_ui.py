import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import pygame
from genesis.app import App
from genesis.observatory import ExperimentSettings
from genesis.persistence import document


class EnvironmentUITests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.p = self.app.observatory

    def tearDown(self):
        pygame.quit()

    def key(self, key):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))

    def test_conditional_drafts_keyboard_and_confirmation(self):
        a, p = self.app, self.p
        p.show(a, "settings")
        p.values.update(season_length="44", drought_duration="6", drought_interval="31")
        self.assertNotIn("season_length", p.content_inputs)
        p.keyboard_focus = "seasons_enabled"
        self.key(pygame.K_SPACE)
        self.assertFalse(a.sim_clock.paused)
        self.assertIn("season_length", p.content_inputs)
        p.activate(a, "droughts_enabled")
        self.assertIn("drought_duration", p.content_inputs)
        p.activate(a, "seasons_enabled")
        p.activate(a, "droughts_enabled")
        self.assertEqual(p.values["season_length"], "44")
        self.assertEqual(p.values["drought_duration"], "6")
        self.assertEqual(p.draft_settings().drought_duration, 15)
        p.activate(a, "droughts_enabled")
        p.values["drought_duration"] = "999"
        p.activate(a, "start")
        self.assertTrue(p.notice_error)
        self.assertIsNone(p.pending)
        p.values["drought_duration"] = "6"
        p.activate(a, "start")
        self.assertIsNotNone(p.pending)
        self.assertFalse(a.world.environment.enabled)
        p.activate(a, "confirm")
        self.assertTrue(a.world.environment.enabled)

    def test_chip_events_panel_appearance_and_renderer_preserve_both_rngs(self):
        a, p = self.app, self.p
        a.start_experiment(ExperimentSettings(seasons_enabled=True, droughts_enabled=True))
        before = document(a.world, a.sim_clock, a.history)
        for size in ((1380, 900), (960, 720)):
            a.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
            a.draw()
            a.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=a.environment_chip.center))
            self.assertEqual(p.tab, "environment")
            self.assertIsNone(a.selected_id)
            a.draw()
            self.assertTrue(all(p.rect.contains(r) for r in p.buttons.values()))
            a.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-3, pos=p.content.center))
            self.assertGreater(p.scrolls["environment"], 0)
            p.activate(a, "environment_chip")
            a.draw()
            self.assertNotIn("environment_status", a.buttons)
            p.activate(a, "environment_chip")
            p.activate(a, "effects")
            p.activate(a, "transparency")
            a.draw()
            p.opened = False
        self.assertEqual(document(a.world, a.sim_clock, a.history), before)

    def test_invalid_environment_load_does_not_replace_active_world(self):
        a = self.app
        original = a.world
        bad = deepcopy(document(a.world, a.sim_clock, a.history))
        bad["environment"]["cycle_position"] = 50
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"invalid.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            self.assertFalse(a.load_file(path))
        self.assertIs(a.world, original)
        self.assertIn("cycle", self.p.world_notice)
