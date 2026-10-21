#!/usr/bin/env python3
"""
verify_migrations.py — Database Migration Safety & Lock Contention Validator

Audits database migrations for reversibility, zero-downtime compatibility,
and dangerous table-locking hazards.

Usage:
    python3 verify_migrations.py --dir /path/to/migrations --check
    python3 verify_migrations.py --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

HAZARDS = [
    {
        "id": "MIG-LOCK-ADD-NOT-NULL",
        "severity": "CRITICAL",
        "description": "ADD COLUMN NOT NULL without DEFAULT will lock table or fail on non-empty rows",
        "pattern": re.compile(r'ADD\s+COLUMN\s+.*?NOT\s+NULL(?!\s+DEFAULT)', re.IGNORECASE),
    },
    {
        "id": "MIG-LOCK-NON-CONCURRENT-INDEX",
        "severity": "HIGH",
        "description": "CREATE INDEX without CONCURRENTLY locks table against writes during build",
        "pattern": re.compile(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?!CONCURRENTLY)', re.IGNORECASE),
    },
    {
        "id": "MIG-BREAK-DROP-COLUMN",
        "severity": "HIGH",
        "description": "DROP COLUMN causes immediate breaking change for running services",
        "pattern": re.compile(r'DROP\s+COLUMN\s+', re.IGNORECASE),
    },
    {
        "id": "MIG-BREAK-DROP-TABLE",
        "severity": "HIGH",
        "description": "DROP TABLE causes immediate breaking change for running services",
        "pattern": re.compile(r'DROP\s+TABLE\s+', re.IGNORECASE),
    },
    {
        "id": "MIG-LOCK-ALTER-TYPE",
        "severity": "HIGH",
        "description": "ALTER COLUMN TYPE causes full table rewrite with exclusive table lock",
        "pattern": re.compile(r'ALTER\s+COLUMN\s+\w+\s+TYPE\s+', re.IGNORECASE),
    },
    {
        "id": "MIG-LOCK-RENAME",
        "severity": "MEDIUM",
        "description": "RENAME TABLE/COLUMN breaks active queries and requires phased migration",
        "pattern": re.compile(r'RENAME\s+(?:TABLE|COLUMN)\s+', re.IGNORECASE),
    },
]


def audit_sql_migration(file_path: Path) -> List[Dict[str, Any]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.splitlines()
    for hazard in HAZARDS:
        for idx, line in enumerate(lines, 1):
            if hazard["pattern"].search(line):
                findings.append({
                    "id": hazard["id"],
                    "severity": hazard["severity"],
                    "file": str(file_path),
                    "line": idx,
                    "snippet": line.strip()[:120],
                    "description": hazard["description"],
                })

    return findings


def check_alembic_reversibility(file_path: Path) -> List[Dict[str, Any]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    # Look for def downgrade(): pass or empty downgrade
    if "def downgrade" in content:
        downgrade_match = re.search(r'def downgrade\(\)[^:]*:\s*(pass|\.\.\.|return None)?\s*(?:\n\s*\n|\Z)', content)
        if downgrade_match and downgrade_match.group(1):
            findings.append({
                "id": "MIG-IRREVERSIBLE",
                "severity": "HIGH",
                "file": str(file_path),
                "line": 1,
                "snippet": "def downgrade(): pass",
                "description": "Migration contains empty downgrade() routine; rollback is disabled.",
            })
    return findings


def audit_migrations(root_dir: Path) -> Dict[str, Any]:
    findings = []
    scanned_files = []

    migration_keywords = ["migration", "migrate", "alembic", "schema"]

    for root, dirs, files in os.walk(root_dir):
        # Only inspect relevant migration directories or files
        is_migration_dir = any(k in root.lower() for k in migration_keywords)

        for f in files:
            path = Path(root) / f
            is_mig_file = any(k in f.lower() for k in migration_keywords) or (f.endswith(".sql") and is_migration_dir)

            if is_mig_file and (f.endswith(".sql") or f.endswith(".py")):
                scanned_files.append(str(path.relative_to(root_dir)))
                sql_findings = audit_sql_migration(path)
                findings.extend(sql_findings)

                if f.endswith(".py"):
                    rev_findings = check_alembic_reversibility(path)
                    findings.extend(rev_findings)

    for item in findings:
        item["file"] = str(Path(item["file"]).relative_to(root_dir))

    criticals = sum(1 for f in findings if f["severity"] == "CRITICAL")
    highs = sum(1 for f in findings if f["severity"] == "HIGH")

    return {
        "status": "fail" if (criticals > 0 or highs > 0) else "pass",
        "total_scanned": len(scanned_files),
        "total_findings": len(findings),
        "critical_count": criticals,
        "high_count": highs,
        "scanned_files": scanned_files,
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Database Migration Safety & Lock Contention Validator.")
    parser.add_argument("--dir", type=str, default=".", help="Root directory containing migrations")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if critical or high hazards are found")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    target_dir = Path(args.dir).resolve()

    report = audit_migrations(target_dir)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"🗄️ Database Migration Safety Report for: {target_dir}")
        print(f"   • Status: {'❌ FAILED' if report['status'] == 'fail' else '✅ PASSED'}")
        print(f"   • Migrations Scanned: {report['total_scanned']}")
        print(f"   • Hazards Found: {report['total_findings']} (Critical: {report['critical_count']}, High: {report['high_count']})")

        if report["findings"]:
            print("\n🚨 Identified Hazards:")
            for f in report["findings"][:10]:
                print(f"   [{f['severity']}] {f['id']}: {f['description']}")
                print(f"       -> {f['file']}:{f['line']}")
                print(f"       -> {f['snippet']}")

    if args.check and report["status"] == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
