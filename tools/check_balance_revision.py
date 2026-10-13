"""Long fixed-step trials; observational sampling never consumes world RNG."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import statistics
import shutil
import hashlib
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from genesis.observatory import ExperimentSettings, History
from genesis.presets import PRESETS
from genesis.simulation import World, Traits


def distribution(values, low, high):
    if not values:return None
    a=sorted(values)
    def q(p):
        x=(len(a)-1)*p; i=int(x)
        return a[i]+(a[min(len(a)-1,i+1)]-a[i])*(x-i)
    bins=[0]*10
    for x in a:bins[min(9,int((x-low)/(high-low)*10))]+=1
    return dict(mean=statistics.mean(a),sd=statistics.pstdev(a),minimum=a[0],maximum=a[-1],
                q10=q(.1),q25=q(.25),median=q(.5),q75=q(.75),q90=q(.9),iqr=q(.75)-q(.25),bins=bins,
                lower_bound_fraction=sum(x<=low+.01*(high-low) for x in a)/len(a),
                upper_bound_fraction=sum(x>=high-.01*(high-low) for x in a)/len(a))


def trial(job):
    label, settings, seconds, folder=job
    world=World(settings.seed,settings.config())
    history=History(world,settings)
    started=time.perf_counter();cap=0;pred_cap=0
    counts={s:sum(o.species==s for o in world.organisms.values()) for s in ('prey','predator')}
    extinction={s:None if n else 0 for s,n in counts.items()}
    ranges={s:[n,n] for s,n in counts.items()}
    snapshots=[];eating=0;movement={s:[0.,0] for s in counts};cap_births=[0,0]
    def sample():
        row=dict(time=world.time,food=len(world.food),eating=eating,
                 food_by_particle_size=[sum((f.id-1)%3==kind for f in world.food.values()) for kind in range(3)] if world.config.rules_version==2 else None,
                 cap_steps=cap,counts=dict(counts),catches=world.catches,
                 environment_multiplier=world.environment.multiplier,
                 totals={s:dict(v) for s,v in world.diagnostics.totals.items()},traits={})
        for species in counts:
            group=[o for o in world.organisms.values() if o.species==species]
            row['traits'][species]={key:distribution([getattr(o.traits,key) for o in group],*limits) for key,limits in Traits.BOUNDS.items()}
            row[species+'_energy']=statistics.mean(o.energy for o in group) if group else None
            row[species+'_age']=statistics.mean(o.age for o in group) if group else None
            row[species+'_legacy_purple_fraction']=sum(o.traits.speed>=51 for o in group)/len(group) if group else None
            row[species+'_measured_movement']=movement[species][0]/max(1,movement[species][1])
        snapshots.append(row)
        progress=Path(folder)/f'{label}-{settings.seed}.progress.json'
        progress.write_text(json.dumps(dict(label=label,seed=settings.seed,time=world.time,counts=counts,extinction=extinction)),encoding='utf-8')
    sample()
    for _ in range(round(seconds/world.config.timestep)):
        if not world.organisms:break
        positions={o.id:(o.x,o.y) for o in world.organisms.values()} if world.ticks%30==0 else None
        world.step()
        history.on_step(world)
        for event in world.events:eating+=event.kind=='eat'
        if positions:
            for oid,(x,y) in positions.items():
                o=world.organisms.get(oid)
                if o:
                    movement[o.species][0]+=math.hypot(o.x-x,o.y-y)/world.config.timestep
                    movement[o.species][1]+=1
        pred=len(world.diagnostics.living_catches)
        counts=dict(prey=len(world.organisms)-pred,predator=pred)
        cap+=len(world.organisms)==world.config.population_cap
        pred_cap+=pred==world.config.predator_cap
        for s,n in counts.items():
            ranges[s][0]=min(ranges[s][0],n);ranges[s][1]=max(ranges[s][1],n)
            if n==0 and extinction[s] is None:extinction[s]=world.time
        if world.ticks%1800==0 or not world.organisms:sample()
    from genesis.persistence import save_world
    from genesis.simulation import SimulationClock
    checkpoints=Path(folder)/'worlds';checkpoints.mkdir(exist_ok=True)
    save_world(checkpoints/f'{label}-{settings.seed}.json',world,SimulationClock(world),history)
    return dict(label=label,settings=asdict(settings),requested_seconds=seconds,end_time=world.time,
                wall_seconds=time.perf_counter()-started,final=counts,extinction=extinction,ranges=ranges,
                cap_fraction=cap/max(1,world.ticks),predator_cap_fraction=pred_cap/max(1,world.ticks),
                snapshots=snapshots,diagnostics=world.diagnostics.document())


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=('diagnose','tune','evaluate'),required=True)
    p.add_argument('--seconds',type=int,default=3600)
    p.add_argument('--workers',type=int,default=3)
    p.add_argument('--label',default='initial')
    p.add_argument("--recipe",choices=("normal","stress","all"),default="all")
    p.add_argument('--seed-start',type=int,default=3001)
    p.add_argument('--tuning-seed',type=int,choices=(42,211,223,227))
    p.add_argument('--mutation-percent',type=float,help='Explicit recipe override for reproducing a recorded candidate')
    args=p.parse_args()
    if args.mutation_percent is not None and (args.stage=='diagnose' or not 0<=args.mutation_percent<=20):
        p.error('--mutation-percent requires tune/evaluate and a finite value from 0 to 20')
    folder=Path('artifacts/balance-revision')/f'{args.stage}-{args.label}'
    if folder.exists() and any(folder.iterdir()):
        p.error('Results folder already exists; choose a new --label to preserve recorded evidence')
    folder.mkdir(parents=True,exist_ok=True)
    for name in ('ecology.py','simulation.py','observatory.py'):
        shutil.copy2(Path('genesis')/name,folder/name)
    if args.stage=='diagnose':
        settings=[('original-default',ExperimentSettings()),('original-coexistence',PRESETS[7].settings),('original-environment',PRESETS[6].settings)]
    else:
        from genesis.ecology import recommended_settings
        seeds=((args.tuning_seed,) if args.tuning_seed is not None else (211,223,227)) if args.stage=='tune' else range(args.seed_start,args.seed_start+10)
        settings=[(f'{kind}-rules{rules}',replace(recommended_settings(stress=kind=='stress'),seed=seed,map_seed=seed,rules_version=rules))
                  for rules in ((2,) if args.stage=='tune' else (1,2)) for kind in (('normal','stress') if args.recipe=='all' else (args.recipe,)) for seed in seeds]
    if args.mutation_percent is not None:
        settings=[(label,replace(s,mutation_strength=args.mutation_percent/100)) for label,s in settings]
    jobs=[(label,s,args.seconds,str(folder)) for label,s in settings]
    manifest=dict(stage=args.stage,seconds=args.seconds,workers=args.workers,
                  recipes=[dict(label=label,settings=asdict(s)) for label,s in settings],
                  sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('genesis').glob('*.py')})
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(trial,job) for job in jobs]):
            result=future.result()
            (folder/f"{result['label']}-{result['settings']['seed']}.json").write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps({k:result[k] for k in ('label','settings','end_time','final','extinction','cap_fraction','wall_seconds')}),flush=True)


if __name__=='__main__':main()
