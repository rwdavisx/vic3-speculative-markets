"""Test taking over an AI victor after its parent previously had a player journal."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import mechanics_testbed


def prepare(source, out):
    mechanics_testbed.prepare(source, out, 'successors')
    events = out / 'events/zz_spec_mechanics_tests.txt'
    text = events.read_text(encoding='utf-8-sig').replace(
        'set_global_variable = spec_test_revolution_done',
        '''set_global_variable = spec_test_revolution_done
set_global_variable = { name = spec_ai_victor value = this }
c:FRA = { set_global_variable = { name = spec_ai_parent value = this } }
c:GBR = { trigger_event = { id = spec_ai_victory.1 days = 1 } }''')
    events.write_text(text, encoding='utf-8-sig')
    extra = out / 'events/zz_spec_ai_victory.txt'
    script = '''namespace = spec_ai_victory
spec_ai_victory.1 = { type = country_event title = spec_ai_parent_title desc = spec_ai_parent_desc
option = { name = spec_ai_parent_play
play_as = global_var:spec_ai_parent
global_var:spec_ai_parent = { trigger_event = { id = spec_ai_victory.2 days = 35 } }
} }
spec_ai_victory.2 = { type = country_event hidden = yes immediate = {
if = { limit = { is_player = yes exists = je:je_spec_markets has_variable = spec_je_added }
debug_log = "HOTFIX PASS parent_player_has_journal_and_guard"
} else = { debug_log = "HOTFIX FAIL parent_player_has_journal_and_guard" }
set_global_variable = spec_ai_parent_checked
play_as = c:GBR
} }
spec_ai_victory.3 = { type = country_event title = spec_ai_victor_title desc = spec_ai_victor_desc
option = { name = spec_ai_victor_play
play_as = global_var:spec_ai_victor
global_var:spec_ai_victor = { trigger_event = { id = spec_ai_victory.4 days = 35 } }
} }
spec_ai_victory.4 = { type = country_event hidden = yes immediate = {
if = { limit = { is_player = yes is_country_alive = yes }
debug_log = "HOTFIX PASS ai_victor_takeover_is_player"
} else = { debug_log = "HOTFIX FAIL ai_victor_takeover_is_player" }
if = { limit = { exists = je:je_spec_markets }
debug_log = "HOTFIX PASS ai_victor_takeover_has_journal"
} else = { debug_log = "HOTFIX FAIL ai_victor_takeover_has_journal" }
if = { limit = { has_variable = spec_je_added }
debug_log = "HOTFIX PASS ai_victor_takeover_has_journal_guard"
} else = { debug_log = "HOTFIX FAIL ai_victor_takeover_has_journal_guard" }
debug_log = "HOTFIX INFO AI VICTOR TAKEOVER COMPLETE"
} }
'''
    extra.write_text(script, encoding='utf-8-sig')
    hook = out / 'common/on_actions/zz_spec_ai_victory.txt'
    hook.write_text('''on_monthly_pulse_country = { on_actions = { spec_ai_victory_check } }
spec_ai_victory_check = {
trigger = {
c:GBR ?= this is_player = yes
has_global_variable = spec_ai_parent_checked
NOT = { has_global_variable = spec_ai_victory_checked }
global_var:spec_ai_parent = { is_country_alive = no }
global_var:spec_ai_victor = { is_country_alive = yes }
}
effect = {
set_global_variable = spec_ai_victory_checked
debug_log = "HOTFIX PASS ai_revolution_defeated_player_parent"
trigger_event = { id = spec_ai_victory.3 days = 1 }
}
}
''', encoding='utf-8-sig')
    loc = out / 'localization/english/spec_ai_victory_l_english.yml'
    loc.write_text('''l_english:
 spec_ai_parent_title:0 "TEST: Give the parent a player journal"
 spec_ai_parent_desc:0 "Play France for 35 days. The test then returns to Britain automatically. Let the AI revolution win."
 spec_ai_parent_play:0 "Play the parent for 35 days"
 spec_ai_victor_title:0 "TEST: The AI revolution has won"
 spec_ai_victor_desc:0 "The parent country is gone. Take over the victorious AI country, wait 35 days, then check Financial Markets and Open Finance."
 spec_ai_victor_play:0 "Play the victorious revolution"
''', encoding='utf-8-sig')
    manifest_path = out / 'mechanics-test-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['suite'] = 'ai_victory_takeover'
    manifest['expected_assertions'] += re.findall(r'"HOTFIX PASS (\w+)"', script + hook.read_text(encoding='utf-8-sig'))
    manifest['manual_extension_sha256'] = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in [events, extra, hook, loc]}
    manifest['manual_builder_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prepare(a.source.resolve(), a.out.resolve())
