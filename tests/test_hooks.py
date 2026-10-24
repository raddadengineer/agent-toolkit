#!/usr/bin/env python3
"""
Unit tests for scripts/guard_command.py, scripts/auto_format.py, and hooks/hooks.json.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import guard_command
import auto_format


class TestHooksAndGuards(unittest.TestCase):
    def test_guard_blocks_destructive_rm(self):
        self.assertEqual(guard_command.evaluate_command("rm -rf /")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("rm -r -f /")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("rm --recursive --force ~")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("rm -rf $HOME")["decision"], "deny")

    def test_guard_allows_safe_rm(self):
        self.assertEqual(guard_command.evaluate_command("rm -rf ./build")["decision"], "allow")
        self.assertEqual(guard_command.evaluate_command("rm -f /tmp/test.txt")["decision"], "allow")

    def test_guard_blocks_force_push_and_branch_delete(self):
        self.assertEqual(guard_command.evaluate_command("git push --force origin main")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("git push origin main -f")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("git branch -D main")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("git clean -fdx")["decision"], "deny")
        self.assertEqual(guard_command.evaluate_command("git reset --hard origin/main")["decision"], "deny")

    def test_guard_allows_safe_git_commands(self):
        self.assertEqual(guard_command.evaluate_command("git push origin feature/login")["decision"], "allow")
        self.assertEqual(guard_command.evaluate_command("git push --force-with-lease origin feature/login")["decision"], "allow")
        self.assertEqual(guard_command.evaluate_command("git status --short")["decision"], "allow")

    def test_guard_stdin_stdout_protocol(self):
        payload = json.dumps({"toolCall": {"args": {"CommandLine": "rm -rf /"}}})
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "guard_command.py")],
            input=payload,
            capture_output=True,
            text=True,
            check=True,
        )
        out = json.loads(proc.stdout)
        self.assertEqual(out["decision"], "deny")

    def test_auto_format_stdin_stdout_protocol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_file = Path(tmpdir) / "sample.py"
            dummy_file.write_text("x = 1\n", encoding="utf-8")
            payload = json.dumps({"toolCall": {"args": {"TargetFile": str(dummy_file)}}})
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "auto_format.py")],
                input=payload,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(proc.stdout), {})


if __name__ == "__main__":
    unittest.main()
