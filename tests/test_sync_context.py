#!/usr/bin/env python3
"""
Unit tests for universal sync_context.py helper script.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "skills" / "session-closer" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import sync_context


class TestSyncContext(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_test_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_calculate_checksum(self):
        sample_file = self.root / "sample.txt"
        content = b"Hello, Agent Toolkit!"
        sample_file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        actual = sync_context.calculate_checksum(sample_file)
        self.assertEqual(expected, actual)

    def test_calculate_checksum_missing(self):
        missing = self.root / "nonexistent.txt"
        self.assertEqual("MISSING", sync_context.calculate_checksum(missing))

    def test_sync_files(self):
        f1 = self.root / "AGENTS.md"
        f2 = self.root / "CLAUDE.md"
        f3 = self.root / "GEMINI.md"

        f1.write_text("# Primary Content\nLine 2\n", encoding="utf-8")
        f2.write_text("# Old Content\n", encoding="utf-8")
        # f3 does not exist yet

        tracked = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]
        sync_context.sync_files(self.root, tracked, source_name="AGENTS.md")

        self.assertTrue(f1.exists())
        self.assertTrue(f2.exists())
        self.assertTrue(f3.exists())

        self.assertEqual(f1.read_bytes(), f2.read_bytes())
        self.assertEqual(f1.read_bytes(), f3.read_bytes())
        self.assertTrue(sync_context.check_sync(self.root, tracked))

    def test_auto_detect_latest_source(self):
        f1 = self.root / "AGENTS.md"
        f2 = self.root / "CLAUDE.md"

        f1.write_text("Earlier version", encoding="utf-8")
        os.utime(f1, (1000, 1000))

        f2.write_text("Newest version", encoding="utf-8")
        os.utime(f2, (2000, 2000))

        latest = sync_context.detect_latest_source(self.root, ["AGENTS.md", "CLAUDE.md"])
        self.assertEqual("CLAUDE.md", latest)

    def test_log_session_new_file(self):
        sync_context.log_session(
            repo_root=self.root,
            title="Initial Setup",
            goal="Test session logger",
            changes=["Added module A", "Fixed bug B"],
            validation="Unit tests passed 100%",
            next_steps=["Deploy release v1.0"],
        )

        log_file = self.root / "SESSION_LOG.md"
        self.assertTrue(log_file.exists())
        content = log_file.read_text(encoding="utf-8")

        self.assertIn("Session Log & Handover Ledger", content)
        self.assertIn("Initial Setup", content)
        self.assertIn("Test session logger", content)
        self.assertIn("Added module A", content)
        self.assertIn("Unit tests passed 100%", content)
        self.assertIn("Deploy release v1.0", content)

    def test_log_session_prepend_existing(self):
        # Create an existing log with header and session 1
        sync_context.log_session(
            repo_root=self.root,
            title="Session 1",
            goal="Goal 1",
            changes=["Change 1"],
            validation="OK 1",
            next_steps=["Next 1"],
        )

        # Prepend session 2
        sync_context.log_session(
            repo_root=self.root,
            title="Session 2",
            goal="Goal 2",
            changes=["Change 2"],
            validation="OK 2",
            next_steps=["Next 2"],
        )

        content = (self.root / "SESSION_LOG.md").read_text(encoding="utf-8")
        # Session 2 should appear before Session 1
        pos_s2 = content.find("Session 2")
        pos_s1 = content.find("Session 1")
        self.assertNotEqual(pos_s2, -1)
        self.assertNotEqual(pos_s1, -1)
        self.assertLess(pos_s2, pos_s1)

    def test_init_project(self):
        tracked = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]
        sync_context.init_project(self.root, tracked)

        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertTrue((self.root / "CLAUDE.md").exists())
        self.assertTrue((self.root / "GEMINI.md").exists())
        self.assertTrue((self.root / "SESSION_LOG.md").exists())
        self.assertTrue(sync_context.check_sync(self.root, tracked))


if __name__ == "__main__":
    unittest.main()
