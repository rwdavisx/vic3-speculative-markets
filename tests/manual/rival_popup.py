"""Render one annual win with three rivalries in a disposable player game.

Reuses the first two existing notification contracts. Inspect the rendered
popup separately; dispatch counters alone do not prove visual uniqueness.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import rival_notification_testbed
import mechanics_testbed


def prepare(source, out):
    rival_notification_testbed.prepare(source, out)
    events = out / 'events/zz_spec_mechanics_tests.txt'
    text = events.read_text(encoding='utf-8-sig')
    boundary = '\nset_variable = { name = spec_test_won value = 0 }\nspec_mechanics_rival_year = yes'
    assert text.count(boundary) == 1
    text = text.split(boundary)[0] + '\ndebug_log = "HOTFIX SUITE COMPLETE"\n} }\n'
    events.write_text(text, encoding='utf-8-sig')
    p = out / 'mechanics-test-manifest.json'
    manifest = json.loads(p.read_text())
    manifest.update(suite='rival_popup', expected_assertions=[
        'multiple_wins_one_notification', 'all_three_win_rewards_preserved'],
        manual_builder_sha256=mechanics_testbed.digest(Path(__file__)),
        manual_extension_sha256=mechanics_testbed.digest(events))
    p.write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source.resolve(), args.out.resolve())
