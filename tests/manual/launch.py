"""Launch an already prepared disposable mod with private settings and log mirrors."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import observe


def launch(run, settings_profile):
    run = run.resolve()
    if not (run / 'mod/mechanics-test-manifest.json').is_file():
        raise ValueError('Expected a prepared mechanics fixture')
    profile = run / 'profile'
    profile.mkdir()  # Never reuse a prior run or its logs.
    shutil.copy2(settings_profile / 'pdx_settings.json', profile / 'pdx_settings.json')
    if (settings_profile / 'shadercache').is_dir():
        shutil.copytree(settings_profile / 'shadercache', profile / 'shadercache')
    (profile / 'content_load.json').write_text(json.dumps({
        'enabledMods': [{'path': str(run / 'mod')}], 'disabledDLC': [], 'enabledUGC': []}))
    cmd = [str(observe.GAME / 'victoria3.exe'), '-gdpr-compliant', '-debug_mode',
           '-nosounds', '-no_crash_reporter', f'-userdir={profile}']
    env = {**os.environ, 'SteamAppId': observe.STEAM_APP_ID,
           'SteamGameId': observe.STEAM_APP_ID}
    started = time.time()
    mirrors = [observe.Mirror(profile / 'logs' / f'{s}.log', run / f'{s}_mirror.log', started)
               for s in ['debug', 'error']]
    process = subprocess.Popen(cmd, cwd=str(observe.GAME), env=env)
    (run / 'launch.json').write_text(json.dumps({
        'pid': process.pid, 'command': cmd, 'cwd': str(observe.GAME),
        'steam_app_id': observe.STEAM_APP_ID}, indent=2))
    print(f'PID {process.pid}', flush=True)
    while process.poll() is None:
        for mirror in mirrors:
            mirror.poll()
        time.sleep(.5)
    for mirror in mirrors:
        mirror.poll()
    print(f'Exit {process.returncode}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--settings-profile', type=Path, required=True)
    args = parser.parse_args()
    launch(args.run, args.settings_profile)
