"""Floating glass interface regressions; native visual checks live in tools."""
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from genesis.app import App
from genesis.observatory import History
from genesis.persistence import document
from genesis.presets import PRESETS
from genesis.simulation import World, SimulationClock


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.panel = self.app.observatory

    def tearDown(self):
        pygame.quit()

    def event(self, kind, **values):
        self.app.handle_event(pygame.event.Event(kind, **values))

    def key(self, key, mod=0):
        self.event(pygame.KEYDOWN, key=key, mod=mod)

    def click(self, point, mouse=1):
        self.event(pygame.MOUSEBUTTONDOWN, button=mouse, pos=point)

    def control(self, key):
        self.app._layout()
        if key in self.panel.content_buttons or key in self.panel.content_inputs:
            self.panel.ensure_visible(self.app, key)
        boxes = {**self.app.buttons, **self.panel.buttons, **self.panel.inputs}
        self.click(boxes[key].center)

    def test_default_world_fills_window_and_panel_never_resizes_or_pauses_it(self):
        a = self.app
        self.assertFalse(self.panel.opened)
        self.assertEqual(a.viewport, a.screen.get_rect())
        self.assertEqual(set(a.buttons), {"pause", "1", "2", "4", "observatory"})
        before = (a.viewport.copy(), a.camera.x, a.camera.y, a.scale)
        self.control("observatory")
        self.assertTrue(self.panel.opened)
        self.assertFalse(a.sim_clock.paused)
        self.assertEqual(before, (a.viewport, a.camera.x, a.camera.y, a.scale))
        a.update(.1)
        self.assertEqual(a.world.ticks, 3)
        self.control("close")
        self.assertFalse(self.panel.opened)
        self.assertEqual(before, (a.viewport, a.camera.x, a.camera.y, a.scale))

    def test_panel_drag_resize_minimize_restore_and_session_position(self):
        a, p = self.app, self.panel
        p.show(a, "worlds")
        start = p.rect.copy()
        origin = p.header.center
        self.click(origin)
        self.event(pygame.MOUSEMOTION, pos=(origin[0]-180, origin[1]+90), rel=(-180,90))
        self.event(pygame.MOUSEBUTTONUP, pos=(0,0), button=1)
        self.assertEqual(p.rect.topleft, (start.x-180, start.y+90))
        origin = p.grip.center
        self.click(origin)
        self.event(pygame.MOUSEMOTION, pos=(origin[0]-400, origin[1]-500), rel=(-400,-500))
        self.event(pygame.MOUSEBUTTONUP, pos=(0,0), button=1)
        self.assertEqual(p.rect.size, (400,360))
        self.control("minimize")
        self.assertTrue(p.minimized)
        stored = p.rect.copy()
        self.click(p.edge.center)
        self.assertFalse(p.minimized)
        self.assertEqual(p.rect, stored)
        self.assertEqual(p.tab, "worlds")
        self.control("close")
        self.control("observatory")
        self.assertEqual(p.rect, stored)
        self.event(pygame.VIDEORESIZE, w=700, h=500)
        self.assertEqual(a.screen.get_size(), (960,720))
        self.assertTrue(a.screen.get_rect().contains(p.rect))

    def test_all_tabs_scroll_and_controls_are_clipped_inside_panel(self):
        a,p=self.app,self.panel
        self.event(pygame.VIDEORESIZE,w=960,h=720)
        p.show(a)
        for tab in ("settings","cell","history","evolution","habitats","worlds","appearance"):
            p.tab=tab
            p.layout(a)
            a.draw()
            for rect in (*p.buttons.values(), *p.inputs.values()):
                self.assertTrue(p.rect.contains(rect), (tab,rect))
            self.event(pygame.MOUSEWHEEL,y=-50,pos=p.content.center)
            self.assertEqual(p.scrolls[tab],p.scroll_max)
            a.draw()
        for i in (index for index, preset in enumerate(PRESETS) if preset.settings.rules_version == 2):
            p.show(a,"settings")
            self.control("preset_"+str(i))
            self.assertEqual(p.values,PRESETS[i].settings.text_values())
            self.assertEqual(a.seed,42)

    def test_input_isolation_for_all_mouse_buttons_wheel_motion_and_card(self):
        a,p=self.app,self.panel
        a.camera.zoom=3
        p.show(a)
        before=(a.camera.x,a.camera.y,a.camera.zoom,a.selected_id)
        for mouse in (1,2,3):
            self.click((p.rect.x+10,p.rect.y+180),mouse)
            self.event(pygame.MOUSEMOTION,pos=p.rect.center,rel=(70,50))
            self.event(pygame.MOUSEBUTTONUP,pos=(0,0),button=mouse)
        self.event(pygame.MOUSEWHEEL,pos=p.content.center,y=-4)
        self.assertEqual(before,(a.camera.x,a.camera.y,a.camera.zoom,a.selected_id))
        self.assertIsNone(a.drag_button)
        self.event(pygame.MOUSEWHEEL,pos=(350,450),y=1)
        self.assertGreater(a.camera.zoom,before[2])
        p.opened=False
        a.selected_id=1
        a._layout()
        before=(a.camera.x,a.camera.y,a.camera.zoom)
        self.click(a.card.center,3)
        self.event(pygame.MOUSEMOTION,pos=a.card.center,rel=(25,25))
        self.event(pygame.MOUSEWHEEL,pos=a.card.center,y=3)
        self.assertEqual(before,(a.camera.x,a.camera.y,a.camera.zoom))
        self.assertEqual(a.selected_id,1)

    def test_selection_card_details_deselect_death_and_reset(self):
        a,p=self.app,self.panel
        o=min(a.world.organisms.values(),key=lambda o:(o.x-550)**2+(o.y-380)**2)
        self.click(a.position(o.x,o.y))
        self.assertEqual(a.selected_id,o.id)
        self.assertFalse(p.opened)
        a.draw()
        self.control("details")
        self.assertEqual(p.tab,"cell")
        self.control("follow")
        self.assertEqual(a.follow_id,o.id)
        o.energy=0
        a.update(1/30)
        a.draw()
        self.assertIsNone(a.selected_id)
        self.assertIsNone(a.follow_id)
        self.assertNotIn("details",a.buttons)
        self.assertIn("follow",p.disabled)
        a.selected_id=next(iter(a.world.organisms))
        self.control("deselect")
        self.assertIsNone(a.selected_id)
        a.reset()
        self.assertIsNone(a.selected_id)

    def test_restart_new_experiment_and_extinction_require_confirmation(self):
        a,p=self.app,self.panel
        a.update(.2)
        world=a.world
        self.key(pygame.K_r)
        self.assertIs(a.world,world)
        self.assertTrue(p.pending)
        a.update(.1)
        self.assertEqual(world.ticks,9)  # Confirmation does not pause playback.
        self.control("cancel")
        self.assertIs(a.world,world)
        self.key(pygame.K_r)
        self.control("confirm")
        self.assertEqual(a.world.ticks,0)
        p.show(a,"settings")
        p.values["initial_population"]="25"
        p.values["seed"]="7"
        self.control("start")
        self.assertEqual(a.seed,42)
        self.control("confirm")
        self.assertEqual(a.seed,7)
        self.assertEqual(len(a.world.organisms),25+a.settings.initial_predators)
        a.world.organisms.clear()
        p.opened=False
        a.draw()
        self.control("restart")
        self.assertFalse(a.world.organisms)
        self.control("confirm")
        self.assertEqual(len(a.world.organisms),25+a.settings.initial_predators)

    def test_draft_validation_keyboard_focus_new_seed_and_defaults(self):
        a,p=self.app,self.panel
        p.show(a,"settings")
        self.control("seed")
        self.key(pygame.K_4)
        self.event(pygame.TEXTINPUT,text="4")
        self.assertEqual(p.values["seed"],"4")
        self.assertEqual(a.sim_clock.speed,1)
        self.key(pygame.K_RETURN)
        p.values["food_per_second"]="nan"
        self.control("start")
        self.assertTrue(p.notice_error)
        self.assertIsNone(p.pending)
        self.assertEqual(a.seed,42)
        self.control("defaults")
        self.assertEqual(p.values["seed"],"42")
        rng=a.world.rng.getstate()
        with patch("genesis.observatory_ui.secrets.randbelow",return_value=0):
            self.control("new_seed")
        self.assertEqual(p.values["seed"],"43")
        self.assertEqual(a.world.rng.getstate(),rng)
        p.keyboard_focus=None
        self.key(pygame.K_TAB)
        self.assertEqual(p.keyboard_focus,"minimize")
        self.key(pygame.K_RETURN)
        self.assertTrue(p.minimized)

    def test_world_controls_validate_then_confirm_load_preserve_selection_and_cancel(self):
        a,p=self.app,self.panel
        a.update(1.017)
        a.selected_id=1
        p.show(a,"worlds")
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"world.json"
            before=document(a.world,a.sim_clock,a.history,a.selected_id)
            with patch("genesis.observatory_ui.choose_world_file",return_value=str(path)):
                self.control("save_world")
            self.assertTrue(path.exists())
            self.assertEqual(document(a.world,a.sim_clock,a.history,a.selected_id),before)
            a.update(.2)
            world=a.world
            with patch("genesis.observatory_ui.choose_world_file",return_value=str(path)):
                self.control("load_world")
            self.assertIs(a.world,world)
            self.assertIsNotNone(p.pending)
            self.control("cancel")
            self.assertIs(a.world,world)
            with patch("genesis.observatory_ui.choose_world_file",return_value=str(path)):
                self.control("load_world")
            self.control("confirm")
            self.assertTrue(a.sim_clock.paused)
            self.assertEqual(a.selected_id,1)
            self.assertIsNone(a.follow_id)
            before["clock"]["paused"]=True
            self.assertEqual(document(a.world,a.sim_clock,a.history,a.selected_id),before)
            world=a.world
            path.write_text("broken",encoding="utf-8")
            with patch("genesis.observatory_ui.choose_world_file",return_value=str(path)):
                self.control("load_world")
            self.assertIs(a.world,world)
            self.assertTrue(p.world_notice_error)
            self.assertIsNone(p.pending)
            with patch("genesis.observatory_ui.choose_world_file",return_value=""):
                self.control("load_world")
            self.assertIn("canceled",p.world_notice)
            with patch("genesis.observatory_ui.choose_world_file",side_effect=RuntimeError("unavailable")):
                self.control("save_world")
            self.assertIn("File dialog failed",p.world_notice)

    def test_csv_and_long_messages_scroll_in_worlds(self):
        a,p=self.app,self.panel
        p.show(a,"worlds")
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"export.csv"
            p.export(a,path)
            self.assertEqual(p.saved_path,path.resolve())
            self.assertIn(str(path.resolve()),p.notice)
            p.export(a,path)
            self.assertTrue(p.notice_error)
        p.world_notice="Long path: "+"some_folder/"*200
        a.draw()
        self.event(pygame.MOUSEWHEEL,y=-15,pos=p.content.center)
        self.assertGreater(p.scrolls["worlds"],0)
        a.draw()

    def test_appearance_accessibility_shortcuts_and_hidden_restore(self):
        a,p=self.app,self.panel
        p.show(a,"appearance")
        self.assertIn("follow",p.disabled)
        for name in ("effects","habitats","transparency"):
            self.control(name)
        self.assertFalse(a.visuals.enabled)
        self.assertFalse(a.show_habitats)
        self.assertTrue(a.glass.reduced)
        self.control("hide_ui")
        self.assertTrue(a.ui_hidden)
        self.key(pygame.K_4)
        self.assertEqual(a.sim_clock.speed,4)
        self.key(pygame.K_e)
        self.key(pygame.K_h)
        self.assertTrue(a.visuals.enabled and a.show_habitats)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(a.ui_hidden)
        self.assertEqual(p.tab,"appearance")
        self.key(pygame.K_o)
        self.assertFalse(p.opened)
        for key in (pygame.K_s,pygame.K_l):
            with patch("genesis.observatory_ui.choose_world_file",return_value="") as picker:
                self.key(key,pygame.KMOD_CTRL)
            self.assertTrue(picker.called)
            self.assertEqual(p.tab,"worlds")

    def test_playback_pause_interpolation_and_reset_effects(self):
        a=self.app
        a.update(.05)
        before=a.visuals.pose(a.world.organisms[1],a.alpha)
        time=a.visuals.time
        self.control("pause")
        a.update(2)
        self.assertEqual(before,a.visuals.pose(a.world.organisms[1],a.alpha))
        self.assertEqual(time,a.visuals.time)
        self.control("pause")
        for speed in (2,4,1):
            self.control(str(speed))
            self.assertEqual(a.sim_clock.speed,speed)
        self.key(pygame.K_e)
        a.reset()
        self.assertFalse(a.visuals.enabled)
        self.assertFalse(a.visuals.trails)
        self.assertEqual(a.visuals.current,a.visuals.previous)

    def test_glass_cache_bounded_and_reduced_mode_and_hints_age_when_paused(self):
        a=self.app
        a.sim_clock.paused=True
        a.update(9)
        self.assertEqual(a.world.ticks,0)
        self.assertGreater(a.ui_time,8)
        self.panel.show(a)
        a.draw()
        before=a.glass.refreshes
        a.draw()
        self.assertEqual(a.glass.refreshes,before)
        a.glass.reduced=True
        a.draw()
        self.assertGreater(a.glass.refreshes,before)
        for i in range(12):
            self.panel.rect.x-=1
            a.draw()
        self.assertLessEqual(len(a.glass.cache),8)
        self.assertLessEqual(self.panel.content_surface.get_height(),3000)

    def test_presentation_actions_preserve_exact_seeded_trajectory(self):
        a,p=self.app,self.panel
        a.start_experiment(PRESETS[5].settings)
        control=World(a.seed,a.settings.config())
        history=History(control,a.settings)
        clock=SimulationClock(control,history.on_step)
        for i in range(150):
            if i%15 == 0:
                p.show(a, ("settings","history","appearance")[i//15%3])
                a.glass.reduced=not a.glass.reduced
                a.visuals.toggle()
                p.rect.x=max(20,p.rect.x-10)
                p.scrolls[p.tab]=120
                a.draw()
            a.update(1/30)
            clock.advance(1/30)
        self.assertEqual(document(a.world,a.sim_clock,a.history),document(control,clock,history))

    def test_confirmation_blocks_world_and_defaults_to_cancel_keyboard(self):
        a,p=self.app,self.panel
        self.key(pygame.K_r)
        before=(a.camera.x,a.camera.y,a.camera.zoom,a.selected_id,a.sim_clock.speed)
        self.event(pygame.MOUSEWHEEL,pos=(300,300),y=5)
        self.click((300,300),3)
        self.event(pygame.MOUSEMOTION,pos=(350,350),rel=(50,50))
        self.key(pygame.K_4)
        self.assertEqual(before,(a.camera.x,a.camera.y,a.camera.zoom,a.selected_id,a.sim_clock.speed))
        world=a.world
        self.key(pygame.K_RETURN)
        self.assertIsNone(p.pending)
        self.assertIs(a.world,world)

    def test_repeated_resize_events_do_not_recreate_display_or_change_world(self):
        from genesis.file_dialogs import WorldFilePicker
        a=self.app
        before=document(a.world,a.sim_clock,a.history)
        picker=WorldFilePicker(True,a.seed,a.world.ticks)
        event=pygame.event.Event(pygame.VIDEORESIZE,w=a.screen.get_width(),h=a.screen.get_height())
        with patch("pygame.display.set_mode") as mode:
            a.handle_event(event)
            picker.handle_event(event)
            mode.assert_not_called()
        self.assertEqual(before,document(a.world,a.sim_clock,a.history))
