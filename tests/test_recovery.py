import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.ecology import recommended_settings
from genesis.observatory import History
from genesis.simulation import World, SimulationClock
from genesis.persistence import document, load_world, SaveError
from genesis.recovery import Recovery, find_recovery, write_recovery


def experiment():
    settings = recommended_settings()
    world = World(settings.seed, settings.config())
    history = History(world, settings)
    return world, SimulationClock(world, history.on_step), history


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.world, self.clock, self.history = experiment()
        self.time = 0
        self.r = Recovery(self.root, now=lambda: self.time)

    def tearDown(self):
        self.r.enabled = False
        self.r.close(self.world, self.clock, self.history)
        self.temp.cleanup()

    def wait(self):
        if self.r.future:
            try:
                self.r.future.result(timeout=15)
            except Exception:
                pass
        self.r._poll()

    def test_interval_unchanged_pause_disabled_and_rng(self):
        before = document(self.world, self.clock, self.history)
        self.time = 119
        self.r.tick(self.world, self.clock, self.history)
        self.assertIsNone(self.r.future)
        self.time = 120
        self.r.tick(self.world, self.clock, self.history)
        self.wait()
        self.assertEqual(document(self.world, self.clock, self.history), before)
        latest = self.r.root/'latest.json'
        stamp = latest.stat().st_mtime_ns
        self.clock.paused = True
        self.time = 240
        self.r.tick(self.world, self.clock, self.history)
        self.assertIsNone(self.r.future)
        self.assertEqual(latest.stat().st_mtime_ns, stamp)
        self.r.set_enabled(False)
        self.r.changed_world()
        self.time = 999
        self.r.tick(self.world, self.clock, self.history)
        self.assertIsNone(self.r.future)

    def test_rotation_fallback_and_corrupt_latest_not_rotated(self):
        data = document(self.world, self.clock, self.history)
        write_recovery(self.r.root, data)
        self.clock.advance(1)
        write_recovery(self.r.root, document(self.world, self.clock, self.history))
        self.assertEqual(load_world(self.r.root/'previous.json').world.ticks, 0)
        (self.r.root/'latest.json').write_text('{')
        loaded, path, reason = find_recovery(self.r.root)
        self.assertEqual(loaded.world.ticks, 0)
        self.assertIn('previous', reason)
        write_recovery(self.r.root, document(self.world, self.clock, self.history))
        self.assertEqual(load_world(path).world.ticks, 0)

    def test_failed_commit_preserves_valid_recovery_and_reports_once_per_interval(self):
        write_recovery(self.r.root, document(self.world, self.clock, self.history))
        self.clock.advance(1)
        with patch('genesis.persistence.os.replace', side_effect=OSError('disk full')):
            self.r.changed_world()
            self.r.tick(self.world, self.clock, self.history)
            self.wait()
        self.assertTrue(self.r.error)
        self.assertIn('disk full', self.r.status)
        self.assertEqual(load_world(self.r.root/'latest.json').world.ticks, 0)
        self.r.tick(self.world, self.clock, self.history)
        self.assertIsNone(self.r.future)
        self.assertFalse(list(self.r.root.glob('*.tmp')))

    def test_invalid_new_snapshot_does_not_rotate(self):
        data = document(self.world, self.clock, self.history)
        write_recovery(self.r.root, data)
        before = (self.r.root/'latest.json').read_bytes()
        data['version'] = 999
        with self.assertRaises(SaveError):
            write_recovery(self.r.root, data)
        self.assertEqual((self.r.root/'latest.json').read_bytes(), before)
        self.assertFalse((self.r.root/'previous.json').exists())

    def test_detached_capture_and_exact_continuation(self):
        captured = []
        def writer(root, snapshot):
            captured.append(snapshot)
            return write_recovery(root, snapshot)
        self.clock.advance(30)
        with patch('genesis.recovery.write_recovery', side_effect=writer):
            self.r.changed_world()
            self.r.tick(self.world, self.clock, self.history)
            self.wait()
        loaded = load_world(self.r.root/'latest.json')
        self.assertTrue(loaded.clock.paused)
        loaded.clock.paused = False
        self.clock.advance(30)
        loaded.clock.advance(30)
        self.assertEqual(document(self.world, self.clock, self.history), document(loaded.world, loaded.clock, loaded.history))
        self.assertEqual(captured[0]['world']['ticks'], 900)

    def test_worker_snapshot_stays_detached_while_world_advances(self):
        from threading import Event
        ready, release = Event(), Event()
        actual = write_recovery
        def blocked_writer(root, snapshot):
            ready.set()
            if not release.wait(10):
                raise RuntimeError('Test writer timed out')
            return actual(root, snapshot)
        before = document(self.world, self.clock, self.history)
        with patch('genesis.recovery.write_recovery', side_effect=blocked_writer):
            self.r.changed_world()
            self.r.tick(self.world, self.clock, self.history)
            self.assertTrue(ready.wait(5))
            first = self.r.future
            try:
                self.clock.advance(1)
                self.r.changed_world()
                self.r.tick(self.world, self.clock, self.history)
                self.assertIs(self.r.future, first)
            finally:
                release.set()
            self.wait()
        loaded = load_world(self.r.root/'latest.json')
        loaded.clock.paused = False
        self.assertEqual(document(loaded.world, loaded.clock, loaded.history), before)
        self.r.close(self.world, self.clock, self.history)
        self.assertEqual(load_world(self.r.root/'latest.json').world.ticks, 30)

    def test_failed_latest_replace_keeps_both_old_snapshots(self):
        import os
        data = document(self.world, self.clock, self.history)
        write_recovery(self.r.root, data)
        replace = os.replace
        def fail_latest(source, target):
            if Path(target).name == 'latest.json':
                raise OSError('commit failed')
            return replace(source, target)
        self.clock.advance(1)
        with patch('genesis.persistence.os.replace', side_effect=fail_latest), self.assertRaises(SaveError):
            write_recovery(self.r.root, document(self.world, self.clock, self.history))
        for name in ('latest.json', 'previous.json'):
            self.assertEqual(load_world(self.r.root/name).world.ticks, 0)

    def test_no_valid_recovery_and_pending_shutdown_never_overwrites(self):
        self.r.root.mkdir()
        for name in ('latest.json', 'previous.json'):
            (self.r.root/name).write_text('{')
        self.assertIsNone(find_recovery(self.r.root)[0])
        self.assertIn('No valid recovery', find_recovery(self.r.root)[2])
        self.r.pending_choice = True
        self.r.close(self.world, self.clock, self.history)
        self.assertEqual((self.r.root/'latest.json').read_text(), '{')

    def test_single_writer_pending_choice_and_shutdown(self):
        from concurrent.futures import Future
        self.r.pending_choice = True
        self.r.changed_world()
        self.r.tick(self.world, self.clock, self.history)
        self.assertIsNone(self.r.future)
        self.r.pending_choice = False
        blocked = Future()
        self.r.future = blocked
        self.r.tick(self.world, self.clock, self.history)
        self.assertIs(self.r.future, blocked)
        self.r.future = None
        self.r.close(self.world, self.clock, self.history)
        self.assertEqual(load_world(self.r.root/'latest.json').world.ticks, 0)
        self.r.executor = None


class RecoveryUITests(unittest.TestCase):
    def test_startup_choices_manual_load_toggle_and_new_experiment(self):
        import pygame
        from genesis.app import App
        from genesis.user_files import Preferences
        with tempfile.TemporaryDirectory() as root:
            world, clock, history = experiment()
            clock.advance(1)
            write_recovery(Path(root)/'Recovery', document(world, clock, history))
            app = App(preferences=Preferences(root))
            try:
                app.offer_recovery()
                app.update(500)
                self.assertEqual(app.world.ticks, 0)
                self.assertIsNone(app.recovery.future)
                app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
                self.assertTrue(app.recovery.pending_choice)
                app.observatory.activate(app, 'confirm')
                self.assertEqual(app.world.ticks, 30)
                self.assertTrue(app.sim_clock.paused)
                app.recovery.future.result(timeout=15)
                app.recovery._poll()
                app.offer_recovery()
                app.observatory.activate(app, 'cancel')
                self.assertFalse(app.recovery.pending_choice)
                if app.recovery.future:
                    app.recovery.future.result(timeout=15)
                    app.recovery._poll()
                app.observatory.activate(app, 'autosave')
                self.assertFalse(Preferences(root).values['autosave'])
                app.start_experiment(app.settings)
                self.assertIsNone(app.recovery.future)
                app.observatory.activate(app, 'autosave')
                app.start_experiment(app.settings)
                app.recovery.future.result(timeout=15)
                app.recovery._poll()
                self.assertEqual(load_world(Path(root)/'Recovery/latest.json').world.ticks, 0)
                self.assertTrue(app.load_file(Path(root)/'Recovery/previous.json'))
                app.close_recovery()
                self.assertEqual(load_world(Path(root)/'Recovery/latest.json').world.ticks, app.world.ticks)
            finally:
                app.close_recovery()
                pygame.quit()
