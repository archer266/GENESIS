from contextlib import redirect_stderr
from io import StringIO
import unittest

from genesis.ecology import recommended_settings
from genesis.launch_options import parse_options
from genesis.observatory import ExperimentSettings


class LaunchOptionsTests(unittest.TestCase):
    def test_only_corrected_recipe_is_available(self):
        self.assertEqual(parse_options([])[2], recommended_settings())
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parse_options(['--classic'])

    def test_single_override_retains_remaining_recipe(self):
        settings = parse_options(['--seed','211'])[2]
        self.assertEqual(settings.seed,211)
        self.assertEqual(settings.map_seed,42)
        self.assertEqual(settings.rules_version,2)
        self.assertEqual(settings.initial_predators,8)
        self.assertEqual(settings.mutation_strength,.20)

    def test_disabled_modes_and_zero_founders_are_distinct(self):
        disabled = parse_options(['--no-predators','--no-habitats'])[2]
        self.assertFalse(disabled.predator_enabled)
        self.assertFalse(disabled.habitat_enabled)
        self.assertEqual(disabled.initial_predators,0)
        empty = parse_options(['--predators','0'])[2]
        self.assertTrue(empty.predator_enabled)
        self.assertEqual(empty.initial_predators,0)

    def test_environment_overrides_and_classic_defaults(self):
        settings = parse_options(['--seasons','--droughts','--mutation-percent','18'])[2]
        self.assertEqual(settings,recommended_settings(stress=True))

    def test_enabling_environment_does_not_silently_retune_mutation(self):
        settings = parse_options(['--seasons','--droughts'])[2]
        self.assertEqual(settings.mutation_strength,recommended_settings().mutation_strength)

    def test_invalid_settings_and_conflicting_flags(self):
        for options in (['--population','301'], ['--mutation-percent','nan'],
                        ['--predators','8','--no-predators'], ['--map-seed','-1']):
            with self.subTest(options=options), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                parse_options(options)
