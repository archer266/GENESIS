"""Small Pygame file picker. No Tk or platform GUI dependencies."""

from pathlib import Path
import pygame
from .user_files import Preferences, writable_destination


class WorldFilePicker:
    def __init__(self, saving, seed, tick, directory=None, extension=".json", default_name=None):
        self.saving = saving
        self.screen = pygame.display.get_surface()
        self.background = self.screen.copy()
        self.font = pygame.font.SysFont("Segoe UI,Arial", 16)
        self.small = pygame.font.SysFont("Segoe UI,Arial", 13)
        self.extension = extension
        initial = Path(directory) if directory else Preferences().directory("save")
        self.directory = initial if initial.is_dir() else Path.home()
        default = default_name or f"genesis_seed{seed}_tick{tick}{extension}"
        self.text = {"folder": str(self.directory), "filename": default if saving else ""}
        self.focus = "filename"
        self.replace_text = True
        self.entries = []
        self.scroll = 0
        self.status = "Enter a filename or full path. Load opens paused."
        self.confirm_overwrite = None
        self.running, self.result = True, ""
        self.navigate(self.directory)
        self.layout()

    def layout(self):
        width, height = self.screen.get_size()
        self.box = pygame.Rect(0, 0, min(width - 40, 800), min(height - 40, 590))
        self.box.center = self.screen.get_rect().center
        x, y, w, h = self.box
        self.controls = {"folder": pygame.Rect(x + 18, y + 56, w - 146, 32),
                         "go": pygame.Rect(x + w - 116, y + 56, 98, 32),
                         "up": pygame.Rect(x + 18, y + 98, 124, 28),
                         "filename": pygame.Rect(x + 18, y + h - 91, w - 36, 33),
                         "cancel": pygame.Rect(x + w - 232, y + h - 44, 96, 30),
                         "accept": pygame.Rect(x + w - 126, y + h - 44, 108, 30)}
        self.list_rect = pygame.Rect(x + 18, y + 139, w - 36, h - 275)
        self.visible_rows = self.list_rect.height // 27

    def navigate(self, path):
        try:
            target = Path(path).expanduser().resolve()
            if not target.is_dir():
                raise ValueError("Folder does not exist.")
            entries = []
            for entry in target.iterdir():
                if entry.is_dir() or entry.suffix.lower() == self.extension:
                    entries.append(entry)
                if len(entries) >= 2000:
                    break
            self.entries = sorted(entries, key=lambda p: (not p.is_dir(), p.name.casefold()))
            self.directory = target
            self.text["folder"] = str(target)
            self.scroll = 0
            self.status = f"Folders + {self.extension} files (up to 2,000). You can also type a full path."
        except (OSError, ValueError) as error:
            self.status = f"Cannot open folder: {getattr(error, 'strerror', None) or error}"

    def accept(self):
        try:
            name = self.text["filename"].strip()
            if not name:
                raise ValueError("Enter a filename or full path.")
            path = (self.directory / Path(name).expanduser()).resolve()
            if self.saving and not path.suffix:
                path = path.with_suffix(self.extension)
            if path.suffix.lower() != self.extension:
                raise ValueError(f"Choose a {self.extension} file.")
            if path.is_dir():
                raise ValueError("Choose a file, not a folder.")
            if not self.saving and not path.is_file():
                raise ValueError("World file does not exist.")
            if self.saving:
                writable_destination(path)
                if self.extension == ".csv" and path.exists():
                    raise ValueError("CSV already exists. Choose a new filename.")
            if self.saving and path.exists() and self.confirm_overwrite != path:
                self.confirm_overwrite = path
                self.status = "File exists. Click Replace save (or Enter again) to overwrite it."
                return
            self.result, self.running = str(path), False
        except (ValueError, OSError) as error:
            self.status = str(error)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            pygame.event.post(event)  # Deliver the close request to the app too.
        elif event.type == pygame.VIDEORESIZE:
            target = (max(960, event.w), max(720, event.h))
            if self.screen.get_size() != target:
                self.screen = pygame.display.set_mode(target, pygame.RESIZABLE)
            self.layout()
        elif event.type == pygame.TEXTINPUT and self.focus:
            self.text[self.focus] = (("" if self.replace_text else self.text[self.focus]) + event.text)[:4096]
            self.replace_text = False
            self.confirm_overwrite = None
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.focus == "folder":
                    self.navigate(self.text["folder"])
                else:
                    self.accept()
            elif event.key == pygame.K_TAB:
                self.focus = "folder" if self.focus == "filename" else "filename"
                self.replace_text = True
            elif self.focus and event.key == pygame.K_a and getattr(event, "mod", 0) & pygame.KMOD_CTRL:
                self.replace_text = True
            elif self.focus and event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                self.text[self.focus] = "" if self.replace_text else self.text[self.focus][:-1]
                self.replace_text = False
                self.confirm_overwrite = None
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(max(0, len(self.entries) - self.visible_rows), self.scroll - event.y * 3))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.controls.items():
                if not rect.collidepoint(event.pos):
                    continue
                if key in self.text:
                    self.focus, self.replace_text = key, True
                elif key == "go":
                    self.navigate(self.text["folder"])
                elif key == "up":
                    self.navigate(self.directory.parent)
                elif key == "cancel":
                    self.running = False
                elif key == "accept":
                    self.accept()
                return
            if self.list_rect.collidepoint(event.pos):
                index = self.scroll + (event.pos[1] - self.list_rect.y) // 27
                if index < len(self.entries):
                    entry = self.entries[index]
                    if entry.is_dir():
                        self.navigate(entry)
                    else:
                        self.text["filename"] = entry.name
                        self.focus, self.replace_text = "filename", True
                        self.confirm_overwrite = None

    def draw(self):
        self.layout()
        if self.background.get_size() != self.screen.get_size():
            self.background = pygame.transform.smoothscale(self.background, self.screen.get_size())
        self.screen.blit(self.background, (0, 0))
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((3, 8, 23, 205))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, (13, 25, 49), self.box, border_radius=12)
        pygame.draw.rect(self.screen, (54, 230, 255), self.box, 1, border_radius=12)

        def label(text, x, y, small=False, color=(234, 243, 255)):
            self.screen.blit((self.small if small else self.font).render(text, True, color), (x, y))

        label(("EXPORT CSV" if self.extension == ".csv" else "SAVE WORLD") if self.saving else "LOAD WORLD · OPENS PAUSED", self.box.x + 18, self.box.y + 13)
        label("Simulation stays still while choosing a file. Escape cancels.", self.box.x + 18, self.box.y + 35, True)
        for key, rect in self.controls.items():
            pygame.draw.rect(self.screen, (17, 43, 68) if key == self.focus else (9, 18, 37), rect, border_radius=5)
            pygame.draw.rect(self.screen, (54, 230, 255) if key == self.focus or key == "accept" else (44, 62, 85), rect, 1, border_radius=5)
            if key in self.text:
                value = self.text[key]
                if key == self.focus and self.replace_text:
                    pygame.draw.rect(self.screen, (27, 66, 89), rect.inflate(-8, -8))
                while value and self.font.size(value)[0] > rect.width - 16:
                    value = value[1:]
                label(value, rect.x + 8, rect.y + 5)
            else:
                text = {"go": "Open folder", "up": "Up one folder", "cancel": "Cancel",
                        "accept": "Replace save" if self.confirm_overwrite else (("Export CSV" if self.extension == ".csv" else "Save World") if self.saving else "Load World")}[key]
                surface = self.small.render(text, True, (234, 243, 255))
                self.screen.blit(surface, surface.get_rect(center=rect.center))
        self.screen.set_clip(pygame.Rect(self.box.x + 150, self.box.y + 99, self.box.width - 168, 32))
        label(self.status, self.box.x + 150, self.box.y + 104, True, (255, 205, 94))
        self.screen.set_clip(self.list_rect)
        pygame.draw.rect(self.screen, (7, 16, 34), self.list_rect)
        for index, entry in enumerate(self.entries[self.scroll:self.scroll + self.visible_rows]):
            row = pygame.Rect(self.list_rect.x, self.list_rect.y + index * 27, self.list_rect.width, 26)
            if entry.name == self.text["filename"]:
                pygame.draw.rect(self.screen, (20, 52, 73), row)
            is_directory = entry.is_dir()
            label(("[folder]  " if is_directory else f"[{self.extension[1:]}]    ") + entry.name, row.x + 8, row.y + 3,
                  color=(54, 230, 255) if is_directory else (234, 243, 255))
        self.screen.set_clip(None)
        label("Filename / full path   (click to replace; Ctrl+A selects all)", self.box.x + 18, self.box.bottom - 115, True)
        pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()
        pygame.key.start_text_input()
        try:
            while self.running:
                self.draw()
                for event in pygame.event.get():
                    self.handle_event(event)
                    if not self.running:
                        break
                clock.tick(60)
        finally:
            pygame.key.stop_text_input()
        return self.result


def choose_world_file(saving: bool, seed: int, tick: int, directory=None) -> str:
    return WorldFilePicker(saving, seed, tick, directory).run()
