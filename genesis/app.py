"""Pygame presentation/input; simulation.py and ecology.py own ecosystem rules."""

from dataclasses import replace
from .ecology import recommended_settings
import math
import logging
from .user_files import Preferences, window_geometry, writable_destination
from . import __version__
from pathlib import Path

import pygame
from pygame._sdl2 import Window

from .simulation import SimulationClock, World
from .visuals import EcosystemRenderer, VisualState, organism_color, PALETTE, PREDATOR_PALETTE, GOLD, HABITAT_COLORS
from .habitats import LABELS
from .observatory import ExperimentSettings, History, statistics
from .floating_ui import FloatingPanel
from .glass import Glass, button as glass_button, speed_segments
from .presets import preset_name
from .persistence import SaveError, load_world, save_world
from .camera import Camera
from .recovery import Recovery, find_recovery


BG = (5, 10, 27)
PANEL = (15, 28, 55)
TEXT = (239, 246, 255)
MUTED = (180, 198, 223)
ACCENT = PALETTE[0]
LINE = (36, 57, 85)


class App:
    def __init__(self, seed: int = 42, settings: ExperimentSettings | None = None, preferences: Preferences | None = None):
        pygame.init()
        self.preferences = preferences
        self.recovery = Recovery(preferences.root, preferences.values["autosave"]) if preferences else None
        pygame.display.set_caption(f"GENESIS {__version__}")
        icon = Path(__file__).parent / "assets" / "genesis.png"
        if icon.exists():
            pygame.display.set_icon(pygame.image.load(str(icon)))
        self.screen = pygame.display.set_mode((1380, 900), pygame.RESIZABLE)
        self.fonts = {size: pygame.font.SysFont("Segoe UI,Arial", size+1 if size <= 17 else size) for size in (13, 15, 17, 20, 26, 34)}
        self.settings = replace(settings, rules_version=2) if settings else replace(recommended_settings(), seed=seed)
        self.seed = self.settings.seed
        self.world = World(self.seed, self.settings.config())
        self.visuals = VisualState(self.world)
        self.history = History(self.world, self.settings)
        self.sim_clock = SimulationClock(self.world, self.on_step)
        self.observatory = FloatingPanel(self.settings)
        self.glass = Glass()
        self.ui_time = 0.0
        self.chrome_focus = None
        self.renderer = EcosystemRenderer()
        self.show_habitats = True
        self.show_environment = True
        self._panel_cache = {}
        self.selected_id: int | None = None
        self.running = True
        self.buttons: dict[str, pygame.Rect] = {}
        self.fps = 0.0
        self._discard_elapsed = False
        self.camera = Camera(self.world.config.width, self.world.config.height)
        self.follow_id = None
        self.camera_notice = ""
        self.notice_remaining = 0.0
        self.drag_button = None
        self.ui_hidden = False
        self.fullscreen = False
        self.windowed_size = self.screen.get_size()
        self.windowed_position = Window.from_display_module().position
        self.guide_until = 0
        self._layout()
        if preferences is not None:
            self.apply_preferences()

    def apply_preferences(self):
        p = self.preferences.values
        size, position = window_geometry(p, pygame.display.get_desktop_sizes()[0])
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        Window.from_display_module().position = position
        self.visuals.enabled = p["effects"]
        self.show_habitats, self.show_environment = p["habitats"], p["environment"]
        self.glass.reduced = p["reduced"]
        panel = self.observatory
        panel.rect = pygame.Rect(p["panel_rect"])
        panel.placed, panel.tab = True, p["panel_tab"]
        panel.opened, panel.minimized = p["panel_open"], p["panel_minimized"]
        self.guide_until = 0 if p["guide_seen"] else 12
        if p["fullscreen"]:
            self.toggle_fullscreen()
        self._layout()
        if self.preferences.warning:
            self.notify_camera("Preferences reset to defaults. Details in genesis.log.")

    def save_preferences(self):
        if self.preferences is None:
            return
        p = dict(self.preferences.values)
        size = self.windowed_size if self.fullscreen else self.screen.get_size()
        position = self.windowed_position if self.fullscreen else Window.from_display_module().position
        p.update(autosave=self.recovery.enabled if self.recovery else p["autosave"], effects=self.visuals.enabled, habitats=self.show_habitats,
                 environment=self.show_environment, reduced=self.glass.reduced,
                 fullscreen=self.fullscreen, guide_seen=True, window_size=list(size),
                 window_position=list(position), panel_rect=list(self.observatory.rect),
                 panel_tab=self.observatory.tab, panel_open=self.observatory.opened,
                 panel_minimized=self.observatory.minimized)
        try:
            self.preferences.save(p)
        except (OSError, ValueError):
            logging.getLogger("genesis").exception("Could not save preferences")
            self.notify_camera("Preferences could not be saved. Check the user folder permissions.")

    def remember_directory(self, kind, path):
        if self.preferences is not None:
            self.preferences.values[kind+"_directory"] = str(Path(path).resolve().parent)
            self.save_preferences()

    def file_directory(self, kind):
        return (self.preferences or Preferences()).directory(kind)

    def show_guide(self):
        self.guide_until = self.ui_time+12
        self.observatory.opened = False
        self.ui_hidden = False

    @property
    def scale(self):
        return self.camera.scale

    def _layout(self):
        self.viewport = self.screen.get_rect()
        self.camera.resize(self.viewport)
        self.bar = pygame.Rect(0, 0, 434, 60)
        self.bar.midbottom = (self.screen.get_width()//2, self.screen.get_height()-20)
        x, y = self.bar.x+12, self.bar.y+11
        self.buttons = {"pause": pygame.Rect(x, y, 88, 38),
                        "1": pygame.Rect(x+100, y, 48, 38),
                        "2": pygame.Rect(x+148, y, 48, 38),
                        "4": pygame.Rect(x+196, y, 48, 38),
                        "observatory": pygame.Rect(x+256, y, 154, 38)}
        self.card = pygame.Rect(20, 20, 286, 152)
        self.environment_chip = pygame.Rect(0, 20, 246, 38)
        self.environment_chip.centerx = self.screen.get_width()//2
        if self.show_environment and self.world.environment.enabled:
            self.buttons["environment_status"] = self.environment_chip
        if self.selected_id in self.world.organisms:
            self.buttons["details"] = pygame.Rect(self.card.x+16, self.card.bottom-45, 162, 30)
            self.buttons["deselect"] = pygame.Rect(self.card.right-94, self.card.bottom-45, 78, 30)
        if self.ui_hidden:
            self.buttons = {"hide_ui": pygame.Rect(16, 16, 166, 34)}
        if not self.world.organisms:
            self.buttons["restart"] = pygame.Rect(self.viewport.centerx-95, self.viewport.centery+35, 190, 38)
        self.guide = pygame.Rect(0, 0, min(730, self.screen.get_width()-40), 96)
        self.guide.midbottom = (self.viewport.centerx, self.bar.top-14)
        if self.ui_time < self.guide_until and not self.observatory.opened and not self.ui_hidden:
            self.buttons["dismiss_guide"] = pygame.Rect(self.guide.right-82, self.guide.y+12, 68, 28)
        self.observatory.layout(self)
        if ("environment_status" in self.buttons and self.observatory.opened and not self.observatory.minimized
                and self.observatory.rect.colliderect(self.environment_chip)):
            self.environment_chip.topleft = (20, 184 if self.selected_id in self.world.organisms else 20)
            if self.observatory.rect.colliderect(self.environment_chip):
                del self.buttons["environment_status"]

    def notify_camera(self, message):
        self.camera_notice, self.notice_remaining = message, 3.0

    def clear_camera_target(self):
        self.follow_id = None
        self.drag_button = None
        self.camera_notice, self.notice_remaining = "", 0
        self.camera.fit()

    def fit_world(self):
        self.follow_id = None
        self.camera_notice, self.notice_remaining = "", 0
        self.camera.fit()

    def toggle_follow(self):
        if self.follow_id is not None:
            self.follow_id = None
            self.notify_camera("Follow stopped.")
        elif self.selected_id in self.world.organisms:
            self.follow_id = self.selected_id
            self.notify_camera(f"Following #{self.follow_id}. Drag to leave follow mode.")

    def toggle_ui(self):
        self.ui_hidden = not self.ui_hidden
        self.observatory.focus(None)
        self.drag_button = None
        self._layout()

    def toggle_fullscreen(self):
        try:
            if not self.fullscreen:
                self.windowed_size = self.screen.get_size()
                self.windowed_position = Window.from_display_module().position
                # Borderless desktop fullscreen avoids disruptive display-mode changes.
                self.screen = pygame.display.set_mode(pygame.display.get_desktop_sizes()[0], pygame.NOFRAME)
                Window.from_display_module().position = (0, 0)
            else:
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                Window.from_display_module().position = self.windowed_position
            self.fullscreen = not self.fullscreen
            pygame.event.clear((pygame.VIDEORESIZE, pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED))
        except pygame.error as error:
            self.notify_camera(f"Fullscreen unavailable: {error}")
        self.drag_button = None
        self._layout()

    def reset(self):
        self.start_experiment(self.settings)

    def start_experiment(self, settings):
        settings = replace(settings, rules_version=2)
        self.settings = settings
        self.seed = settings.seed
        self.world = World(self.seed, settings.config())
        self.visuals = VisualState(self.world, enabled=self.visuals.enabled)
        self.history = History(self.world, settings)
        self.sim_clock = SimulationClock(self.world, self.on_step)
        self.selected_id = None
        self.observatory.lineage_view.view(None)
        self.observatory.event_offset = 0
        self.clear_camera_target()
        self.observatory.values = settings.text_values()
        self.observatory.focus(None)
        self.observatory.notice = "Experiment reset to its initial conditions."
        self.observatory.notice_error = False
        self.observatory.saved_path = None
        self._layout()
        self.establish_recovery()

    def on_step(self, world):
        self.history.on_step(world)
        self.visuals.on_step(world)
        if self.follow_id is not None and self.follow_id not in world.organisms:
            self.notify_camera(f"Followed organism #{self.follow_id} died. Follow stopped.")
            self.follow_id = None
        if self.selected_id not in world.organisms:
            self.selected_id = None

    def save_file(self, path):
        panel = self.observatory
        panel.world_scroll = 0
        try:
            saved = save_world(writable_destination(path), self.world, self.sim_clock, self.history, self.selected_id)
        except (SaveError, OSError, ValueError) as error:
            logging.getLogger("genesis").warning("World I/O failed: %s", error)
            panel.world_notice, panel.world_notice_error = str(error), True
            return False
        self.remember_directory("save", saved)
        panel.world_notice = f"World saved at t={self.world.time:.2f}s:\n{saved}"
        panel.world_notice_error = False
        return True

    def load_file(self, path):
        panel = self.observatory
        panel.world_scroll = 0
        try:
            loaded = load_world(path)
        except (SaveError, OSError, ValueError) as error:
            logging.getLogger("genesis").warning("World I/O failed: %s", error)
            panel.world_notice, panel.world_notice_error = str(error), True
            return False
        return self.apply_loaded(loaded, path)

    def apply_loaded(self, loaded, path):
        panel = self.observatory
        if loaded.world.config.rules_version != 2:
            panel.world_notice = "This world uses obsolete simulation rules. Start a new corrected ecosystem instead."
            panel.world_notice_error = True
            return False
        visuals = VisualState(loaded.world, enabled=self.visuals.enabled)
        self.settings, self.seed = loaded.settings, loaded.settings.seed
        self.world, self.history, self.sim_clock = loaded.world, loaded.history, loaded.clock
        self.visuals, self.selected_id = visuals, loaded.selected_id
        panel.lineage_view.view(None)
        panel.event_offset = 0
        self.clear_camera_target()
        self.sim_clock.on_step = self.on_step
        panel.values = self.settings.text_values()
        panel.focus(None)
        panel._graph_cache = None
        panel.notice, panel.notice_error = "Loaded settings. Start new replaces this resumed world.", False
        self.remember_directory("save", path)
        panel.world_notice = f"Loaded PAUSED at t={self.world.time:.2f}s. Resume to continue.\n{Path(path).resolve()}"
        panel.world_notice_error = False
        self._layout()
        self.establish_recovery()
        return True

    def establish_recovery(self):
        if self.recovery:
            self.recovery.changed_world()
            self.recovery.tick(self.world, self.sim_clock, self.history, self.selected_id)

    def offer_recovery(self):
        if not self.recovery:
            return
        loaded, path, reason = find_recovery(self.recovery.root)
        if loaded is None:
            if reason:
                self.recovery.status, self.recovery.error = reason, True
            return
        self.recovery.pending_choice = True
        self._recovery_candidate = (loaded, path)
        self.observatory.confirm(self, f"Resume seed {loaded.settings.seed} at {loaded.world.time:.1f}s, paused? {reason}", lambda: self.choose_recovery(True))

    def choose_recovery(self, resume):
        if not self.recovery or not self.recovery.pending_choice:
            return
        self.recovery.pending_choice = False
        self.observatory.pending = None
        if resume:
            self.apply_loaded(*self._recovery_candidate)
        else:
            self.establish_recovery()
        self._recovery_candidate = None
        self._discard_elapsed = True

    def close_recovery(self):
        if self.recovery:
            self.recovery.close(self.world, self.sim_clock, self.history, self.selected_id)

    def handle_event(self, event):
        self._layout()
        if self.observatory.handle_event(self, event):
            return
        point = getattr(event, "pos", pygame.mouse.get_pos())
        surfaces = ([self.buttons["hide_ui"]] if self.ui_hidden else
                    [self.bar]+([self.card] if self.selected_id in self.world.organisms else [])+
                    ([self.environment_chip] if "environment_status" in self.buttons else []))
        if "dismiss_guide" in self.buttons:
            surfaces.append(self.guide)
        over_ui = any(rect.collidepoint(point) for rect in surfaces)
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL) and over_ui:
            self.drag_button = None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for key, rect in self.buttons.items():
                    if rect.collidepoint(point):
                        self.activate_control(key)
                        break
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == self.drag_button:
            self.drag_button = None
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.drag_button = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (2, 3) and self.viewport.collidepoint(point):
            self.drag_button = event.button
            return
        if event.type == pygame.MOUSEMOTION and self.drag_button:
            if event.rel != (0, 0):
                if self.follow_id is not None:
                    self.notify_camera("Follow stopped. Manual camera.")
                self.follow_id = None
                self.camera.pan(*event.rel)
            return
        if event.type == pygame.MOUSEWHEEL and self.viewport.collidepoint(point):
            self.camera.zoom_at(point, event.y)
            return
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            target = (max(960, event.w), max(720, event.h))
            if not self.fullscreen and self.screen.get_size() != target:
                self.screen = pygame.display.set_mode(target, pygame.RESIZABLE)
            self._layout()
        elif event.type == pygame.KEYDOWN:
            if getattr(event, "mod", 0) & pygame.KMOD_CTRL and event.key in (pygame.K_s, pygame.K_l):
                self.observatory.file_action(self, event.key == pygame.K_s)
            elif event.key == pygame.K_SPACE:
                self.sim_clock.paused = not self.sim_clock.paused
            elif event.key == pygame.K_r:
                self.observatory.confirm_restart(self)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_4):
                self.sim_clock.speed = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_4: 4}[event.key]
            elif event.key == pygame.K_ESCAPE:
                if self.ui_hidden:
                    self.toggle_ui()
                elif self.fullscreen:
                    self.toggle_fullscreen()
                else:
                    self.selected_id = self.follow_id = None
            elif event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif event.key == pygame.K_i:
                self.toggle_ui()
            elif event.key == pygame.K_HOME:
                self.fit_world()
            elif event.key == pygame.K_f:
                self.toggle_follow()
            elif event.key == pygame.K_e:
                self.visuals.toggle()
            elif event.key == pygame.K_h:
                self.show_habitats = not self.show_habitats
            elif event.key == pygame.K_o:
                self.observatory.toggle(self)
            elif event.key == pygame.K_TAB:
                keys = list(self.buttons)
                index = keys.index(self.chrome_focus) if self.chrome_focus in keys else -1
                step = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                self.chrome_focus = keys[(index+step)%len(keys)]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.chrome_focus in self.buttons:
                self.activate_control(self.chrome_focus)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if "restart" in self.buttons and self.buttons["restart"].collidepoint(point):
                self.observatory.confirm_restart(self)
                return
            self.chrome_focus = None
            x, y = self.camera.screen_to_world(*point)
            def distance(organism):
                pose = self.visuals.pose(organism, self.alpha)
                return math.hypot(pose.x-x, pose.y-y)
            nearest = min(self.world.organisms.values(), key=distance, default=None)
            self.selected_id = (nearest.id if nearest and distance(nearest)
                                <= max(nearest.traits.size*1.28, 4/self.scale)+5/self.scale else None)
            if self.follow_id != self.selected_id:
                self.follow_id = None
            self._layout()

    def activate_control(self, key):
        if key == "dismiss_guide":
            self.guide_until = 0
        elif key == "pause":
            self.sim_clock.paused = not self.sim_clock.paused
        elif key in ("1", "2", "4"):
            self.sim_clock.speed = int(key)
        elif key == "observatory":
            self.observatory.toggle(self)
        elif key == "details":
            self.observatory.lineage_view.view(self.selected_id)
            self.observatory.show(self, "cell")
        elif key == "environment_status":
            self.observatory.show(self, "environment")
        elif key == "deselect":
            self.selected_id = self.follow_id = None
        elif key == "hide_ui":
            self.toggle_ui()
        elif key == "restart":
            self.observatory.confirm_restart(self)
        self._layout()

    @property
    def alpha(self):
        # Pause leaves this fraction untouched, freezing at the displayed pose.
        return self.sim_clock.accumulator / self.world.config.timestep

    def update(self, elapsed):
        self.ui_time += elapsed
        self.notice_remaining = max(0, self.notice_remaining - elapsed)
        if not self.sim_clock.paused:
            self.visuals.advance(elapsed)
        if not (self.recovery and self.recovery.pending_choice):
            self.sim_clock.advance(elapsed)
        self.update_camera(elapsed)
        if self.recovery:
            self.recovery.tick(self.world, self.sim_clock, self.history, self.selected_id)

    def update_camera(self, elapsed):
        target = self.world.organisms.get(self.follow_id)
        if target:
            pose = self.visuals.pose(target, self.alpha)
            self.camera.follow(pose.x, pose.y, elapsed)
        elif self.follow_id is not None:
            self.notify_camera(f"Followed organism #{self.follow_id} died. Follow stopped.")
            self.follow_id = None

    def panel(self, rect):
        key = rect.size
        if key not in self._panel_cache:
            # Window resizing cannot grow this cache without bound.
            if len(self._panel_cache) >= 6:
                self._panel_cache.clear()
            surface = pygame.Surface(key, pygame.SRCALPHA)
            pygame.draw.rect(surface, (*PANEL, 215), surface.get_rect(), border_radius=10)
            pygame.draw.rect(surface, (*LINE, 185), surface.get_rect(), 1, border_radius=10)
            self._panel_cache[key] = surface
        self.screen.blit(self._panel_cache[key], rect)

    def label(self, text, x, y, size=15, color=TEXT):
        self.screen.blit(self.fonts[size].render(str(text), True, color), (x, y))

    def button(self, key, label, active=False):
        glass_button(self, self.buttons[key], label, active, self.chrome_focus == key)

    def position(self, x, y):
        return tuple(round(v) for v in self.camera.world_to_screen(x, y))

    def row(self, label, value, y, color=TEXT):
        x = self.sidebar.x + 20
        self.label(label, x, y, color=MUTED)
        surface = self.fonts[15].render(str(value), True, color)
        self.screen.blit(surface, (self.sidebar.right - 20 - surface.get_width(), y))

    def divider(self, y):
        pygame.draw.line(self.screen, LINE, (self.sidebar.x + 20, y), (self.sidebar.right - 20, y))

    def draw(self):
        self._layout()
        self.screen.fill(BG)
        self.renderer.draw(self.screen, self.viewport, self.scale, self.world, self.visuals,
                           self.alpha, self.selected_id, self.show_habitats, self.camera)
        if not self.ui_hidden:
            if "environment_status" in self.buttons:
                env = self.world.environment
                self.glass.draw(self.screen, self.environment_chip, "environment", self.ui_time)
                title = ("Drought / " if env.drought_end is not None else "")+env.season+f" / {env.multiplier:.2f}x food"
                text = self.fonts[13].render(title, True, TEXT)
                self.screen.blit(text, text.get_rect(center=self.environment_chip.center))
                if self.chrome_focus == "environment_status" or self.environment_chip.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(self.screen, (172, 203, 228), self.environment_chip.inflate(-4, -4), 1, border_radius=16)
            self.glass.draw(self.screen, self.bar, "bar", self.ui_time)
            self.button("pause", "Play" if self.sim_clock.paused else "Pause", self.sim_clock.paused)
            speed_segments(self)
            self.button("observatory", "Settings", self.observatory.opened and not self.observatory.minimized)
            selected = self.world.organisms.get(self.selected_id)
            if selected:
                self.glass.draw(self.screen, self.card, "card", self.ui_time)
                self.label(f"{selected.species.title()} #{selected.id}", self.card.x+16, self.card.y+13, 17, organism_color(selected))
                self.label(f"Energy {selected.energy:.1f} / {self.world.config.energy_capacity:g}", self.card.x+16, self.card.y+44, 15)
                self.label(f"Age {selected.age:.1f}s   /   Generation {selected.generation}", self.card.x+16, self.card.y+73, 13, MUTED)
                self.button("details", "Details")
                self.button("deselect", "Deselect")
            if "dismiss_guide" in self.buttons:
                self.glass.draw(self.screen, self.guide, "guide", self.ui_time)
                self.label("Explore your ecosystem", self.guide.x+18, self.guide.y+12, 17)
                self.label("Space: pause / play   |   Wheel: zoom   |   Right-drag: pan", self.guide.x+18, self.guide.y+42, 15)
                self.label("Click a cell to inspect   |   O: Settings   |   Reopen this guide in Appearance", self.guide.x+18, self.guide.y+66, 13)
                self.button("dismiss_guide", "Got it")
        else:
            self.button("hide_ui", "Restore UI [I / Esc]")
            selected = self.world.organisms.get(self.selected_id)
            if selected:
                pose = self.visuals.pose(selected, self.alpha)
                sx, sy = self.position(pose.x, pose.y)
                if self.viewport.collidepoint(sx, sy):
                    self.hud_label(f"{selected.species.title()} #{selected.id}", min(self.viewport.right-160, sx+20), max(60, sy-24))
        if self.notice_remaining > 0:
            self.hud_label(self.camera_notice, 22, self.screen.get_height()-104)
        if not self.world.organisms:
            rect = pygame.Rect(0, 0, 390, 150)
            rect.center = self.viewport.center
            self.glass.draw(self.screen, rect, "extinct", self.ui_time)
            self.label("Ecosystem extinct", rect.x+26, rect.y+20, 26)
            self.label("Every lineage ended. Restart to replay.", rect.x+26, rect.y+62, 15, MUTED)
            self.button("restart", "Restart experiment...")
        self.observatory.draw(self)
        pygame.display.flip()

    def hud_label(self, text, x, y):
        surface = self.fonts[13].render(text, True, TEXT)
        box = pygame.Rect(x - 4, y - 2, surface.get_width() + 8, surface.get_height() + 4)
        self.screen.set_clip(self.viewport)
        pygame.draw.rect(self.screen, (12, 24, 46), box, border_radius=4)
        self.screen.blit(surface, (x, y))
        self.screen.set_clip(None)

    def draw_inspector(self, y):
        selected = self.world.organisms.get(self.selected_id)
        x = self.sidebar.x + 20
        self.label("ECOSYSTEM", x, y, 13, ACCENT)
        self.label(f"{len(self.world.organisms):03d}", x, y + 24, 34)
        self.label(f"/ {self.world.config.population_cap} organisms", x + 83, y + 41, 15, MUTED)
        self.row("Births / deaths / catches", f"{self.world.births} / {self.world.deaths} / {self.world.catches}", y + 65)
        minutes, seconds = divmod(int(self.world.time), 60)
        self.row("Simulation time", f"{minutes:02d}:{seconds:02d}", y + 90)
        self.row("Food available", len(self.world.food), y + 115, GOLD)
        self.divider(y + 145)
        self.label("AVERAGE INHERITED TRAITS", x, y + 157, 13, ACCENT)
        average = self.world.averages()
        for offset, label, value, unit in ((182, "Speed trait", average.speed, "u/s"),
                                           (207, "Sensing radius", average.sense, "u"),
                                           (232, "Body radius", average.size, "u")):
            color = PALETTE[3] if label == "Speed trait" else (PALETTE[4] if label == "Sensing radius" else PALETTE[1])
            self.row(label, f"{value:.1f} {unit}" if self.world.organisms else "—", y + offset, color)
        self.divider(y + 262)
        self.label("ORGANISM INSPECTOR", x, y + 274, 13, ACCENT)
        if selected and "follow" in self.buttons:
            self.button("follow", "Unfollow [F]" if self.follow_id else "Follow [F]", bool(self.follow_id))
        if selected:
            self.label(f"{selected.species.title()} #{selected.id:04d} · Gen {selected.generation}", x, y + 297, 20, organism_color(selected))
            self.row("Energy", f"{selected.energy:.1f} / {self.world.config.energy_capacity:.0f}", y + 326)
            bar = pygame.Rect(x, y + 350, self.sidebar.width - 40, 5)
            pygame.draw.rect(self.screen, LINE, bar, border_radius=2)
            pygame.draw.rect(self.screen, organism_color(selected), (bar.x, bar.y, max(0, round(bar.width * selected.energy / self.world.config.energy_capacity)), 5), border_radius=2)
            self.row("Age", f"{selected.age:.1f} / {self.world.maximum_age(selected.species):.0f} s", y + 367)
            self.row("Speed trait", f"{selected.traits.speed:.2f} u/s", y + 390)
            self.row("Sensing radius", f"{selected.traits.sense:.2f} u", y + 413)
            self.row("Body radius", f"{selected.traits.size:.2f} u", y + 436)
            parent = f"#{selected.parent_id:04d}" if selected.parent_id else "Founder"
            habitat = LABELS[self.world.habitats.region_at(selected.x, selected.y)]
            self.row("Parent / habitat", f"{parent} / {habitat}", y + 459)
            if self.world.config.rules_version == 2:
                if selected.species == "predator":
                    remaining = self.world.handling.get(selected.id, 0)
                    activity = f"Digesting / {remaining:.1f} s" if remaining else "Satiated" if selected.energy >= 170 else "Seeking prey"
                    self.row("Activity", activity, y + 482)
                else:
                    from .ecology import efficiencies
                    foods = (name for name, efficiency in zip(("Small", "Medium", "Large"), efficiencies(selected.traits.size)) if efficiency >= .25)
                    self.row("Digestible food", " / ".join(foods), y + 482)
        else:
            self.label("Organism has died." if self.selected_id else "Click an organism to inspect it.", x, y + 307, 15)
            self.label("Its ring shows the sensing radius.", x, y + 335, 13, MUTED)
            self.label("Traits pass to offspring with small", x, y + 374, 13, MUTED)
            self.label("mutations. Survival shapes the rest.", x, y + 394, 13, MUTED)
        # Lineage occupies the space below the inspector in Details.
        legend_y = 0 if self.observatory.tab == "cell" else self.sidebar.bottom - 78
        if legend_y < y + 500:
            return
        self.divider(legend_y - 12)
        self.label("COLOR = INHERITED BODY SIZE", x, legend_y, 13, MUTED)
        palette = PREDATOR_PALETTE if selected and selected.species == "predator" else PALETTE
        for i, color in enumerate(palette):
            pygame.draw.rect(self.screen, color, (x + i * 52, legend_y + 26, 46, 4), border_radius=2)
        self.label("3         4.5         6         7.5         9", x, legend_y + 38, 13, MUTED)

    def run(self, frames: int | None = None, screenshot: str | None = None):
        render_clock = pygame.time.Clock()
        rendered = 0
        try:
            while self.running and (frames is None or rendered < frames):
                # Preserve all elapsed time; fixed ticks are never dropped to raise FPS.
                elapsed = render_clock.tick(60) / 1000
                for event in pygame.event.get():
                    self.handle_event(event)
                if self._discard_elapsed:
                    render_clock.tick()
                    elapsed = 0.0
                    self._discard_elapsed = False
                self.update(elapsed)
                self.fps = render_clock.get_fps()
                self.draw()
                rendered += 1
            if screenshot:
                path = writable_destination(screenshot)
                path.parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(self.screen, str(path))
        finally:
            self.close_recovery()
            self.save_preferences()
            pygame.quit()


def main():
    from .launch_options import parse_options
    parser, args, settings = parse_options()
    app = App(settings=settings, preferences=Preferences())
    if args.load and not app.load_file(args.load):
        pygame.quit()
        parser.exit(2, app.observatory.world_notice + "\n")
    if not args.load:
        app.offer_recovery()
    app.run(args.frames, args.screenshot)
