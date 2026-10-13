"""Conditional drafts and keyboard controls must remain presentation-only."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import unittest
import pygame
from genesis.app import App
from genesis.persistence import document
from genesis.observatory import ExperimentSettings


class RefinementTests(unittest.TestCase):
    def setUp(self):
        self.app = App(settings=ExperimentSettings())
        self.p = self.app.observatory
        self.p.show(self.app, "settings")

    def tearDown(self):
        pygame.quit()

    def key(self, key, mod=0):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))

    def test_only_corrected_rules_and_draft_isolation(self):
        p,a=self.p,self.app
        before=document(a.world,a.sim_clock,a.history)
        self.assertNotIn('rules_version',p.content_buttons)
        self.assertNotIn('rules_version',p.content_inputs)
        self.assertEqual(p.draft_settings().rules_version,2)
        p.activate(a,'defaults')
        self.assertEqual(p.draft_settings().rules_version,2)
        self.assertEqual(document(a.world,a.sim_clock,a.history),before)
        p.activate(a,'start')
        self.assertIsNotNone(p.pending)
        p.activate(a,'cancel')
        self.assertEqual(document(a.world,a.sim_clock,a.history),before)

    def test_obsolete_load_retains_current_world_and_only_corrected_presets(self):
        from pathlib import Path
        from genesis.presets import display_presets
        a=self.app
        before=document(a.world,a.sim_clock,a.history)
        self.assertFalse(a.load_file(Path(__file__).parent/'fixtures'/'phase10_world_v6.json'))
        self.assertTrue(a.observatory.world_notice_error)
        self.assertIn('obsolete',a.observatory.world_notice)
        self.assertEqual(document(a.world,a.sim_clock,a.history),before)
        self.assertEqual([p.name for _,p in display_presets()],['Living Ecosystem','Living Seasons'])
        self.assertTrue(all(p.settings.rules_version==2 for _,p in display_presets()))

    def test_toggles_conditional_fields_retained_drafts_and_effective_settings(self):
        p, a = self.p, self.app
        before = document(a.world, a.sim_clock, a.history)
        p.values.update(initial_predators="17", map_seed="123456")
        short = p.content_height()
        for field, toggle in (("initial_predators", "predator_enabled"), ("map_seed", "habitat_enabled")):
            self.assertNotIn(field, p.content_inputs)
            self.assertNotIn(toggle, p.content_inputs)
            p.activate(a, toggle)
            self.assertIn(field, p.content_inputs)
            p.activate(a, toggle)
            self.assertNotIn(field, p.content_inputs)
        self.assertEqual(p.values["initial_predators"], "17")
        self.assertEqual(p.values["map_seed"], "123456")
        self.assertEqual(p.draft_settings().initial_predators, 0)
        self.assertEqual(p.draft_settings().map_seed, 42)
        p.activate(a, "predator_enabled")
        p.activate(a, "habitat_enabled")
        self.assertEqual(p.draft_settings().initial_predators, 17)
        self.assertEqual(p.draft_settings().map_seed, 123456)
        self.assertEqual(p.content_height(), short+78)
        self.assertEqual(before, document(a.world, a.sim_clock, a.history))

    def test_keyboard_skips_hidden_fields_space_toggles_and_mouse_is_isolated(self):
        p, a = self.p, self.app
        p.focus("mutation_percent")
        self.key(pygame.K_TAB)
        self.assertEqual(p.keyboard_focus, "predator_enabled")
        self.assertIsNone(p.active_field)
        self.key(pygame.K_SPACE)
        self.assertEqual(p.values["predator_enabled"], "1")
        self.assertFalse(a.sim_clock.paused)
        self.key(pygame.K_TAB)
        self.assertEqual(p.keyboard_focus, "initial_predators")
        self.key(pygame.K_TAB, pygame.KMOD_SHIFT)
        self.key(pygame.K_RETURN)
        self.key(pygame.K_TAB)
        self.assertEqual(p.keyboard_focus, "habitat_enabled")
        self.key(pygame.K_SPACE)
        p.ensure_visible(a, "habitat_enabled")
        point = p.buttons["habitat_enabled"].center
        camera = (a.camera.x, a.camera.y, a.scale)
        for kind, values in ((pygame.MOUSEBUTTONDOWN, {"button": 3}),
                             (pygame.MOUSEMOTION, {"rel": (40, 40)}),
                             (pygame.MOUSEWHEEL, {"y": -2})):
            a.handle_event(pygame.event.Event(kind, pos=point, **values))
        self.assertEqual(camera, (a.camera.x, a.camera.y, a.scale))
        self.assertIsNone(a.selected_id)
        self.assertGreater(p.scrolls["settings"], 0)
