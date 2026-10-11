"""Native display controls, screenshot capture and explicitly measured throughput."""
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.persistence import document
from genesis.presets import PRESETS

out = Path("artifacts").resolve()
out.mkdir(exist_ok=True)
app = App()


def click(rect):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))


def capture(name):
    pygame.event.pump()
    app.draw()
    pygame.image.save(app.screen, str(out / (name + ".png")))


def choose(path):
    pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=str(path)))
    for _ in range(2):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))


try:
    print("Display:", pygame.display.get_driver(), flush=True)
    assert pygame.display.get_driver() != "dummy"
    panel = app.observatory
    click(panel.buttons["worlds"])
    capture("phase5-worlds-normal")
    click(panel.buttons["preset_5"])
    assert panel.values == PRESETS[5].settings.text_values()
    assert not app.settings.habitat_enabled
    capture("phase5-drafts-normal")
    click(panel.buttons["start"])
    assert app.settings.habitat_enabled and app.settings.predator_enabled
    for _ in range(900):
        pygame.event.pump()
        app.update(1 / 30)
    click(app.buttons["pause"])
    before = document(app.world, app.sim_clock, app.history)
    click(app.buttons["habitats"])
    assert not app.show_habitats
    capture("phase5-overlay-off")
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h, mod=0))
    assert app.show_habitats
    assert before == document(app.world, app.sim_clock, app.history)
    app.selected_id = next(iter(app.world.organisms))
    for size, suffix in (((1380, 900), "normal"), ((960, 720), "minimum")):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
        for tab, _ in panel.TABS:
            click(panel.buttons[tab])
            capture(f"phase5-{tab}-{suffix}")
            for rect in (*panel.buttons.values(), *panel.inputs.values()):
                assert app.sidebar.contains(rect), (tab, rect)
    click(panel.buttons["settings"])
    panel.values["map_seed"] = "-1"
    original = app.world
    click(panel.buttons["start"])
    assert app.world is original and panel.notice_error
    capture("phase5-invalid-map-seed")
    panel.values = app.settings.text_values()
    click(panel.buttons["export"])
    assert panel.saved_path.exists() and not panel.notice_error
    capture("phase5-csv")
    click(panel.buttons["worlds"])
    path = out / "phase5-world.json"
    choose(path)
    click(panel.buttons["save_world"])
    assert not panel.world_notice_error, panel.world_notice
    before = document(app.world, app.sim_clock, app.history, app.selected_id)
    app.reset()
    choose(path)
    click(panel.buttons["load_world"])
    assert not panel.world_notice_error, panel.world_notice
    assert app.sim_clock.paused
    assert document(app.world, app.sim_clock, app.history, app.selected_id) == before
    capture("phase5-loaded")
    # Invalid map must not replace the running world via desktop load controls.
    data = json.loads(path.read_text())
    data["habitats"]["movement_multipliers"][2] = 0
    bad = out / "phase5-invalid-map.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    choose(bad)
    click(panel.buttons["load_world"])
    assert panel.world_notice_error
    assert document(app.world, app.sim_clock, app.history, app.selected_id) == before
    capture("phase5-load-error")
    results = []
    for size in ((1380, 900), (960, 720)):
        for speed in (1, 4):
            app.start_experiment(PRESETS[5].settings)
            app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
            panel.tab = "history"
            app.sim_clock.speed = speed
            for _ in range(30):
                pygame.event.pump()
                app.update(1 / 60)
                app.draw()
            durations = []
            for _ in range(240):
                start = time.perf_counter()
                pygame.event.pump()
                app.update(1 / 60)
                app.draw()
                durations.append(time.perf_counter() - start)
            result = {"size": size, "speed": speed, "frames": len(durations),
                      "uncapped_fps": round(len(durations) / sum(durations), 1),
                      "median_frame_ms": round(statistics.median(durations) * 1000, 2),
                      "p95_frame_ms": round(sorted(durations)[int(.95 * len(durations))] * 1000, 2),
                      "final_population": len(app.world.organisms)}
            results.append(result)
            print(json.dumps(result), flush=True)
    (out / "habitat-performance.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Desktop controls, actual picker, map validation, CSV, immutable overlay and normal/minimum layouts passed.")
    print("240 uncapped update/draw frames per case after 30 warmup frames, initial Patchwork founders, FX on.")
finally:
    pygame.quit()
