#!/usr/bin/env python3
"""
Unit tests for manage_adr.py (system-architect skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import manage_adr


class TestManageAdr(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.adr_dir = Path(self.tmp.name) / "docs" / "adr"

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_creates_record_0000_and_readme(self):
        manage_adr.init_adr_repo(self.adr_dir)
        rec0 = self.adr_dir / "0000-record-architecture-decisions.md"
        readme = self.adr_dir / "README.md"

        self.assertTrue(rec0.exists())
        self.assertTrue(readme.exists())
        self.assertIn("Record Architecture Decisions", rec0.read_text(encoding="utf-8"))
        self.assertIn("0000", readme.read_text(encoding="utf-8"))

    def test_create_new_adr_increments_sequence(self):
        manage_adr.init_adr_repo(self.adr_dir)
        adr1 = manage_adr.create_new_adr(self.adr_dir, "Adopt Redis for Caching")
        self.assertEqual(adr1.name, "0001-adopt-redis-for-caching.md")
        self.assertTrue(adr1.exists())

        adr2 = manage_adr.create_new_adr(self.adr_dir, "Use PostgreSQL Partitioning")
        self.assertEqual(adr2.name, "0002-use-postgresql-partitioning.md")
        self.assertTrue(adr2.exists())

        records = manage_adr.list_adrs(self.adr_dir)
        self.assertEqual(len(records), 3)  # 0000, 0001, 0002

    def test_audit_passes_on_valid_adrs(self):
        manage_adr.init_adr_repo(self.adr_dir)
        manage_adr.create_new_adr(self.adr_dir, "Switch to gRPC")
        audit = manage_adr.audit_adrs(self.adr_dir)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["records_count"], 2)


if __name__ == "__main__":
    unittest.main()
