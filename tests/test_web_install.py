#!/usr/bin/env python3
"""
Unit tests for direct web installation capabilities in install.sh and install.ps1.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = TOOLKIT_ROOT / "install.sh"
INSTALL_PS1 = TOOLKIT_ROOT / "install.ps1"
PWSH_BIN = shutil.which("pwsh") or shutil.which("powershell")


class TestWebInstall(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_web_test_")
        self.fake_home = Path(self.test_dir) / "home"
        self.fake_home.mkdir(parents=True, exist_ok=True)
        self.target = Path(self.test_dir) / "target_project"
        self.target.mkdir(parents=True, exist_ok=True)
        self.toolkit_install_dir = Path(self.test_dir) / "toolkit_inst"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_install_sh_help_contains_web_options(self):
        result = subprocess.run([str(INSTALL_SH), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("-w, --web", result.stdout)
        self.assertIn("--install-dir", result.stdout)
        self.assertIn("curl -fsSL https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.sh | bash", result.stdout)

    def test_install_sh_web_flag_with_local_repo(self):
        env = dict(
            os.environ,
            HOME=str(self.fake_home),
            AGENT_TOOLKIT_REPO=str(TOOLKIT_ROOT),
            AGENT_TOOLKIT_BRANCH="main",
        )
        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SH),
                "--web",
                "--install-dir",
                str(self.toolkit_install_dir),
                "--target",
                str(self.target),
                "--tool",
                "claude",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        self.assertTrue((self.toolkit_install_dir / "skills").exists())
        self.assertTrue((self.target / ".claude" / "commands" / "session-starter.md").exists())
        self.assertTrue((self.target / "CLAUDE.md").exists())

    def test_install_sh_piped_stdin_with_arguments(self):
        script_content = INSTALL_SH.read_text(encoding="utf-8")
        env = dict(
            os.environ,
            HOME=str(self.fake_home),
            AGENT_TOOLKIT_REPO=str(TOOLKIT_ROOT),
            AGENT_TOOLKIT_BRANCH="main",
        )
        result = subprocess.run(
            [
                "bash",
                "-s",
                "--",
                "--install-dir",
                str(self.toolkit_install_dir),
                "--target",
                str(self.target),
                "--tool",
                "cursor",
            ],
            input=script_content,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        self.assertTrue((self.toolkit_install_dir / "agents").exists())
        self.assertTrue((self.target / ".cursor" / "rules" / "session-workflows.mdc").exists())
        self.assertTrue((self.target / ".cursorrules").exists())

    def test_install_sh_piped_stdin_default_global(self):
        script_content = INSTALL_SH.read_text(encoding="utf-8")
        env = dict(
            os.environ,
            HOME=str(self.fake_home),
            AGENT_TOOLKIT_REPO=str(TOOLKIT_ROOT),
            AGENT_TOOLKIT_BRANCH="main",
        )
        result = subprocess.run(
            ["bash"],
            input=script_content,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        global_atk = self.fake_home / ".local" / "bin" / "atk"
        self.assertTrue(global_atk.exists())

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_help_contains_web_options(self):
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", str(INSTALL_PS1), "-Help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("-Web, -w, --web", result.stdout)
        self.assertIn("-InstallDir", result.stdout)
        self.assertIn("irm https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.ps1 | iex", result.stdout)

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_web_mode_in_memory_scriptblock(self):
        ps_content = INSTALL_PS1.read_text(encoding="utf-8")
        test_script = f"""
$sb = [scriptblock]::Create(@'
{ps_content}
'@)
& $sb -InstallDir '{self.toolkit_install_dir.as_posix()}' -Target '{self.target.as_posix()}' -Tool claude
"""
        env = dict(
            os.environ,
            HOME=str(self.fake_home),
            USERPROFILE=str(self.fake_home),
            AGENT_TOOLKIT_REPO=str(TOOLKIT_ROOT),
            AGENT_TOOLKIT_BRANCH="main",
        )
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", "-Command", test_script],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        self.assertTrue((self.toolkit_install_dir / "skills").exists())
        self.assertTrue((self.target / ".claude" / "commands" / "session-starter.md").exists())
        self.assertTrue((self.target / "CLAUDE.md").exists())

    @unittest.skipIf(PWSH_BIN is None, "PowerShell (pwsh or powershell) not installed")
    def test_install_ps1_web_mode_default_global(self):
        ps_content = INSTALL_PS1.read_text(encoding="utf-8")
        test_script = f"""
$sb = [scriptblock]::Create(@'
{ps_content}
'@)
& $sb -InstallDir '{self.toolkit_install_dir.as_posix()}'
"""
        env = dict(
            os.environ,
            HOME=str(self.fake_home),
            USERPROFILE=str(self.fake_home),
            AGENT_TOOLKIT_REPO=str(TOOLKIT_ROOT),
            AGENT_TOOLKIT_BRANCH="main",
        )
        result = subprocess.run(
            [PWSH_BIN, "-NoProfile", "-Command", test_script],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        global_atk_ps1 = self.fake_home / ".local" / "bin" / "atk.ps1"
        self.assertTrue(global_atk_ps1.exists())


if __name__ == "__main__":
    unittest.main()
