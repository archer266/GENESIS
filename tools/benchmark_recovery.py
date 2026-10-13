"""Measure recovery costs against a validated, populated world; no rendering."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import platform
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.persistence import load_world, document
from genesis.recovery import write_recovery

parser = argparse.ArgumentParser()
parser.add_argument('world', type=Path)
parser.add_argument('--output', type=Path, default=Path('artifacts/recovery-costs.json'))
args = parser.parse_args()
loaded = load_world(args.world)
baseline = document(loaded.world, loaded.clock, loaded.history)
rows = []
with tempfile.TemporaryDirectory(prefix='Genesis recovery benchmark ') as root:
    for _ in range(5):
        start = time.perf_counter()
        snapshot = document(loaded.world, loaded.clock, loaded.history, defer_archives=True)
        capture = time.perf_counter() - start
        elapsed = write_recovery(root, snapshot)
        rows.append(dict(capture_ms=capture*1000, write_ms=elapsed*1000))
    # Observe foreground responsiveness while the actual writer owns the GIL
    # intermittently. This is a scheduling probe, not a rendered frame benchmark.
    with ThreadPoolExecutor(max_workers=1) as worker:
        snapshot = document(loaded.world, loaded.clock, loaded.history, defer_archives=True)
        future = worker.submit(write_recovery, root, snapshot)
        gaps = []
        previous = time.perf_counter()
        while not future.done():
            time.sleep(.001)
            now = time.perf_counter()
            gaps.append((now-previous)*1000)
            previous = now
        future.result()
assert document(loaded.world, loaded.clock, loaded.history) == baseline
result = dict(platform=platform.platform(), python=platform.python_version(),
              fixture=str(args.world), population=len(loaded.world.organisms),
              lineage=len(loaded.world.lineage.records), history=len(loaded.history.samples),
              samples=rows, foreground_probe_max_gap_ms=max(gaps),
              foreground_probe_p95_gap_ms=sorted(gaps)[int(.95*(len(gaps)-1))],
              rng_and_model_unchanged=True)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
