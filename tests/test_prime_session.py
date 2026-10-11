#!/usr/bin/env python3
"""
Unit tests for prime_session.py helper script.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
import sys

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "skills" / "session-starter" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import prime_session


class TestPrimeSession(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_prime_test_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_last_session(self):
        sample_log = """# Project — Session Log & Handover Ledger

### Session [2026-10-10 18:30] — Initial Feature Release

- **Goal**:
  - Implement basic user authentication.
- **Changes Completed**:
  - Added AuthController.ts
  - Configured JWT verification
- **Validation**:
  - All 15 unit tests passed (exit 0)
- **Next Steps / Handover**:
  - Implement refresh token rotation
  - Setup Redis session store

---

### Session [2026-10-09 12:00] — Prior Work
- **Goal**:
  - Previous goal
"""
        log_file = self.root / "SESSION_LOG.md"
        log_file.write_text(sample_log, encoding="utf-8")

        parsed = prime_session.parse_last_session(log_file)
        self.assertIsNotNone(parsed)
        self.assertEqual("2026-10-10 18:30", parsed["timestamp"])
        self.assertEqual("Initial Feature Release", parsed["title"])
        self.assertEqual("Implement basic user authentication.", parsed["goal"])
        self.assertEqual(["Added AuthController.ts", "Configured JWT verification"], parsed["changes"])
        self.assertIn("15 unit tests passed", parsed["validation"])
        self.assertEqual(["Implement refresh token rotation", "Setup Redis session store"], parsed["next_steps"])

    def test_parse_last_session_missing_file(self):
        missing = self.root / "NONEXISTENT_LOG.md"
        self.assertIsNone(prime_session.parse_last_session(missing))

    def test_check_context_sync_all_missing(self):
        res = prime_session.check_context_sync(self.root)
        self.assertFalse(res["in_sync"])
        self.assertEqual("missing_all", res["status"])

    def test_check_context_sync_matching(self):
        for f in ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]:
            (self.root / f).write_text("Identical content across files", encoding="utf-8")

        res = prime_session.check_context_sync(self.root)
        self.assertTrue(res["in_sync"])
        self.assertEqual("ok", res["status"])


if __name__ == "__main__":
    unittest.main()
