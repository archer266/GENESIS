"""Optional, non-authoritative recovery scheduling. Workers receive detached data only."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
import logging
from pathlib import Path
import time

from .persistence import document, encode_document, atomic_write, load_world, SaveError

INTERVAL = 120.0


def find_recovery(root):
    """Validate before offering recovery; never modify either candidate."""
    errors = []
    for name in ('latest.json', 'previous.json'):
        path = Path(root) / name
        if not path.exists():
            continue
        try:
            loaded = load_world(path)
            if loaded.world.config.rules_version != 2:
                raise SaveError('Obsolete simulation rules.')
            reason = 'Latest recovery unavailable; using the previous valid snapshot.' if name == 'previous.json' else ''
            return loaded, path, reason
        except (OSError, ValueError) as error:
            errors.append(f'{name}: {error}')
    return None, None, 'No valid recovery snapshot. ' + '; '.join(errors) if errors else ''


def write_recovery(root, snapshot):
    """Validate new data first. A failed commit leaves at least the old valid file."""
    start = time.perf_counter()
    # Containers are detached. These shared values are recursively immutable:
    # frozen Sample/Statistics and frozen LineageRecord/Traits. Death replaces
    # archive records; it never mutates a captured birth/death record.
    for container, key in ((snapshot['lineage'], 'records'), (snapshot['history'], 'samples')):
        container[key] = [asdict(row) if is_dataclass(row) else row for row in container[key]]
    content = encode_document(snapshot)
    root = Path(root)
    latest = root / 'latest.json'
    if latest.exists():
        try:
            load_world(latest)
        except (OSError, ValueError):
            pass  # Never rotate corruption over a good previous snapshot.
        else:
            atomic_write(root / 'previous.json', latest.read_text(encoding='utf-8'))
    atomic_write(latest, content)
    return time.perf_counter() - start


class Recovery:
    def __init__(self, root, enabled=True, now=time.monotonic):
        self.root = Path(root) / 'Recovery'
        self.enabled, self.now = enabled, now
        self.pending_choice = False
        self.status = 'Autosave ready / every 2 minutes' if enabled else 'Autosave off'
        self.error = False
        self.epoch = 0
        self.saved_token = None
        self.force = False
        self.deadline = now() + INTERVAL
        self.future = None
        self.executor = None
        self.capture_seconds = self.write_seconds = 0.0

    def changed_world(self):
        self.epoch += 1
        self.force = True

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.deadline = self.now() + INTERVAL
        self.status = 'Autosave ready / every 2 minutes' if enabled else 'Autosave off'
        self.error = False

    def _poll(self):
        if self.future is not None and self.future.done():
            try:
                self.write_seconds = self.future.result()
                self.saved_token = self.inflight_token
                self.status, self.error = 'Recovery saved / latest checkpoint ready', False
            except Exception as error:
                self.status, self.error = f'Autosave failed: {error}', True
                logging.getLogger('genesis').exception('Recovery write failed')
            self.future = None

    def tick(self, world, clock, history, selection=None):
        self._poll()
        if not self.enabled or self.pending_choice or self.future is not None:
            return
        token = (self.epoch, world.ticks)
        if not self.force and self.now() < self.deadline:
            return
        self.deadline = self.now() + INTERVAL
        self.force = False
        if token == self.saved_token:
            return
        try:
            start = time.perf_counter()
            # Called on the UI thread between complete fixed simulation steps.
            snapshot = document(world, clock, history, selection, defer_archives=True)
            self.capture_seconds = time.perf_counter() - start
            if self.executor is None:
                self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='genesis-recovery')
            self.inflight_token = token
            self.future = self.executor.submit(write_recovery, self.root, snapshot)
            self.status, self.error = 'Saving recovery...', False
        except Exception as error:
            self.status, self.error = f'Autosave failed: {error}', True
            logging.getLogger('genesis').exception('Recovery capture failed')

    def close(self, world, clock, history, selection=None):
        # Finish any earlier world first, then checkpoint the current world once.
        if self.future is not None:
            try:
                self.future.result()
            except Exception:
                pass
            self._poll()
        self.force = True
        self.tick(world, clock, history, selection)
        if self.executor is not None:
            self.executor.shutdown(wait=True)
        self._poll()
