"""Pure simulation model. No Pygame, wall clock, or global random state."""

from dataclasses import dataclass, fields
import math
import random
from typing import Callable
from genesis.habitats import HabitatMap
from genesis.lineage import LineageArchive


@dataclass(frozen=True)
class Traits:
    speed: float = 40.0
    sense: float = 90.0
    size: float = 5.0

    BOUNDS = {"speed": (18.0, 75.0), "sense": (35.0, 160.0), "size": (3.0, 9.0)}
    MUTATION = 0.06

    def mutated(self, rng: random.Random, strength: float = MUTATION) -> "Traits":
        values = {}
        for name, (low, high) in self.BOUNDS.items():
            value = getattr(self, name) * (1 + rng.uniform(-strength, strength))
            values[name] = max(low, min(high, value))
        return Traits(**values)


@dataclass(frozen=True)
class Config:
    width: float = 1100.0
    height: float = 760.0
    timestep: float = 1 / 30
    initial_population: int = 100
    population_cap: int = 300
    initial_food: int = 420
    food_cap: int = 650
    food_per_second: float = 20.0
    food_energy: float = 27.0
    initial_energy: float = 85.0
    energy_capacity: float = 180.0
    reproduction_threshold: float = 145.0
    offspring_energy: float = 65.0
    reproduction_cost: float = 6.0
    reproduction_cooldown: float = 12.0
    maturity_age: float = 8.0
    max_age: float = 180.0
    mutation_strength: float = Traits.MUTATION
    predator_enabled: bool = False
    initial_predators: int = 0
    predator_cap: int = 40
    predator_energy_multiplier: float = 2.5
    catch_efficiency: float = 0.65
    habitat_enabled: bool = False
    map_seed: int = 42

    def __post_init__(self):
        if type(self.habitat_enabled) is not bool or type(self.map_seed) is not int or not 0 <= self.map_seed <= 4294967295:
            raise ValueError("Habitat mode must be boolean and map seed an integer from 0 to 4294967295")
        if (type(self.predator_enabled) is not bool or type(self.initial_predators) is not int
                or not 0 <= self.initial_predators <= self.predator_cap
                or (not self.predator_enabled and self.initial_predators)
                or self.initial_population + self.initial_predators > self.population_cap):
            raise ValueError("Invalid predator configuration or combined population exceeds cap")
        if self.width < 30 or self.height < 30 or self.timestep <= 0:
            raise ValueError("World dimensions must be >= 30 and timestep must be positive")
        if not 0 <= self.initial_population <= self.population_cap:
            raise ValueError("Initial population must fit population cap")
        if not 0 <= self.initial_food <= self.food_cap or self.food_per_second < 0:
            raise ValueError("Invalid food configuration")
        if not 0 < self.offspring_energy + self.reproduction_cost <= self.reproduction_threshold <= self.energy_capacity:
            raise ValueError("Reproduction must be funded by the parent's energy")
        if not math.isfinite(self.mutation_strength) or not 0 <= self.mutation_strength <= 0.2:
            raise ValueError("Mutation strength must be between 0 and 0.2")


@dataclass
class Organism:
    id: int
    x: float
    y: float
    heading: float
    traits: Traits
    energy: float
    age: float = 0.0
    generation: int = 0
    parent_id: int | None = None
    cooldown: float = 0.0
    wander_turn: float = 0.0
    wander_timer: float = 0.0
    species: str = "prey"


@dataclass(frozen=True)
class Food:
    id: int
    x: float
    y: float


@dataclass(frozen=True)
class SimulationEvent:
    """Read-only facts from the latest tick, for optional presentation consumers."""

    kind: str
    organism_id: int
    x: float
    y: float
    traits: Traits


def energy_rate(traits: Traits) -> float:
    """Energy/second: basal metabolism, locomotion, body and sensing costs."""
    return (0.48 + 0.52 * (traits.speed / 40) ** 2 * (traits.size / 5)
            + 0.34 * (traits.size / 5) ** 2 + 0.30 * (traits.sense / 90) ** 2)


def habitat_energy_rate(traits, movement_multiplier):
    """Actual-speed locomotion with inverse-square drag in dense regions.

    Constant propulsion effort: moving slower through resistance is not an
    energy discount. Basal/body/sensing costs remain time-based and unchanged.
    """
    if movement_multiplier == 1:
        return energy_rate(traits)
    actual_speed = traits.speed * movement_multiplier
    locomotion = .52 * (actual_speed / 40) ** 2 * (traits.size / 5) / movement_multiplier ** 2
    rate = .48 + locomotion + .34 * (traits.size / 5) ** 2 + .30 * (traits.sense / 90) ** 2
    return max(energy_rate(traits), rate)  # No floating-point discount either.


class World:
    GRID_SIZE = 80.0

    def __init__(self, seed: int = 42, config: Config | None = None, habitats: HabitatMap | None = None):
        self.config = config or Config()
        self.seed = seed
        self.rng = random.Random(seed)
        self.organisms: dict[int, Organism] = {}
        self.food: dict[int, Food] = {}
        self._food_grid: dict[tuple[int, int], dict[int, Food]] = {}
        self._next_organism_id = 1
        self._next_food_id = 1
        self._food_credit = 0.0
        self.ticks = 0
        self.births = 0
        self.deaths = 0
        self.catches = 0
        self.events: list[SimulationEvent] = []
        self.lineage = LineageArchive()
        self._stepping = False
        c = self.config
        self.habitats = habitats or HabitatMap.generate(c.width, c.height, c.habitat_enabled, c.map_seed)
        for _ in range(c.initial_population):
            traits = Traits(self.rng.uniform(28, 52), self.rng.uniform(60, 120), self.rng.uniform(4, 6.5))
            self.add_organism(self.rng.uniform(10, c.width - 10),
                              self.rng.uniform(10, c.height - 10), traits)
        for _ in range(c.initial_food):
            self._spawn_food()
        for _ in range(c.initial_predators):
            traits = Traits(self.rng.uniform(50, 65), self.rng.uniform(100, 150), self.rng.uniform(5.5, 8))
            self.add_organism(self.rng.uniform(10, c.width - 10),
                              self.rng.uniform(10, c.height - 10), traits, species="predator")

    @property
    def time(self) -> float:
        return self.ticks * self.config.timestep

    @property
    def event_time(self):
        return (self.ticks + int(self._stepping)) * self.config.timestep

    def add_organism(self, x: float, y: float, traits: Traits | None = None,
                     energy: float | None = None, **kwargs) -> Organism:
        organism = Organism(self._next_organism_id, x, y, self.rng.uniform(-math.pi, math.pi),
                            traits or Traits(), self.config.initial_energy if energy is None else energy,
                            **kwargs)
        self.organisms[organism.id] = organism
        self._next_organism_id += 1
        self.lineage.record_birth(organism, self.event_time)
        return organism

    def _cell(self, x: float, y: float) -> tuple[int, int]:
        return math.floor(x / self.GRID_SIZE), math.floor(y / self.GRID_SIZE)

    def add_food(self, x: float, y: float) -> Food:
        food = Food(self._next_food_id, x, y)
        self._next_food_id += 1
        self.food[food.id] = food
        self._food_grid.setdefault(self._cell(x, y), {})[food.id] = food
        return food

    def _spawn_food(self):
        if self.config.habitat_enabled:
            self.add_food(*self.habitats.food_position(self.rng))
        else:
            self.add_food(self.rng.uniform(0, self.config.width), self.rng.uniform(0, self.config.height))

    def _remove_food(self, food: Food):
        del self.food[food.id]
        cell = self._cell(food.x, food.y)
        del self._food_grid[cell][food.id]
        if not self._food_grid[cell]:
            del self._food_grid[cell]

    def nearest_food(self, organism: Organism) -> Food | None:
        radius = organism.traits.sense
        x, y = organism.x, organism.y
        x0, y0 = self._cell(x - radius, y - radius)
        x1, y1 = self._cell(x + radius, y + radius)
        nearest = None
        best = radius * radius
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                for food in self._food_grid.get((cx, cy), {}).values():
                    distance = (food.x - x) ** 2 + (food.y - y) ** 2
                    if distance <= best:
                        if distance < best or nearest is None or food.id < nearest.id:
                            best, nearest = distance, food
        return nearest

    def _eat(self, organism: Organism, food: Food | None):
        if food and math.hypot(food.x - organism.x, food.y - organism.y) <= organism.traits.size + 3:
            organism.energy = min(self.config.energy_capacity, organism.energy + self.config.food_energy)
            self._remove_food(food)
            self.events.append(SimulationEvent("eat", organism.id, food.x, food.y, organism.traits))

    def _reproduce(self, parent: Organism) -> Organism | None:
        c = self.config
        if (len(self.organisms) >= c.population_cap or parent.energy < c.reproduction_threshold
                or parent.age < c.maturity_age or parent.cooldown > 0):
            return None
        if parent.species == "predator" and sum(o.species == "predator" for o in self.organisms.values()) >= c.predator_cap:
            return None
        traits = parent.traits.mutated(self.rng, c.mutation_strength)
        angle = self.rng.uniform(-math.pi, math.pi)
        offset = parent.traits.size + traits.size + 2
        x = max(traits.size, min(c.width - traits.size, parent.x + math.cos(angle) * offset))
        y = max(traits.size, min(c.height - traits.size, parent.y + math.sin(angle) * offset))
        parent.energy -= c.offspring_energy + c.reproduction_cost
        parent.cooldown = c.reproduction_cooldown
        child = self.add_organism(x, y, traits, c.offspring_energy, generation=parent.generation + 1,
                                  parent_id=parent.id, cooldown=c.reproduction_cooldown, species=parent.species)
        self.births += 1
        self.events.append(SimulationEvent("birth", child.id, child.x, child.y, child.traits))
        return child

    def step(self):
        """Advance exactly one fixed tick; newborns first act on the next tick."""
        c = self.config
        dt = c.timestep
        self.events.clear()
        self._stepping = True
        # Randomized, seeded order avoids permanently favoring older IDs at food.
        order = list(self.organisms)
        self.rng.shuffle(order)
        # The disabled path below retains the Phase 3 operations and RNG order.
        if c.predator_enabled:
            self._animal_grid = {}
            for animal in self.organisms.values():
                self._animal_grid.setdefault(self._cell(animal.x, animal.y), []).append(
                    (animal.id, animal.x, animal.y, animal.species))
        for oid in order:
            organism = self.organisms[oid]
            organism.age += dt
            organism.cooldown = max(0, organism.cooldown - dt)
            movement = (self.habitats.movement_multipliers[self.habitats.region_at(organism.x, organism.y)]
                        if c.habitat_enabled else 1.0)
            rate = habitat_energy_rate(organism.traits, movement) if c.habitat_enabled else energy_rate(organism.traits)
            organism.energy -= rate * dt
            if organism.species == "predator":
                organism.energy -= rate * dt * (c.predator_energy_multiplier - 1)
            if organism.energy <= 0 or organism.age >= c.max_age:
                self.lineage.record_death(oid, self.event_time, "energy" if organism.energy <= 0 else "age")
                self.events.append(SimulationEvent("death", organism.id, organism.x, organism.y, organism.traits))
                del self.organisms[oid]
                self.deaths += 1
                continue
            food = self.nearest_food(organism) if organism.species == "prey" else None
            target = self.nearest_animal(organism) if c.predator_enabled else None
            if target:
                _, tx, ty, _ = target
                dx, dy = tx - organism.x, ty - organism.y
                if organism.species == "prey":
                    dx, dy = -dx, -dy
                    # Escape dominates; food still gently influences steering.
                    if food:
                        length = max(1, math.hypot(dx, dy))
                        fl = max(1, math.hypot(food.x - organism.x, food.y - organism.y))
                        dx = dx / length + .15 * (food.x - organism.x) / fl
                        dy = dy / length + .15 * (food.y - organism.y) / fl
                desired = math.atan2(dy, dx)
                delta = (desired - organism.heading + math.pi) % (2 * math.pi) - math.pi
                organism.heading += max(-4 * dt, min(4 * dt, delta))
            elif food:
                desired = math.atan2(food.y - organism.y, food.x - organism.x)
                delta = (desired - organism.heading + math.pi) % (2 * math.pi) - math.pi
                organism.heading += max(-4 * dt, min(4 * dt, delta))
            else:
                organism.wander_timer -= dt
                if organism.wander_timer <= 0:
                    organism.wander_turn = self.rng.uniform(-1.8, 1.8)
                    organism.wander_timer = self.rng.uniform(0.4, 1.4)
                organism.heading += organism.wander_turn * dt
            speed = organism.traits.speed * movement if c.habitat_enabled else organism.traits.speed
            organism.x += math.cos(organism.heading) * speed * dt
            organism.y += math.sin(organism.heading) * speed * dt
            radius = organism.traits.size
            if organism.x < radius or organism.x > c.width - radius:
                organism.x = max(radius, min(c.width - radius, organism.x))
                organism.heading = math.pi - organism.heading
            if organism.y < radius or organism.y > c.height - radius:
                organism.y = max(radius, min(c.height - radius, organism.y))
                organism.heading = -organism.heading
            organism.heading = (organism.heading + math.pi) % (2 * math.pi) - math.pi
            self._eat(organism, food)
            if not c.predator_enabled:
                self._reproduce(organism)
        if c.predator_enabled:
            self.resolve_catches()
            for oid in order:
                if oid in self.organisms:
                    self._reproduce(self.organisms[oid])
        food_rate = c.food_per_second * self.habitats.mean_food_multiplier if c.habitat_enabled else c.food_per_second
        self._food_credit += food_rate * dt
        count = int(self._food_credit + 1e-9)
        self._food_credit = max(0.0, self._food_credit - count)
        for _ in range(min(count, c.food_cap - len(self.food))):
            self._spawn_food()
        self.ticks += 1
        self._stepping = False

    def nearest_animal(self, organism):
        """Perception uses start-of-tick positions, with distance/ID tie breaks."""
        radius = organism.traits.sense
        x0, y0 = self._cell(organism.x - radius, organism.y - radius)
        x1, y1 = self._cell(organism.x + radius, organism.y + radius)
        candidates = []
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                for target in self._animal_grid.get((cx, cy), ()):
                    oid, x, y, species = target
                    if species == organism.species or oid not in self.organisms:
                        continue
                    distance = (x - organism.x) ** 2 + (y - organism.y) ** 2
                    if distance <= radius ** 2:
                        candidates.append((distance, oid, target))
        return min(candidates)[2] if candidates else None

    def resolve_catches(self):
        """Ascending predator ID, nearest contact then prey ID; one catch per tick.

        Only remaining prey energy is transferred, with digestion loss and a cap.
        """
        prey = {o.id: o for o in self.organisms.values() if o.species == "prey"}
        # Post-movement contacts need a fresh grid, not the perception snapshot.
        # The grid only prunes impossible contacts; distance/ID ordering is unchanged.
        contact_grid = {}
        for animal in prey.values():
            contact_grid.setdefault(self._cell(animal.x, animal.y), []).append(animal)
        largest_prey = max((p.traits.size for p in prey.values()), default=0)
        for predator in sorted((o for o in self.organisms.values() if o.species == "predator"), key=lambda o: o.id):
            radius = predator.traits.size + largest_prey
            x0, y0 = self._cell(predator.x - radius, predator.y - radius)
            x1, y1 = self._cell(predator.x + radius, predator.y + radius)
            contacts = []
            for cx in range(x0, x1 + 1):
                for cy in range(y0, y1 + 1):
                    for p in contact_grid.get((cx, cy), ()):
                        if p.id not in prey:
                            continue
                        distance = (p.x - predator.x) ** 2 + (p.y - predator.y) ** 2
                        if distance <= (p.traits.size + predator.traits.size) ** 2:
                            contacts.append((distance, p.id))
            if contacts:
                victim = prey.pop(min(contacts)[1])
                predator.energy = min(self.config.energy_capacity, predator.energy + max(0, victim.energy) * self.config.catch_efficiency)
                del self.organisms[victim.id]
                self.lineage.record_death(victim.id, self.event_time, "caught")
                self.deaths += 1
                self.catches += 1
                self.events.append(SimulationEvent("catch", predator.id, victim.x, victim.y, predator.traits))

    def averages(self) -> Traits:
        count = len(self.organisms)
        if not count:
            return Traits(0, 0, 0)
        return Traits(*(sum(getattr(o.traits, field.name) for o in self.organisms.values()) / count
                        for field in fields(Traits)))


class SimulationClock:
    """Wall-time adapter shared by the app and tests. Speed only adds fixed ticks."""

    def __init__(self, world: World, on_step: Callable[[World], None] | None = None):
        self.world = world
        self.on_step = on_step
        self.speed = 1
        self.paused = False
        self.accumulator = 0.0

    def advance(self, wall_seconds: float) -> int:
        if wall_seconds < 0:
            raise ValueError("Elapsed time cannot be negative")
        if self.paused or not self.world.organisms:
            return 0
        if self.speed not in (1, 2, 4):
            raise ValueError("Supported speeds are 1, 2 and 4")
        self.accumulator += wall_seconds * self.speed
        steps = 0
        while self.accumulator + 1e-10 >= self.world.config.timestep:
            self.world.step()
            if self.on_step is not None:
                self.on_step(self.world)
            self.accumulator = max(0.0, self.accumulator - self.world.config.timestep)
            steps += 1
            if not self.world.organisms:
                self.accumulator = 0.0
                break
        return steps
