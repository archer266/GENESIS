import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import tempfile
import unittest
import pygame
from genesis.app import App
from genesis.observatory import ExperimentSettings
from genesis.persistence import document

class DiagnosticUITests(unittest.TestCase):
    def test_tabs_scrolling_export_and_input_isolation(self):
        a=App(settings=ExperimentSettings(predator_enabled=True,initial_predators=8))
        try:
            a.update(2)
            before=document(a.world,a.sim_clock,a.history)
            for size in ((1380,900),(960,720)):
                a.handle_event(pygame.event.Event(pygame.VIDEORESIZE,w=size[0],h=size[1]))
                p=a.observatory;p.rect.width=400;p.show(a,'diagnostics');a.draw()
                for name,_ in p.OBS:self.assertTrue(p.buttons['view_'+name].colliderect(p.rect))
                a.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=p.content.center))
                self.assertIsNone(a.selected_id);self.assertIsNone(a.drag_button)
                p.pointer=p.content.center
                a.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=-5,x=0))
                p.scrolls['diagnostics']=600;a.draw()
                p.keyboard_focus='view_history'
                a.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0))
                self.assertEqual(p.tab,'history')
                p.show(a,'worlds');p.ensure_visible(a,'export_diagnostics')
                self.assertIn('export_diagnostics',p.buttons)
                with tempfile.TemporaryDirectory() as folder:
                    p.export_diagnostics(a,Path(folder)/'d.csv')
                    self.assertFalse(p.notice_error);self.assertTrue(p.saved_path.exists())
            self.assertEqual(before,document(a.world,a.sim_clock,a.history))
        finally:pygame.quit()
