"""Compare original beta, candidate, and vanilla from identical native saves.

This is crash investigation, not a replacement for the release gate. Keep all
results, including failures; do not retry until green or discard failed seeds.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import mechanics_testbed
import sweep


def run(out, candidate, seeds):
    out.mkdir(parents=True, exist_ok=False)
    mods = {'vanilla': sweep.vanilla()}
    for name, source in [('original', ROOT / 'beta/mod'), ('candidate', candidate)]:
        mod = out / 'fixtures' / name
        mechanics_testbed.prepare(source, mod, 'campaign_repeated')
        mods[name] = mod
    results = []
    for seed in range(seeds):
        label = f'{out.name}_seed{seed + 1}'
        sweep.make_seed(mods['vanilla'], label)
        save = sweep.SAVES / f'{label}.v3'
        seed_copy = out / save.name
        shutil.copy2(save, seed_copy)
        seed_hash = hashlib.sha256(seed_copy.read_bytes()).hexdigest()
        for arm, mod in mods.items():
            target = out / f'seed{seed + 1}_{arm}'
            target.mkdir()
            job = sweep.start(mod, '1841.6.1', 0, save=seed_copy)
            job.update(build=arm, save=str(seed_copy))
            (target / 'launch.json').write_text(json.dumps({
                'pid': job['proc'].pid, 'profile': str(job['user']),
                'mod': str(mod), 'save': str(seed_copy), 'save_sha256': seed_hash,
            }, indent=2))
            print(f'Seed {seed + 1}: {arm} PID {job["proc"].pid}', flush=True)
            while job['proc'].poll() is None:
                sweep.poll(job)
                if time.time() - job['wall'] > 1800:
                    job['proc'].kill()
                    job['proc'].wait()
                    break
                time.sleep(1)
            code = job['proc'].returncode
            status = 'done' if code == 0 else 'crashed_or_terminated'
            for directory in ['crashes', 'save games']:
                src = job['user'] / directory
                if src.exists():
                    shutil.copytree(src, target / directory)
            game = sweep.finish(job, status, target)
            result = {'seed': seed + 1, 'arm': arm, 'return_code': code,
                      'status': status, 'date': game['date'], 'save_sha256': seed_hash,
                      'run': str(target)}
            results.append(result)
            (out / 'results.json').write_text(json.dumps(results, indent=2))
            print(json.dumps(result), flush=True)
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--seeds', type=int, default=2)
    a = p.parse_args()
    run(a.out.resolve(), a.candidate.resolve(), a.seeds)
