#!/usr/bin/env python3
"""
Unit tests for PowerShell installation support (bin/atk.ps1, install.ps1, and profile setup).
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
ATK_PS1 = TOOLKIT_ROOT / "bin" / "atk.ps1"
INSTALL_PS1 = TOOLKIT_ROOT / "install.ps1"
INSTALL_SH = TOOLKIT_ROOT / "install.sh"
PWSH_BIN = shutil.which("pwsh") or shutil.which("powershell")


class TestPowerShellInstall(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_pwsh_test_")
        self.target = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scripts_exist_and_executable(self):
        self.assertTrue(ATK_PS1.exists(), "bin/atk.ps1 must exist")
        self.assertTrue(INSTALL_PS1.exists(), "install.ps1 must exist")
        self.assertTrue(os.access(ATK_PS1, os.X_OK), "bin/atk.ps1 should be executable")
        self.assertTrue(os.access(INSTALL_PS1, os.X_OK), "install.ps1 should be executable")

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_help(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Agent Toolkit CLI (atk) [PowerShell]", result.stdout)
        self.assertIn("Core Commands:", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_version(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "version"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("agent-toolkit (atk) v1.0.0", result.stdout)
        self.assertIn(str(TOOLKIT_ROOT), result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_unknown_command(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "invalid_command_xyz"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown command: invalid_command_xyz", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_debug_help(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "debug", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Universal Root-Cause Debugger", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_drift(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "drift"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Documentation Drift Audit", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_review(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "review", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Automated Adversarial Code Reviewer", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_test_gen(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "test-gen", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Deterministic Test Suite & Boundary Matrix Generator", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_adr(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "adr", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Architecture Decision Record (ADR) Manager", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_docker(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "docker", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Container Hardening & Dockerfile Security Linter", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_ci(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "ci", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("CI/CD Pipeline Synthesizer & Workflow Security Auditor", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_dep(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "dep", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Multi-Ecosystem Dependency Security & Manifest Auditor", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_atk_ps1_release(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(ATK_PS1), "release", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Semantic Versioning, Conventional Commits & Changelog Manager", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_help(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(INSTALL_PS1), "-Help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage: install.ps1", result.stdout)
        self.assertIn("-Global", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_list(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(INSTALL_PS1), "-List"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Agent Toolkit — Available Components:", result.stdout)
        self.assertIn("session-closer", result.stdout)
        self.assertIn("software_engineer", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_target_tool(self):
        result = subprocess.run(
            [
                PWSH_BIN,
                "-NoProfile",
                str(INSTALL_PS1),
                "-Target",
                str(self.target),
                "-Tool",
                "claude",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        commands_dir = self.target / ".claude" / "commands"
        self.assertTrue(commands_dir.exists())
        self.assertTrue((commands_dir / "session-starter.md").exists())
        self.assertTrue((self.target / "CLAUDE.md").exists())

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_all_components(self):
        result = subprocess.run(
            [
                PWSH_BIN,
                "-NoProfile",
                str(INSTALL_PS1),
                "-Target",
                str(self.target),
                "-All",
                "-Mode",
                "copy",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        agents_dir = self.target / ".agents"
        self.assertTrue(agents_dir.exists())
        self.assertTrue((agents_dir / "skills" / "session-starter").exists())
        self.assertTrue((agents_dir / "agents" / "software_engineer").exists())
        self.assertTrue((agents_dir / "hooks.json").exists())
        self.assertTrue((agents_dir / "mcp_config.json").exists())
        self.assertTrue((agents_dir / "scripts").exists())

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_powershell_profile_configuration_and_function_invocation(self):
        profile_file = self.target / "Microsoft.PowerShell_profile.ps1"
        profile_file.write_text("# Existing user configuration\n", encoding="utf-8")

        # Test configuring the profile using PowerShell
        configure_cmd = f"""
        $profilePath = '{profile_file.as_posix()}'
        $toolkitRoot = '{TOOLKIT_ROOT.as_posix()}'
        $atkPs1 = Join-Path $toolkitRoot 'bin/atk.ps1'
        $startMarker = '# >>> agent-toolkit initialize >>>'
        $endMarker = '# <<< agent-toolkit initialize <<<'
        $block = @"
$startMarker
function atk {{ & "$atkPs1" @args }}
function agent-toolkit {{ & "$atkPs1" @args }}
$endMarker
"@
        $existing = Get-Content -LiteralPath $profilePath -Raw
        $newContent = $existing.TrimEnd() + "`n`n" + $block.Trim() + "`n"
        Set-Content -LiteralPath $profilePath -Value $newContent -Encoding utf8
        """
        subprocess.run([PWSH_BIN, "-NoProfile", "-Command", configure_cmd], check=True)

        content = profile_file.read_text(encoding="utf-8")
        self.assertIn("# >>> agent-toolkit initialize >>>", content)
        self.assertIn("function atk", content)
        self.assertIn("function agent-toolkit", content)

        # Verify that dot-sourcing the profile lets us run 'atk version'
        run_via_function = f"""
        . '{profile_file.as_posix()}'
        atk version
        """
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", "-Command", run_via_function],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("agent-toolkit (atk) v1.0.0", result.stdout)

    def test_atk_ps1_installs_and_update_all(self):
        target_dir = Path(self.test_dir) / "pwsh_project"
        target_dir.mkdir()
        custom_reg = Path(self.test_dir) / "pwsh_installs.json"

        env = dict(os.environ, AGENT_TOOLKIT_REGISTRY=str(custom_reg))

        # 1. Install via atk.ps1
        install_cmd = f"& '{ATK_PS1.as_posix()}' install -Target '{target_dir.as_posix()}' -Tool claude"
        res_inst = subprocess.run([PWSH_BIN, "-NoProfile", "-Command", install_cmd], capture_output=True, text=True, env=env)
        self.assertEqual(res_inst.returncode, 0)

        # 2. Check installs listing
        list_cmd = f"& '{ATK_PS1.as_posix()}' installs"
        res_list = subprocess.run([PWSH_BIN, "-NoProfile", "-Command", list_cmd], capture_output=True, text=True, env=env)
        self.assertEqual(res_list.returncode, 0)
        self.assertIn(str(target_dir.resolve()), res_list.stdout)

        # 3. Update all via atk.ps1 update -All
        update_cmd = f"& '{ATK_PS1.as_posix()}' update -All"
        res_upd = subprocess.run([PWSH_BIN, "-NoProfile", "-Command", update_cmd], capture_output=True, text=True, env=env)
        self.assertEqual(res_upd.returncode, 0)
        self.assertIn("Updated:", res_upd.stdout)
        self.assertIn(str(target_dir.resolve()), res_upd.stdout)


if __name__ == "__main__":
    unittest.main()
