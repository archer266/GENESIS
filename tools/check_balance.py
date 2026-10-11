"""Headless diagnostic trials. Processes are independent; no world interventions."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.observatory import ExperimentSettings
from genesis.simulation import World

BASE = ExperimentSettings(predator_enabled=True, initial_predators=8, habitat_enabled=True,
                          seasons_enabled=True, droughts_enabled=True)
RECIPES = {
    'phase8': BASE,
    'gentle': replace(BASE, food_per_second=40, initial_population=160, mutation_strength=.02,
                      season_length=300, drought_duration=5, drought_interval=300),
    'stable_traits': replace(BASE, food_per_second=40, initial_population=160, mutation_strength=0,
                            season_length=300, drought_duration=5, drought_interval=300),
    'rich': replace(BASE, food_per_second=60, initial_population=200, mutation_strength=.01,
                    season_length=300, drought_duration=5, drought_interval=300),
}

def run(job):
    label, settings, seconds = job
    w = World(settings.seed, settings.config())
    ranges = {s: [sum(o.species == s for o in w.organisms.values())]*2 for s in ('prey','predator')}
    extinction = {s: (0.0 if bounds[0] == 0 else None) for s,bounds in ranges.items()}
    cap_ticks = 0
    predator_cap_ticks = 0
    snapshots = []
    started = time.perf_counter()
    for i in range(round(seconds/w.config.timestep)):
        if not w.organisms: break
        w.step()
        pred = len(w.diagnostics.living_catches)
        counts = dict(prey=len(w.organisms)-pred, predator=pred)
        cap_ticks += len(w.organisms) == w.config.population_cap
        predator_cap_ticks += pred == w.config.predator_cap
        for s, n in counts.items():
            ranges[s][0] = min(ranges[s][0], n); ranges[s][1] = max(ranges[s][1], n)
            if n == 0 and extinction[s] is None: extinction[s] = w.time
        if w.ticks % 1800 == 0 or not w.organisms or (extinction['predator'] == w.time):
            snap = w.diagnostics.snapshot(w)
            snap['time'] = w.time
            for s in ranges:
                group = [o for o in w.organisms.values() if o.species == s]
                for k in ('speed','sense','size'):
                    snap[s+'_'+k] = sum(getattr(o.traits,k) for o in group)/len(group) if group else None
            snapshots.append(snap)
    return dict(label=label, settings=asdict(settings), requested_seconds=seconds, end_time=w.time,
                wall_seconds=time.perf_counter()-started, final=counts, ranges=ranges, extinction=extinction,
                cap_ticks=cap_ticks, cap_fraction=cap_ticks/max(1,w.ticks), predator_cap_ticks=predator_cap_ticks,
                environment_events=w.environment.total_events, droughts=w.environment.drought_count,
                diagnostics=w.diagnostics.document(), snapshots=snapshots)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=('reproduce','tune','evaluate','moderate','baseline','preset'),required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.stage == 'reproduce':
        old=json.loads(Path('artifacts/environment-trials.json').read_text())
        jobs=[('phase8',ExperimentSettings(**r['settings']),600) for r in old]
    elif args.stage == 'tune':
        jobs=[(label,replace(s,seed=seed,map_seed=seed),1800) for label,s in RECIPES.items() if label != 'phase8' for seed in (101,103,107)]
    elif args.stage == 'baseline':
        jobs=[(label,replace(s,seed=seed,map_seed=seed),1800) for label,s in [('phase8',BASE),('balanced',ExperimentSettings())] for seed in range(1001,1011)]
    elif args.stage == 'moderate':
        jobs=[(label,replace(BASE,seed=seed,map_seed=seed,initial_population=160,initial_predators=4,food_per_second=food,mutation_strength=mutation,season_length=300,drought_duration=5,drought_interval=300),1800) for label,food,mutation in [('moderate_zero',20,0),('moderate_low',24,.005)] for seed in (101,103,107)]
    else:
        from genesis.presets import PRESETS
        candidate=next(p.settings for p in PRESETS if p.name == 'Coexistence')
        jobs=[('coexistence',candidate,1800)] if args.stage == 'preset' else [(label,replace(s,seed=seed,map_seed=seed),1800) for label,s in [('coexistence',candidate)] for seed in range(1001,1011)]
    out=Path(f'artifacts/balance-{args.stage}.json')
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(run,job) for job in jobs]):
            r=future.result(); rows.append(r)
            out.write_text(json.dumps(rows,indent=2))
            print(json.dumps({k:r[k] for k in ('label','settings','end_time','final','extinction','cap_fraction','wall_seconds')}),flush=True)
    if args.stage == 'reproduce':
        for r in rows:
            expected=next(x for x in old if x['settings']==r['settings'])
            assert r['end_time']==expected['simulation_seconds']
            assert r['final']=={k:expected[k] for k in ('prey','predator')}
            t=r['diagnostics']['totals']
            assert sum(v['births'] for v in t.values())==expected['births']
            assert sum(v['deaths_energy']+v['deaths_age']+v['deaths_caught'] for v in t.values())==expected['deaths']
            assert t['predator']['catches']==expected['catches']
        print('All six recorded Phase 8 outcomes reproduced exactly.',flush=True)

if __name__=='__main__': main()
