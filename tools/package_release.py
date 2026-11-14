"""Package checked stable or CMF mod files without overwriting a release.

Examples:
    py -3 -B tools/package_release.py
    py -3 -B tools/package_release.py --mod compatibility/cmf/mod

This records artifact integrity, not a claim that runtime tests have passed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"
PREFIXES = {
    "speculative_markets": "Speculative_Markets",
    "speculative_markets_cmf_compat": "Speculative_Markets_CMF_Compatibility",
    "speculative_markets_morgenroete": "Speculative_Markets_Morgenroete_Compatibility",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(folder):
    files = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(f"Redirected source path: {path}")
        if path.is_file():
            files[path.relative_to(folder).as_posix()] = path.read_bytes()
    return files


def package(folder):
    folder = Path(folder).resolve()
    files = snapshot(folder)
    metadata = json.loads(files[".metadata/metadata.json"].decode("utf-8-sig"))
    mod_id, version = metadata["id"], metadata["version"]
    if mod_id not in PREFIXES or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Expected stable or CMF metadata with a major.minor.patch version")
    relationships = metadata.get("relationships", [])
    if not isinstance(relationships, list) or any(
            not isinstance(item, dict) or item.get("rel_type") != "dependency"
            for item in relationships):
        raise ValueError("Victoria 3 1.15.1 metadata supports only dependency relationships")
    for rel, data in files.items():
        if Path(rel).suffix.lower() in {".txt", ".gui", ".yml"}:
            if re.search(r"\bdebug_log\b|HOTFIX (?:PASS|FAIL)|PROBE tag=|spec_hotfix", data.decode("utf-8-sig")):
                raise ValueError(f"Refusing test/debug content: {rel}")
    if RELEASES.resolve() != RELEASES:
        raise ValueError("Release directory must not be redirected")
    stem = f"{PREFIXES[mod_id]}_{version}"
    archive_path = RELEASES / f"{stem}.zip"
    manifest_path = RELEASES / f"{stem}.manifest.json"
    for path in (archive_path, manifest_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Release artifact already exists; not overwritten: {path}")
    hashes = {rel: sha(data) for rel, data in files.items()}
    provenance = None
    if mod_id == "speculative_markets_cmf_compat":
        provenance = json.loads((folder.parent / "build_manifest.json").read_text(encoding="utf-8"))
        if provenance["output_files"] != hashes:
            raise ValueError("CMF output no longer matches its build manifest")
        for parent in provenance["parents"].values():
            for rel, expected in parent["files"].items():
                if sha((Path(parent["path"]) / rel).read_bytes()) != expected:
                    raise ValueError(f"CMF parent changed since generation: {parent['path']}/{rel}")
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w") as archive:
        for rel, data in sorted(files.items()):
            entry = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    content = packed.getvalue()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if archive.testzip() is not None or {name: archive.read(name) for name in archive.namelist()} != files:
            raise ValueError("Archive integrity or byte verification failed")
    if snapshot(folder) != files:
        raise ValueError("Source changed during packaging; wait for a stable build")
    manifest = {
        "id": mod_id, "version": version, "source": str(folder),
        "built_against": (ROOT / "built_against.txt").read_text(encoding="utf-8").strip(),
        "packaged_utc": datetime.now(timezone.utc).isoformat(),
        "archive": archive_path.name, "archive_sha256": sha(content),
        "file_count": len(files), "files_sha256": hashes,
    }
    if provenance is not None:
        manifest["build_provenance"] = provenance
    rendered = json.dumps(manifest, indent=2) + "\n"
    RELEASES.mkdir(exist_ok=True)
    # Exclusive creation is the final protection against concurrent packaging.
    created = []
    try:
        with archive_path.open("xb") as output:
            created.append(archive_path)
            output.write(content)
        with manifest_path.open("x", encoding="utf-8") as output:
            created.append(manifest_path)
            output.write(rendered)
    except OSError:
        for path in created:
            path.unlink()
        raise
    if archive_path.read_bytes() != content:
        raise OSError(f"Archive changed after writing: {archive_path}")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, default=ROOT / "mod")
    args = parser.parse_args(argv)
    try:
        manifest = package(args.mod)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Packaging failed: {error}\n")
    print(f"Verified {manifest['file_count']} files: {RELEASES / manifest['archive']}")
    print(f"SHA256 {manifest['archive_sha256']}")


if __name__ == "__main__":
    main()
