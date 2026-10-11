#!/usr/bin/env python3
"""
Unit tests for bisect_debugger.py.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import bisect_debugger


class TestBisectDebugger(unittest.TestCase):
    def test_analyze_python_trace(self):
        trace = """Traceback (most recent call last):
  File "src/app.py", line 42, in handle_request
    result = calculate_total(order)
  File "src/billing.py", line 105, in calculate_total
    raise ValueError("Invalid currency code")
ValueError: Invalid currency code"""

        result = bisect_debugger.analyze_trace_text(trace)
        self.assertEqual(result["error_type"], "ValueError")
        self.assertEqual(result["error_message"], "Invalid currency code")
        self.assertEqual(result["total_frames"], 2)
        self.assertEqual(result["suggested_file"], "src/billing.py")
        self.assertEqual(result["suggested_line"], 105)

    def test_generate_reproduction_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "repro.sh"
            script = bisect_debugger.generate_reproduction_script("echo 'testing failure' && exit 1", str(out_path))
            self.assertTrue(Path(script).exists())
            content = Path(script).read_text(encoding="utf-8")
            self.assertIn("echo 'testing failure'", content)


if __name__ == "__main__":
    unittest.main()
