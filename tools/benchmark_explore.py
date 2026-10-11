"""Native SDL benchmark. Capacity replay and continuous playback are separate workloads."""
import argparse
import copy
import cProfile
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import sys
import time
import winreg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from genesis.app import App
from genesis.observatory import ExperimentSettings
from genesis.persistence import document, load_world, save_world
from genesis.simulation import SimulationClock
from genesis.visuals import VisualState


def summary(values):
    ordered = sorted(values)
    return {"median_ms": round(statistics.median(values) * 1000, 3),
            "p95_ms": round(ordered[int((len(ordered)-1) * .95)] * 1000, 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="final")
    parser.add_argument("--samples", type=int, default=240)
    parser.add_argument("--profile-only", action="store_true")
    args = parser.parse_args()
    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    settings = ExperimentSettings(seed=2026, initial_population=260, food_per_second=80,
                                  predator_enabled=True, initial_predators=40,
                                  habitat_enabled=True, map_seed=2026)
    app = App(settings=settings)
    assert pygame.display.get_driver() != "dummy", "Benchmark requires a native display"
    checkpoint = out / "phase6-benchmark-checkpoint.json"
    if not checkpoint.exists():
        for i in range(4237):
            pygame.event.pump()
            app.update(1/30)
        save_world(checkpoint, app.world, app.sim_clock, app.history)
    loaded = load_world(checkpoint)
    app.world, app.history, app.sim_clock = loaded.world, loaded.history, loaded.clock
    app.sim_clock.paused = False
    app.sim_clock.on_step = app.on_step
    app.visuals = VisualState(app.world)
    for _ in range(10):
        app.update(1/30)
    assert app.world.ticks == 4247 and len(app.world.organisms) == 300
    source = (app.world, app.history, app.visuals)
    app.observatory.show(app, "history")
    print("Capacity fixture:", app.world.ticks, "ticks,", len(app.world.organisms), "organisms,",
          sum(o.species == "predator" for o in app.world.organisms.values()), "predators,",
          len(app.world.food), "food", flush=True)

    def restore(fx, speed):
        app.world, app.history, app.visuals = copy.deepcopy(source, {id(source[0].habitats): source[0].habitats})
        app.visuals.enabled = fx
        app.sim_clock = SimulationClock(app.world, app.on_step)
        app.sim_clock.speed = speed

    for _ in range(30):
        app.draw()
    render_samples = []
    for _ in range(240):
        t = time.perf_counter()
        app.draw()
        render_samples.append(time.perf_counter()-t)
    (out / f"phase6-render-{args.label}.json").write_text(json.dumps(summary(render_samples), indent=2))
    profile = cProfile.Profile()
    profile.enable()
    for _ in range(100):
        app.draw()
    profile.disable()
    with (out / f"phase6-profile-{args.label}.txt").open("w") as stream:
        pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumtime").print_stats(35)
    if args.profile_only:
        pygame.quit()
        return

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
        cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0]
    result = {"environment": {"cpu": cpu, "logical_processors": os.cpu_count(),
               "os": platform.platform(), "python": platform.python_version(),
               "pygame": pygame.version.ver, "sdl": pygame.get_sdl_version(),
               "driver": pygame.display.get_driver(), "drawing": "software surfaces; flip included",
               "desktop_sizes": pygame.display.get_desktop_sizes()},
              "settings": asdict(settings), "fixture_tick": 4247, "fixture_population": 300,
              "fixture_predators": 36, "fixture_food": 420, "samples_per_case": args.samples,
              "method": "Capacity replay: deepcopy outside timing before each 1/30s input; 1 or 4 complete ticks. Render frozen cap snapshot with real trails/events. Continuous: fixed 1/60s input, all steps executed. 30 draw warmups. Times exclude event pumping and fixture copies. No FPS inference from replay.",
              "capacity": [], "continuous": []}
    hashes = {}
    for size in ((1380, 900), (960, 720)):
        app.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        app._layout()
        for speed in (1, 4):
            for fx in (True, False):
                restore(fx, speed)
                for _ in range(30):
                    app.draw()
                sims, renders = [], []
                started = time.perf_counter()
                for _ in range(args.samples):
                    pygame.event.pump()
                    clone = copy.deepcopy(source[0], {id(source[0].habitats): source[0].habitats})
                    clock = SimulationClock(clone)
                    clock.speed = speed
                    t = time.perf_counter()
                    steps = clock.advance(1/30)
                    sims.append(time.perf_counter()-t)
                    assert steps == speed
                    t = time.perf_counter()
                    app.draw()
                    renders.append(time.perf_counter()-t)
                case = {"resolution": size, "speed": speed, "effects": fx,
                        "wall_duration_s": round(time.perf_counter()-started, 3),
                        "core_simulation": summary(sims), "render": summary(renders),
                        "complete_steps_per_sample": speed, "render_population": 300}
                result["capacity"].append(case)
                print("capacity", case, flush=True)

                restore(fx, speed)
                original_step = app.world.step
                core = [0.0]
                def timed_step():
                    t = time.perf_counter()
                    original_step()
                    core[0] += time.perf_counter()-t
                app.world.step = timed_step
                sims, updates, renders, frames, populations = [], [], [], [], []
                started = time.perf_counter()
                for _ in range(args.samples):
                    pygame.event.pump()
                    core[0] = 0
                    t = time.perf_counter()
                    app.update(1/60)
                    u = time.perf_counter()-t
                    t = time.perf_counter()
                    app.draw()
                    r = time.perf_counter()-t
                    sims.append(core[0]); updates.append(u); renders.append(r); frames.append(u+r)
                    populations.append(len(app.world.organisms))
                del app.world.step
                steps = app.world.ticks - 4247
                assert steps == args.samples * speed // 2
                data = document(app.world, app.sim_clock, app.history)
                data["clock"]["speed"] = 1
                digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                if speed in hashes:
                    assert hashes[speed] == digest, "Rendering/resolution changed simulation"
                hashes[speed] = digest
                case = {"resolution": size, "speed": speed, "effects": fx,
                        "wall_duration_s": round(time.perf_counter()-started, 3),
                        "simulation_duration_s": steps/30, "complete_steps": steps,
                        "population_min": min(populations), "population_max": max(populations),
                        "population_end": populations[-1], "core_simulation": summary(sims),
                        "update_including_observers": summary(updates), "render": summary(renders),
                        "total_frame": summary(frames), "final_state_sha256": digest}
                result["continuous"].append(case)
                print("continuous", case, flush=True)
    (out / f"phase6-performance-{args.label}.json").write_text(json.dumps(result, indent=2))
    pygame.quit()


if __name__ == "__main__":
    main()
