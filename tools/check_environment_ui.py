"""Native environment controls, event markers, paused loading and screenshots."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.presets import PRESETS
from genesis.persistence import document


def main():
    app = App(settings=replace(next(p.settings for p in PRESETS if p.name == 'Changing Seasons'), season_length=40, drought_interval=30, drought_duration=5))
    assert pygame.display.get_driver() == "windows"
    p = app.observatory
    while app.world.environment.drought_end is None:
        pygame.event.pump()
        app.update(1/30)
    app.update(.8)  # Let the next 1-second statistics sample include the drought marker.
    app.sim_clock.paused = True
    original = document(app.world, app.sim_clock, app.history)
    def control(key):
        app._layout()
        p.ensure_visible(app, key)
        box = {**app.buttons, **p.buttons, **p.inputs}[key]
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=box.center, button=1))
    def capture(name):
        pygame.event.pump()
        app.draw()
        pygame.image.save(app.screen, f"artifacts/environment-{name}.png")
    for size, name in (((1380, 900), "normal"), ((960, 720), "minimum")):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
        p.rect.width = 460 if name == "normal" else 400
        p.opened = False
        capture("chip-"+name)
        control("environment_status")
        assert p.tab == "environment" and app.selected_id is None
        p.scrolls["environment"] = 0
        capture("events-"+name)
        p.scrolls["environment"] = 370
        capture("history-"+name)
        control("view_history")
        capture("graphs-"+name)
        control("settings")
        p.ensure_visible(app, "seasons_enabled")
        p.scrolls["settings"] = p.content_buttons["seasons_enabled"].y-36
        capture("setup-"+name)
        values = dict(p.values)
        control("seasons_enabled")
        control("droughts_enabled")
        assert "season_length" not in p.content_inputs and "drought_duration" not in p.content_inputs
        capture("off-drafts-"+name)
        control("seasons_enabled")
        control("droughts_enabled")
        assert p.values == values
        control("appearance")
        control("environment_chip")
        app._layout()
        assert "environment_status" not in app.buttons
        control("environment_chip")
        control("transparency")
        control("effects")
        p.show(app, "environment")
        p.scrolls["environment"] = 0
        capture("reduced-no-fx-"+name)
        app.visuals.toggle()
        app.glass.reduced = False
        assert document(app.world, app.sim_clock, app.history) == original
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/"environment.json"
        assert app.save_file(path)
        assert app.load_file(path)
        assert app.sim_clock.paused
        assert document(app.world, app.sim_clock, app.history) == original
        app.history.export_csv(Path(folder)/"environment.csv")
    pygame.quit()
    print("Native environment checks passed: chip, Event tab/graphs, conditional drafts, effects/transparency, two sizes, unchanged RNG/world, save/load and CSV.")


if __name__ == "__main__":
    main()
