# Ecosystem balance revision — investigation in progress

This report distinguishes reproduced observations from proposed rules. The
predeclared release gates are in `BALANCE_REVISION_PLAN.md`. An experimental
candidate is not an accepted release merely because short trials look better.

## What “purple” meant

The old renderer used five speed bins, with boundaries at 33, 39, 45 and 51.
Every inherited speed from 51 through the upper bound of 75 used the same
purple color. Species used separate palettes; angular bodies identified
predators. Color never represented fitness, age, energy, body size or ancestry.
Consequently color hid differences, but was not the only problem.

Three fixed-step reproductions used the documented original settings and seeds.
They ran for 3,600 simulation seconds or irreversible complete extinction:

| Original recipe | Seed | Final prey / predators | Predator extinction | Shared cap occupancy |
|---|---:|---:|---:|---:|
| Default (predators disabled) | 42 | 234 / 0 | Absent initially | 1.12% |
| Coexistence | 101 | 300 / 0 | 3,273.23 s | 45.06% |
| Changing Seasons | 42 | 0 / 0 | 243.77 s | 0% |

Default prey all fell in the purple bin after an hour. Within that world the
speed/body-size interquartile ranges were 5.31 / 0.38; 25.6% were within 1% of
maximum speed and 20.1% within 1% of minimum size. Coexistence had still narrower
speed/sensing/size IQRs of 0.59 / 3.37 / 0.051. These are within-world figures,
not variation pooled across seeds.

The organisms were **not inert particles**. During the final five minutes the
default world had 6,000 eating events and 475 births; Coexistence had 9,250 eating
events and 493 births. Default had 5,742 births during the hour. Coexistence had
10,638 prey births, 913 predator births and 7,699 catches before losing predators.
Changing Seasons lost prey at 220.77 s: 694 were caught and 22 died of energy
depletion; its 129 predator deaths were all energy depletion.

## Mechanism findings

- Speed increases encounters and escape, while small bodies have lower survival
  and movement costs. A single interchangeable food resource provided little
  countervailing advantage to larger bodies. Very low mutation in Coexistence
  (0.5%) also allowed exceptionally narrow trait distributions.
- Clipped mutation accumulates exact-bound values. Reflection keeps mutations
  bounded without that clipping artifact; it does not enforce trait diversity.
- A controlled isolated-food test demonstrated an arrival defect: constant-speed
  turning can orbit food indefinitely. With reproduction disabled, an organism
  at speed 75 and radius 3, initialized on its turn circle around one food, failed
  to eat it during 900 steps. The new arrival steering eats it in the same test.
- Original movement/reproduction actors were shuffled every tick. They did not
  always favor older IDs. Original contested catches did use ascending predator
  IDs; revised catches use the existing shuffled order and nearest-contact/ID
  tie breaks. Each victim can still be consumed only once.
- The shared cap deferred reproduction without charging reproductive energy.
  Coexistence recorded 3,948,073 prey and 67,121 predator blocked opportunities
  (per-tick counters, not unique failed births). Its 45% cap occupancy was a real
  constraint; the corrected recipe must spend under 10% at this cap.
- Reproduction transfers parental energy and charges its explicit overhead.
  No free-energy reproduction or incorrect seasonal/habitat multiplier was
  demonstrated. Those calculations remain unchanged.

## Experimental Ecology rules

Only corrected rules are exposed in the desktop. Ecology changes are explicit
fixed rules, independent of population targets, presentation, or elapsed wall
time. They never respawn organisms or force survival outcomes.

Three golden food particle sizes are regenerated in a deterministic sequence.
Inherited body size determines digestive efficiency: specialists compete for
different finite renewable resources. Larger cells can efficiently use the
larger, higher-energy particles, but pay greater body and propulsion costs;
small cells are harder for predators to detect. This creates resource niches
instead of maintaining variety with cosmetic recoloring or organism quotas.

Prey brake when arriving at food. Both species brake during sharp turns, with
larger bodies turning more slowly. Predators lead moving targets, require
sufficient body size to handle a victim, digest after a catch, and incur a
documented local interference cost from nearby hunters. Lower cruising effort
when wandering is charged consistently; dense habitat still requires propulsion
effort despite slower motion. Predator reproduction requires more stored energy,
transfers more to its child, and has a longer cooldown. Thresholds, bounds,
costs and candidate parameters are archived with each trial.

The new palette interpolates 33 shades across inherited **body size 3–9**:
small cells are cyan/lime, medium cells orange, and large cells pink/violet.
This deliberately shows the trait that governs dietary specialization; speed
remains visible in motion and numerical inspection. It is not a claim of
adaptation. Appearance explains the mapping, and the Observatory retains
numerical distributions of all three traits. Biological acceptance is assessed
independently of this presentation change.

### Candidate 11 rule specification

These are explicit simulation rules, not feedback tuned to a target population:

| Component | Ecology rule |
|---|---|
| Trait bounds | Speed 18–75, sensing 35–160, body radius 3–9; unchanged |
| Founders | Prey body sizes span 3.3–8.7 instead of Classic's 4–6.5; speed/sensing founder ranges and RNG draw counts are unchanged |
| Food types | Target body radii 3.75 / 5.75 / 8; energy factors 0.75 / 1 / 1.4 |
| Assimilation | `0.05 + 0.95 / (1 + ((size - target) / 0.9)^4)`; only particles with efficiency >= 0.25 are digestible |
| Meal energy | `27 * type energy factor * assimilation`, limited by the organism's 180 energy capacity |
| Resource capacity | 217 / 217 / 216 particles; total <= 650. No organism quotas. Unconsumed food cannot block renewal of another resource |
| Renewal | Existing habitat and environmental multipliers; scheduled spawn attempts cycle across food types. A full resource skips its attempt, without reallocating it to another resource |
| Prey reproduction | Energy >=145; maturity 8 s; transfer 65 + overhead 6; cooldown 12 s |
| Predator reproduction | Energy >=160; maturity 20 s; transfer 80 + overhead 6; cooldown 45 s |
| Maximum age | Prey 180 s; predators 360 s. Both still require feeding throughout life |
| Mutation | Uniform signed change up to `strength * (upper-lower)/2`, reflected at bounds; three seeded draws per birth |
| Catch | Physical overlap; hunter size >=85% of victim size; transfer 65% of remaining prey energy; each victim resolves once |
| Digestion | `6 + 0.5 * victim size` seconds; stationary, no further catches, ongoing energy expense |
| Local interference | Hunters pay `1.5 * sum(max(0, 1-distance/160))` energy/s for other nearby hunters; start-of-step positions |

Propulsion and maintenance expense per second is
`0.60 + 0.50*(speed/reference)^2*sqrt(size/5)
+ 0.80*(effort/reference)^3*sqrt(size/5)
+ 0.22*(size/5)^2 + 0.35*(sensing/90)^2`, with reference speed 40 for prey
and 55 for predators. `effort` is commanded movement speed divided by the habitat
movement multiplier. High-speed capacity therefore has an upkeep cost even
while braking; actual propulsion pays a separate cost. Dense regions reduce
movement to 60% without making propulsion cheaper. Boundary clamping can reduce
achieved displacement; energy pays for attempted propulsion, not teleportation.

Hunting uses a 1.25 pursuit-speed factor and short predictive lead; idle hunters
cruise at 45% speed. Prey flee and give nearby food a small steering weight.
Sensing costs energy; it also increases food choices, warning distance and
hunting range. Smaller prey have shorter detection distances. Larger bodies
access different foods and can handle larger victims, but cost more energy and
turn more slowly. Neither species can turn more than `5*sqrt(5/size)` radians/s;
arrival and sharp-turn braking avoid the original orbit trap.

The initial candidate 11 recipe used 160 prey, 8 predators, base food 28/s,
mutation strength 14%, and seeded habitats. The accepted candidate 14 changes
mutation to 20% for normal conditions and 18% for the stress recipe. Stress adds a 180-second seasonal cycle,
10-second droughts, and drought-free gaps of 120–240 seconds. Seasonal
multipliers remain 0.5–1.5, drought multiplies by 0.25, and gardens regenerate
at twice the open-water rate. These factors multiply; they never kill, create
organisms or change traits directly.

## Validation status

Baseline verified: 148 tests passed in 94.729 seconds. An intermediate full
suite passed 172 tests in 278.446 seconds while trials were running. The current
focused Ecology suite passed 25 tests in 71.278 seconds, including exact
continuation across future drought/season transitions. Five launch-option
tests also passed; final full-suite and package validation remain in progress.

The first six candidates were not accepted. Candidate 6 retained both species
in three ten-minute normal trials but lost predators at 1,920.33 s in one
hour-long trial. It also failed the declared diversity gate. This is why short
survival demonstrations are insufficient. No held-out seeds have been used to
tune it. Candidate 8 retained both species in all six hour-long tuning worlds
but failed normal-world speed diversity in all three. Candidate 10 passed
diversity in both persistent normal worlds, but lost predators in the third at
2,714.9 s; all three stressed worlds retained both species. Candidate 11 tightens
the resource niches. Its three normal tuning worlds passed persistence,
activity, diversity and cap checks; all three stressed tuning worlds retained
both species with ongoing births and catches. Stress cap occupancy remained
high. These are tuning results, not held-out evidence.

An additional seed-42 check retained both species for an hour under normal and
stressed settings. Normal prey IQRs at 30/45/60 minutes were speed
13.71/12.12/17.34, sensing 13.06/17.41/17.29, and body size 3.45/3.73/3.57.
The sensing threshold failed at 30 minutes; this world does not count as passing
the strict multi-checkpoint diversity gate. [Per-world tuning tables](reports/balance-revision/tuning/RESULTS.md),
[seed 42](reports/balance-revision/default-seed/RESULTS.md), and
[original recipes](reports/balance-revision/original-recipes/RESULTS.md) retain
these observations.

### First held-out evaluation: not accepted

Candidate 11 completed the matched 40-world evaluation on seeds 3001–3010.
Ecology retained both species in **10/10 normal** and **9/10 stressed** worlds;
Classic retained them in **0/10** for both matched recipes. All persistent
Ecology worlds passed the late activity checks, and all ten normal Ecology
worlds met the cap limit. However, only **6/10 normal worlds** passed all three
trait-diversity checkpoints, below the predeclared 8/10 gate. This is a failed
release gate despite the substantial survival improvement.

[The complete first held-out comparison](reports/balance-revision/candidate11-heldout/RESULTS.md)
is retained. Candidate 12 changes only the recipe's existing mutation-strength
setting from 14% to 18%, addressing the sensing-variation shortfall already
measured on seed 42. Mechanics remain unchanged. It is being retested on
211/223/227/42; the next evaluation uses fresh seeds 4001–4010. Final evaluation
and release paths will follow validation.

### Rendering work

The 33-shade palette exposed thrashing in the old 96-surface sprite cache.
In the same 360-frame, 4× near-cap workload, prey sprite misses fell from 40,553
to 16 using a cache bounded by **512 entries and 16 MiB of pixel buffers per
species**. Cached pixels are unchanged and are tested against direct rendering.
The timing runs had concurrent trial load, so their timings are not used to
claim a frame-rate improvement. Final idle-machine source/package measurements
remain to be performed.


## Accepted candidate 14 and corrected-only desktop

Candidate 14 uses the candidate 11 mechanics with mutation strength .20 in
Living Ecosystem and .18 in Living Seasons. These explicit recipes were selected
using tuning seeds 211, 223, 227 and 42, before evaluating fresh seeds 4001?4010.
The 40 matched one-hour trials passed the predeclared gates: normal 10/10
persistent, active, diverse and under the cap threshold; stress 9/10 persistent
and active. Old rules under matched conditions retained both species in 0/10
normal and 0/10 stress trials. This is finite evidence, not guaranteed survival.
Stress diversity passed in 7/10 worlds and cap occupancy remains higher.

[Full per-world results, extinction times and trait checkpoints](reports/balance-revision/candidate14-heldout/RESULTS.md).
Normal corrected cap occupancy ranged 0.05?2.84%; old normal worlds spent
94.06?95.85% of steps at the cap. Corrected normal catches were 4,670?5,333,
with continuing births in both species rather than stationary survival.

At the user's request, the desktop exposes only corrected rules: no Classic
control, preset entry, or CLI flag. Startup and Defaults use Living Ecosystem;
obsolete-rule loads leave the active world intact and show an error. Internal
legacy model support remains solely for regression/research comparisons, not
as an available desktop mode. Existing save files are not deleted.
