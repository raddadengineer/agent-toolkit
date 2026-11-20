#!/usr/bin/env python3
"""
Unit tests for sys_admin.py — Universal System Administration, Hardening & SRE Triage Tool.
"""

from datetime import datetime, timedelta, timezone
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
SCRIPT_DIR = TOOLKIT_ROOT / "skills" / "sys-admin" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import sys_admin
import sys_admin_sre


class TestSysAdminAudits(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_sysadmin_test_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ssh_config_audit_hazards_and_pass(self):
        bad_ssh = self.root / "sshd_config"
        bad_ssh.write_text(
            "PermitRootLogin yes\n"
            "PasswordAuthentication yes\n"
            "PermitEmptyPasswords yes\n"
            "Protocol 1\n"
            "X11Forwarding yes\n",
            encoding="utf-8",
        )
        rep = sys_admin.audit_path(bad_ssh)
        ids = {f["id"] for f in rep["findings"]}
        self.assertEqual(rep["status"], "fail")
        self.assertTrue(
            {"SYS-SSH-ROOT", "SYS-SSH-PASS", "SYS-SSH-EMPTY-PASS", "SYS-SSH-PROTO1", "SYS-SSH-X11"}.issubset(ids)
        )

        prohibit_ssh = self.root / "legacy_sshd.conf"
        prohibit_ssh.write_text("PermitRootLogin without-password\n", encoding="utf-8")
        rep_warn = sys_admin.audit_path(prohibit_ssh)
        self.assertEqual(rep_warn["status"], "pass")
        self.assertEqual([f["id"] for f in rep_warn["findings"]], ["SYS-SSH-ROOT-PROHIBIT"])

        clean_ssh = self.root / "hardened_sshd.conf"
        clean_ssh.write_text(
            "# PermitRootLogin yes\n"
            "PermitRootLogin no\n"
            "PasswordAuthentication no\n"
            "PermitEmptyPasswords no\n"
            "X11Forwarding no\n",
            encoding="utf-8",
        )
        rep_clean = sys_admin.audit_path(clean_ssh)
        self.assertEqual(rep_clean["status"], "pass")
        self.assertEqual(rep_clean["total_findings"], 0)

    def test_systemd_unit_audit_and_oneshot_exemption(self):
        bad_unit = self.root / "api.service"
        bad_unit.write_text(
            "[Unit]\n"
            "Description=Unsafe API\n"
            "[Service]\n"
            "User=root\n"
            "UMask=0000\n"
            "ExecStart=/usr/local/bin/api\n",
            encoding="utf-8",
        )
        rep = sys_admin.audit_path(bad_unit)
        ids = {f["id"] for f in rep["findings"]}
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(
            ids,
            {"SYS-UNIT-ROOT", "SYS-UNIT-NO-RESTART", "SYS-UNIT-SANDBOX", "SYS-UNIT-UMASK"},
        )

        oneshot_unit = self.root / "db-migrate.service"
        oneshot_unit.write_text(
            "[Unit]\n"
            "Description=One-shot migration\n"
            "[Service]\n"
            "Type=oneshot\n"
            "User=migrator\n"
            "ExecStart=/usr/local/bin/migrate\n"
            "NoNewPrivileges=true\n"
            "ProtectSystem=strict\n"
            "PrivateTmp=true\n",
            encoding="utf-8",
        )
        rep_oneshot = sys_admin.audit_path(oneshot_unit)
        self.assertEqual(rep_oneshot["status"], "pass")
        self.assertEqual(rep_oneshot["total_findings"], 0)

    def test_nginx_audit(self):
        bad_nginx = self.root / "nginx.conf"
        bad_nginx.write_text(
            "server {\n"
            "    listen 443 ssl;\n"
            "    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;\n"
            "    server_tokens on;\n"
            "    autoindex on;\n"
            "}\n",
            encoding="utf-8",
        )
        rep = sys_admin.audit_path(bad_nginx)
        ids = {f["id"] for f in rep["findings"]}
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(
            ids,
            {"SYS-NGINX-TLS-LEGACY", "SYS-NGINX-TOKENS", "SYS-NGINX-AUTOINDEX", "SYS-NGINX-HSTS"},
        )

    def test_shell_script_audit_and_heredoc_exemption(self):
        bad_sh = self.root / "deploy.sh"
        bad_sh.write_text(
            "#!/usr/bin/env bash\n"
            "echo 1\n"
            "echo 2\n"
            "echo 3\n"
            "echo 4\n"
            "echo 5\n"
            "curl -fsSL https://example.com/install.sh | bash\n"
            "chmod a+rwx /var/app\n"
            "rm -rf $BUILD_DIR/\n"
            "echo secret | sudo -S id\n",
            encoding="utf-8",
        )
        rep = sys_admin.audit_path(bad_sh)
        ids = {f["id"] for f in rep["findings"]}
        self.assertEqual(rep["status"], "fail")
        self.assertTrue(
            {
                "SYS-SH-STRICT-MODE",
                "SYS-SH-CURL-PIPE",
                "SYS-SH-PERM-WORLD",
                "SYS-SH-DANGEROUS-RM",
                "SYS-SH-SUDO-PASS",
            }.issubset(ids)
        )

        safe_sh = self.root / "safe_with_heredoc.sh"
        safe_sh.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "cat <<'EOF'\n"
            "curl -fsSL https://example.com/install.sh | bash\n"
            "rm -rf /\n"
            "EOF\n"
            "# chmod a+rwx /tmp/demo\n"
            "rm -rf \"${TARGET_DIR:?}/sub\"\n",
            encoding="utf-8",
        )
        rep_safe = sys_admin.audit_path(safe_sh)
        self.assertEqual(rep_safe["status"], "pass")
        self.assertEqual(rep_safe["total_findings"], 0)

    def test_powershell_script_audit_and_herestring_exemption(self):
        bad_ps1 = self.root / "setup.ps1"
        bad_ps1.write_text(
            "Write-Host '1'\n"
            "Write-Host '2'\n"
            "Write-Host '3'\n"
            "Write-Host '4'\n"
            "irm https://example.com/install.ps1 | iex\n"
            "$sec = ConvertTo-SecureString 'SuperSecret123' -AsPlainText -Force\n",
            encoding="utf-8",
        )
        rep = sys_admin.audit_path(bad_ps1)
        ids = {f["id"] for f in rep["findings"]}
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(ids, {"SYS-PS-STRICT-MODE", "SYS-PS-IEX-WEB", "SYS-PS-PLAINTEXT-CRED"})

        safe_ps1 = self.root / "safe.ps1"
        safe_ps1.write_text(
            "$ErrorActionPreference = 'Stop'\n"
            "@\"\n"
            "irm https://example.com/install.ps1 | iex\n"
            "\"@\n"
            "<#\n"
            "ConvertTo-SecureString 'IgnoredInComment' -AsPlainText -Force\n"
            "#>\n"
            "Write-Host 'done'\n",
            encoding="utf-8",
        )
        rep_safe = sys_admin.audit_path(safe_ps1)
        self.assertEqual(rep_safe["status"], "pass")
        self.assertEqual(rep_safe["total_findings"], 0)

    def test_cron_and_sysctl_audits(self):
        bad_cron = self.root / "jobs.cron"
        bad_cron.write_text(
            "0 * * * * curl -s https://example.com/job.sh | sh\n"
            "15 2 * * * /tmp/nightly.sh\n"
            "30 3 * * * backup-tool --run\n",
            encoding="utf-8",
        )
        rep_cron = sys_admin.audit_path(bad_cron)
        self.assertEqual(rep_cron["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_cron["findings"]},
            {"SYS-CRON-CURL-PIPE", "SYS-CRON-TMP-EXEC", "SYS-CRON-NO-PATH"},
        )

        bad_sysctl = self.root / "99-custom-sysctl.conf"
        bad_sysctl.write_text(
            "net.ipv4.conf.all.accept_redirects = 1\n"
            "kernel.kptr_restrict = 0\n",
            encoding="utf-8",
        )
        rep_sysctl = sys_admin.audit_path(bad_sysctl)
        self.assertEqual(rep_sysctl["status"], "pass")
        self.assertEqual(
            {f["id"] for f in rep_sysctl["findings"]},
            {"SYS-SYSCTL-REDIRECT", "SYS-SYSCTL-KPTR"},
        )

    def test_terraform_and_ansible_audits(self):
        bad_tf = self.root / "main.tf"
        bad_tf.write_text(
            'resource "aws_security_group" "web_and_ssh" {\n'
            "  ingress {\n"
            "    from_port = 443\n"
            "    to_port = 443\n"
            '    protocol = "tcp"\n'
            '    cidr_blocks = ["0.0.0.0/0"]\n'
            "  }\n"
            "  ingress {\n"
            "    from_port = 22\n"
            "    to_port = 22\n"
            '    protocol = "tcp"\n'
            '    cidr_blocks = ["0.0.0.0/0"]\n'
            "  }\n"
            "}\n"
            'resource "aws_db_instance" "db" {\n'
            "  storage_encrypted = false\n"
            "  publicly_accessible = true\n"
            "}\n",
            encoding="utf-8",
        )
        rep_tf = sys_admin.audit_path(bad_tf)
        self.assertEqual(rep_tf["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_tf["findings"]},
            {"SYS-TF-OPEN-CIDR", "SYS-TF-UNENCRYPTED"},
        )
        self.assertEqual(sum(1 for f in rep_tf["findings"] if f["id"] == "SYS-TF-OPEN-CIDR"), 1)

        bad_ansible = self.root / "site-playbook.yml"
        bad_ansible.write_text(
            "- hosts: all\n"
            "  tasks:\n"
            "    - name: Fetch release\n"
            "      ansible.builtin.get_url:\n"
            "        url: https://example.com/app.tar.gz\n"
            "        dest: /opt/app.tar.gz\n"
            "        validate_certs: false\n"
            "      ignore_errors: true\n",
            encoding="utf-8",
        )
        rep_ans = sys_admin.audit_path(bad_ansible)
        self.assertEqual(rep_ans["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_ans["findings"]},
            {"SYS-ANSIBLE-NO-TLS", "SYS-ANSIBLE-IGNORE-ERR"},
        )

    def test_caddy_k8s_compose_sudoers_and_firewall_audits(self):
        caddy = self.root / "Caddyfile"
        caddy.write_text(
            "http://app.example.com {\n"
            "  auto_https off\n"
            "  file_server browse\n"
            "  reverse_proxy https://backend:8443 {\n"
            "    transport http {\n"
            "      tls_insecure_skip_verify\n"
            "    }\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        rep_caddy = sys_admin.audit_path(caddy)
        self.assertEqual(rep_caddy["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_caddy["findings"]},
            {
                "SYS-CADDY-HTTP-ONLY",
                "SYS-CADDY-AUTO-HTTPS-OFF",
                "SYS-CADDY-FILE-BROWSE",
                "SYS-CADDY-INSECURE-SKIP-VERIFY",
            },
        )

        k8s = self.root / "deployment.yaml"
        k8s.write_text(
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "spec:\n"
            "  template:\n"
            "    spec:\n"
            "      hostNetwork: true\n"
            "      containers:\n"
            "        - name: app\n"
            "          securityContext:\n"
            "            privileged: true\n"
            "            runAsUser: 0\n"
            "          volumeMounts:\n"
            "            - mountPath: /var/run/docker.sock\n",
            encoding="utf-8",
        )
        rep_k8s = sys_admin.audit_path(k8s)
        self.assertEqual(rep_k8s["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_k8s["findings"]},
            {
                "SYS-K8S-HOST-NS",
                "SYS-K8S-PRIVILEGED",
                "SYS-K8S-RUN-AS-ROOT",
                "SYS-K8S-DOCKER-SOCK",
                "SYS-K8S-NO-LIMITS",
            },
        )

        # Confirm GitHub Actions workflow is NOT misclassified as K8s
        gh_wf = self.root / "ci.yml"
        gh_wf.write_text("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8")
        self.assertEqual(sys_admin.audit_path(gh_wf)["files_audited"], 0)

        compose = self.root / "docker-compose.yml"
        compose.write_text(
            "services:\n"
            "  db:\n"
            "    image: postgres:16.2\n"
            "    network_mode: host\n"
            "    ports:\n"
            '      - "5432:5432"\n'
            '      - "127.0.0.1:6379:6379"\n',
            encoding="utf-8",
        )
        rep_comp = sys_admin.audit_path(compose)
        self.assertEqual(rep_comp["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_comp["findings"]},
            {"SYS-K8S-HOST-NS", "SYS-COMPOSE-PORT-WILDCARD"},
        )

        sudoers = self.root / "sudoers"
        sudoers.write_text(
            "deploy ALL=(ALL) NOPASSWD: ALL\n"
            "ops ALL=(ALL) NOPASSWD: /usr/bin/vim\n",
            encoding="utf-8",
        )
        rep_sudo = sys_admin.audit_path(sudoers)
        self.assertEqual(rep_sudo["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_sudo["findings"]},
            {"SYS-SUDO-NOPASSWD-ALL", "SYS-SUDO-WILDCARD-SHELL", "SYS-SUDO-NO-USE-PTY"},
        )

        fw = self.root / "iptables.rules"
        fw.write_text(
            "*filter\n"
            ":INPUT ACCEPT [0:0]\n"
            "-A INPUT -p tcp --dport 22 -j ACCEPT\n"
            "-A INPUT -s 10.0.0.0/8 -p tcp --dport 5432 -j ACCEPT\n",
            encoding="utf-8",
        )
        rep_fw = sys_admin.audit_path(fw)
        self.assertEqual(rep_fw["status"], "fail")
        self.assertEqual(
            {f["id"] for f in rep_fw["findings"]},
            {"SYS-FW-DEFAULT-ACCEPT", "SYS-FW-OPEN-MGMT"},
        )
        self.assertEqual(sum(1 for f in rep_fw["findings"] if f["id"] == "SYS-FW-OPEN-MGMT"), 1)

    def test_inline_suppressions_and_baseline_diffing(self):
        ssh_cfg = self.root / "team_sshd.conf"
        ssh_cfg.write_text(
            "# sysadmin-ignore: SYS-SSH-X11\n"
            "X11Forwarding yes\n"
            "PermitRootLogin no\n"
            "PasswordAuthentication yes # sysadmin-ignore: all\n",
            encoding="utf-8",
        )
        rep = sys_admin.audit_path(ssh_cfg)
        self.assertEqual(rep["status"], "pass")
        self.assertEqual(rep["total_findings"], 0)
        self.assertEqual(rep["suppressed_count"], 2)

        # Baseline write & diff
        leaky = self.root / "leaky_sshd.conf"
        leaky.write_text("PermitRootLogin yes\n", encoding="utf-8")
        bl_path = self.root / "baseline.json"
        first = sys_admin.audit_path(leaky, write_baseline_path=bl_path)
        self.assertEqual(first["status"], "fail")
        self.assertTrue(bl_path.exists())

        gated = sys_admin.audit_path(leaky, baseline_path=bl_path)
        self.assertEqual(gated["status"], "pass")
        self.assertEqual(gated["total_findings"], 0)
        self.assertEqual(gated["baselined_count"], 1)


class TestSysAdminScaffoldAndRuntime(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_sysadmin_rt_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_templates_scaffold_and_pass_audit(self):
        auditable = {"systemd", "nginx", "backup", "backup-ps1", "cron", "sshd"}
        for tmpl_name in sys_admin.TEMPLATES:
            res = sys_admin.scaffold_template(tmpl_name, service_name="Billing API", target_dir=self.root)
            out_path = Path(res["output"])
            self.assertTrue(out_path.exists(), f"Missing scaffold output for {tmpl_name}")
            if res["executable"] and os.name != "nt":
                self.assertTrue(os.access(out_path, os.X_OK), f"{tmpl_name} should be executable")
            if tmpl_name in auditable:
                audit_rep = sys_admin.audit_path(out_path)
                self.assertEqual(
                    audit_rep["total_findings"],
                    0,
                    f"Template {tmpl_name} produced audit findings: {audit_rep['findings']}",
                )

    def test_scaffold_overwrite_protection_and_name_sanitization(self):
        self.assertEqual(sys_admin.sanitize_name("../../etc/passwd"), "etc-passwd")
        self.assertEqual(sys_admin.sanitize_name("   "), "app")

        first = sys_admin.scaffold_template("sshd", service_name="bastion", target_dir=self.root)
        with self.assertRaises(FileExistsError):
            sys_admin.scaffold_template("sshd", service_name="bastion", target_dir=self.root, force=False)

        forced = sys_admin.scaffold_template("sshd", service_name="bastion", target_dir=self.root, force=True)
        self.assertEqual(first["output"], forced["output"])

    def test_memory_parsers_and_thresholds(self):
        meminfo = (
            "MemTotal:       16777216 kB\n"
            "MemFree:         2097152 kB\n"
            "MemAvailable:    8388608 kB\n"
        )
        linux_mem = sys_admin.parse_proc_meminfo(meminfo)
        self.assertIsNotNone(linux_mem)
        self.assertEqual(linux_mem["total_gb"], 16.0)
        self.assertEqual(linux_mem["available_gb"], 8.0)
        self.assertEqual(linux_mem["percent_used"], 50.0)

        vm_stat_sample = (
            "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
            "Pages free:                              100000.\n"
            "Pages active:                            262144.\n"
            "Pages wired down:                        131072.\n"
            "Pages occupied by compressor:            131072.\n"
        )
        # 524288 pages * 16384 bytes = 8 GiB out of 16 GiB total -> 50%
        total_bytes = 16 * (1024 ** 3)
        mac_mem = sys_admin.parse_macos_vm_stat(vm_stat_sample, total_bytes)
        self.assertIsNotNone(mac_mem)
        self.assertEqual(mac_mem["total_gb"], 16.0)
        self.assertEqual(mac_mem["used_gb"], 8.0)
        self.assertEqual(mac_mem["percent_used"], 50.0)

        self.assertEqual(sys_admin.evaluate_threshold_status(50.0, 80.0, 90.0), "ok")
        self.assertEqual(sys_admin.evaluate_threshold_status(85.0, 80.0, 90.0), "warning")
        self.assertEqual(sys_admin.evaluate_threshold_status(95.0, 80.0, 90.0), "critical")

    def test_host_health_schema_and_json(self):
        health = sys_admin.collect_host_health(target_path=str(self.root))
        self.assertIn(health["status"], {"pass", "warn", "fail"})
        self.assertIn("disk", health)
        self.assertIn("memory", health)
        self.assertIn("cpu_count", health)
        serialized = json.dumps(health)
        self.assertIn("timestamp_utc", serialized)

    def test_host_port_parser_tls_expiry_and_loopback_tcp(self):
        self.assertEqual(sys_admin.parse_host_port("example.com"), ("example.com", 443))
        self.assertEqual(sys_admin.parse_host_port("db.internal:5432"), ("db.internal", 5432))
        self.assertEqual(sys_admin.parse_host_port("[::1]:8443"), ("::1", 8443))
        with self.assertRaises(ValueError):
            sys_admin.parse_host_port("example.com:99999")

        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(sys_admin.evaluate_tls_expiry(now + timedelta(days=45), now=now)["status"], "pass")
        self.assertEqual(sys_admin.evaluate_tls_expiry(now + timedelta(days=15), now=now)["status"], "warn")
        self.assertEqual(sys_admin.evaluate_tls_expiry(now + timedelta(days=3), now=now)["status"], "fail")
        expired = sys_admin.evaluate_tls_expiry(now - timedelta(days=1), now=now)
        self.assertEqual(expired["status"], "fail")
        self.assertTrue(expired["expired"])

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port = srv.getsockname()[1]
            open_rep = sys_admin.check_tcp_port(f"127.0.0.1:{port}", timeout=2.0)
            self.assertEqual(open_rep["status"], "pass")
            self.assertTrue(open_rep["reachable"])

        closed_rep = sys_admin.check_tcp_port(f"127.0.0.1:{port}", timeout=1.0)
        self.assertEqual(closed_rep["status"], "fail")
        self.assertFalse(closed_rep["reachable"])

    def test_cli_subprocess_audit_and_health(self):
        script_path = SCRIPT_DIR / "sys_admin.py"

        bad_file = self.root / "bad_sshd.conf"
        bad_file.write_text("PermitRootLogin yes\n", encoding="utf-8")
        res_fail = subprocess.run(
            [sys.executable, str(script_path), "--audit", str(bad_file), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_fail.returncode, 1)
        data_fail = json.loads(res_fail.stdout)
        self.assertEqual(data_fail["status"], "fail")

        clean_file = self.root / "good_sshd.conf"
        clean_file.write_text("PermitRootLogin no\nPasswordAuthentication no\n", encoding="utf-8")
        res_pass = subprocess.run(
            [sys.executable, str(script_path), "--audit", str(clean_file), "--check", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_pass.returncode, 0)
        data_pass = json.loads(res_pass.stdout)
        self.assertEqual(data_pass["status"], "pass")

        res_health = subprocess.run(
            [sys.executable, str(script_path), "--health", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_health.returncode, 0)
        health_data = json.loads(res_health.stdout)
        self.assertIn("disk", health_data)
        self.assertIn("inodes", health_data["disk"])

    def test_v2_parsers_ssh_validation_and_native_lint(self):
        launchctl_sample = (
            "PID\tStatus\tLabel\n"
            "123\t0\tcom.apple.Finder\n"
            "-\t0\tcom.apple.clean\n"
            "-\t78\tcom.example.worker\n"
            "-\t2\tcom.apple.ignored\n"
        )
        self.assertEqual(sys_admin.parse_launchctl_list(launchctl_sample), ["com.example.worker"])

        win_json = '[{"Name": "Spooler"}, {"Name": "wuauserv"}]'
        self.assertEqual(sys_admin.parse_windows_stopped_services(win_json), ["Spooler", "wuauserv"])

        ps_sample = (
            "  PID  %CPU %MEM STAT COMMAND\n"
            "  101  82.5  12.1 R   python3\n"
            "  102   0.0   0.1 Z   defunct-worker\n"
            "  103   4.0  45.0 S   postgres\n"
        )
        parsed_ps = sys_admin.parse_ps_output(ps_sample)
        self.assertEqual(parsed_ps["total_processes"], 3)
        self.assertEqual(parsed_ps["zombie_count"], 1)
        self.assertEqual(parsed_ps["top_cpu"][0]["pid"], 101)
        self.assertEqual(parsed_ps["top_memory"][0]["pid"], 103)

        file_nr = sys_admin.parse_proc_file_nr("4096\t0\t100000\n")
        self.assertEqual(file_nr, {"allocated": 4096, "max": 100000, "percent_used": 4.1})

        self.assertEqual(sys_admin_sre.validate_ssh_target("ops@bastion.internal"), "ops@bastion.internal")
        for bad_target in ("-oProxyCommand=id", "user@host;rm -rf /", "user host", ""):
            with self.assertRaises(ValueError):
                sys_admin_sre.validate_ssh_target(bad_target)

        # Native validator check on valid vs syntactically broken shell script
        broken_sh = self.root / "broken.sh"
        broken_sh.write_text("#!/usr/bin/env bash\nif [ -f foo ]; then\n  echo hi\n", encoding="utf-8")
        native_rep = sys_admin_sre.run_native_validators(broken_sh)
        if shutil.which("shellcheck") or shutil.which("bash"):
            self.assertTrue(len(native_rep["findings"]) >= 1)


if __name__ == "__main__":
    unittest.main()
