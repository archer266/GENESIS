"""Reproducible near-cap workload; not an ecological survival trial."""
from pathlib import Path
import sys
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from genesis.ecology import recommended_settings
from genesis.observatory import History
from genesis.simulation import World, SimulationClock
from genesis.persistence import save_world, load_world

settings=replace(recommended_settings(stress=True),seed=1931,map_seed=1931,initial_population=280,initial_predators=20)
for rules, name in ((2,'ecology-cap'),):
    recipe=replace(settings,rules_version=rules)
    world=World(recipe.seed,recipe.config());history=History(world,recipe)
    path=save_world(f'artifacts/{name}.json',world,SimulationClock(world),history)
    assert load_world(path).world.rng.getstate()==world.rng.getstate()
    print(path)
