"""The unattended runner must retain complete engine telemetry and assertions."""
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sweep


class LogPollingTests(unittest.TestCase):
    def test_multiple_rotations_preserve_chronological_order(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / "debug.log"
            mirror = sweep.observe.Mirror(src, root / "mirror.log", 0)
            src.write_bytes(b"first\n")
            self.assertEqual(mirror.poll(), "first\n")
            with src.open("ab") as stream:
                stream.write(b"tail\n")
            src.rename(root / "debug.2.log")
            (root / "debug.1.log").write_bytes(b"middle\n")
            src.write_bytes(b"latest\n")
            self.assertEqual(mirror.poll(), "tail\nmiddle\nlatest\n")
            self.assertEqual(mirror.poll(), "")

    def test_rotation_preserves_unread_tail_and_larger_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src, dst = root / "debug.log", root / "mirror.log"
            mirror = sweep.observe.Mirror(src, dst, 0)
            src.write_bytes(b"first\n")
            self.assertEqual(mirror.poll(), "first\n")
            with src.open("a", newline="\n") as stream:
                stream.write("unread assertion\n")
            src.rename(root / "debug.1.log")
            src.write_bytes(b"new file is larger than the previous offset\n")
            self.assertEqual(mirror.poll(), "unread assertion\nnew file is larger than the previous offset\n")
            self.assertEqual(mirror.poll(), "")

    def test_partial_rows_and_assertions_survive_poll_boundaries(self):
        job = {"mirror": Mock(), "seen": [], "date": None, "last": 0}
        job["mirror"].poll.side_effect = [
            "prefix HOTFIX PA", "SS complete_case\nPROBE tag=GBR date=January ",
            "2, 1836 gdp=1234\nSPEC tag=GBR conf=", "55\n",
        ]
        with patch.object(sweep, "keep_saves"):
            for _ in range(4):
                sweep.poll(job)
        self.assertEqual(job["seen"], [
            "prefix HOTFIX PASS complete_case",
            "PROBE tag=GBR date=January 2, 1836 gdp=1234",
            "SPEC tag=GBR conf=55",
        ])
        self.assertEqual(job["date"], "January 2, 1836")
        self.assertEqual(job["pending"], "")


if __name__ == "__main__":
    unittest.main()
