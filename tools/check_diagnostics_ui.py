"""Native diagnostics controls and readability captures at both supported sizes."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.observatory import ExperimentSettings
from genesis.persistence import document

def main():
    a=App(settings=ExperimentSettings(predator_enabled=True,initial_predators=8,habitat_enabled=True,seasons_enabled=True,droughts_enabled=True))
    assert pygame.display.get_driver()=='windows'
    for _ in range(900):
        pygame.event.pump();a.update(1/30)
    a.sim_clock.paused=True
    before=document(a.world,a.sim_clock,a.history)
    p=a.observatory
    for size,name in (((1380,900),'normal'),((960,720),'minimum')):
        a.handle_event(pygame.event.Event(pygame.VIDEORESIZE,w=size[0],h=size[1]))
        p.rect.width=460 if name=='normal' else 400
        p.show(a,'history');a._layout()
        a.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=p.buttons['view_diagnostics'].center,button=1))
        assert p.tab=='diagnostics'
        for offset,label in ((0,'prey'),(490,'predators'),(850,'notes')):
            p.scrolls['diagnostics']=offset;a.draw()
            pygame.image.save(a.screen,f'artifacts/diagnostics-{label}-{name}.png')
        p.show(a,'worlds');p.ensure_visible(a,'export_diagnostics');a.draw()
        pygame.image.save(a.screen,f'artifacts/diagnostics-worlds-{name}.png')
        with tempfile.TemporaryDirectory() as folder:
            p.export_diagnostics(a,Path(folder)/'d.csv');assert not p.notice_error
        assert document(a.world,a.sim_clock,a.history)==before
    from genesis.presets import PRESETS
    index=next(i for i,preset in enumerate(PRESETS) if preset.name=='Coexistence')
    p.show(a,'settings');p.ensure_visible(a,'preset_'+str(index))
    a.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=p.buttons['preset_'+str(index)].center,button=1))
    assert p.draft_settings()==PRESETS[index].settings
    assert document(a.world,a.sim_clock,a.history)==before
    p.ensure_visible(a,'start');a.draw()
    pygame.image.save(a.screen,'artifacts/coexistence-draft-minimum.png')
    p.activate(a,'start');assert p.pending is not None
    p.activate(a,'cancel');assert document(a.world,a.sim_clock,a.history)==before
    p.activate(a,'start');p.activate(a,'confirm')
    assert a.settings==PRESETS[index].settings and a.world.ticks==0
    assert a.world.diagnostics.totals['predator']['observed_initial']==4
    pygame.quit()
    print('Native diagnostics checks passed at both sizes: navigation, scrolling, CSV, unchanged world/RNG, and Coexistence draft/cancel/confirmed start.')

if __name__=='__main__':main()
