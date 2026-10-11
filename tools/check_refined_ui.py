"""Native milestone-one capture, before lineage implementation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.presets import PRESETS
from genesis.persistence import document


def main():
    app = App(settings=PRESETS[5].settings)
    assert pygame.display.get_driver() == "windows"
    for _ in range(300):
        app.update(1/30)
    app.sim_clock.paused = True
    p = app.observatory
    before = document(app.world, app.sim_clock, app.history)
    for size, name in (((1380, 900), "normal"), ((960, 720), "minimum")):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
        p.opened = False
        app.draw()
        pygame.image.save(app.screen, f"artifacts/refined-closed-{name}.png")
        p.show(app, "settings")
        for enabled in (True, False):
            p.values["predator_enabled"] = p.values["habitat_enabled"] = str(int(enabled))
            p.scrolls["settings"] = 0
            app.draw()
            pygame.image.save(app.screen, f"artifacts/refined-{'expanded' if enabled else 'compact'}-{name}.png")
        p.keyboard_focus = "predator_enabled"
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0))
        assert p.values["predator_enabled"] == "1" and "initial_predators" in p.content_inputs
        assert app.sim_clock.paused
        p.ensure_visible(app, "preset_5")
        app.draw()
        pygame.image.save(app.screen, f"artifacts/refined-presets-{name}.png")
    assert document(app.world, app.sim_clock, app.history) == before
    pygame.quit()
    print("Native refinement checks passed: normal/minimum, conditional drafts, keyboard toggle, scrolling, unchanged world.")


if __name__ == "__main__":
    main()
