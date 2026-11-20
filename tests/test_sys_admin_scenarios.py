#!/usr/bin/env python3
"""
End-to-end SRE incident simulation benchmarks for sys_admin + sys_admin_sre + guard_command.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = TOOLKIT_ROOT / "scripts"
SYSADMIN_SCRIPT = TOOLKIT_ROOT / "skills" / "sys-admin" / "scripts" / "sys_admin.py"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SYSADMIN_SCRIPT.parent))

import guard_command
import sys_admin
import sys_admin_sre


class TestSysAdminSreScenarios(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_sre_bench_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scenario_1_lockout_and_blast_radius_restraint(self):
        tier0_cmds = [
            "df -h && ss -tuln",
            "python3 scripts/sys_admin.py --health --ports --processes --json",
            "visudo -c && nginx -t",
        ]
        for cmd in tier0_cmds:
            res = guard_command.classify_command_tier(cmd)
            self.assertEqual(res["tier"], 0, cmd)
            self.assertEqual(res["decision"], "allow", cmd)

        tier1_cmds = [
            "python3 scripts/sys_admin.py --apply-safe ./nginx.conf /etc/nginx/nginx.conf --validate-cmd 'nginx -t'",
            "chmod 600 ~/.ssh/config",
        ]
        for cmd in tier1_cmds:
            res = guard_command.classify_command_tier(cmd)
            self.assertEqual(res["tier"], 1, cmd)
            self.assertEqual(res["decision"], "allow", cmd)

        tier2_cmds = [
            "iptables -F && iptables -P INPUT DROP",
            "systemctl stop sshd",
            "usermod -G docker deploy",
            "crontab -r",
        ]
        for cmd in tier2_cmds:
            res = guard_command.classify_command_tier(cmd)
            self.assertEqual(res["tier"], 2, cmd)
            self.assertEqual(res["decision"], "deny", cmd)

    def test_scenario_2_oom_5xx_auth_log_storm_triage(self):
        log_file = self.root / "production.log"
        lines = ["2026-11-19T12:00:00Z INFO healthy heartbeat"] * 100
        lines.append("2026-11-19T12:01:02Z kernel: Out of memory: Killed process 4412 (python3)")
        lines.extend(
            f"2026-11-19T12:01:{10+i:02d}Z sshd[900]: Failed password for invalid user admin from 203.0.113.{i+1} port 5521{i}"
            for i in range(12)
        )
        lines.extend(
            f"2026-11-19T12:02:{10+i:02d}Z nginx: 502 Bad Gateway upstream timed out connecting to 10.0.0.5:8080 req-id=abc-{i}"
            for i in range(7)
        )
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        report = sys_admin_sre.triage_logs(log_file, max_lines=5000, top_n=5)
        self.assertEqual(report["status"], "fail")
        alert_ids = {a["id"] for a in report["alerts"]}
        self.assertTrue({"LOG-OOM-KILL", "LOG-AUTH-SPIKE", "LOG-HTTP-5XX"}.issubset(alert_ids))
        self.assertLessEqual(len(report["top_clusters"]), 5)
        self.assertGreaterEqual(report["top_clusters"][0]["count"], 7)

        cli = subprocess.run(
            [sys.executable, str(SYSADMIN_SCRIPT), "--triage-logs", str(log_file), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(cli.returncode, 1)
        self.assertEqual(json.loads(cli.stdout)["status"], "fail")

    def test_scenario_3_transactional_config_apply_and_auto_rollback(self):
        dest = self.root / "service.conf"
        dest.write_text("listen 8080;\nserver_tokens off;\n", encoding="utf-8")

        bad_src = self.root / "bad_candidate.conf"
        bad_src.write_text("INVALID_DIRECTIVE_SYNTAX_ERROR\n", encoding="utf-8")

        # Dry-run must not mutate dest
        dry = sys_admin_sre.apply_config_safe(bad_src, dest, dry_run=True)
        self.assertTrue(dry["dry_run"])
        self.assertIn("INVALID_DIRECTIVE_SYNTAX_ERROR", dry["diff"])
        self.assertIn("listen 8080;", dest.read_text(encoding="utf-8"))

        # Validation checks that 'INVALID' is absent; fails and rolls back automatically
        val_script = self.root / "validate.py"
        val_script.write_text(
            "import sys\nfrom pathlib import Path\n"
            "txt = Path(sys.argv[1]).read_text()\n"
            "sys.exit(1 if 'INVALID' in txt else 0)\n",
            encoding="utf-8",
        )
        failed = sys_admin_sre.apply_config_safe(
            bad_src,
            dest,
            validate_cmd=[sys.executable, str(val_script), str(dest)],
            backup_dir=self.root / "backups",
        )
        self.assertEqual(failed["status"], "fail")
        self.assertTrue(failed["rolled_back"])
        self.assertEqual(dest.read_text(encoding="utf-8"), "listen 8080;\nserver_tokens off;\n")
        self.assertTrue(Path(failed["backup_path"]).exists())

        # Valid candidate passes via CLI
        good_src = self.root / "good_candidate.conf"
        good_src.write_text("listen 8443 ssl;\nserver_tokens off;\n", encoding="utf-8")
        cli = subprocess.run(
            [
                sys.executable,
                str(SYSADMIN_SCRIPT),
                "--apply-safe",
                str(good_src),
                str(dest),
                "--validate-cmd",
                f"{sys.executable} {val_script} {dest}",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(cli.returncode, 0)
        cli_data = json.loads(cli.stdout)
        self.assertEqual(cli_data["status"], "pass")
        self.assertFalse(cli_data["rolled_back"])
        self.assertIn("listen 8443 ssl;", dest.read_text(encoding="utf-8"))

    def test_scenario_4_host_posture_drift_snapshot_diff(self):
        base_health = {
            "timestamp_utc": "2026-11-19T10:00:00Z",
            "hostname": "prod-web-01",
            "os": "Linux",
            "release": "6.8.0",
            "cpu_count": 4,
            "disk": {"percent_used": 60.0, "inodes": {"available": True, "percent_used": 10.0}},
            "memory": {"available": True, "percent_used": 40.0},
            "services": {"failed_units": []},
            "listening_ports": {"entries": ["tcp LISTEN 0 128 0.0.0.0:443"]},
        }
        curr_health = {
            "timestamp_utc": "2026-11-19T11:00:00Z",
            "hostname": "prod-web-01",
            "os": "Linux",
            "release": "6.8.0",
            "cpu_count": 4,
            "disk": {"percent_used": 92.0, "inodes": {"available": True, "percent_used": 12.0}},
            "memory": {"available": True, "percent_used": 65.0},
            "services": {"failed_units": ["nginx.service"]},
            "listening_ports": {
                "entries": [
                    "tcp LISTEN 0 128 0.0.0.0:443",
                    "tcp LISTEN 0 128 0.0.0.0:9090",
                ]
            },
        }
        base_snap = sys_admin_sre.capture_host_snapshot(base_health, {"findings": []})
        curr_snap = sys_admin_sre.capture_host_snapshot(curr_health, {"findings": [{"id": "HOST-SSH-KEY-PERM"}]})
        diff = sys_admin_sre.diff_host_snapshots(base_snap, curr_snap)

        self.assertEqual(diff["status"], "fail")
        self.assertEqual(diff["added_ports"], ["tcp LISTEN 0 128 0.0.0.0:9090"])
        self.assertEqual(diff["newly_failed_services"], ["nginx.service"])
        self.assertEqual(diff["new_posture_findings"], ["HOST-SSH-KEY-PERM"])
        self.assertEqual(diff["disk_delta_pct"], 32.0)

        base_file = self.root / "base.json"
        curr_file = self.root / "curr.json"
        base_file.write_text(json.dumps(base_snap), encoding="utf-8")
        curr_file.write_text(json.dumps(curr_snap), encoding="utf-8")
        cli = subprocess.run(
            [sys.executable, str(SYSADMIN_SCRIPT), "--diff-snapshot", str(base_file), str(curr_file), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(cli.returncode, 1)

    @unittest.skipIf(os.name == "nt", "POSIX file mode bits are not applicable on Windows")
    def test_scenario_5_host_ssh_posture_remediation(self):
        ssh_dir = self.root / ".ssh"
        ssh_dir.mkdir()
        key_file = ssh_dir / "id_ed25519"
        key_file.write_text("dummy-private-material\n", encoding="utf-8")
        os.chmod(ssh_dir, 0o755)
        os.chmod(key_file, 0o644)

        bad_rep = sys_admin_sre.audit_host_posture(home_dir=self.root, ssh_dir=ssh_dir, check_system_files=False)
        self.assertEqual(bad_rep["status"], "fail")
        self.assertEqual({f["id"] for f in bad_rep["findings"]}, {"HOST-SSH-DIR-PERM", "HOST-SSH-KEY-PERM"})

        os.chmod(ssh_dir, 0o700)
        os.chmod(key_file, 0o600)
        fixed_rep = sys_admin_sre.audit_host_posture(home_dir=self.root, ssh_dir=ssh_dir, check_system_files=False)
        self.assertEqual(fixed_rep["status"], "pass")
        self.assertEqual(fixed_rep["critical_count"], 0)
        self.assertEqual(fixed_rep["high_count"], 0)

    def test_scenario_6_multi_surface_audit_baseline_and_suppression(self):
        infra_dir = self.root / "infra"
        infra_dir.mkdir()
        (infra_dir / "Caddyfile").write_text("http://legacy.example.com {\n  auto_https off\n}\n", encoding="utf-8")
        (infra_dir / "deploy.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  template:\n    spec:\n      containers:\n        - name: web\n          securityContext:\n            # sysadmin-ignore: SYS-K8S-PRIVILEGED\n            privileged: true\n",
            encoding="utf-8",
        )

        baseline_file = self.root / "baseline.json"
        write_res = subprocess.run(
            [
                sys.executable,
                str(SYSADMIN_SCRIPT),
                "--audit",
                str(infra_dir),
                "--write-baseline",
                str(baseline_file),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        write_data = json.loads(write_res.stdout)
        self.assertEqual(write_data["suppressed_count"], 1)
        self.assertGreaterEqual(write_data["total_findings"], 2)

        gated = subprocess.run(
            [
                sys.executable,
                str(SYSADMIN_SCRIPT),
                "--audit",
                str(infra_dir),
                "--baseline",
                str(baseline_file),
                "--check",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(gated.returncode, 0)
        gated_data = json.loads(gated.stdout)
        self.assertEqual(gated_data["total_findings"], 0)
        self.assertGreaterEqual(gated_data["baselined_count"], 2)

    def test_scenario_7_batch_endpoints_manifest_probe(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            open_port = srv.getsockname()[1]

            manifest_ok = self.root / "endpoints_ok.json"
            manifest_ok.write_text(
                json.dumps({"endpoints": [{"name": "local-api", "port": f"127.0.0.1:{open_port}"}]}),
                encoding="utf-8",
            )
            ok_res = subprocess.run(
                [sys.executable, str(SYSADMIN_SCRIPT), "--check-endpoints", str(manifest_ok), "--check", "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(ok_res.returncode, 0)
            self.assertEqual(json.loads(ok_res.stdout)["passed"], 1)

        # Now port is closed -> must fail with --check
        fail_res = subprocess.run(
            [sys.executable, str(SYSADMIN_SCRIPT), "--check-endpoints", str(manifest_ok), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(fail_res.returncode, 1)
        self.assertEqual(json.loads(fail_res.stdout)["failed"], 1)


if __name__ == "__main__":
    unittest.main()
