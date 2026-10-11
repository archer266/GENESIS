"""Observational energy/event ledger. Never consulted by simulation decisions."""
from collections import deque
from copy import deepcopy
from dataclasses import asdict
import csv
from pathlib import Path
import math

SPECIES = ("prey", "predator")
COUNTS = ("observed_initial", "births", "deaths_energy", "deaths_age", "deaths_caught", "catches",
          "population_cap_blocks", "predator_cap_blocks")
ENERGY = ("initial_energy", "feeding_gained", "feeding_overflow", "metabolism_spent",
          "reproduction_spent", "offspring_transferred", "death_energy_removed", "organism_seconds")
LIMIT = 61


class Diagnostics:
    def __init__(self):
        self.since_tick = 0
        self.legacy = False
        self.base_counts = dict(births=0, deaths=0, catches=0)
        self.totals = {s: {**dict.fromkeys(COUNTS, 0), **dict.fromkeys(ENERGY, 0.0)} for s in SPECIES}
        self.living_catches = {}
        self.dead_predators = 0
        self.dead_predator_catches = 0
        self.samples = deque(maxlen=LIMIT)

    @classmethod
    def observe_existing(cls, world):
        d = cls()
        d.since_tick, d.legacy = world.ticks, True
        d.base_counts = {k: getattr(world, k) for k in d.base_counts}
        for o in world.organisms.values():
            d.add(o, founder=True)
        d.sample(world)
        return d

    def add(self, o, founder=False):
        t = self.totals[o.species]
        t["observed_initial" if founder else "births"] += 1
        if founder:
            t["initial_energy"] += o.energy
        if o.species == "predator":
            self.living_catches[str(o.id)] = 0

    def death(self, o, cause):
        t = self.totals[o.species]
        t["deaths_"+cause] += 1
        # Signed residual includes the last tick's small energy overshoot.
        t["death_energy_removed"] += o.energy
        if o.species == "predator":
            self.dead_predators += 1
            self.dead_predator_catches += self.living_catches.pop(str(o.id), 0)

    def feed(self, o, before, offered):
        gained = o.energy-before
        self.totals[o.species]["feeding_gained"] += gained
        self.totals[o.species]["feeding_overflow"] += max(0.0, offered-gained)

    def snapshot(self, world):
        row = {"tick": world.ticks}
        for s in SPECIES:
            group = [o for o in world.organisms.values() if o.species == s]
            row.update({s+"_"+k: v for k, v in self.totals[s].items()})
            row[s+"_population"] = len(group)
            row[s+"_average_energy"] = sum(o.energy for o in group)/len(group) if group else None
        return row

    def sample(self, world):
        if not self.samples or (self.samples[-1]["tick"] != world.ticks and
                                (world.ticks % 30 == 0 or not world.organisms)):
            self.samples.append(self.snapshot(world))

    def recent(self, world):
        """Rates over up to 60 simulation seconds; partial first window explicit."""
        now = self.snapshot(world)
        cutoff = world.ticks-round(60/world.config.timestep)
        old = next((r for r in self.samples if r["tick"] >= cutoff), now)
        seconds = (world.ticks-old["tick"])*world.config.timestep
        rates = {}
        for s in SPECIES:
            for k in ("births", "deaths_energy", "deaths_age", "deaths_caught", "catches", "feeding_gained", "metabolism_spent"):
                key = s+"_"+k
                rates[key] = (now[key]-old[key])/seconds if seconds else None
        return seconds, rates

    def document(self):
        return dict(since_tick=self.since_tick, legacy=self.legacy, base_counts=dict(self.base_counts),
                    totals=deepcopy(self.totals), living_catches=dict(self.living_catches),
                    dead_predators=self.dead_predators, dead_predator_catches=self.dead_predator_catches,
                    capacity=LIMIT, samples=deepcopy(list(self.samples)))

    def export_csv(self, path, world, settings):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = list(self.samples)
        current = self.snapshot(world)
        if not rows or rows[-1]["tick"] != current["tick"]:
            rows.append(current)
        metadata = {"diagnostics_since_tick": self.since_tick, "legacy_partial": self.legacy,
                    "retained_sample_capacity": LIMIT, **asdict(settings)}
        with path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["simulation_seconds", *current, *metadata])
            writer.writeheader()
            for row in rows:
                writer.writerow({"simulation_seconds": row["tick"]*world.config.timestep, **row, **metadata})
        return path

    @classmethod
    def restore(cls, raw, world):
        def require(ok, message):
            if not ok:
                raise ValueError("Invalid diagnostics: "+message)
        def count(v, high=10**12):
            require(type(v) is int and 0 <= v <= high, "counter out of range")
        def finite(v, signed=False):
            require(type(v) in (int, float) and math.isfinite(v) and
                    (-1e18 if signed else 0) <= v <= 1e18, "energy or time out of range")
        d = cls()
        require(isinstance(raw, dict) and set(raw) == set(d.document()), "schema")
        count(raw['since_tick'], world.ticks)
        require(type(raw['legacy']) is bool, "legacy flag")
        require(raw['legacy'] or raw['since_tick'] == 0, "lifetime origin")
        require(type(raw['capacity']) is int and raw['capacity'] == LIMIT, "capacity")
        require(isinstance(raw['base_counts'], dict) and set(raw['base_counts']) == set(d.base_counts), "base counts")
        for k,v in raw['base_counts'].items():
            count(v, getattr(world,k))
            require(raw['legacy'] or v == 0, "lifetime base counts")
        require(isinstance(raw['totals'], dict) and set(raw['totals']) == set(SPECIES), "species")
        for s,t in raw['totals'].items():
            require(isinstance(t,dict) and set(t) == set(COUNTS+ENERGY), "ledger fields")
            for k in COUNTS: count(t[k])
            for k in ENERGY: finite(t[k], k == 'death_energy_removed')
            group=[o for o in world.organisms.values() if o.species==s]
            count(t['observed_initial'],world.config.population_cap)
            if not raw['legacy']:
                expected=world.config.initial_population if s=='prey' else world.config.initial_predators
                require(t['observed_initial']==expected and t['initial_energy']==expected*world.config.initial_energy, "founder energy/count")
            deaths=sum(t['deaths_'+cause] for cause in ('energy','age','caught'))
            require(t['observed_initial']+t['births']-deaths == len(group), "species accounting")
            require(t['offspring_transferred'] == t['births']*world.config.offspring_energy, "offspring transfer")
            require(t['reproduction_spent'] == t['births']*world.config.reproduction_cost, "reproduction expense")
            balance=t['initial_energy']+t['feeding_gained']-t['metabolism_spent']-t['reproduction_spent']-t['death_energy_removed']
            require(math.isclose(balance,sum(o.energy for o in group),rel_tol=1e-8,abs_tol=1e-5), "energy balance")
        totals=raw['totals']
        require(totals['prey']['catches']==0 and totals['predator']['deaths_caught']==0, "species roles")
        require(totals['prey']['deaths_caught']==totals['predator']['catches'], "catch victims")
        for k in ('births','deaths','catches'):
            observed=sum(sum(t['deaths_'+c] for c in ('energy','age','caught')) if k=='deaths' else t[k] for t in totals.values())
            require(observed+raw['base_counts'][k]==getattr(world,k), "world counters")
        living=raw['living_catches']
        require(isinstance(living,dict) and set(living)=={str(o.id) for o in world.organisms.values() if o.species=='predator'}, "living predator IDs")
        for v in living.values(): count(v)
        count(raw['dead_predators']); count(raw['dead_predator_catches'])
        require(raw['dead_predators']==totals['predator']['deaths_energy']+totals['predator']['deaths_age'], "dead predators")
        require(sum(living.values())+raw['dead_predator_catches']==totals['predator']['catches'], "individual catches")
        samples=raw['samples']
        require(isinstance(samples,list) and 1 <= len(samples) <= LIMIT, "sample count")
        periodic=world.ticks//30-raw['since_tick']//30
        terminal=int(not world.organisms and world.ticks%30!=0 and world.ticks>raw['since_tick'])
        total=1+periodic+terminal
        require(len(samples)==min(LIMIT,total), "retained sample count")
        d.since_tick, d.legacy = raw['since_tick'], raw['legacy']
        d.totals, d.base_counts = deepcopy(totals), dict(raw['base_counts'])
        d.living_catches=dict(living)
        d.dead_predators, d.dead_predator_catches=raw['dead_predators'], raw['dead_predator_catches']
        schema=set(d.snapshot(world))
        previous=None
        for index,row in enumerate(samples,start=max(0,total-LIMIT)):
            require(isinstance(row,dict) and set(row)==schema, "sample schema")
            count(row['tick'],world.ticks)
            expected_tick=raw['since_tick'] if index==0 else min((raw['since_tick']//30+index)*30,world.ticks)
            require(row['tick']==expected_tick, "sample phase")
            require(row['tick']>=d.since_tick and (previous is None or row['tick']>previous['tick']), "sample order")
            for s in SPECIES:
                n=row[s+'_population']; count(n,world.config.population_cap)
                mean=row[s+'_average_energy']
                require((n==0 and mean is None) or (n>0 and type(mean) in (int,float) and math.isfinite(mean) and 0<mean<=world.config.energy_capacity), "average energy")
                for k in COUNTS+ENERGY:
                    v=row[s+'_'+k]
                    if k in COUNTS: count(v)
                    else: finite(v,k=='death_energy_removed')
                    if k!='death_energy_removed':
                        require(v<=totals[s][k] and (previous is None or v>=previous[s+'_'+k]), "sample totals")
                require(n==row[s+'_observed_initial']+row[s+'_births']-sum(row[s+'_deaths_'+c] for c in ('energy','age','caught')), "sample population")
            if row['tick']==world.ticks:
                require(row==d.snapshot(world), "current sample")
            previous=row
        expected_last = world.ticks if not world.organisms else max(d.since_tick,world.ticks//30*30)
        require(samples[-1]['tick']==expected_last, "latest sample time")
        d.samples=deque(deepcopy(samples),maxlen=LIMIT)
        return d
