"""Build a disposable player-takeover extension of the AI successor fixture.

Run with --out runs/.../mod. Start a fresh standalone game as Britain, accept
the two test takeover events, and verify the new country's journal/Finance UI.
The original 12 assertions must pass too; never package this test output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import mechanics_testbed


def prepare(out, source=ROOT / 'beta/mod'):
    mechanics_testbed.prepare(source, out, 'successors')
    events = out / 'events/zz_spec_mechanics_tests.txt'
    text = events.read_text(encoding='utf-8-sig')
    text = text.replace('set_global_variable = spec_test_revolution_done', '''set_global_variable = spec_test_revolution_done
set_global_variable = { name = spec_manual_rev value = this }
every_country = { limit = { is_player = yes } trigger_event = { id = spec_manual_takeover.1 days = 1 } }''')
    text = text.replace('set_global_variable = spec_test_secession_done', '''set_global_variable = spec_test_secession_done
set_global_variable = { name = spec_manual_sec value = this }
if = { limit = { has_global_variable = spec_manual_rev_checked }
every_country = { limit = { is_player = yes } trigger_event = { id = spec_manual_takeover.2 days = 1 } }
}''')
    events.write_text(text, encoding='utf-8-sig')
    extra = ['namespace = spec_manual_takeover']
    loc = ['l_english:']
    expected = []
    for num, kind, label in [(1, 'rev', 'revolution'), (2, 'sec', 'secession')]:
        extra.append(f'''spec_manual_takeover.{num} = {{
type = country_event
title = spec_manual_{kind}_title
desc = spec_manual_{kind}_desc
option = {{
name = spec_manual_{kind}_play
play_as = global_var:spec_manual_{kind}
global_var:spec_manual_{kind} = {{ trigger_event = {{ id = spec_manual_takeover.{num + 2} days = 35 }} }}
}}
}}''')
        loc.extend([
            f' spec_manual_{kind}_title:0 "TEST: Play the {label}"',
            f' spec_manual_{kind}_desc:0 "The AI initialization checks have finished. Take control, wait 35 days, then inspect Financial Markets and Open Finance. This is a disposable test game."',
            f' spec_manual_{kind}_play:0 "Play as the new {label} country"',
        ])
        checks = {
            f'{label}_takeover_is_player': 'is_player = yes',
            f'{label}_takeover_has_finance': 'has_variable = spec_conf var:spec_conf >= 0 var:spec_conf <= 100 has_variable = spec_debt var:spec_debt >= 0 has_variable = spec_fast_steel has_variable = spec_stance',
            f'{label}_takeover_has_journal': 'exists = je:je_spec_markets',
            f'{label}_takeover_journal_guard_set': 'has_variable = spec_je_added',
        }
        body = []
        for name, condition in checks.items():
            expected.append(name)
            body.append(f'if = {{ limit = {{ {condition} }} debug_log = "HOTFIX PASS {name}" }} else = {{ debug_log = "HOTFIX FAIL {name}" }}')
        body.append(f'set_global_variable = spec_manual_{kind}_checked')
        if kind == 'rev':
            body.append('''if = { limit = { has_global_variable = spec_manual_sec }
trigger_event = { id = spec_manual_takeover.2 days = 7 }
}''')
        else:
            body.append('debug_log = "HOTFIX INFO PLAYER TAKEOVERS COMPLETE"')
        extra.append(f'spec_manual_takeover.{num + 2} = {{ type = country_event hidden = yes immediate = {{\n' + '\n'.join(body) + '\n} }')
    extra_path = out / 'events/zz_spec_manual_takeover.txt'
    extra_path.write_text('\n'.join(extra) + '\n', encoding='utf-8-sig')
    loc_path = out / 'localization/english/spec_manual_takeover_l_english.yml'
    loc_path.write_text('\n'.join(loc) + '\n', encoding='utf-8-sig')
    manifest_path = out / 'mechanics-test-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['suite'] = 'player_takeover'
    manifest['expected_assertions'] += expected
    manifest['manual_extension_sha256'] = {
        str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [events, extra_path, loc_path]
    }
    manifest['manual_builder_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT / 'beta/mod')
    args = parser.parse_args()
    prepare(args.out.resolve(), args.source.resolve())
