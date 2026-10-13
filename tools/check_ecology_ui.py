"""Native scripted checks; no claim of manual pointer testing."""
from pathlib import Path
import argparse
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
parser=argparse.ArgumentParser()
parser.add_argument('--load',type=Path,help='Inspect a retained mature trial world')
parser.add_argument('--output',type=Path,default=Path('artifacts/ecology-ui'))
args=parser.parse_args()
root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
os.environ['GENESIS_USER_DATA_DIR']=str(root/'preferences')
os.environ.pop('SDL_VIDEODRIVER',None)
import pygame
from genesis.app import App
from genesis.ecology import recommended_settings
from genesis.persistence import document

app=App(settings=recommended_settings());p=app.observatory
if args.load:
    assert app.load_file(args.load), p.world_notice
    app.guide_until=0;app.notice_remaining=0
assert pygame.display.get_driver()=='windows'
before=document(app.world,app.sim_clock,app.history)
try:
    for size,label in (((1380,900),'normal'),((960,720),'minimum')):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE,w=size[0],h=size[1]))
        p.opened=False;app._layout();app.draw()
        pygame.image.save(app.screen,str(root/f'world-{label}.png'))
        p.show(app,'settings');app.draw()
        pygame.image.save(app.screen,str(root/f'experiment-{label}.png'))
        assert 'rules_version' not in p.content_buttons
        assert p.draft_settings().rules_version==2
        p.show(app,'appearance');p.scrolls['appearance']=550;app.draw()
        pygame.image.save(app.screen,str(root/f'legend-{label}.png'))
        target=next(iter(app.world.handling),None) or next(iter(app.world.organisms),None)
        app.selected_id=target
        p.show(app,'cell');p.scrolls['cell']=280;app.draw()
        pygame.image.save(app.screen,str(root/f'details-{label}.png'))
        assert document(app.world,app.sim_clock,app.history)==before
    print('Native Windows SDL: normal/minimum rendering, corrected-only setup and model/RNG isolation passed.')
finally:pygame.quit()
