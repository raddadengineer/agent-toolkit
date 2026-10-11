#!/usr/bin/env python3
"""
Unit tests for check_doc_drift.py.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import check_doc_drift


class TestCheckDocDrift(unittest.TestCase):
    def test_detect_undocumented_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skills = root / "skills"
            skills.mkdir()
            (skills / "mystery_skill").mkdir()

            readme = root / "README.md"
            readme.write_text("# Readme\nNo mention of mystery.\n", encoding="utf-8")

            report = check_doc_drift.check_documentation_drift(root)
            self.assertTrue(report["warning_count"] > 0)
            items = [f["item"] for f in report["findings"]]
            self.assertIn("mystery_skill", items)


if __name__ == "__main__":
    unittest.main()
