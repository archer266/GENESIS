"""Build a findings report from completed, recorded trials and benchmarks."""
import json
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'artifacts'/name).read_text())
def load(stage):return read('balance-'+stage+'.json')
def alive(r):return all(r['final'][s]>0 for s in ('prey','predator'))
def interval(values):return f'{min(values):.2f}-{max(values):.2f}'

def main():
    reproduction=load('reproduce'); tuning=load('tune')+load('moderate'); evaluation=load('baseline')+load('evaluate')
    assert len(reproduction)==6 and len(tuning)==15 and len(evaluation)==30
    candidate=[r for r in evaluation if r['label']=='coexistence']
    assert len(candidate)==10 and {r['settings']['seed'] for r in candidate}==set(range(1001,1011))
    default=load('preset')[0]
    failed_reference=load('reference42')[0]
    before=read('lineage-performance-phase9-before.json');after=read('lineage-performance-phase9-after.json')
    text=f'''# Phase 9: Ecosystem balance and diagnostics

Coexistence retained both species at 30 simulated minutes in **{sum(map(alive,candidate))}/10 held-out runs**, compared with **0/10** for the unchanged Changing Seasons recipe. **Coexistence remains unreliable across seeds.** This is finite-horizon coexistence, not proof of a stable equilibrium or permanent survival. The original Balanced default remains prey-only and unchanged.

## Investigation before balance selection

The six recorded Phase 8 trials were rerun at their original seeds (42, 7, 2026), settings and 600-second horizon, or full extinction. End times, populations, total births, deaths and catches matched exactly. Every predator death was energy depletion; none reached maximum age. Seed 42 at food 20 exhausted its prey at 220.767 seconds and predators at 243.767 seconds. At food 2, sparse feeding and low prey energy were consistent with the early predator losses. At food 20, surviving prey became faster while predators approached the speed ceiling; this raises pursuit difficulty and metabolic expense. These observations do not isolate the effect of each trait or setting.

Code review and focused regression checks found no demonstrated defect in hunting/fleeing, start-of-tick perception, physical contact ordering, one-time catches, offspring transfers, or environmental food calculations. Contact remains the established discrete endpoint rule. Food regeneration remains base rate times the seasonal/drought product times habitat weighting, with fractional credit and a food cap. No survival rule was changed.

Predators continue paying 2.5 times the trait-based metabolic rate and receiving 65% of caught prey's remaining energy, limited by capacity. Catches occur even near capacity, so surplus energy is lost. A child receives 65 energy from its parent, plus the parent pays 6 extra; transfers are not new species-level energy. New diagnostics confirmed substantial overflow, births and eventual starvation. The shared population cap also blocks eligible reproduction attempts; this is existing behavior, not a hidden balance adjustment.

| Seed | Base food/s | Predator births | Predator energy/age deaths | Catches / observed predator | Accepted feeding energy | Metabolic energy spent | Reproduction cost | Feeding overflow |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
'''
    for r in sorted(reproduction,key=lambda r:(-r['settings']['food_per_second'],r['settings']['seed'])):
        t=r['diagnostics']['totals']['predator'];observed=t['observed_initial']+t['births']
        text+=f"| {r['settings']['seed']} | {r['settings']['food_per_second']} | {t['births']} | {t['deaths_energy']} / {t['deaths_age']} | {t['catches']/observed:.2f} | {t['feeding_gained']:.1f} | {t['metabolism_spent']:.1f} | {t['reproduction_spent']:.1f} | {t['feeding_overflow']:.1f} |\n"
    text+='''
The denominator for catches/observed predator is initial predators plus subsequent predator births, including living individuals; it is not a per-second hunting rate. Full species ledgers, minute samples, traits and individual living-predator catch counts are in `artifacts/balance-reproduce.json`. Dead-predator catch counts are aggregated, not retained as an unlimited individual archive.

| Seed | Base food/s | Prey births | Prey energy / age / caught deaths | Accepted food energy | Metabolic energy spent |
| --- | --- | --- | --- | --- | --- |
'''
    for r in sorted(reproduction,key=lambda r:(-r['settings']['food_per_second'],r['settings']['seed'])):
        t=r['diagnostics']['totals']['prey']
        text+=f"| {r['settings']['seed']} | {r['settings']['food_per_second']} | {t['births']} | {t['deaths_energy']} / {t['deaths_age']} / {t['deaths_caught']} | {t['feeding_gained']:.1f} | {t['metabolism_spent']:.1f} |\n"
    text+='''
## Tuning and frozen candidate

Only tuning seeds **101, 103, 107** were used to choose settings. Five recipes were run for 1,800 seconds each. All had habitats, predators, seasons and droughts enabled; map seed equaled world seed; cycle length was 300 seconds, drought duration 5 seconds and gaps 300-600 seconds. No new parameters were needed.

| Recipe | Initial prey/predators | Food/s | Mutation | Both species at 30 min | Mean time at combined cap |
| --- | --- | --- | --- | --- | --- |
'''
    for label in ('gentle','stable_traits','rich','moderate_zero','moderate_low'):
        rows=[r for r in tuning if r['label']==label];s=rows[0]['settings']
        text+=f"| {label} | {s['initial_population']} / {s['initial_predators']} | {s['food_per_second']} | {100*s['mutation_strength']:g}% | {sum(map(alive,rows))}/3 | {100*mean(r['cap_fraction'] for r in rows):.2f}% |\n"
    text+='''
More food alone was ineffective: the richer recipes lost all predators and spent much of each run at the cap. The moderate-food, low-mutation recipe was the only one retaining both species on all three tuning seeds. It became **Coexistence**, frozen before candidate evaluation: **160 prey, 4 predators, 24 food/s, +/-0.5% mutation**, habitats, 300-second seasons and 5-second droughts with 300-600-second gaps. After evaluation, the shipped preset uses visible world/map seed **101**, an existing tuning example, rather than claiming that arbitrary seeds reliably coexist. The frozen parameter recipe was not retuned; evaluation always overrides world/map seeds with 1001-1010. The frozen recipe is recorded in `artifacts/coexistence-frozen-recipe.json`; the later, explicit reference-seed choice is in `artifacts/coexistence-reference.json`. No rules, costs, trait bounds or original defaults changed; no advanced tuning controls were added.

## Held-out evaluation

All three configurations used the same previously untuned seeds **1001-1010**, with map seed equal to world seed. Each run was scheduled for **1,800 simulation seconds (54,000 fixed ticks)**, stopping only on complete ecosystem extinction as the app does. Balanced is the literal default (predators, habitats and events off). Changing Seasons is the Phase 8 environmental baseline (100/8 organisms, food 20, mutation 6%, cycle 120s, drought 15s, gaps 90-180s). Coexistence is the frozen recipe above. All 30 evaluation runs reached the full 1,800-second endpoint. Changing Seasons completed 15 seasonal cycles and Coexistence completed six, with several droughts in each enabled run. Seeded randomness remained the sole behavioral randomness; nothing respawned, held populations constant or adjusted difficulty.

Ranges include initial populations and every post-step population. Cap percentage is the proportion of actual simulated ticks with total population exactly 300, not the proportion of minute samples. Predator cap is still 40. “Absent” means predators were not introduced, not that they became extinct. Extinction times are simulation seconds. A dash means no extinction before the endpoint.

'''
    for label,title in [('balanced','Balanced (unchanged literal default)'),('phase8','Changing Seasons (unchanged environmental baseline)'),('coexistence','Coexistence (held-out evaluation)')]:
        rows=sorted((r for r in evaluation if r['label']==label),key=lambda r:r['settings']['seed'])
        text+=f'### {title}\n\n| Seed | End seconds | Final prey/predators | Prey range | Predator range | Prey extinction | Predator extinction | At combined cap |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n'
        for r in rows:
            def ext(s):
                if s=='predator' and r['settings']['initial_predators']==0:return 'Absent'
                value=r['extinction'][s];return '-' if value is None else f'{value:.2f}'
            text+=f"| {r['settings']['seed']} | {r['end_time']:.2f} | {r['final']['prey']} / {r['final']['predator']} | {r['ranges']['prey'][0]}-{r['ranges']['prey'][1]} | {r['ranges']['predator'][0]}-{r['ranges']['predator'][1]} | {ext('prey')} | {ext('predator')} | {100*r['cap_fraction']:.2f}% |\n"
        text+=f"\n{sum(r['cap_ticks']>0 for r in rows)}/10 runs reached the combined cap; mean fraction of time there: {100*mean(r['cap_fraction'] for r in rows):.2f}%. "
        if label!='balanced':text+=f"Observed droughts per run: {min(r['droughts'] for r in rows)}-{max(r['droughts'] for r in rows)}. "
        text+='\n\n'
    text+=f"A separate rerun of the shipped reference seed **101** ended at {default['end_time']:.2f}s with **{default['final']['prey']} prey / {default['final']['predator']} predators**; extinction times: {'none before the endpoint' if alive(default) else str(default['extinction'])}. The earlier post-freeze seed-42 check lost predators at 220.1 seconds and ended with 246 prey; it remains recorded in `artifacts/balance-reference42.json`. Reference 101 was chosen from the tuning set, never from held-out evaluation successes. This curated example does not improve the 4/10 held-out result.\n"
    text+='''
Full results and minute diagnostics are in `artifacts/balance-baseline.json`, `balance-evaluate.json`, `balance-preset.json`, `balance-tune.json` and `balance-moderate.json`. These are small finite seed sets, not statistical guarantees. Reduced mutation deliberately slows inherited change; the observations cannot establish long-term stability, adaptation or the isolated causal contribution of each changed setting. Population caps materially affect reproduction.

## Diagnostics, persistence and checks

**Observatory > Diagnostics** shows species-level births, death causes, catches, current average energy, energy flows, eligible cap-blocked attempts, lifetime totals and recent per-second rates. It does not add default-world chrome. Recent rates span up to 60 simulation seconds and report the actual interval. The ledger keeps 61 tick-sampled rows plus fixed-size species totals; individual catch counters exist only for living predators (at most 40), with dead counts aggregated. **Worlds > Export diagnostics as CSV** writes these cumulative snapshots plus the current row and experiment settings, including the seed. Existing statistics and lineage exports remain available.

Version **6** is necessary to retain these otherwise unreconstructable ledgers and recent history. Valid **v1-v5** files still load. Legacy diagnostics begin at the load tick with explicit partial-history labeling; no earlier deaths, energy or individual catches are invented. Version 5 environment state and earlier lineage/habitat migrations remain intact. Validation checks schemas, finite bounds, species/world counters, energy balance, offspring transfers, predator IDs/catches, sample phase/capacity and current state before replacement. Saves remain atomic and loads paused. The signed energy removed at death includes the existing final-tick depletion overshoot, allowing conservation checks without changing costs.

Baseline: **122 tests passed in 77.933 seconds**. Final: **136 tests passed in 93.919 seconds** (the final suite shared CPU with headless trials; this duration is not a performance benchmark). Added checks cover accounting, caps, RNG/physical equivalence against frozen Phase 8 code, fixed-speed equivalence, exact save continuation, all old versions, old Custom saves matching the newly named preset, malformed diagnostics, CSV and UI isolation. Existing atomic-write failures, environmental calculations, catch ordering, energy conservation, habitats, camera, lineage and visual tests pass.

Native scripted glass, environment, lineage and diagnostic UI checks passed at **1380x900 and 960x720**, including file pickers, replacement confirmations, fullscreen/hidden-control restoration, scroll/keyboard access, exports, and Coexistence draft/cancel/confirm. Screenshots of normal/minimum layouts were reviewed. These were automated desktop interactions and screenshot inspection, not manual pointer testing.

## Matched short performance measurements

'''
    text+=f"Hardware/environment: {before['cpu'].strip()}; {before['os']}; Python {before['python']}; Pygame {before['pygame']}; SDL {'.'.join(map(str,before['sdl']))}. Native Windows software rendering, display flip included.\n\n"
    text+='''Before/after used the identical naturally evolved environment-enabled checkpoint, loaded and advanced ten ticks to 2651. The start contained 273 prey, 27 predators and 404 food. Population remained 300 throughout, predators/habitats/events/effects enabled, normal glass, History panel open and fitted camera. Each case used 30 frozen warmup draws, then 240 active frames at 1/60-second input, processing exactly 120 ticks at 1x or 480 at 4x. These are 4 or 16 simulation seconds, not sustained gameplay measurements. No ticks were dropped. Final measurements ran after headless trial workers stopped. Event pumping/setup are excluded. Simulation, full update, rendering and total are measured separately; total is update plus render. Median is the upper middle sample; p95 uses floor((N-1)*0.95). Core simulation times are per rendered frame, including zero-step frames at 1x, not per-tick averages.

| Build | Resolution | Speed | Core simulation median/p95 ms | Render median/p95 ms | Total median/p95 ms | Wall seconds |
| --- | --- | --- | --- | --- | --- | --- |
'''
    for label,d in [('Before',before),('After',after)]:
        for r in d['cases']:
            def v(k):return f"{r[k]['median_ms']:.3f} / {r[k]['p95_ms']:.3f}"
            text+=f"| {label} | {'x'.join(map(str,r['resolution']))} | {r['speed']}x | {v('simulation')} | {v('render')} | {v('total')} | {r['wall_seconds']} |\n"
    assert [r['state_sha256'] for r in before['cases']]==[r['state_sha256'] for r in after['cases']]
    text+='''
Physical world/RNG, habitat, settings and retained-statistics hashes match in every before/after case. New diagnostic records are intentionally outside that historical fingerprint; their exact continuation is tested separately. Raw files are `artifacts/lineage-performance-phase9-before.json` and `...phase9-after.json`. Small timing differences include scheduling noise. This is not a claim of sustained 60 FPS, fullscreen performance, effects-off performance or long-duration rendering stability. No simulation optimization was introduced; diagnostics add observational work.

## Reproduce and launch (PowerShell)

```powershell
Set-Location "C:\\Users\\Admin\\Desktop\\Coding Projects\\Genesis"
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
.\\.venv\\Scripts\\python.exe tools\\check_balance.py --stage reproduce
.\\.venv\\Scripts\\python.exe tools\\check_balance.py --stage tune
.\\.venv\\Scripts\\python.exe tools\\check_balance.py --stage moderate
.\\.venv\\Scripts\\python.exe tools\\check_balance.py --stage baseline
.\\.venv\\Scripts\\python.exe tools\\check_balance.py --stage evaluate
.\\.venv\\Scripts\\python.exe tools\\check_balance.py --stage preset --workers 1
.\\.venv\\Scripts\\python.exe tools\\check_diagnostics_ui.py
.\\.venv\\Scripts\\python.exe tools\\benchmark_lineage.py --label local-balance --environment
.\\.venv\\Scripts\\python.exe -m genesis
```

Choose **Settings > Experiment > Coexistence**, inspect the draft, then **Start new experiment** and confirm. Defaults remain unchanged. Headless trials can use `--workers 1` to reduce CPU load; do not run them alongside a rendering benchmark. Dependencies and fresh-install commands are in README.md. No neural networks, new species, terrain editing, forced cycles, respawning or adaptive difficulty were added.
'''
    (ROOT/'BALANCE_REPORT.md').write_text(text,encoding='utf-8')

if __name__=='__main__':main()
