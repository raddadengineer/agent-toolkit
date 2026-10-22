#!/usr/bin/env python3
"""
Unit tests for review_code.py (code-reviewer skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import review_code


class TestReviewCode(unittest.TestCase):
    def test_clean_diff_verdict_approve(self):
        diff_text = """diff --git a/src/service.py b/src/service.py
--- a/src/service.py
+++ b/src/service.py
@@ -10,3 +10,4 @@
+def add_numbers(a: int, b: int) -> int:
+    return a + b
"""
        changed_files = ["src/service.py", "tests/test_service.py"]
        res = review_code.review_diff(diff_text, changed_files)
        self.assertEqual(res["verdict"], "APPROVE")
        self.assertEqual(res["critical_count"], 0)

    def test_detects_silent_error_swallowing(self):
        diff_text = """diff --git a/src/worker.py b/src/worker.py
--- a/src/worker.py
+++ b/src/worker.py
@@ -25,3 +25,5 @@
+try:
+    do_critical_work()
+except Exception:
+    pass
"""
        changed_files = ["src/worker.py", "tests/test_worker.py"]
        res = review_code.review_diff(diff_text, changed_files)
        self.assertEqual(res["verdict"], "REQUEST CHANGES")
        self.assertGreater(res["critical_count"], 0)
        finding_ids = [f["id"] for f in res["findings"]]
        self.assertIn("CRIT-SWALLOW-ERR", finding_ids)

    def test_detects_async_blocking_sleep(self):
        diff_text = """diff --git a/src/async_handler.py b/src/async_handler.py
--- a/src/async_handler.py
+++ b/src/async_handler.py
@@ -12,3 +12,5 @@
+async def handle_request():
+    time.sleep(5)
"""
        changed_files = ["src/async_handler.py", "tests/test_async_handler.py"]
        res = review_code.review_diff(diff_text, changed_files)
        self.assertEqual(res["verdict"], "REQUEST CHANGES")
        finding_ids = [f["id"] for f in res["findings"]]
        self.assertIn("CRIT-ASYNC-BLOCK", finding_ids)

    def test_warns_on_production_changes_without_tests(self):
        diff_text = """diff --git a/src/billing.py b/src/billing.py
--- a/src/billing.py
+++ b/src/billing.py
@@ -1,2 +1,3 @@
+TAX_RATE = 0.08
"""
        changed_files = ["src/billing.py"]
        res = review_code.review_diff(diff_text, changed_files)
        self.assertEqual(res["verdict"], "APPROVE (with recommendations)")
        finding_ids = [f["id"] for f in res["findings"]]
        self.assertIn("WARN-NO-TESTS", finding_ids)


if __name__ == "__main__":
    unittest.main()
