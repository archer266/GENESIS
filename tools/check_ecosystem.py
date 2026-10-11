"""Repeatable long-run health/performance check, independent of the UI."""

from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.simulation import World


for seed in (42, 7, 2026):
    world = World(seed)
    started = time.perf_counter()
    peak = len(world.organisms)
    for _ in range(9000):
        world.step()
        peak = max(peak, len(world.organisms))
        assert len(world.organisms) <= world.config.population_cap
        assert len(world.food) <= world.config.food_cap
        assert len(world.organisms) == world.config.initial_population + world.births - world.deaths
        for organism in world.organisms.values():
            assert 0 < organism.energy <= world.config.energy_capacity
            assert organism.traits.size <= organism.x <= world.config.width - organism.traits.size
            assert organism.traits.size <= organism.y <= world.config.height - organism.traits.size
    elapsed = time.perf_counter() - started
    print(json.dumps({"seed": seed, "simulation_seconds": world.time,
                      "population": len(world.organisms), "peak_population": peak,
                      "births": world.births, "deaths": world.deaths,
                      "maximum_living_generation": max((o.generation for o in world.organisms.values()), default=0),
                      "average_traits": asdict(world.averages()),
                      "wall_seconds": round(elapsed, 3), "ticks_per_second": round(world.ticks / elapsed)}), flush=True)
