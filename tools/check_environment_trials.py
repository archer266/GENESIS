"""Seeded, unmodified ecosystem trials; no population interventions."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.presets import PRESETS
from genesis.simulation import World, SimulationClock
from genesis.habitats import occupancy


def main():
    rows = []
    for food in (20, 2):
        for seed in (42, 7, 2026):
            settings = replace(next(p.settings for p in PRESETS if p.name == 'Changing Seasons'), seed=seed, map_seed=seed, food_per_second=food)
            w = World(seed, settings.config())
            clock = SimulationClock(w)
            extinctions = {"prey": None, "predator": None}
            minima = {"prey": 100, "predator": 8}
            started = time.perf_counter()
            for _ in range(18000):
                clock.advance(1/30)
                counts = {species: sum(o.species == species for o in w.organisms.values()) for species in minima}
                for species, count in counts.items():
                    minima[species] = min(minima[species], count)
                    if count == 0 and extinctions[species] is None:
                        extinctions[species] = round(w.time, 3)
                if not w.organisms:
                    break
            row = {"settings": asdict(settings), "simulation_seconds": w.time,
                   "wall_seconds": round(time.perf_counter()-started, 3), **counts,
                   "births": w.births, "deaths": w.deaths, "catches": w.catches,
                   "minimum_populations": minima, "extinction_seconds": extinctions,
                   "droughts": w.environment.drought_count, "events_retained": len(w.environment.history),
                   "occupancy": occupancy(w)}
            rows.append(row)
            print(json.dumps(row), flush=True)
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/environment-trials.json").write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
