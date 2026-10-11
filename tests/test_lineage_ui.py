import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile
import json
from pathlib import Path
import unittest
import pygame
from genesis.app import App
from genesis.persistence import document, restore


class LineageUITests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.p = self.app.observatory
        parent = self.app.world.organisms[1]
        parent.age = 8
        self.children = []
        for _ in range(8):
            parent.energy, parent.cooldown = 180, 0
            self.children.append(self.app.world._reproduce(parent))
        self.app.selected_id = 1
        self.app.activate_control("details")

    def tearDown(self):
        pygame.quit()

    def test_archived_relative_browsing_select_follow_and_death_lifecycle(self):
        a, p = self.app, self.p
        child = self.children[0]
        p.activate(a, f"relative_children_{child.id}")
        self.assertEqual(p.lineage_view.view_id, child.id)
        self.assertEqual(a.selected_id, 1)
        p.activate(a, "lineage_select")
        self.assertEqual(a.selected_id, child.id)
        self.assertIsNone(a.follow_id)
        p.activate(a, "lineage_follow")
        self.assertEqual(a.follow_id, child.id)
        child.energy = .001
        a.update(1/30)
        self.assertIsNone(a.selected_id)
        self.assertIsNone(a.follow_id)
        self.assertEqual(p.lineage_view.view_id, child.id)
        a.draw()
        self.assertIn("lineage_select", p.disabled)
        self.assertEqual(p.lineage_view.status(a.world.lineage.records[child.id]), "Dead")
        p.activate(a, "relative_ancestors_1")
        p.activate(a, "lineage_follow")
        self.assertEqual(a.follow_id, 1)
        a.reset()
        self.assertIsNone(p.lineage_view.view_id)

    def test_virtual_lists_scroll_and_keyboard_selection_without_camera_input(self):
        a, p = self.app, self.p
        p.scrolls["cell"] = 1050
        a.draw()
        rect = p.lineage_view.list_rects["children"].move(p.content.x, p.content.y-p.scrolls["cell"]).clip(p.content)
        before = (a.camera.x, a.camera.y, a.scale, a.world.rng.getstate())
        offset = p.scrolls["cell"]
        a.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-2, pos=rect.center))
        self.assertEqual(p.lineage_view.offsets["children"], 2)
        self.assertEqual(p.scrolls["cell"], offset)
        self.assertEqual(before, (a.camera.x, a.camera.y, a.scale, a.world.rng.getstate()))
        self.assertLessEqual(sum(k.startswith("relative_children") for k in p.content_buttons), 5)
        p.keyboard_focus = f"relative_children_{self.children[2].id}"
        a.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
        self.assertEqual(p.lineage_view.view_id, self.children[2].id)
        self.assertEqual(a.selected_id, 1)

    def test_unavailable_record_load_clear_and_csv_ui_errors(self):
        a, p = self.app, self.p
        p.lineage_view.view(99999)
        a.draw()
        self.assertIn("lineage_follow", p.disabled)
        self.assertEqual(p.lineage_view.rows["ancestors"], [(99999, None)])
        a.reset()
        a.update(.1)
        loaded = restore(document(a.world, a.sim_clock, a.history))
        p.lineage_view.view(1)
        a.apply_loaded(loaded, "example.json")
        self.assertIsNone(p.lineage_view.view_id)
        p.show(a, "worlds")
        self.assertIn("export_lineage", p.content_buttons)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"lineage.csv"
            p.export_lineage(a, path)
            self.assertFalse(p.notice_error)
            self.assertIn(str(path.resolve()), p.notice)
            p.export_lineage(a, path)
            self.assertTrue(p.notice_error)
            self.assertIn("Lineage export failed", p.notice)
            before = a.world
            bad = document(a.world, a.sim_clock, a.history)
            bad["lineage"]["records"][0]["parent_id"] = 1
            invalid = Path(root)/"bad-archive.json"
            invalid.write_text(json.dumps(bad), encoding="utf-8")
            self.assertFalse(a.load_file(invalid))
            self.assertIs(a.world, before)
            self.assertIn("founder", p.world_notice.lower())
