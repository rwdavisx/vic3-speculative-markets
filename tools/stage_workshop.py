"""Stage one immutable release archive for steam_upload.py; never upload here."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from steam_upload import CHANNELS, ROOT, STAGING, inspect_stage


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('channel', choices=CHANNELS)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    manifest_path = archive.with_suffix('.manifest.json')
    release = json.loads(manifest_path.read_text(encoding='utf-8'))
    archive_hash = sha(archive.read_bytes())
    if archive_hash != release['archive_sha256']:
        raise ValueError('Archive hash differs from immutable release manifest')
    with zipfile.ZipFile(archive) as zipped:
        files = {n: zipped.read(n) for n in zipped.namelist() if not n.endswith('/')}
    metadata = json.loads(files['.metadata/metadata.json'].decode('utf-8-sig'))
    if metadata['id'] != CHANNELS[args.channel][0]:
        raise ValueError('Wrong distribution for this Workshop channel')
    folder = STAGING / args.channel
    if folder.resolve() != folder or not folder.resolve().is_relative_to(STAGING.resolve()):
        raise ValueError('Staging target escaped workspace')
    for name in files:
        if not (folder / name).resolve().is_relative_to(folder.resolve()):
            raise ValueError('Archive entry escaped staging')
    deltas = {}
    if args.channel in ('beta', 'cmf'):
        preview = ROOT / f'workshop/new_items/{args.channel}_preview.png'
        data = preview.read_bytes()
        deltas['thumbnail.png'] = {'old_sha256': sha(files['thumbnail.png']) if 'thumbnail.png' in files else None,
                                   'new_sha256': sha(data), 'preview_source': str(preview)}
        files['thumbnail.png'] = data
    manifest = STAGING / 'manifest.json'
    previous = json.loads(manifest.read_text()) if manifest.exists() else {'items': {}}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    history = STAGING / 'history'
    history.mkdir(parents=True, exist_ok=True)
    if manifest.exists():
        with (history / f'{stamp}.json').open('x', encoding='utf-8') as stream:
            stream.write(manifest.read_text())
    # Only disposable staging files are replaced; archives remain untouched.
    for old in folder.rglob('*'):
        if old.is_symlink() or (hasattr(old, 'is_junction') and old.is_junction()):
            raise ValueError('Redirected staging entry')
    for old in folder.rglob('*'):
        if old.is_file() and old.relative_to(folder).as_posix() not in files:
            old.unlink()
    for name, data in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    previous['items'][args.channel] = {
        'source_archive': str(archive), 'source_manifest': str(manifest_path),
        'source_archive_sha256': archive_hash, 'version': metadata['version'], 'id': metadata['id'],
        'files_sha256': {n: sha(data) for n, data in files.items()}, 'deltas': deltas,
        'staged_at_utc': stamp}
    manifest.write_text(json.dumps(previous, indent=2) + '\n')
    plan = inspect_stage(args.channel)
    print(json.dumps({k: v for k, v in plan.items() if k != 'files_sha256'}, indent=2))


if __name__ == '__main__':
    main()
