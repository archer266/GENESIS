"""Native display validation and optional isolated glass-rendering measurements."""
import argparse
import json
from pathlib import Path
import statistics
import platform
import winreg
import sys
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from pygame._sdl2 import Window
from genesis.app import App
from genesis.presets import PRESETS
from genesis.persistence import document
from genesis.file_dialogs import WorldFilePicker


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--benchmark",action="store_true")
    args=parser.parse_args()
    out=Path("artifacts")
    out.mkdir(exist_ok=True)
    app=App(settings=PRESETS[5].settings)
    assert pygame.display.get_driver() == "windows", "Run with native Windows SDL"
    panel=app.observatory
    checks=[]

    def event(kind,**values):
        app.handle_event(pygame.event.Event(kind,**values))
    def key(key):
        event(pygame.KEYDOWN,key=key,mod=0)
    def click(point):
        event(pygame.MOUSEBUTTONDOWN,button=1,pos=point)
    def control(name):
        app._layout()
        if name in panel.content_buttons or name in panel.content_inputs:
            panel.ensure_visible(app,name)
        click({**app.buttons,**panel.buttons,**panel.inputs}[name].center)
    def capture(name):
        pygame.event.pump()
        app.draw()
        pygame.image.save(app.screen,out/("glass-"+name+".png"))

    try:
        for _ in range(600):
            pygame.event.pump()
            app.update(1/30)
        app.sim_clock.paused=True
        initial=document(app.world,app.sim_clock,app.history)
        for size,name in (((1380,900),"normal"),((960,720),"minimum")):
            event(pygame.VIDEORESIZE,w=size[0],h=size[1])
            panel.opened=False
            app.selected_id=None
            app.notice_remaining=0
            app._layout()
            capture("closed-"+name)
            viewport=app.viewport.copy()
            control("observatory")
            assert app.viewport == viewport
            for tab in ("settings","history","cell","evolution","habitats","worlds","appearance"):
                panel.tab=tab
                panel.scrolls[tab]=0
                capture(tab+"-"+name)
                event(pygame.MOUSEWHEEL,y=-100,pos=panel.content.center)
                capture(tab+"-scrolled-"+name)
                assert panel.scrolls[tab] == panel.scroll_max
            panel.tab="settings"
            panel.scrolls["settings"]=620
            capture("presets-"+name)
            origin=panel.header.center
            click(origin)
            event(pygame.MOUSEMOTION,pos=(origin[0]-120,origin[1]+40),rel=(-120,40))
            event(pygame.MOUSEBUTTONUP,button=1,pos=(0,0))
            origin=panel.grip.center
            click(origin)
            event(pygame.MOUSEMOTION,pos=(origin[0]-60,origin[1]-80),rel=(-60,-80))
            event(pygame.MOUSEBUTTONUP,button=1,pos=(0,0))
            assert app.screen.get_rect().contains(panel.rect)
            capture("resized-"+name)
            control("minimize")
            capture("minimized-"+name)
            click(panel.edge.center)
            assert not panel.minimized
            control("close")
            target=min(app.world.organisms.values(),key=lambda o:(o.x-550)**2+(o.y-380)**2)
            pose=app.visuals.pose(target,app.alpha)
            click(app.position(pose.x,pose.y))
            assert app.selected_id == target.id and not panel.opened
            capture("card-"+name)
            control("details")
            assert panel.tab == "cell"
            control("follow")
            assert app.follow_id == target.id
            capture("details-"+name)
            app.follow_id=None
            assert document(app.world,app.sim_clock,app.history) == initial
            checks.append(f"{size}: closed/open, seven content views, full scrolling, presets, drag/resize, minimize/restore, card/details/follow; unchanged world")

        panel.show(app,"appearance")
        control("transparency")
        capture("reduce-transparency")
        assert app.glass.reduced
        control("effects")
        assert not app.visuals.enabled
        control("habitats")
        assert not app.show_habitats
        control("fit")
        saved_size=app.screen.get_size()
        saved_position=Window.from_display_module().position
        control("fullscreen")
        assert app.fullscreen and Window.from_display_module().position == (0,0)
        control("hide_ui")
        capture("hidden-fullscreen")
        assert app.ui_hidden
        key(pygame.K_ESCAPE)
        assert not app.ui_hidden
        key(pygame.K_F11)
        assert not app.fullscreen and app.screen.get_size() == saved_size
        assert Window.from_display_module().position == saved_position
        checks.append("Appearance toggles, Fit, primary-display fullscreen and size/position restoration, hidden UI restore")

        panel.show(app,"worlds")
        import uuid
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT,text=str((out/("glass-history-"+uuid.uuid4().hex[:8]+".csv")).resolve())))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0))
        control("export")
        assert panel.saved_path.is_file()
        path=(out/"glass-world.json").resolve()
        # Post text/Enter into the actual existing Pygame picker; twice confirms overwrite.
        original_picker_run=WorldFilePicker.run
        def picker_run(picker):
            pygame.event.clear()  # Synthetic mode switches leave queued native resize events.
            pygame.time.set_timer(pygame.event.Event(pygame.TEXTINPUT,text=str(path)), 100, loops=1)
            pygame.time.set_timer(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,mod=0,unicode="\r"), 220, loops=2)
            pygame.time.set_timer(pygame.QUIT, 4000, loops=1)
            try:
                result=original_picker_run(picker)
                print("Picker:",picker.status,"->",result,flush=True)
                return result
            finally:
                for kind in (pygame.TEXTINPUT,pygame.KEYDOWN,pygame.QUIT):
                    pygame.time.set_timer(kind,0)
                    pygame.event.clear(kind)
        with patch.object(WorldFilePicker,"run",picker_run):
            control("save_world")
        assert path.exists() and not panel.world_notice_error, panel.world_notice
        with patch.object(WorldFilePicker,"run",picker_run):
            control("load_world")
        assert panel.pending
        capture("load-confirmation")
        control("cancel")
        assert document(app.world,app.sim_clock,app.history) == initial
        with patch.object(WorldFilePicker,"run",picker_run):
            control("load_world")
        control("confirm")
        assert app.sim_clock.paused and not app.follow_id
        capture("loaded")
        key(pygame.K_r)
        assert panel.pending
        capture("restart-confirmation")
        control("cancel")
        panel.show(app,"settings")
        control("preset_5")
        control("new_seed")
        control("start")
        assert panel.pending
        capture("new-confirmation")
        control("cancel")
        panel.values["map_seed"]="-1"
        control("start")
        assert panel.notice_error and not panel.pending
        capture("invalid-draft")
        checks.append("CSV, actual native Pygame picker save/load, validated load confirmation/cancel/accept, restart and new experiment confirmation, invalid drafts")
        (out/"glass-desktop-checks.json").write_text(json.dumps({"driver":pygame.display.get_driver(),"checks":checks},indent=2))
        print("PASS",*checks,sep="\n",flush=True)
        if args.benchmark:
            benchmark(app,out)
    finally:
        pygame.quit()


def benchmark(app,out):
    # Initial Patchwork population, frozen simulation: this measures rendering only.
    app.start_experiment(PRESETS[5].settings)
    for _ in range(30):
        app.update(1/30)
    app.sim_clock.paused=True
    app.selected_id=None
    app.show_habitats=True
    if not app.visuals.enabled:
        app.visuals.toggle()
        # Rebuild actual trails from simulation events before taking the snapshot.
        app.sim_clock.paused=False
        for _ in range(10): app.update(1/30)
        app.sim_clock.paused=True
    snapshot=document(app.world,app.sim_clock,app.history)
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
        cpu=winreg.QueryValueEx(key,"ProcessorNameString")[0]
    result={"cpu":cpu,"os":platform.platform(),"driver":pygame.display.get_driver(),"python":sys.version,"pygame":pygame.version.ver,
            "sdl":pygame.get_sdl_version(),"population":len(app.world.organisms),"food":len(app.world.food),
            "method":"Native software rendering + flip, frozen seeded Patchwork snapshot. 30 warmups, 240 uncapped frames per case. UI time advances 1/60s per frame to exercise 10Hz local frost refresh. Glass time sums only Glass.draw; total includes world/UI/flip. No simulation timing or FPS claim.","cases":[]}
    def summary(samples):
        return {"median_ms":round(statistics.median(samples)*1000,3),
                "p95_ms":round(sorted(samples)[int((len(samples)-1)*.95)]*1000,3)}
    original=app.glass.draw
    glass_time=[0.0]
    def timed(*args,**kwargs):
        t=time.perf_counter()
        original(*args,**kwargs)
        glass_time[0]+=time.perf_counter()-t
    app.glass.draw=timed
    for size in ((1380,900),(960,720)):
        app.screen=pygame.display.set_mode(size,pygame.RESIZABLE)
        for opened in (False,True):
            for reduced in (False,True):
                panel=app.observatory
                panel.rect=pygame.Rect(size[0]-484,24,460,min(620,size[1]-130))
                panel.opened,panel.minimized,panel.tab=opened,False,"history"
                panel.scrolls["history"]=0
                app.glass.reduced=reduced
                for _ in range(30):
                    app.ui_time+=1/60
                    app.draw()
                timings,glass=[],[]
                refreshes=app.glass.refreshes
                start=time.perf_counter()
                for _ in range(240):
                    pygame.event.pump()
                    app.ui_time+=1/60
                    glass_time[0]=0
                    t=time.perf_counter()
                    app.draw()
                    timings.append(time.perf_counter()-t)
                    glass.append(glass_time[0])
                case={"resolution":size,"panel_open":opened,"reduce_transparency":reduced,
                      "frames":240,"wall_seconds":round(time.perf_counter()-start,3),
                      "glass":summary(glass),"total_render":summary(timings),
                      "surface_refreshes":app.glass.refreshes-refreshes}
                result["cases"].append(case)
                print(case,flush=True)
    app.glass.draw=original
    assert document(app.world,app.sim_clock,app.history) == snapshot
    (out/"glass-performance.json").write_text(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
