"""Evaluate predeclared per-world criteria; never changes a trial or its settings."""
import argparse
import csv
import json
from pathlib import Path


def assess(run):
    rows={r['time']:r for r in run['snapshots']}
    persistent=run['end_time']==3600 and all(v is None for v in run['extinction'].values())
    diversity=True
    for time in (1800,2700,3600):
        row=rows.get(time)
        if row is None:diversity=False;continue
        for trait,minimum in (('size',1),('speed',8),('sense',15)):
            d=row['traits']['prey'][trait]
            if not d or d['iqr']<minimum or max(d['lower_bound_fraction'],d['upper_bound_fraction'])>.30:
                diversity=False
    active=persistent
    for start,end in ((2700,3000),(3000,3300),(3300,3600)):
        a,b=rows.get(start),rows.get(end)
        if a is None or b is None:active=False;continue
        if (b['catches']-a['catches']<10 or
            b['totals']['prey']['births']-a['totals']['prey']['births']<10 or
            b['totals']['predator']['births']-a['totals']['predator']['births']<2):active=False
    return dict(persistent=persistent,active=active,diverse=diversity,cap_ok=run['cap_fraction']<.10)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path)
    args=parser.parse_args();groups={};flat=[];checkpoints=[]
    for path in sorted(args.folder.glob('*.json')):
        if '.progress.' in path.name or path.name in ('assessment.json','manifest.json'):continue
        run=json.loads(path.read_text(encoding='utf-8'))
        if 'snapshots' not in run:continue
        result=assess(run);groups.setdefault(run['label'],[]).append(result)
        row=dict(label=run['label'],seed=run['settings']['seed'],**result,
                 prey=run['final']['prey'],predators=run['final']['predator'],
                 prey_extinction=run['extinction']['prey'],predator_extinction=run['extinction']['predator'],
                 cap_fraction=run['cap_fraction'],predator_cap_fraction=run['predator_cap_fraction'])
        diagnostics=run['diagnostics']
        living=list(diagnostics['living_catches'].values())
        row['living_predator_mean_catches']=sum(living)/len(living) if living else None
        row['dead_predator_mean_catches']=(diagnostics['dead_predator_catches']/diagnostics['dead_predators']
                                         if diagnostics['dead_predators'] else None)
        exposure=diagnostics['totals']['predator']['organism_seconds']
        row['catches_per_predator_minute']=diagnostics['totals']['predator']['catches']*60/exposure if exposure else None
        final=run['snapshots'][-1]
        row['final_food']=final['food']
        row['food_eating_events']=final['eating']
        for species in ('prey','predator'):
            row[species+'_final_average_energy']=final[species+'_energy']
            row[species+'_sampled_mean_movement']=final[species+'_measured_movement']
            row[species+'_minimum'],row[species+'_maximum']=run['ranges'][species]
            for key,value in run['diagnostics']['totals'][species].items():row[species+'_'+key]=value
        flat.append(row)
        for snapshot in run['snapshots']:
            if snapshot['time'] not in (0,900,1800,2700,3600):continue
            for species in ('prey','predator'):
                cp=dict(label=run['label'],seed=run['settings']['seed'],time=snapshot['time'],species=species,
                        population=snapshot['counts'][species],food=snapshot['food'],meals=snapshot['eating'],
                        energy=snapshot[species+'_energy'],movement=snapshot[species+'_measured_movement'])
                for i,name in enumerate(('small','medium','large')):
                    kinds=snapshot.get('food_by_particle_size')
                    cp['food_'+name]=kinds[i] if kinds else None
                for trait,distribution in snapshot['traits'][species].items():
                    for key in ('mean','sd','minimum','maximum','iqr','q10','median','q90','lower_bound_fraction','upper_bound_fraction'):
                        cp[trait+'_'+key]=distribution[key] if distribution else None
                    cp[trait+'_histogram_10bins']=json.dumps(distribution['bins']) if distribution else None
                checkpoints.append(cp)
    report={label:dict(n=len(values),**{key:sum(v[key] for v in values) for key in ('persistent','active','diverse','cap_ok')})
            for label,values in groups.items()}
    normal,stress=report.get('normal-rules2',{}),report.get('stress-rules2',{})
    accepted=(normal.get('n')==10 and stress.get('n')==10 and normal['persistent']>=9 and stress['persistent']>=8
              and normal['active']==normal['persistent'] and stress['active']==stress['persistent']
              and normal['diverse']>=8 and normal['cap_ok']==10)
    output=dict(groups=report,acceptance_passed=accepted)
    (args.folder/'assessment.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    for name,rows in (('summary.csv',flat),('checkpoints.csv',checkpoints)):
        if rows:
            with (args.folder/name).open('w',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
