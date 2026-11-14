"""Package a separate beta from a generated Speculative Markets build.

No gameplay source is forked here. Default input is the checked main mod; a
separately generated non-debug build can be selected with --source. Nothing is
installed, enabled, uploaded, or written back to the source directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BETA_ROOT = ROOT / "beta"
STABLE_ID = "speculative_markets"
BETA_ID = "speculative_markets_beta"
METADATA = ".metadata/metadata.json"
GUIDANCE = "Enable either Speculative Markets or Speculative Markets - Beta, never both."


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(folder):
    """Read a complete build without following file or directory redirects."""
    folder = Path(folder)
    if folder.is_symlink() or (hasattr(folder, "is_junction") and folder.is_junction()):
        raise ValueError(f"Redirected build directory: {folder}")
    files = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(f"Redirected build path: {path}")
        if path.is_file():
            files[path.relative_to(folder).as_posix()] = path.read_bytes()
    return files


def beta_files(source, revision):
    """Preserve every source byte except the beta's distinct launcher metadata."""
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("Beta revision must be a positive integer")
    metadata = json.loads(source[METADATA].decode("utf-8-sig"))
    if metadata.get("id") != STABLE_ID:
        raise ValueError(f"Expected source ID {STABLE_ID!r}, got {metadata.get('id')!r}")
    version = metadata.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Expected a stable major.minor.patch source version, got {version!r}")
    relationships = metadata.get("relationships", [])
    # Launcher metadata permits other types, but Victoria 3 1.15.1's game-side
    # reader rejects them. The real beta launch caught incompatible_with.
    if not isinstance(relationships, list) or any(
            not isinstance(item, dict) or item.get("rel_type") != "dependency"
            for item in relationships):
        raise ValueError("Victoria 3 1.15.1 metadata supports only dependency relationships")
    for rel, data in source.items():
        if Path(rel).suffix.lower() in {".txt", ".gui", ".yml"}:
            text = data.decode("utf-8-sig")
            if re.search(r"\bdebug_log\b|HOTFIX (?:PASS|FAIL)|PROBE tag=|spec_hotfix", text):
                raise ValueError(f"Refusing test/debug content: {rel}")
    # Copy descriptive game fields, never publishing IDs or distribution tokens.
    beta = {key: metadata[key] for key in
            ("supported_game_version", "tags", "game_custom_data") if key in metadata}
    beta.update({
        "name": "Speculative Markets - Beta", "id": BETA_ID,
        "version": f"{version}-beta.{revision}",
        "short_description": f"Testing branch. {GUIDANCE}",
        "relationships": relationships,
    })
    if any(item.get("id") == BETA_ID for item in beta["relationships"]):
        raise ValueError("Source metadata has a relationship to the beta itself")
    result = dict(source)
    result[METADATA] = (json.dumps(beta, indent=2) + "\n").encode("utf-8")
    return result, beta, version


def destination(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    allowed = BETA_ROOT.resolve()
    if not (out == allowed or out.is_relative_to(allowed)):
        raise ValueError(f"Beta output must stay within {allowed}")
    if out == source or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError("Beta output must not overlap its source")
    for name in ("mod", "releases", "build_manifest.json"):
        path = out / name
        if path.resolve() != path or path.is_symlink():
            raise ValueError(f"Redirected output path: {path}")
    return source, out


def _previous_output(out):
    """Do not replace an unowned or locally modified mod directory."""
    target = out / "mod"
    if not target.exists():
        return
    manifest = out / "build_manifest.json"
    if not manifest.is_file():
        raise ValueError(f"Existing beta output has no build manifest: {target}")
    previous = json.loads(manifest.read_text(encoding="utf-8"))
    actual = {rel: digest(data) for rel, data in snapshot(target).items()}
    if previous.get("beta_id") != BETA_ID or actual != previous.get("files_sha256"):
        raise ValueError(f"Existing beta output was modified; preserve it before rebuilding: {target}")


def build(source=ROOT / "mod", out=BETA_ROOT, revision=1):
    source, out = destination(source, out)
    original = snapshot(source)
    files, metadata, source_version = beta_files(original, revision)
    _previous_output(out)
    out.mkdir(parents=True, exist_ok=True)
    releases = out / "releases"
    releases.mkdir(exist_ok=True)
    archive_name = f"Speculative_Markets_Beta_{metadata['version']}.zip"
    archive_path = releases / archive_name
    manifest_path = releases / archive_name.replace(".zip", ".manifest.json")
    for path in (archive_path, manifest_path):
        if path.resolve() != path or path.is_symlink():
            raise ValueError(f"Redirected archive path: {path}")
    with tempfile.TemporaryDirectory(prefix=".staging-", dir=out) as temporary:
        staging = Path(temporary)
        staged_mod = staging / "mod"
        for rel, data in files.items():
            path = staged_mod / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        staged_archive = staging / archive_name
        with zipfile.ZipFile(staged_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for rel, data in sorted(files.items()):
                entry = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, data)
        with zipfile.ZipFile(staged_archive) as archive:
            if archive.testzip() is not None or {name: archive.read(name) for name in archive.namelist()} != files:
                raise ValueError("Beta ZIP verification failed")
        if archive_path.exists() and archive_path.read_bytes() != staged_archive.read_bytes():
            raise ValueError("This beta version already has different packaged bytes; increase --revision")
        if snapshot(source) != original:
            raise ValueError("Source changed during beta packaging; build again after it is stable")
        manifest = {
            "beta_id": BETA_ID, "beta_version": metadata["version"],
            "source_version": source_version, "source": str(source),
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "archive": str(archive_path), "archive_sha256": digest(staged_archive.read_bytes()),
            "source_files_sha256": {rel: digest(data) for rel, data in original.items()},
            "files_sha256": {rel: digest(data) for rel, data in files.items()},
            "changed_source_files": [METADATA], "guidance": GUIDANCE,
        }
        # Previous output was fingerprint-checked above. Move it inside this
        # validated staging directory, with rollback if the new rename fails.
        target = out / "mod"
        previous = staging / "previous"
        if target.exists():
            target.rename(previous)
        try:
            staged_mod.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise
        staged_archive.replace(archive_path)
        rendered = json.dumps(manifest, indent=2) + "\n"
        manifest_path.write_text(rendered, encoding="utf-8")
        (out / "build_manifest.json").write_text(rendered, encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "mod", help="Generated non-debug source mod")
    parser.add_argument("--out", type=Path, default=BETA_ROOT, help="Output container inside beta/ (holds mod/ and releases/)")
    parser.add_argument("--revision", type=int, default=1, help="Positive beta iteration appended to the source version")
    args = parser.parse_args(argv)
    try:
        source, out = destination(args.source, args.out)
        # Check the unmodified generated source, whose metadata still has the
        # generator's stable version. Beta metadata is checked separately above.
        environment = dict(os.environ, SPEC_MOD_OUT=str(source))
        subprocess.run([sys.executable, "-B", str(ROOT / "tools/check.py")],
                       cwd=ROOT, env=environment, check=True)
        manifest = build(source, out, args.revision)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Beta build failed: {error}\n")
    print(f"Built {manifest['beta_version']}: {manifest['archive']}")
    print(f"Verified {len(manifest['files_sha256'])} files; gameplay bytes match {source}")
    print(GUIDANCE)


if __name__ == "__main__":
    main()
