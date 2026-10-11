"""Opt-in, deterministic desktop QA entry point, also usable inside the bundle.

No network or source imports. All artifacts go to an explicitly chosen folder.
This exercises native SDL through programmatic events, not manual interaction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import winreg

import pygame
from .app import App
from .file_dialogs import WorldFilePicker
from .persistence import document, load_world
from .user_files import Preferences, writable_destination


def fingerprint(app):
    data=document(app.world, app.sim_clock, app.history)
    data['clock']['paused']=True
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def smoke(app, output, fixtures, relaunch):
    checks=[]
    p=app.observatory
    if relaunch:
        assert app.glass.reduced and not app.visuals.enabled
        assert p.tab=='worlds' and p.rect.width==430
        assert app.screen.get_size()==(960,720) and app.guide_until==0
        assert app.preferences.values['save_directory']==str(output/'Files Ω')
        assert app.preferences.values['export_directory']==str(output/'Files Ω')
        app.draw()
        pygame.image.save(app.screen,str(output/'relaunch.png'))
        return ['Preferences restored across separate process launches']
    assert app.guide_until==12 and not p.opened
    app.draw(); pygame.image.save(app.screen,str(output/'first-launch.png'))
    app.activate_control('dismiss_guide'); assert app.guide_until==0
    before=fingerprint(app)
    def click(point):
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
    def key(code):
        app.handle_event(pygame.event.Event(pygame.KEYDOWN,key=code,mod=0))
    for size,name in (((1380,900),'normal'),((960,720),'minimum')):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE,w=size[0],h=size[1]))
        p.opened=False;app._layout()
        app.draw();pygame.image.save(app.screen,str(output/f'closed-{name}.png'))
        click(app.buttons['pause'].center); assert app.sim_clock.paused
        click(app.buttons['4'].center); assert app.sim_clock.speed==4
        click(app.buttons['1'].center)
        click(app.buttons['pause'].center); assert not app.sim_clock.paused
        click(app.buttons['observatory'].center);assert p.opened
        for tab in ('settings','history','evolution','habitats','environment','diagnostics','worlds','appearance'):
            p.show(app,tab);app.draw()
        pygame.image.save(app.screen,str(output/f'appearance-{name}.png'))
        p.ensure_visible(app,'guide');click(p.buttons['guide'].center)
        assert not p.opened and app.guide_until>app.ui_time
        app._layout(); click(app.buttons['dismiss_guide'].center)
        assert app.guide_until==0
        checks.append(f'Playback, all tabs, guide reopen/dismiss at {size}')
    app.toggle_fullscreen();assert app.fullscreen
    app.draw();pygame.image.save(app.screen,str(output/'fullscreen.png'))
    app.toggle_fullscreen();assert not app.fullscreen and app.screen.get_size()==(960,720)
    app.toggle_ui();assert app.ui_hidden
    key(pygame.K_ESCAPE);assert not app.ui_hidden
    assert fingerprint(app)==before
    checks.append('Fullscreen/window restoration, Hide UI restoration; model and RNG unchanged')
    folder=output/'Files Ω';folder.mkdir(exist_ok=True)
    # Real modal picker receives SDL text/Enter input; no mocked return values.
    def picker_input(name):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT,text=str(folder/name)))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0))
    p.show(app,'worlds')
    picker_input('checkpoint 日本語.json');p.file_action(app,True)
    assert not p.world_notice_error and (folder/'checkpoint 日本語.json').is_file()
    saved=fingerprint(app)
    app.update(1)
    picker_input('checkpoint 日本語.json');p.file_action(app,False)
    assert p.pending
    p.activate(app,'confirm');assert app.sim_clock.paused and fingerprint(app)==saved
    for kind in ('history','lineage','diagnostics'):
        picker_input(kind+' 日本語.csv');p.export_action(app,kind)
        assert not p.notice_error and (folder/(kind+' 日本語.csv')).is_file()
    checks.append('Native modal save/load, replacement confirmation, three CSV destination pickers; Unicode paths')
    invalid=folder/'invalid.json';invalid.write_text('{')
    before=fingerprint(app);assert not app.load_file(invalid) and fingerprint(app)==before
    p.export(app,folder/'history 日本語.csv');assert p.notice_error
    if getattr(sys,'frozen',False):
        assert not app.save_file(Path(sys.executable).parent/'forbidden.json')
        assert not (Path(sys.executable).parent/'forbidden.json').exists()
    checks.append('Readable invalid-load/existing-export errors; current world retained; frozen app-folder writes rejected')
    for fixture in sorted(fixtures.glob('phase*_world_v*.json')):
        assert app.load_file(fixture)
        app.sim_clock.paused=False
        app.update(2)
        checkpoint=folder/(fixture.stem+'-resumed.json')
        assert app.save_file(checkpoint)
        app.update(3)
        expected=fingerprint(app)
        assert app.load_file(checkpoint)
        app.sim_clock.paused=False;app.update(3)
        assert fingerprint(app)==expected
        checks.append(f'{fixture.name}: migration and exact continuation after v6 re-save')
    app.glass.reduced=True;app.visuals.enabled=False
    p.show(app,'worlds');p.rect.width=430;app._layout()
    app.save_preferences()
    return checks


def benchmark(app, fixture):
    cases=[]
    def summary(items):
        v=sorted(items)
        return dict(median_ms=round(v[len(v)//2]*1000,3),p95_ms=round(v[int((len(v)-1)*.95)]*1000,3))
    for speed in (1,4):
        app.apply_loaded(load_world(fixture),fixture)
        app.sim_clock.paused=False
        for _ in range(10):app.update(1/30)
        app.sim_clock.speed=speed
        app.ui_time=20;app.guide_until=0;app.notice_remaining=0
        app.visuals.enabled=True;app.show_habitats=True;app.glass.reduced=False
        app.screen=pygame.display.set_mode((1380,900),pygame.RESIZABLE)
        app.observatory.rect=pygame.Rect(896,24,460,620)
        app.observatory.show(app,'history')
        for _ in range(30):pygame.event.pump();app.draw()
        tick=app.world.ticks;population=len(app.world.organisms)
        core=[0.];step=app.world.step
        def timed_step():
            start=time.perf_counter();step();core[0]+=time.perf_counter()-start
        app.world.step=timed_step
        samples={key:[] for key in ('simulation','update','render','total')}
        populations=[];start=time.perf_counter()
        for _ in range(360):
            pygame.event.pump();core[0]=0
            t=time.perf_counter();app.update(1/60);update=time.perf_counter()-t
            t=time.perf_counter();app.draw();render=time.perf_counter()-t
            for key,value in zip(samples,(core[0],update,render,update+render)):samples[key].append(value)
            populations.append(len(app.world.organisms))
        wall=time.perf_counter()-start
        del app.world.step
        assert app.world.ticks-tick==180*speed
        cases.append(dict(speed=speed,frames=360,resolution=[1380,900],population_start=population,
                          population_range=[min(populations),max(populations)],wall_seconds=round(wall,3),
                          ticks=app.world.ticks-tick,state_sha256=fingerprint(app),
                          **{k:summary(v) for k,v in samples.items()}))
    return cases


def main(arguments):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--fixtures',required=True)
    parser.add_argument('--mode',choices=('smoke','relaunch','benchmark'),default='smoke')
    args=parser.parse_args(arguments)
    output=writable_destination(args.output);output.mkdir(parents=True,exist_ok=True)
    fixtures=Path(args.fixtures).resolve()
    app=App(preferences=Preferences())
    assert pygame.display.get_driver()=='windows', 'Native Windows SDL is required for desktop release checks'
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
        cpu=winreg.QueryValueEx(key,'ProcessorNameString')[0]
    result=dict(mode=args.mode,frozen=bool(getattr(sys,'frozen',False)),executable=sys.executable,
                pygame_path=pygame.__file__,cwd=str(Path.cwd()),cpu=cpu,os=platform.platform(),
                python=platform.python_version(),pygame=pygame.version.ver,sdl=pygame.get_sdl_version(),
                display_driver=pygame.display.get_driver())
    try:
        if args.mode=='benchmark':
            result['method']='30 frozen warmup draws + 360 active frames per speed, fixed 1/60 input, FX/habitats on, History panel open, flip included, event pump excluded; no dropped steps. Short benchmark, not sustained FPS.'
            result['cases']=benchmark(app,fixtures/'environment-cap.json')
        else:
            result['checks']=smoke(app,output,fixtures,args.mode=='relaunch')
        result['passed']=True
    except Exception as error:
        result['passed']=False;result['error']=repr(error)
        raise
    finally:
        app.save_preferences();pygame.quit()
        (output/(args.mode+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
