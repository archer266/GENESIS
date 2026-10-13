import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from genesis.app import App
from genesis.camera import Camera
from genesis.observatory import History
from genesis.persistence import document
from genesis.presets import PRESETS
from genesis.simulation import World, SimulationClock


class CameraMathTests(unittest.TestCase):
    def camera(self):
        c = Camera(1100, 760)
        c.resize((24, 94, 800, 550))
        return c

    def test_conversions_round_trip_at_all_zoom_levels_and_offsets(self):
        c = self.camera()
        for zoom in (1, 1.2, 3, 6):
            c.zoom = zoom
            c.pan(30, -17)
            for point in ((0, 0), (1100, 760), (378.2, 500.6)):
                actual = c.screen_to_world(*c.world_to_screen(*point))
                self.assertAlmostEqual(actual[0], point[0])
                self.assertAlmostEqual(actual[1], point[1])

    def test_zoom_anchors_cursor_except_when_world_bounds_require_clamping(self):
        c = self.camera()
        point = (327, 264)
        before = c.screen_to_world(*point)
        c.zoom_at(point, 4)
        after = c.screen_to_world(*point)
        self.assertAlmostEqual(before[0], after[0])
        self.assertAlmostEqual(before[1], after[1])
        c.zoom_at(point, -4)
        self.assertAlmostEqual(c.zoom, 1)
        c.zoom_at(point, 1000)
        self.assertEqual(c.zoom, c.max_zoom)
        c.zoom_at(point, -1000)
        self.assertEqual(c.zoom, 1)

    def test_pan_bounds_fit_resize_and_smooth_follow(self):
        c = self.camera()
        c.zoom = 3
        c.pan(100000, -100000)
        self.assertGreaterEqual(c.left, -1e-9)
        self.assertLessEqual(c.top + c.viewport[3] / c.scale, c.height + 1e-9)
        c.fit()
        c.zoom = 3
        a, b = self.camera(), self.camera()
        a.zoom = b.zoom = 3
        for _ in range(60):
            a.follow(700, 400, 1/60)
        for _ in range(30):
            b.follow(700, 400, 1/30)
        self.assertAlmostEqual(a.x, b.x)
        self.assertAlmostEqual(a.y, b.y)
        self.assertTrue(550 < a.x < 700)
        c.resize((0, 0, 3840, 2160))
        c.zoom_at((1900, 1000), 20)
        self.assertLessEqual(c.scale, 8)
        c.fit()
        self.assertEqual((c.x, c.y), (550, 380))


class CameraAppTests(unittest.TestCase):
    def setUp(self):
        self.app = App(settings=PRESETS[5].settings)

    def tearDown(self):
        pygame.quit()

    def event(self, event_type, **kwargs):
        self.app.handle_event(pygame.event.Event(event_type, **kwargs))

    def test_selection_and_right_drag_do_not_conflict_at_multiple_zooms(self):
        app = self.app
        organism = min(app.world.organisms.values(), key=lambda o: (o.x-550)**2 + (o.y-380)**2)
        for zoom in (1, 2, 6):
            app.camera.zoom = zoom
            app.camera.x, app.camera.y = organism.x, organism.y
            app.camera.clamp()
            pose = app.visuals.pose(organism, app.alpha)
            self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.position(pose.x, pose.y))
            self.assertEqual(app.selected_id, organism.id)
        app.toggle_follow()
        self.event(pygame.MOUSEBUTTONDOWN, button=3, pos=app.viewport.center)
        self.event(pygame.MOUSEMOTION, rel=(30, -10), pos=app.viewport.center, buttons=(0, 0, 1))
        self.assertIsNone(app.follow_id)
        self.assertEqual(app.selected_id, organism.id)
        self.event(pygame.MOUSEBUTTONUP, button=3, pos=(0, 0))
        self.assertIsNone(app.drag_button)

    def test_wheel_routing_sidebar_scroll_and_fit(self):
        app = self.app
        panel = app.observatory
        panel.show(app, "settings")
        panel.notice = "Path / " * 200
        app.draw()
        self.event(pygame.MOUSEWHEEL, y=3, pos=(350, 450))
        self.assertGreater(app.camera.zoom, 1)
        zoom = app.camera.zoom
        self.event(pygame.MOUSEWHEEL, y=-2, pos=app.sidebar.center)
        self.assertEqual(app.camera.zoom, zoom)
        self.assertGreater(panel.scrolls["settings"], 0)
        self.event(pygame.KEYDOWN, key=pygame.K_HOME, mod=0)
        self.assertEqual(app.camera.zoom, 1)

    def test_follow_death_pause_reset_and_load_lifecycle(self):
        app = self.app
        target = next(iter(app.world.organisms.values()))
        app.selected_id = target.id
        app.camera.zoom = 3
        app.toggle_follow()
        app.sim_clock.paused = True
        before = (app.camera.x, app.camera.y)
        app.update(.05)
        self.assertNotEqual(before, (app.camera.x, app.camera.y))
        self.assertEqual(app.world.ticks, 0)
        app.sim_clock.paused = False
        target.energy = 0
        app.update(1/30)
        self.assertIsNone(app.follow_id)
        self.assertIsNone(app.selected_id)
        self.assertIn("died", app.camera_notice)
        self.assertGreater(app.notice_remaining, 0)
        app.reset()
        self.assertIsNone(app.follow_id)
        self.assertEqual(app.camera.zoom, 1)
        app.selected_id = next(iter(app.world.organisms))
        app.toggle_follow()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "camera.json"
            self.assertTrue(app.save_file(path))
            self.assertTrue(app.load_file(path))
        self.assertIsNone(app.follow_id)
        self.assertEqual(app.camera.zoom, 1)
        self.assertTrue(app.sim_clock.paused)
        self.assertNotIn("camera", document(app.world, app.sim_clock, app.history))

    def test_camera_fx_and_hidden_ui_preserve_exact_seeded_results(self):
        app = self.app
        control = World(app.seed, app.settings.config())
        history = History(control, app.settings)
        clock = SimulationClock(control, history.on_step)
        for i in range(180):
            if i % 15 == 0:
                app.camera.zoom_at(app.viewport.center, 1 if i % 30 == 0 else -1)
                app.camera.pan(3, -4)
                app.visuals.toggle()
                app.toggle_ui()
                app.selected_id = next(iter(app.world.organisms))
                app.toggle_follow()
                app.draw()
            app.update(1/30)
            clock.advance(1/30)
        self.assertEqual(document(app.world, app.sim_clock, app.history), document(control, clock, history))

    def test_hidden_controls_restore_and_fullscreen_transitions_preserve_world(self):
        app = self.app
        before = document(app.world, app.sim_clock, app.history)
        self.event(pygame.KEYDOWN, key=pygame.K_i, mod=0)
        self.assertTrue(app.ui_hidden)
        self.assertFalse(app.observatory.buttons)
        self.assertIn("hide_ui", app.buttons)
        app.draw()
        self.event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0)
        self.assertFalse(app.ui_hidden)
        # Dummy SDL can emulate mode switches, but real fullscreen is checked separately.
        size = app.screen.get_size()
        self.event(pygame.KEYDOWN, key=pygame.K_F11, mod=0)
        self.assertTrue(app.fullscreen)
        self.event(pygame.KEYDOWN, key=pygame.K_F11, mod=0)
        self.assertFalse(app.fullscreen)
        self.assertEqual(app.screen.get_size(), size)
        self.assertEqual(document(app.world, app.sim_clock, app.history), before)

    def test_renderer_clips_zoomed_world_and_caches_are_bounded(self):
        app = self.app
        app.camera.zoom = 6
        app.camera.clamp()
        app.viewport = pygame.Rect(50, 50, 800, 550)
        app.camera.resize(app.viewport)
        app.screen.fill((123, 45, 67))
        app.renderer.draw(app.screen, app.viewport, app.scale, app.world, app.visuals,
                          app.alpha, None, True, app.camera)
        self.assertEqual(app.screen.get_at((0, 0))[:3], (123, 45, 67))
        self.assertEqual(app.renderer._view_background.get_size(), app.viewport.size)
        self.assertEqual(app.renderer.overlay.get_size(), app.viewport.size)
        from genesis.visuals import cell_sprite, predator_sprite
        for make in (cell_sprite,predator_sprite):
            info=make.cache_info()
            self.assertLessEqual(info.currsize,512)
            self.assertLessEqual(info.bytes,16*1024*1024)

    def test_main_loop_processes_long_frame_without_discarding_ticks(self):
        app = self.app
        pygame.event.clear()
        with patch("genesis.app.pygame.time.Clock") as clock:
            clock.return_value.tick.return_value = 600
            clock.return_value.get_fps.return_value = 0
            app.run(frames=1)
        self.assertEqual(app.world.ticks, 18)  # A 600ms frame, not the old 250ms clamp.


if __name__ == "__main__":
    unittest.main()
