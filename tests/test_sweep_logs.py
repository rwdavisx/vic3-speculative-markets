"""The unattended runner must retain complete engine telemetry and assertions."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sweep


class LogPollingTests(unittest.TestCase):
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
