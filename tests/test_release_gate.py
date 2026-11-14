"""A release gate must reject incomplete or stale evidence, not just FAIL lines."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import release_gate as gate
import steam_upload


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run'
        self.run.mkdir()
        (self.run / 'meta.json').write_text(json.dumps({'status': 'done', 'date': 'March 31, 1836'}))
        (self.run / 'assertions.log').write_text('HOTFIX PASS a\nHOTFIX SUITE COMPLETE\n')
        (self.run / 'error.log').write_text('')
        self.spec = {'mode': 'automatic', 'until': '1836.4.1'}

    def evaluate(self):
        return gate.evaluate_case(self.spec, ['a'], [self.run])

    def test_complete_case_passes(self):
        self.assertTrue(self.evaluate()['passed'])

    def test_crash_after_pass_is_rejected(self):
        (self.run / 'meta.json').write_text(json.dumps({'status': 'crashed', 'date': 'March 31, 1836'}))
        self.assertFalse(self.evaluate()['passed'])

    def test_missing_error_log_is_not_clean(self):
        (self.run / 'error.log').unlink()
        self.assertFalse(self.evaluate()['passed'])

    def test_short_run_and_missing_completion_are_rejected(self):
        (self.run / 'meta.json').write_text(json.dumps({'status': 'done', 'date': 'March 1, 1836'}))
        self.assertFalse(self.evaluate()['passed'])
        (self.run / 'assertions.log').write_text('HOTFIX PASS a\n')
        self.assertFalse(self.evaluate()['passed'])

    def test_repeated_checks_require_every_sample(self):
        self.spec['occurrences'] = 21
        self.assertFalse(self.evaluate()['passed'])
        (self.run / 'assertions.log').write_text('HOTFIX PASS a\n' * 21 + 'HOTFIX SUITE COMPLETE\n')
        self.assertTrue(self.evaluate()['passed'])

    def test_failure_is_not_erased_by_later_pass(self):
        (self.run / 'assertions.log').write_text('HOTFIX FAIL a\nHOTFIX PASS a\nHOTFIX SUITE COMPLETE\n')
        self.assertFalse(self.evaluate()['passed'])

    def test_reload_requires_two_processes_and_checkpoint(self):
        self.spec['mode'] = 'reload'
        self.assertFalse(self.evaluate()['passed'])

    def test_new_fixture_cannot_silently_escape_inventory(self):
        (self.root / 'new_case.txt').write_text('namespace = test')
        with self.assertRaisesRegex(ValueError, 'Unregistered'):
            gate.check_inventory({}, self.root)

    def test_payload_hashes_ignore_artwork_but_not_scripts(self):
        (self.root / 'thumbnail.png').write_bytes(b'old')
        (self.root / 'script.txt').write_text('old')
        before = gate.payload(gate.snapshot(self.root))
        (self.root / 'thumbnail.png').write_bytes(b'new')
        self.assertEqual(before, gate.payload(gate.snapshot(self.root)))
        (self.root / 'script.txt').write_text('changed')
        self.assertNotEqual(before, gate.payload(gate.snapshot(self.root)))

    def report_fixture(self):
        target = self.root / 'payload'
        target.mkdir()
        (target / 'script.txt').write_text('production')
        hashes = gate.snapshot(target)
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps({'source_sha256': hashes, 'expected_assertions': ['a']}))
        result = self.evaluate()
        result.update(manifest=str(manifest), manifest_sha256=gate.digest(manifest), expected=['a'],
                      runs=[str(self.run)], checkpoint=None)
        report = self.root / 'report.json'
        data = {'automatic_pass': True, 'results': {'case': result}, 'source_sha256': hashes,
                'test_inputs_sha256': {'test': 'hash'}, 'python_exit_code': 0, 'python_logs_sha256': {}}
        report.write_text(json.dumps(data))
        catalog = self.root / 'catalog.json'
        catalog.write_text(json.dumps({'suites': {'case': self.spec}}))
        for mock in [patch.object(gate, 'CATALOG', catalog), patch.object(gate, 'check_inventory'),
                     patch.object(gate, 'test_inputs', return_value={'test': 'hash'})]:
            mock.start()
            self.addCleanup(mock.stop)
        return report, target, data

    def test_verification_rechecks_evidence_and_payload(self):
        report, target, _ = self.report_fixture()
        gate.verify_report(report, target)
        (target / 'script.txt').write_text('different')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            gate.verify_report(report, target)

    def test_verification_rejects_edited_logs(self):
        report, target, _ = self.report_fixture()
        (self.run / 'assertions.log').write_text('HOTFIX PASS a\n')
        with self.assertRaisesRegex(ValueError, 'Changed evidence'):
            gate.verify_report(report, target)

    def test_subset_cannot_claim_full_pass(self):
        report, target, data = self.report_fixture()
        data['results'] = {}
        report.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'complete passing'):
            gate.verify_report(report, target)

    def test_stale_harness_invalidates_report(self):
        report, target, data = self.report_fixture()
        data['test_inputs_sha256'] = {'test': 'old'}
        report.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'harness changed'):
            gate.verify_report(report, target)

    def test_content_upload_without_gate_stops_before_steam(self):
        with patch.object(steam_upload, 'inspect_stage', return_value={'folder': str(self.root)}), \
             patch.object(steam_upload, 'known_id', return_value=123), \
             patch.object(steam_upload, 'description', return_value=('description', 'hash')), \
             patch.object(steam_upload, 'changelog', return_value='notes'), \
             patch.object(steam_upload, 'receipt'), patch.object(steam_upload, 'emit'), \
             patch.object(steam_upload, 'Steam') as steam:
            with self.assertRaises(SystemExit):
                steam_upload.main(['update', 'stable', '--public', '--execute'])
            steam.assert_not_called()


if __name__ == '__main__':
    unittest.main()
