"""Publish measured trial summaries; no simulation or parameter selection."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', type=Path, default=Path('reports/balance-revision'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    runs = []
    for path in sorted(args.folder.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if 'snapshots' in data:
            runs.append(data)
    lines = ['# Ecosystem trials: '+args.folder.name, '',
             '60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. '
             'The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. ' +
             ('Manifest records frozen settings and source hashes.' if (args.folder/'manifest.json').exists()
              else 'These initial diagnostic runs preceded manifest capture; no source-hash record is claimed.'), '',
             '| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |',
             '|---|---:|---:|---|---:|---:|---:|']
    def time(value):
        return 'none' if value is None else f'{value:.2f}'
    for r in runs:
        d = r['diagnostics']['totals']
        lines.append(f"| {r['label']} | {r['settings']['seed']} | {r['final']['prey']} / {r['final']['predator']} "
                     f"| {time(r['extinction']['prey'])} / {time(r['extinction']['predator'])} "
                     f"| {d['prey']['births']} / {d['predator']['births']} | {d['predator']['catches']} | {r['cap_fraction']:.2%} |")
    lines += ['', '## Within-world prey diversity', '',
              'Each entry is speed / sensing / body-size IQR, measured within that one world. '
              'Missing means the population was unavailable; nothing is pooled across seeds.', '',
              '| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |',
              '|---|---:|---|---|---|']
    for r in runs:
        by_time = {s['time']: s for s in r['snapshots']}
        entries = []
        for t in (1800, 2700, 3600):
            traits = by_time.get(t, {}).get('traits', {}).get('prey', {})
            entries.append(' / '.join(f"{traits[k]['iqr']:.2f}" if traits.get(k) else 'missing'
                                      for k in ('speed', 'sense', 'size')))
        lines.append(f"| {r['label']} | {r['settings']['seed']} | " + ' | '.join(entries) + ' |')
    (args.output/'RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    for name in ('manifest.json', 'assessment.json', 'summary.csv', 'checkpoints.csv'):
        if (args.folder/name).exists():
            shutil.copy2(args.folder/name, args.output/name)
    print(args.output.resolve())


if __name__ == '__main__':
    main()
