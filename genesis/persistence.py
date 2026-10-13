"""Versioned, validated JSON checkpoints. No pickle, graphics, or active RNG use."""

from dataclasses import asdict, dataclass
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile

from . import __version__
from .diagnostics import Diagnostics
from .observatory import ExperimentSettings, History, Sample, Statistics, statistics
from .presets import preset_name
from .simulation import Food, Organism, SimulationClock, Traits, World
from .habitats import HabitatMap, REGIONS
from .lineage import LineageArchive, LineageRecord, ARCHIVE_LIMIT, CAUSES
from .environment import Environment, EnvironmentEvent, DEFAULTS, STAT_DEFAULTS, HISTORY_LIMIT, SEASONS


FORMAT = "genesis-world"
VERSION = 7
MAX_BYTES = 16 * 1024 * 1024
MAX_COUNT = 10**12


class SaveError(ValueError):
    """A readable persistence failure safe to show in the application."""


@dataclass
class LoadedWorld:
    settings: ExperimentSettings
    world: World
    clock: SimulationClock
    history: History
    selected_id: int | None


def document(world, clock, history, selected_id=None, *, defer_archives=False):
    """Copy a coherent between-ticks checkpoint without mutating any inputs."""
    return {
        "ecology": {"handling": {str(k): v for k,v in world.handling.items()}},
        "format": FORMAT, "version": VERSION, "application_version": __version__,
        "settings": asdict(history.settings), "preset": preset_name(history.settings),
        "config": asdict(world.config), "habitats": world.habitats.document(),
        "lineage": world.lineage.document(defer_records=defer_archives),
        "environment": world.environment.document(),
        "diagnostics": world.diagnostics.document(),
        "world": {"ticks": world.ticks, "births": world.births, "deaths": world.deaths, "catches": world.catches,
                  "next_organism_id": world._next_organism_id, "next_food_id": world._next_food_id,
                  "food_credit": world._food_credit, "rng_state": world.rng.getstate(),
                  "organisms": [asdict(o) for o in world.organisms.values()],
                  "food": [asdict(f) for f in world.food.values()]},
        "clock": {"speed": clock.speed, "paused": clock.paused, "accumulator": clock.accumulator},
        "history": {"capacity": history.samples.maxlen, "interval_ticks": history.interval_ticks,
                    "dropped_samples": history.dropped_samples, "revision": history.revision,
                    "last_seen_tick": history._last_seen_tick, "baseline": asdict(history.baseline),
                    "samples": list(history.samples) if defer_archives else [asdict(sample) for sample in history.samples]},
        "selection": selected_id if selected_id in world.organisms else None,
    }


def require(condition, message):
    if not condition:
        raise SaveError(message)


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names), f"Invalid {label}: missing or unexpected fields.")
    return value


def integer(value, low, high, label):
    require(type(value) is int and low <= value <= high, f"Invalid {label}: expected integer {low}–{high}.")
    return value


def number(value, low, high, label):
    require(type(value) in (int, float) and low <= value <= high and math.isfinite(value),
            f"Invalid {label}: expected finite number {low}–{high}.")
    return value


def read_stats(raw, config):
    fields(raw, Statistics.__dataclass_fields__, "statistics")
    number(raw["season_multiplier"], .5, 1.5, "season multiplier")
    require(config.seasons_enabled or raw["season_multiplier"] == 1, "Season multiplier in disabled world.")
    require(type(raw["drought_multiplier"]) in (int, float) and raw["drought_multiplier"] in (.25, 1.0), "Invalid drought multiplier.")
    require(config.droughts_enabled or raw["drought_multiplier"] == 1, "Drought in disabled world.")
    number(raw["environment_multiplier"], .125, 1.5, "environment multiplier")
    require(raw["environment_multiplier"] == raw["season_multiplier"]*raw["drought_multiplier"], "Combined environment multiplier disagrees.")
    population = integer(raw["population"], 0, config.population_cap, "sample population")
    births = integer(raw["births"], 0, MAX_COUNT, "sample births")
    deaths = integer(raw["deaths"], 0, MAX_COUNT, "sample deaths")
    require(population == config.initial_population + config.initial_predators + births - deaths, "Sample population accounting is inconsistent.")
    prey = integer(raw["prey_population"], 0, config.population_cap, "prey population")
    predators = integer(raw["predator_population"], 0, config.predator_cap, "predator population")
    catches = integer(raw["catches"], 0, deaths, "catches")
    require(prey + predators == population, "Species populations disagree with total.")
    require(config.predator_enabled or (predators == 0 and catches == 0), "Predators in disabled experiment.")
    for species, count in (("prey", prey), ("predator", predators)):
        for name, bounds in Traits.BOUNDS.items():
            value = raw[f"{species}_average_{name}"]
            if count:
                number(value, *bounds, f"{species} average {name}")
            else:
                require(value is None, "Empty species must have null trait averages.")
    integer(raw["food"], 0, config.food_cap, "sample food")
    for kind, total in (("prey", prey), ("predator", predators), ("food", raw["food"])):
        values = [integer(raw[f"{region}_{kind}"], 0, total, "regional occupancy") for region in REGIONS]
        require(sum(values) == total, "Regional occupancy totals are inconsistent.")
        require(config.habitat_enabled or values == [total, 0, 0], "Non-uniform occupancy in uniform world.")
    for name, bounds in Traits.BOUNDS.items():
        value = raw[f"average_{name}"]
        if population:
            number(value, *bounds, f"average {name}")
        else:
            require(value is None, "Empty populations must have null trait averages.")
    if population:
        integer(raw["highest_generation"], 0, births, "highest generation")
    else:
        require(raw["highest_generation"] is None, "Empty populations must have null generation.")
    return Statistics(**raw)


def migrate_v1(data):
    """Expand only the exact legacy schema; normal validation checks all values."""
    data = deepcopy(data)
    settings_keys = set(ExperimentSettings.__dataclass_fields__) - {"predator_enabled", "initial_predators", "habitat_enabled", "map_seed"} - set(DEFAULTS)
    fields(data.get("settings"), settings_keys, "version 1 settings")
    additions = {"predator_enabled": False, "initial_predators": 0,
                 "predator_cap": 40, "predator_energy_multiplier": 2.5, "catch_efficiency": .65}
    fields(data.get("config"), set(asdict(ExperimentSettings().config())) - set(additions) - {"habitat_enabled", "map_seed"} - set(DEFAULTS), "version 1 configuration")
    data["settings"].update(predator_enabled=False, initial_predators=0)
    data["config"].update(additions)
    raw = fields(data.get("world"), ("ticks", "births", "deaths", "next_organism_id", "next_food_id",
                                    "food_credit", "rng_state", "organisms", "food"), "version 1 world")
    require(isinstance(raw["organisms"], list), "Invalid version 1 organisms.")
    for organism in raw["organisms"]:
        fields(organism, set(Organism.__dataclass_fields__) - {"species"}, "version 1 organism")
        organism["species"] = "prey"
    raw["catches"] = 0
    history = fields(data.get("history"), ("capacity", "interval_ticks", "dropped_samples", "revision", "last_seen_tick", "baseline", "samples"), "version 1 history")
    require(isinstance(history["samples"], list), "Invalid version 1 history samples.")
    stats_rows = [history["baseline"]]
    for sample in history["samples"]:
        fields(sample, Sample.__dataclass_fields__, "version 1 sample")
        stats_rows.append(sample["stats"])
    for stats in stats_rows:
        fields(stats, ("population", "births", "deaths", "food", "average_speed", "average_sense", "average_size", "highest_generation"), "version 1 statistics")
        stats.update(prey_population=stats["population"], predator_population=0, catches=0)
        for name in Traits.BOUNDS:
            stats[f"prey_average_{name}"] = stats[f"average_{name}"]
            stats[f"predator_average_{name}"] = None
    data["version"] = 2
    return data


def migrate_v2(data):
    """Legacy history belongs entirely to open water; never infer a new map."""
    data = deepcopy(data)
    fields(data, ("format", "version", "application_version", "settings", "preset", "config", "world", "clock", "history", "selection"), "version 2 save")
    fields(data["settings"], set(ExperimentSettings.__dataclass_fields__) - {"habitat_enabled", "map_seed"} - set(DEFAULTS), "version 2 settings")
    fields(data["config"], set(asdict(ExperimentSettings().config())) - {"habitat_enabled", "map_seed"} - set(DEFAULTS), "version 2 config")
    data["settings"].update(habitat_enabled=False, map_seed=42)
    data["config"].update(habitat_enabled=False, map_seed=42)
    data["habitats"] = HabitatMap.generate(1100, 760).document()
    history = fields(data["history"], ("capacity", "interval_ticks", "dropped_samples", "revision", "last_seen_tick", "baseline", "samples"), "version 2 history")
    require(isinstance(history["samples"], list), "Invalid version 2 samples.")
    rows = [history["baseline"]]
    for sample in history["samples"]:
        fields(sample, Sample.__dataclass_fields__, "version 2 sample")
        rows.append(sample["stats"])
    regional = {f"{region}_{kind}" for region in REGIONS for kind in ("prey", "predator", "food")}
    for stats in rows:
        fields(stats, set(Statistics.__dataclass_fields__) - regional - set(STAT_DEFAULTS), "version 2 statistics")
        for region in REGIONS:
            for kind, total in (("prey", stats["prey_population"]), ("predator", stats["predator_population"]), ("food", stats["food"])):
                stats[f"{region}_{kind}"] = total if region == "open_water" else 0
    data["version"] = 3
    return data


def read_lineage(raw, world):
    fields(raw, ("capacity", "pruned_count", "legacy_unavailable", "records"), "lineage archive")
    capacity = integer(raw["capacity"], world.config.population_cap, ARCHIVE_LIMIT, "lineage capacity")
    archive = LineageArchive(capacity)
    archive.pruned_count = integer(raw["pruned_count"], 0, world.deaths, "pruned record count")
    archive.legacy_unavailable = integer(raw["legacy_unavailable"], 0, world.deaths, "legacy unavailable count")
    rows = raw["records"]
    require(isinstance(rows, list) and len(rows) <= capacity, "Invalid lineage records or archive capacity exceeded.")
    require(len(rows)+archive.pruned_count+archive.legacy_unavailable == world._next_organism_id-1,
            "Lineage archive accounting disagrees with organism IDs.")
    previous_id = 0
    founders = world.config.initial_population + world.config.initial_predators
    for row in rows:
        fields(row, LineageRecord.__dataclass_fields__, "lineage record")
        oid = integer(row["id"], previous_id+1, world._next_organism_id-1, "ordered lineage ID")
        previous_id = oid
        require(row["species"] in ("prey", "predator"), "Invalid lineage species.")
        require(world.config.predator_enabled or row["species"] == "prey", "Predator lineage in disabled world.")
        generation = integer(row["generation"], 0, world.births, "lineage generation")
        if oid <= founders:
            require(row["parent_id"] is None and generation == 0, "Invalid founder record.")
            require(row["species"] == ("prey" if oid <= world.config.initial_population else "predator"), "Invalid founder record species.")
        else:
            integer(row["parent_id"], 1, oid-1, "lineage parent ID")
            require(generation > 0, "Invalid offspring generation.")
        fields(row["traits"], Traits.BOUNDS, "recorded traits")
        traits = Traits(**{key: number(row["traits"][key], *bounds, "recorded "+key) for key, bounds in Traits.BOUNDS.items()})
        observed = number(row["recorded_time"], 0, world.time, "recording time")
        require(row["origin"] in ("birth", "legacy_snapshot"), "Invalid lineage record origin.")
        if row["origin"] == "birth":
            born = number(row["birth_time"], 0, world.time, "birth time")
            require(born == observed, "Birth record observation time disagrees.")
            require(oid > founders or born == 0, "Founders must be recorded at time zero.")
        else:
            require(row["birth_time"] is None, "Legacy birth time must remain unknown.")
        if row["death_time"] is None:
            require(row["death_cause"] is None and oid in world.organisms, "Living archive record is absent from world.")
        else:
            number(row["death_time"], observed, world.time, "death time")
            require(row["death_cause"] in CAUSES and oid not in world.organisms, "Invalid death record or living/dead contradiction.")
            require(row["death_cause"] != "caught" or (row["species"] == "prey" and world.config.predator_enabled),
                    "Only prey in predator mode can be caught.")
        record = LineageRecord(**{**row, "traits": traits})
        archive._records[oid] = record
    for oid, organism in world.organisms.items():
        record = archive.records.get(oid)
        require(record is not None, "Living organism has no lineage record.")
        for key in ("species", "parent_id", "generation", "traits"):
            require(getattr(record, key) == getattr(organism, key), "Living organism and birth record disagree.")
    for record in archive.records.values():
        parent = archive.records.get(record.parent_id)
        if parent:
            require(parent.species == record.species and parent.generation+1 == record.generation,
                    "Lineage parent species or generation disagrees.")
            if record.birth_time is not None:
                require(parent.birth_time is None or parent.birth_time <= record.birth_time,
                        "Child was born before its parent.")
                require(parent.death_time is None or record.birth_time <= parent.death_time,
                        "Child was born after its parent died.")
    require(sum(r.death_cause == "caught" for r in archive.records.values()) <= world.catches,
            "Recorded catches exceed the world's catch counter.")
    return archive


def read_environment(raw, world):
    env = Environment(world.seed, world.config)
    fields(raw, env.document(), "environment")
    integer(raw["seed"], env.seed, env.seed, "environment seed")
    env.ticks = integer(raw["ticks"], world.ticks, world.ticks, "environment tick")
    integer(raw["cycle_position"], env.cycle_position, env.cycle_position, "cycle position")
    require(raw["next_season"] == env.next_season and (raw["next_season"] is None or type(raw["next_season"]) is int), "Invalid next season transition.")
    integer(raw["history_limit"], HISTORY_LIMIT, HISTORY_LIMIT, "environment history limit")
    maximum = 0 if world.ticks < env.interval_ticks else 1+(world.ticks-env.interval_ticks)//(env.interval_ticks+env.duration_ticks)
    count = integer(raw["drought_count"], 0, maximum, "drought count")
    env.drought_count = count
    env.drought_start, env.drought_end, env.next_drought = raw["drought_start"], raw["drought_end"], raw["next_drought"]
    if not world.config.droughts_enabled:
        require(count == 0 and env.drought_start is None and env.drought_end is None and env.next_drought is None,
                "Drought state in disabled world.")
    elif env.drought_end is not None:
        integer(env.drought_start, max(env.interval_ticks, world.ticks-env.duration_ticks+1), world.ticks, "drought start")
        integer(env.drought_end, env.drought_start+env.duration_ticks, env.drought_start+env.duration_ticks, "drought end")
        require(env.next_drought is None and count > 0, "Conflicting drought schedule.")
    else:
        require(env.drought_start is None, "Inactive drought has a start time.")
        integer(env.next_drought, world.ticks+1, world.ticks+2*env.interval_ticks, "next drought")
    rng = raw["rng_state"]
    require(isinstance(rng, (list, tuple)) and len(rng) == 3 and type(rng[0]) is int and rng[0] == 3 and rng[2] is None, "Invalid environment RNG header.")
    require(isinstance(rng[1], (list, tuple)) and len(rng[1]) == 625, "Invalid environment RNG size.")
    for word in rng[1][:-1]:
        integer(word, 0, 2**32-1, "environment RNG word")
    integer(rng[1][-1], 0, 624, "environment RNG index")
    if not world.config.droughts_enabled:
        require(tuple(rng[1]) == env.rng.getstate()[1], "Unused environment RNG must retain its initial state.")
    env.rng.setstate((3, tuple(rng[1]), None))
    total = (world.ticks*4//env.cycle_ticks+1 if world.config.seasons_enabled else 0)+2*count-int(env.drought_end is not None)
    env.total_events = integer(raw["total_events"], total, total, "environment event total")
    rows = raw["history"]
    require(isinstance(rows, list) and len(rows) == min(total, HISTORY_LIMIT), "Environment history count disagrees.")
    env.history.clear()
    previous = (-1, -1)
    last_drought = None
    for row in rows:
        fields(row, EnvironmentEvent.__dataclass_fields__, "environment event")
        tick = integer(row["tick"], 0, world.ticks, "environment event tick")
        require(row["kind"] in ("season", "drought_start", "drought_end"), "Unknown environment event.")
        order = 0 if row["kind"] == "season" else 1
        require((tick, order) > previous, "Environment events out of order or duplicated.")
        previous = (tick, order)
        require(type(row["drought"]) is bool, "Invalid event drought flag.")
        require(world.config.droughts_enabled or not row["drought"], "Drought event in disabled world.")
        phase = (tick % env.cycle_ticks)*4//env.cycle_ticks
        require(row["season"] == (SEASONS[phase] if world.config.seasons_enabled else "Steady"), "Event season disagrees with cycle.")
        if row["kind"] == "season":
            require(world.config.seasons_enabled and (tick == 0 or tick*4//env.cycle_ticks != (tick-1)*4//env.cycle_ticks), "Invalid season boundary event.")
        else:
            require(world.config.droughts_enabled and row["drought"] == (row["kind"] == "drought_start"), "Invalid drought event state.")
            if last_drought:
                last_tick, last_kind = last_drought
                require(row["kind"] != last_kind, "Drought history must alternate start/end.")
                if row["kind"] == "drought_end":
                    require(tick-last_tick == env.duration_ticks, "Historical drought duration disagrees.")
                else:
                    require(env.interval_ticks <= tick-last_tick <= 2*env.interval_ticks, "Historical drought interval out of bounds.")
            last_drought = (tick, row["kind"])
        expected = env.seasonal_at(tick)*(.25 if row["drought"] else 1)
        number(row["multiplier"], expected, expected, "event multiplier")
        env.history.append(EnvironmentEvent(**row))
    if count:
        require(last_drought is not None, "Recent drought transition missing.")
        if env.drought_end is not None:
            require(last_drought == (env.drought_start, "drought_start"), "Active drought disagrees with history.")
        else:
            require(last_drought[1] == "drought_end" and env.interval_ticks <= env.next_drought-last_drought[0] <= 2*env.interval_ticks, "Next drought disagrees with history.")
    elif world.config.droughts_enabled:
        require(env.interval_ticks <= env.next_drought <= 2*env.interval_ticks, "Initial drought interval out of bounds.")
    seasons = [e for e in env.history if e.kind == "season"]
    if world.config.seasons_enabled:
        quarter = world.ticks*4//env.cycle_ticks
        expected = [math.ceil(q*env.cycle_ticks/4) for q in range(quarter-len(seasons)+1, quarter+1)]
        require(seasons and [e.tick for e in seasons] == expected, "Retained season boundaries are missing or stale.")
    # A season event at the same tick as a drought transition records the new state.
    drought_rows = {e.tick: e.drought for e in env.history if e.kind != "season"}
    active = None
    for e in env.history:
        if e.tick in drought_rows:
            active = drought_rows[e.tick]
        if active is not None:
            require(e.drought == active, "Event drought state disagrees with recorded transitions.")
    return env


def restore(data) -> LoadedWorld:
    """Validate all content before returning an isolated, paused candidate world."""
    require(isinstance(data, dict), "Save must contain a JSON object.")
    require(data.get("format") == FORMAT, "This is not a GENESIS world file.")
    if type(data.get("version")) is int and 1 <= data["version"] <= 6:
        data = deepcopy(data)
        for key in ("settings", "config"):
            require(isinstance(data.get(key), dict) and "rules_version" not in data[key], "Invalid legacy rules settings.")
            data[key]["rules_version"] = 1
    if type(data.get("version")) is int and data["version"] == 1:
        data = migrate_v1(data)
    if type(data.get("version")) is int and data["version"] == 2:
        data = migrate_v2(data)
    require(type(data.get("version")) is int and data["version"] in (3, 4, 5, 6, VERSION),
            f"Unsupported save version {data.get('version')!r}; supported versions are 1 through {VERSION}.")
    legacy_rules = data["version"] < 7
    legacy_lineage = data["version"] == 3
    legacy_environment = data["version"] < 5
    legacy_diagnostics = data["version"] < 6
    fields(data, ("format", "version", "application_version", "settings", "preset", "config", "habitats", "world", "clock", "history", "selection") + (() if legacy_lineage else ("lineage",)) + (() if legacy_environment else ("environment",)) + (() if legacy_diagnostics else ("diagnostics",)) + (() if legacy_rules else ("ecology",)), "save")
    if legacy_rules:
        data = deepcopy(data)
        data["ecology"] = {"handling": {}}
    if legacy_environment:
        data = deepcopy(data)
        for key, schema in (("settings", ExperimentSettings.__dataclass_fields__), ("config", asdict(ExperimentSettings().config()))):
            fields(data[key], set(schema)-set(DEFAULTS), "legacy "+key)
            data[key].update(DEFAULTS)
        hist = fields(data["history"], ("capacity", "interval_ticks", "dropped_samples", "revision", "last_seen_tick", "baseline", "samples"), "legacy history")
        require(isinstance(hist["samples"], list), "Invalid legacy samples.")
        for row in [hist["baseline"]]+[fields(s, Sample.__dataclass_fields__, "legacy sample")["stats"] for s in hist["samples"]]:
            fields(row, set(Statistics.__dataclass_fields__)-set(STAT_DEFAULTS), "legacy statistics")
            row.update(STAT_DEFAULTS)
    require(isinstance(data["application_version"], str), "Invalid application version.")
    fields(data["settings"], ExperimentSettings.__dataclass_fields__, "settings")
    try:
        settings = ExperimentSettings(**data["settings"])
    except (ValueError, TypeError) as error:
        raise SaveError(f"Invalid experiment settings: {error}") from error
    config = settings.config()
    fields(data["config"], asdict(config), "configuration")
    for name, expected in asdict(config).items():
        value = data["config"][name]
        if type(expected) is bool:
            require(type(value) is bool and value == expected, f"Invalid configuration {name}.")
            continue
        number(value, expected, expected, f"configuration {name}")
        if type(expected) is int:
            integer(value, expected, expected, f"configuration {name}")
    require(data["preset"] == preset_name(settings) or
            (legacy_diagnostics and data["preset"] == "Custom" and preset_name(settings) == "Coexistence"),
            "Preset label does not match experiment settings.")
    try:
        habitats = HabitatMap.from_document(data["habitats"], config.width, config.height, config.habitat_enabled)
    except (ValueError, TypeError) as error:
        raise SaveError(f"Invalid habitat map: {error}") from error
    raw = fields(data["world"], ("ticks", "births", "deaths", "catches", "next_organism_id", "next_food_id", "food_credit", "rng_state", "organisms", "food"), "world")
    ticks = integer(raw["ticks"], 0, MAX_COUNT, "tick")
    births = integer(raw["births"], 0, MAX_COUNT, "births")
    deaths = integer(raw["deaths"], 0, MAX_COUNT, "deaths")
    catches = integer(raw["catches"], 0, deaths, "catches")
    require(config.predator_enabled or catches == 0, "Catches in disabled experiment.")
    founders = config.initial_population + config.initial_predators
    next_id = integer(raw["next_organism_id"], 1, MAX_COUNT, "organism ID counter")
    require(next_id == founders + births + 1, "Organism ID counter and births disagree.")
    next_food = integer(raw["next_food_id"], config.initial_food + 1, MAX_COUNT, "food ID counter")
    credit = number(raw["food_credit"], 0, 1, "fractional food credit")
    require(credit < 1, "Fractional food credit must be less than one.")
    require(isinstance(raw["organisms"], list) and len(raw["organisms"]) <= config.population_cap, "Invalid organism list or population cap exceeded.")
    require(isinstance(raw["food"], list) and len(raw["food"]) <= config.food_cap, "Invalid food list or food cap exceeded.")
    # This temporary founder world validates comparisons without touching the
    # active world. Its private RNG is overwritten before any resumed step.
    world = World(settings.seed, config, habitats=habitats)
    founder_stats = statistics(world)
    world.organisms.clear()
    world.food.clear()
    world._food_grid.clear()
    for item in raw["organisms"]:
        fields(item, Organism.__dataclass_fields__, "organism")
        oid = integer(item["id"], 1, next_id - 1, "organism ID")
        require(item["species"] in ("prey", "predator"), "Invalid organism species.")
        require(config.predator_enabled or item["species"] == "prey", "Predator in disabled world.")
        if oid <= founders:
            require(item["species"] == ("prey" if oid <= config.initial_population else "predator"), "Invalid founder species.")
        require(oid not in world.organisms, "Duplicate organism ID.")
        fields(item["traits"], Traits.BOUNDS, "traits")
        traits = Traits(**{name: number(item["traits"][name], *bounds, name) for name, bounds in Traits.BOUNDS.items()})
        number(item["x"], traits.size, config.width - traits.size, "organism x")
        number(item["y"], traits.size, config.height - traits.size, "organism y")
        number(item["heading"], -math.pi, math.pi, "heading")
        number(item["energy"], 0, config.energy_capacity, "energy")
        maximum_age = world.maximum_age(item["species"])
        number(item["age"], 0, maximum_age, "age")
        require(item["energy"] > 0 and item["age"] < maximum_age, "Saved living organism is already dead.")
        number(item["cooldown"], 0, 45 if config.rules_version == 2 and item["species"] == "predator" else config.reproduction_cooldown, "reproduction cooldown")
        number(item["wander_turn"], -1.8, 1.8, "wander turn")
        number(item["wander_timer"], 0, 1.4, "wander timer")
        generation = integer(item["generation"], 0, births, "generation")
        if oid <= founders:
            require(item["parent_id"] is None and generation == 0, "Invalid founder lineage.")
        else:
            integer(item["parent_id"], 1, oid - 1, "parent ID")
            require(generation > 0, "Offspring generation must be positive.")
        world.organisms[oid] = Organism(**{**item, "traits": traits})
    ecological = fields(data["ecology"], ("handling",), "ecology")
    require(isinstance(ecological["handling"], dict), "Invalid handling state.")
    require(config.rules_version == 2 or not ecological["handling"], "Handling state in Classic world.")
    world.handling = {}
    for key, value in ecological["handling"].items():
        require(isinstance(key, str) and key.isascii() and key.isdecimal() and str(int(key)) == key, "Invalid handling ID.")
        oid = int(key)
        require(oid in world.organisms and world.organisms[oid].species == "predator", "Handling target must be a living predator.")
        remaining = number(value, 0, 10.5, "handling time")
        require(remaining > 0, "Empty handling interval.")
        world.handling[oid] = remaining
    for organism in world.organisms.values():
        parent = world.organisms.get(organism.parent_id)
        if parent:
            require(organism.generation == parent.generation + 1, "Parent and offspring generations disagree.")
            require(organism.species == parent.species, "Parent and offspring species disagree.")
    require(sum(o.species == "predator" for o in world.organisms.values()) <= config.predator_cap, "Predator cap exceeded.")
    require(len(world.organisms) == founders + births - deaths, "Population, births and deaths disagree.")
    for item in raw["food"]:
        fields(item, Food.__dataclass_fields__, "food")
        fid = integer(item["id"], 1, next_food - 1, "food ID")
        require(fid not in world.food, "Duplicate food ID.")
        number(item["x"], 0, config.width, "food x")
        number(item["y"], 0, config.height, "food y")
        food = Food(**item)
        world.food[fid] = food
        world._food_grid.setdefault(world._cell(food.x, food.y), {})[fid] = food
    if config.rules_version == 2:
        for kind in range(3):
            limit = config.food_cap//3 + int(kind < config.food_cap%3)
            require(sum((f.id-1)%3 == kind for f in world.food.values()) <= limit,
                    "Food resource capacity exceeded.")
    rng = raw["rng_state"]
    require(isinstance(rng, (list, tuple)) and len(rng) == 3 and type(rng[0]) is int and rng[0] == 3, "Invalid RNG state version.")
    require(isinstance(rng[1], (list, tuple)) and len(rng[1]) == 625, "Invalid RNG state size.")
    for value in rng[1][:-1]:
        integer(value, 0, 2**32 - 1, "RNG state word")
    integer(rng[1][-1], 0, 624, "RNG index")
    require(rng[2] is None, "Unexpected Gaussian RNG cache for this simulation.")
    world.rng.setstate((3, tuple(rng[1]), None))
    world.ticks, world.births, world.deaths = ticks, births, deaths
    world.catches = catches
    world._next_organism_id, world._next_food_id, world._food_credit = next_id, next_food, credit
    if legacy_environment:
        world.environment.ticks = ticks
    else:
        world.environment = read_environment(data["environment"], world)
    if legacy_lineage:
        world.lineage = LineageArchive()
        world.lineage.legacy_unavailable = deaths
        for organism in sorted(world.organisms.values(), key=lambda o: o.id):
            world.lineage.record_birth(organism, world.time, legacy=True)
    else:
        world.lineage = read_lineage(data["lineage"], world)
    try:
        world.diagnostics = Diagnostics.observe_existing(world) if legacy_diagnostics else Diagnostics.restore(data["diagnostics"], world)
    except (ValueError, TypeError, KeyError) as error:
        raise SaveError(f"Invalid diagnostics: {error}") from error
    clock_raw = fields(data["clock"], ("speed", "paused", "accumulator"), "clock")
    require(type(clock_raw["speed"]) is int and clock_raw["speed"] in (1, 2, 4), "Invalid playback speed.")
    require(type(clock_raw["paused"]) is bool, "Invalid pause flag.")
    accumulator = number(clock_raw["accumulator"], 0, config.timestep, "clock accumulator")
    require(accumulator < config.timestep, "Clock accumulator must be less than a tick.")
    history_raw = fields(data["history"], ("capacity", "interval_ticks", "dropped_samples", "revision", "last_seen_tick", "baseline", "samples"), "history")
    capacity = integer(history_raw["capacity"], 2, 3601, "history capacity")
    interval = integer(history_raw["interval_ticks"], 30, 30, "sampling interval")
    integer(history_raw["last_seen_tick"], ticks, ticks, "last sampled observation")
    require(read_stats(history_raw["baseline"], config) == founder_stats, "Founder comparisons do not match the seed and settings.")
    total = 1 + ticks // interval + int(not world.organisms and ticks % interval != 0)
    integer(history_raw["revision"], total, total, "history revision")
    dropped = integer(history_raw["dropped_samples"], max(0, total - capacity), max(0, total - capacity), "dropped history count")
    rows = history_raw["samples"]
    require(isinstance(rows, list) and len(rows) == min(total, capacity), "History sample count is inconsistent.")
    history = History(world, settings, capacity, interval)
    history.samples.clear()
    previous = founder_stats
    for index, item in enumerate(rows, start=dropped):
        fields(item, Sample.__dataclass_fields__, "history sample")
        expected_tick = min(index * interval, ticks)
        integer(item["tick"], expected_tick, expected_tick, "history tick")
        number(item["simulation_seconds"], expected_tick * config.timestep, expected_tick * config.timestep, "sample time")
        expected_kind = "initial" if index == 0 else ("extinction" if not world.organisms and expected_tick == ticks else "periodic")
        require(item["sample_kind"] == expected_kind, "Invalid history sample kind.")
        stats = read_stats(item["stats"], config)
        require(stats.season_multiplier == world.environment.seasonal_at(expected_tick), "Sample seasonal multiplier disagrees with time.")
        require(previous.births <= stats.births <= births and previous.deaths <= stats.deaths <= deaths, "Non-monotonic history counters.")
        require(previous.catches <= stats.catches <= catches, "Non-monotonic catch counts.")
        if expected_tick == 0:
            require(stats == founder_stats, "Initial history differs from founder statistics.")
        if expected_tick == ticks:
            require(stats == statistics(world), "Latest history differs from world statistics.")
        require(stats.population > 0 or expected_kind == "extinction", "Unexpected empty historical population.")
        history.samples.append(Sample(expected_tick, item["simulation_seconds"], expected_kind, stats))
        previous = stats
    history.baseline, history.dropped_samples = founder_stats, dropped
    history.revision, history._last_seen_tick = total, ticks
    clock = SimulationClock(world, history.on_step)
    clock.speed, clock.accumulator, clock.paused = clock_raw["speed"], accumulator, True
    selection = data["selection"]
    if selection is not None:
        integer(selection, 1, MAX_COUNT, "selected organism ID")
    return LoadedWorld(settings, world, clock, history, selection if selection in world.organisms else None)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON field: {key}.")
        result[key] = value
    return result


def load_world(path) -> LoadedWorld:
    try:
        with Path(path).expanduser().open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "Save exceeds the 16 MiB size limit.")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
        return restore(data)
    except SaveError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        raise SaveError(f"Could not load world: {error}") from error


def save_world(path, world, clock, history, selected_id=None) -> Path:
    return save_document(path, document(world, clock, history, selected_id))


def encode_document(data):
    restore(data)  # Validate before any existing file is replaced.
    content = json.dumps(data, allow_nan=False, indent=2)
    require(len(content.encode("utf-8")) <= MAX_BYTES, "Save exceeds the 16 MiB size limit.")
    return content


def save_document(path, data):
    return atomic_write(path, encode_document(data))


def atomic_write(path, content) -> Path:
    temporary = None
    try:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return target
    except SaveError:
        raise
    except (OSError, ValueError, TypeError, OverflowError) as error:
        raise SaveError(f"Could not save world: {error}") from error
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
