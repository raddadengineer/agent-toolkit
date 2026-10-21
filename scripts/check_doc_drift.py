#!/usr/bin/env python3
"""
check_doc_drift.py — Documentation & Schema Drift Sentinel

Validates that documented agents, skills, and commands in README.md and documentation
match the actual filesystem assets and detects broken internal links.

Usage:
    python3 check_doc_drift.py --check
    python3 check_doc_drift.py --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def get_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    while cur != cur.parent:
        if (cur / ".git").exists() or ((cur / "skills").exists() and (cur / "agents").exists()):
            return cur
        cur = cur.parent
    return Path.cwd().resolve()


def check_documentation_drift(repo_root: Path) -> Dict[str, Any]:
    findings = []

    # 1. Check skills on disk vs documented
    disk_skills = set()
    skills_dir = repo_root / "skills"
    if skills_dir.exists():
        disk_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()}

    # 2. Check agents on disk vs documented
    disk_agents = set()
    agents_dir = repo_root / "agents"
    if agents_dir.exists():
        disk_agents = {d.name for d in agents_dir.iterdir() if d.is_dir()}

    # 3. Read README.md
    readme_path = repo_root / "README.md"
    readme_content = ""
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")

    # Check that every skill on disk is mentioned in README
    for skill in disk_skills:
        if skill not in readme_content:
            findings.append({
                "type": "undocumented_skill",
                "severity": "WARNING",
                "item": skill,
                "message": f"Skill '{skill}' exists on disk but is not documented in README.md",
            })

    # Check that every agent on disk is mentioned in README
    for agent in disk_agents:
        if agent not in readme_content:
            findings.append({
                "type": "undocumented_agent",
                "severity": "WARNING",
                "item": agent,
                "message": f"Subagent '{agent}' exists on disk but is not documented in README.md",
            })

    # 4. Check for broken file markdown links in README
    # Matches [text](file:///path) or [text](./path) or [text](path/to/file)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    for match in link_pattern.finditer(readme_content):
        link_target = match.group(2).split("#")[0].strip()
        # Only check local paths
        if link_target.startswith("http://") or link_target.startswith("https://"):
            continue
        if link_target.startswith("file://"):
            target_path = Path(link_target.replace("file://", ""))
        else:
            target_path = repo_root / link_target

        # If it looks like a path and doesn't exist
        if "/" in link_target and not target_path.exists():
            findings.append({
                "type": "broken_link",
                "severity": "CRITICAL",
                "item": link_target,
                "message": f"Broken markdown reference in README.md: '{link_target}' not found on disk",
            })

    criticals = sum(1 for f in findings if f["severity"] == "CRITICAL")
    warnings = sum(1 for f in findings if f["severity"] == "WARNING")

    return {
        "status": "fail" if criticals > 0 else "pass",
        "disk_skills": sorted(list(disk_skills)),
        "disk_agents": sorted(list(disk_agents)),
        "total_findings": len(findings),
        "critical_count": criticals,
        "warning_count": warnings,
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Documentation & Schema Drift Sentinel.")
    parser.add_argument("--dir", type=str, default=None, help="Repository root directory")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if critical doc drift or broken links are found")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    repo_root = Path(args.dir).resolve() if args.dir else get_repo_root()

    report = check_documentation_drift(repo_root)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"📖 Documentation Drift Audit for: {repo_root}")
        print(f"   • Status: {'❌ FAILED' if report['status'] == 'fail' else '✅ PASSED'}")
        print(f"   • Skills on Disk: {len(report['disk_skills'])}")
        print(f"   • Agents on Disk: {len(report['disk_agents'])}")
        print(f"   • Total Findings: {report['total_findings']} (Critical: {report['critical_count']}, Warnings: {report['warning_count']})")

        if report["findings"]:
            print("\n🚨 Findings:")
            for f in report["findings"]:
                print(f"   [{f['severity']}] {f['type']}: {f['message']}")

    if args.check and report["status"] == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
