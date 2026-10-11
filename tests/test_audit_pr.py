#!/usr/bin/env python3
"""
Unit tests for audit_pr.py helper script.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
import sys

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "skills" / "pr-prep" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import audit_pr


class TestAuditPR(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_audit_test_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_audit_diff_detects_debug_statements(self):
        # Mock git diff output by testing the pattern scanning logic
        diff_text = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -10,3 +10,5 @@
+    x = 10
+    print("debugging value of x")
+    return x
"""
        # Test pattern detection directly against sample lines
        findings = []
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added = line[1:]
                for pattern, desc in audit_pr.DEBUG_PATTERNS:
                    import re
                    if re.search(pattern, added):
                        findings.append(desc)

        self.assertIn("Python print debug statement", findings)

    def test_audit_diff_detects_secrets(self):
        diff_text = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,2 +1,3 @@
+api_key = 'sk_live_1234567890abcdef12345678'
"""
        findings = []
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added = line[1:]
                for pattern, desc, *flags in audit_pr.SECRET_PATTERNS:
                    import re
                    fl = flags[0] if flags else 0
                    if re.search(pattern, added, fl):
                        findings.append(desc)

        self.assertIn("Stripe Live Secret Key", findings)

    def test_generate_pr_markdown(self):
        mock_audit = {
            "changed_files": ["src/index.ts", "src/auth.ts"],
            "changed_count": 2,
            "diff_stat": "src/index.ts | 4 ++++\nsrc/auth.ts | 2 ++",
            "findings": [],
            "clean": True,
        }
        md = audit_pr.generate_pr_markdown(
            self.root,
            mock_audit,
            title="feat: add authentication",
            validation_proof="All 20 tests passed",
        )
        self.assertIn("feat: add authentication", md)
        self.assertIn("src/index.ts", md)
        self.assertIn("src/auth.ts", md)
        self.assertIn("All 20 tests passed", md)


if __name__ == "__main__":
    unittest.main()
