"""Phase 3 native display checks with programmatic file-picker input events."""

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.persistence import document
from genesis.file_dialogs import WorldFilePicker


output = Path("artifacts").resolve()
output.mkdir(exist_ok=True)
app = App()


def click(rect):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))


def capture(name):
    app.draw()
    pygame.image.save(app.screen, str(output / f"{name}.png"))


def choose_path(path):
    pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=str(path)))
    # A second Enter confirms replacement if the destination already exists.
    for _ in range(2):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))


try:
    print(f"Native display: {pygame.display.get_driver()}", flush=True)
    for _ in range(361):
        pygame.event.pump()
        app.update(1 / 30)
    app.selected_id = next(iter(app.world.organisms))
    panel = app.observatory
    click(panel.buttons["worlds"])
    capture("phase3-worlds")
    path = output / "phase3-world.json"
    saved = document(app.world, app.sim_clock, app.history, app.selected_id)
    original_draw = WorldFilePicker.draw
    def capture_picker(picker):
        original_draw(picker)
        pygame.image.save(picker.screen, str(output / "phase3-file-picker.png"))
    choose_path(path)
    with patch.object(WorldFilePicker, "draw", capture_picker):
        click(panel.buttons["save_world"])
    assert path.exists() and not panel.world_notice_error, panel.world_notice
    capture("phase3-saved")
    for _ in range(30):
        app.update(1 / 30)
    choose_path(path)
    click(panel.buttons["load_world"])
    assert app.sim_clock.paused and not panel.world_notice_error
    saved["clock"]["paused"] = True
    assert document(app.world, app.sim_clock, app.history, app.selected_id) == saved
    capture("phase3-loaded")
    app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=960, h=720))
    capture("phase3-minimum-worlds")
    click(panel.buttons["preset_2"])
    assert panel.values["food_per_second"] == "6" and app.settings.food_per_second == 20
    capture("phase3-preset-draft")
    click(panel.buttons["new_seed"])
    assert int(panel.values["seed"]) != app.seed
    click(panel.buttons["start"])
    assert app.settings.food_per_second == 6
    capture("phase3-scarcity")
    click(panel.buttons["worlds"])
    invalid = output / "phase3-invalid.json"
    invalid.write_text('{"format":"genesis-world","version":999}', encoding="utf-8")
    before = document(app.world, app.sim_clock, app.history)
    choose_path(invalid)
    click(panel.buttons["load_world"])
    assert panel.world_notice_error and "Unsupported" in panel.world_notice
    assert document(app.world, app.sim_clock, app.history) == before
    capture("phase3-load-error")
    choose_path(path)
    with patch("genesis.persistence.os.replace", side_effect=OSError("Simulated write denied")):
        click(panel.buttons["save_world"])
    assert panel.world_notice_error
    capture("phase3-save-error")
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
    click(panel.buttons["load_world"])
    assert "canceled" in panel.world_notice
    print("Save/load controls, paused exact restoration, selection, drafts, new seed, invalid load, failed save and cancel passed.")
    print("Screenshots captured at 1380x900 and 960x720. Real Pygame file picker driven by input events; no manual interaction asserted.")
finally:
    pygame.quit()
