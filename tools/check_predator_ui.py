"""Real SDL display check using programmatic Pygame input and screenshots."""
from pathlib import Path
import sys
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
    print("Display driver:", pygame.display.get_driver(), flush=True)
    assert pygame.display.get_driver() != "dummy", "This script requires a real display"
    panel = app.observatory
    click(panel.buttons["worlds"])
    capture("phase4-worlds-normal")
    click(panel.buttons["preset_4"])
    assert panel.values == PRESETS[4].settings.text_values()
    capture("phase4-setup-normal")
    click(panel.buttons["start"])
    assert app.settings.predator_enabled and app.settings.initial_predators == 8
    for speed in (1, 2, 4):
        click(app.buttons[str(speed)])
        before = app.world.ticks
        app.update(1 / 30)
        assert app.world.ticks - before == speed
    for _ in range(300):
        pygame.event.pump()
        app.update(1 / 30)
    click(app.buttons["pause"])
    before = app.world.ticks
    app.update(1)
    assert app.world.ticks == before
    click(panel.buttons["history"])
    capture("phase4-history-normal")
    predator = next(o for o in app.world.organisms.values() if o.species == "predator")
    pose = app.visuals.pose(predator, app.alpha)
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.position(pose.x, pose.y)))
    assert app.selected_id == predator.id
    capture("phase4-inspector-normal")
    click(app.buttons["effects"])
    assert not app.visuals.enabled
    click(app.buttons["effects"])
    click(panel.buttons["worlds"])
    checkpoint = document(app.world, app.sim_clock, app.history, app.selected_id)
    path = out / "phase4-world.json"
    choose(path)
    click(panel.buttons["save_world"])
    assert not panel.world_notice_error, panel.world_notice
    app.reset()
    choose(path)
    click(panel.buttons["load_world"])
    assert not panel.world_notice_error, panel.world_notice
    assert app.sim_clock.paused
    assert document(app.world, app.sim_clock, app.history, app.selected_id) == checkpoint
    capture("phase4-loaded-normal")
    for size, suffix in (((1380, 900), "normal"), ((960, 720), "minimum")):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
        for tab, _ in panel.TABS:
            click(panel.buttons[tab])
            app.draw()
            for rect in (*panel.buttons.values(), *panel.inputs.values()):
                assert app.sidebar.contains(rect), (tab, rect)
            capture(f"phase4-{tab}-{suffix}")
            if tab == "evolution":
                click(panel.buttons["species"])
                assert panel.species == "predator"
                capture(f"phase4-predator-distributions-{suffix}")
                click(panel.buttons["species"])
    click(panel.buttons["settings"])
    panel.values["initial_predators"] = "41"
    before = app.world
    click(panel.buttons["start"])
    assert app.world is before and panel.notice_error
    capture("phase4-validation-minimum")
    panel.values = app.settings.text_values()
    # Export current observed history through the control.
    click(panel.buttons["export"])
    assert panel.saved_path.exists() and not panel.notice_error
    capture("phase4-csv-minimum")
    print("Preset, setup validation, all tabs, species switch, inspector, FX, pause, 1/2/4 speeds, CSV,")
    print("actual file-picker save/load and exact paused restoration passed at normal/minimum sizes.")
    print("Programmatic input checks; screenshots saved for separate visual review.")
finally:
    pygame.quit()
