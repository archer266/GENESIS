"""Native display smoke check with programmatic UI events and review screenshots."""

from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.observatory import ExperimentSettings


output = Path("artifacts")
output.mkdir(exist_ok=True)
app = App()


def click(rect):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))


def capture(name):
    app.draw()
    pygame.image.save(app.screen, str(output / f"{name}.png"))


try:
    print(f"Display backend: {pygame.display.get_driver()}", flush=True)
    for speed in (1, 2, 4):
        app.reset()
        click(app.buttons[str(speed)])
        started = time.perf_counter()
        for _ in range(180):
            pygame.event.pump()
            app.update(1 / 60)
            app.draw()
        duration = time.perf_counter() - started
        print(f"{speed}x / 1380x900 / effects + history: {180 / duration:.1f} uncapped frames/s; {app.world.ticks} ticks", flush=True)
    app.reset()
    for _ in range(90):
        app.update(1 / 60)
    app.selected_id = 1
    app.observatory.tab = "cell"
    capture("neon-inspector")
    for _ in range(1800):
        app.update(1 / 30)
    for tab in ("history", "evolution", "settings"):
        click(app.observatory.buttons[tab])
        capture(f"observatory-{tab}")
    app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=960, h=720))
    for tab in ("history", "evolution", "settings", "cell"):
        click(app.observatory.buttons[tab])
        capture(f"minimum-{tab}")
    click(app.buttons["observatory"])
    capture("minimum-collapsed")
    click(app.buttons["observatory"])
    click(app.observatory.buttons["settings"])
    panel = app.observatory
    click(panel.inputs["seed"])
    app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="2026"))
    panel.values["food_per_second"] = "nan"
    click(panel.buttons["start"])
    assert panel.notice_error
    capture("experiment-invalid")
    panel.values["food_per_second"] = "15"
    panel.values["mutation_percent"] = "9"
    click(panel.buttons["start"])
    assert app.seed == 2026 and app.world.ticks == 0
    app.update(2)
    path = output / "observatory-smoke.csv"
    if path.exists():
        path.unlink()  # Only replace this explicitly named generated artifact.
    panel.export(app, path)
    assert path.is_file() and not panel.notice_error
    capture("experiment-export")
    panel.export(app, path)
    assert panel.notice_error
    capture("experiment-export-error")
    click(app.buttons["effects"])
    capture("effects-off")
    click(app.buttons["effects"])
    # Explicit fixture: actual death steps, never fabricated animation events.
    for organism in app.world.organisms.values():
        organism.energy = 0
    app.update(1 / 30)
    click(panel.buttons["evolution"])
    capture("observatory-extinct")
    click(app.buttons["restart"])
    assert len(app.world.organisms) == 100 and app.seed == 2026
    app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=1380, h=900))
    app.start_experiment(ExperimentSettings(initial_population=300))
    app.observatory.tab = "evolution"
    click(app.buttons["4"])
    started = time.perf_counter()
    for _ in range(180):
        pygame.event.pump()
        app.update(1 / 60)
        app.draw()
    print(f"300 initial cells / 4x / evolution + effects: {180 / (time.perf_counter() - started):.1f} uncapped frames/s", flush=True)
    capture("population-cap")
    print("Display, playback, resize, tabs, drafts, validation, start/reset, CSV success/error, FX and extinction checks passed.")
finally:
    pygame.quit()
