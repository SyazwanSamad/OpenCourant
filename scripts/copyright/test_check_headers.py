# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check that repairs preserve attribution on moved and derived sources."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_headers as checker


class HeaderRepairs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'source.F'

    def write_header(self, variant):
        header = '\r\n'.join(line.rstrip('\r') for line in checker.render(variant, '2026', 'Copyright>', False))
        body = b'      X = 1\r\nC form feed:\x0c preserved\r\n      END\r\n'
        self.path.write_bytes(header.encode('latin1') + b'\r\n' + body)
        return body

    def test_legacy_source_at_new_path_keeps_original_attribution(self):
        body = self.write_header('legacy')
        report = checker.check_file(str(self.path), set(), 2026)
        self.assertEqual(report.target, ('modified', '2026'))
        self.assertTrue(checker.fix_file(str(self.path), report, 2026, set()))
        data = self.path.read_bytes()
        self.assertIn(b'Copyright (C) 2026 Siemens', data)
        self.assertIn(b'Modified by the OpenCourant project, 2026.', data)
        self.assertTrue(data.endswith(body))
        self.assertFalse(checker.check_file(str(self.path), set(), 2026).errors)

    def test_modified_legacy_source_at_new_path_is_valid(self):
        self.write_header('modified')
        self.assertFalse(checker.check_file(str(self.path), set(), 2026).errors)

    def test_malformed_legacy_source_at_new_path_keeps_attribution(self):
        self.write_header('legacy')
        self.path.write_bytes(self.path.read_bytes().replace(b'WITHOUT ANY WARRANTY', b'broken warranty line'))
        with patch.object(checker, 'git_blob', return_value=None):
            report = checker.check_file(str(self.path), set(), 2026)
        self.assertEqual(report.target, ('modified', '2026'))

    def test_new_source_without_legacy_notice_uses_new_header(self):
        body = b'      END\n'
        self.path.write_bytes(body)
        report = checker.check_file(str(self.path), set(), 2026)
        self.assertEqual(report.target, ('new', '2026'))
        self.assertTrue(checker.fix_file(str(self.path), report, 2026, set()))
        self.assertNotIn(b'Siemens', self.path.read_bytes())
        self.assertTrue(self.path.read_bytes().endswith(body))
        self.assertFalse(checker.check_file(str(self.path), set(), 2026).errors)

    def test_changed_legacy_source_still_requires_modification_notice(self):
        self.write_header('legacy')
        with patch.object(checker, 'git_blob', return_value=b'      OLD_BODY\n'):
            report = checker.check_file(str(self.path), {str(self.path)}, 2026)
        self.assertEqual(report.target, ('modified', '2026'))


if __name__ == '__main__':
    unittest.main()
