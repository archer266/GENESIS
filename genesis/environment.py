"""Fixed-tick food pressures, with an independent RNG and bounded event log."""
from collections import deque
from dataclasses import asdict, dataclass
import math
import random


DEFAULTS = dict(seasons_enabled=False, season_length=120, droughts_enabled=False,
                drought_duration=15, drought_interval=90)
STAT_DEFAULTS = dict(season_multiplier=1.0, drought_multiplier=1.0, environment_multiplier=1.0)
SEASONS = ("Spring", "Summer", "Autumn", "Winter")
HISTORY_LIMIT = 256
DROUGHT_FACTOR = .25


def validate_settings(settings):
    for key in ("seasons_enabled", "droughts_enabled"):
        if type(getattr(settings, key)) is not bool:
            raise ValueError(f"{key}: expected an Off/On switch.")
    for key, low, high in (("season_length", 40, 600), ("drought_duration", 5, 60), ("drought_interval", 30, 300)):
        value = getattr(settings, key)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{key.replace('_', ' ').title()}: enter a whole number from {low} to {high} seconds.")


@dataclass(frozen=True)
class EnvironmentEvent:
    tick: int
    kind: str
    season: str
    drought: bool
    multiplier: float


class Environment:
    def __init__(self, seed, config):
        self.config = config
        self.seed = seed ^ 0xE17A5EED
        self.rng = random.Random(self.seed)
        self.ticks = 0
        self.cycle_ticks = round(config.season_length/config.timestep)
        self.duration_ticks = round(config.drought_duration/config.timestep)
        self.interval_ticks = round(config.drought_interval/config.timestep)
        self.next_drought = self._gap() if config.droughts_enabled else None
        self.drought_start = self.drought_end = None
        self.drought_count = 0
        self.history = deque(maxlen=HISTORY_LIMIT)
        self.total_events = 0
        if config.seasons_enabled:
            self._record("season")

    @property
    def enabled(self):
        return self.config.seasons_enabled or self.config.droughts_enabled

    def _gap(self):
        return self.rng.randint(self.interval_ticks, self.interval_ticks*2)

    @property
    def cycle_position(self):
        return self.ticks % self.cycle_ticks if self.config.seasons_enabled else 0

    @property
    def season(self):
        return SEASONS[min(3, self.cycle_position*4//self.cycle_ticks)] if self.config.seasons_enabled else "Steady"

    def seasonal_at(self, tick):
        return 1 + .5*math.sin(2*math.pi*(tick % self.cycle_ticks)/self.cycle_ticks) if self.config.seasons_enabled else 1.0

    @property
    def seasonal_multiplier(self):
        return self.seasonal_at(self.ticks)

    @property
    def drought_multiplier(self):
        return DROUGHT_FACTOR if self.drought_end is not None else 1.0

    @property
    def multiplier(self):
        return self.seasonal_multiplier*self.drought_multiplier

    @property
    def next_season(self):
        if not self.config.seasons_enabled:
            return None
        # ceil boundaries also work for custom model timesteps.
        phase = self.cycle_position*4//self.cycle_ticks
        return self.ticks-self.cycle_position+math.ceil((phase+1)*self.cycle_ticks/4)

    @property
    def next_transition(self):
        return min((t for t in (self.next_season, self.next_drought, self.drought_end) if t is not None), default=None)

    def _record(self, kind):
        self.history.append(EnvironmentEvent(self.ticks, kind, self.season, self.drought_end is not None, self.multiplier))
        self.total_events += 1

    def advance(self):
        previous = self.season
        self.ticks += 1
        transition = None
        if self.drought_end == self.ticks:
            self.drought_start = self.drought_end = None
            self.next_drought = self.ticks+self._gap()
            transition = "drought_end"
        elif self.next_drought == self.ticks:
            self.drought_start = self.ticks
            self.drought_end = self.ticks+self.duration_ticks
            self.next_drought = None
            self.drought_count += 1
            transition = "drought_start"
        if previous != self.season:
            self._record("season")
        if transition:
            self._record(transition)

    def document(self):
        return dict(seed=self.seed, ticks=self.ticks, cycle_position=self.cycle_position,
                    next_season=self.next_season, next_drought=self.next_drought,
                    drought_start=self.drought_start, drought_end=self.drought_end,
                    drought_count=self.drought_count, rng_state=self.rng.getstate(),
                    history_limit=HISTORY_LIMIT, total_events=self.total_events,
                    history=[asdict(e) for e in self.history])
