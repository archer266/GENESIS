"""Non-authoritative desktop preferences, safe destinations and bounded logs."""
from copy import deepcopy
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile

DEFAULTS = dict(version=1, effects=True, habitats=True, environment=True,
                reduced=False, fullscreen=False, guide_seen=False,
                window_size=[1380, 900], window_position=[60, 40],
                panel_rect=[880, 24, 460, 620], panel_tab="settings",
                panel_open=False, panel_minimized=False,
                save_directory="", export_directory="")
TABS = {"settings", "history", "evolution", "habitats", "cell", "appearance", "environment", "diagnostics", "worlds"}


def writable_destination(path):
    path = Path(path).expanduser().resolve()
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
        if path == root or root in path.parents:
            raise ValueError("Choose a location outside the GENESIS application folder.")
    return path


def user_directory():
    override = os.environ.get("GENESIS_USER_DATA_DIR")
    return writable_destination(override or Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "GENESIS")


def validate(raw):
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("Unsupported preferences format; using defaults.")
    result = deepcopy(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if type(default) is bool:
            valid = type(value) is bool
        elif isinstance(default, list):
            valid = isinstance(value, list) and len(value) == len(default) and all(type(n) is int and abs(n) <= 32768 for n in value)
            if valid and key == "window_size":
                valid = 960 <= value[0] <= 16384 and 720 <= value[1] <= 16384
            if valid and key == "panel_rect":
                valid = 400 <= value[2] <= 1600 and 300 <= value[3] <= 1600
        elif key == "panel_tab":
            valid = isinstance(value, str) and value in TABS
        elif key.endswith("directory"):
            valid = isinstance(value, str) and len(value) <= 4096 and "\0" not in value
        else:
            valid = type(value) is int and value == 1
        if not valid:
            raise ValueError(f"Invalid preference '{key}'; using defaults.")
        result[key] = value
    return result


def window_geometry(values, desktop):
    # Restore to the primary display if a previous monitor is unavailable.
    dw, dh = desktop
    w, h = (min(values["window_size"][i], desktop[i]) for i in range(2))
    x, y = values["window_position"]
    return (w, h), (max(0, min(x, dw-w)), max(0, min(y, dh-h)))


class Preferences:
    def __init__(self, root=None):
        self.root = writable_destination(root) if root is not None else user_directory()
        self.path = self.root / "preferences.json"
        self.values = deepcopy(DEFAULTS)
        self.warning = ""
        try:
            if self.path.exists():
                if self.path.stat().st_size > 65536:
                    raise ValueError("Preferences file is too large; using defaults.")
                self.values = validate(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, RecursionError) as error:
            self.warning = f"Preferences reset: {error}"
            logging.getLogger("genesis").warning(self.warning)

    def save(self, values):
        values = validate(values)
        self.root.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.root, suffix=".tmp", delete=False) as stream:
                name = stream.name
                json.dump(values, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            self.values = values
        finally:
            if name and Path(name).exists():
                Path(name).unlink()

    def directory(self, kind):
        previous = self.values[kind+"_directory"]
        try:
            path = writable_destination(previous) if previous else None
            if path and path.is_dir():
                return path
        except (OSError, ValueError):
            pass
        path = self.root / ("Worlds" if kind == "save" else "Exports")
        path.mkdir(parents=True, exist_ok=True)
        return path


def configure_logging(root):
    root = writable_destination(root)
    root.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(root / "genesis.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("genesis")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
