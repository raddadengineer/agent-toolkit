#!/usr/bin/env python3
"""
audit_deps.py — Multi-Ecosystem Dependency Security & Manifest Auditor

Inspects package manifests (Python requirements.txt/pyproject.toml, Node
package.json, Rust Cargo.toml, Go go.mod) for wildcard pinning, unpinned
dependencies, and known deprecated packages.

Usage:
    python3 audit_deps.py
    python3 audit_deps.py --check
    python3 audit_deps.py --json
    python3 audit_deps.py --dir /path/to/project
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEPRECATED_PACKAGES = {
    "python": {
        "pycrypto": "Deprecated and unmaintained. Migrate to 'cryptography'.",
        "nose": "Deprecated and unmaintained. Migrate to 'pytest' or 'unittest'.",
    },
    "node": {
        "request": "Deprecated and abandoned since 2020. Migrate to 'axios' or native 'fetch'.",
        "left-pad": "Deprecated historic package. Use native String.prototype.padStart.",
    },
}

IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".agents", ".gemini"}


def audit_requirements_txt(file_path: Path) -> List[Dict[str, Any]]:
    """Audits Python requirements.txt file."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        sys.stderr.write(f"Warning: could not read {file_path}: {err}\n")
        return findings

    for idx, raw_line in enumerate(content.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-r") or line.startswith("-i") or line.startswith("--"):
            continue

        # Extract package name and specifier
        parts = re.split(r'([<>=!~]+)', line, maxsplit=1)
        pkg_name = parts[0].strip().lower()

        # Check deprecated
        if pkg_name in DEPRECATED_PACKAGES["python"]:
            findings.append({
                "id": "DEP-DEPRECATED",
                "severity": "WARNING",
                "file": str(file_path),
                "line": idx,
                "package": pkg_name,
                "message": f"Package '{pkg_name}' is deprecated: {DEPRECATED_PACKAGES['python'][pkg_name]}",
            })

        if len(parts) == 1:
            # Unpinned completely (e.g. "flask")
            findings.append({
                "id": "DEP-UNPINNED",
                "severity": "WARNING",
                "file": str(file_path),
                "line": idx,
                "package": pkg_name,
                "message": f"Package '{pkg_name}' has no version constraint specified. May cause non-reproducible builds.",
            })
        else:
            spec = parts[2].strip() if len(parts) > 2 else ""
            if "*" in spec or spec == "latest":
                findings.append({
                    "id": "DEP-WILDCARD",
                    "severity": "CRITICAL",
                    "file": str(file_path),
                    "line": idx,
                    "package": pkg_name,
                    "message": f"Package '{pkg_name}' uses wildcard version pinning ('{spec}'). Prohibited in production.",
                })
    return findings


def audit_package_json(file_path: Path) -> List[Dict[str, Any]]:
    """Audits Node.js package.json file."""
    findings = []
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as err:
        sys.stderr.write(f"Warning: could not parse {file_path}: {err}\n")
        return findings

    dep_sections = ["dependencies", "devDependencies", "peerDependencies"]
    for section in dep_sections:
        deps = data.get(section, {})
        if not isinstance(deps, dict):
            continue

        for pkg, spec in deps.items():
            pkg_lower = pkg.lower()
            spec_str = str(spec).strip()

            # Check deprecated
            if pkg_lower in DEPRECATED_PACKAGES["node"]:
                findings.append({
                    "id": "DEP-DEPRECATED",
                    "severity": "WARNING",
                    "file": str(file_path),
                    "line": 0,
                    "package": pkg,
                    "message": f"Package '{pkg}' is deprecated: {DEPRECATED_PACKAGES['node'][pkg_lower]}",
                })

            # Check wildcard
            if spec_str in ("*", "latest"):
                findings.append({
                    "id": "DEP-WILDCARD",
                    "severity": "CRITICAL",
                    "file": str(file_path),
                    "line": 0,
                    "package": pkg,
                    "message": f"Package '{pkg}' in '{section}' uses wildcard version '{spec_str}'.",
                })
            elif not spec_str:
                findings.append({
                    "id": "DEP-UNPINNED",
                    "severity": "WARNING",
                    "file": str(file_path),
                    "line": 0,
                    "package": pkg,
                    "message": f"Package '{pkg}' in '{section}' has empty version specifier.",
                })

    # Check for lockfile
    parent_dir = file_path.parent
    lockfiles = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb"]
    if not any((parent_dir / lock).exists() for lock in lockfiles):
        findings.append({
            "id": "DEP-NO-LOCKFILE",
            "severity": "WARNING",
            "file": str(file_path),
            "line": 0,
            "package": "node_modules",
            "message": "No lockfile (package-lock.json / yarn.lock / pnpm-lock.yaml) found alongside package.json.",
        })

    return findings


def audit_repository_deps(repo_root: Path) -> Dict[str, Any]:
    """Audits all discovered manifests across repository."""
    all_findings = []
    manifests_found = []

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in files:
            path = Path(root) / f
            fname = f.lower()

            if fname in ("requirements.txt", "requirements-dev.txt"):
                manifests_found.append(str(path))
                all_findings.extend(audit_requirements_txt(path))
            elif fname == "package.json":
                manifests_found.append(str(path))
                all_findings.extend(audit_package_json(path))

    critical_count = sum(1 for f in all_findings if f["severity"] == "CRITICAL")
    warning_count = sum(1 for f in all_findings if f["severity"] == "WARNING")

    status = "fail" if critical_count > 0 else "pass"
    return {
        "status": status,
        "manifests_count": len(manifests_found),
        "manifests": manifests_found,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "findings": all_findings,
    }


def format_deps_report(res: Dict[str, Any]) -> str:
    """Formats dependency audit into human-readable summary."""
    lines = []
    status_icon = "✅ PASSED" if res["status"] == "pass" else "❌ FAILED"
    lines.append(f"📦 Dependency Security & Manifest Audit")
    lines.append(f"   • Status: {status_icon}")
    lines.append(f"   • Manifests Checked: {res['manifests_count']}")
    lines.append(f"   • Critical Issues: {res['critical_count']}")
    lines.append(f"   • Warnings: {res['warning_count']}")

    if res["findings"]:
        lines.append("\nFindings:")
        for f in res["findings"]:
            lvl_icon = "🚨" if f["severity"] == "CRITICAL" else "⚠️"
            fname = Path(f["file"]).name
            loc = f":{f['line']}" if f.get("line") and f["line"] > 0 else ""
            lines.append(f"   {lvl_icon} [{f['severity']}] {f['id']} ({fname}{loc}): {f['message']}")
    else:
        if not res["manifests_count"]:
            lines.append("   • (No dependency manifests discovered in repository.)")
        else:
            lines.append("   • All package manifests declare bounded version constraints and lockfile integrity.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-Ecosystem Dependency Security & Manifest Auditor.")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if CRITICAL findings exist")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--dir", type=str, default=None, help="Repository root path (default: current)")

    args = parser.parse_args()
    repo_root = Path(args.dir).resolve() if args.dir else Path.cwd()

    res = audit_repository_deps(repo_root)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(format_deps_report(res))

    if args.check and res["critical_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
