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

    def test_guard_blocks_sysadmin_lockouts(self):
        blocked = [
            "iptables -F",
            "iptables -P INPUT DROP",
            "ufw reset",
            "nft flush ruleset",
            "systemctl stop sshd",
            "chmod -R 755 /etc",
            "chown -R root:root /",
            "reboot",
            "crontab -r",
            "usermod -G docker bob",
            'echo "x" > /etc/sudoers',
        ]
        for cmd in blocked:
            res = guard_command.evaluate_command(cmd)
            self.assertEqual(res["decision"], "deny", f"Expected deny for: {cmd}")

    def test_guard_allows_safe_sysadmin_commands(self):
        allowed = [
            "iptables -L -n",
            "ufw status",
            "systemctl status sshd",
            "chmod -R 755 ./build",
            "cat /var/run/reboot-required",
            "crontab -l",
            "usermod -aG docker bob",
            "visudo -c",
        ]
        for cmd in allowed:
            res = guard_command.evaluate_command(cmd)
            self.assertEqual(res["decision"], "allow", f"Expected allow for: {cmd}")

    def test_classify_command_tier(self):
        t0 = guard_command.classify_command_tier("df -h && systemctl status nginx")
        self.assertEqual(t0["tier"], 0)
        self.assertEqual(t0["label"], "READ_ONLY")

        t0_tool = guard_command.classify_command_tier("python3 scripts/sys_admin.py --health --json")
        self.assertEqual(t0_tool["tier"], 0)

        t1 = guard_command.classify_command_tier("chmod 600 ~/.ssh/config")
        self.assertEqual(t1["tier"], 1)
        self.assertEqual(t1["label"], "STANDARD_MUTATION")

        t2 = guard_command.classify_command_tier("systemctl stop sshd")
        self.assertEqual(t2["tier"], 2)
        self.assertEqual(t2["label"], "HIGH_BLAST_RADIUS")
        self.assertEqual(t2["decision"], "deny")

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
