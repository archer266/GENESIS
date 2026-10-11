"""Starting configurations only; presets never participate in simulation steps."""

from dataclasses import dataclass, replace

from .observatory import ExperimentSettings


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    settings: ExperimentSettings


PRESETS = (
    Preset("Balanced", "Original food and variation.", ExperimentSettings()),
    Preset("Abundance", "More renewable food.", ExperimentSettings(food_per_second=40)),
    Preset("Scarcity", "Limited food; uncertain survival.", ExperimentSettings(food_per_second=6)),
    Preset("Rapid Mutation", "Stronger bounded mutations.", ExperimentSettings(mutation_strength=0.18)),
    Preset("Predator–Prey", "Two competing populations.",
           ExperimentSettings(predator_enabled=True, initial_predators=8)),
    Preset("Patchwork Ecosystem", "Rich gardens; slower dense water.",
           ExperimentSettings(predator_enabled=True, initial_predators=8, habitat_enabled=True)),
    Preset("Changing Seasons", "Food ebbs and recovers; droughts add temporary scarcity. Survival is uncertain.",
           ExperimentSettings(predator_enabled=True, initial_predators=8, habitat_enabled=True,
                              seasons_enabled=True, droughts_enabled=True)),
    Preset("Coexistence", "Reference seed 101; seed-sensitive coexistence, not guaranteed.",
           ExperimentSettings(seed=101, map_seed=101, initial_population=160, food_per_second=24, mutation_strength=.005,
                              predator_enabled=True, initial_predators=4, habitat_enabled=True,
                              seasons_enabled=True, season_length=300, droughts_enabled=True,
                              drought_duration=5, drought_interval=300)),
)


def preset_name(settings: ExperimentSettings) -> str:
    """Seed is independent of the ecosystem recipe; edits may make it Custom."""
    for preset in PRESETS:
        if replace(settings, seed=preset.settings.seed, map_seed=preset.settings.map_seed) == preset.settings:
            return preset.name
    return "Custom"
