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
        self.assertIn("agent-toolkit (atk) v1.", result.stdout)
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

    def test_atk_debug_help(self):
        result = subprocess.run([str(ATK_BIN), "debug", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Universal Root-Cause Debugger", result.stdout)

    def test_atk_drift_check(self):
        result = subprocess.run([str(ATK_BIN), "drift"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Documentation Drift Audit", result.stdout)

    def test_atk_review_command(self):
        result = subprocess.run([str(ATK_BIN), "review", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Automated Adversarial Code Reviewer", result.stdout)

    def test_atk_test_gen_command(self):
        result = subprocess.run([str(ATK_BIN), "test-gen", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Deterministic Test Suite & Boundary Matrix Generator", result.stdout)

    def test_atk_adr_command(self):
        result = subprocess.run([str(ATK_BIN), "adr", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Architecture Decision Record (ADR) Manager", result.stdout)

    def test_atk_docker_command(self):
        result = subprocess.run([str(ATK_BIN), "docker", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Container Hardening & Dockerfile Security Linter", result.stdout)

    def test_atk_ci_command(self):
        result = subprocess.run([str(ATK_BIN), "ci", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("CI/CD Pipeline Synthesizer & Workflow Security Auditor", result.stdout)

    def test_atk_dep_command(self):
        result = subprocess.run([str(ATK_BIN), "dep", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Multi-Ecosystem Dependency Security & Manifest Auditor", result.stdout)

    def test_atk_release_command(self):
        result = subprocess.run([str(ATK_BIN), "release", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Semantic Versioning, Conventional Commits & Changelog Manager", result.stdout)

    def test_atk_installs_command(self):
        result = subprocess.run([str(ATK_BIN), "installs", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Manage agent-toolkit project installation registry", result.stdout)

    def test_atk_update_all_flow(self):
        custom_reg = self.target / "custom_installs.json"
        env = dict(os.environ, AGENT_TOOLKIT_REGISTRY=str(custom_reg))

        # 1. Install into target
        install_res = subprocess.run(
            [str(ATK_BIN), "install", "--target", str(self.target), "--tool", "claude"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(install_res.returncode, 0)

        # 2. Check installs listing
        list_res = subprocess.run(
            [str(ATK_BIN), "installs"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(list_res.returncode, 0)
        self.assertIn(str(self.target.resolve()), list_res.stdout)

        # 3. Test atk update --all
        update_res = subprocess.run(
            [str(ATK_BIN), "update", "--all"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(update_res.returncode, 0)
        self.assertIn("Updated:", update_res.stdout)
        self.assertIn(str(self.target.resolve()), update_res.stdout)


if __name__ == "__main__":
    unittest.main()
