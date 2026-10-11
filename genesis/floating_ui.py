"""Floating settings, isolated input routing and session-only glass presentation."""
import pygame
import logging
from .file_dialogs import WorldFilePicker
from .user_files import writable_destination
from . import observatory_ui as legacy
from .observatory_ui import ObservatoryPanel, TEXT, MUTED, ACCENT
from .observatory import ExperimentSettings, statistics
from .presets import PRESETS, preset_name
from .persistence import load_world, SaveError
from .glass import button
from .lineage_ui import LineageView
from .environment import DEFAULTS
from .environment_ui import draw_environment
from .diagnostics_ui import draw_diagnostics


class FloatingPanel(ObservatoryPanel):
    TABS = (("settings", "Experiment"), ("history", "Observatory"), ("worlds", "Worlds"), ("appearance", "Appearance"))
    OBS = (("cell", "Overview"), ("history", "History"), ("evolution", "Traits"), ("habitats", "Habitats"), ("environment", "Events"), ("diagnostics", "Diagnostics"))
    FIELDS = ObservatoryPanel.FIELDS + (("seasons_enabled", "Seasons", "Off / On"),
              ("season_length", "Cycle seconds", "40-600"), ("droughts_enabled", "Droughts", "Off / On"),
              ("drought_duration", "Drought seconds", "5-60"), ("drought_interval", "Min. gap seconds", "30-300"))
    SWITCHES = ("predator_enabled", "habitat_enabled", "seasons_enabled", "droughts_enabled")

    def __init__(self, settings):
        super().__init__(settings)
        self.opened = False
        self.minimized = False
        self.tab = "settings"
        self.rect = pygame.Rect(0, 24, 460, 620)
        self.placed = False
        self.scrolls = {}
        self.drag = None
        self.keyboard_focus = None
        self.pending = None
        self.confirm_text = ""
        self.content_buttons = {}
        self.content_inputs = {}
        self.titles = {}
        self.disabled = set()
        self.pointer = (0, 0)
        self.content_surface = None
        self.hint_until = 0
        self.hover_hint = ""
        self.hover_hint_until = 0
        self.lineage_view = LineageView()
        self.event_offset = 0

    def visible_fields(self):
        return [row for row in self.FIELDS
                if not (row[0] == "initial_predators" and self.values["predator_enabled"] == "0")
                and not (row[0] == "map_seed" and self.values["habitat_enabled"] == "0")
                and not (row[0] == "season_length" and self.values["seasons_enabled"] == "0")
                and not (row[0] in ("drought_duration", "drought_interval") and self.values["droughts_enabled"] == "0")]

    def draft_settings(self):
        # Hidden drafts remain intact. Only effective settings enter the model.
        values = dict(self.values)
        if values["predator_enabled"] == "0":
            values["initial_predators"] = "0"
        if values["habitat_enabled"] == "0":
            values["map_seed"] = "42"
        for toggle, keys in (("seasons_enabled", ("season_length",)), ("droughts_enabled", ("drought_duration", "drought_interval"))):
            if values[toggle] == "0":
                for key in keys:
                    values[key] = str(DEFAULTS[key])
        return ExperimentSettings.from_text(values)

    @property
    def setup_end(self):
        return 109 + len(self.visible_fields())*39

    @property
    def section(self):
        return "history" if self.tab in dict(self.OBS) else self.tab

    def show(self, app, tab=None):
        if not self.opened:
            self.hint_until = app.ui_time + 5
        self.opened, self.minimized = True, False
        app.ui_hidden = False
        app.drag_button = None
        if tab is not None:
            self.tab = tab
        self.focus(None)
        self.layout(app)

    def toggle(self, app):
        if self.opened and not self.minimized:
            self.opened = False
            self.focus(None)
        else:
            self.show(app)
        self.layout(app)

    def confirm(self, app, text, callback):
        self.pending, self.confirm_text = callback, text
        self.focus(None)
        self.keyboard_focus = "cancel"
        app.drag_button = None
        self.layout(app)

    def confirm_restart(self, app):
        self.confirm(app, f"Restart seed {app.seed}? The current world and retained history will be replaced.", app.reset)

    def content_height(self):
        if self.tab == "settings":
            return self.setup_end + 261 + len(PRESETS)*158 + min(1200, len(self.notice)//40*19)
        if self.tab == "worlds":
            return 515 + min(2600, (len(self.world_notice)+len(self.notice))//40*19)
        return {"history": 700, "evolution": 700, "habitats": 590, "cell": 1540, "appearance": 925, "environment": 950, "diagnostics": 1230}[self.tab]

    def layout(self, app):
        screen = app.screen.get_rect()
        if not self.placed:
            self.rect.right = screen.right-24
            self.rect.height = min(620, screen.h-130)
            self.placed = True
        self.rect.size = (min(max(400, self.rect.w), min(720, screen.w-24)),
                          min(max(360, self.rect.h), screen.h-96))
        self.rect.clamp_ip(screen.inflate(-24, -24))
        app.sidebar = self.rect.copy()  # Compatibility for reused read-only charts.
        self.header = pygame.Rect(self.rect.x+16, self.rect.y+8, self.rect.w-108, 36)
        self.grip = pygame.Rect(self.rect.right-25, self.rect.bottom-25, 22, 22)
        self.edge = pygame.Rect(screen.right-94, max(16, min(screen.h-130, self.rect.y)), 82, 34)
        self.buttons, self.inputs = {}, {}
        self.content_buttons, self.content_inputs, self.titles, self.disabled = {}, {}, {}, set()
        self.confirm_rect = pygame.Rect(0, 0, min(450, screen.w-48), 190)
        self.confirm_rect.center = screen.center
        if self.pending:
            self.buttons = {"cancel": pygame.Rect(self.confirm_rect.x+22, self.confirm_rect.bottom-57, 190, 35),
                            "confirm": pygame.Rect(self.confirm_rect.right-212, self.confirm_rect.bottom-57, 190, 35)}
            return
        if app.ui_hidden or not self.opened or self.minimized:
            return
        self.buttons["minimize"] = pygame.Rect(self.rect.right-83, self.rect.y+12, 30, 29)
        self.buttons["close"] = pygame.Rect(self.rect.right-46, self.rect.y+12, 30, 29)
        width = (self.rect.w-32)//4
        for i, (key, _) in enumerate(self.TABS):
            self.buttons[key] = pygame.Rect(self.rect.x+16+i*width, self.rect.y+54, width-4, 32)
        top = self.rect.y+100
        if self.section == "history":
            width = (self.rect.w-32)//3
            for i, (key, _) in enumerate(self.OBS):
                self.buttons["view_"+key] = pygame.Rect(self.rect.x+16+(i%3)*width, top+(i//3)*35, width-4, 29)
            top += 77
        self.content = pygame.Rect(self.rect.x+8, top, self.rect.w-16, self.rect.bottom-top-28)
        self.scroll_max = max(0, self.content_height()-self.content.h)
        self.scrolls[self.tab] = max(0, min(self.scroll_max, self.scrolls.get(self.tab, 0)))
        w = self.content.w
        def control(key, title, y, x=18, width=None):
            self.content_buttons[key] = pygame.Rect(x, y, width or w-36, 34)
            self.titles[key] = title
        if self.tab == "settings":
            for i, (key, title, _) in enumerate(self.visible_fields()):
                y = 77+i*39+(32 if key in DEFAULTS else 0)
                if key in self.SWITCHES:
                    control(key, {"predator_enabled": "Predators", "habitat_enabled": "Habitats"}.get(key, title), y)
                else:
                    self.content_inputs[key] = pygame.Rect(w-166, y, 145, 30)
            end = self.setup_end
            control("defaults", "Defaults", end+25, width=100)
            control("new_seed", "New seed draft", end+25, x=126, width=w-144)
            control("start", "Start new experiment...", end+72)
            control("reset", "Restart same seed...  [R]", end+116)
            for i, preset in enumerate(PRESETS):
                control("preset_"+str(i), preset.name, end+202+i*158)
        elif self.tab == "worlds":
            control("save_world", "Save World   [Ctrl+S]", 66)
            control("load_world", "Load World...   [Ctrl+L]", 111)
            control("export", "Export retained history as CSV", 156)
            control("export_lineage", "Export lineage archive as CSV", 201)
            control("export_diagnostics", "Export diagnostics as CSV", 246)
        elif self.tab == "appearance":
            control("guide", "Show quick guide", 805)
            control("environment_chip", "Environment status chip / "+("On" if app.show_environment else "Off"), 755)
            control("effects", "Effects  [E]   /   "+("On" if app.visuals.enabled else "Off"), 61)
            control("habitats", "Habitat overlay  [H]   /   "+("On" if app.show_habitats else "Off"), 107)
            control("transparency", "Reduce Transparency   /   "+("On" if app.glass.reduced else "Off"), 153)
            control("fullscreen", "Windowed  [F11]" if app.fullscreen else "Fullscreen  [F11]", 220)
            control("hide_ui", "Hide interface  [I]", 266)
            control("fit", "Fit World  [Home]", 312)
            control("follow", "Unfollow  [F]" if app.follow_id else "Follow selected  [F]", 358)
            if app.selected_id not in app.world.organisms:
                self.disabled.add("follow")
        elif self.tab == "evolution":
            control("species", self.species.title()+" / switch", 16, x=w-146, width=126)
        elif self.tab == "cell":
            control("lineage_jump", "Lineage", 6, x=w-130, width=110)
            control("follow", "Unfollow [F]" if app.follow_id else "Follow [F]", 284, x=w-130, width=110)
            if app.selected_id not in app.world.organisms:
                self.disabled.add("follow")
            self.lineage_view.layout(app, self, control)
        elif self.tab == "environment":
            control("events_newer", "Newer", 369, width=130)
            control("events_older", "Older", 369, x=158, width=130)
            if self.event_offset == 0:
                self.disabled.add("events_newer")
            if self.event_offset+12 >= len(app.world.environment.history):
                self.disabled.add("events_older")
        offset = self.scrolls[self.tab]
        for source, target in ((self.content_buttons, self.buttons), (self.content_inputs, self.inputs)):
            for key, rect in source.items():
                mapped = rect.move(self.content.x, self.content.y-offset)
                clipped = mapped.clip(self.content)
                if clipped.w and clipped.h:
                    target[key] = clipped
        self.track = pygame.Rect(self.rect.right-9, self.content.y, 3, self.content.h)
        thumb_h = max(24, round(self.content.h*self.content.h/self.content_height()))
        self.thumb = pygame.Rect(self.track.x-3, self.track.y+round(offset/max(1,self.scroll_max)*(self.track.h-thumb_h)), 9, thumb_h)

    def ensure_visible(self, app, key):
        rect = self.content_inputs.get(key, self.content_buttons.get(key))
        if rect is not None:
            offset = self.scrolls.get(self.tab, 0)
            if rect.top < offset:
                offset = rect.top
            elif rect.bottom > offset+self.content.h:
                offset = rect.bottom-self.content.h
            self.scrolls[self.tab] = offset
            self.layout(app)

    def handle_event(self, app, event):
        self.layout(app)
        point = getattr(event, "pos", pygame.mouse.get_pos())
        if hasattr(event, "pos"):
            self.pointer = point
        if self.pending:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.pending = None
                elif event.key == pygame.K_TAB:
                    self.keyboard_focus = "confirm" if self.keyboard_focus == "cancel" else "cancel"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.activate(app, self.keyboard_focus)
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for key, rect in self.buttons.items():
                    if rect.collidepoint(point):
                        self.activate(app, key)
                        break
            return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL, pygame.TEXTINPUT)
        if event.type == pygame.WINDOWFOCUSLOST:
            self.drag = None
        if self.drag:
            if event.type == pygame.MOUSEBUTTONUP:
                self.drag = None
                return True
            if event.type == pygame.MOUSEMOTION:
                mode, origin, rect = self.drag
                dx, dy = point[0]-origin[0], point[1]-origin[1]
                if mode == "move":
                    self.rect.topleft = (rect.x+dx, rect.y+dy)
                elif mode == "resize":
                    self.rect.size = (rect.w+dx, rect.h+dy)
                else:
                    self.scrolls[self.tab] = rect + dy*self.scroll_max/max(1,self.track.h-self.thumb.h)
                self.layout(app)
                return True
            if event.type in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN):
                return True
        if app.ui_hidden:
            return False
        if self.minimized and self.opened and self.edge.collidepoint(point):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.show(app)
            return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL, pygame.MOUSEMOTION)
        if not self.opened or self.minimized:
            return False
        if self.active_field and event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.keyboard_focus = self.active_field
            self.focus(None)
        if self.active_field and event.type in (pygame.TEXTINPUT, pygame.KEYDOWN):
            previous_field = self.active_field
            super().handle_event(app, event)
            self.keyboard_focus = self.active_field or previous_field
            if self.active_field:
                self.ensure_visible(app, self.active_field)
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.opened = False
                return True
            if event.key == pygame.K_TAB:
                keys = [k for k in self.buttons if k not in self.content_buttons]
                keys += sorted([*self.content_inputs, *self.content_buttons],
                               key=lambda k: (self.content_inputs.get(k, self.content_buttons.get(k)).y,
                                              self.content_inputs.get(k, self.content_buttons.get(k)).x))
                keys = [k for k in keys if k not in self.disabled]
                step = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                index = keys.index(self.keyboard_focus) if self.keyboard_focus in keys else (-1 if step == 1 else 0)
                self.keyboard_focus = keys[(index+step)%len(keys)]
                self.ensure_visible(app, self.keyboard_focus)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.keyboard_focus:
                if self.keyboard_focus in self.content_inputs:
                    self.focus(self.keyboard_focus)
                else:
                    self.activate(app, self.keyboard_focus)
                return True
            if event.key in (pygame.K_PAGEDOWN, pygame.K_PAGEUP):
                self.scrolls[self.tab] += self.content.h*(1 if event.key == pygame.K_PAGEDOWN else -1)
                self.layout(app)
                return True
        inside = self.rect.collidepoint(point)
        if event.type == pygame.MOUSEWHEEL and inside:
            if not (self.tab == "cell" and self.lineage_view.wheel(self, point, -event.y)):
                self.scrolls[self.tab] -= event.y*42
            self.layout(app)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and inside:
            app.drag_button = None
            if event.button == 1:
                if self.grip.collidepoint(point):
                    self.drag = ("resize", point, self.rect.copy())
                elif self.header.collidepoint(point):
                    self.drag = ("move", point, self.rect.copy())
                elif self.scroll_max and self.thumb.collidepoint(point):
                    self.drag = ("scroll", point, self.scrolls[self.tab])
                else:
                    for key, rect in self.inputs.items():
                        if rect.collidepoint(point):
                            self.keyboard_focus = key
                            self.focus(key)
                            return True
                    self.focus(None)
                    for key, rect in self.buttons.items():
                        if rect.collidepoint(point):
                            self.keyboard_focus = key
                            self.activate(app, key)
                            break
            return True
        if event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and inside:
            # Crossing into UI cancels world drag instead of moving behind glass.
            app.drag_button = None
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.focus(None)
            self.keyboard_focus = None
        return False

    def activate(self, app, key):
        if key in self.disabled:
            return
        if key in ("cancel", "confirm"):
            callback = self.pending
            self.pending = None
            self.keyboard_focus = None
            if key == "confirm" and callback:
                callback()
        elif key in dict(self.TABS) or key.startswith("view_"):
            self.tab = key.removeprefix("view_")
            if self.tab == "cell" and self.lineage_view.view_id is None:
                self.lineage_view.view(app.selected_id)
            self.focus(None)
        elif key == "close":
            self.opened = False
            self.focus(None)
        elif key == "minimize":
            self.minimized = True
            self.focus(None)
        elif key == "species":
            self.species = "predator" if self.species == "prey" else "prey"
        elif key in self.SWITCHES:
            self.values[key] = "0" if self.values[key] == "1" else "1"
            self.focus(None)
        elif key == "defaults":
            self.values = ExperimentSettings().text_values()
            self.notice, self.notice_error = "Defaults prepared. Start new to apply.", False
        elif key == "new_seed":
            self.values["seed"] = str((app.seed+1+legacy.secrets.randbelow(2**32-1)) % 2**32)
            self.notice, self.notice_error = "New seed prepared. Start new to apply.", False
        elif key.startswith("preset_"):
            preset = PRESETS[int(key.split("_")[1])]
            self.values = preset.settings.text_values()
            self.notice, self.notice_error = preset.name+" prepared. Edit fields, then Start new.", False
            self.scrolls["settings"] = 0
        elif key == "start":
            self.start_experiment(app)
        elif key == "reset":
            self.confirm_restart(app)
        elif key in ("save_world", "load_world"):
            self.file_action(app, key == "save_world")
        elif key == "export":
            self.export_action(app, "history")
        elif key == "export_diagnostics":
            self.export_action(app, "diagnostics")
        elif key == "export_lineage":
            self.export_action(app, "lineage")
        elif key == "lineage_jump":
            if self.lineage_view.view_id is None:
                self.lineage_view.view(app.selected_id)
            self.scrolls["cell"] = 520
        elif key.startswith(("lineage_", "relative_", "ancestors_", "children_")):
            self.lineage_view.activate(app, self, key)
        elif key == "guide":
            app.show_guide()
        elif key == "effects":
            app.visuals.toggle()
        elif key == "habitats":
            app.show_habitats = not app.show_habitats
        elif key == "transparency":
            app.glass.reduced = not app.glass.reduced
        elif key == "environment_chip":
            app.show_environment = not app.show_environment
        elif key in ("events_newer", "events_older"):
            self.event_offset = max(0, min(max(0, len(app.world.environment.history)-12), self.event_offset+(-12 if key == "events_newer" else 12)))
        elif key == "fullscreen":
            app.toggle_fullscreen()
        elif key == "hide_ui":
            app.toggle_ui()
        elif key == "fit":
            app.fit_world()
        elif key == "follow":
            app.toggle_follow()
        self.layout(app)

    def export_action(self, app, kind):
        app._discard_elapsed = True
        try:
            name = f"{kind}_seed{app.seed}_tick{app.world.ticks}_{legacy.uuid.uuid4().hex[:8]}.csv"
            path = WorldFilePicker(True, app.seed, app.world.ticks,
                                   app.file_directory("export"), ".csv", name).run()
            if path:
                {"history": self.export, "lineage": self.export_lineage,
                 "diagnostics": self.export_diagnostics}[kind](app, path)
            else:
                self.notice, self.notice_error = "Export canceled.", False
        except Exception as error:
            logging.getLogger("genesis").exception("Export dialog failed")
            self.notice, self.notice_error = f"Export failed: {error}", True
        app.screen = pygame.display.get_surface()
        app._layout()

    def export_diagnostics(self, app, path=None):
        if path is None:
            path = app.file_directory("export") / f"diagnostics_seed{app.seed}_tick{app.world.ticks}_{legacy.uuid.uuid4().hex[:8]}.csv"
        try:
            self.saved_path = app.world.diagnostics.export_csv(writable_destination(path), app.world, app.settings)
            app.remember_directory("export", self.saved_path)
            self.notice, self.notice_error = f"Saved diagnostics: {self.saved_path}", False
        except (OSError, ValueError) as error:
            logging.getLogger("genesis").exception("CSV export failed")
            self.notice, self.notice_error = f"Diagnostics export failed: {error}", True

    def export_lineage(self, app, path=None):
        if path is None:
            path = app.file_directory("export") / f"lineage_seed{app.seed}_tick{app.world.ticks}_{legacy.uuid.uuid4().hex[:8]}.csv"
        try:
            self.saved_path = app.world.lineage.export_csv(writable_destination(path), app.settings)
            app.remember_directory("export", self.saved_path)
            self.notice = f"Saved {len(app.world.lineage.records)} lineage records:\n{self.saved_path}"
            self.notice_error = False
        except (OSError, ValueError) as error:
            logging.getLogger("genesis").exception("CSV export failed")
            self.notice, self.notice_error = f"Lineage export failed: {error}", True

    def start_experiment(self, app):
        try:
            settings = self.draft_settings()
        except ValueError as error:
            self.notice, self.notice_error = str(error), True
            self.scrolls["settings"] = self.content_height()
            return
        self.confirm(app, f"Start seed {settings.seed} with {settings.initial_population} prey and {settings.initial_predators} predators? This replaces the current world and history.", lambda: app.start_experiment(settings))

    def file_action(self, app, saving):
        self.show(app, "worlds")
        app._discard_elapsed = True  # Existing modal picker explicitly suspends playback.
        try:
            path = legacy.choose_world_file(saving, app.seed, app.world.ticks, directory=app.file_directory("save"))
            if not path:
                self.world_notice, self.world_notice_error = "Save canceled." if saving else "Load canceled. Current world unchanged.", False
            elif saving:
                app.save_file(path)
            else:
                candidate = load_world(path)  # Validate before asking to replace anything.
                self.confirm(app, f"Load seed {candidate.settings.seed} at {candidate.world.time:.1f}s? Current world and history will be replaced. The loaded world opens paused.", lambda: app.apply_loaded(candidate, path))
        except (SaveError, OSError, ValueError) as error:
            logging.getLogger("genesis").warning("World I/O failed: %s", error)
            self.world_notice, self.world_notice_error = str(error), True
        except Exception as error:
            logging.getLogger("genesis").exception("File dialog failed")
            self.world_notice, self.world_notice_error = f"File dialog failed: {error}", True
        app.screen = pygame.display.get_surface()
        app._layout()

    def draw_button(self, app, key, title, active=False):
        rect = self.content_buttons[key]
        global_rect = rect.move(self.content.x, self.content.y-self.scrolls[self.tab])
        if key in self.SWITCHES:
            enabled = self.values[key] == "1"
            focused = self.keyboard_focus == key
            hover = self.content.collidepoint(self.pointer) and global_rect.collidepoint(self.pointer)
            pygame.draw.rect(app.screen, (34, 49, 70) if hover else (25, 39, 59), rect, border_radius=10)
            if focused:
                pygame.draw.rect(app.screen, (208, 231, 255), rect, 2, border_radius=10)
            app.label(title, rect.x+10, rect.y+7, 15)
            app.label("On" if enabled else "Off", rect.right-91, rect.y+7, 15)
            track = pygame.Rect(rect.right-52, rect.y+6, 43, 23)
            pygame.draw.rect(app.screen, (56, 166, 158) if enabled else (79, 96, 118), track, border_radius=12)
            pygame.draw.circle(app.screen, (248, 253, 255), (track.right-12 if enabled else track.x+12, track.centery), 9)
            return
        button(app, rect, title, active, self.keyboard_focus == key, key in self.disabled,
               self.content.collidepoint(self.pointer) and global_rect.collidepoint(self.pointer))

    def draw_content(self, app):
        size = (self.content.w, self.content_height())
        if self.content_surface is None or self.content_surface.get_size() != size:
            self.content_surface = pygame.Surface(size, pygame.SRCALPHA)
        surface = self.content_surface
        surface.fill((0, 0, 0, 0))
        screen, sidebar, buttons = app.screen, app.sidebar, app.buttons
        app.screen, app.sidebar = surface, pygame.Rect(0, -80, size[0], size[1]+80)
        app.buttons = self.content_buttons
        try:
            if self.tab in ("history", "evolution", "habitats"):
                {"history": self.draw_history, "evolution": self.draw_evolution, "habitats": self.draw_habitats}[self.tab](app)
            elif self.tab == "cell":
                app.draw_inspector(16)
                self.lineage_view.draw(app, self)
            elif self.tab == "environment":
                draw_environment(app, self)
            elif self.tab == "diagnostics":
                draw_diagnostics(app, self)
            elif self.tab == "settings":
                app.label("Experiment", 18, 10, 20)
                self.wrap(app, f"Active: {preset_name(app.settings)} / seed {app.seed}", 18, 40, size[0]-36)
                for key, title, limits in self.visible_fields():
                    if key not in self.content_inputs:
                        continue
                    box = self.content_inputs[key]
                    app.label("Predators (0 off / 1 on)" if key == "predator_enabled" else title, 18, box.y+6, 13)
                    pygame.draw.rect(surface, (24, 37, 56), box, border_radius=8)
                    active = self.active_field == key or self.keyboard_focus == key
                    pygame.draw.rect(surface, (183, 217, 249) if active else (66, 81, 104), box, 2 if active else 1, border_radius=8)
                    if self.active_field == key and self.replace_text:
                        pygame.draw.rect(surface, (52, 76, 101), box.inflate(-8, -8), border_radius=4)
                    surface.set_clip(box.inflate(-12, -2))
                    app.label(self.values[key]+("|" if self.active_field == key and not self.replace_text else ""), box.x+8, box.y+4, 15)
                    surface.set_clip(None)
                section_y = self.content_buttons["seasons_enabled"].y-29
                app.label("Environment", 18, section_y, 17, ACCENT)
                end = self.setup_end
                app.label("Drafts only. Starting replaces this world.", 18, end, 13, MUTED)
                app.label("Starting presets", 18, end+171, 17)
                for i, preset in enumerate(PRESETS):
                    y = end+242+i*158
                    s = preset.settings
                    app.label(f"Seed {s.seed} / {s.initial_population} prey / {s.initial_predators} predators", 18, y, 13, MUTED)
                    app.label(f"Food {s.food_per_second:g}/s / mutation +/-{s.mutation_strength*100:g}%", 18, y+21, 13, MUTED)
                    description = (f"Habitats / map seed {s.map_seed}" if s.habitat_enabled else "Uniform habitat")+" / "+preset.description
                    if s.seasons_enabled or s.droughts_enabled:
                        description = f"Cycle {s.season_length}s; drought {s.drought_duration}s; gaps {s.drought_interval}-{s.drought_interval*2}s. Food pressure; uncertain survival."
                    self.wrap(app, description, 18, y+44, size[0]-36)
                self.wrap(app, self.notice or "Defaults and presets fill drafts only.", 18, end+214+len(PRESETS)*158, size[0]-36, (255, 156, 165) if self.notice_error else MUTED)
            elif self.tab == "worlds":
                app.label("Worlds & exports", 18, 10, 20)
                app.label("Checkpoint the ecosystem. Export its retained history.", 18, 40, 13, MUTED)
                y = self.wrap(app, self.world_notice, 18, 303, size[0]-36, (255, 156, 165) if self.world_notice_error else MUTED)
                y = self.wrap(app, self.notice if self.saved_path or self.notice_error else "CSV includes seeds, experiment settings and sampled statistics.", 18, y+25, size[0]-36, (255, 156, 165) if self.notice_error else MUTED)
                self.wrap(app, "Load validates the file, then asks before replacing this experiment. Save/load picker time is excluded from playback.", 18, y+28, size[0]-36)
            else:
                app.label("Appearance & interaction", 18, 10, 20)
                app.label("Presentation preferences never change the ecosystem.", 18, 40, 13, MUTED)
                self.wrap(app, "Wheel: zoom at cursor. Right or middle drag: pan. Left click: select. F: follow selected. Home: Fit World.\n\nSpace: pause/play. 1 / 2 / 4: speed. O: Settings. I: hide or restore UI. Esc: cancel, close panel, restore UI or exit fullscreen.\n\nE: effects. H: habitat illumination. Water / gardens / dense regions retain their simulation rules when hidden.", 18, 412, size[0]-36)
                for i, title in enumerate(("Water", "Gardens", "Dense")):
                    color = legacy.HABITAT_COLORS[i]
                    pygame.draw.circle(surface, color, (24+i*120, 626), 4)
                    app.label(title, 36+i*120, 617, 13, color)
                app.label("CELL COLOR = INHERITED SPEED", 18, 661, 13, MUTED)
                for i, color in enumerate(legacy.PALETTE):
                    pygame.draw.rect(surface, color, (18+i*66, 693, 58, 4), border_radius=2)
                app.label("<33       33-39      39-45      45-51      >=51", 18, 706, 13, MUTED)
            for key, title in self.titles.items():
                if self.tab != "evolution" or key != "species":
                    self.draw_button(app, key, title)
        finally:
            app.screen, app.sidebar, app.buttons = screen, sidebar, buttons
        app.screen.blit(surface, self.content, pygame.Rect(0, round(self.scrolls[self.tab]), self.content.w, self.content.h))

    def draw(self, app):
        self.layout(app)
        if not app.ui_hidden and self.opened and not self.pending:
            if self.minimized:
                app.glass.draw(app.screen, self.edge, "edge", app.ui_time)
                button(app, self.edge.inflate(-4, -4), "Settings")
            else:
                app.glass.draw(app.screen, self.rect, "panel", app.ui_time)
                app.label("Settings", self.rect.x+20, self.rect.y+17, 17)
                for key, title in (("minimize", "-"), ("close", "x")):
                    button(app, self.buttons[key], title, focused=self.keyboard_focus == key)
                for key, title in self.TABS:
                    button(app, self.buttons[key], title, self.section == key, self.keyboard_focus == key)
                if self.section == "history":
                    for key, title in self.OBS:
                        button(app, self.buttons["view_"+key], "Details" if key == "cell" and app.selected_id else title, self.tab == key, self.keyboard_focus == "view_"+key)
                self.draw_content(app)
                if self.scroll_max:
                    pygame.draw.rect(app.screen, (108, 128, 151), self.thumb, border_radius=4)
                context = ("Drag to move" if self.header.collidepoint(self.pointer) else
                        "Drag to resize" if self.grip.collidepoint(self.pointer) else
                        "")
                if context != self.hover_hint:
                    self.hover_hint, self.hover_hint_until = context, app.ui_time+3
                hint = (context if app.ui_time < self.hover_hint_until else "") or (
                    "Scroll for more" if app.ui_time < self.hint_until and self.scroll_max else "")
                if hint:
                    app.label(hint, self.rect.x+19, self.rect.bottom-23, 13, MUTED)
                for d in (0, 5, 10):
                    pygame.draw.line(app.screen, (128, 148, 171), (self.rect.right-8-d, self.rect.bottom-8), (self.rect.right-8, self.rect.bottom-8-d))
        if self.pending:
            # The world continues behind confirmation; only input is modal.
            app.glass.draw(app.screen, self.confirm_rect, "confirm", app.ui_time)
            app.label("Replace active experiment?", self.confirm_rect.x+22, self.confirm_rect.y+18, 20)
            self.wrap(app, self.confirm_text, self.confirm_rect.x+22, self.confirm_rect.y+56, self.confirm_rect.w-44, TEXT)
            for key, title in (("cancel", "Cancel"), ("confirm", "Replace experiment")):
                button(app, self.buttons[key], title, key == "confirm", self.keyboard_focus == key)
