"""Experiment configuration, bounded tick-sampled history and CSV, without UI."""

from collections import deque
import csv
from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path

from . import __version__
from .simulation import Config, Traits, World
from .habitats import occupancy, REGIONS
from .environment import DEFAULTS, validate_settings


@dataclass(frozen=True)
class ExperimentSettings:
    seed: int = 42
    initial_population: int = 100
    food_per_second: float = 20.0
    mutation_strength: float = 0.06
    predator_enabled: bool = False
    initial_predators: int = 0
    habitat_enabled: bool = False
    map_seed: int = 42
    seasons_enabled: bool = False
    season_length: int = 120
    droughts_enabled: bool = False
    drought_duration: int = 15
    drought_interval: int = 90

    def __post_init__(self):
        validate_settings(self)
        if type(self.habitat_enabled) is not bool or type(self.map_seed) is not int or not 0 <= self.map_seed <= 4294967295:
            raise ValueError("Habitats: mode must be off/on and map seed an integer from 0 to 4294967295.")
        if (type(self.predator_enabled) is not bool or type(self.initial_predators) is not int
                or not 0 <= self.initial_predators <= 40
                or (not self.predator_enabled and self.initial_predators != 0)):
            raise ValueError("Predators: enable mode and choose 0 to 40; disabled mode requires 0.")
        for label, value, low, high in (("Seed", self.seed, 0, 4294967295),
                                        ("Starting population", self.initial_population, 1, 300)):
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{label} must be a whole number from {low} to {high}.")
        for label, value, high in (("Food regeneration", self.food_per_second, 80),
                                   ("Mutation strength", self.mutation_strength, 0.2)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= high:
                raise ValueError(f"{label} must be a finite number from 0 to {high}.")
        if self.initial_population + self.initial_predators > 300:
            raise ValueError("Starting prey plus predators must not exceed 300.")

    def config(self) -> Config:
        return replace(Config(), initial_population=self.initial_population,
                       food_per_second=self.food_per_second, mutation_strength=self.mutation_strength,
                       predator_enabled=self.predator_enabled, initial_predators=self.initial_predators,
                       habitat_enabled=self.habitat_enabled, map_seed=self.map_seed,
                       **{k: getattr(self, k) for k in DEFAULTS})

    def text_values(self) -> dict[str, str]:
        return {"seed": str(self.seed), "initial_population": str(self.initial_population),
                "food_per_second": f"{self.food_per_second:g}",
                "mutation_percent": f"{self.mutation_strength * 100:g}",
                "predator_enabled": "1" if self.predator_enabled else "0",
                "initial_predators": str(self.initial_predators),
                "habitat_enabled": "1" if self.habitat_enabled else "0", "map_seed": str(self.map_seed),
                **{k: str(int(getattr(self, k))) for k in DEFAULTS}}

    @classmethod
    def from_text(cls, values: dict[str, str]) -> "ExperimentSettings":
        parsed = {}
        labels = {"seed": "Seed", "initial_population": "Starting population",
                  "food_per_second": "Food regeneration", "mutation_percent": "Mutation percent"}
        for key, label in labels.items():
            try:
                parsed[key] = (int if key in ("seed", "initial_population") else float)(values[key].strip())
            except (ValueError, KeyError, TypeError):
                raise ValueError(f"{label}: enter a {'whole number' if key in ('seed', 'initial_population') else 'number'}.") from None
        if not math.isfinite(parsed["mutation_percent"]) or not 0 <= parsed["mutation_percent"] <= 20:
            raise ValueError("Mutation percent must be between 0 and 20.")
        mode = values.get("predator_enabled", "0").strip()
        if mode not in ("0", "1"):
            raise ValueError("Predator mode: enter 0 (off) or 1 (on).")
        try:
            predators = int(values.get("initial_predators", "0").strip())
        except ValueError:
            raise ValueError("Starting predators: enter a whole number from 0 to 40.") from None
        habitat_mode = values.get("habitat_enabled", "0").strip()
        if habitat_mode not in ("0", "1"):
            raise ValueError("Habitat mode: enter 0 (uniform) or 1 (patchwork).")
        try:
            map_seed = int(values.get("map_seed", "42").strip())
        except ValueError:
            raise ValueError("Map seed: enter a whole number from 0 to 4294967295.") from None
        environment = {}
        for key, default in DEFAULTS.items():
            try:
                value = int(values.get(key, str(int(default))))
                if type(default) is bool and value not in (0, 1):
                    raise ValueError()
                environment[key] = bool(value) if type(default) is bool else value
            except (ValueError, TypeError):
                raise ValueError(f"{key.replace('_', ' ').title()}: enter a valid whole number.") from None
        return cls(parsed["seed"], parsed["initial_population"], parsed["food_per_second"], parsed["mutation_percent"] / 100,
                   mode == "1", predators, habitat_mode == "1", map_seed, **environment)


@dataclass(frozen=True)
class Statistics:
    population: int
    births: int
    deaths: int
    food: int
    average_speed: float | None
    average_sense: float | None
    average_size: float | None
    highest_generation: int | None
    prey_population: int = 0
    predator_population: int = 0
    catches: int = 0
    prey_average_speed: float | None = None
    prey_average_sense: float | None = None
    prey_average_size: float | None = None
    predator_average_speed: float | None = None
    predator_average_sense: float | None = None
    predator_average_size: float | None = None
    open_water_prey: int = 0
    open_water_predator: int = 0
    open_water_food: int = 0
    garden_prey: int = 0
    garden_predator: int = 0
    garden_food: int = 0
    dense_prey: int = 0
    dense_predator: int = 0
    dense_food: int = 0
    season_multiplier: float = 1.0
    drought_multiplier: float = 1.0
    environment_multiplier: float = 1.0


def statistics(world: World) -> Statistics:
    organisms = list(world.organisms.values())
    count = len(organisms)
    averages = [sum(getattr(o.traits, name) for o in organisms) / count if count else None
                for name in Traits.BOUNDS]
    groups = [[o for o in organisms if o.species == species] for species in ("prey", "predator")]
    means = [sum(getattr(o.traits, name) for o in group) / len(group) if group else None
             for group in groups for name in Traits.BOUNDS]
    return Statistics(count, world.births, world.deaths, len(world.food), *averages,
                      max((o.generation for o in organisms), default=None),
                      len(groups[0]), len(groups[1]), world.catches, *means, **occupancy(world),
                      season_multiplier=world.environment.seasonal_multiplier,
                      drought_multiplier=world.environment.drought_multiplier,
                      environment_multiplier=world.environment.multiplier)


def distributions(world: World, bins: int = 10, species: str | None = None) -> dict[str, tuple[int, ...]]:
    if type(bins) is not int or bins < 1:
        raise ValueError("Histogram bin count must be a positive integer")
    result = {}
    for name, (low, high) in Traits.BOUNDS.items():
        counts = [0] * bins
        for organism in world.organisms.values():
            if species is not None and organism.species != species:
                continue
            index = int((getattr(organism.traits, name) - low) / (high - low) * bins)
            counts[max(0, min(bins - 1, index))] += 1
        result[name] = tuple(counts)
    return result


@dataclass(frozen=True)
class Sample:
    tick: int
    simulation_seconds: float
    sample_kind: str
    stats: Statistics


class History:
    """Initial + every 30 ticks (one second), plus an explicit terminal sample.

    Observe after EVERY step, even when several ticks occur in one render frame.
    Bounded to 3,601 rows by default; baseline stays available after eviction.
    """

    def __init__(self, world: World, settings: ExperimentSettings, capacity: int = 3601, interval_ticks: int = 30):
        if type(capacity) is not int or capacity < 2 or type(interval_ticks) is not int or interval_ticks < 1:
            raise ValueError("History requires capacity >= 2 and interval_ticks >= 1")
        self.settings = settings
        self.config = world.config
        self.habitats = world.habitats
        self.interval_ticks = interval_ticks
        self.samples: deque[Sample] = deque(maxlen=capacity)
        self.baseline = statistics(world)
        self.dropped_samples = 0
        self.revision = 0
        self._last_seen_tick = world.ticks
        self._append(world, "initial")

    def _append(self, world, kind):
        if len(self.samples) == self.samples.maxlen:
            self.dropped_samples += 1
        self.samples.append(Sample(world.ticks, world.time, kind, statistics(world)))
        self.revision += 1

    def on_step(self, world):
        if world.ticks <= self._last_seen_tick:
            return
        self._last_seen_tick = world.ticks
        if not world.organisms:
            # Capture the final zero even when extinction falls between samples.
            if self.samples[-1].stats.population:
                self._append(world, "extinction")
        elif world.ticks % self.interval_ticks == 0:
            self._append(world, "periodic")

    def export_csv(self, path: str | Path) -> Path:
        """Export retained rows, full rules and seed. Never overwrite a file."""
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {"genesis_version": __version__, "seed": self.settings.seed,
                    "environment_seed": self.settings.seed ^ 0xE17A5EED,
                    "season_min_multiplier": .5, "season_max_multiplier": 1.5,
                    "active_drought_multiplier": .25,
                    **{f"config_{key}": value for key, value in asdict(self.config).items()},
                    **{f"habitat_{region}_food_multiplier": self.habitats.food_multipliers[i] for i, region in enumerate(REGIONS)},
                    **{f"habitat_{region}_movement_multiplier": self.habitats.movement_multipliers[i] for i, region in enumerate(REGIONS)},
                    "sampling_interval_ticks": self.interval_ticks,
                    "history_capacity": self.samples.maxlen, "dropped_samples": self.dropped_samples,
                    **{f"starting_{name}": value for name, value in asdict(self.baseline).items()
                       if "average_" in name}}
        fields = ["tick", "simulation_seconds", "sample_kind", *Statistics.__dataclass_fields__, *metadata]
        with path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for sample in self.samples:
                writer.writerow({"tick": sample.tick, "simulation_seconds": sample.simulation_seconds,
                                 "sample_kind": sample.sample_kind, **asdict(sample.stats), **metadata})
        return path
