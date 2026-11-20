---
name: sys-admin
description: >-
  Cross-platform system administration, infrastructure hardening, and SRE incident
  triage skill. Runs live host health/inode/process checks, log condensation, host
  posture audits, transactional config apply with rollback, drift snapshots, and
  hardened template scaffolding.
---

# Universal System Administration & SRE Skill

This skill guides AI agents and operators through safe, deterministic **system administration, infrastructure security hardening, cross-platform ops automation (Linux/macOS/Windows), and Principal-level SRE incident triage**.

---

## 🏛️ Core System Administration & SRE Standards

1. **Read-Only Triage First (USE & RED Methods)**:
   - Always inspect utilization, saturation, errors (`--health --ports --processes`), condensed logs (`--triage-logs`), host permissions (`--audit-host`), and drift (`--diff-snapshot`) before modifying configurations or restarting services.

2. **Mechanical Blast-Radius Guardrails**:
   - Respect Tier 0 (`READ_ONLY`), Tier 1 (`STANDARD_MUTATION`), and Tier 2 (`HIGH_BLAST_RADIUS`) boundaries enforced by `guard_command.py`.
   - Use `--apply-safe SRC DEST --validate-cmd "..."` to preview unified diffs (`--dry-run`), capture SHA-256 receipts, snapshot backups, and **automatically roll back** if validation fails.

3. **Least Privilege & Hardened Defaults**:
   - Disable SSH root/password logins; enforce `0700`/`0600` on `~/.ssh`.
   - Sandbox `systemd` units (`User=`, `NoNewPrivileges=true`, `ProtectSystem=strict`, `PrivateTmp=true`).
   - Enforce TLS 1.2/1.3 and HSTS on Nginx/Caddy, non-privileged Kubernetes/Compose workloads with resource limits, default-deny firewalls, and strict `sudoers` rules (`Defaults use_pty`, no `NOPASSWD: ALL`).

4. **Idempotent, Fail-Fast Automation**:
   - Bash scripts must enable `set -euo pipefail`, quote variable expansions, guard removals with `${VAR:?}`, and avoid piping remote downloads to shells.
   - PowerShell scripts must set `$ErrorActionPreference = 'Stop'` and `Set-StrictMode -Version Latest`, and avoid `irm ... | iex` or hardcoded `-AsPlainText` secrets.

5. **Zero False Verification**:
   - Never claim a host is healthy, a config is hardened, or a service recovered without running verification commands and observing exit code `0`.

---

## 🔄 Execution Workflow

```
[1. USE/RED Triage & Logs] ──► [2. Audit Posture, Configs & Drift] ──► [3. Safe Apply w/ Validation & Auto-Rollback] ──► [4. Verify Recovery (Exit 0)]
```

---

## 🛠️ Automated SysAdmin & SRE Toolkit (`sys_admin.py`)

The bundled `sys_admin.py` + `sys_admin_sre.py` engine uses Python 3.10+ standard library only (zero external dependencies):

### Common Recipes

```bash
# 1. Deep host triage (CPU, load, RAM, disk, inodes, services, ports, top processes & FDs):
python3 skills/sys-admin/scripts/sys_admin.py --health --ports --processes --json
atk sysadmin --health --ports --processes

# 2. Token-efficient log triage & live host security posture audit:
atk sysadmin --triage-logs /var/log/nginx --max-lines 50000 --top-n 10
atk sysadmin --audit-host --check

# 3. Network, DNS, TCP port, TLS cert, batch endpoint manifest & read-only SSH triage:
atk sysadmin --check-tls example.com:443
atk sysadmin --check-port localhost:5432
atk sysadmin --check-dns example.com
atk sysadmin --check-endpoints endpoints.json --check
atk sysadmin --ssh ops@bastion.internal

# 4. Hybrid static + native config/script/IaC auditing with inline ignores & baselines:
atk sysadmin --audit . --native-lint --check
atk sysadmin --audit . --write-baseline .sysadmin-baseline.json
atk sysadmin --audit . --baseline .sysadmin-baseline.json --check

# 5. Transactional config apply with pre-reload validation & automatic rollback:
atk sysadmin --apply-safe ./nginx.conf /etc/nginx/conf.d/app.conf --validate-cmd "nginx -t" --dry-run
atk sysadmin --apply-safe ./nginx.conf /etc/nginx/conf.d/app.conf --validate-cmd "nginx -t"

# 6. Host drift snapshots (compare baseline vs live host or two snapshots):
atk sysadmin --snapshot host-baseline.json
atk sysadmin --diff-snapshot host-baseline.json --json

# 7. Scaffold hardened configs, backup scripts, runbooks & blameless postmortems:
atk sysadmin --list-templates
atk sysadmin --scaffold systemd --name api-server
atk sysadmin --scaffold runbook --name payments-api
atk sysadmin --scaffold postmortem --name auth-outage
```

---

## 🚨 Hardening & Hazard Detection Matrix

### Static Configuration, Script & IaC Rules (`--audit`)

| Rule ID | Severity | Domain | Anti-Pattern / Hazard | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `SYS-SSH-ROOT` | **CRITICAL** | SSH | `PermitRootLogin yes` | Set `PermitRootLogin no`. |
| `SYS-SSH-ROOT-PROHIBIT` | **WARNING** | SSH | Legacy `PermitRootLogin without-password` | Set `PermitRootLogin no` (or `prohibit-password`). |
| `SYS-SSH-PASS` | **HIGH** | SSH | `PasswordAuthentication yes` | Set `PasswordAuthentication no`; use SSH keys. |
| `SYS-SSH-EMPTY-PASS` | **CRITICAL** | SSH | `PermitEmptyPasswords yes` | Set `PermitEmptyPasswords no`. |
| `SYS-SSH-PROTO1` | **CRITICAL** | SSH | Legacy SSH `Protocol 1` | Enforce SSH Protocol 2 only. |
| `SYS-SSH-X11` | **WARNING** | SSH | `X11Forwarding yes` | Set `X11Forwarding no`. |
| `SYS-UNIT-ROOT` | **HIGH** | Systemd | `[Service]` omits non-root `User=` or sets `root`/`0` | Create dedicated service user and set `User=`. |
| `SYS-UNIT-NO-RESTART` | **WARNING** | Systemd | Non-oneshot service lacks `Restart=` | Add `Restart=on-failure` and `RestartSec=5s`. |
| `SYS-UNIT-SANDBOX` | **WARNING** | Systemd | Missing `NoNewPrivileges`, `ProtectSystem`, `PrivateTmp` | Enable systemd sandboxing directives. |
| `SYS-UNIT-UMASK` | **HIGH** | Systemd | Permissive `UMask=0000` / `0002` | Set `UMask=0027` or `UMask=0077`. |
| `SYS-NGINX-TLS-LEGACY` | **CRITICAL** | Nginx | `ssl_protocols` enables SSLv2/SSLv3/TLSv1/TLSv1.1 | Restrict to `ssl_protocols TLSv1.2 TLSv1.3;`. |
| `SYS-NGINX-TOKENS` | **WARNING** | Nginx | `server_tokens on` | Set `server_tokens off;`. |
| `SYS-NGINX-AUTOINDEX` | **HIGH** | Nginx | `autoindex on` | Set `autoindex off;`. |
| `SYS-NGINX-HSTS` | **WARNING** | Nginx | TLS `listen ... ssl` without HSTS header | Add `Strict-Transport-Security` header. |
| `SYS-CADDY-AUTO-HTTPS-OFF` | **HIGH** | Caddy | `auto_https off` | Keep automatic HTTPS enabled or configure TLS certs. |
| `SYS-CADDY-INSECURE-SKIP-VERIFY` | **CRITICAL** | Caddy | `tls_insecure_skip_verify` | Remove and configure trusted upstream CA certs. |
| `SYS-CADDY-HTTP-ONLY` | **WARNING** | Caddy | Plaintext `http://` non-local site block | Serve external hosts over HTTPS. |
| `SYS-CADDY-FILE-BROWSE` | **HIGH** | Caddy | `file_server browse` | Remove `browse` unless intentionally indexing files. |
| `SYS-K8S-PRIVILEGED` | **CRITICAL** | K8s / Compose | `privileged: true` | Set `privileged: false`; drop unneeded caps. |
| `SYS-K8S-HOST-NS` | **HIGH** | K8s / Compose | `hostNetwork`/`hostPID`/`hostIPC: true` or `network_mode: host` | Use isolated pod/bridge networking. |
| `SYS-K8S-DOCKER-SOCK` | **CRITICAL** | K8s / Compose | Mounts `/var/run/docker.sock` | Remove socket mount or use rootless BuildKit/Kaniko. |
| `SYS-K8S-RUN-AS-ROOT` | **HIGH** | Kubernetes | `runAsUser: 0` or `runAsNonRoot: false` | Enforce `runAsNonRoot: true` and non-zero UID. |
| `SYS-K8S-NO-LIMITS` | **WARNING** | Kubernetes | Workload omits `resources.limits` | Set CPU and memory `limits`. |
| `SYS-COMPOSE-PORT-WILDCARD` | **WARNING** | Compose | Sensitive DB/Docker port bound without `127.0.0.1:` | Bind to `127.0.0.1:<port>:<port>` or private network. |
| `SYS-SUDO-NOPASSWD-ALL` | **CRITICAL** | Sudoers | `NOPASSWD: ALL` | Restrict to explicit command paths with password auth. |
| `SYS-SUDO-WILDCARD-SHELL` | **HIGH** | Sudoers | `NOPASSWD:` grants shell-escape tool (`vim`, `python`, etc.) | Wrap specific operations in a dedicated script. |
| `SYS-SUDO-NO-USE-PTY` | **WARNING** | Sudoers | Primary `sudoers` omits `Defaults use_pty` | Add `Defaults use_pty` via `visudo`. |
| `SYS-FW-DEFAULT-ACCEPT` | **HIGH** | Firewall | Default `INPUT` policy is `ACCEPT` | Enforce default-deny `DROP` after allow rules. |
| `SYS-FW-OPEN-MGMT` | **CRITICAL** | Firewall | Admin/DB port (`22`, `3389`, `5432`, etc.) open to all | Scope ingress rules to trusted source CIDRs. |
| `SYS-SH-STRICT-MODE` | **WARNING** | Shell | Missing `set -e` / `set -euo pipefail` | Add `set -euo pipefail` near script header. |
| `SYS-SH-CURL-PIPE` | **CRITICAL** | Shell | `curl`/`wget` piped directly to shell | Download, verify SHA-256 checksum, then run. |
| `SYS-SH-PERM-WORLD` | **HIGH** | Shell | `chmod` assigns world-writable mode (`a+rwx` / mode 777) | Use `750`/`755` for scripts, `640`/`644` for configs. |
| `SYS-SH-DANGEROUS-RM` | **CRITICAL** | Shell | `rm -rf` on `/`, `~`, `$HOME`, or unguarded `$VAR/` | Guard with `${VAR:?}` before recursive deletion. |
| `SYS-SH-SUDO-PASS` | **CRITICAL** | Shell | Piping password via `echo ... \| sudo -S` | Use scoped `NOPASSWD` sudoers entries instead. |
| `SYS-PS-STRICT-MODE` | **WARNING** | PowerShell | Missing `$ErrorActionPreference` / `Set-StrictMode` | Set `$ErrorActionPreference = 'Stop'`. |
| `SYS-PS-IEX-WEB` | **CRITICAL** | PowerShell | `irm`/`iwr` piped directly to `iex`/`Invoke-Expression` | Download, verify hash/signature, then execute. |
| `SYS-PS-PLAINTEXT-CRED` | **HIGH** | PowerShell | Hardcoded literal in `ConvertTo-SecureString -AsPlainText` | Load secrets from vault/env or `Get-Credential`. |
| `SYS-CRON-CURL-PIPE` | **CRITICAL** | Cron | Cron pipes remote download to shell | Deploy versioned scripts in `/usr/local/sbin`. |
| `SYS-CRON-TMP-EXEC` | **HIGH** | Cron | Cron executes files from `/tmp/` or `/var/tmp/` | Move scripts to root-owned `/usr/local/sbin`. |
| `SYS-CRON-NO-PATH` | **WARNING** | Cron | Relative cron command without explicit `PATH=` | Define `PATH=` header or use absolute paths. |
| `SYS-SYSCTL-REDIRECT` | **WARNING** | Sysctl | `accept_redirects=1` or `accept_source_route=1` | Set both kernel flags to `0`. |
| `SYS-SYSCTL-KPTR` | **WARNING** | Sysctl | `kernel.kptr_restrict=0` or `randomize_va_space=0` | Set `kptr_restrict=1` (or `2`) and `randomize_va_space=2`. |
| `SYS-TF-OPEN-CIDR` | **CRITICAL** | Terraform | Sensitive port (`22`, `3389`, `5432`, etc.) open to `0.0.0.0/0` | Restrict ingress CIDRs to VPC/bastion/VPN ranges. |
| `SYS-TF-UNENCRYPTED` | **HIGH** | Terraform | `encrypted = false` or `publicly_accessible = true` | Enable encryption and restrict public access. |
| `SYS-ANSIBLE-NO-TLS` | **HIGH** | Ansible | `validate_certs: false` | Remove override or configure trusted CA bundle. |
| `SYS-ANSIBLE-IGNORE-ERR` | **WARNING** | Ansible | Blanket `ignore_errors: true` | Replace with targeted `failed_when:` assertions. |

*Suppress verified false positives inline with `# sysadmin-ignore: <RULE-ID>` (or `all`) or adopt incrementally via `--write-baseline` / `--baseline`.*

### Live Host Posture & Log Incident Rules (`--audit-host`, `--triage-logs`)

| Rule ID | Severity | Signal | Remediation |
| :--- | :--- | :--- | :--- |
| `HOST-SSH-DIR-PERM` | **HIGH** | `~/.ssh` accessible to group/others | Run `chmod 700 ~/.ssh`. |
| `HOST-SSH-KEY-PERM` | **CRITICAL** | `~/.ssh` private keys, `config`, or `authorized_keys` too open | Run `chmod 600` on sensitive SSH files. |
| `HOST-SHADOW-PERM` | **CRITICAL** | `/etc/shadow` world-readable | Run `chmod 640 /etc/shadow && chown root:shadow /etc/shadow`. |
| `HOST-REBOOT-REQUIRED` | **WARNING** | `/var/run/reboot-required` present | Schedule controlled reboot and verify recovery. |
| `HOST-PERMISSIVE-UMASK` | **WARNING** | Process umask permits world-writable files | Set `umask 027` or `umask 077`. |
| `LOG-OOM-KILL` | **CRITICAL** | Kernel OOM killer terminated process | Inspect memory leaks/limits (`MemoryMax`). |
| `LOG-DISK-IO` | **CRITICAL** | `ENOSPC` / `Read-only file system` / `I/O error` | Check `df -hT && df -i` and storage health. |
| `LOG-AUTH-SPIKE` | **HIGH** | `>= 10` SSH/auth failure lines | Confirm key-only SSH and firewall/fail2ban rules. |
| `LOG-HTTP-5XX` | **HIGH** | `>= 5` 5xx / `upstream timed out` / `Connection refused` | Triage backend processes and proxy timeouts. |
| `LOG-TLS-ERROR` | **HIGH** | Expired cert or TLS handshake failure in logs | Probe `--check-tls` and inspect cert chain. |
| `LOG-CRASH-LOOP` | **HIGH** | `Main process exited`, `segfault`, `panic:`, or restart loop | Inspect `journalctl -u <svc>` and roll back recent change. |

---

## 🌐 Cross-Platform Quick Triage Reference

| Check | Linux | macOS | Windows (PowerShell) |
| :--- | :--- | :--- | :--- |
| **Toolkit Summary** | `atk sysadmin --health --ports --processes` | `atk sysadmin --health --ports --processes` | `atk sysadmin --health --ports --processes` |
| **Services** | `systemctl --failed` / `journalctl -xeu <svc>` | `launchctl list` / `log show --last 15m` | `Get-Service` / `Get-EventLog` |
| **Disk & Inodes** | `df -hT` / `df -i` | `df -h` | `Get-PSDrive -PSProvider FileSystem` |
| **Listening Ports** | `ss -tulnp` | `lsof -iTCP -sTCP:LISTEN -nP` | `Get-NetTCPConnection -State Listen` |
| **DNS & TLS** | `atk sysadmin --check-dns <host>` | `atk sysadmin --check-tls <host>` | `Resolve-DnsName <host>` |
