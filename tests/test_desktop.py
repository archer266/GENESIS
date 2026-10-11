import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.user_files import DEFAULTS, Preferences, validate, window_geometry, writable_destination


class PreferenceTests(unittest.TestCase):
    def test_defaults_do_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Preferences(Path(directory)/"new")
            self.assertEqual(p.values, DEFAULTS)
            self.assertFalse(p.root.exists())

    def test_unicode_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Preferences(Path(directory)/"Living worlds Ω 日本語")
            v = dict(p.values, reduced=True, effects=False, guide_seen=True,
                     export_directory=str(p.root/"Exports Ω"), panel_tab="diagnostics")
            p.save(v)
            self.assertEqual(Preferences(p.root).values, v)

    def test_invalid_json_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Preferences(directory)
            for data in ("[", "null", '{"version": 99}', '{"version": 1, "effects": 1}', '{"version":1,"window_size":[true,900]}'):
                p.path.write_text(data)
                recovered = Preferences(directory)
                self.assertTrue(recovered.warning)
                self.assertEqual(recovered.values, DEFAULTS)

    def test_oversized_file_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Preferences(directory)
            p.path.write_text(" "*65537)
            self.assertTrue(Preferences(directory).warning)

    def test_failed_atomic_write_keeps_old_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Preferences(directory)
            p.save(p.values)
            original=p.path.read_bytes()
            with patch("genesis.user_files.os.replace", side_effect=OSError("locked")):
                with self.assertRaises(OSError):
                    p.save(dict(p.values, effects=False))
            self.assertEqual(p.path.read_bytes(), original)
            self.assertEqual(list(p.root.glob("*.tmp")), [])

    def test_missing_directory_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Preferences(directory)
            p.values["save_directory"]=str(Path(directory)/"unavailable")
            self.assertEqual(p.directory("save"), Path(directory)/"Worlds")
            p.values["save_directory"]=directory
            self.assertEqual(p.directory("save"), Path(directory))

    def test_frozen_destinations_outside_bundle_only(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/"app"
            with patch("sys.frozen", True, create=True), patch("sys.executable", str(bundle/"GENESIS.exe")):
                with self.assertRaises(ValueError):
                    writable_destination(bundle/"nested/world.json")
                self.assertEqual(writable_destination(bundle/"../save Ω.json"), Path(directory)/"save Ω.json")

    def test_unavailable_monitor_clamps_window(self):
        v=dict(DEFAULTS, window_size=[3000, 2000], window_position=[-2800, 1900])
        self.assertEqual(window_geometry(v,(1920,1080)), ((1920,1080),(0,0)))

    def test_bad_layout_and_paths_rejected(self):
        for key,value in (("panel_tab","unknown"),("panel_rect",[0,0,-1,2]),("save_directory","a\0b"), ("fullscreen","true")):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, **{key:value}))


class DesktopAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    def test_preferences_and_guide_do_not_change_world(self):
        import pygame
        from genesis.app import App
        from genesis.persistence import document
        with tempfile.TemporaryDirectory() as directory:
            p=Preferences(directory)
            p.save(dict(p.values, reduced=True, effects=False, guide_seen=True, panel_tab="worlds"))
            a=App(preferences=p)
            self.assertTrue(a.glass.reduced)
            self.assertEqual(a.guide_until,0)
            before=document(a.world,a.sim_clock,a.history)
            a.show_guide(); a.activate_control("dismiss_guide")
            a.save_preferences()
            self.assertEqual(document(a.world,a.sim_clock,a.history),before)
            self.assertEqual(Preferences(directory).values["panel_tab"],"worlds")
            pygame.quit()

    def test_save_success_remembers_directory_but_failure_does_not(self):
        import pygame
        from genesis.app import App
        with tempfile.TemporaryDirectory() as directory:
            p=Preferences(Path(directory)/"prefs")
            a=App(preferences=p)
            dest=Path(directory)/"Worlds Ω"/"saved.json"
            self.assertTrue(a.save_file(dest))
            remembered=Preferences(p.root).values["save_directory"]
            self.assertEqual(remembered,str(dest.parent))
            with patch("genesis.app.save_world",side_effect=OSError("denied")):
                self.assertFalse(a.save_file(Path(directory)/"failed/world.json"))
            self.assertEqual(Preferences(p.root).values["save_directory"],remembered)
            pygame.quit()

    def test_csv_picker_and_cancel(self):
        import pygame
        from genesis.app import App
        from genesis.file_dialogs import WorldFilePicker
        with tempfile.TemporaryDirectory() as directory:
            a=App(preferences=Preferences(directory))
            picker=WorldFilePicker(True,42,0,directory,".csv","sample.csv")
            picker.accept()
            self.assertEqual(picker.result,str(Path(directory)/"sample.csv"))
            a.observatory.export(a,picker.result)
            self.assertFalse(a.observatory.notice_error)
            other=WorldFilePicker(True,42,0,directory,".csv","sample.csv")
            other.accept()
            self.assertTrue(other.running)
            with patch("genesis.floating_ui.WorldFilePicker.run",return_value=""):
                a.observatory.export_action(a,"lineage")
            self.assertEqual(a.observatory.notice,"Export canceled.")
            pygame.quit()
