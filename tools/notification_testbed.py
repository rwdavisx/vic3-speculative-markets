"""Launch isolated engine regressions for the boom-notification crash.

py -3 -B tools/notification_testbed.py beta_103
Select Great Britain in the loaded lobby, start, and advance past January 30.
The fixture never belongs in a release. Each run and its fixture are immutable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import notify

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT/'runs/notification_scope_repro'
GAME = Path('G:/SteamLibrary/steamapps/common/Victoria 3/binaries')
SAVE = Path('G:/GameDev/_claude_scratch/vic/saves/hotfix_1_0_baseline_early_base_1_1840.v3')


def post(good, severity, bank=1, over=1, people=0):
    return (f'g:{good} = {{ save_scope_as = spec_note_good }}\n'
            + ''.join(f'set_variable = {{ name = spec_note_{k}_{good} value = {v} }}\n'
                      for k, v in (('bank', bank), ('over', over), ('ppl', people)))
            + notify.boom_note_scopes(good, '')
            + notify.boom_post(severity, ''))


def fixture_files():
    defaults = ('g:wood = { save_scope_as = spec_note_good }\n'
                + ''.join(f'remove_variable = spec_note_{k}_wood\n' for k in ('bank', 'over', 'ppl'))
                + notify.boom_note_scopes('wood', '') + notify.boom_post(1, ''))
    cases = [post('grain', 1, 2, 1.5, 3), post('steel', 2, 1.25, 1.75, 2),
             post('coal', 3, 1.8, 2, 1), defaults,
             post('grain', 2, 2.25, 1.25, 2) + post('steel', 3, 1.75, 2.5, 3),
             post('iron', 2, 1.6, 1, 0), post('tools', 3, 1, 1.9, 0),
             post('fish', 1, 1.04, 1.04, 0),
             "g:grain = { save_scope_as = spec_note_good }\npost_notification = spec_feverish\n"]
    actions = '''on_game_started_after_lobby = { on_actions = { spec_note_test_setup } }
spec_note_test_setup = {
    effect = { c:GBR = { trigger_event = { on_action = spec_note_test_1 days = 1 } } }
}
'''
    for number, body in enumerate(cases, 1):
        following = f'trigger_event = {{ on_action = spec_note_test_{number+1} days = 3 }}' if number < len(cases) else 'debug_log = "SPEC_NOTE_TEST COMPLETE"'
        actions += f'''spec_note_test_{number} = {{
    trigger = {{ is_player = yes }}
    effect = {{
        debug_log = "SPEC_NOTE_TEST case_{number} before"
        {body}
        debug_log = "SPEC_NOTE_TEST case_{number} after"
        {following}
    }}
}}
'''
    return actions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('--spec', type=Path, default=ROOT/'beta/mod')
    parser.add_argument('--cmf', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_]+', args.name):
        parser.error('Use a plain run name')
    user = RUNS/args.name
    if user.exists():
        parser.error('Run already exists; choose a new name to preserve evidence')
    spec = args.spec.resolve()
    metadata = json.loads((spec/'.metadata/metadata.json').read_text(encoding='utf-8-sig'))
    assert metadata['id'] in ('speculative_markets_beta', 'speculative_markets')
    user.mkdir(parents=True)
    (user/'save games').mkdir()
    shutil.copyfile(SAVE, user/'save games/notification_test.v3')
    settings = json.loads((ROOT/'runs/cmf_compat/beta_metadata_final/pdx_settings.json').read_text())
    settings['game'].update(save_to_cloud=False, save_on_exit=False, autosave='never')
    (user/'pdx_settings.json').write_text(json.dumps(settings, indent=2))
    cache = ROOT/'runs/cmf_compat/beta_metadata_final/shadercache'
    if cache.is_dir():
        shutil.copytree(cache, user/'shadercache')
    fixture = user/'fixture'
    (fixture/'.metadata').mkdir(parents=True)
    (fixture/'.metadata/metadata.json').write_text(json.dumps({
        'name':'Notification regression fixture - DO NOT PUBLISH', 'id':'spec_note_test',
        'version':'0.0.0', 'supported_game_version':'1.15.*', 'tags':['Utilities'],
        'short_description':'Disposable notification tests.', 'relationships':[],
        'game_custom_data':{'multiplayer_synchronized':True}}))
    (fixture/'common/on_actions').mkdir(parents=True)
    (fixture/'common/on_actions/spec_note_test.txt').write_text(fixture_files(), encoding='utf-8-sig')
    mods = [spec, fixture]
    if args.cmf:
        mods.insert(0, Path('G:/SteamLibrary/steamapps/workshop/content/529340/3385002128'))
        mods.append(ROOT/'compatibility/cmf/mod')
    (user/'content_load.json').write_text(json.dumps({'enabledMods':[{'path':str(p)} for p in mods], 'disabledDLC':[], 'enabledUGC':[]}))
    # Audio and notifications enabled, matching normal play. No normal-profile changes.
    command = [str(GAME/'victoria3.exe'), '-gdpr-compliant', '-debug_mode', '-no_crash_reporter',
               f'-userdir={user}', '-loadsave=notification_test']
    process = subprocess.Popen(command, cwd=GAME, env={**os.environ, 'SteamAppId':'529340', 'SteamGameId':'529340'})
    hashes = {p.relative_to(spec).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(spec.rglob('*')) if p.is_file()}
    record = {'pid':process.pid, 'command':command, 'mods':[str(p) for p in mods], 'metadata':metadata,
              'source_save_sha256':hashlib.sha256(SAVE.read_bytes()).hexdigest(), 'mod_files_sha256':hashes}
    (user/'launch.json').write_text(json.dumps(record, indent=2))
    print(json.dumps({'pid':process.pid, 'userdir':str(user), 'version':metadata['version']}))


if __name__ == '__main__':
    main()
