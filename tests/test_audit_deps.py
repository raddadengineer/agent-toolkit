#!/usr/bin/env python3
"""
Unit tests for audit_deps.py (dependency-auditor skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import audit_deps


class TestAuditDeps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_requirements_passes(self):
        req = self.dir / "requirements.txt"
        req.write_text("flask==3.0.0\nrequests>=2.31.0\n", encoding="utf-8")

        res = audit_deps.audit_repository_deps(self.dir)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["critical_count"], 0)

    def test_detects_wildcard_pinning(self):
        req = self.dir / "requirements.txt"
        req.write_text("urllib3==*\n", encoding="utf-8")

        res = audit_deps.audit_repository_deps(self.dir)
        self.assertEqual(res["status"], "fail")
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("DEP-WILDCARD", ids)

    def test_detects_unpinned_dependency(self):
        req = self.dir / "requirements.txt"
        req.write_text("numpy\n", encoding="utf-8")

        res = audit_deps.audit_repository_deps(self.dir)
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("DEP-UNPINNED", ids)

    def test_detects_deprecated_package(self):
        req = self.dir / "requirements.txt"
        req.write_text("pycrypto==2.6.1\n", encoding="utf-8")

        res = audit_deps.audit_repository_deps(self.dir)
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("DEP-DEPRECATED", ids)


if __name__ == "__main__":
    unittest.main()
