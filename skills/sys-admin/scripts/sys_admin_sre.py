#!/usr/bin/env python3
"""
sys_admin_sre.py — Deep SRE Operations Engine for sys_admin.py

Provides token-efficient log triage, live host security posture auditing,
transactional safe config application with automatic rollback, host drift snapshots,
batch endpoint health checks, read-only SSH remote triage, and native validator
delegation (Python 3.10+ stdlib only).
"""

from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple


IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".agents",
    ".gemini",
    ".idea",
    ".vscode",
}

SKIP_SELF_NAMES = {
    "sys_admin.py",
    "sys_admin_sre.py",
    "audit_security.py",
    "guard_command.py",
    "review_code.py",
    "audit_pr.py",
}


def _note_exc(exc: Exception) -> str:
    """Formats exception type and message for diagnostic reporting."""
    return f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# 1. Token-Efficient Log Triage
# ---------------------------------------------------------------------------

_LOG_INCIDENT_RULES = [
    (
        "LOG-OOM-KILL",
        "CRITICAL",
        1,
        re.compile(r"(?:Out of memory:\s*Killed process|invoked oom-killer|\boom-killer\b)", re.IGNORECASE),
        "Kernel OOM killer terminated a process due to memory exhaustion",
        "Inspect memory limits/leaks, review 'dmesg -T | grep -i oom', and tune MemoryMax/swap.",
    ),
    (
        "LOG-DISK-IO",
        "CRITICAL",
        1,
        re.compile(r"(?:No space left on device|\bENOSPC\b|Read-only file system|\bI/O error\b)", re.IGNORECASE),
        "Filesystem exhaustion, read-only remount, or storage I/O failure detected",
        "Check block/inode usage ('df -hT && df -i') and SMART/kernel disk health before restarting writes.",
    ),
    (
        "LOG-AUTH-SPIKE",
        "HIGH",
        10,
        re.compile(r"(?:Failed password for|Invalid user\b|authentication failure\b)", re.IGNORECASE),
        "Elevated SSH/authentication failure volume (possible brute-force scan)",
        "Verify PermitRootLogin/PasswordAuthentication are disabled and check fail2ban/firewall rules.",
    ),
    (
        "LOG-HTTP-5XX",
        "HIGH",
        5,
        re.compile(r"(?:\b50[0234]\b|upstream timed out|bad gateway|Connection refused)", re.IGNORECASE),
        "Repeated upstream/proxy 5xx errors or refused backend connections",
        "Verify backend service health, socket queue limits, and upstream proxy timeouts.",
    ),
    (
        "LOG-TLS-ERROR",
        "HIGH",
        1,
        re.compile(r"(?:certificate has expired|SSL_do_handshake\(\)\s*failed|x509:\s*certificate)", re.IGNORECASE),
        "TLS certificate expiration or handshake failure recorded in logs",
        "Run '--check-tls' against the endpoint, verify fullchain/key permissions, and renew certs.",
    ),
    (
        "LOG-CRASH-LOOP",
        "HIGH",
        1,
        re.compile(
            r"(?:Main process exited,\s*code=exited|Scheduled restart job|\bsegfault at\b|\bpanic:)",
            re.IGNORECASE,
        ),
        "Service crash, panic, segfault, or systemd restart loop detected",
        "Inspect recent unit logs ('journalctl -u <service> -n 100') and recent config/binary deploys.",
    ),
]

_LOG_ERROR_RE = re.compile(
    r"\b(?:emerg|alert|crit|critical|fatal|panic|error|err|failed|failure|exception|traceback|oom|timeout|denied)\b",
    re.IGNORECASE,
)
_LOG_WARN_RE = re.compile(r"\b(?:warn|warning|deprecated|retry)\b", re.IGNORECASE)


def _normalize_log_signature(line: str) -> str:
    """Strips volatile timestamps, IPs, UUIDs, hex values, and numbers for clustering."""
    sig = line.strip()
    sig = re.sub(r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*", "", sig)
    sig = re.sub(r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s*", "", sig)
    sig = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "<UUID>", sig)
    sig = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b", "<IP>", sig)
    sig = re.sub(r"\b0x[0-9a-fA-F]+\b", "<HEX>", sig)
    sig = re.sub(r"\b\d+\b", "<N>", sig)
    sig = re.sub(r"\s+", " ", sig).strip()
    return sig[:140]


def triage_logs(log_source: Path, max_lines: int = 50000, top_n: int = 10) -> Dict[str, Any]:
    """Condenses large log files into structured incident alerts and top deduplicated error clusters."""
    resolved = Path(log_source).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Log source not found: {resolved}")

    if resolved.is_file():
        files = [resolved]
    else:
        files = sorted(p for p in resolved.rglob("*.log") if p.is_file())
        if not files:
            files = sorted(p for p in resolved.iterdir() if p.is_file())

    collected_lines: List[str] = []
    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            collected_lines.extend(text.splitlines())
        except OSError as exc:
            _ = _note_exc(exc)

    if max_lines > 0 and len(collected_lines) > max_lines:
        collected_lines = collected_lines[-max_lines:]

    rule_counts: Dict[str, int] = {r[0]: 0 for r in _LOG_INCIDENT_RULES}
    rule_samples: Dict[str, str] = {}
    cluster_counts: Counter = Counter()
    cluster_samples: Dict[str, str] = {}
    error_lines = 0
    warn_lines = 0

    for raw in collected_lines:
        stripped = raw.strip()
        if not stripped:
            continue

        matched_incident = False
        for rule_id, _sev, _thresh, pattern, _msg, _rem in _LOG_INCIDENT_RULES:
            if pattern.search(stripped):
                rule_counts[rule_id] += 1
                rule_samples.setdefault(rule_id, stripped[:180])
                matched_incident = True

        is_err = matched_incident or bool(_LOG_ERROR_RE.search(stripped))
        is_warn = bool(_LOG_WARN_RE.search(stripped))

        if is_err:
            error_lines += 1
            sig = _normalize_log_signature(stripped)
            if sig:
                cluster_counts[sig] += 1
                cluster_samples.setdefault(sig, stripped[:180])
        elif is_warn:
            warn_lines += 1
            sig = _normalize_log_signature(stripped)
            if sig:
                cluster_counts[sig] += 1
                cluster_samples.setdefault(sig, stripped[:180])

    alerts: List[Dict[str, Any]] = []
    for rule_id, severity, threshold, _pattern, message, remediation in _LOG_INCIDENT_RULES:
        count = rule_counts[rule_id]
        if count >= threshold:
            alerts.append({
                "id": rule_id,
                "severity": severity,
                "count": count,
                "message": message,
                "sample": rule_samples.get(rule_id, ""),
                "remediation": remediation,
            })

    top_clusters = [
        {"count": cnt, "signature": sig, "sample": cluster_samples.get(sig, "")}
        for sig, cnt in cluster_counts.most_common(max(1, top_n))
    ]

    if any(a["severity"] in {"CRITICAL", "HIGH"} for a in alerts):
        status = "fail"
    elif error_lines > 0 or warn_lines > 0:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "source": str(resolved),
        "lines_scanned": len(collected_lines),
        "error_lines": error_lines,
        "warn_lines": warn_lines,
        "alerts": alerts,
        "top_clusters": top_clusters,
    }


# ---------------------------------------------------------------------------
# 2. Live Host Security Posture Audit
# ---------------------------------------------------------------------------

def audit_host_posture(
    home_dir: Optional[Path] = None,
    ssh_dir: Optional[Path] = None,
    check_system_files: bool = True,
) -> Dict[str, Any]:
    """Audits local host SSH file permissions, shadow file permissions, umask, and reboot state."""
    findings: List[Dict[str, Any]] = []
    checks_run = 0

    if os.name == "nt":
        return {
            "status": "pass",
            "checks_run": 0,
            "critical_count": 0,
            "high_count": 0,
            "warning_count": 0,
            "skipped_windows": True,
            "findings": findings,
        }

    resolved_home = Path(home_dir).resolve() if home_dir else Path.home().resolve()
    resolved_ssh = Path(ssh_dir).resolve() if ssh_dir else (resolved_home / ".ssh")

    if resolved_ssh.exists() and resolved_ssh.is_dir():
        checks_run += 1
        try:
            dir_mode = stat.S_IMODE(resolved_ssh.stat().st_mode)
            if dir_mode & 0o077 != 0:
                findings.append({
                    "id": "HOST-SSH-DIR-PERM",
                    "severity": "HIGH",
                    "target": str(resolved_ssh),
                    "mode": oct(dir_mode),
                    "message": f"SSH directory {resolved_ssh} is accessible to group/others (mode {oct(dir_mode)})",
                    "remediation": f"Run: chmod 700 '{resolved_ssh}'",
                })
        except OSError as exc:
            _ = _note_exc(exc)

        sensitive_names = {"authorized_keys", "authorized_keys2", "config", "id_rsa", "id_ed25519", "id_ecdsa"}
        try:
            for child in sorted(resolved_ssh.iterdir()):
                if not child.is_file() or child.name.endswith(".pub"):
                    continue
                if child.name in sensitive_names or child.suffix.lower() == ".pem":
                    checks_run += 1
                    fmode = stat.S_IMODE(child.stat().st_mode)
                    if fmode & 0o077 != 0:
                        findings.append({
                            "id": "HOST-SSH-KEY-PERM",
                            "severity": "CRITICAL",
                            "target": str(child),
                            "mode": oct(fmode),
                            "message": f"Sensitive SSH file {child.name} has overly permissive mode {oct(fmode)}",
                            "remediation": f"Run: chmod 600 '{child}'",
                        })
        except OSError as exc:
            _ = _note_exc(exc)

    # Check process umask without permanently altering it
    checks_run += 1
    current_umask = os.umask(0o022)
    os.umask(current_umask)
    if (current_umask & 0o002) == 0:
        findings.append({
            "id": "HOST-PERMISSIVE-UMASK",
            "severity": "WARNING",
            "target": "process-umask",
            "mode": oct(current_umask),
            "message": f"Process umask {oct(current_umask)} allows world-writable newly created files",
            "remediation": "Set 'umask 027' or 'umask 077' in shell/service profiles.",
        })

    if check_system_files:
        shadow_path = Path("/etc/shadow")
        if shadow_path.exists():
            checks_run += 1
            try:
                shadow_mode = stat.S_IMODE(shadow_path.stat().st_mode)
                if shadow_mode & 0o004 != 0:
                    findings.append({
                        "id": "HOST-SHADOW-PERM",
                        "severity": "CRITICAL",
                        "target": str(shadow_path),
                        "mode": oct(shadow_mode),
                        "message": f"/etc/shadow is world-readable (mode {oct(shadow_mode)})",
                        "remediation": "Restrict immediately: chmod 640 /etc/shadow && chown root:shadow /etc/shadow",
                    })
            except OSError as exc:
                _ = _note_exc(exc)

        reboot_marker = Path("/var/run/reboot-required")
        checks_run += 1
        if reboot_marker.exists():
            findings.append({
                "id": "HOST-REBOOT-REQUIRED",
                "severity": "WARNING",
                "target": str(reboot_marker),
                "mode": "present",
                "message": "System reboot pending (/var/run/reboot-required exists for kernel/security updates)",
                "remediation": "Schedule a controlled maintenance reboot and verify services post-boot.",
            })

    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    warning_count = sum(1 for f in findings if f["severity"] == "WARNING")

    return {
        "status": "fail" if (critical_count > 0 or high_count > 0) else "pass",
        "checks_run": checks_run,
        "critical_count": critical_count,
        "high_count": high_count,
        "warning_count": warning_count,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# 3. Transactional Safe Config Apply with Automatic Rollback
# ---------------------------------------------------------------------------

def apply_config_safe(
    source: Path,
    destination: Path,
    validate_cmd: Optional[List[str]] = None,
    backup_dir: Optional[Path] = None,
    dry_run: bool = False,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Atomically applies a config file with SHA-256 receipts, pre-reload validation, and auto-rollback."""
    src = Path(source).resolve()
    dst = Path(destination).resolve()
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Source config file not found: {src}")

    new_bytes = src.read_bytes()
    new_text = new_bytes.decode("utf-8", errors="replace")
    sha256_after = hashlib.sha256(new_bytes).hexdigest()

    had_existing = dst.exists()
    if had_existing:
        old_bytes = dst.read_bytes()
        old_text = old_bytes.decode("utf-8", errors="replace")
        sha256_before: Optional[str] = hashlib.sha256(old_bytes).hexdigest()
        existing_mode = stat.S_IMODE(dst.stat().st_mode)
    else:
        old_text = ""
        sha256_before = None
        existing_mode = None

    diff = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{dst}",
            tofile=f"b/{dst}",
        )
    )

    if dry_run:
        return {
            "status": "pass",
            "dry_run": True,
            "destination": str(dst),
            "sha256_before": sha256_before,
            "sha256_after": sha256_after,
            "diff": diff,
        }

    dst.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Optional[Path] = None
    if had_existing:
        bdir = Path(backup_dir).resolve() if backup_dir else (dst.parent / ".sysadmin-backups")
        bdir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = bdir / f"{dst.name}.{stamp}.bak"
        shutil.copy2(dst, backup_path)

    def _atomic_write_bytes(payload: bytes, mode: Optional[int]) -> None:
        tmp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(dst.parent),
                prefix=f".{dst.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = Path(tmp.name)
            if mode is not None and os.name != "nt":
                os.chmod(tmp_path, mode)
            os.replace(tmp_path, dst)
        except Exception:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    _atomic_write_bytes(new_bytes, existing_mode)

    if validate_cmd:
        val_rc = 1
        val_stdout = ""
        val_stderr = ""
        try:
            res = subprocess.run(
                validate_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            val_rc = res.returncode
            val_stdout = res.stdout.strip()
            val_stderr = res.stderr.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            val_rc = 1
            val_stderr = _note_exc(exc)

        if val_rc != 0:
            if had_existing and backup_path and backup_path.exists():
                _atomic_write_bytes(backup_path.read_bytes(), existing_mode)
            elif not had_existing and dst.exists():
                dst.unlink(missing_ok=True)

            return {
                "status": "fail",
                "dry_run": False,
                "rolled_back": True,
                "destination": str(dst),
                "backup_path": str(backup_path) if backup_path else None,
                "sha256_before": sha256_before,
                "sha256_after": sha256_after,
                "validation_returncode": val_rc,
                "validation_stdout": val_stdout,
                "validation_stderr": val_stderr,
                "diff": diff,
            }

    return {
        "status": "pass",
        "dry_run": False,
        "rolled_back": False,
        "destination": str(dst),
        "backup_path": str(backup_path) if backup_path else None,
        "sha256_before": sha256_before,
        "sha256_after": sha256_after,
        "diff": diff,
    }


# ---------------------------------------------------------------------------
# 4. Host Posture Drift Snapshots
# ---------------------------------------------------------------------------

def _read_linux_sysctls() -> Dict[str, str]:
    keys = {
        "net.ipv4.ip_forward": Path("/proc/sys/net/ipv4/ip_forward"),
        "net.ipv4.conf.all.accept_redirects": Path("/proc/sys/net/ipv4/conf/all/accept_redirects"),
        "kernel.kptr_restrict": Path("/proc/sys/kernel/kptr_restrict"),
        "kernel.randomize_va_space": Path("/proc/sys/kernel/randomize_va_space"),
    }
    values: Dict[str, str] = {}
    for key, p in keys.items():
        if p.exists():
            try:
                values[key] = p.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError as exc:
                _ = _note_exc(exc)
    return values


def capture_host_snapshot(
    health_report: Dict[str, Any],
    posture_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Captures a normalized, diffable host telemetry and posture snapshot."""
    disk = health_report.get("disk", {})
    inodes = disk.get("inodes") or {}
    mem = health_report.get("memory", {})
    services = health_report.get("services", {})
    ports = health_report.get("listening_ports") or {}
    posture_ids = sorted({f["id"] for f in (posture_report or {}).get("findings", []) if "id" in f})

    return {
        "timestamp_utc": health_report.get("timestamp_utc") or datetime.now(timezone.utc).isoformat(),
        "hostname": health_report.get("hostname", ""),
        "os": health_report.get("os", ""),
        "release": health_report.get("release", ""),
        "cpu_count": health_report.get("cpu_count"),
        "disk_percent": disk.get("percent_used", 0.0),
        "inode_percent": inodes.get("percent_used") if inodes.get("available") else None,
        "memory_percent": mem.get("percent_used") if mem.get("available") else None,
        "failed_units": sorted(services.get("failed_units", [])),
        "listening_ports": sorted(ports.get("entries", [])),
        "posture_finding_ids": posture_ids,
        "sysctl": _read_linux_sysctls(),
    }


def diff_host_snapshots(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Computes security and operational drift between two host posture snapshots."""
    base_ports = set(baseline.get("listening_ports", []))
    curr_ports = set(current.get("listening_ports", []))
    added_ports = sorted(curr_ports - base_ports)
    removed_ports = sorted(base_ports - curr_ports)

    base_failed = set(baseline.get("failed_units", []))
    curr_failed = set(current.get("failed_units", []))
    newly_failed_services = sorted(curr_failed - base_failed)
    recovered_services = sorted(base_failed - curr_failed)

    base_posture = set(baseline.get("posture_finding_ids", []))
    curr_posture = set(current.get("posture_finding_ids", []))
    new_posture_findings = sorted(curr_posture - base_posture)

    base_disk = float(baseline.get("disk_percent") or 0.0)
    curr_disk = float(current.get("disk_percent") or 0.0)
    disk_delta_pct = round(curr_disk - base_disk, 2)

    base_mem = baseline.get("memory_percent")
    curr_mem = current.get("memory_percent")
    memory_delta_pct = round(float(curr_mem) - float(base_mem), 2) if (base_mem is not None and curr_mem is not None) else None

    os_changed = (
        baseline.get("os") != current.get("os")
        or baseline.get("release") != current.get("release")
    )

    base_sysctl = baseline.get("sysctl", {})
    curr_sysctl = current.get("sysctl", {})
    sysctl_changes: Dict[str, Dict[str, Any]] = {}
    for k in sorted(set(base_sysctl) | set(curr_sysctl)):
        if base_sysctl.get(k) != curr_sysctl.get(k):
            sysctl_changes[k] = {"before": base_sysctl.get(k), "after": curr_sysctl.get(k)}

    if newly_failed_services or new_posture_findings or (curr_disk >= 90.0 and disk_delta_pct > 0):
        status = "fail"
    elif added_ports or disk_delta_pct >= 10.0 or os_changed or sysctl_changes:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "baseline_timestamp": baseline.get("timestamp_utc"),
        "current_timestamp": current.get("timestamp_utc"),
        "added_ports": added_ports,
        "removed_ports": removed_ports,
        "newly_failed_services": newly_failed_services,
        "recovered_services": recovered_services,
        "new_posture_findings": new_posture_findings,
        "disk_delta_pct": disk_delta_pct,
        "memory_delta_pct": memory_delta_pct,
        "os_changed": os_changed,
        "sysctl_changes": sysctl_changes,
    }


# ---------------------------------------------------------------------------
# 5. Batch Endpoint Health Probes
# ---------------------------------------------------------------------------

def check_endpoints_manifest(
    manifest_path: Path,
    check_tls_fn: Callable[..., Dict[str, Any]],
    check_port_fn: Callable[..., Dict[str, Any]],
    check_dns_fn: Callable[[str], Dict[str, Any]],
    timeout: float = 5.0,
    warn_days: int = 30,
    crit_days: int = 7,
) -> Dict[str, Any]:
    """Executes DNS, TCP port, and TLS checks across an endpoints JSON manifest."""
    resolved = Path(manifest_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Endpoints manifest not found: {resolved}")

    raw_data = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(raw_data, dict):
        endpoints = raw_data.get("endpoints", [])
    elif isinstance(raw_data, list):
        endpoints = raw_data
    else:
        raise ValueError("Endpoints manifest must be a JSON object with 'endpoints' or a JSON array")

    results: List[Dict[str, Any]] = []
    passed = 0
    warned = 0
    failed = 0

    def _record(name: str, kind: str, target: str, probe_fn: Callable[[], Dict[str, Any]]) -> None:
        nonlocal passed, warned, failed
        try:
            res = probe_fn()
        except ValueError as exc:
            res = {"status": "fail", "error": _note_exc(exc)}
        st = res.get("status", "fail")
        if st == "pass":
            passed += 1
        elif st == "warn":
            warned += 1
        else:
            failed += 1
        results.append({"name": name, "kind": kind, "target": target, **res})

    for idx, item in enumerate(endpoints, 1):
        if not isinstance(item, dict):
            continue
        label = str(item.get("name") or f"endpoint-{idx}")
        if item.get("dns"):
            dns_host = str(item["dns"])
            _record(label, "dns", dns_host, lambda h=dns_host: check_dns_fn(h))
        if item.get("port"):
            port_spec = str(item["port"])
            _record(label, "tcp", port_spec, lambda p=port_spec: check_port_fn(p, timeout=timeout))
        if item.get("tls"):
            tls_spec = str(item["tls"])
            _record(
                label,
                "tls",
                tls_spec,
                lambda t=tls_spec: check_tls_fn(t, timeout=timeout, warn_days=warn_days, crit_days=crit_days),
            )

    overall = "fail" if failed > 0 else ("warn" if warned > 0 else "pass")
    return {
        "status": overall,
        "manifest": str(resolved),
        "total_checks": len(results),
        "passed": passed,
        "warned": warned,
        "failed": failed,
        "results": results,
    }


# ---------------------------------------------------------------------------
# 6. Read-Only SSH Remote Triage
# ---------------------------------------------------------------------------

_SSH_TARGET_RE = re.compile(r"^[a-zA-Z0-9._-]+(?:@[a-zA-Z0-9._:-]+)?$")


def validate_ssh_target(target: str) -> str:
    """Validates a remote [user@]host target against option-injection or shell metacharacters."""
    clean = (target or "").strip()
    if not clean or clean.startswith("-") or ".." in clean or not _SSH_TARGET_RE.match(clean):
        raise ValueError(f"Unsafe or invalid SSH target specification: {target!r}")
    return clean


def run_remote_health_check(target: str, timeout: int = 8) -> Dict[str, Any]:
    """Runs non-interactive read-only host triage over SSH BatchMode."""
    clean_target = validate_ssh_target(target)
    ssh_bin = shutil.which("ssh")
    if not ssh_bin:
        return {
            "status": "fail",
            "target": clean_target,
            "error": "ssh client binary not found in PATH",
        }

    remote_cmd = "uname -srm; uptime; df -Pk /; systemctl --failed --no-legend --plain 2>/dev/null || true"
    cmd = [
        ssh_bin,
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={max(1, int(timeout))}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "--",
        clean_target,
        remote_cmd,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5, check=False)
        return {
            "status": "pass" if res.returncode == 0 else "fail",
            "target": clean_target,
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "status": "fail",
            "target": clean_target,
            "error": _note_exc(exc),
        }


# ---------------------------------------------------------------------------
# 7. Opportunistic Native Validator Delegation
# ---------------------------------------------------------------------------

def _collect_target_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    collected: List[Path] = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in sorted(dirs) if d not in IGNORE_DIRS and d != "tests"]
        for fname in sorted(files):
            if fname.startswith("test_") or fname in SKIP_SELF_NAMES:
                continue
            collected.append(Path(root) / fname)
    return collected


def run_native_validators(target: Path, timeout: int = 10) -> Dict[str, Any]:
    """Runs available upstream validators (shellcheck/bash -n, systemd-analyze, caddy, ansible-lint, tflint)."""
    resolved = Path(target).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Validation target not found: {resolved}")

    files = _collect_target_files(resolved)
    base_dir = resolved.parent if resolved.is_file() else resolved
    findings: List[Dict[str, Any]] = []
    tools_used: List[str] = []
    tools_skipped: List[str] = []

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(base_dir)) if p != base_dir else p.name
        except ValueError as exc:
            _ = _note_exc(exc)
            return str(p)

    # 1. Shell scripts: shellcheck or bash -n fallback
    shell_files = [p for p in files if p.suffix.lower() in {".sh", ".bash"}]
    if shell_files:
        shellcheck_bin = shutil.which("shellcheck")
        bash_bin = shutil.which("bash")
        if shellcheck_bin:
            tools_used.append("shellcheck")
            try:
                res = subprocess.run(
                    [shellcheck_bin, "-f", "json", *[str(p) for p in shell_files]],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                if res.stdout.strip():
                    items = json.loads(res.stdout)
                    for item in items:
                        lvl = str(item.get("level", "warning")).lower()
                        sev = "HIGH" if lvl == "error" else "WARNING"
                        findings.append({
                            "id": f"NATIVE-SC{item.get('code', '0000')}",
                            "severity": sev,
                            "category": "Native Validator (shellcheck)",
                            "file": _rel(Path(item.get("file", ""))),
                            "line": int(item.get("line", 1)),
                            "snippet": "",
                            "message": item.get("message", "shellcheck warning"),
                            "remediation": f"Resolve SC{item.get('code', '')} finding reported by shellcheck.",
                            "source": "shellcheck",
                        })
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                _ = _note_exc(exc)
        elif bash_bin:
            tools_skipped.append("shellcheck")
            tools_used.append("bash -n")
            for sh_file in shell_files:
                try:
                    res = subprocess.run(
                        [bash_bin, "-n", str(sh_file)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    if res.returncode != 0:
                        err_text = res.stderr.strip() or "bash syntax error"
                        line_match = re.search(r"line\s+(\d+):", err_text)
                        line_no = int(line_match.group(1)) if line_match else 1
                        findings.append({
                            "id": "NATIVE-BASH-SYNTAX",
                            "severity": "HIGH",
                            "category": "Native Validator (bash -n)",
                            "file": _rel(sh_file),
                            "line": line_no,
                            "snippet": err_text[:120],
                            "message": f"Shell syntax error detected by bash -n: {err_text}",
                            "remediation": "Fix shell syntax error before executing script.",
                            "source": "bash -n",
                        })
                except (OSError, subprocess.SubprocessError) as exc:
                    _ = _note_exc(exc)
        else:
            tools_skipped.extend(["shellcheck", "bash -n"])

    # 2. Systemd units
    unit_files = [p for p in files if p.suffix.lower() == ".service"]
    if unit_files:
        sd_bin = shutil.which("systemd-analyze")
        if sd_bin:
            tools_used.append("systemd-analyze")
            for ufile in unit_files:
                try:
                    res = subprocess.run(
                        [sd_bin, "verify", str(ufile)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    if res.returncode != 0:
                        msg = (res.stderr or res.stdout).strip()
                        findings.append({
                            "id": "NATIVE-SYSTEMD-VERIFY",
                            "severity": "WARNING",
                            "category": "Native Validator (systemd-analyze)",
                            "file": _rel(ufile),
                            "line": 1,
                            "snippet": msg[:120],
                            "message": msg or "systemd-analyze verify reported issues",
                            "remediation": "Fix unit directive warnings reported by systemd-analyze verify.",
                            "source": "systemd-analyze",
                        })
                except (OSError, subprocess.SubprocessError) as exc:
                    _ = _note_exc(exc)
        else:
            tools_skipped.append("systemd-analyze")

    # 3. Caddyfiles
    caddy_files = [
        p for p in files if p.name == "Caddyfile" or p.name.startswith("Caddyfile.") or p.suffix.lower() == ".caddy"
    ]
    if caddy_files:
        caddy_bin = shutil.which("caddy")
        if caddy_bin:
            tools_used.append("caddy")
            for cfile in caddy_files:
                try:
                    res = subprocess.run(
                        [caddy_bin, "validate", "--config", str(cfile)],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    if res.returncode != 0:
                        msg = (res.stderr or res.stdout).strip()
                        findings.append({
                            "id": "NATIVE-CADDY-VALIDATE",
                            "severity": "HIGH",
                            "category": "Native Validator (caddy)",
                            "file": _rel(cfile),
                            "line": 1,
                            "snippet": msg[:120],
                            "message": msg or "caddy validate failed",
                            "remediation": "Correct Caddyfile syntax before reload.",
                            "source": "caddy",
                        })
                except (OSError, subprocess.SubprocessError) as exc:
                    _ = _note_exc(exc)
        else:
            tools_skipped.append("caddy")

    # 4. Ansible playbooks
    ansible_files = [
        p
        for p in files
        if p.suffix.lower() in {".yml", ".yaml"} and ("playbook" in p.name.lower() or "ansible" in p.name.lower())
    ]
    if ansible_files:
        al_bin = shutil.which("ansible-lint")
        if al_bin:
            tools_used.append("ansible-lint")
            try:
                res = subprocess.run(
                    [al_bin, "-f", "json", *[str(p) for p in ansible_files]],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                if res.stdout.strip():
                    items = json.loads(res.stdout)
                    for item in items:
                        findings.append({
                            "id": f"NATIVE-ANSIBLE-{item.get('check_name', 'LINT')}",
                            "severity": "WARNING",
                            "category": "Native Validator (ansible-lint)",
                            "file": str(item.get("location", {}).get("path", "")),
                            "line": int(item.get("location", {}).get("lines", {}).get("begin", 1)),
                            "snippet": "",
                            "message": item.get("description", "ansible-lint finding"),
                            "remediation": "Address ansible-lint recommendation.",
                            "source": "ansible-lint",
                        })
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                _ = _note_exc(exc)
        else:
            tools_skipped.append("ansible-lint")

    # 5. Terraform
    tf_dirs = sorted({p.parent for p in files if p.suffix.lower() == ".tf"})
    if tf_dirs:
        tf_bin = shutil.which("tflint")
        if tf_bin:
            tools_used.append("tflint")
            for tdir in tf_dirs:
                try:
                    res = subprocess.run(
                        [tf_bin, "--format", "json"],
                        cwd=str(tdir),
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    if res.stdout.strip():
                        data = json.loads(res.stdout)
                        for issue in data.get("issues", []):
                            rng = issue.get("range", {})
                            findings.append({
                                "id": f"NATIVE-TFLINT-{issue.get('rule', {}).get('name', 'RULE')}",
                                "severity": "WARNING",
                                "category": "Native Validator (tflint)",
                                "file": str(rng.get("filename", "")),
                                "line": int(rng.get("start", {}).get("line", 1)),
                                "snippet": "",
                                "message": issue.get("message", "tflint finding"),
                                "remediation": "Address tflint recommendation.",
                                "source": "tflint",
                            })
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    _ = _note_exc(exc)
        else:
            tools_skipped.append("tflint")

    return {
        "tools_used": tools_used,
        "tools_skipped": tools_skipped,
        "findings": findings,
    }
