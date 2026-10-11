"""Seeded five-minute habitat trials; records observations, not target outcomes."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.habitats import REGIONS, occupancy
from genesis.observatory import ExperimentSettings, History, statistics
from genesis.simulation import SimulationClock, World

results = []
for seed in (42, 7, 2026):
    settings = ExperimentSettings(seed=seed, predator_enabled=True, initial_predators=8,
                                  habitat_enabled=True, map_seed=seed)
    world = World(seed, settings.config())
    history = History(world, settings)
    clock = SimulationClock(world, history.on_step)
    samples = [{"seconds": 0, **asdict(statistics(world))}]
    extinction = {"prey": None, "predator": None}
    for tick in range(9000):
        clock.advance(1 / 30)
        counts = {kind: sum(o.species == kind for o in world.organisms.values()) for kind in extinction}
        assert len(world.organisms) == 108 + world.births - world.deaths
        assert len(world.organisms) <= 300 and counts["predator"] <= 40
        assert len(world.food) <= 650
        for o in world.organisms.values():
            assert 0 < o.energy <= 180 and 0 <= o.age < 180
            assert o.traits.size <= o.x <= 1100 - o.traits.size
            assert o.traits.size <= o.y <= 760 - o.traits.size
        for kind in extinction:
            if not counts[kind] and extinction[kind] is None:
                extinction[kind] = world.time
        if (tick + 1) % 1800 == 0 or not world.organisms:
            stats = statistics(world)
            samples.append({"seconds": world.time, **asdict(stats)})
            for kind, total in (("prey", counts["prey"]), ("predator", counts["predator"]), ("food", len(world.food))):
                assert sum(getattr(stats, f"{region}_{kind}") for region in REGIONS) == total
        if not world.organisms:
            break
    result = {"settings": asdict(settings), "area_cells": {r: world.habitats.cells.count(i) for i, r in enumerate(REGIONS)},
              "extinction_seconds": extinction, "samples": samples}
    results.append(result)
    print(json.dumps({"seed": seed, "seconds": world.time, "prey": counts["prey"], "predator": counts["predator"],
                      "catches": world.catches, "occupancy": occupancy(world), "extinction": extinction}), flush=True)
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/habitat-trials.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
