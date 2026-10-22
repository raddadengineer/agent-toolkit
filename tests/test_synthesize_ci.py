#!/usr/bin/env python3
"""
Unit tests for synthesize_ci.py (ci-workflow skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import synthesize_ci


class TestSynthesizeCi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_scaffolds_workflow(self):
        synthesize_ci.init_ci_pipeline(self.dir, "python")
        ci_path = self.dir / ".github" / "workflows" / "ci.yml"
        self.assertTrue(ci_path.exists())

        res = synthesize_ci.audit_repository_ci(self.dir)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["critical_count"], 0)

    def test_detects_unpinned_action_branch(self):
        wf_dir = self.dir / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        bad_wf = wf_dir / "bad.yml"
        bad_wf.write_text(
            """name: Bad CI
permissions: read-all
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@main
""",
            encoding="utf-8",
        )

        res = synthesize_ci.audit_repository_ci(self.dir)
        self.assertEqual(res["status"], "fail")
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("CI-UNPINNED-ACTION", ids)


if __name__ == "__main__":
    unittest.main()
