"""Record each actual notification and its named opponent in an isolated monthly rivalry settlement.

Observer GBR stands in for a human player only in the extracted helper. Actual
production post_notification calls remain in place, alongside test counters.
"""
import argparse
import json
from pathlib import Path
import mechanics_testbed as testbed

def instrument(text):
    assert 'is_player = yes' in text
    text = text.replace('is_player = yes', 'c:GBR ?= this')
    for kind in ('won', 'lost'):
        call = f'post_notification = spec_rival_{kind}'
        assert call in text
        text = text.replace(call, f'change_variable = {{ name = spec_test_{kind} add = 1 }}\n'
                            f'add_to_variable_list = {{ name = spec_test_{kind}_opponents target = scope:spec_note_src }}\n'
                            f'add_to_variable_list = {{ name = spec_test_{kind}_seats target = scope:spec_note_state }}\n' + call)
    return text


def prepare(source, out):
    testbed.prepare(source, out, 'rival_notifications')
    helper = out / 'common/scripted_effects/zz_spec_mechanics_helpers.txt'
    text = helper.read_text(encoding='utf-8-sig')
    text = instrument(text)
    helper.write_text(text, encoding='utf-8-sig')
    manifest_path = out / 'mechanics-test-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['instrumentation'] = (
        'Extracted production monthly settlement body. GBR stands in for the player. '
        'Each actual notification call increments a counter and records its named opponent. '
        'This counts dispatch calls, not rendered toast instances.'
    )
    manifest['instrumented_helper_sha256'] = testbed.digest(helper)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source.resolve(), args.out.resolve())
