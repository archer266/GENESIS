"""Immutable coordinate-based habitats. Map generation owns an independent RNG."""
from bisect import bisect_right
from dataclasses import dataclass, field
import math
import random

REGIONS = ("open_water", "garden", "dense")
LABELS = ("Open water", "Gardens", "Dense regions")
FOOD_MULTIPLIERS = (1.0, 2.0, 1.0)
MOVEMENT_MULTIPLIERS = (1.0, 1.0, 0.6)
COLUMNS, ROWS = 55, 38


@dataclass(frozen=True)
class HabitatMap:
    width: float
    height: float
    columns: int
    rows: int
    cells: tuple[int, ...]
    food_multipliers: tuple[float, ...] = FOOD_MULTIPLIERS
    movement_multipliers: tuple[float, ...] = MOVEMENT_MULTIPLIERS
    _cumulative: tuple[float, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 30 for v in (self.width, self.height)):
            raise ValueError("Habitat dimensions must be finite world dimensions of at least 30.")
        if (type(self.columns) is not int or type(self.rows) is not int
                or (self.columns, self.rows) not in ((1, 1), (COLUMNS, ROWS))):
            raise ValueError("Habitat grid must be 1x1 uniform or 55x38 patchwork.")
        if not isinstance(self.cells, tuple) or len(self.cells) != self.columns * self.rows:
            raise ValueError("Habitat cell count does not match map dimensions.")
        if any(type(v) is not int or not 0 <= v < len(REGIONS) for v in self.cells):
            raise ValueError("Habitat region values must be integers 0, 1 or 2.")
        for values, expected in ((self.food_multipliers, FOOD_MULTIPLIERS),
                                 (self.movement_multipliers, MOVEMENT_MULTIPLIERS)):
            if (not isinstance(values, tuple) or len(values) != 3
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                    or values != expected):
                raise ValueError("Unsupported habitat multipliers: food 1/2/1, movement 1/1/0.6 required.")
        cumulative, total = [], 0.0
        for region in self.cells:
            total += self.food_multipliers[region]
            cumulative.append(total)
        object.__setattr__(self, "_cumulative", tuple(cumulative))

    @classmethod
    def generate(cls, width, height, enabled=False, seed=42):
        if not enabled:
            return cls(width, height, 1, 1, (0,))
        rng = random.Random(seed)
        order = list(range(3))
        rng.shuffle(order)
        phases = (rng.uniform(0, math.tau), rng.uniform(0, math.tau))
        # Two gentle meandering boundaries: every band spans the full height,
        # remains broad and overlaps its neighbor row. No isolated islands.
        cells = []
        for y in range(ROWS):
            t = y / (ROWS - 1)
            left = round(COLUMNS * (.31 + .075 * math.sin(t * math.tau + phases[0])))
            right = round(COLUMNS * (.68 + .075 * math.sin(t * math.tau + phases[1])))
            cells.extend(order[0 if x < left else 1 if x < right else 2] for x in range(COLUMNS))
        return cls(width, height, COLUMNS, ROWS, tuple(cells))

    def region_at(self, x, y):
        # Right/bottom world edges belong to the last tile; slight overshoots
        # during wall reflection are clamped, never wrapped or negative-indexed.
        col = min(self.columns - 1, max(0, int(x / self.width * self.columns)))
        row = min(self.rows - 1, max(0, int(y / self.height * self.rows)))
        return self.cells[row * self.columns + col]

    @property
    def mean_food_multiplier(self):
        return self._cumulative[-1] / len(self.cells)

    def food_position(self, rng):
        """Area-weighted local regeneration, with exactly three simulation draws."""
        index = min(len(self.cells) - 1, bisect_right(self._cumulative, rng.random() * self._cumulative[-1]))
        col, row = index % self.columns, index // self.columns
        return ((col + rng.random()) * self.width / self.columns,
                (row + rng.random()) * self.height / self.rows)

    def document(self):
        return {name: getattr(self, name) for name in
                ("width", "height", "columns", "rows", "cells", "food_multipliers", "movement_multipliers")}

    @classmethod
    def from_document(cls, raw, width, height, enabled):
        names = {"width", "height", "columns", "rows", "cells", "food_multipliers", "movement_multipliers"}
        if not isinstance(raw, dict) or set(raw) != names:
            raise ValueError("Invalid habitat map fields.")
        values = dict(raw)
        for name in ("cells", "food_multipliers", "movement_multipliers"):
            if not isinstance(values[name], (list, tuple)):
                raise ValueError(f"Habitat {name} must be an array.")
            values[name] = tuple(values[name])
        result = cls(**values)
        if result.width != width or result.height != height:
            raise ValueError("Habitat dimensions do not match the world.")
        if enabled:
            if (result.columns, result.rows) != (COLUMNS, ROWS) or set(result.cells) != {0, 1, 2}:
                raise ValueError("Patchwork requires a 55x38 map containing all three regions.")
        elif (result.columns, result.rows, result.cells) != (1, 1, (0,)):
            raise ValueError("Uniform worlds require a single open-water tile.")
        return result


def occupancy(world):
    """Location counts only, not a claim about adaptation."""
    counts = {f"{region}_{kind}": 0 for region in REGIONS for kind in ("prey", "predator", "food")}
    for organism in world.organisms.values():
        region = REGIONS[world.habitats.region_at(organism.x, organism.y)]
        counts[f"{region}_{organism.species}"] += 1
    for food in world.food.values():
        region = REGIONS[world.habitats.region_at(food.x, food.y)]
        counts[f"{region}_food"] += 1
    return counts
