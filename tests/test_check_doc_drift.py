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

    def test_detect_and_sync_script_drift(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_scripts = root / "skills" / "demo" / "scripts"
            skill_scripts.mkdir(parents=True)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True)

            (root / "README.md").write_text("# demo\n", encoding="utf-8")

            s1 = skill_scripts / "tool.py"
            s2 = scripts_dir / "tool.py"
            s1.write_text("print('v2')\n", encoding="utf-8")
            s2.write_text("print('v1')\n", encoding="utf-8")

            report = check_doc_drift.check_documentation_drift(root)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["critical_count"], 1)

            synced = check_doc_drift.sync_skill_scripts(root)
            self.assertIn("tool.py", synced)

            report_after = check_doc_drift.check_documentation_drift(root)
            self.assertEqual(report_after["status"], "pass")
            self.assertEqual(report_after["critical_count"], 0)


if __name__ == "__main__":
    unittest.main()
