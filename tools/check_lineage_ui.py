"""Native scripted lineage browsing and normal/minimum screenshot checks."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.presets import PRESETS
from genesis.persistence import document, restore


def main():
    app = App(settings=PRESETS[5].settings)
    assert pygame.display.get_driver() == "windows"
    for _ in range(1800):
        pygame.event.pump()
        app.update(1/30)
    app.sim_clock.paused = True
    p = app.observatory
    target = max(app.world.organisms.values(), key=lambda o: o.generation)
    assert target.generation > 0
    def control(key):
        app._layout()
        p.ensure_visible(app, key)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=p.buttons[key].center))
    def capture(name):
        pygame.event.pump()
        app.draw()
        pygame.image.save(app.screen, f"artifacts/lineage-{name}.png")
    original = document(app.world, app.sim_clock, app.history)
    for size, name in (((1380, 900), "normal"), ((960, 720), "minimum")):
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
        p.rect.width = 460 if name == "normal" else 400
        app.selected_id = target.id
        app.activate_control("details")
        p.scrolls["cell"] = 0
        capture("details-"+name)
        control("lineage_jump")
        capture("record-"+name)
        parent = app.world.lineage.records[target.parent_id]
        control(f"relative_ancestors_{parent.id}")
        assert p.lineage_view.view_id == parent.id
        capture("parent-"+name)
        p.scrolls["cell"] = 1020
        capture("offspring-"+name)
        control(f"relative_children_{target.id}")
        control("lineage_select")
        control("lineage_follow")
        assert app.selected_id == app.follow_id == target.id
        app.follow_id = None
        dead = next(r for r in app.world.lineage.records.values() if r.death_time is not None)
        p.lineage_view.view(dead.id)
        p.scrolls["cell"] = 520
        capture("dead-"+name)
        assert "lineage_follow" in p.disabled
        p.lineage_view.view(app.world._next_organism_id+1)
        capture("unavailable-"+name)
        assert "lineage_select" in p.disabled
        p.show(app, "worlds")
        with tempfile.TemporaryDirectory() as folder:
            p.export_lineage(app, Path(folder)/"lineage.csv")
            assert not p.notice_error
            capture("export-"+name)
        p.opened = False
        capture("closed-"+name)
        assert document(app.world, app.sim_clock, app.history) == original
    legacy = dict(original, version=3)
    del legacy["lineage"]
    from copy import deepcopy
    from genesis.environment import DEFAULTS, STAT_DEFAULTS
    legacy = deepcopy(legacy)
    del legacy["environment"]
    del legacy["diagnostics"]
    for key in DEFAULTS:
        del legacy["settings"][key]
        del legacy["config"][key]
    for row in [legacy["history"]["baseline"]]+[s["stats"] for s in legacy["history"]["samples"]]:
        for key in STAT_DEFAULTS:
            del row[key]
    app.apply_loaded(restore(legacy), "legacy-v3.json")
    assert p.lineage_view.view_id is None
    app.selected_id = next(iter(app.world.organisms))
    app.activate_control("details")
    control("lineage_jump")
    capture("legacy-minimum")
    app.world.organisms[app.selected_id].energy = .001
    viewed = p.lineage_view.view_id
    app.sim_clock.paused = False
    app.update(1/30)
    assert p.lineage_view.view_id == viewed and app.selected_id is None
    capture("death-retained-minimum")
    app.reset()
    assert p.lineage_view.view_id is None
    pygame.quit()
    print("Native lineage checks passed: relative browsing, select/follow, dead/unavailable/legacy records, CSV, death/reset/load lifecycle, two sizes and unchanged simulation.")


if __name__ == "__main__":
    main()
