"""Reject launcher-only metadata which Victoria 3 1.15.1 cannot read."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spec_release_packager", ROOT / "tools/package_release.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class ReleaseMetadataTests(unittest.TestCase):
    def test_game_rejected_relationships_fail_before_artifact_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / ".metadata").mkdir(parents=True)
            output = root / "releases"
            with patch.object(packager, "RELEASES", output):
                for mod_id in ("speculative_markets", "speculative_markets_cmf_compat"):
                    for kind in ("incompatible_with", "load_after", "load_before", None):
                        with self.subTest(mod_id=mod_id, kind=kind):
                            metadata = {"id": mod_id, "version": "1.0.2", "relationships": [
                                {"rel_type": kind, "id": "other", "resource_type": "mod"}]}
                            (source / ".metadata/metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
                            with self.assertRaisesRegex(ValueError, "only dependency"):
                                packager.package(source)
                            self.assertFalse(output.exists())
                metadata["id"] = "speculative_markets"
                metadata["relationships"][0]["rel_type"] = "dependency"
                (source / ".metadata/metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
                manifest = packager.package(source)
                self.assertTrue((output / manifest["archive"]).is_file())


if __name__ == "__main__":
    unittest.main()
