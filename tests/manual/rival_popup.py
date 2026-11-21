"""Render three distinct opponents' win notices in a disposable player game.

Reuses the first settlement scenario. Inspect rendered opponent names separately.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import rival_notification_testbed
import mechanics_testbed


def prepare(source, out, *, host="GBR", decision=False):
    if host not in {"GBR", "RUS"}:
        raise ValueError("Choose Britain or Russia so the three opposing Exchanges remain distinct.")
    rival_notification_testbed.prepare(source, out)
    events = out / 'events/zz_spec_mechanics_tests.txt'
    text = events.read_text(encoding='utf-8-sig')
    loop = 'while = { count = 5 # independent settlement scenarios'
    assert text.count(loop) == 1
    text = text.replace(loop, 'while = { count = 1 # only the three simultaneous wins')
    events.write_text(text.replace('c:GBR', f'c:{host}'), encoding='utf-8-sig')
    start = out / 'common/on_actions/zz_spec_mechanics_start.txt'
    helper = out / 'common/scripted_effects/zz_spec_mechanics_helpers.txt'
    for path in (start, helper):
        path.write_text(path.read_text(encoding='utf-8-sig').replace('c:GBR', f'c:{host}'), encoding='utf-8-sig')
    if decision:
        # Keep the game paused and close unrelated events before watching the toast queue.
        start.unlink()
        button = out / 'common/decisions/zz_spec_rival_popup.txt'
        button.parent.mkdir(parents=True, exist_ok=True)
        button.write_text(f"""spec_test_settle_exchanges = {{
    is_shown = {{ c:{host} ?= this is_player = yes }}
    possible = {{ has_variable = spec_conf }}
    when_taken = {{ trigger_event = {{ id = spec_mechanics_rival_notifications.1 }} }}
    ai_chance = {{ value = 0 }}
}}
""", encoding='utf-8-sig')
        (out / 'localization/english/zz_spec_rival_popup_l_english.yml').write_text(
            'l_english:\n spec_test_settle_exchanges: "Settle Three Test Contests"\n'
            ' spec_test_settle_exchanges_desc: "Settle three contests against Paris, Berlin and Vienna."\n',
            encoding='utf-8-sig')
    p = out / 'mechanics-test-manifest.json'
    manifest = json.loads(p.read_text())
    manifest.update(suite='rival_popup', expected_assertions=[
        'separate_named_win_for_each_opponent', 'all_three_win_rewards_preserved',
        'finished_contests_do_not_notify_again'],
        host=host, activation='decision' if decision else 'monthly',
        instrumented_helper_sha256=mechanics_testbed.digest(helper),
        manual_builder_sha256=mechanics_testbed.digest(Path(__file__)),
        manual_extension_sha256=mechanics_testbed.digest(events))
    p.write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--host', choices=['GBR', 'RUS'], default='GBR')
    parser.add_argument('--decision', action='store_true', help='Settle the contests from Journal > Decisions')
    args = parser.parse_args()
    prepare(args.source.resolve(), args.out.resolve(), host=args.host, decision=args.decision)
