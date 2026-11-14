"""Build a version-pinned delta against a separately generated SM parent.

The patch contains only our generated code; Morgenroete remains a dependency.
Never edit the installed parent or copy the third-party bridge's implementation.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def hashes(folder, prefixes=None):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()
            and (prefixes is None or p.relative_to(folder).as_posix().startswith(prefixes))}


def delta(base, extended):
    missing = set(base) - set(extended)
    if missing:
        raise ValueError(f'Patch cannot remove parent files: {sorted(missing)}')
    return {name: sha for name, sha in extended.items() if base.get(name) != sha}


def verify_parent(base, parent):
    mismatches = [name for name, sha in base.items()
                  if not name.startswith('.metadata/') and parent.get(name) != sha]
    if mismatches:
        raise ValueError(f'Generator does not match chosen parent; rebuild/rebase first: {mismatches}')


def build(parent, mr, out):
    parent, mr, out = (p.resolve() for p in (parent, mr, out))
    if out.exists():
        raise ValueError('Use a new output folder; previous candidates are immutable')
    if not out.is_relative_to(ROOT / 'runs'):
        raise ValueError('Unverified patches must be built beneath runs/')
    if not (mr / '.metadata/metadata.json').is_file():
        raise ValueError('Missing Morgenroete metadata')
    original = hashes(parent)
    out.mkdir(parents=True)
    for name, extension in [('baseline', False), ('extended', True)]:
        env = {k: v for k, v in os.environ.items() if k not in ('SPEC_MOD_OUT', 'SPEC_MORGENROETE', 'SPEC_TUNING')}
        env['SPEC_MOD_OUT'] = str(out / name)
        if extension:
            env['SPEC_MORGENROETE'] = str(mr)
        subprocess.run([sys.executable, '-B', str(ROOT / 'tools/generate.py')], env=env, cwd=ROOT, check=True)
        subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check.py')], env=env, cwd=ROOT, check=True,
                       stdout=(out / f'{name}_check.txt').open('w', encoding='utf-8'))
    base, extended = hashes(out / 'baseline'), hashes(out / 'extended')
    verify_parent(base, original)
    changes = {name: sha for name, sha in delta(base, extended).items() if not name.startswith('.metadata/')}
    patch = out / 'mod'
    for name in changes:
        dest = patch / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out / 'extended' / name, dest)
    # Morgenroete supplies uranium/printing types but omits the workshop type.
    # Define only the missing type, using the engine's building-specific modifier.
    types = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (mr / 'common/modifier_type_definitions').glob('*.txt'))
    key = 'building_instrument_workshops_throughput_add'
    if not re.search(rf'^\s*{key}\s*=\s*\{{', types, re.M):
        target = patch / 'common/modifier_type_definitions/spec_mr_modifier_types.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'{key} = {{\n\tdecimals = 1\n\tcolor = good\n\tpercent = yes\n\tgame_data = {{ ai_value = 0 }}\n}}\n', encoding='utf-8-sig')
        for language in ('english', 'braz_por', 'french', 'german', 'japanese', 'korean', 'polish', 'russian', 'simp_chinese', 'spanish', 'turkish'):
            target = patch / f'localization/{language}/spec_mr_l_{language}.yml'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'l_{language}:\n {key}: "$building_instrument_workshops$ Throughput"\n {key}_desc: "A bonus or penalty to the input and output of $building_instrument_workshops$."\n', encoding='utf-8-sig')
    meta = json.loads((parent / '.metadata/metadata.json').read_text(encoding='utf-8-sig'))
    metadata = {'name': 'Speculative Markets - Morgenroete Compatibility (Test)',
                'id': 'speculative_markets_morgenroete', 'version': '0.1.0-test',
                'supported_game_version': '1.15.*', 'short_description': 'Requires the matching Speculative Markets build and Morgenroete.',
                'tags': ['Gameplay'], 'relationships': [{'rel_type': 'dependency', 'id': '2889925770',
                'display_name': 'Morgenroete - Dawn of Flavor', 'resource_type': 'mod', 'version': '*'}],
                'game_custom_data': {'multiplayer_synchronized': True}}
    (patch / '.metadata').mkdir(parents=True)
    (patch / '.metadata/metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    manifest = {'status': 'UNVERIFIED CANDIDATE - NOT PUBLISHED', 'parent_version': meta['version'],
                'parent_id': meta['id'], 'parent': str(parent), 'morgenroete': str(mr),
                'morgenroete_metadata': json.loads((mr / '.metadata/metadata.json').read_text(encoding='utf-8-sig')),
                'parent_hashes': original, 'patch_hashes': hashes(patch),
                'generator_hashes': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted((ROOT / 'tools').rglob('*.py'))},
                'upstream_inputs': hashes(mr, ('common/goods/', 'common/buildings/', 'common/building_groups/', 'common/company_types/', 'common/modifier_type_definitions/')),
                'scope': ['elgar_instruments', 'good_uranium', 'manzoni_prints'],
                'excluded': {'air_travel': 'Local service; outside the tradable-goods bridge scope.',
                             'elgar_music': 'Non-tradable service; outside the tradable-goods bridge scope.'}}
    if hashes(parent) != original:
        raise ValueError('Parent changed during build')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(f'Candidate: {patch}; {len(changes)} changed generated files. Parent: {meta["version"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, default=ROOT / 'beta/mod')
    parser.add_argument('--morgenroete', type=Path, default=Path('G:/SteamLibrary/steamapps/workshop/content/529340/2889925770'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.parent, args.morgenroete, args.out)
