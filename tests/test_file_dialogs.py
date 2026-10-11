import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    from genesis.file_dialogs import WorldFilePicker
except ImportError:
    pygame = None


@unittest.skipIf(pygame is None, "Pygame is not installed")
class FilePickerTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def tearDown(self):
        pygame.quit()

    def test_navigation_filter_scroll_and_minimum_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "subfolder").mkdir()
            (root / "ignore.txt").write_text("not a world")
            for index in range(30):
                (root / f"save{index}.json").write_text("{}")
            picker = WorldFilePicker(False, 42, 0, root)
            self.assertEqual(len(picker.entries), 31)
            self.assertEqual(picker.entries[0].name, "subfolder")
            picker.draw()
            for rect in picker.controls.values():
                self.assertTrue(picker.box.contains(rect))
            picker.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-2))
            self.assertGreater(picker.scroll, 0)
            picker.navigate(root / "subfolder")
            self.assertEqual(picker.directory, root / "subfolder")
            picker.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=picker.controls["up"].center))
            self.assertEqual(picker.directory, root)
            picker.navigate(root / "missing")
            self.assertIn("Cannot open folder", picker.status)
            self.assertEqual(picker.directory, root)

    def test_save_extension_replace_confirmation_and_cancel_do_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.json"
            path.write_text("original")
            picker = WorldFilePicker(True, 42, 0, directory)
            picker.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="old.json"))
            picker.accept()
            self.assertTrue(picker.running)
            self.assertEqual(picker.confirm_overwrite, path)
            picker.accept()
            self.assertFalse(picker.running)
            self.assertEqual(picker.result, str(path))
            self.assertEqual(path.read_text(), "original")
            picker = WorldFilePicker(True, 42, 0, directory)
            picker.text["filename"] = "new"
            picker.accept()
            self.assertEqual(picker.result, str(Path(directory) / "new.json"))
            self.assertFalse(Path(picker.result).exists())
            picker = WorldFilePicker(False, 42, 0, directory)
            picker.text["filename"] = "missing.json"
            picker.accept()
            self.assertIn("does not exist", picker.status)
            picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            self.assertEqual(picker.result, "")
            self.assertFalse(picker.running)

    def test_real_modal_loop_accepts_text_input_and_load_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "choice.json"
            path.write_text("{}")
            picker = WorldFilePicker(False, 42, 0, directory)
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=str(path)))
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.assertEqual(picker.run(), str(path))
