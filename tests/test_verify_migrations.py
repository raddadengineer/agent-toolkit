#!/usr/bin/env python3
"""
Unit tests for verify_migrations.py.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_migrations


class TestVerifyMigrations(unittest.TestCase):
    def test_detect_locking_add_not_null(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_file = Path(tmpdir) / "0001_add_user_status.sql"
            mig_file.write_text("ALTER TABLE users ADD COLUMN status VARCHAR(32) NOT NULL;\n", encoding="utf-8")

            findings = verify_migrations.audit_sql_migration(mig_file)
            self.assertTrue(len(findings) > 0)
            rule_ids = [f["id"] for f in findings]
            self.assertIn("MIG-LOCK-ADD-NOT-NULL", rule_ids)

    def test_detect_non_concurrent_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mig_file = Path(tmpdir) / "0002_add_index.sql"
            mig_file.write_text("CREATE INDEX idx_users_email ON users(email);\n", encoding="utf-8")

            findings = verify_migrations.audit_sql_migration(mig_file)
            self.assertTrue(len(findings) > 0)
            rule_ids = [f["id"] for f in findings]
            self.assertIn("MIG-LOCK-NON-CONCURRENT-INDEX", rule_ids)


if __name__ == "__main__":
    unittest.main()
