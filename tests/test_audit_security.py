#!/usr/bin/env python3
"""
Unit tests for audit_security.py.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import audit_security


class TestAuditSecurity(unittest.TestCase):
    def test_sast_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vuln_file = Path(tmpdir) / "vulnerable.py"
            vuln_file.write_text("import os\nos.system('ls ' + user_input)\n", encoding="utf-8")

            findings = audit_security.scan_file_for_sast(vuln_file)
            self.assertTrue(len(findings) > 0)
            rule_ids = [f["id"] for f in findings]
            self.assertIn("SEC-CMDI", rule_ids)

    def test_clean_file_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clean_file = Path(tmpdir) / "safe.py"
            clean_file.write_text("import subprocess\nsubprocess.run(['ls', '-la'])\n", encoding="utf-8")

            findings = audit_security.scan_file_for_sast(clean_file)
            self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()
