"""Read-only observatory charts and reusable draft editing / CSV helpers."""

from pathlib import Path
import uuid
import logging
from .user_files import writable_destination
import secrets

import pygame

from .observatory import ExperimentSettings, distributions, statistics
from .simulation import Traits
from .visuals import PALETTE, GOLD, HABITAT_COLORS, EcosystemRenderer
from .habitats import REGIONS, LABELS, occupancy
from .presets import PRESETS, preset_name
from .file_dialogs import choose_world_file


TEXT = (239, 246, 255)
MUTED = (180, 198, 223)
LINE = (36, 57, 85)
ACCENT = PALETTE[0]
TRAIT_COLORS = (PALETTE[3], PALETTE[4], PALETTE[1])


class ObservatoryPanel:
    TABS = (("history", "History"), ("evolution", "Traits"), ("habitats", "Habitats"), ("settings", "Setup"), ("worlds", "Worlds"), ("cell", "Cell"))
    FIELDS = (("seed", "Random seed", "0–4294967295"),
              ("initial_population", "Starting prey", "1–300"),
              ("food_per_second", "Food / sim second", "0–80"),
              ("mutation_percent", "Mutation ± %", "0–20"),
              ("predator_enabled", "Predator mode", "0 = off / 1 = on"),
              ("initial_predators", "Starting predators", "0–40; combined cap 300"),
              ("habitat_enabled", "Habitats (0 off / 1 on)", "0 = uniform / 1 = patchwork"),
              ("map_seed", "Map seed", "0–4294967295"))

    def __init__(self, settings):
        self.opened = True
        self.tab = "history"
        self.values = settings.text_values()
        self.active_field = None
        self.replace_text = False
        self.notice = ""
        self.notice_error = False
        self.notice_scroll = 0
        self.notice_scroll_max = 0
        self.saved_path = None
        self.buttons = {}
        self.inputs = {}
        self._graph_cache = None
        self.species = "prey"
        self.world_notice = "Save a checkpoint or load a world paused."
        self.world_notice_error = False
        self.world_scroll = 0
        self.world_scroll_max = 0
        self.map_preview = EcosystemRenderer()

    def focus(self, key):
        self.active_field = key
        self.replace_text = True
        if key:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()

    def handle_event(self, app, event):
        if event.type == pygame.TEXTINPUT and self.active_field:
            text = "" if self.replace_text else self.values[self.active_field]
            self.values[self.active_field] = (text + event.text)[:24]
            self.replace_text = False
            return True
        if event.type == pygame.KEYDOWN and self.active_field:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.focus(None)
            elif event.key == pygame.K_TAB:
                keys = list(self.values)
                direction = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                self.focus(keys[(keys.index(self.active_field) + direction) % len(keys)])
            elif event.key == pygame.K_a and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                self.replace_text = True
            elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                self.values[self.active_field] = "" if self.replace_text else self.values[self.active_field][:-1]
                self.replace_text = False
            return True  # Editing numbers must never trigger playback hotkeys.
        return False

    def export(self, app, path=None):
        self.notice_scroll = 0
        if path is None:
            root = app.file_directory("export")
            path = root / f"genesis_seed{app.seed}_tick{app.world.ticks}_{uuid.uuid4().hex[:8]}.csv"
        try:
            self.saved_path = app.history.export_csv(writable_destination(path))
            app.remember_directory("export", self.saved_path)
            self.notice = f"Saved {len(app.history.samples)} rows:\n{self.saved_path}"
            self.notice_error = False
        except (OSError, ValueError) as error:
            logging.getLogger("genesis").exception("Statistics export failed")
            self.notice = f"Export failed: {error}"
            self.notice_error = True

    @staticmethod
    def wrap(app, text, x, y, width, color=MUTED, size=13, line_height=19):
        # Character wrapping also accommodates long Windows paths without spaces.
        for paragraph in text.split("\n"):
            line = ""
            for char in paragraph:
                if app.fonts[size].size(line + char)[0] > width and line:
                    split = line.rfind(" ")
                    app.label(line[:split] if split > 0 else line, x, y, size, color)
                    y += line_height
                    line = line[split + 1:] if split > 0 else ""
                line += char
            app.label(line, x, y, size, color)
            y += line_height
        return y

    def draw_history(self, app):
        rect = app.sidebar
        current = statistics(app.world)
        app.label(f"Prey {current.prey_population}  /  Predators {current.predator_population}  /  Catches {current.catches}",
                  rect.x + 18, rect.y + 96, 13, TEXT)
        available = rect.height - 175
        height = available // 4
        specs = (("population", "Population", 0, 300),
                 ("average_speed", "Movement (u/s)", 18, 75),
                 ("average_sense", "Sensing radius (u)", 35, 160),
                 ("average_size", "Body radius (u)", 3, 9))
        key = (app.history, app.history.revision, rect.size, app.world.environment.total_events)
        if self._graph_cache is None or self._graph_cache[0] != key:
            surface = pygame.Surface((rect.width, available), pygame.SRCALPHA)
            samples = list(app.history.samples)
            start = samples[0].simulation_seconds
            end = max(start + 1, samples[-1].simulation_seconds)
            for index, (attr, title, low, high) in enumerate(specs):
                y = index * height
                if attr != "population":
                    values = [getattr(s.stats, species + "_" + attr) for s in samples
                              for species in ("prey", "predator")
                              if getattr(s.stats, species + "_" + attr) is not None]
                    if values:
                        padding = max((max(values) - min(values)) * .2, (high - low) * .015)
                        low, high = max(low, min(values) - padding), min(high, max(values) + padding)
                surface.blit(app.fonts[13].render(title, True, TEXT), (18, y))
                chart = pygame.Rect(49, y + 27, rect.width - 75, height - 51)
                if attr == "population":
                    for event in app.world.environment.history:
                        when = event.tick*app.world.config.timestep
                        if start <= when <= end:
                            cx = round(chart.left+(when-start)/(end-start)*chart.width)
                            color = (59, 109, 125, 130) if event.kind == "season" else ((212, 161, 84, 150) if event.kind == "drought_start" else (175, 164, 126, 130))
                            pygame.draw.line(surface, color, (cx, chart.top), (cx, chart.bottom))
                for value, cy in ((high, chart.top), (low, chart.bottom)):
                    pygame.draw.line(surface, LINE, (chart.left, cy), (chart.right, cy))
                    label = app.fonts[13].render(f"{value:g}" if attr == "population" else f"{value:.1f}", True, MUTED)
                    surface.blit(label, (chart.left - label.get_width() - 7, cy - 8))
                for species, color, lx in (("prey", ACCENT, 166), ("predator", PALETTE[3], 247)):
                    field = species + "_" + attr
                    value = getattr(samples[-1].stats, field)
                    label = "--" if value is None else f"{value:.1f}"
                    surface.blit(app.fonts[13].render(label, True, color), (lx, y))
                    points = []
                    for sample in samples:
                        value = getattr(sample.stats, field)
                        if value is None:
                            if len(points) > 1:
                                pygame.draw.aalines(surface, color, False, points)
                            points = []
                            continue
                        points.append((chart.left + (sample.simulation_seconds - start) / (end - start) * chart.width,
                                       chart.bottom - (value - low) / (high - low) * chart.height))
                    if len(points) > 1:
                        pygame.draw.aalines(surface, color, False, points)
                    elif points:
                        pygame.draw.circle(surface, color, (round(points[0][0]), round(points[0][1])), 2)
                for text, cx in ((f"{start:g}s", chart.left), (f"{end:g}s", chart.right)):
                    label = app.fonts[13].render(text, True, MUTED)
                    surface.blit(label, (cx - (label.get_width() if cx == chart.right else 0), chart.bottom + 3))
                label = app.fonts[13].render("simulation time", True, MUTED)
                surface.blit(label, (chart.centerx - label.get_width() // 2, chart.bottom + 3))
            self._graph_cache = (key, surface)
        app.label("PREY", rect.x + 166, rect.y + 118, 13, ACCENT)
        app.label("PREDATORS", rect.x + 247, rect.y + 118, 13, PALETTE[3])
        app.screen.blit(self._graph_cache[1], (rect.x, rect.y + 143))
        extinction = (" / prey extinct" if not current.prey_population else " / predators extinct"
                      if app.settings.predator_enabled and not current.predator_population else "")
        app.label(f"1s / {len(app.history.samples)} rows / {app.history.dropped_samples} dropped{extinction}",
                  rect.x + 18, rect.bottom - 24, 13, MUTED)

    def draw_evolution(self, app):
        rect = app.sidebar
        x, y = rect.x + 18, rect.y + 98
        current = statistics(app.world)
        baseline = app.history.baseline
        app.label("TRAIT AVERAGES", x, y, 13, ACCENT)
        self.draw_button(app, "species", self.species.title() + " / switch", True)
        app.label("Start", x + 151, y + 24, 13, MUTED)
        app.label("Now", x + 221, y + 24, 13, MUTED)
        for i, (attr, title, color) in enumerate(zip(("average_speed", "average_sense", "average_size"),
                                                   ("Movement", "Sensing radius", "Body radius"), TRAIT_COLORS)):
            attr = self.species + "_" + attr
            now = getattr(current, attr)
            app.label(title, x, y + 50 + i * 26, 15, color)
            app.label(f"{getattr(baseline, attr):.2f}" if getattr(baseline, attr) is not None else "—", x + 151, y + 50 + i * 26, 15)
            app.label(f"{now:.2f}" if now is not None else "—", x + 221, y + 50 + i * 26, 15)
        app.label(f"Highest living generation: {current.highest_generation if current.highest_generation is not None else '—'}", x, y + 139, 15)
        app.label(f"CURRENT DISTRIBUTIONS  ·  {getattr(current, self.species + '_population')} {self.species}", x, y + 174, 13, ACCENT)
        histograms = distributions(app.world, species=self.species)
        height = min(139, (rect.bottom - (y + 207) - 26) // 3)
        for index, (name, title, color) in enumerate(zip(Traits.BOUNDS, ("Movement · units/s", "Sensing radius · units", "Body radius · units"), TRAIT_COLORS)):
            top = y + 205 + index * height
            app.label(title, x, top, 13, color)
            counts = histograms[name]
            peak = max(1, max(counts))
            chart = pygame.Rect(x + 31, top + 23, rect.width - 73, height - 46)
            pygame.draw.line(app.screen, LINE, chart.bottomleft, chart.bottomright)
            app.label(str(peak), x, chart.top - 4, 13, MUTED)
            app.label("0", x, chart.bottom - 10, 13, MUTED)
            for i, count in enumerate(counts):
                width = chart.width / len(counts)
                bar_height = round(count / peak * chart.height)
                if bar_height:
                    pygame.draw.rect(app.screen, color, (round(chart.x + i * width + 1), chart.bottom - bar_height,
                                                        max(1, round(width - 3)), bar_height), border_radius=2)
            low, high = Traits.BOUNDS[name]
            app.label(f"{low:g}", chart.x, chart.bottom + 3, 13, MUTED)
            app.label(f"{high:g}", chart.right - 19, chart.bottom + 3, 13, MUTED)
            app.label("trait value", chart.centerx - 28, chart.bottom + 3, 13, MUTED)
        app.label("Y = cell count · 10 equal-width bins", x, rect.bottom - 24, 13, MUTED)

    def draw_habitats(self, app):
        rect = app.sidebar
        x, y = rect.x + 18, rect.y + 100
        app.label("CURRENT HABITAT OCCUPANCY", x, y, 13, ACCENT)
        app.label("Region", x, y + 31, 13, MUTED)
        for i, title in enumerate(("Prey", "Pred", "Food")):
            app.label(title, x + 145 + i * 58, y + 31, 13, MUTED)
        counts = occupancy(app.world)
        for i, region in enumerate(REGIONS):
            top = y + 57 + i * 31
            app.label(LABELS[i], x, top, 15, HABITAT_COLORS[i])
            for j, kind in enumerate(("prey", "predator", "food")):
                app.label(str(counts[f"{region}_{kind}"]), x + 145 + j * 58, top, 15)
        self.wrap(app, "Location counts only; occupancy does not establish adaptation.", x, y + 157, rect.width - 36)
        app.label(f"ACTIVE MAP: seed {app.settings.map_seed}" if app.settings.habitat_enabled else "ACTIVE MAP: uniform open water", x, y + 210, 13, ACCENT)
        size = (rect.width - 36, 135)
        self.map_preview.prepare(size, app.world.habitats, True)
        app.screen.blit(self.map_preview.background, (x, y + 236))
        app.label("Food / movement multipliers", x, y + 383, 13, MUTED)
        app.label("Water 1 / 1 · Gardens 2 / 1 · Dense 1 / 0.6", x, y + 406, 13)
        self.wrap(app, "H toggles illumination only. Change habitat drafts in Experiment, then Start new.", x, y + 439, rect.width - 36)
