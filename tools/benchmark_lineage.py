"""Matched active-world UI benchmark; fixed input time, no dropped simulation ticks."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import winreg
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.persistence import load_world, document, save_world
from genesis.observatory import ExperimentSettings
from genesis.visuals import VisualState


def summary(values):
    values = sorted(values)
    return {"median_ms": round(values[len(values)//2]*1000, 3),
            "p95_ms": round(values[int((len(values)-1)*.95)]*1000, 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--environment", action="store_true", help="Measure a separate, naturally evolved environment-enabled cap fixture")
    args = parser.parse_args()
    app = App()
    assert pygame.display.get_driver() == "windows"
    fixture = Path(__file__).resolve().parents[1]/"tests/fixtures/phase6_world_v3.json"
    if args.environment:
        fixture = Path("artifacts/environment-cap.json")
        if not fixture.exists():
            app.start_experiment(ExperimentSettings(seed=2026, initial_population=260, food_per_second=80,
                predator_enabled=True, initial_predators=40, habitat_enabled=True, map_seed=2026,
                seasons_enabled=True, season_length=40, droughts_enabled=True, drought_duration=5, drought_interval=30))
            for _ in range(18000):
                pygame.event.pump()
                app.update(1/30)
                env = app.world.environment
                if app.world.ticks > 1800 and len(app.world.organisms) == 300 and 10 < env.next_transition-env.ticks < 60:
                    save_world(fixture, app.world, app.sim_clock, app.history)
                    break
            else:
                raise RuntimeError("No natural cap fixture found in 600 seconds")
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
        cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0]
    result = {"cpu": cpu, "os": platform.platform(), "python": platform.python_version(),
              "pygame": pygame.version.ver, "sdl": pygame.get_sdl_version(),
              "environment_enabled": args.environment,
              "method": "Native SDL software surfaces, flip included; 30 frozen warmup draws, 240 active frames per case at fixed 1/60s input; effects on, habitats/predators on, History panel open. Core simulation, full update, render and total measured separately. Event pumping excluded. No steps discarded. Median is upper middle sample.", "cases": []}
    for size in ((1380, 900), (960, 720)):
        for speed in (1, 4):
            loaded = load_world(fixture)
            app.apply_loaded(loaded, fixture)
            app.sim_clock.paused = False
            for _ in range(10):
                app.update(1/30)
            start_tick = app.world.ticks
            start_population = len(app.world.organisms)
            start_events = app.world.environment.total_events
            assert start_population >= 290
            app.sim_clock.speed = speed
            app.ui_time = 10
            app.notice_remaining = 0
            app.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            app._layout()
            app.observatory.show(app, "history")
            for _ in range(30):
                app.draw()
            core = [0.]
            step = app.world.step
            def timed_step():
                t = time.perf_counter()
                step()
                core[0] += time.perf_counter()-t
            app.world.step = timed_step
            samples = {k: [] for k in ("simulation", "update", "render", "total")}
            populations = []
            start = time.perf_counter()
            for _ in range(240):
                pygame.event.pump()
                core[0] = 0
                t = time.perf_counter()
                app.update(1/60)
                update = time.perf_counter()-t
                t = time.perf_counter()
                app.draw()
                render = time.perf_counter()-t
                for k, v in zip(samples, (core[0], update, render, update+render)):
                    samples[k].append(v)
                populations.append(len(app.world.organisms))
            wall = time.perf_counter()-start
            del app.world.step
            assert app.world.ticks-start_tick == 120*speed
            # Comparing physical state excludes new observational archive/schema fields.
            state = document(app.world, app.sim_clock, app.history)
            physical = {k: state[k] for k in ("world", "history", "habitats", "settings")}
            if not args.environment:
                # Same physical fingerprint as the Phase 7 baseline schema.
                for k in ("seasons_enabled", "season_length", "droughts_enabled", "drought_duration", "drought_interval"):
                    physical["settings"].pop(k, None)
                for row in [physical["history"]["baseline"]]+[s["stats"] for s in physical["history"]["samples"]]:
                    for k in ("season_multiplier", "drought_multiplier", "environment_multiplier"):
                        row.pop(k, None)
            digest = hashlib.sha256(json.dumps(physical, sort_keys=True).encode()).hexdigest()
            row = {"resolution": size, "speed": speed, "frames": 240, "wall_seconds": round(wall, 3),
                   "simulation_seconds": 4*speed, "population_start": start_population, "start_tick": start_tick,
                   "environment_events": app.world.environment.total_events-start_events,
                   "population_min": min(populations), "population_max": max(populations), "population_end": populations[-1],
                   "state_sha256": digest, **{k: summary(v) for k, v in samples.items()}}
            result["cases"].append(row)
            print(row, flush=True)
    Path(f"artifacts/lineage-performance-{args.label}.json").write_text(json.dumps(result, indent=2))
    pygame.quit()


if __name__ == "__main__":
    main()
