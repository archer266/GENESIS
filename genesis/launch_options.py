"""Desktop launch recipes; explicit overrides do not erase preset defaults."""
import argparse
from dataclasses import replace

from .ecology import recommended_settings
from .observatory import ExperimentSettings


def parse_options(arguments=None):
    parser = argparse.ArgumentParser(description="GENESIS — an evolving artificial life ecosystem")
    parser.add_argument('--seed', type=int, help='Reproducible world seed (default: 42)')
    parser.add_argument('--population', type=int, help='Starting prey, 1–300 (Ecology default: 160)')
    parser.add_argument('--food-rate', type=float, help='Base food regeneration, 0–80/s (Ecology default: 28)')
    parser.add_argument('--mutation-percent', type=float, help='Mutation strength, 0–20 (Ecology default: 20)')
    predators = parser.add_mutually_exclusive_group()
    predators.add_argument('--predators', type=int, help='Enable predators with 0–40 starting hunters (default: 8)')
    predators.add_argument('--no-predators', action='store_true', help='Disable predators')
    for name, help_text in (
        ('habitats', 'Seeded habitat map (Ecology default: enabled)'),
        ('seasons', 'Smooth seasonal food variation (default: disabled)'),
        ('droughts', 'Reproducibly scheduled droughts (default: disabled)'),
    ):
        parser.add_argument('--'+name, action=argparse.BooleanOptionalAction, default=None, help=help_text)
    parser.add_argument('--map-seed', type=int, help='Independent map seed, 0–4294967295 (default: 42)')
    parser.add_argument('--season-length', type=int, help='Full seasonal cycle, 40–600 simulation seconds')
    parser.add_argument('--drought-duration', type=int, help='Drought length, 5–60 simulation seconds')
    parser.add_argument('--drought-interval', type=int, help='Minimum drought-free gap, 30–300 seconds; maximum twice this')
    parser.add_argument('--frames', type=int, help='Exit after this many rendered frames (smoke checks)')
    parser.add_argument('--screenshot', help='Save a PNG on exit')
    parser.add_argument('--load', metavar='PATH', help='Load a versioned JSON world, paused')
    args = parser.parse_args(arguments)
    base = recommended_settings()
    fields = {
        'seed': args.seed, 'initial_population': args.population,
        'food_per_second': args.food_rate, 'habitat_enabled': args.habitats,
        'map_seed': args.map_seed, 'seasons_enabled': args.seasons,
        'season_length': args.season_length, 'droughts_enabled': args.droughts,
        'drought_duration': args.drought_duration, 'drought_interval': args.drought_interval,
    }
    if args.mutation_percent is not None:
        fields['mutation_strength'] = args.mutation_percent/100
    if args.predators is not None:
        fields.update(predator_enabled=True, initial_predators=args.predators)
    elif args.no_predators:
        fields.update(predator_enabled=False, initial_predators=0)
    try:
        settings = replace(base, **{key: value for key, value in fields.items() if value is not None})
    except ValueError as error:
        parser.error(str(error))
    return parser, args, settings
