#!/usr/bin/env python3
"""
sys_admin.py — Universal System Administration, Infrastructure Hardening & SRE Triage Tool

Provides live cross-platform host diagnostics, network/DNS/TLS certificate checks,
static security/hardening audits for server configs, ops scripts, and IaC manifests,
and hardened template scaffolding for services, proxies, backups, runbooks, and postmortems.

Usage:
    python3 sys_admin.py --health [--ports] [--json]
    python3 sys_admin.py --check-tls example.com:443
    python3 sys_admin.py --check-port localhost:5432
    python3 sys_admin.py --check-dns example.com
    python3 sys_admin.py --audit [PATH] [--check] [--json]
    python3 sys_admin.py --scaffold systemd --name api-server [--output path] [--force]
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import resource
except ImportError as exc:
    _RESOURCE_IMPORT_ERR = str(exc)
    resource = None  # type: ignore[assignment]

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import sys_admin_sre


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

SENSITIVE_TF_PORTS = {"22", "3389", "5432", "3306", "6379", "27017"}

_AUDIT_SENTINEL = "__UNSET__"


def _note_exc(exc: Exception) -> str:
    """Normalizes exception descriptions for structured diagnostics."""
    return f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# 1. Host Health & Live Triage
# ---------------------------------------------------------------------------

def evaluate_threshold_status(percent: float, warn: float, crit: float) -> str:
    """Evaluates percentage metric against warning and critical thresholds."""
    if percent >= crit:
        return "critical"
    if percent >= warn:
        return "warning"
    return "ok"


def parse_proc_meminfo(text: str) -> Optional[Dict[str, float]]:
    """Parses Linux /proc/meminfo text into GB and percentage metrics."""
    values_kb: Dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_()]+):\s+(\d+)\s+kB", line.strip())
        if match:
            values_kb[match.group(1)] = int(match.group(2))

    total_kb = values_kb.get("MemTotal", 0)
    if total_kb <= 0:
        return None

    if "MemAvailable" in values_kb:
        avail_kb = values_kb["MemAvailable"]
    else:
        avail_kb = (
            values_kb.get("MemFree", 0)
            + values_kb.get("Buffers", 0)
            + values_kb.get("Cached", 0)
            + values_kb.get("SReclaimable", 0)
        )

    avail_kb = max(0, min(total_kb, avail_kb))
    used_kb = max(0, total_kb - avail_kb)
    gib = 1024 * 1024
    return {
        "total_gb": round(total_kb / gib, 2),
        "used_gb": round(used_kb / gib, 2),
        "available_gb": round(avail_kb / gib, 2),
        "percent_used": round((used_kb / total_kb) * 100.0, 2),
    }


def parse_macos_vm_stat(vm_stat_text: str, total_bytes: int) -> Optional[Dict[str, float]]:
    """Parses macOS vm_stat output and total physical bytes into memory metrics."""
    if total_bytes <= 0 or not vm_stat_text.strip():
        return None

    page_size = 4096
    page_match = re.search(r"page size of (\d+) bytes", vm_stat_text)
    if page_match:
        page_size = int(page_match.group(1))

    counts: Dict[str, int] = {}
    for line in vm_stat_text.splitlines():
        match = re.match(r'^([^:]+):\s+(\d+)\.', line.strip())
        if match:
            counts[match.group(1).strip().lower()] = int(match.group(2))

    if not counts:
        return None

    active = counts.get("pages active", 0)
    wired = counts.get("pages wired down", 0)
    compressed = counts.get("pages occupied by compressor", 0)
    used_pages = active + wired + compressed

    if used_pages == 0:
        free = counts.get("pages free", 0)
        inactive = counts.get("pages inactive", 0)
        speculative = counts.get("pages speculative", 0)
        total_pages = total_bytes // page_size
        used_pages = max(0, total_pages - free - inactive - speculative)

    used_bytes = min(total_bytes, max(0, used_pages * page_size))
    avail_bytes = max(0, total_bytes - used_bytes)
    gib = 1024 ** 3
    return {
        "total_gb": round(total_bytes / gib, 2),
        "used_gb": round(used_bytes / gib, 2),
        "available_gb": round(avail_bytes / gib, 2),
        "percent_used": round((used_bytes / total_bytes) * 100.0, 2),
    }


def collect_memory_usage() -> Dict[str, Any]:
    """Collects host RAM metrics on Linux, macOS, or Windows using stdlib/OS tools."""
    system_name = platform.system().lower()
    if system_name == "linux":
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            try:
                parsed = parse_proc_meminfo(meminfo.read_text(encoding="utf-8", errors="ignore"))
                if parsed:
                    return {"available": True, **parsed}
                return {"available": False, "error": "Unable to parse /proc/meminfo"}
            except OSError as exc:
                return {"available": False, "error": _note_exc(exc)}
        return {"available": False, "error": "/proc/meminfo not found"}

    if system_name == "darwin":
        try:
            mem_res = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            vm_res = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if mem_res.returncode == 0 and vm_res.returncode == 0:
                total_bytes = int(mem_res.stdout.strip())
                parsed = parse_macos_vm_stat(vm_res.stdout, total_bytes)
                if parsed:
                    return {"available": True, **parsed}
            return {"available": False, "error": "Unable to collect macOS vm_stat/hw.memsize"}
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return {"available": False, "error": _note_exc(exc)}

    if system_name == "windows":
        ps_bin = shutil.which("powershell") or shutil.which("pwsh")
        if not ps_bin:
            return {"available": False, "error": "PowerShell binary not found"}
        try:
            res = subprocess.run(
                [
                    ps_bin,
                    "-NoProfile",
                    "-Command",
                    "$os = Get-CimInstance Win32_OperatingSystem; "
                    "@{Total=$os.TotalVisibleMemorySize; Free=$os.FreePhysicalMemory} | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                total_kb = float(data.get("Total", 0))
                free_kb = float(data.get("Free", 0))
                if total_kb > 0:
                    used_kb = max(0.0, total_kb - free_kb)
                    gib = 1024 * 1024
                    return {
                        "available": True,
                        "total_gb": round(total_kb / gib, 2),
                        "used_gb": round(used_kb / gib, 2),
                        "available_gb": round(free_kb / gib, 2),
                        "percent_used": round((used_kb / total_kb) * 100.0, 2),
                    }
            return {"available": False, "error": "Unable to query Win32_OperatingSystem"}
        except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
            return {"available": False, "error": _note_exc(exc)}

    return {"available": False, "error": f"Unsupported platform: {system_name}"}


def collect_uptime_seconds() -> Optional[float]:
    """Returns host uptime in seconds when supported, else None."""
    system_name = platform.system().lower()
    if system_name == "linux":
        uptime_path = Path("/proc/uptime")
        if uptime_path.exists():
            try:
                first = uptime_path.read_text(encoding="utf-8", errors="ignore").split()[0]
                return round(float(first), 2)
            except (OSError, ValueError, IndexError) as exc:
                _ = _note_exc(exc)
                return None
    elif system_name == "darwin":
        try:
            res = subprocess.run(
                ["sysctl", "-n", "kern.boottime"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if res.returncode == 0:
                match = re.search(r"sec\s*=\s*(\d+)", res.stdout)
                if match:
                    return round(max(0.0, time.time() - float(match.group(1))), 2)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            _ = _note_exc(exc)
            return None
    return None


def collect_inode_usage(target_path: str, warn: float = 80.0, crit: float = 90.0) -> Dict[str, Any]:
    """Collects POSIX inode utilization via os.statvfs when available."""
    if not hasattr(os, "statvfs"):
        return {"available": False, "error": "os.statvfs not supported on this platform"}
    try:
        st = os.statvfs(target_path)
        total = int(st.f_files)
        free = int(st.f_favail)
        if total <= 0:
            return {"available": False, "error": "Filesystem reports 0 total inodes"}
        used = max(0, total - free)
        percent = round((used / total) * 100.0, 2)
        return {
            "available": True,
            "total_inodes": total,
            "used_inodes": used,
            "free_inodes": free,
            "percent_used": percent,
            "status": evaluate_threshold_status(percent, warn, crit),
        }
    except OSError as exc:
        return {"available": False, "error": _note_exc(exc)}


def parse_launchctl_list(text: str) -> List[str]:
    """Parses macOS `launchctl list` output for exited non-Apple jobs with non-zero exit status."""
    failed: List[str] = []
    for raw in text.splitlines():
        parts = raw.strip().split(None, 2)
        if len(parts) < 3 or parts[0] == "PID":
            continue
        pid, status_str, label = parts[0], parts[1], parts[2].strip()
        if label.startswith("com.apple."):
            continue
        if pid == "-" and status_str.lstrip("-").isdigit() and int(status_str) > 0:
            failed.append(label)
    return failed


def parse_windows_stopped_services(text: str) -> List[str]:
    """Parses PowerShell Win32_Service JSON or line output for stopped Auto-start services."""
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            items = data if isinstance(data, list) else [data]
            return [str(item.get("Name")) for item in items if isinstance(item, dict) and item.get("Name")]
        except ValueError as exc:
            _ = _note_exc(exc)
    names: List[str] = []
    for line in stripped.splitlines():
        tok = line.strip()
        if tok and tok.lower() not in {"name", "----"}:
            names.append(tok.split()[0])
    return names


def collect_failed_services() -> Dict[str, Any]:
    """Checks for failed or unexpectedly stopped services across Linux, macOS, and Windows."""
    sys_name = platform.system().lower()
    if sys_name == "linux" and shutil.which("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "--failed", "--no-legend", "--plain"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if res.returncode == 0:
                units = [line.split()[0] for line in res.stdout.splitlines() if line.strip()]
                return {
                    "manager": "systemd",
                    "available": True,
                    "failed_count": len(units),
                    "failed_units": units,
                }
            return {
                "manager": "systemd",
                "available": False,
                "failed_count": 0,
                "failed_units": [],
                "error": res.stderr.strip() or f"systemctl exited {res.returncode}",
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "manager": "systemd",
                "available": False,
                "failed_count": 0,
                "failed_units": [],
                "error": _note_exc(exc),
            }

    if sys_name == "darwin" and shutil.which("launchctl"):
        try:
            res = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if res.returncode == 0:
                failed = parse_launchctl_list(res.stdout)
                return {
                    "manager": "launchd",
                    "available": True,
                    "failed_count": len(failed),
                    "failed_units": failed,
                }
            return {
                "manager": "launchd",
                "available": False,
                "failed_count": 0,
                "failed_units": [],
                "error": res.stderr.strip() or f"launchctl exited {res.returncode}",
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "manager": "launchd",
                "available": False,
                "failed_count": 0,
                "failed_units": [],
                "error": _note_exc(exc),
            }

    if sys_name == "windows":
        ps_bin = shutil.which("powershell") or shutil.which("pwsh")
        if ps_bin:
            try:
                res = subprocess.run(
                    [
                        ps_bin,
                        "-NoProfile",
                        "-Command",
                        "Get-CimInstance Win32_Service -Filter \"StartMode='Auto' AND State!='Running'\" "
                        "| Select-Object Name | ConvertTo-Json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if res.returncode == 0:
                    failed = parse_windows_stopped_services(res.stdout)
                    return {
                        "manager": "scm",
                        "available": True,
                        "failed_count": len(failed),
                        "failed_units": failed,
                    }
            except (OSError, subprocess.SubprocessError) as exc:
                return {
                    "manager": "scm",
                    "available": False,
                    "failed_count": 0,
                    "failed_units": [],
                    "error": _note_exc(exc),
                }

    return {
        "manager": "none",
        "available": False,
        "failed_count": 0,
        "failed_units": [],
    }


def parse_ps_output(text: str) -> Dict[str, Any]:
    """Parses `ps -eo pid,pcpu,pmem,stat,comm` output into top CPU/RAM processes and zombie count."""
    procs: List[Dict[str, Any]] = []
    zombies = 0
    for raw in text.splitlines():
        parts = raw.strip().split(None, 4)
        if len(parts) < 5 or parts[0].upper() == "PID":
            continue
        try:
            pid = int(parts[0])
            cpu_pct = float(parts[1])
            mem_pct = float(parts[2])
        except ValueError as exc:
            _ = _note_exc(exc)
            continue
        state = parts[3]
        comm = parts[4].strip()
        if state.upper().startswith("Z"):
            zombies += 1
        procs.append({"pid": pid, "cpu_percent": cpu_pct, "mem_percent": mem_pct, "stat": state, "command": comm})

    top_cpu = sorted(procs, key=lambda p: p["cpu_percent"], reverse=True)[:5]
    top_memory = sorted(procs, key=lambda p: p["mem_percent"], reverse=True)[:5]
    return {
        "total_processes": len(procs),
        "zombie_count": zombies,
        "top_cpu": top_cpu,
        "top_memory": top_memory,
    }


def parse_proc_file_nr(text: str) -> Optional[Dict[str, Any]]:
    """Parses Linux /proc/sys/fs/file-nr (`allocated unused max`) into FD metrics."""
    parts = text.strip().split()
    if len(parts) < 3:
        return None
    try:
        allocated = int(parts[0])
        maximum = int(parts[2])
    except ValueError as exc:
        _ = _note_exc(exc)
        return None
    if maximum <= 0:
        return None
    return {
        "allocated": allocated,
        "max": maximum,
        "percent_used": round((allocated / maximum) * 100.0, 2),
    }


def collect_process_summary() -> Dict[str, Any]:
    """Collects top CPU/RAM processes, zombie counts, and file descriptor usage/limits."""
    summary: Dict[str, Any] = {
        "available": False,
        "total_processes": 0,
        "zombie_count": 0,
        "top_cpu": [],
        "top_memory": [],
        "fd_usage": None,
        "nofile_limit": None,
    }

    if resource is not None and hasattr(resource, "RLIMIT_NOFILE"):
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            summary["nofile_limit"] = {"soft": soft, "hard": hard}
        except (OSError, ValueError) as exc:
            _ = _note_exc(exc)

    file_nr = Path("/proc/sys/fs/file-nr")
    if file_nr.exists():
        try:
            parsed_nr = parse_proc_file_nr(file_nr.read_text(encoding="utf-8", errors="ignore"))
            if parsed_nr:
                summary["fd_usage"] = parsed_nr
        except OSError as exc:
            _ = _note_exc(exc)

    if shutil.which("ps") and os.name != "nt":
        try:
            res = subprocess.run(
                ["ps", "-eo", "pid,pcpu,pmem,stat,comm"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if res.returncode == 0:
                parsed = parse_ps_output(res.stdout)
                summary.update({"available": True, **parsed})
        except (OSError, subprocess.SubprocessError) as exc:
            summary["error"] = _note_exc(exc)

    return summary


def collect_listening_ports() -> Dict[str, Any]:
    """Collects best-effort read-only listening sockets via ss, lsof, or netstat."""
    candidates: List[Tuple[str, List[str]]] = []
    if shutil.which("ss"):
        candidates.append(("ss", ["ss", "-tuln"]))
    if shutil.which("lsof"):
        candidates.append(("lsof", ["lsof", "-iTCP", "-sTCP:LISTEN", "-nP"]))
    if shutil.which("netstat"):
        candidates.append(("netstat", ["netstat", "-an"]))

    last_error = "No port inspection tool (ss, lsof, netstat) found"
    for tool_name, cmd in candidates:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=False)
            if res.returncode == 0:
                lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
                entries = lines[1:] if len(lines) > 1 else lines
                if tool_name == "netstat":
                    entries = [ln for ln in entries if "LISTEN" in ln.upper()]
                return {
                    "available": True,
                    "tool": tool_name,
                    "count": len(entries),
                    "entries": entries[:50],
                }
            last_error = res.stderr.strip() or f"{tool_name} exited {res.returncode}"
        except (OSError, subprocess.SubprocessError) as exc:
            last_error = _note_exc(exc)

    return {
        "available": False,
        "tool": None,
        "count": 0,
        "entries": [],
        "error": last_error,
    }


def collect_host_health(
    target_path: str = ".",
    disk_warn: float = 80.0,
    disk_crit: float = 90.0,
    mem_warn: float = 85.0,
    mem_crit: float = 95.0,
    include_ports: bool = False,
    include_processes: bool = False,
) -> Dict[str, Any]:
    """Collects cross-platform host diagnostics and evaluates threshold alerts."""
    resolved_target = str(Path(target_path).resolve())
    usage = shutil.disk_usage(resolved_target)
    disk_percent = round((usage.used / usage.total) * 100.0, 2) if usage.total > 0 else 0.0
    disk_status = evaluate_threshold_status(disk_percent, disk_warn, disk_crit)
    inodes = collect_inode_usage(resolved_target, warn=disk_warn, crit=disk_crit)
    gib = 1024 ** 3

    disk_info: Dict[str, Any] = {
        "path": resolved_target,
        "total_gb": round(usage.total / gib, 2),
        "used_gb": round(usage.used / gib, 2),
        "free_gb": round(usage.free / gib, 2),
        "percent_used": disk_percent,
        "status": disk_status,
        "inodes": inodes,
    }

    cpu_count = os.cpu_count() or 1
    load_info: Optional[Dict[str, float]] = None
    if hasattr(os, "getloadavg"):
        try:
            l1, l5, l15 = os.getloadavg()
            load_info = {
                "1m": round(l1, 2),
                "5m": round(l5, 2),
                "15m": round(l15, 2),
                "per_cpu_1m": round(l1 / cpu_count, 2),
            }
        except OSError as exc:
            _ = _note_exc(exc)
            load_info = None

    mem_info = collect_memory_usage()
    if mem_info.get("available"):
        mem_info["status"] = evaluate_threshold_status(float(mem_info["percent_used"]), mem_warn, mem_crit)

    services = collect_failed_services()
    ports = collect_listening_ports() if include_ports else None
    processes = collect_process_summary() if include_processes else None
    uptime_sec = collect_uptime_seconds()

    alerts: List[Dict[str, str]] = []
    if disk_status == "critical":
        alerts.append({
            "id": "HEALTH-DISK-CRIT",
            "severity": "CRITICAL",
            "message": f"Disk usage at {disk_percent}% (>= {disk_crit}%) on {resolved_target}",
        })
    elif disk_status == "warning":
        alerts.append({
            "id": "HEALTH-DISK-WARN",
            "severity": "WARNING",
            "message": f"Disk usage at {disk_percent}% (>= {disk_warn}%) on {resolved_target}",
        })

    if inodes.get("available"):
        if inodes["status"] == "critical":
            alerts.append({
                "id": "HEALTH-INODE-CRIT",
                "severity": "CRITICAL",
                "message": f"Inode usage at {inodes['percent_used']}% (>= {disk_crit}%) on {resolved_target}",
            })
        elif inodes["status"] == "warning":
            alerts.append({
                "id": "HEALTH-INODE-WARN",
                "severity": "WARNING",
                "message": f"Inode usage at {inodes['percent_used']}% (>= {disk_warn}%) on {resolved_target}",
            })

    if mem_info.get("available"):
        mem_status = mem_info["status"]
        if mem_status == "critical":
            alerts.append({
                "id": "HEALTH-MEM-CRIT",
                "severity": "CRITICAL",
                "message": f"Memory usage at {mem_info['percent_used']}% (>= {mem_crit}%)",
            })
        elif mem_status == "warning":
            alerts.append({
                "id": "HEALTH-MEM-WARN",
                "severity": "WARNING",
                "message": f"Memory usage at {mem_info['percent_used']}% (>= {mem_warn}%)",
            })

    if load_info is not None:
        per_cpu = load_info["per_cpu_1m"]
        if per_cpu >= 2.0:
            alerts.append({
                "id": "HEALTH-LOAD-CRIT",
                "severity": "CRITICAL",
                "message": f"CPU load average per core is {per_cpu} (1m load {load_info['1m']} / {cpu_count} cores)",
            })
        elif per_cpu >= 1.0:
            alerts.append({
                "id": "HEALTH-LOAD-WARN",
                "severity": "WARNING",
                "message": f"CPU load average per core is {per_cpu} (1m load {load_info['1m']} / {cpu_count} cores)",
            })

    if services.get("failed_count", 0) > 0:
        svc_sev = "CRITICAL" if services.get("manager") == "systemd" else "WARNING"
        alerts.append({
            "id": "HEALTH-SERVICES-FAIL",
            "severity": svc_sev,
            "message": f"{services['failed_count']} failed {services['manager']} unit(s): {', '.join(services['failed_units'])}",
        })

    if processes is not None:
        if processes.get("zombie_count", 0) >= 5:
            alerts.append({
                "id": "HEALTH-ZOMBIES-WARN",
                "severity": "WARNING",
                "message": f"{processes['zombie_count']} zombie (Z) processes detected",
            })
        fd_usage = processes.get("fd_usage")
        if fd_usage:
            fd_pct = float(fd_usage["percent_used"])
            if fd_pct >= 90.0:
                alerts.append({
                    "id": "HEALTH-FD-CRIT",
                    "severity": "CRITICAL",
                    "message": f"Kernel file descriptor usage at {fd_pct}% ({fd_usage['allocated']}/{fd_usage['max']})",
                })
            elif fd_pct >= 80.0:
                alerts.append({
                    "id": "HEALTH-FD-WARN",
                    "severity": "WARNING",
                    "message": f"Kernel file descriptor usage at {fd_pct}% ({fd_usage['allocated']}/{fd_usage['max']})",
                })

    if any(a["severity"] == "CRITICAL" for a in alerts):
        overall_status = "fail"
    elif any(a["severity"] == "WARNING" for a in alerts):
        overall_status = "warn"
    else:
        overall_status = "pass"

    report: Dict[str, Any] = {
        "status": overall_status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": cpu_count,
        "uptime_seconds": uptime_sec,
        "load_average": load_info,
        "disk": disk_info,
        "memory": mem_info,
        "services": services,
        "alerts": alerts,
    }
    if ports is not None:
        report["listening_ports"] = ports
    if processes is not None:
        report["processes"] = processes
    return report


# ---------------------------------------------------------------------------
# 2. Network, DNS & TLS Health Checks
# ---------------------------------------------------------------------------

def parse_host_port(spec: str, default_port: int = 443) -> Tuple[str, int]:
    """Parses host, host:port, or [ipv6]:port into (host, port)."""
    raw = spec.strip()
    if not raw:
        raise ValueError("Host specification cannot be empty")

    bracket_match = re.match(r"^\[([^\]]+)\](?::(\d+))?$", raw)
    if bracket_match:
        host = bracket_match.group(1).strip()
        port = int(bracket_match.group(2)) if bracket_match.group(2) else default_port
    elif raw.count(":") == 1:
        host_part, port_part = raw.split(":", 1)
        host = host_part.strip()
        if not port_part.isdigit():
            raise ValueError(f"Invalid port in host specification: {spec}")
        port = int(port_part)
    else:
        host = raw
        port = default_port

    if not host:
        raise ValueError(f"Missing hostname in specification: {spec}")
    if port < 1 or port > 65535:
        raise ValueError(f"Port out of valid range (1-65535): {port}")
    return host, port


def evaluate_tls_expiry(
    not_after: datetime,
    now: Optional[datetime] = None,
    warn_days: int = 30,
    crit_days: int = 7,
) -> Dict[str, Any]:
    """Evaluates certificate expiration timestamp against warning and critical thresholds."""
    not_after_utc = not_after.astimezone(timezone.utc) if not_after.tzinfo else not_after.replace(tzinfo=timezone.utc)
    now_ref = now or datetime.now(timezone.utc)
    now_utc = now_ref.astimezone(timezone.utc) if now_ref.tzinfo else now_ref.replace(tzinfo=timezone.utc)

    days_remaining = round((not_after_utc - now_utc).total_seconds() / 86400.0, 2)
    expired = days_remaining <= 0

    if expired or days_remaining <= crit_days:
        status = "fail"
    elif days_remaining <= warn_days:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "expired": expired,
        "days_remaining": days_remaining,
        "not_after": not_after_utc.isoformat(),
    }


def _flatten_cert_name(entries: Any) -> str:
    """Formats an OpenSSL certificate subject/issuer tuple into a readable string."""
    parts: List[str] = []
    for rdn in entries or ():
        for key, val in rdn:
            parts.append(f"{key}={val}")
    return ", ".join(parts)


def check_tls_certificate(
    host_spec: str,
    timeout: float = 5.0,
    warn_days: int = 30,
    crit_days: int = 7,
) -> Dict[str, Any]:
    """Inspects remote TLS certificate validity, expiration, SANs, and protocol version."""
    host, port = parse_host_port(host_spec, default_port=443)
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert() or {}
                tls_version = ssock.version() or "unknown"

        not_after_raw = cert.get("notAfter")
        if not not_after_raw:
            return {
                "status": "fail",
                "host": host,
                "port": port,
                "tls_version": tls_version,
                "error": "Peer certificate missing notAfter field",
            }

        not_after_dt = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        expiry = evaluate_tls_expiry(not_after_dt, warn_days=warn_days, crit_days=crit_days)
        sans = [val for kind, val in cert.get("subjectAltName", ()) if kind == "DNS"]

        status = expiry["status"]
        legacy_protocol = tls_version in {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}
        if legacy_protocol:
            status = "fail"

        return {
            "status": status,
            "host": host,
            "port": port,
            "tls_version": tls_version,
            "legacy_protocol": legacy_protocol,
            "subject": _flatten_cert_name(cert.get("subject")),
            "issuer": _flatten_cert_name(cert.get("issuer")),
            "san_dns": sans[:20],
            "expired": expiry["expired"],
            "days_remaining": expiry["days_remaining"],
            "not_after": expiry["not_after"],
        }
    except (OSError, ssl.SSLError, ValueError) as exc:
        return {
            "status": "fail",
            "host": host,
            "port": port,
            "error": _note_exc(exc),
        }


def check_tcp_port(host_spec: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Tests TCP port reachability and measures connection latency in milliseconds."""
    host, port = parse_host_port(host_spec, default_port=443)
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency_ms = round((time.monotonic() - start) * 1000.0, 2)
        return {
            "status": "pass",
            "host": host,
            "port": port,
            "reachable": True,
            "latency_ms": latency_ms,
        }
    except OSError as exc:
        latency_ms = round((time.monotonic() - start) * 1000.0, 2)
        return {
            "status": "fail",
            "host": host,
            "port": port,
            "reachable": False,
            "latency_ms": latency_ms,
            "error": _note_exc(exc),
        }


def check_dns_resolution(hostname: str) -> Dict[str, Any]:
    """Resolves A/AAAA records for a hostname and measures lookup latency."""
    host = hostname.strip()
    if not host:
        raise ValueError("Hostname cannot be empty")
    start = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, None)
        latency_ms = round((time.monotonic() - start) * 1000.0, 2)
        ipv4 = sorted({info[4][0] for info in infos if info[0] == socket.AF_INET})
        ipv6 = sorted({info[4][0] for info in infos if info[0] == socket.AF_INET6})
        addresses = ipv4 + ipv6
        return {
            "status": "pass" if addresses else "fail",
            "hostname": host,
            "addresses": addresses,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "latency_ms": latency_ms,
        }
    except socket.gaierror as exc:
        latency_ms = round((time.monotonic() - start) * 1000.0, 2)
        return {
            "status": "fail",
            "hostname": host,
            "addresses": [],
            "ipv4": [],
            "ipv6": [],
            "latency_ms": latency_ms,
            "error": _note_exc(exc),
        }


# ---------------------------------------------------------------------------
# 3. Static Config & Ops Script Hardening Auditor
# ---------------------------------------------------------------------------

def _make_finding(
    rule_id: str,
    severity: str,
    category: str,
    file_label: str,
    line: int,
    snippet: str,
    message: str,
    remediation: str,
) -> Dict[str, Any]:
    return {
        "id": rule_id,
        "severity": severity,
        "category": category,
        "file": file_label,
        "line": line,
        "snippet": snippet.strip()[:120],
        "message": message,
        "remediation": remediation,
    }


def _strip_inline_comment(line: str) -> str:
    """Strips # comments outside single/double quotes."""
    in_single = False
    in_double = False
    escaped = False
    for idx, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and not in_single:
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:idx]
    return line


def _extract_active_shell_lines(content: str) -> List[Tuple[int, str]]:
    """Returns (line_no, line_text) excluding comments, blank lines, and heredoc bodies."""
    active: List[Tuple[int, str]] = []
    heredoc_delim: Optional[str] = None
    strip_tabs = False
    heredoc_re = re.compile(r"<<(-?)\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?(?:\s|$|;|#)")

    for idx, raw_line in enumerate(content.splitlines(), 1):
        if heredoc_delim is not None:
            candidate = raw_line.lstrip("\t") if strip_tabs else raw_line
            if candidate.strip() == heredoc_delim:
                heredoc_delim = None
                strip_tabs = False
            continue

        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        code_part = _strip_inline_comment(raw_line).strip()
        if not code_part:
            continue

        active.append((idx, code_part))
        hd_match = heredoc_re.search(code_part)
        if hd_match:
            strip_tabs = hd_match.group(1) == "-"
            heredoc_delim = hd_match.group(2)

    return active


def _extract_active_ps1_lines(content: str) -> List[Tuple[int, str]]:
    """Returns (line_no, line_text) excluding comments, block comments, and here-strings."""
    active: List[Tuple[int, str]] = []
    in_block_comment = False
    herestring_end: Optional[str] = None

    for idx, raw_line in enumerate(content.splitlines(), 1):
        if herestring_end is not None:
            if raw_line.startswith(herestring_end):
                herestring_end = None
            continue

        stripped = raw_line.strip()
        if in_block_comment:
            if "#>" in stripped:
                in_block_comment = False
            continue

        if stripped.startswith("<#"):
            if "#>" not in stripped[2:]:
                in_block_comment = True
            continue

        if not stripped or stripped.startswith("#"):
            continue

        code_part = _strip_inline_comment(raw_line).strip()
        if not code_part:
            continue

        active.append((idx, code_part))
        if re.search(r'@"(\s*#.*)?$', code_part):
            herestring_end = '"@'
        elif re.search(r"@'(\s*#.*)?$", code_part):
            herestring_end = "'@"

    return active


def _audit_ssh_config(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    rules = [
        (
            "SYS-SSH-ROOT",
            "CRITICAL",
            re.compile(r"^\s*PermitRootLogin\s+yes\b", re.IGNORECASE),
            "SSH root login is enabled (PermitRootLogin yes)",
            "Set 'PermitRootLogin no' in sshd_config.",
        ),
        (
            "SYS-SSH-ROOT-PROHIBIT",
            "WARNING",
            re.compile(r"^\s*PermitRootLogin\s+without-password\b", re.IGNORECASE),
            "SSH uses legacy PermitRootLogin without-password directive",
            "Set 'PermitRootLogin no' (or 'prohibit-password' only if automated SSH keys are mandatory).",
        ),
        (
            "SYS-SSH-PASS",
            "HIGH",
            re.compile(r"^\s*PasswordAuthentication\s+yes\b", re.IGNORECASE),
            "SSH password authentication is enabled (brute-force exposure)",
            "Set 'PasswordAuthentication no' and enforce public-key authentication.",
        ),
        (
            "SYS-SSH-EMPTY-PASS",
            "CRITICAL",
            re.compile(r"^\s*PermitEmptyPasswords\s+yes\b", re.IGNORECASE),
            "SSH permits empty passwords (PermitEmptyPasswords yes)",
            "Set 'PermitEmptyPasswords no'.",
        ),
        (
            "SYS-SSH-PROTO1",
            "CRITICAL",
            re.compile(r"^\s*Protocol\s+(?:1|1\s*,\s*2|2\s*,\s*1)\b", re.IGNORECASE),
            "Legacy insecure SSH Protocol 1 enabled",
            "Remove Protocol 1 and require SSH Protocol 2 only.",
        ),
        (
            "SYS-SSH-X11",
            "WARNING",
            re.compile(r"^\s*X11Forwarding\s+yes\b", re.IGNORECASE),
            "SSH X11 forwarding is enabled",
            "Set 'X11Forwarding no' unless interactive GUI forwarding is required.",
        ),
    ]

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        for rule_id, severity, pattern, msg, rem in rules:
            if pattern.search(active):
                findings.append(_make_finding(rule_id, severity, "SSH Hardening", file_label, idx, active, msg, rem))
    return findings


def _audit_systemd_unit(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    section = ""
    service_lines: List[Tuple[int, str]] = []
    exec_line = 1
    has_exec = False
    user_val: Optional[str] = None
    user_line = 1
    unit_type: Optional[str] = None
    restart_val: Optional[str] = None
    has_sandbox = False

    for idx, raw_line in enumerate(content.splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        sec_match = re.match(r"^\[([^\]]+)\]$", stripped)
        if sec_match:
            section = sec_match.group(1).strip().lower()
            continue
        if section != "service":
            continue

        service_lines.append((idx, stripped))
        if "=" not in stripped:
            continue
        key, val = [part.strip() for part in stripped.split("=", 1)]
        key_l = key.lower()
        val_l = val.lower()

        if key_l == "execstart" and val:
            has_exec = True
            exec_line = idx
        elif key_l == "user":
            user_val = val_l
            user_line = idx
        elif key_l == "type":
            unit_type = val_l
        elif key_l == "restart":
            restart_val = val_l
        elif key_l == "umask" and val_l in {"0000", "0002", "000", "002"}:
            findings.append(
                _make_finding(
                    "SYS-UNIT-UMASK",
                    "HIGH",
                    "Systemd Hardening",
                    file_label,
                    idx,
                    stripped,
                    f"Overly permissive systemd UMask={val}",
                    "Set 'UMask=0027' or 'UMask=0077' inside [Service].",
                )
            )
        elif (
            (key_l == "nonewprivileges" and val_l in {"true", "yes", "1"})
            or (key_l == "protectsystem" and val_l in {"strict", "full", "true", "yes"})
            or (key_l == "privatetmp" and val_l in {"true", "yes", "1"})
        ):
            has_sandbox = True

    if has_exec:
        if user_val is None or user_val in {"root", "0"}:
            snippet = f"User={user_val}" if user_val is not None else "Missing User= in [Service]"
            findings.append(
                _make_finding(
                    "SYS-UNIT-ROOT",
                    "HIGH",
                    "Systemd Hardening",
                    file_label,
                    user_line if user_val is not None else exec_line,
                    snippet,
                    "Systemd service runs as root or omits dedicated non-root User=",
                    "Set 'User=<service-user>' and 'Group=<service-group>' in [Service].",
                )
            )

        if unit_type != "oneshot" and (restart_val is None or restart_val == "no"):
            findings.append(
                _make_finding(
                    "SYS-UNIT-NO-RESTART",
                    "WARNING",
                    "Systemd Reliability",
                    file_label,
                    exec_line,
                    f"Type={unit_type or 'simple'} without Restart=",
                    "Long-running systemd service lacks automatic restart policy",
                    "Add 'Restart=on-failure' and 'RestartSec=5s' for resilient recovery.",
                )
            )

        if not has_sandbox:
            findings.append(
                _make_finding(
                    "SYS-UNIT-SANDBOX",
                    "WARNING",
                    "Systemd Hardening",
                    file_label,
                    exec_line,
                    "Missing NoNewPrivileges/ProtectSystem/PrivateTmp",
                    "Systemd service lacks basic sandboxing directives",
                    "Add 'NoNewPrivileges=true', 'ProtectSystem=strict', and 'PrivateTmp=true'.",
                )
            )

    return findings


def _audit_nginx_config(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    has_ssl_listen = False
    ssl_listen_line = 1
    has_hsts = "strict-transport-security" in content.lower()

    legacy_tls_re = re.compile(r"\b(?:SSLv2|SSLv3|TLSv1(?:\.0)?(?![.\d])|TLSv1\.1)\b", re.IGNORECASE)

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue

        if re.search(r"^\s*ssl_protocols\b", active, re.IGNORECASE) and legacy_tls_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-NGINX-TLS-LEGACY",
                    "CRITICAL",
                    "Reverse Proxy / TLS",
                    file_label,
                    idx,
                    active,
                    "Nginx enables deprecated SSL/TLS protocol versions",
                    "Restrict to 'ssl_protocols TLSv1.2 TLSv1.3;'.",
                )
            )

        if re.search(r"^\s*server_tokens\s+on\b", active, re.IGNORECASE):
            findings.append(
                _make_finding(
                    "SYS-NGINX-TOKENS",
                    "WARNING",
                    "Reverse Proxy Hardening",
                    file_label,
                    idx,
                    active,
                    "Nginx exposes server version banner (server_tokens on)",
                    "Set 'server_tokens off;'.",
                )
            )

        if re.search(r"^\s*autoindex\s+on\b", active, re.IGNORECASE):
            findings.append(
                _make_finding(
                    "SYS-NGINX-AUTOINDEX",
                    "HIGH",
                    "Reverse Proxy Hardening",
                    file_label,
                    idx,
                    active,
                    "Directory listing enabled in Nginx (autoindex on)",
                    "Set 'autoindex off;' or remove directive to prevent file enumeration.",
                )
            )

        if re.search(r"^\s*listen\s+[^;\n]*\bssl\b", active, re.IGNORECASE):
            has_ssl_listen = True
            ssl_listen_line = idx

    if has_ssl_listen and not has_hsts:
        findings.append(
            _make_finding(
                "SYS-NGINX-HSTS",
                "WARNING",
                "Reverse Proxy / TLS",
                file_label,
                ssl_listen_line,
                "TLS listener missing Strict-Transport-Security",
                "TLS virtual host omits HTTP Strict Transport Security (HSTS) header",
                "Add 'add_header Strict-Transport-Security \"max-age=63072000; includeSubDomains\" always;'.",
            )
        )

    return findings


def _audit_shell_script(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    first_line = content.splitlines()[0] if content.splitlines() else ""
    has_shebang = bool(re.match(r"^#!\s*/.*\b(?:ba|z|da|k)?sh\b", first_line))
    active_lines = _extract_active_shell_lines(content)

    has_strict_mode = any(
        re.search(r"\bset\s+(?:-[a-zA-Z]*e[a-zA-Z]*|-o\s+errexit)\b", line)
        for _, line in active_lines
    )
    if (has_shebang or len(active_lines) > 5) and len(active_lines) > 5 and not has_strict_mode:
        findings.append(
            _make_finding(
                "SYS-SH-STRICT-MODE",
                "WARNING",
                "Shell Safety",
                file_label,
                1,
                first_line or active_lines[0][1],
                "Shell script lacks strict fail-fast mode (set -e / set -euo pipefail)",
                "Add 'set -euo pipefail' near the top of the script.",
            )
        )

    curl_pipe_re = re.compile(r"(?:curl|wget)\b[^|;\n]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b")
    perm_world_re = re.compile(r"\bchmod\s+(?:-[a-zA-Z]+\s+)*(?:[0-7]?7{3}|a\+rwx|o\+r?w)\b")
    dangerous_rm_re = re.compile(
        r"\brm\s+(?:-[rRfF]+\s+|--(?:recursive|force)\s+)+"
        r"(?:(?:/\*?|/\s|~/?|\$HOME/?|\$\{HOME\}/?)(?:\s|$|;|&|\|)|[\"']?\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)/)"
    )
    sudo_pass_re = re.compile(r"\becho\b[^|;\n]*\|\s*sudo\s+-S\b")

    for idx, line in active_lines:
        if curl_pipe_re.search(line):
            findings.append(
                _make_finding(
                    "SYS-SH-CURL-PIPE",
                    "CRITICAL",
                    "Supply Chain / Shell Safety",
                    file_label,
                    idx,
                    line,
                    "Remote payload piped directly to shell interpreter",
                    "Download script to a verified temporary file, inspect/verify SHA-256 checksum, then execute.",
                )
            )
        if perm_world_re.search(line):
            findings.append(
                _make_finding(
                    "SYS-SH-PERM-WORLD",
                    "HIGH",
                    "Filesystem Permissions",
                    file_label,
                    idx,
                    line,
                    "chmod assigns world-writable file permissions (mode 777 or a+rwx)",
                    "Restrict permissions to least-privilege (e.g., 750/755 for executables, 640/644 for configs).",
                )
            )
        if dangerous_rm_re.search(line):
            findings.append(
                _make_finding(
                    "SYS-SH-DANGEROUS-RM",
                    "CRITICAL",
                    "Destructive Command Guard",
                    file_label,
                    idx,
                    line,
                    "Destructive recursive rm targets root/home or unguarded variable path",
                    "Guard variables with '${VAR:?}' and validate non-empty target directories before removal.",
                )
            )
        if sudo_pass_re.search(line):
            findings.append(
                _make_finding(
                    "SYS-SH-SUDO-PASS",
                    "CRITICAL",
                    "Credential Hygiene",
                    file_label,
                    idx,
                    line,
                    "Password piped via echo into sudo -S",
                    "Configure scoped NOPASSWD sudoers rules for specific commands instead of piping passwords.",
                )
            )

    return findings


def _audit_ps1_script(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    active_lines = _extract_active_ps1_lines(content)

    has_strict_mode = any(
        re.search(r"\$ErrorActionPreference\s*=|Set-StrictMode\b", line, re.IGNORECASE)
        for _, line in active_lines
    )
    if len(active_lines) > 5 and not has_strict_mode:
        findings.append(
            _make_finding(
                "SYS-PS-STRICT-MODE",
                "WARNING",
                "PowerShell Safety",
                file_label,
                1,
                active_lines[0][1],
                "PowerShell script lacks $ErrorActionPreference or Set-StrictMode",
                "Add \"$ErrorActionPreference = 'Stop'\" and \"Set-StrictMode -Version Latest\".",
            )
        )

    iex_web_re = re.compile(
        r"(?:irm|iwr|Invoke-RestMethod|Invoke-WebRequest)\b[^|;\n]*\|\s*(?:iex|Invoke-Expression)\b",
        re.IGNORECASE,
    )
    plain_cred_re = re.compile(
        r"ConvertTo-SecureString\b(?=[^\n]*-AsPlainText\b)(?=[^\n]*[\"'][^\"']+[\"'])",
        re.IGNORECASE,
    )

    for idx, line in active_lines:
        if iex_web_re.search(line):
            findings.append(
                _make_finding(
                    "SYS-PS-IEX-WEB",
                    "CRITICAL",
                    "Supply Chain / PowerShell Safety",
                    file_label,
                    idx,
                    line,
                    "Remote PowerShell payload piped directly to Invoke-Expression (iex)",
                    "Download script locally, validate Authenticode/SHA-256 hash, and execute explicitly.",
                )
            )
        if plain_cred_re.search(line):
            findings.append(
                _make_finding(
                    "SYS-PS-PLAINTEXT-CRED",
                    "HIGH",
                    "Credential Hygiene",
                    file_label,
                    idx,
                    line,
                    "Hardcoded plaintext secret passed to ConvertTo-SecureString -AsPlainText",
                    "Read secrets from SecretManagement vault, environment, or interactive Get-Credential.",
                )
            )

    return findings


def _audit_cron_file(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    has_path_env = False
    schedule_re = re.compile(
        r"^\s*(?:@(?:reboot|yearly|annually|monthly|weekly|daily|hourly)|"
        r"[0-9*,/-]+\s+[0-9*,/-]+\s+[0-9*,/-]+\s+[0-9*,/-]+\s+[0-9*,/-]+)\s+(.+)$"
    )
    curl_pipe_re = re.compile(r"(?:curl|wget)\b[^|;\n]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b")
    tmp_exec_re = re.compile(r"(?:^|\s)(?:/tmp/|/var/tmp/)[^\s;|&]+")

    relative_jobs: List[Tuple[int, str]] = []
    for idx, raw_line in enumerate(content.splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^PATH\s*=", stripped):
            has_path_env = True
            continue
        if curl_pipe_re.search(stripped):
            findings.append(
                _make_finding(
                    "SYS-CRON-CURL-PIPE",
                    "CRITICAL",
                    "Cron Security",
                    file_label,
                    idx,
                    stripped,
                    "Cron job pipes remote download directly into shell",
                    "Deploy versioned scripts to /usr/local/sbin with root-only write permissions.",
                )
            )
        if tmp_exec_re.search(stripped):
            findings.append(
                _make_finding(
                    "SYS-CRON-TMP-EXEC",
                    "HIGH",
                    "Cron Security",
                    file_label,
                    idx,
                    stripped,
                    "Cron job executes artifact from world-writable /tmp or /var/tmp",
                    "Move script to a dedicated non-world-writable directory such as /usr/local/sbin.",
                )
            )

        sched_match = schedule_re.match(stripped)
        if sched_match:
            cmd_part = sched_match.group(1).strip()
            first_token = cmd_part.split()[0]
            if not first_token.startswith("/") and "=" not in first_token:
                relative_jobs.append((idx, stripped))

    if relative_jobs and not has_path_env:
        first_idx, first_snippet = relative_jobs[0]
        findings.append(
            _make_finding(
                "SYS-CRON-NO-PATH",
                "WARNING",
                "Cron Reliability",
                file_label,
                first_idx,
                first_snippet,
                "Cron job invokes relative command without explicit PATH= environment header",
                "Define 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' or use absolute paths.",
            )
        )

    return findings


def _audit_sysctl_config(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    redirect_re = re.compile(
        r"^\s*net\.ipv[46]\.conf\.[^=\s]+\.(?:accept_redirects|accept_source_route)\s*=\s*1\b"
    )
    kptr_re = re.compile(r"^\s*(?:kernel\.kptr_restrict|kernel\.randomize_va_space)\s*=\s*0\b")

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if redirect_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-SYSCTL-REDIRECT",
                    "WARNING",
                    "Kernel Network Hardening",
                    file_label,
                    idx,
                    active,
                    "ICMP redirects or source routing enabled in sysctl",
                    "Set accept_redirects=0 and accept_source_route=0.",
                )
            )
        if kptr_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-SYSCTL-KPTR",
                    "WARNING",
                    "Kernel Hardening",
                    file_label,
                    idx,
                    active,
                    "Kernel pointer restriction or ASLR disabled in sysctl",
                    "Set kernel.kptr_restrict=1 (or 2) and kernel.randomize_va_space=2.",
                )
            )
    return findings


def _audit_terraform(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    block_stack: List[Dict[str, Any]] = []
    open_cidr_re = re.compile(r'"(?:0\.0\.0\.0/0|::/0)"')
    port_re = re.compile(r"\b(?:from_port|to_port|port)\s*=\s*(\d+)\b")
    proto_all_re = re.compile(r'\bprotocol\s*=\s*"-1"')
    unencrypted_re = re.compile(
        r"^\s*(?:(?:storage_)?encrypted\s*=\s*false|publicly_accessible\s*=\s*true)\b"
    )

    for idx, raw_line in enumerate(content.splitlines(), 1):
        cleaned = _strip_inline_comment(raw_line)
        cleaned = re.sub(r"//.*$", "", cleaned).strip()
        if not cleaned:
            continue

        if unencrypted_re.search(cleaned):
            findings.append(
                _make_finding(
                    "SYS-TF-UNENCRYPTED",
                    "HIGH",
                    "IaC Security (Terraform)",
                    file_label,
                    idx,
                    cleaned,
                    "Terraform resource disables storage encryption or enables public accessibility",
                    "Enable encryption (encrypted = true) and restrict publicly_accessible = false.",
                )
            )

        open_braces = cleaned.count("{")
        close_braces = cleaned.count("}")

        if open_braces > 0:
            for _ in range(open_braces):
                block_stack.append({
                    "start_line": idx,
                    "has_open_cidr": False,
                    "cidr_line": idx,
                    "cidr_snippet": "",
                    "ports": set(),
                    "proto_all": False,
                })

        target_block = block_stack[-1] if block_stack else None
        if target_block is not None:
            if open_cidr_re.search(cleaned):
                target_block["has_open_cidr"] = True
                target_block["cidr_line"] = idx
                target_block["cidr_snippet"] = cleaned
            for pm in port_re.finditer(cleaned):
                target_block["ports"].add(pm.group(1))
            if proto_all_re.search(cleaned):
                target_block["proto_all"] = True

        if close_braces > 0:
            for _ in range(close_braces):
                if not block_stack:
                    break
                finished = block_stack.pop()
                if finished["has_open_cidr"]:
                    exposed_sensitive = finished["ports"] & SENSITIVE_TF_PORTS
                    wildcard_all = "0" in finished["ports"] and (
                        "65535" in finished["ports"] or finished["proto_all"]
                    )
                    if exposed_sensitive or wildcard_all:
                        port_desc = ", ".join(sorted(exposed_sensitive)) if exposed_sensitive else "all ports"
                        findings.append(
                            _make_finding(
                                "SYS-TF-OPEN-CIDR",
                                "CRITICAL",
                                "IaC Network Security (Terraform)",
                                file_label,
                                finished["cidr_line"],
                                finished["cidr_snippet"],
                                f"Terraform security rule opens sensitive port(s) ({port_desc}) to 0.0.0.0/0 or ::/0",
                                "Restrict cidr_blocks to trusted VPC CIDRs, bastion hosts, or VPN ranges.",
                            )
                        )

    return findings


def _audit_ansible(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    no_tls_re = re.compile(r"^\s*validate_certs\s*:\s*(?:false|no)\b", re.IGNORECASE)
    ignore_err_re = re.compile(r"^\s*ignore_errors\s*:\s*(?:true|yes)\b", re.IGNORECASE)

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if no_tls_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-ANSIBLE-NO-TLS",
                    "HIGH",
                    "IaC Security (Ansible)",
                    file_label,
                    idx,
                    active,
                    "Ansible task disables TLS certificate verification (validate_certs: false)",
                    "Remove validate_certs: false or configure trusted CA certificates.",
                )
            )
        if ignore_err_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-ANSIBLE-IGNORE-ERR",
                    "WARNING",
                    "IaC Reliability (Ansible)",
                    file_label,
                    idx,
                    active,
                    "Ansible task suppresses failures via ignore_errors: true",
                    "Use explicit 'failed_when:' conditions instead of blanket ignore_errors.",
                )
            )
    return findings


def _audit_caddyfile(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    auto_https_off_re = re.compile(r"^\s*auto_https\s+off\b", re.IGNORECASE)
    skip_verify_re = re.compile(r"\btls_insecure_skip_verify\b", re.IGNORECASE)
    http_only_re = re.compile(r"\bhttp://(?!localhost\b|127\.0\.0\.1\b|\[::1\])", re.IGNORECASE)
    file_browse_re = re.compile(r"^\s*file_server\b[^\n]*\bbrowse\b", re.IGNORECASE)

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if auto_https_off_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-CADDY-AUTO-HTTPS-OFF",
                    "HIGH",
                    "Reverse Proxy / TLS (Caddy)",
                    file_label,
                    idx,
                    active,
                    "Caddy disables automatic HTTPS (auto_https off)",
                    "Keep automatic HTTPS enabled or explicitly configure TLS certificates.",
                )
            )
        if skip_verify_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-CADDY-INSECURE-SKIP-VERIFY",
                    "CRITICAL",
                    "Reverse Proxy / TLS (Caddy)",
                    file_label,
                    idx,
                    active,
                    "Caddy disables upstream TLS certificate verification (tls_insecure_skip_verify)",
                    "Remove tls_insecure_skip_verify and configure trusted upstream CA certificates.",
                )
            )
        if http_only_re.search(active) and not active.lower().startswith("reverse_proxy"):
            findings.append(
                _make_finding(
                    "SYS-CADDY-HTTP-ONLY",
                    "WARNING",
                    "Reverse Proxy / TLS (Caddy)",
                    file_label,
                    idx,
                    active,
                    "Plaintext http:// site address configured for non-local host",
                    "Serve external hosts over HTTPS instead of explicit http://.",
                )
            )
        if file_browse_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-CADDY-FILE-BROWSE",
                    "HIGH",
                    "Reverse Proxy Hardening (Caddy)",
                    file_label,
                    idx,
                    active,
                    "Directory browsing enabled in Caddy (file_server browse)",
                    "Remove 'browse' from file_server unless intentionally publishing a file index.",
                )
            )
    return findings


def _audit_k8s_manifest(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    priv_re = re.compile(r"^\s*privileged\s*:\s*true\b", re.IGNORECASE)
    host_ns_re = re.compile(r"^\s*(?:hostNetwork|hostPID|hostIPC)\s*:\s*true\b", re.IGNORECASE)
    docker_sock_re = re.compile(r"/var/run/docker\.sock")
    run_root_re = re.compile(r"^\s*(?:runAsUser\s*:\s*0|runAsNonRoot\s*:\s*false)\b", re.IGNORECASE)

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if priv_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-PRIVILEGED",
                    "CRITICAL",
                    "Kubernetes Security",
                    file_label,
                    idx,
                    active,
                    "Kubernetes container runs in privileged mode (privileged: true)",
                    "Set 'privileged: false' and grant only minimal Linux capabilities if required.",
                )
            )
        if host_ns_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-HOST-NS",
                    "HIGH",
                    "Kubernetes Security",
                    file_label,
                    idx,
                    active,
                    "Kubernetes pod shares host network, PID, or IPC namespace",
                    "Remove hostNetwork/hostPID/hostIPC: true to preserve pod isolation.",
                )
            )
        if docker_sock_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-DOCKER-SOCK",
                    "CRITICAL",
                    "Kubernetes Security",
                    file_label,
                    idx,
                    active,
                    "Host Docker socket (/var/run/docker.sock) mounted into container",
                    "Avoid mounting docker.sock; use rootless builds (Kaniko/BuildKit) instead.",
                )
            )
        if run_root_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-RUN-AS-ROOT",
                    "HIGH",
                    "Kubernetes Security",
                    file_label,
                    idx,
                    active,
                    "Kubernetes pod/container configured to run as root (UID 0)",
                    "Set 'runAsNonRoot: true' and an unprivileged 'runAsUser' (e.g., 10001).",
                )
            )

    kind_match = re.search(
        r"^\s*kind\s*:\s*(Deployment|DaemonSet|StatefulSet|Pod|Job|CronJob)\b",
        content,
        re.MULTILINE,
    )
    if kind_match and re.search(r"^\s*containers\s*:", content, re.MULTILINE):
        if not re.search(r"^\s*limits\s*:", content, re.MULTILINE):
            findings.append(
                _make_finding(
                    "SYS-K8S-NO-LIMITS",
                    "WARNING",
                    "Kubernetes Reliability",
                    file_label,
                    1,
                    f"kind: {kind_match.group(1)} missing resources.limits",
                    "Kubernetes workload lacks CPU/memory resource limits",
                    "Define 'resources.limits.cpu' and 'resources.limits.memory' to prevent noisy-neighbor OOMs.",
                )
            )

    return findings


def _audit_compose_manifest(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    priv_re = re.compile(r"^\s*privileged\s*:\s*true\b", re.IGNORECASE)
    host_net_re = re.compile(r"^\s*network_mode\s*:\s*[\"']?host[\"']?\b", re.IGNORECASE)
    docker_sock_re = re.compile(r"/var/run/docker\.sock")
    sensitive_port_re = re.compile(
        r"^\s*-\s*[\"']?(?:(?:0\.0\.0\.0|\[::\]):)?(?:(?:5432|3306|6379|27017|2375):\d+|\d+:(?:5432|3306|6379|27017|2375))(?:/(?:tcp|udp))?[\"']?\s*$"
    )

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if priv_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-PRIVILEGED",
                    "CRITICAL",
                    "Container Compose Security",
                    file_label,
                    idx,
                    active,
                    "Docker Compose service runs in privileged mode (privileged: true)",
                    "Remove 'privileged: true' and use explicit least-privilege cap_add if needed.",
                )
            )
        if host_net_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-HOST-NS",
                    "HIGH",
                    "Container Compose Security",
                    file_label,
                    idx,
                    active,
                    "Docker Compose service uses host network namespace (network_mode: host)",
                    "Use an isolated user-defined bridge network instead of network_mode: host.",
                )
            )
        if docker_sock_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-K8S-DOCKER-SOCK",
                    "CRITICAL",
                    "Container Compose Security",
                    file_label,
                    idx,
                    active,
                    "Host Docker socket (/var/run/docker.sock) mounted into service",
                    "Avoid mounting docker.sock or isolate behind a read-only socket proxy.",
                )
            )
        if sensitive_port_re.search(active) and not re.search(r"(?:127\.0\.0\.1|::1|localhost):", active):
            findings.append(
                _make_finding(
                    "SYS-COMPOSE-PORT-WILDCARD",
                    "WARNING",
                    "Container Compose Network",
                    file_label,
                    idx,
                    active,
                    "Docker Compose binds sensitive DB/daemon port on all host interfaces",
                    "Bind to loopback ('127.0.0.1:<port>:<port>') or keep internal on a private Docker network.",
                )
            )
    return findings


def _audit_sudoers(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    nopasswd_all_re = re.compile(r"\bNOPASSWD\s*:\s*ALL\b")
    nopasswd_shell_re = re.compile(
        r"\bNOPASSWD\s*:[^\n]*(?:^|[\s,/])(?:vim|vi|nano|less|more|find|awk|python3?|perl|ruby|bash|sh|tar|env)\b"
    )
    has_use_pty = False

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if re.match(r"^\s*Defaults\b[^\n]*\buse_pty\b", active):
            has_use_pty = True
        if nopasswd_all_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-SUDO-NOPASSWD-ALL",
                    "CRITICAL",
                    "Privilege Escalation (Sudoers)",
                    file_label,
                    idx,
                    active,
                    "Unrestricted passwordless sudo (NOPASSWD: ALL)",
                    "Restrict sudoers rules to explicit, absolute command paths and require authentication.",
                )
            )
        elif nopasswd_shell_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-SUDO-WILDCARD-SHELL",
                    "HIGH",
                    "Privilege Escalation (Sudoers)",
                    file_label,
                    idx,
                    active,
                    "NOPASSWD grants a binary with trivial root shell escape (GTFOBins risk)",
                    "Replace with a narrowly scoped wrapper script instead of granting editors/interpreters.",
                )
            )

    if Path(file_label).name.lower() == "sudoers" and not has_use_pty:
        findings.append(
            _make_finding(
                "SYS-SUDO-NO-USE-PTY",
                "WARNING",
                "Privilege Escalation (Sudoers)",
                file_label,
                1,
                "Missing 'Defaults use_pty'",
                "Primary sudoers file omits 'Defaults use_pty' (TTY session hijacking mitigation)",
                "Add 'Defaults use_pty' to /etc/sudoers via visudo.",
            )
        )
    return findings


def _audit_firewall(content: str, file_label: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    default_accept_re = re.compile(
        r"(?:^\s*:INPUT\s+ACCEPT\b|\bhook\s+input\b[^\n]*\bpolicy\s+accept\b)",
        re.IGNORECASE,
    )
    iptables_open_re = re.compile(
        r"-(?:A|I)\s+INPUT\b[^\n]*--dport\s+(?:22|3389|5432|3306|6379|27017)\b[^\n]*-j\s+ACCEPT\b",
        re.IGNORECASE,
    )
    nft_open_re = re.compile(
        r"\b(?:tcp\s+)?dport\b[^\n]*\b(?:22|3389|5432|3306|6379|27017)\b[^\n]*\baccept\b",
        re.IGNORECASE,
    )

    for idx, raw_line in enumerate(content.splitlines(), 1):
        active = _strip_inline_comment(raw_line).strip()
        if not active:
            continue
        if default_accept_re.search(active):
            findings.append(
                _make_finding(
                    "SYS-FW-DEFAULT-ACCEPT",
                    "HIGH",
                    "Firewall Hardening",
                    file_label,
                    idx,
                    active,
                    "Firewall INPUT chain defaults to ACCEPT policy",
                    "Enforce default-deny ('policy drop' / ':INPUT DROP') after allowing established & SSH rules.",
                )
            )
        if iptables_open_re.search(active):
            has_source = bool(re.search(r"(?:^|\s)(?:-s|--source)\s+\S+", active))
            open_world = bool(re.search(r"(?:0\.0\.0\.0/0|::/0)", active))
            if open_world or not has_source:
                findings.append(
                    _make_finding(
                        "SYS-FW-OPEN-MGMT",
                        "CRITICAL",
                        "Firewall Hardening",
                        file_label,
                        idx,
                        active,
                        "Firewall rule allows unrestricted source access to sensitive admin/DB port",
                        "Scope ingress rule with an explicit trusted source CIDR (-s <trusted-cidr>).",
                    )
                )
        elif nft_open_re.search(active):
            has_saddr = bool(re.search(r"\bsaddr\b", active))
            open_world = bool(re.search(r"(?:0\.0\.0\.0/0|::/0)", active))
            if open_world or not has_saddr:
                findings.append(
                    _make_finding(
                        "SYS-FW-OPEN-MGMT",
                        "CRITICAL",
                        "Firewall Hardening",
                        file_label,
                        idx,
                        active,
                        "nftables rule allows unrestricted source access to sensitive admin/DB port",
                        "Restrict nftables rule with 'ip saddr <trusted-cidr>'.",
                    )
                )
    return findings


def _parse_ignore_directives(content: str) -> Dict[int, Set[str]]:
    """Parses '# sysadmin-ignore: RULE1,RULE2' inline or next-line suppression comments."""
    ignores: Dict[int, Set[str]] = {}
    ignore_re = re.compile(r"#\s*sysadmin-ignore\s*:\s*([A-Za-z0-9_,\s-]+)", re.IGNORECASE)
    for idx, raw_line in enumerate(content.splitlines(), 1):
        match = ignore_re.search(raw_line)
        if not match:
            continue
        rules = {tok.strip().upper() for tok in match.group(1).split(",") if tok.strip()}
        if not rules:
            continue
        before_comment = raw_line[: match.start()].strip()
        target_line = idx if before_comment else (idx + 1)
        ignores.setdefault(target_line, set()).update(rules)
    return ignores


def compute_finding_fingerprint(finding: Dict[str, Any]) -> str:
    """Computes a deterministic 16-hex-char fingerprint for baseline diffing."""
    raw = f"{finding.get('id', '')}|{finding.get('file', '')}|{finding.get('snippet', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _classify_auditable_file(file_path: Path, content: str) -> Optional[str]:
    """Determines config/script audit category from filename, parent dir, and content."""
    name_l = file_path.name.lower()
    ext_l = file_path.suffix.lower()
    parent_l = file_path.parent.name.lower()

    if name_l == "sshd_config" or ("sshd" in name_l and ext_l == ".conf"):
        return "ssh"
    if ext_l == ".service":
        return "systemd"
    if "sysctl" in name_l and ext_l == ".conf":
        return "sysctl"
    if name_l == "caddyfile" or name_l.startswith("caddyfile.") or ext_l == ".caddy":
        return "caddy"
    if (name_l == "sudoers" or parent_l == "sudoers.d" or "sudoers" in name_l) and ext_l not in {
        ".py",
        ".md",
        ".json",
        ".txt",
    }:
        return "sudoers"
    if ext_l == ".nft" or ("nftables" in name_l and ext_l == ".conf") or (
        ("ufw" in name_l or "iptables" in name_l) and ext_l in {".rules", ".conf"}
    ):
        return "firewall"
    if (
        "nginx" in name_l
        or ext_l == ".vhost"
        or (
            ext_l == ".conf"
            and any(tok in content for tok in ("ssl_protocols", "server_tokens", "proxy_pass", "server {"))
        )
    ):
        return "nginx"
    if ext_l in {".sh", ".bash", ".zsh"}:
        return "shell"
    if ext_l == ".ps1":
        return "powershell"
    if name_l.startswith("crontab") or ext_l == ".cron" or parent_l in {
        "cron.d",
        "cron.daily",
        "cron.hourly",
        "cron.weekly",
        "cron.monthly",
    }:
        return "cron"
    if ext_l == ".tf":
        return "terraform"
    if ext_l in {".yml", ".yaml"} and (name_l.startswith("docker-compose") or name_l.startswith("compose")):
        return "compose"
    if (
        ext_l in {".yml", ".yaml"}
        and re.search(r"^\s*apiVersion\s*:", content, re.MULTILINE)
        and re.search(r"^\s*kind\s*:", content, re.MULTILINE)
    ):
        return "k8s"
    if ext_l in {".yml", ".yaml"} and (
        "playbook" in name_l
        or "ansible" in name_l
        or (re.search(r"^\s*-?\s*hosts\s*:", content, re.MULTILINE) and re.search(r"^\s*tasks\s*:", content, re.MULTILINE))
    ):
        return "ansible"
    return None


def _audit_single_file(file_path: Path, base_dir: Path) -> Tuple[bool, List[Dict[str, Any]], int]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        _ = _note_exc(exc)
        return False, [], 0

    kind = _classify_auditable_file(file_path, content)
    if kind is None:
        return False, [], 0

    try:
        file_label = str(file_path.relative_to(base_dir)) if file_path != base_dir else file_path.name
    except ValueError as exc:
        _ = _note_exc(exc)
        file_label = str(file_path)

    auditors = {
        "ssh": _audit_ssh_config,
        "systemd": _audit_systemd_unit,
        "nginx": _audit_nginx_config,
        "caddy": _audit_caddyfile,
        "shell": _audit_shell_script,
        "powershell": _audit_ps1_script,
        "cron": _audit_cron_file,
        "sysctl": _audit_sysctl_config,
        "terraform": _audit_terraform,
        "ansible": _audit_ansible,
        "k8s": _audit_k8s_manifest,
        "compose": _audit_compose_manifest,
        "sudoers": _audit_sudoers,
        "firewall": _audit_firewall,
    }
    raw_findings = auditors[kind](content, file_label)
    ignores = _parse_ignore_directives(content)
    active_findings: List[Dict[str, Any]] = []
    suppressed_count = 0

    for item in raw_findings:
        line_ignores = ignores.get(int(item.get("line", 0)), set())
        rule_id = str(item.get("id", "")).upper()
        if "ALL" in line_ignores or rule_id in line_ignores:
            suppressed_count += 1
        else:
            item["fingerprint"] = compute_finding_fingerprint(item)
            active_findings.append(item)

    return True, active_findings, suppressed_count


def audit_path(
    target: Path,
    baseline_path: Optional[Path] = None,
    write_baseline_path: Optional[Path] = None,
    native_lint: bool = False,
) -> Dict[str, Any]:
    """Audits a single file or directory tree for system hardening, ops script, and IaC hazards."""
    resolved = target.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Audit target does not exist: {resolved}")

    findings: List[Dict[str, Any]] = []
    files_audited = 0
    suppressed_count = 0
    native_tools_used: List[str] = []
    native_tools_skipped: List[str] = []

    if resolved.is_file():
        audited, file_findings, file_suppressed = _audit_single_file(resolved, resolved.parent)
        if audited:
            files_audited = 1
            findings.extend(file_findings)
            suppressed_count += file_suppressed
    else:
        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in sorted(dirs) if d not in IGNORE_DIRS and d != "tests"]
            for fname in sorted(files):
                if fname.startswith("test_") or fname in SKIP_SELF_NAMES:
                    continue
                fpath = Path(root) / fname
                audited, file_findings, file_suppressed = _audit_single_file(fpath, resolved)
                if audited:
                    files_audited += 1
                    findings.extend(file_findings)
                    suppressed_count += file_suppressed

    if native_lint:
        native_res = sys_admin_sre.run_native_validators(resolved)
        native_tools_used = native_res["tools_used"]
        native_tools_skipped = native_res["tools_skipped"]
        for nf in native_res["findings"]:
            nf["fingerprint"] = compute_finding_fingerprint(nf)
            findings.append(nf)

    if write_baseline_path is not None:
        wb_path = Path(write_baseline_path).resolve()
        wb_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_payload = {
            "version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "fingerprints": sorted({f["fingerprint"] for f in findings}),
        }
        wb_path.write_text(json.dumps(baseline_payload, indent=2) + "\n", encoding="utf-8")

    baselined_count = 0
    if baseline_path is not None:
        bl_path = Path(baseline_path).resolve()
        if not bl_path.exists():
            raise FileNotFoundError(f"Baseline file not found: {bl_path}")
        bl_data = json.loads(bl_path.read_text(encoding="utf-8"))
        known_fps = set(bl_data.get("fingerprints", []))
        filtered: List[Dict[str, Any]] = []
        for f in findings:
            if f["fingerprint"] in known_fps:
                baselined_count += 1
            else:
                filtered.append(f)
        findings = filtered

    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    warning_count = sum(1 for f in findings if f["severity"] == "WARNING")

    report: Dict[str, Any] = {
        "status": "fail" if (critical_count > 0 or high_count > 0) else "pass",
        "target": str(resolved),
        "files_audited": files_audited,
        "total_findings": len(findings),
        "critical_count": critical_count,
        "high_count": high_count,
        "warning_count": warning_count,
        "suppressed_count": suppressed_count,
        "baselined_count": baselined_count,
        "findings": findings,
    }
    if native_lint:
        report["native_tools_used"] = native_tools_used
        report["native_tools_skipped"] = native_tools_skipped
    return report


# ---------------------------------------------------------------------------
# 4. Hardened Template Scaffolder
# ---------------------------------------------------------------------------

def sanitize_name(name: str) -> str:
    """Sanitizes service/incident names to safe lowercase alphanumeric/hyphen slugs."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-_").lower()
    return cleaned or "app"


def _render_systemd_template(name: str) -> str:
    return f"""[Unit]
Description={name} managed service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={name}
Group={name}
WorkingDirectory=/opt/{name}
ExecStart=/opt/{name}/bin/{name}
Restart=on-failure
RestartSec=5s

# Security sandboxing
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
CapabilityBoundingSet=
UMask=0027

# Resource limits
MemoryMax=512M
CPUQuota=100%

[Install]
WantedBy=multi-user.target
"""


def _render_nginx_template(name: str) -> str:
    return f"""server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {name}.example.com;

    server_tokens off;
    autoindex off;

    ssl_certificate /etc/letsencrypt/live/{name}.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{name}.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {{
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }}
}}
"""


def _render_backup_sh_template(name: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail
umask 077

SERVICE_NAME="{name}"
SOURCE_DIR="${{SOURCE_DIR:-/var/lib/{name}}}"
BACKUP_ROOT="${{BACKUP_ROOT:-/var/backups/{name}}}"
RETENTION_DAYS="${{RETENTION_DAYS:-14}}"
LOCK_FILE="/tmp/backup-${{SERVICE_NAME}}.lock"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE_PATH="${{BACKUP_ROOT}}/${{SERVICE_NAME}}-${{STAMP}}.tar.gz"

mkdir -p "${{BACKUP_ROOT}}"

exec 9>"${{LOCK_FILE}}"
if ! flock -n 9; then
    echo "Backup already running for ${{SERVICE_NAME}}" >&2
    exit 1
fi

if [ ! -d "${{SOURCE_DIR}}" ]; then
    echo "Source directory not found: ${{SOURCE_DIR}}" >&2
    exit 1
fi

tar -czf "${{ARCHIVE_PATH}}" -C "$(dirname "${{SOURCE_DIR}}")" "$(basename "${{SOURCE_DIR}}")"
sha256sum "${{ARCHIVE_PATH}}" > "${{ARCHIVE_PATH}}.sha256"

find "${{BACKUP_ROOT}}" -maxdepth 1 -type f -name "${{SERVICE_NAME}}-*.tar.gz*" -mtime "+${{RETENTION_DAYS}}" -delete
echo "Backup completed: ${{ARCHIVE_PATH}}"
"""


def _render_backup_ps1_template(name: str) -> str:
    return f"""#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ServiceName = "{name}"
$SourceDir = if ($env:SOURCE_DIR) {{ $env:SOURCE_DIR }} else {{ "C:\\Data\\$ServiceName" }}
$BackupRoot = if ($env:BACKUP_ROOT) {{ $env:BACKUP_ROOT }} else {{ "C:\\Backups\\$ServiceName" }}
$RetentionDays = if ($env:RETENTION_DAYS) {{ [int]$env:RETENTION_DAYS }} else {{ 14 }}

if (-not (Test-Path -LiteralPath $SourceDir)) {{
    throw "Source directory not found: $SourceDir"
}}

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$ArchivePath = Join-Path $BackupRoot "$ServiceName-$Stamp.zip"

Compress-Archive -Path $SourceDir -DestinationPath $ArchivePath -CompressionLevel Optimal
$Hash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash
Set-Content -LiteralPath "$ArchivePath.sha256" -Value "$Hash  $(Split-Path -Leaf $ArchivePath)" -Encoding utf8

$Cutoff = (Get-Date).ToUniversalTime().AddDays(-$RetentionDays)
Get-ChildItem -LiteralPath $BackupRoot -Filter "$ServiceName-*.zip*" |
    Where-Object {{ $_.LastWriteTimeUtc -lt $Cutoff }} |
    Remove-Item -Force

Write-Host "Backup completed: $ArchivePath"
"""


def _render_cron_template(name: str) -> str:
    return f"""# Hardened cron job for {name}
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""

# Run daily at 02:15 UTC with non-overlapping flock guard
15 2 * * * {name} /usr/bin/flock -n /var/lock/{name}-backup.lock /usr/local/sbin/backup-{name}.sh >> /var/log/{name}/backup.log 2>&1
"""


def _render_sshd_template(name: str) -> str:
    return f"""# Hardened OpenSSH drop-in configuration for {name}
# Install at: /etc/ssh/sshd_config.d/99-{name}-sshd-hardening.conf
# Validate before reload: sshd -t

PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
"""


def _render_runbook_template(name: str) -> str:
    return f"""# Operational Runbook: `{name}`

## 1. Service Overview & Ownership
- **Service**: `{name}`
- **Owner / On-Call**: Infrastructure / SRE
- **SLO Targets**: 99.9% availability | P99 latency < 250ms | RPO 24h / RTO 30m

## 2. Fast Triage Commands
- **Toolkit Health Check**: `atk sysadmin --health --ports --json`
- **Linux**: `systemctl status {name}`, `journalctl -u {name} -n 100 --no-pager`, `ss -tulnp`
- **macOS**: `launchctl list | grep {name}`, `lsof -iTCP -sTCP:LISTEN -nP`
- **Windows**: `Get-Service -Name {name}`, `Get-EventLog -LogName Application -Newest 50`
- **Endpoint / TLS**: `atk sysadmin --check-tls {name}.example.com:443`

## 3. Common Failure Modes & Mitigations
| Symptom | Likely Cause | Diagnostic Check | Safe Mitigation |
| :--- | :--- | :--- | :--- |
| High latency / 502 | Upstream exhausted or hung worker | Check CPU/memory load & socket queue | Reload gracefully after `nginx -t` |
| Disk full alerts | Unrotated logs or stale artifacts | `df -h` and `du -sh /var/log/*` | Truncate/archive rotated logs safely |
| TLS handshake error | Expired or mismatched certificate | `atk sysadmin --check-tls ...` | Renew cert and verify chain before reload |

## 4. Rollback & Recovery Procedure
1. Capture pre-change diagnostics (`atk sysadmin --health --json`).
2. Restore previous known-good config/binary release.
3. Validate syntax (`sshd -t` / `nginx -t` / `systemd-analyze verify`).
4. Reload service and verify health endpoint returns HTTP 200.
"""


def _render_postmortem_template(name: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""# Blameless Incident Postmortem: {name} ({today})

## 1. Executive Summary
- **Date (UTC)**: {today}
- **Severity**: SEV-2
- **Duration / TTD / TTM / TTR**: Duration: _TBD_ | TTD: _TBD_ | TTM: _TBD_ | TTR: _TBD_
- **Customer Impact**: _Describe user-facing impact, affected endpoints, and error budget burn._

## 2. Timeline (UTC)
| Time (UTC) | Event / Observation |
| :--- | :--- |
| HH:MM | Alert triggered / symptom observed |
| HH:MM | Triage started and root cause isolated |
| HH:MM | Mitigation deployed and service stabilized |
| HH:MM | Full verification passed (exit code 0) |

## 3. Root Cause Analysis (5 Whys)
1. **Why did the incident occur?** _TBD_
2. **Why did safeguards not prevent it?** _TBD_
3. **Systemic contributing factors**: _TBD_

## 4. Retrospective
- **What went well**: _Fast detection, clear runbook, clean rollback._
- **What went poorly**: _Gaps in alerting, missing pre-flight config audit._
- **Where we got lucky**: _Low-traffic window or redundant standby._

## 5. Corrective Action Items
| Action | Priority | Owner | Tracking |
| :--- | :--- | :--- | :--- |
| Add automated `atk sysadmin --audit --check` gate in CI | P1 | SRE | _Issue #_ |
| Update service runbook with triage query | P2 | On-Call | _Issue #_ |
"""


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "systemd": {
        "description": "Hardened systemd service unit with non-root user and cgroup sandboxing",
        "filename": lambda name: f"{name}.service",
        "executable": False,
        "render": _render_systemd_template,
    },
    "nginx": {
        "description": "Hardened Nginx reverse proxy virtual host with TLS 1.2/1.3 and HSTS",
        "filename": lambda name: f"{name}-nginx.conf",
        "executable": False,
        "render": _render_nginx_template,
    },
    "backup": {
        "description": "Idempotent Bash backup script with strict mode, flock, SHA-256, and pruning",
        "filename": lambda name: f"backup-{name}.sh",
        "executable": True,
        "render": _render_backup_sh_template,
    },
    "backup-ps1": {
        "description": "Idempotent PowerShell backup script with StrictMode, SHA-256, and pruning",
        "filename": lambda name: f"backup-{name}.ps1",
        "executable": True,
        "render": _render_backup_ps1_template,
    },
    "cron": {
        "description": "Hardened cron schedule with explicit PATH, MAILTO, and flock lock guard",
        "filename": lambda name: f"{name}.cron",
        "executable": False,
        "render": _render_cron_template,
    },
    "sshd": {
        "description": "Hardened OpenSSH drop-in configuration disabling root and password login",
        "filename": lambda name: f"99-{name}-sshd-hardening.conf",
        "executable": False,
        "render": _render_sshd_template,
    },
    "runbook": {
        "description": "SRE operational runbook with cross-platform triage and rollback steps",
        "filename": lambda name: str(Path("docs") / "runbooks" / f"{name}.md"),
        "executable": False,
        "render": _render_runbook_template,
    },
    "postmortem": {
        "description": "Blameless incident postmortem template with UTC timeline and 5 Whys",
        "filename": lambda name: str(
            Path("docs") / "postmortems" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{name}.md"
        ),
        "executable": False,
        "render": _render_postmortem_template,
    },
}


def scaffold_template(
    template_name: str,
    service_name: str = "app",
    target_dir: Path = Path("."),
    output_path: Optional[Path] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Renders and writes a hardened sysadmin/SRE template safely."""
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template '{template_name}'. Choose from: {', '.join(sorted(TEMPLATES))}")

    clean_name = sanitize_name(service_name)
    spec = TEMPLATES[template_name]
    dest = Path(output_path) if output_path else (Path(target_dir).resolve() / spec["filename"](clean_name))

    if dest.exists() and not force:
        raise FileExistsError(f"Destination already exists (use --force to overwrite): {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    rendered = spec["render"](clean_name)
    dest.write_text(rendered, encoding="utf-8")

    if spec.get("executable"):
        current_mode = dest.stat().st_mode
        dest.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP)

    return {
        "status": "pass",
        "template": template_name,
        "service_name": clean_name,
        "output": str(dest),
        "executable": bool(spec.get("executable")),
    }


# ---------------------------------------------------------------------------
# 5. Human-Readable Output Formatting & CLI Entrypoint
# ---------------------------------------------------------------------------

def _print_health_report(report: Dict[str, Any]) -> None:
    status_badge = {"pass": "✅ HEALTHY", "warn": "⚠️ WARNING", "fail": "❌ CRITICAL"}[report["status"]]
    print(f"🖥️  Host Health Report — {report['hostname']} ({report['os']} {report['release']})")
    print(f"   • Status: {status_badge}")
    print(f"   • CPU Cores: {report['cpu_count']} | Arch: {report['machine']}")
    if report.get("uptime_seconds") is not None:
        print(f"   • Uptime: {report['uptime_seconds']}s")
    if report.get("load_average") is not None:
        la = report["load_average"]
        print(f"   • Load Avg: {la['1m']} / {la['5m']} / {la['15m']} (per-core 1m: {la['per_cpu_1m']})")
    disk = report["disk"]
    print(
        f"   • Disk ({disk['path']}): {disk['used_gb']} GB / {disk['total_gb']} GB "
        f"({disk['percent_used']}% used) [{disk['status'].upper()}]"
    )
    inodes = disk.get("inodes") or {}
    if inodes.get("available"):
        print(
            f"   • Inodes: {inodes['used_inodes']} / {inodes['total_inodes']} "
            f"({inodes['percent_used']}% used) [{inodes['status'].upper()}]"
        )
    mem = report["memory"]
    if mem.get("available"):
        print(
            f"   • Memory: {mem['used_gb']} GB / {mem['total_gb']} GB "
            f"({mem['percent_used']}% used) [{mem['status'].upper()}]"
        )
    else:
        print(f"   • Memory: unavailable ({mem.get('error', 'unknown')})")
    svc = report["services"]
    if svc.get("available"):
        print(f"   • Services ({svc['manager']}): {svc['failed_count']} failed unit(s)")
    if report.get("listening_ports"):
        ports = report["listening_ports"]
        print(f"   • Listening Ports ({ports.get('tool') or 'n/a'}): {ports['count']} socket(s)")
    if report.get("processes"):
        proc = report["processes"]
        print(f"   • Processes: {proc['total_processes']} total, {proc['zombie_count']} zombie(s)")
        if proc.get("fd_usage"):
            fd = proc["fd_usage"]
            print(f"   • Kernel FDs: {fd['allocated']} / {fd['max']} ({fd['percent_used']}% used)")
    if report["alerts"]:
        print("\n🚨 Alerts:")
        for alert in report["alerts"]:
            print(f"   [{alert['severity']}] {alert['id']}: {alert['message']}")


def _print_audit_report(report: Dict[str, Any]) -> None:
    print(f"🔒 SysAdmin Hardening Audit for: {report['target']}")
    print(f"   • Status: {'❌ FAILED' if report['status'] == 'fail' else '✅ PASSED'}")
    print(f"   • Files Audited: {report['files_audited']}")
    print(
        f"   • Findings: {report['total_findings']} "
        f"(Critical: {report['critical_count']}, High: {report['high_count']}, Warnings: {report['warning_count']})"
    )
    if report.get("suppressed_count") or report.get("baselined_count"):
        print(
            f"   • Suppressed: {report.get('suppressed_count', 0)} | "
            f"Baselined: {report.get('baselined_count', 0)}"
        )
    if report["findings"]:
        print("\n🚨 Findings:")
        for f in report["findings"][:20]:
            print(f"   [{f['severity']}] {f['id']} ({f['category']}): {f['message']}")
            print(f"       -> {f['file']}:{f['line']} | {f['snippet']}")
            print(f"       -> Fix: {f['remediation']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Universal System Administration, Infrastructure Hardening & SRE Triage Tool"
    )
    # Health triage options
    parser.add_argument("--health", action="store_true", help="Run cross-platform host health diagnostics")
    parser.add_argument("--ports", action="store_true", help="Include listening sockets in --health output")
    parser.add_argument("--processes", action="store_true", help="Include top processes, zombies, and FD usage in --health")
    parser.add_argument("--disk-warn", type=float, default=80.0, help="Disk usage warning threshold %% (default: 80)")
    parser.add_argument("--disk-crit", type=float, default=90.0, help="Disk usage critical threshold %% (default: 90)")
    parser.add_argument("--mem-warn", type=float, default=85.0, help="Memory usage warning threshold %% (default: 85)")
    parser.add_argument("--mem-crit", type=float, default=95.0, help="Memory usage critical threshold %% (default: 95)")

    # Static hardening audit options
    parser.add_argument(
        "--audit",
        nargs="?",
        const=None,
        default=_AUDIT_SENTINEL,
        metavar="PATH",
        help="Audit server configs, shell/PowerShell scripts, cron, and IaC manifests",
    )
    parser.add_argument("--dir", "--path", "--repo", dest="dir", type=str, default=".", help="Target directory or file")
    parser.add_argument("--native-lint", action="store_true", help="Run available native validators (shellcheck/bash -n, caddy, etc.)")
    parser.add_argument("--baseline", type=str, default=None, metavar="FILE", help="Filter out findings matching a baseline JSON")
    parser.add_argument("--write-baseline", type=str, default=None, metavar="FILE", help="Write audit finding fingerprints to baseline JSON")

    # Deep SRE triage, posture, drift snapshots & safe apply
    parser.add_argument("--audit-host", action="store_true", help="Audit local host SSH permissions, shadow mode, umask, and reboot state")
    parser.add_argument("--triage-logs", type=str, default=None, metavar="PATH", help="Condense log file or directory into incident alerts and error clusters")
    parser.add_argument("--max-lines", type=int, default=50000, help="Maximum trailing log lines to scan (default: 50000)")
    parser.add_argument("--top-n", type=int, default=10, help="Maximum error clusters in --triage-logs output (default: 10)")
    parser.add_argument(
        "--apply-safe",
        nargs=2,
        default=None,
        metavar=("SRC", "DEST"),
        help="Atomically apply config SRC -> DEST with SHA-256 receipts, validation, and auto-rollback",
    )
    parser.add_argument("--validate-cmd", type=str, default=None, help="Validation command (e.g. 'nginx -t') for --apply-safe")
    parser.add_argument("--backup-dir", type=str, default=None, help="Backup directory for --apply-safe")
    parser.add_argument("--dry-run", action="store_true", help="Preview unified diff without mutating files during --apply-safe")
    parser.add_argument("--snapshot", type=str, default=None, metavar="OUT.json", help="Capture host telemetry/posture snapshot to JSON")
    parser.add_argument(
        "--diff-snapshot",
        nargs="+",
        default=None,
        metavar="SNAPSHOT.json",
        help="Compare baseline snapshot against live host (1 arg) or second snapshot (2 args)",
    )
    parser.add_argument("--check-endpoints", type=str, default=None, metavar="MANIFEST.json", help="Batch-check DNS/TCP/TLS endpoints from JSON manifest")
    parser.add_argument("--ssh", type=str, default=None, metavar="[USER@]HOST", help="Run read-only remote host triage over BatchMode SSH")

    # Scaffolding options
    parser.add_argument(
        "--scaffold",
        "--init",
        dest="scaffold",
        choices=sorted(TEMPLATES.keys()),
        help="Scaffold a hardened ops config, script, runbook, or postmortem",
    )
    parser.add_argument("--list-templates", action="store_true", help="List available hardened scaffold templates")
    parser.add_argument("--name", type=str, default="app", help="Service or incident slug for scaffolding (default: app)")
    parser.add_argument("--output", type=str, default=None, help="Explicit output path for --scaffold")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output file during --scaffold")

    # Network & TLS options
    parser.add_argument("--check-tls", type=str, default=None, metavar="HOST[:PORT]", help="Check remote TLS cert expiry & version")
    parser.add_argument("--check-port", type=str, default=None, metavar="HOST:PORT", help="Check TCP port reachability & latency")
    parser.add_argument("--check-dns", type=str, default=None, metavar="HOSTNAME", help="Resolve DNS A/AAAA records & latency")
    parser.add_argument("--timeout", type=float, default=5.0, help="Network check timeout in seconds (default: 5.0)")
    parser.add_argument("--tls-warn-days", type=int, default=30, help="TLS expiry warning days (default: 30)")
    parser.add_argument("--tls-crit-days", type=int, default=7, help="TLS expiry critical days (default: 7)")

    # General output & gating
    parser.add_argument("--check", action="store_true", help="Exit with code 1 if status is 'fail'")
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    audit_requested = args.audit != _AUDIT_SENTINEL
    has_action = any([
        args.health,
        audit_requested,
        args.audit_host,
        args.triage_logs is not None,
        args.apply_safe is not None,
        args.snapshot is not None,
        args.diff_snapshot is not None,
        args.check_endpoints is not None,
        args.ssh is not None,
        args.scaffold is not None,
        args.list_templates,
        args.check_tls is not None,
        args.check_port is not None,
        args.check_dns is not None,
    ])

    if not has_action:
        parser.print_help()
        return 0

    if args.list_templates:
        payload = {
            "templates": {k: v["description"] for k, v in sorted(TEMPLATES.items())}
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("🧰 Available Hardened SysAdmin / SRE Templates:")
            for name, desc in payload["templates"].items():
                print(f"   • {name:<12} {desc}")
        return 0

    overall_failed = False

    if args.scaffold is not None:
        try:
            res = scaffold_template(
                template_name=args.scaffold,
                service_name=args.name,
                target_dir=Path(args.dir),
                output_path=Path(args.output) if args.output else None,
                force=args.force,
            )
        except (FileExistsError, ValueError) as exc:
            if args.json:
                print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
            else:
                print(f"❌ {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"✅ Scaffolded '{res['template']}' template for '{res['service_name']}': {res['output']}")
        return 0

    if args.apply_safe is not None:
        src_path, dst_path = Path(args.apply_safe[0]), Path(args.apply_safe[1])
        val_cmd = shlex.split(args.validate_cmd) if args.validate_cmd else None
        try:
            apply_res = sys_admin_sre.apply_config_safe(
                source=src_path,
                destination=dst_path,
                validate_cmd=val_cmd,
                backup_dir=Path(args.backup_dir) if args.backup_dir else None,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            if args.json:
                print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
            else:
                print(f"❌ {exc}", file=sys.stderr)
            return 1

        if apply_res["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(apply_res, indent=2))
        else:
            if apply_res.get("dry_run"):
                print(f"🔍 Dry-run diff for {apply_res['destination']}:\n{apply_res['diff'] or '(no changes)'}")
            elif apply_res["status"] == "pass":
                print(f"✅ Safely applied {apply_res['destination']} (sha256: {apply_res['sha256_after'][:12]})")
            else:
                print(f"❌ Validation failed and auto-rolled back {apply_res['destination']}: {apply_res.get('validation_stderr')}")
        return 1 if overall_failed else 0

    if args.health:
        health_report = collect_host_health(
            target_path=args.dir,
            disk_warn=args.disk_warn,
            disk_crit=args.disk_crit,
            mem_warn=args.mem_warn,
            mem_crit=args.mem_crit,
            include_ports=args.ports,
            include_processes=args.processes,
        )
        if health_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(health_report, indent=2))
        else:
            _print_health_report(health_report)

    if args.audit_host:
        posture_report = sys_admin_sre.audit_host_posture()
        if posture_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(posture_report, indent=2))
        else:
            print(
                f"🛡️ Host Security Posture: {'❌ FAILED' if posture_report['status'] == 'fail' else '✅ PASSED'} "
                f"(Checks: {posture_report['checks_run']}, Critical: {posture_report['critical_count']}, "
                f"High: {posture_report['high_count']}, Warnings: {posture_report['warning_count']})"
            )
            for item in posture_report["findings"]:
                print(f"   [{item['severity']}] {item['id']}: {item['message']}")
                print(f"       -> Fix: {item['remediation']}")

    if args.triage_logs is not None:
        try:
            log_report = sys_admin_sre.triage_logs(
                Path(args.triage_logs),
                max_lines=args.max_lines,
                top_n=args.top_n,
            )
        except FileNotFoundError as exc:
            if args.json:
                print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
            else:
                print(f"❌ {exc}", file=sys.stderr)
            return 1
        if log_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(log_report, indent=2))
        else:
            print(
                f"📜 Log Triage ({log_report['source']}): {log_report['lines_scanned']} line(s), "
                f"{log_report['error_lines']} error(s), {log_report['warn_lines']} warning(s)"
            )
            for alert in log_report["alerts"]:
                print(f"   [{alert['severity']}] {alert['id']} (x{alert['count']}): {alert['message']}")
            if log_report["top_clusters"]:
                print("   Top Clusters:")
                for c in log_report["top_clusters"]:
                    print(f"     • (x{c['count']}) {c['signature']}")

    if args.snapshot is not None:
        snap_health = collect_host_health(
            target_path=args.dir,
            disk_warn=args.disk_warn,
            disk_crit=args.disk_crit,
            mem_warn=args.mem_warn,
            mem_crit=args.mem_crit,
            include_ports=True,
        )
        snap_posture = sys_admin_sre.audit_host_posture()
        snapshot_data = sys_admin_sre.capture_host_snapshot(snap_health, snap_posture)
        out_snap = Path(args.snapshot).resolve()
        out_snap.parent.mkdir(parents=True, exist_ok=True)
        out_snap.write_text(json.dumps(snapshot_data, indent=2) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps({"status": "pass", "snapshot_file": str(out_snap), "snapshot": snapshot_data}, indent=2))
        else:
            print(f"📸 Captured host posture snapshot to: {out_snap}")

    if args.diff_snapshot is not None:
        if len(args.diff_snapshot) > 2:
            print("❌ --diff-snapshot accepts 1 path (baseline vs live) or 2 paths (baseline vs current)", file=sys.stderr)
            return 1
        base_file = Path(args.diff_snapshot[0]).resolve()
        if not base_file.exists():
            print(f"❌ Baseline snapshot not found: {base_file}", file=sys.stderr)
            return 1
        baseline_data = json.loads(base_file.read_text(encoding="utf-8"))
        if len(args.diff_snapshot) == 2:
            curr_file = Path(args.diff_snapshot[1]).resolve()
            if not curr_file.exists():
                print(f"❌ Current snapshot not found: {curr_file}", file=sys.stderr)
                return 1
            current_data = json.loads(curr_file.read_text(encoding="utf-8"))
        else:
            live_health = collect_host_health(target_path=args.dir, include_ports=True)
            live_posture = sys_admin_sre.audit_host_posture()
            current_data = sys_admin_sre.capture_host_snapshot(live_health, live_posture)

        diff_res = sys_admin_sre.diff_host_snapshots(baseline_data, current_data)
        if diff_res["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(diff_res, indent=2))
        else:
            print(
                f"📊 Host Drift Status: {diff_res['status'].upper()} | "
                f"Disk delta: {diff_res['disk_delta_pct']}% | "
                f"Added ports: {len(diff_res['added_ports'])} | "
                f"Newly failed services: {len(diff_res['newly_failed_services'])}"
            )

    if args.check_endpoints is not None:
        try:
            ep_report = sys_admin_sre.check_endpoints_manifest(
                Path(args.check_endpoints),
                check_tls_certificate,
                check_tcp_port,
                check_dns_resolution,
                timeout=args.timeout,
                warn_days=args.tls_warn_days,
                crit_days=args.tls_crit_days,
            )
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            if args.json:
                print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
            else:
                print(f"❌ {exc}", file=sys.stderr)
            return 1
        if ep_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(ep_report, indent=2))
        else:
            print(
                f"🌐 Endpoints Batch Check: {ep_report['status'].upper()} "
                f"({ep_report['passed']} pass, {ep_report['warned']} warn, {ep_report['failed']} fail)"
            )

    if args.ssh is not None:
        try:
            ssh_report = sys_admin_sre.run_remote_health_check(args.ssh, timeout=int(args.timeout))
        except ValueError as exc:
            ssh_report = {"status": "fail", "error": str(exc)}
        if ssh_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(ssh_report, indent=2))
        else:
            icon = "✅" if ssh_report["status"] == "pass" else "❌"
            print(f"{icon} Remote SSH Triage ({args.ssh}):\n{ssh_report.get('stdout') or ssh_report.get('error') or ssh_report.get('stderr')}")

    if args.check_tls is not None:
        try:
            tls_report = check_tls_certificate(
                args.check_tls,
                timeout=args.timeout,
                warn_days=args.tls_warn_days,
                crit_days=args.tls_crit_days,
            )
        except ValueError as exc:
            tls_report = {"status": "fail", "error": str(exc)}
        if tls_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(tls_report, indent=2))
        else:
            icon = "✅" if tls_report["status"] == "pass" else ("⚠️" if tls_report["status"] == "warn" else "❌")
            print(f"{icon} TLS Check ({args.check_tls}): {tls_report}")

    if args.check_port is not None:
        try:
            port_report = check_tcp_port(args.check_port, timeout=args.timeout)
        except ValueError as exc:
            port_report = {"status": "fail", "error": str(exc)}
        if port_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(port_report, indent=2))
        else:
            icon = "✅" if port_report["status"] == "pass" else "❌"
            print(f"{icon} TCP Port Check ({args.check_port}): {port_report}")

    if args.check_dns is not None:
        try:
            dns_report = check_dns_resolution(args.check_dns)
        except ValueError as exc:
            dns_report = {"status": "fail", "error": str(exc)}
        if dns_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(dns_report, indent=2))
        else:
            icon = "✅" if dns_report["status"] == "pass" else "❌"
            print(f"{icon} DNS Check ({args.check_dns}): {dns_report}")

    if audit_requested:
        audit_target = Path(args.audit) if args.audit is not None else Path(args.dir)
        try:
            audit_report = audit_path(
                audit_target,
                baseline_path=Path(args.baseline) if args.baseline else None,
                write_baseline_path=Path(args.write_baseline) if args.write_baseline else None,
                native_lint=args.native_lint,
            )
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            if args.json:
                print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
            else:
                print(f"❌ {exc}", file=sys.stderr)
            return 1
        if audit_report["status"] == "fail":
            overall_failed = True
        if args.json:
            print(json.dumps(audit_report, indent=2))
        else:
            _print_audit_report(audit_report)

    if args.check and overall_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
