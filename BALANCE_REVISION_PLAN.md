# Balance revision: criteria declared before held-out evaluation

Baseline: 148 tests passed in 94.729 seconds on 2026-10-12.

Tuning seeds: 211, 223, 227. Diagnostic reproduction also uses the documented
default seed 42, Coexistence reference seed 101, and Changing Seasons seed 42.
Held-out seeds: 3001–3010, with map seed equal to world seed. They must not be
used to choose parameters. If acceptance fails, report the failure, revise on
tuning seeds, and use a new held-out seed range for the next evaluation.

Each held-out evaluation is 60 simulation minutes (108,000 fixed steps), or
irreversible complete extinction. Compare Classic and corrected rules under
identical starting recipes, seeds and durations for recommended and stressed
conditions. Also reproduce the original default, Coexistence and Changing
Seasons recipes for the full horizon. No resets, respawns or interventions.

Acceptance criteria, to be evaluated per world rather than on pooled traits:

1. Both species remain present for the full hour in at least 9/10 recommended
   runs and 8/10 stressed runs. Extinction remains possible.
2. In those persistent worlds, each of the last three five-minute observation
   windows has at least 10 prey births, 2 predator births and 10 catches.
3. At least 8/10 recommended worlds retain meaningful prey trait variation at
   30, 45 and 60 minutes: size IQR >= 1.0, speed IQR >= 8, sensing IQR >= 15;
   no more than 30% within 1% of either bound of any one trait.
4. Recommended worlds spend under 10% of steps at the shared population cap.
5. Exact Classic continuation, seeded reproducibility, fixed-step speed
   equivalence, honest energy accounting and persistence tests pass.

Stress uses seasons and droughts, including multiple full cycles. Parameters
and the selected candidate must be frozen before launching held-out trials.
Report species extinction times, births/catches/deaths, cap fractions, food,
feeding/energy, movement, trait quantiles and histograms at multiple checkpoints.
The model must support the result; changing color bins alone cannot pass.

Candidate 11 was frozen for the first held-out evaluation on 2026-10-12.
The three tuning seeds each passed normal survival, activity, diversity and
cap criteria; all three stress trials retained active populations of both
species. Stress cap occupancy was high and is reported separately. The exact
source hashes and settings are retained in the evaluation manifest. No tuning
changes are permitted based on seeds 3001–3010; a failed evaluation requires
another tuning cycle and a fresh evaluation range.

Candidate 11 failed the first held-out gate: normal persistence 10/10, stress
persistence 9/10, active interactions in all persistent worlds, normal cap
10/10, but normal multi-checkpoint diversity only 6/10 (required 8/10).
The results are retained under `reports/balance-revision/candidate11-heldout`.
No release is accepted on those results. Candidate 12 changes only the existing
mutation-strength setting from 14% to 18%, addressing the sensing-variation
shortfall already observed on tuning/default seed 42. Tune on 211/223/227/42;
the next held-out range is **4001–4010**, never 3001–3010 again.

Candidate 12 (18%) retained both species in all eight tuning/default runs,
but passed normal diversity in only 3/4. Candidate 13 (20%) passed every
normal gate on all four tuning/default seeds; stress passed on 211/223/227
but seed 42 lost predators at 1,144.97 seconds. No fresh held-out seeds were
used for these choices.

**Candidate 14 is frozen for evaluation on 4001–4010:** the normal Living
Ecosystem recipe uses 20% mutation, and Living Seasons explicitly uses 18%.
All other mechanics/settings are unchanged from candidate 11. Both recipes
passed their relevant gates on all four tuning/default seeds. Mutation is an
editable starting setting, never automatic feedback: manually toggling events
does not change it. The comparison matches Classic and Ecology settings within
each recipe; it does not claim to isolate environmental effects alone between
the two recipes. Acceptance thresholds are unchanged.
