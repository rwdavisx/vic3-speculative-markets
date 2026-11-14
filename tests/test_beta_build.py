"""Packaging regressions: isolation, identity, stale files and reproducibility."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spec_beta_builder", ROOT / "beta/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BetaBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "stable"
        self.out = self.root / "beta"
        self.source.mkdir()
        (self.source / ".metadata").mkdir()
        (self.source / builder.METADATA).write_text(json.dumps({
            "id": builder.STABLE_ID, "name": "Speculative Markets", "version": "1.0.2",
            "supported_game_version": "1.15.*", "relationships": [],
            "steam_id": "must-not-be-inherited",
        }), encoding="utf-8")
        (self.source / "events").mkdir()
        (self.source / "events/spec_events.txt").write_bytes(b"spec_event = {}\n")
        self.guard = patch.object(builder, "BETA_ROOT", self.out)
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def test_distinct_identity_same_gameplay_and_reproducible_archive(self):
        before = builder.snapshot(self.source)
        first = builder.build(self.source, self.out, 1)
        archive = Path(first["archive"]).read_bytes()
        second = builder.build(self.source, self.out, 1)
        self.assertEqual(before, builder.snapshot(self.source))
        self.assertEqual(archive, Path(second["archive"]).read_bytes())
        result = builder.snapshot(self.out / "mod")
        self.assertEqual(set(before), set(result))
        self.assertEqual([key for key in before if before[key] != result[key]], [builder.METADATA])
        metadata = json.loads(result[builder.METADATA])
        self.assertEqual(metadata["id"], builder.BETA_ID)
        self.assertEqual(metadata["version"], "1.0.2-beta.1")
        self.assertNotIn("steam_id", metadata)
        self.assertEqual(metadata["relationships"], [])
        self.assertIn("never both", metadata["short_description"])
        with zipfile.ZipFile(first["archive"]) as packed:
            self.assertEqual(result, {name: packed.read(name) for name in packed.namelist()})

    def test_game_reader_rejects_launcher_only_relationship_types(self):
        source = builder.snapshot(self.source)
        metadata = json.loads(source[builder.METADATA])
        for kind in ("incompatible_with", "load_after", "load_before", None):
            with self.subTest(kind=kind):
                metadata["relationships"] = [{"rel_type": kind, "id": "other", "resource_type": "mod"}]
                source[builder.METADATA] = json.dumps(metadata).encode("utf-8")
                with self.assertRaisesRegex(ValueError, "only dependency"):
                    builder.beta_files(source, 2)
        metadata["relationships"] = [{"rel_type": "dependency", "id": "other", "resource_type": "mod"}]
        source[builder.METADATA] = json.dumps(metadata).encode("utf-8")
        _, beta, _ = builder.beta_files(source, 2)
        self.assertEqual(beta["relationships"], metadata["relationships"])

    def test_refuses_source_destination_and_outside_beta(self):
        before = builder.snapshot(self.source)
        for out in (self.source, self.root, self.root / "other"):
            with self.subTest(out=out), self.assertRaises(ValueError):
                builder.build(self.source, out)
        self.assertEqual(before, builder.snapshot(self.source))

    def test_refuses_debug_and_preserves_existing_beta(self):
        builder.build(self.source, self.out)
        before = builder.snapshot(self.out)
        (self.source / "events/test.txt").write_text('debug_log = "test"', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "test/debug"):
            builder.build(self.source, self.out, 2)
        self.assertEqual(before, builder.snapshot(self.out))

    def test_rebuild_removes_stale_owned_files_but_protects_local_changes(self):
        builder.build(self.source, self.out)
        (self.source / "events/spec_events.txt").unlink()
        builder.build(self.source, self.out, 2)
        self.assertFalse((self.out / "mod/events/spec_events.txt").exists())
        changed = self.out / "mod/my_changes.txt"
        changed.write_text("keep this", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "modified"):
            builder.build(self.source, self.out, 3)
        self.assertEqual(changed.read_text(encoding="utf-8"), "keep this")

    def test_changed_artifact_requires_a_new_revision(self):
        first = builder.build(self.source, self.out)
        before = builder.snapshot(self.out)
        (self.source / "events/spec_events.txt").write_text("new_event = {}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "increase --revision"):
            builder.build(self.source, self.out)
        self.assertEqual(before, builder.snapshot(self.out))
        second = builder.build(self.source, self.out, 2)
        self.assertNotEqual(first["archive_sha256"], second["archive_sha256"])


if __name__ == "__main__":
    unittest.main()
