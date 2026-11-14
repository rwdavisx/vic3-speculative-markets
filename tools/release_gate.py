"""Run the complete standalone automated inventory against one frozen beta.

Manual UI/war checks and excluded compatibility suites are reported separately.
An automated pass is not a claim that every possible game state is correct.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import hotfix_testbed
import mechanics_testbed
import rival_notification_testbed

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'tests/release_suites.json'
AUTO = {'automatic', 'reload', 'legacy'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): digest(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}


def payload(files):
    return {p: h for p, h in files.items()
            if not p.startswith('.metadata/') and p != 'thumbnail.png'}


def test_inputs():
    paths = [CATALOG, *ROOT.glob('tools/*.py'), *ROOT.glob('tests/test_*.py')]
    cases = json.loads(CATALOG.read_text())['suites']
    paths += [p for p in (ROOT / 'tests/mechanics').glob('*')
              if p.suffix in {'.txt', '.json'} and not p.name.startswith('verification_')
              and cases.get(p.name.split('.')[0], {}).get('mode') != 'excluded']
    paths += list(ROOT.glob('tests/hotfix_*_events.txt'))
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


def check_inventory(cases, folder=None):
    folder = folder or ROOT / 'tests/mechanics'
    found = {p.stem for p in folder.glob('*.txt') if '.' not in p.stem}
    unknown = found - cases.keys()
    missing = {n for n, s in cases.items() if s['mode'] != 'excluded'} - found - {'legacy_hotfix'}
    if unknown or missing:
        raise ValueError(f'Unregistered fixtures: {sorted(unknown)}; missing: {sorted(missing)}')
    for name, spec in cases.items():
        if spec['mode'] not in AUTO | {'manual', 'excluded'}:
            raise ValueError(f'Unknown mode: {name}')
        if spec['mode'] not in AUTO and not spec.get('reason'):
            raise ValueError(f'Explicit reason required: {name}')


def evaluate_case(spec, expected, runs, checkpoint=None):
    """Re-read raw logs. A runner exiting successfully is insufficient."""
    problems, text, errors, evidence = [], '', [], {}
    try:
        for i, run in enumerate(runs):
            meta = json.loads((run / 'meta.json').read_text())
            until = spec.get('checkpoint_until') if spec['mode'] == 'reload' and i == 0 else spec['until']
            deadline = datetime.strptime(until, '%Y.%m.%d') - timedelta(days=1)
            if meta['status'] != 'done' or datetime.strptime(meta['date'], '%B %d, %Y') < deadline:
                problems.append(f'Run did not complete its scheduled interval: {run}')
            text += (run / 'assertions.log').read_text(encoding='utf-8-sig') + '\n'
            errors.append(run / 'error.log')
            for filename in ('meta.json', 'assertions.log', 'error.log'):
                path = run / filename
                evidence[str(path)] = digest(path)
        if spec['mode'] == 'reload':
            if len(runs) != 2 or checkpoint is None or not checkpoint.is_file():
                problems.append('Reload requires two completed processes and a preserved checkpoint')
            else:
                evidence[str(checkpoint)] = digest(checkpoint)
                loaded = json.loads((runs[1] / 'meta.json').read_text()).get('save')
                if loaded != checkpoint.stem or checkpoint.stat().st_size == 0:
                    problems.append('Second process did not load the recorded checkpoint')
        found = hotfix_testbed.RESULT.findall(text)
        passed = Counter(n for status, n in found if status == 'PASS')
        failed = sorted({n for status, n in found if status == 'FAIL'})
        if failed:
            problems.append(f'Failed assertions: {failed}')
        if set(passed) != set(expected):
            problems.append('Missing or unexpected assertion names')
        if any(passed[n] != spec.get('occurrences', 1) for n in expected):
            problems.append('Assertion occurrence counts do not match the contract')
        if 'HOTFIX SUITE COMPLETE' not in text:
            problems.append('Missing completion marker')
        gate = hotfix_testbed.check_error_logs(errors)
        if gate['blocking_error_count']:
            problems.append('Blocking mod/harness diagnostics')
        return {'passed': not problems, 'problems': problems, 'pass_occurrences': dict(passed),
                'failed_assertions': failed, 'error_gate': gate, 'evidence_sha256': evidence}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'passed': False, 'problems': [*problems, str(exc)], 'evidence_sha256': evidence}


def command(args, log):
    with log.open('w', encoding='utf-8') as stream:
        return subprocess.run([sys.executable, '-B', *map(str, args)], cwd=ROOT,
                              stdout=stream, stderr=subprocess.STDOUT).returncode


def run_case(name, spec, root, label):
    out = root / 'fixtures' / name
    try:
        if spec['mode'] == 'legacy':
            hotfix_testbed.prepare(out, root / 'source')
            manifest_path = out / hotfix_testbed.MANIFEST
        else:
            if name == 'rival_notifications':
                rival_notification_testbed.prepare(root / 'source', out)
            else:
                mechanics_testbed.prepare(root / 'source', out, name)
            manifest_path = out / 'mechanics-test-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        runs, checkpoint = [], None
        stages = ['before', 'after'] if spec['mode'] == 'reload' else ['run']
        for stage in stages:
            batch = f'gate_{label}_{name}_{stage}'
            if (ROOT / 'runs' / f'sweep_{batch}').exists():
                raise ValueError(f'Existing run evidence: {batch}')
            until = spec['checkpoint_until'] if stage == 'before' else spec['until']
            args = ['tools/sweep.py', '--name', batch, '--arm', f'test={out}',
                    '--until', until, '--jobs', '1', '--timeout', '30']
            if stage == 'before':
                args += ['--keep', '1837']
            elif stage == 'after':
                args += ['--save', str(checkpoint)]
            if command(args, root / f'{name}_{stage}.log'):
                raise RuntimeError(f'Sweep process failed: {name}/{stage}')
            run = ROOT / 'runs' / f'sweep_{batch}' / 'test_01'
            runs.append(run)
            if stage == 'before':
                saved = Path('G:/GameDev/_claude_scratch/vic/saves') / f'{batch}_test_1_1837.v3'
                checkpoint = root / f'{name}_1837.v3'
                shutil.copy2(saved, checkpoint)
        result = evaluate_case(spec, manifest['expected_assertions'], runs, checkpoint)
        result.update(runs=[str(p) for p in runs], checkpoint=str(checkpoint) if checkpoint else None,
                      manifest=str(manifest_path), manifest_sha256=digest(manifest_path),
                      expected=manifest['expected_assertions'])
        return result
    except Exception as exc:
        return {'passed': False, 'problems': [f'{type(exc).__name__}: {exc}']}


def verify_report(report_path, target):
    """Reject subsets, stale tests, changed packages or edited/missing evidence."""
    report = json.loads(report_path.read_text())
    catalog = json.loads(CATALOG.read_text())['suites']
    check_inventory(catalog)
    required = {n for n, s in catalog.items() if s['mode'] in AUTO}
    if set(report['results']) != required or not report.get('automatic_pass'):
        raise ValueError('A complete passing automated run is required; a subset is not a release gate')
    if report['test_inputs_sha256'] != test_inputs():
        raise ValueError('Test definitions or harness changed after validation')
    if payload(report['source_sha256']) != payload(snapshot(target)):
        raise ValueError('Release gameplay/UI bytes differ from the tested beta')
    for name, old in report['results'].items():
        for path, expected_hash in old.get('evidence_sha256', {}).items():
            if digest(Path(path)) != expected_hash:
                raise ValueError(f'Changed evidence: {path}')
        if digest(Path(old['manifest'])) != old['manifest_sha256']:
            raise ValueError(f'Changed fixture manifest: {name}')
        manifest = json.loads(Path(old['manifest']).read_text())
        source_key = 'beta_source_sha256' if catalog[name]['mode'] == 'legacy' else 'source_sha256'
        if manifest[source_key] != report['source_sha256']:
            raise ValueError(f'Fixture source mismatch: {name}')
        if old['expected'] != manifest['expected_assertions']:
            raise ValueError(f'Assertion inventory changed: {name}')
        fresh = evaluate_case(catalog[name], manifest['expected_assertions'], [Path(p) for p in old['runs']],
                              Path(old['checkpoint']) if old['checkpoint'] else None)
        if not fresh['passed']:
            raise ValueError(f'Invalid evidence for {name}: {fresh["problems"]}')
    for path, expected_hash in report['python_logs_sha256'].items():
        if digest(Path(path)) != expected_hash:
            raise ValueError('Python test log changed')
    if report['python_exit_code'] != 0:
        raise ValueError('Python tests did not pass')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'run', 'verify'])
    parser.add_argument('--source', type=Path, default=ROOT / 'beta/mod')
    parser.add_argument('--name')
    parser.add_argument('--jobs', type=int, choices=[1, 2], default=2)
    parser.add_argument('--only', nargs='+', help='Development subset; never satisfies the release gate')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text())['suites']
    check_inventory(catalog)
    automatic = {n: s for n, s in catalog.items() if s['mode'] in AUTO}
    pending = {n: s for n, s in catalog.items() if s['mode'] not in AUTO}
    if args.action == 'verify':
        if not args.report:
            parser.error('--report is required')
        report = verify_report(args.report.resolve(), args.source.resolve())
        print(json.dumps({'automatic_pass': True, 'manual_and_excluded': report['manual_and_excluded']}, indent=2))
        return 0
    if args.action == 'plan':
        print(json.dumps({'automatic_suites': len(automatic), 'suites': catalog}, indent=2))
        return 0
    if not args.name or not re.fullmatch('[a-z0-9_]{1,32}', args.name):
        parser.error('--name must be a unique lowercase label (up to 32 characters)')
    if args.only and not set(args.only) <= automatic.keys():
        parser.error('--only names must be automated suites')
    root = ROOT / 'runs/release_gate' / args.name
    root.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    if json.loads((source / '.metadata/metadata.json').read_text(encoding='utf-8-sig'))['id'] != 'speculative_markets_beta':
        raise ValueError('Run against a beta distribution')
    before = snapshot(source)
    shutil.copytree(source, root / 'source')
    if snapshot(root / 'source') != before:
        raise ValueError('Source changed while freezing')
    inputs = test_inputs()
    python_log = root / 'python.log'
    python_code = command(['-m', 'unittest', 'discover', '-s', 'tests'], python_log)
    selected = {n: automatic[n] for n in (args.only or automatic)}
    report = {'schema': 1, 'source': str(source), 'source_sha256': before,
              'test_inputs_sha256': inputs, 'python_exit_code': python_code,
              'python_logs_sha256': {str(python_log): digest(python_log)}, 'results': {},
              'manual_and_excluded': pending, 'automatic_pass': False,
              'note': 'Automated pass does not waive relevant live UI/war checks.'}
    report_path = root / 'report.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    if python_code:
        print(f'Python checks failed: {python_log}', flush=True)
        return 1
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_case, n, s, root, args.name): n for n, s in selected.items()}
        for future in as_completed(futures):
            name = futures[future]
            result = future.result()
            report['results'][name] = result
            report_path.write_text(json.dumps(report, indent=2) + '\n')
            print(f'{name}: {"PASS" if result["passed"] else "FAIL"} {result.get("problems", [])}', flush=True)
    report['automatic_pass'] = (set(selected) == set(automatic) and all(r['passed'] for r in report['results'].values())
                                and inputs == test_inputs() and before == snapshot(source))
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Report: {report_path}; full automated pass: {report["automatic_pass"]}', flush=True)
    return int(not all(r['passed'] for r in report['results'].values())
               or inputs != test_inputs() or before != snapshot(source))


if __name__ == '__main__':
    raise SystemExit(main())
