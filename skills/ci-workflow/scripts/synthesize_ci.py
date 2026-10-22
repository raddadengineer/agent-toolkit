#!/usr/bin/env python3
"""
synthesize_ci.py — CI/CD Pipeline Synthesizer & Workflow Security Auditor

Generates hardened GitHub Actions workflows integrated with agent-toolkit
verification gates, and audits existing CI pipelines for supply-chain risks.

Usage:
    python3 synthesize_ci.py --init --stack python
    python3 synthesize_ci.py --audit
    python3 synthesize_ci.py --audit --check
    python3 synthesize_ci.py --audit --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CI_TEMPLATES = {
    "python": """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions: read-all

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Test & Quality Gate
    runs-on: ubuntu-latest
    timeout-minutes: 15

    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: "pip"

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

      - name: Run Unit Tests
        run: python -m unittest discover -s tests

      - name: Verify Context Sync
        if: hashFiles('skills/session-closer/scripts/sync_context.py') != ''
        run: python3 skills/session-closer/scripts/sync_context.py --check
""",
    "node": """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions: read-all

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Build & Test
    runs-on: ubuntu-latest
    timeout-minutes: 15

    strategy:
      matrix:
        node-version: [18, 20]

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: "npm"

      - name: Install Dependencies
        run: npm ci

      - name: Run Linter & Tests
        run: |
          npm run lint --if-present
          npm test
""",
    "go": """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions: read-all

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Test Go Code
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: "1.22"
          cache: true

      - name: Verify Dependencies
        run: go mod verify

      - name: Run Tests with Race Detector
        run: go test -v -race ./...
""",
    "rust": """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions: read-all

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Build & Test Rust
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Rust Cache
        uses: Swatinem/rust-cache@v2

      - name: Cargo Check & Test
        run: |
          cargo check --all-targets
          cargo test --all-targets
""",
}


def audit_workflow_file(file_path: Path) -> List[Dict[str, Any]]:
    """Audits a single GitHub Actions YAML file for security anti-patterns."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        sys.stderr.write(f"Warning: could not read {file_path}: {err}\n")
        return findings

    lines = content.splitlines()

    has_permissions = False
    in_jobs = False
    current_job = ""
    job_has_timeout = False

    for idx, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Top level permissions
        if re.match(r'^permissions:', raw_line):
            has_permissions = True

        # Unpinned actions
        action_match = re.search(r'uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([A-Za-z0-9_.-]+)', line)
        if action_match:
            action_name = action_match.group(1)
            action_ref = action_match.group(2)
            if action_ref.lower() in ("main", "master", "latest", "head"):
                findings.append({
                    "id": "CI-UNPINNED-ACTION",
                    "severity": "CRITICAL",
                    "file": str(file_path),
                    "line": idx,
                    "snippet": line,
                    "message": f"Action '{action_name}' is pinned to mutable branch '@{action_ref}'. Pin to specific tag or commit SHA.",
                })

        # pull_request_target warning
        if re.search(r'\bpull_request_target\b', line):
            findings.append({
                "id": "CI-PULL-REQUEST-TARGET",
                "severity": "CRITICAL",
                "file": str(file_path),
                "line": idx,
                "snippet": line,
                "message": "Dangerous 'pull_request_target' trigger detected. Forks can potentially access repo secrets.",
            })

        # Job timeout tracking
        if re.match(r'^jobs:', raw_line):
            in_jobs = True
            continue

        if in_jobs:
            job_match = re.match(r'^\s\s([A-Za-z0-9_.-]+):', raw_line)
            if job_match and not raw_line.strip().startswith("timeout-minutes:"):
                # Check previous job timeout
                if current_job and not job_has_timeout:
                    findings.append({
                        "id": "CI-MISSING-TIMEOUT",
                        "severity": "WARNING",
                        "file": str(file_path),
                        "line": idx,
                        "snippet": f"Job: {current_job}",
                        "message": f"Job '{current_job}' does not define 'timeout-minutes'. Hung runners will exhaust pipeline minutes.",
                    })
                current_job = job_match.group(1)
                job_has_timeout = False

            if re.search(r'timeout-minutes:\s*\d+', line):
                job_has_timeout = True

    # Check last job in file
    if current_job and not job_has_timeout:
        findings.append({
            "id": "CI-MISSING-TIMEOUT",
            "severity": "WARNING",
            "file": str(file_path),
            "line": len(lines),
            "snippet": f"Job: {current_job}",
            "message": f"Job '{current_job}' does not define 'timeout-minutes'.",
        })

    if not has_permissions:
        findings.append({
            "id": "CI-BROAD-PERMISSIONS",
            "severity": "WARNING",
            "file": str(file_path),
            "line": 1,
            "snippet": "Missing top-level permissions",
            "message": "No top-level 'permissions: read-all' declared. Workflow may inherit broad default write tokens.",
        })

    return findings


def audit_repository_ci(repo_root: Path) -> Dict[str, Any]:
    """Audits all GitHub Actions workflows in repository."""
    workflows_dir = repo_root / ".github" / "workflows"
    all_findings = []
    scanned_files = []

    if workflows_dir.exists():
        for f in workflows_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".yml", ".yaml"):
                scanned_files.append(str(f))
                all_findings.extend(audit_workflow_file(f))

    critical_count = sum(1 for f in all_findings if f["severity"] == "CRITICAL")
    warning_count = sum(1 for f in all_findings if f["severity"] == "WARNING")

    status = "fail" if critical_count > 0 else "pass"
    return {
        "status": status,
        "workflows_dir": str(workflows_dir),
        "files_scanned": scanned_files,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "findings": all_findings,
    }


def format_ci_report(res: Dict[str, Any]) -> str:
    """Formats CI audit report for CLI output."""
    lines = []
    icon = "✅ PASSED" if res["status"] == "pass" else "❌ FAILED"
    lines.append(f"🔄 CI/CD Security Audit for: {res['workflows_dir']}")
    lines.append(f"   • Status: {icon}")
    lines.append(f"   • Workflows Scanned: {len(res['files_scanned'])}")
    lines.append(f"   • Critical Issues: {res['critical_count']}")
    lines.append(f"   • Warnings: {res['warning_count']}")

    if res["findings"]:
        lines.append("\nFindings:")
        for f in res["findings"]:
            lvl_icon = "🚨" if f["severity"] == "CRITICAL" else "⚠️"
            fname = Path(f["file"]).name
            lines.append(f"   {lvl_icon} [{f['severity']}] {f['id']} ({fname}:{f['line']}): {f['message']}")
    else:
        if not res["files_scanned"]:
            lines.append("   • (No workflows found. Run 'atk ci --init' to scaffold a pipeline.)")
        else:
            lines.append("   • All workflows enforce timeout bounds, explicit permissions, and pinned actions.")
    return "\n".join(lines)


def init_ci_pipeline(repo_root: Path, stack: str):
    """Scaffolds a GitHub Actions CI workflow for the specified stack."""
    if stack not in CI_TEMPLATES:
        print(f"❌ Unsupported stack: '{stack}'. Choose from: {', '.join(CI_TEMPLATES.keys())}", file=sys.stderr)
        sys.exit(1)

    wf_dir = repo_root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    ci_path = wf_dir / "ci.yml"

    if ci_path.exists():
        print(f"⚠️ CI workflow already exists at {ci_path}. Refusing to overwrite.")
    else:
        ci_path.write_text(CI_TEMPLATES[stack], encoding="utf-8")
        print(f"✅ Scaffolding hardened GitHub Actions CI pipeline for {stack}: {ci_path}")


def main():
    parser = argparse.ArgumentParser(description="CI/CD Pipeline Synthesizer & Workflow Security Auditor.")
    parser.add_argument("--init", action="store_true", help="Scaffold hardened GitHub Actions CI pipeline")
    parser.add_argument(
        "--stack",
        choices=["python", "node", "go", "rust"],
        default="python",
        help="Technology stack for CI pipeline (default: python)",
    )
    parser.add_argument("--audit", action="store_true", help="Audit existing workflows in .github/workflows/")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if CRITICAL findings exist")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--dir", type=str, default=None, help="Repository root path (default: current)")

    args = parser.parse_args()
    repo_root = Path(args.dir).resolve() if args.dir else Path.cwd()

    if args.init:
        init_ci_pipeline(repo_root, args.stack)
        sys.exit(0)

    # Default to audit if --audit or no flags provided
    res = audit_repository_ci(repo_root)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(format_ci_report(res))

    if args.check and res["critical_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
