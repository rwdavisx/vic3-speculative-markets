"""Build the Speculative Markets - Tech & Res compatibility patch: the generated files that differ when the
generators also read Tech & Res's goods and buildings. Load order: Tech & Res, Speculative Markets, this patch."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from morgenroete_build import ROOT, delta, hashes, verify_parent  # noqa: E402
import mod_sources  # noqa: E402

LANGUAGES = ('english', 'braz_por', 'french', 'german', 'japanese', 'korean', 'polish', 'russian', 'simp_chinese',
             'spanish', 'turkish')


def build(parent, tr, out, version='0.1.0-test', tuning=None):
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-test)?', version):
        raise ValueError('Invalid patch version')
    parent, tr, out = (p.resolve() for p in (parent, tr, out))
    if out.exists():
        raise ValueError('Use a new output folder; previous candidates are immutable')
    if not out.is_relative_to(ROOT / 'runs'):
        raise ValueError('Unverified patches must be built beneath runs/')
    if tuning:
        tuning = tuning.resolve(strict=True)
    original = hashes(parent)
    out.mkdir(parents=True)
    for name, extension in [('baseline', False), ('extended', True)]:
        env = {k: v for k, v in os.environ.items() if k not in ('SPEC_MOD_OUT', 'SPEC_MORGENROETE', 'SPEC_TECHRES', 'SPEC_TUNING')}
        env['SPEC_MOD_OUT'] = str(out / name)
        if tuning:
            env['SPEC_TUNING'] = str(tuning)
        if extension:
            env['SPEC_TECHRES'] = str(tr)
        subprocess.run([sys.executable, '-B', str(ROOT / 'tools/generate.py')], env=env, cwd=ROOT, check=True)
        subprocess.run([sys.executable, '-B', str(ROOT / 'tools/check.py')], env=env, cwd=ROOT, check=True,
                       stdout=(out / f'{name}_check.txt').open('w', encoding='utf-8'))
    base, extended = hashes(out / 'baseline'), hashes(out / 'extended')
    verify_parent(base, original)
    changes = {n: sha for n, sha in delta(base, extended).items() if not n.startswith('.metadata/')}
    patch = out / 'mod'
    for name in changes:
        dest = patch / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out / 'extended' / name, dest)
    # Throughput modifier types the generated files use but neither the game nor Tech & Res defines.
    used = set()
    for p in patch.rglob('*.txt'):
        used |= set(re.findall(r'\bbuilding_(\w+?)_throughput_add\b', p.read_text(encoding='utf-8-sig')))
    defs = set()
    for root in (Path('G:/SteamLibrary/steamapps/common/Victoria 3/game'), tr, out / 'extended'):
        for p in (root / 'common/modifier_type_definitions').glob('*.txt'):
            defs |= set(re.findall(r'^(\w+)\s*=\s*\{', p.read_text(encoding='utf-8-sig'), re.M))
    missing = sorted(b for b in used if f'building_{b}_throughput_add' not in defs)
    if missing:
        target = patch / 'common/modifier_type_definitions/spec_tr_modifier_types.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(''.join(f'building_{b}_throughput_add = {{\n\tdecimals = 1\n\tcolor = good\n\tpercent = yes\n'
                                  f'\tgame_data = {{ ai_value = 0 }}\n}}\n' for b in missing), encoding='utf-8-sig')
        for language in LANGUAGES:
            # Tech & Res supplies some names without declaring a modifier type.
            # Check names and descriptions independently in each language.
            defined = set()
            for source in (tr / 'localization').rglob(f'*_l_{language}.yml'):
                defined.update(re.findall(r'^\s*([\w]+):', source.read_text(encoding='utf-8-sig'), re.M))
            fallback = {}
            for building in missing:
                key = f'building_{building}_throughput_add'
                fallback[key] = f'$building_{building}$ ($concept_throughput$)'
                fallback[key + '_desc'] = '$building_throughput_add_desc$'
            lines = [f' {key}: "{value}"\n' for key, value in fallback.items() if key not in defined]
            if lines:
                target = patch / f'localization/{language}/spec_tr_l_{language}.yml'
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f'l_{language}:\n' + ''.join(lines), encoding='utf-8-sig')
    meta = json.loads((parent / '.metadata/metadata.json').read_text(encoding='utf-8-sig'))
    tr_meta = json.loads((tr / '.metadata/metadata.json').read_text(encoding='utf-8-sig'))
    metadata = {'name': 'Speculative Markets - Tech & Res Compatibility' + (' (Test)' if version.endswith('-test') else ''),
                'id': 'speculative_markets_techres', 'version': version, 'supported_game_version': '1.15.*',
                'short_description': 'Requires the matching Speculative Markets build and Tech & Res.',
                'tags': ['Utilities'], 'relationships': [{'rel_type': 'dependency', 'id': tr_meta['id'],  # its metadata id (tech.res), not the Workshop number
                'display_name': '[1.15] Tech & Res', 'resource_type': 'mod', 'version': '*'}],
                'game_custom_data': {'multiplayer_synchronized': True}}
    (patch / '.metadata').mkdir(parents=True)
    (patch / '.metadata/metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    goods = sorted({g for m in mod_sources.TR_SELLS.values() for g in m.values()}
                   | {g for u in mod_sources.TR_UPGRADES.values() for g, _ in u})
    manifest = {'status': 'UNVERIFIED CANDIDATE - NOT PUBLISHED', 'parent_version': meta['version'],
                'parent_id': meta['id'], 'parent': str(parent), 'techres': str(tr),
                'techres_metadata': tr_meta,
                'parent_hashes': original, 'patch_hashes': hashes(patch),
                'generator_hashes': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted((ROOT / 'tools').rglob('*.py'))},
                'upstream_inputs': hashes(tr, ('common/goods/', 'common/buildings/', 'common/building_groups/',
                                               'common/company_types/', 'common/modifier_type_definitions/')),
                'scope': goods, 'excluded': mod_sources.TR_EXCLUDED, 'added_modifier_types': missing}
    if tuning:
        manifest['tuning_sha256'] = hashlib.sha256(tuning.read_bytes()).hexdigest()
    if hashes(parent) != original:
        raise ValueError('Parent changed during build')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Candidate: {patch}; {len(changes)} changed generated files, {len(missing)} modifier types added. '
          f'Parent: {meta["version"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, default=ROOT / 'mod')
    parser.add_argument('--techres', type=Path, default=Path('G:/SteamLibrary/steamapps/workshop/content/529340/3472248460'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--version', default='0.1.0-test')
    parser.add_argument('--tuning', type=Path, help='Explicit tuning file used to generate the chosen parent')
    args = parser.parse_args()
    build(args.parent, args.techres, args.out, args.version, args.tuning)
