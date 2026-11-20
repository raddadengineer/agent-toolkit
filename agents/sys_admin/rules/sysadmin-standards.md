# Universal System Administration & Principal SRE Standards

These standards enforce mechanical blast-radius safety, systematic USE/RED diagnostics, least-privilege infrastructure hardening, transactional configuration changes, and disciplined SRE incident response across Linux, macOS, and Windows.

---

## 1. Risk Tiers, Triage First & Transactional Change Safety
- **Respect mechanical blast-radius guardrails**: Never invoke Tier 2 lockout/outage commands (flushing firewall chains, stopping `sshd`/networking, recursive `chmod`/`chown` on root OS paths, `crontab -r`, `usermod -G` without `-a`, or writing `/etc/sudoers` outside `visudo`).
- **Triage via USE & RED before mutation**: Inspect CPU, memory, disk, **inodes**, file descriptors, failed services (`systemd`/`launchd`/Windows SCM), listening sockets, and condensed logs (`--triage-logs`) before changing config or restarting services.
- **Transactional apply with rollback**: Preview changes with `--apply-safe ... --dry-run`, validate syntax (`sshd -t`, `nginx -t`, `caddy validate`, `systemd-analyze verify`, `visudo -c`), and rely on automatic backup rollback on non-zero validation exit.
- **Track drift & memory**: Capture known-good host posture snapshots (`--snapshot` / `--diff-snapshot`) and recall/record host topology facts in `memory/`.

---

## 2. Server, Daemon, Host Posture & Network Hardening
- **SSH & host posture**: Enforce `PermitRootLogin no`, `PasswordAuthentication no`, `PermitEmptyPasswords no`, SSH Protocol 2, and `X11Forwarding no`; keep `~/.ssh` at `0700` and private keys/`config`/`authorized_keys` at `0600` (`--audit-host`).
- **Systemd service sandboxing**: Bind services to dedicated non-root `User=`/`Group=`, configure `Restart=on-failure`, restrict `UMask=0027`, and enable `NoNewPrivileges=true`, `ProtectSystem=strict`, and `PrivateTmp=true`.
- **Sudoers & firewalls**: Ban `NOPASSWD: ALL` and passwordless GTFOBins/interpreters, require `Defaults use_pty`, enforce default-deny firewall `INPUT` policies, and block unrestricted `0.0.0.0/0` access to sensitive admin/DB ports (`22`, `3389`, `5432`, `3306`, `6379`, `27017`).
- **Kernel hygiene**: Disable ICMP redirects and IP source routing in `sysctl`, and keep `kernel.kptr_restrict` and ASLR enabled.

---

## 3. Reverse Proxy, TLS, Containers & IaC Security
- **Nginx & Caddy**: Disable `server_tokens` and `autoindex` / `file_server browse`, allow only `TLSv1.2 TLSv1.3`, emit `Strict-Transport-Security` headers, keep Caddy `auto_https` enabled, and never use `tls_insecure_skip_verify`.
- **Kubernetes & Docker Compose**: Block `privileged: true`, `/var/run/docker.sock` mounts, `hostNetwork`/`hostPID`/`hostIPC`, and `runAsUser: 0`; enforce CPU/memory `limits` and bind Compose DB ports to `127.0.0.1`.
- **Terraform & Ansible**: Require storage encryption (`encrypted = true`), disable `publicly_accessible = true`, keep `validate_certs` enabled, and avoid blanket `ignore_errors: true`.

---

## 4. Safe Cross-Platform Scripting, Cron & Postmortems
- **Bash / Zsh**: Start scripts with `set -euo pipefail`, protect variable removals with `${VAR:?}`, never pipe `curl`/`wget` directly into a shell, never pipe passwords to `sudo -S`, and never grant world-writable permissions (`a+rwx` / mode 777).
- **PowerShell**: Enforce `$ErrorActionPreference = 'Stop'` and `Set-StrictMode -Version Latest`, never pipe `irm`/`iwr` into `iex`, and never hardcode secrets in `ConvertTo-SecureString -AsPlainText`.
- **Cron & Postmortems**: Declare explicit `SHELL=` and `PATH=`, wrap recurring jobs in `flock` locks, never run jobs from `/tmp`, and document incidents blamelessly with UTC timelines, TTD/TTM/TTR metrics, 5-Whys, and corrective action items.
