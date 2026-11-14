"""Exercise visible depression choices using unchanged option bodies and existing oracles.

Each case clones the production event under a unique test ID to avoid its native
repeat cooldown. Choice text, triggers and effects remain intact. Instrumentation
checks the chosen effect immediately, then schedules the next baseline setup.
This checks button routing, not natural event scheduling or repeat cooldowns.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import mechanics_testbed


def end_block(text, opening):
    depth = 0
    quoted = False
    for i in range(opening, len(text)):
        c = text[i]
        if c == '"' and (i == 0 or text[i-1] != '\\'):
            quoted = not quoted
        if quoted:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('Unclosed block')


def prepare(source, out):
    mechanics_testbed.prepare(source, out, 'depression_options')
    original = (source / 'events/spec_depression_events.txt').read_text(encoding='utf-8-sig')
    fixture = (ROOT / 'tests/mechanics/depression_options.txt').read_text(encoding='utf-8-sig')
    oracles = re.findall(r'spec_mechanics_ld_(\d)_([abc]) = yes\s+if = \{ limit = \{ (.*?) \} debug_log = "HOTFIX PASS option_\d_[abc]_gbr_contract"', fixture)
    assert len(oracles) == 17
    setup = '''activate_law = law_type:law_interventionism
set_global_variable = { name = spec_ld_phase value = 2 }
set_global_variable = { name = spec_ld_months value = 60 }
set_global_variable = { name = spec_ld_progress value = 50 }
set_variable = { name = spec_ld value = 2 }
set_variable = { name = spec_ld_own value = 50 }
set_variable = { name = spec_conf value = 50 }
set_variable = { name = spec_c_total value = 0 }
set_variable = { name = spec_c_caution value = 0 }
'''
    pieces = ['namespace = spec_mechanics_depression_options']
    expected = []
    cases = []
    for index, (number, letter, condition) in enumerate(oracles, 1):
        start = original.index(f'spec_depression.{number} = {{')
        opening = original.index('{', start)
        body = original[opening:end_block(original, opening)+1]
        edits = []
        for match in re.finditer(r'\n\toption = \{', body):
            op = body.index('{', match.start())
            end = end_block(body, op)
            # Other countries can tick the world-recovery value between event
            # delivery and its paused display. Reset the oracle baseline at
            # selection, immediately before the unchanged production effects.
            name = re.search(r'name = (spec_depression\.\d\.[abc])', body[op:end]).group(1)
            cash_setup = '''add_treasury = 10000000
set_variable = { name = spec_test_cash value = gold_reserves }
change_variable = { name = spec_test_cash subtract = spec_rescue_cost }
''' if name == 'spec_depression.4.b' else ''
            edits.append((op+1, '\n' + setup + cash_setup + '\n'))
            assertion = f'live_depression_{number}_{letter}'
            if name == f'spec_depression.{number}.{letter}':
                check = f'if = {{ limit = {{ {condition} }} debug_log = "HOTFIX PASS {assertion}" }} else = {{ debug_log = "HOTFIX FAIL {assertion}" }}'
            else:
                check = f'debug_log = "HOTFIX FAIL wrong_button_{number}_{letter}"'
            tail = (f'trigger_event = {{ id = spec_mechanics_depression_options.{index+1} days = 1 }}'
                    if index < len(oracles) else 'debug_log = "HOTFIX SUITE COMPLETE"')
            edits.append((end, '\n' + check + '\n' + tail + '\n'))
        for pos, insertion in sorted(edits, reverse=True):
            body = body[:pos] + insertion + body[pos:]
        pieces.append(f'spec_mechanics_depression_options.{100+index} = {body}')
        pieces.append(f'spec_mechanics_depression_options.{index} = {{ type = country_event hidden = yes immediate = {{\n{setup}\ndebug_log = "HOTFIX INFO CLICK {number}.{letter}"\ntrigger_event = {{ id = spec_mechanics_depression_options.{100+index} }}\n}} }}')
        expected.append(assertion)
        cases.append({'case':index, 'production_option':f'spec_depression.{number}.{letter}', 'condition':condition})
    target = out / 'events/zz_spec_mechanics_tests.txt'
    target.write_text('\n\n'.join(pieces), encoding='utf-8-sig')
    p = out / 'mechanics-test-manifest.json'
    manifest = json.loads(p.read_text())
    manifest.update(suite='depression_buttons', expected_assertions=expected, cases=cases,
                    manual_builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    manual_extension_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    p.write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prepare(a.source.resolve(), a.out.resolve())
