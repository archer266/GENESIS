"""Experimental rules 2. Classic rules remain in simulation.py.

Resource particle sizes provide renewable niches, not population quotas.
All behavior is fixed-step and all mutations/order use the world's RNG.
"""
import math
from functools import lru_cache
from .simulation import Traits, SimulationEvent

PARTICLE_SIZES = (3.75, 5.75, 8.0)
PARTICLE_ENERGY = (.75, 1.0, 1.4)


def recommended_settings(stress=False):
    from .observatory import ExperimentSettings
    return ExperimentSettings(initial_population=160, food_per_second=28, mutation_strength=.18 if stress else .20,
        predator_enabled=True, initial_predators=8, habitat_enabled=True,
        seasons_enabled=stress,droughts_enabled=stress,season_length=180,drought_duration=10,drought_interval=120,rules_version=2)


def mutate(traits, rng, strength):
    values={}
    for key,(low,high) in Traits.BOUNDS.items():
        value=getattr(traits,key)+rng.uniform(-strength,strength)*(high-low)*.5
        # Reflection avoids a point mass caused by clipping at either bound.
        if value<low:value=2*low-value
        if value>high:value=2*high-value
        values[key]=value
    return Traits(**values)


@lru_cache(maxsize=8192)
def efficiencies(size):
    return tuple(.05+.95/(1+((size-target)/.9)**4) for target in PARTICLE_SIZES)


def feeding_value(organism, food, config):
    kind=(food.id-1)%3
    return config.food_energy*PARTICLE_ENERGY[kind]*efficiencies(organism.traits.size)[kind]


def nearest_food(world,o):
    radius=o.traits.sense;x,y=o.x,o.y
    x0,y0=world._cell(x-radius,y-radius);x1,y1=world._cell(x+radius,y+radius)
    efficiency=efficiencies(o.traits.size)
    best=None;candidate=None
    for cx in range(x0,x1+1):
        for cy in range(y0,y1+1):
            for food in world._food_grid.get((cx,cy),{}).values():
                d=(food.x-x)**2+(food.y-y)**2
                if d<=radius*radius:
                    kind=(food.id-1)%3
                    if efficiency[kind]<.25:continue  # Not a digestible particle for this body.
                    score=(d+100)/(efficiency[kind]*PARTICLE_ENERGY[kind])**2
                    key=(score,food.id)
                    if best is None or key<best:best=key;candidate=food
    return candidate


def nearest_animal(world,o):
    radius=o.traits.sense;x,y=o.x,o.y
    x0,y0=world._cell(x-radius,y-radius);x1,y1=world._cell(x+radius,y+radius)
    candidates=[]
    for cx in range(x0,x1+1):
        for cy in range(y0,y1+1):
            for target in world._animal_grid.get((cx,cy),()):
                oid,tx,ty,species=target
                if species==o.species or oid not in world.organisms:continue
                visible=radius
                if o.species=='predator':
                    prey=world.organisms[oid]
                    if o.traits.size<.85*prey.traits.size:continue
                    visible*=min(1,.4+.6*(prey.traits.size/7)**2)
                d=(tx-x)**2+(ty-y)**2
                if d<=visible**2:candidates.append((d,oid,target))
    return min(candidates)[2] if candidates else None


def interference(world,o):
    if o.species!='predator':return 0.0
    radius=160.0
    x0,y0=world._cell(o.x-radius,o.y-radius);x1,y1=world._cell(o.x+radius,o.y+radius)
    crowding=0.0
    for cx in range(x0,x1+1):
        for cy in range(y0,y1+1):
            for oid,x,y,species in world._animal_grid.get((cx,cy),()):
                if oid!=o.id and species=='predator' and oid in world.organisms:
                    d=math.hypot(o.x-x,o.y-y)
                    if d<radius:crowding+=1-d/radius
    return 1.5*crowding


def energy_rate(o, speed, movement=1):
    # Propulsion through dense habitat costs the same effort at its lower speed.
    effort=speed/movement
    t=o.traits
    reference=55 if o.species=="predator" else 40
    # Maintaining a high-speed propulsion system costs energy even while
    # braking/foraging. Actual movement still pays its separate effort cost.
    return .60+.50*(t.speed/reference)**2*math.sqrt(t.size/5)+.80*(effort/reference)**3*math.sqrt(t.size/5)+.22*(t.size/5)**2+.35*(t.sense/90)**2


def regenerate_food(world, count):
    """Each resource has finite carrying capacity, independent of consumers.

    A resource nobody eats cannot occupy the entire shared food budget. Skipped
    IDs advance the existing deterministic particle cycle, so no new RNG or
    saved phase counter is necessary. No organism population is reserved.
    """
    counts=[0,0,0]
    for food in world.food.values():counts[(food.id-1)%3]+=1
    for _ in range(count):
        kind=(world._next_food_id-1)%3
        limit=world.config.food_cap//3+int(kind<world.config.food_cap%3)
        if counts[kind]<limit:
            world._spawn_food();counts[kind]+=1
        else:
            world._next_food_id+=1


def remove(world,o,cause):
    world.diagnostics.death(o,cause)
    world.lineage.record_death(o.id,world.event_time,cause)
    world.events.append(SimulationEvent('death',o.id,o.x,o.y,o.traits))
    world.handling.pop(o.id,None)
    del world.organisms[o.id];world.deaths+=1


def catches(world,order):
    # Existing seeded actor order resolves contention, not permanent ID priority.
    grid={}
    for o in world.organisms.values():
        if o.species=='prey':grid.setdefault(world._cell(o.x,o.y),[]).append(o)
    for oid in order:
        o=world.organisms.get(oid)
        if o is None or o.species!='predator' or o.energy>=170 or world.handling.get(oid,0)>0:continue
        radius=o.traits.size+9;x0,y0=world._cell(o.x-radius,o.y-radius);x1,y1=world._cell(o.x+radius,o.y+radius)
        contacts=[]
        for cx in range(x0,x1+1):
            for cy in range(y0,y1+1):
                for p in grid.get((cx,cy),()):
                    if p.id not in world.organisms or o.traits.size<.85*p.traits.size:continue
                    d=(o.x-p.x)**2+(o.y-p.y)**2
                    if d<=(o.traits.size+p.traits.size)**2:contacts.append((d,p.id))
        if not contacts:continue
        victim=world.organisms[min(contacts)[1]]
        world.handling[o.id]=6+.5*victim.traits.size
        offered=max(0,victim.energy)*world.config.catch_efficiency
        before=o.energy;o.energy=min(world.config.energy_capacity,before+offered)
        world.diagnostics.feed(o,before,offered)
        world.diagnostics.totals['predator']['catches']+=1
        world.diagnostics.living_catches[str(o.id)]+=1
        world.diagnostics.death(victim,'caught');world.lineage.record_death(victim.id,world.event_time,'caught')
        del world.organisms[victim.id];world.deaths+=1;world.catches+=1
        world.events.append(SimulationEvent('catch',o.id,victim.x,victim.y,o.traits))


def step(world):
    c=world.config;dt=c.timestep
    world.events.clear();world._stepping=True
    order=list(world.organisms);world.rng.shuffle(order)
    world._animal_grid={}
    velocities={}
    for o in world.organisms.values():
        world._animal_grid.setdefault(world._cell(o.x,o.y),[]).append((o.id,o.x,o.y,o.species))
        movement=world.habitats.movement_multipliers[world.habitats.region_at(o.x,o.y)] if c.habitat_enabled else 1
        velocities[o.id]=(math.cos(o.heading)*o.traits.speed*movement,math.sin(o.heading)*o.traits.speed*movement)
    for oid in order:
        o=world.organisms[oid];o.age+=dt;o.cooldown=max(0,o.cooldown-dt)
        if o.age>=world.maximum_age(o.species) or o.energy<=0:
            remove(world,o,'energy' if o.energy<=0 else 'age');continue
        movement=world.habitats.movement_multipliers[world.habitats.region_at(o.x,o.y)] if c.habitat_enabled else 1
        if world.handling.get(oid,0)>0:
            remaining=max(0,world.handling[oid]-dt)
            if remaining:world.handling[oid]=remaining
            else:world.handling.pop(oid)
            before=o.energy;o.energy-=(energy_rate(o,0,movement)*c.predator_energy_multiplier+interference(world,o))*dt
            ledger=world.diagnostics.totals[o.species]
            ledger['metabolism_spent']+=before-o.energy;ledger['organism_seconds']+=dt
            if o.energy<=0:remove(world,o,'energy')
            continue
        food=nearest_food(world,o) if o.species=='prey' else None
        target=nearest_animal(world,o) if c.predator_enabled else None
        if o.species=='predator' and o.energy>=170:target=None
        speed=o.traits.speed*movement
        if target:
            tid,tx,ty,_=target;dx,dy=tx-o.x,ty-o.y
            if o.species=='prey':
                dx,dy=-dx,-dy
                if food:
                    length=max(1,math.hypot(dx,dy));fl=max(1,math.hypot(food.x-o.x,food.y-o.y))
                    dx=dx/length+.15*(food.x-o.x)/fl;dy=dy/length+.15*(food.y-o.y)/fl
            else:
                speed*=1.25
                lead=min(.8,math.hypot(dx,dy)/max(1,speed))
                vx,vy=velocities[tid];dx+=vx*lead;dy+=vy*lead
            desired=math.atan2(dy,dx)
        elif food:
            dx,dy=food.x-o.x,food.y-o.y
            desired=math.atan2(dy,dx)
            # Arrival steering: turn radius shrinks below contact distance.
            speed=min(speed,max(2,math.hypot(dx,dy)*1.7))
        else:
            if o.species=='predator':speed*=.45
            o.wander_timer-=dt
            if o.wander_timer<=0:
                o.wander_turn=world.rng.uniform(-1.8,1.8);o.wander_timer=world.rng.uniform(.4,1.4)
            desired=o.heading+o.wander_turn*dt
        turn=5.0*math.sqrt(5/o.traits.size)
        delta=(desired-o.heading+math.pi)%math.tau-math.pi
        if target or food:
            speed*=max(.25,math.cos(delta))
        o.heading+=max(-turn*dt,min(turn*dt,delta))
        before=o.energy
        expense=(energy_rate(o,speed,movement)*(c.predator_energy_multiplier if o.species=='predator' else 1)+interference(world,o))*dt
        o.energy-=expense
        ledger=world.diagnostics.totals[o.species];ledger['metabolism_spent']+=before-o.energy;ledger['organism_seconds']+=dt
        if o.energy<=0:remove(world,o,'energy');continue
        o.x+=math.cos(o.heading)*speed*dt;o.y+=math.sin(o.heading)*speed*dt
        r=o.traits.size
        if o.x<r or o.x>c.width-r:o.x=max(r,min(c.width-r,o.x));o.heading=math.pi-o.heading
        if o.y<r or o.y>c.height-r:o.y=max(r,min(c.height-r,o.y));o.heading=-o.heading
        o.heading=(o.heading+math.pi)%math.tau-math.pi
        if food and math.hypot(food.x-o.x,food.y-o.y)<=r+3:
            before=o.energy;offered=feeding_value(o,food,c)
            o.energy=min(c.energy_capacity,o.energy+offered);world.diagnostics.feed(o,before,offered)
            world._remove_food(food);world.events.append(SimulationEvent('eat',o.id,food.x,food.y,o.traits))
    if c.predator_enabled:catches(world,order)
    for oid in order:
        if oid in world.organisms:world._reproduce(world.organisms[oid])
    rate=c.food_per_second*(world.habitats.mean_food_multiplier if c.habitat_enabled else 1)
    if world.environment.enabled:world.environment.advance();rate*=world.environment.multiplier
    else:world.environment.ticks+=1
    world._food_credit+=rate*dt
    count=int(world._food_credit+1e-9);world._food_credit=max(0,world._food_credit-count)
    if count:regenerate_food(world,count)
    world.ticks+=1;world._stepping=False;world.diagnostics.sample(world)
