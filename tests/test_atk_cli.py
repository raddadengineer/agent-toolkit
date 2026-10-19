#!/usr/bin/env python3
"""
Unit tests for the global bin/atk CLI launcher.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
ATK_BIN = TOOLKIT_ROOT / "bin" / "atk"


class TestAtkCli(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_cli_test_")
        self.target = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_atk_help(self):
        result = subprocess.run([str(ATK_BIN), "help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Agent Toolkit CLI (atk)", result.stdout)
        self.assertIn("Core Commands:", result.stdout)

    def test_atk_version(self):
        result = subprocess.run([str(ATK_BIN), "version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("agent-toolkit (atk) v1.0.0", result.stdout)
        self.assertIn(str(TOOLKIT_ROOT), result.stdout)

    def test_atk_install_into_target(self):
        result = subprocess.run(
            [str(ATK_BIN), "install", "--target", str(self.target), "--tool", "claude"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        claude_commands = self.target / ".claude" / "commands"
        self.assertTrue(claude_commands.exists())
        self.assertTrue((claude_commands / "session-starter.md").exists())
        self.assertTrue((self.target / "CLAUDE.md").exists())

    def test_atk_unknown_command(self):
        result = subprocess.run([str(ATK_BIN), "foobar_invalid"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown command: foobar_invalid", result.stdout)


if __name__ == "__main__":
    unittest.main()
