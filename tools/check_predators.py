"""Repeatable five-minute trials, with observed outcomes rather than targets."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.observatory import ExperimentSettings, History, statistics
from genesis.simulation import World, SimulationClock, Traits


results = []
for seed in (42, 7, 2026):
    settings = ExperimentSettings(seed=seed, predator_enabled=True, initial_predators=8)
    world = World(seed, settings.config())
    history = History(world, settings)
    clock = SimulationClock(world, history.on_step)
    extinction = {"prey": None, "predator": None}
    milestones = []
    predator_births = 0
    started = time.perf_counter()
    for tick in range(9000):
        clock.advance(1 / 30)
        for event in world.events:
            if event.kind == "birth" and world.organisms[event.organism_id].species == "predator":
                predator_births += 1
        stats = statistics(world)
        assert stats.population == 108 + world.births - world.deaths
        assert stats.population <= 300 and stats.predator_population <= 40
        assert world.catches <= world.deaths
        for organism in world.organisms.values():
            assert 0 < organism.energy <= 180
            assert 0 <= organism.age < 180
            for name, (low, high) in Traits.BOUNDS.items():
                assert low <= getattr(organism.traits, name) <= high
            assert organism.traits.size <= organism.x <= 1100 - organism.traits.size
            assert organism.traits.size <= organism.y <= 760 - organism.traits.size
        for species in extinction:
            if not getattr(stats, species + "_population") and extinction[species] is None:
                extinction[species] = world.time
        if (tick + 1) % 1800 == 0 or not world.organisms:
            milestones.append({"seconds": world.time, **asdict(stats)})
        if not world.organisms:
            break
    row = {"seed": seed, "settings": asdict(settings), "extinction_seconds": extinction,
           "predator_births": predator_births, "milestones": milestones,
           "wall_seconds": round(time.perf_counter() - started, 2)}
    results.append(row)
    print(json.dumps(row), flush=True)
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/predator-trials.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
