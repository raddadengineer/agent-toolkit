#!/usr/bin/env python3
"""
manage_adr.py — Architecture Decision Record (ADR) Manager & Sentinel

Manages, indexes, and validates Architecture Decision Records (ADRs) in docs/adr/
following the Michael Nygard template format.

Usage:
    python3 manage_adr.py --init
    python3 manage_adr.py --new "Adopt Redis for Caching"
    python3 manage_adr.py --list
    python3 manage_adr.py --audit
    python3 manage_adr.py --list --json
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_repo_root() -> Path:
    """Finds repository root by searching upward for markers."""
    cur = Path.cwd().resolve()
    while cur != cur.parent:
        if (cur / ".git").exists() or ((cur / "skills").exists() and (cur / "agents").exists()):
            return cur
        cur = cur.parent
    return Path.cwd().resolve()


def slugify(text: str) -> str:
    """Converts a title into a URL/filename-friendly kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def get_adr_dir(repo_root: Path, custom_dir: Optional[str] = None) -> Path:
    if custom_dir:
        return Path(custom_dir).resolve()
    return repo_root / "docs" / "adr"


def parse_adr_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Extracts metadata and sections from an ADR markdown file."""
    if not file_path.is_file() or file_path.suffix.lower() != ".md" or file_path.name == "README.md":
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        sys.stderr.write(f"Warning: could not read {file_path}: {err}\n")
        return None

    # Number and title
    title_match = re.search(r'^#\s+(\d+)\.\s*(.*)$', content, re.MULTILINE)
    if not title_match:
        # Fallback to general # header
        title_match = re.search(r'^#\s*(.*)$', content, re.MULTILINE)
        if not title_match:
            return None
        num = re.search(r'^(\d+)', file_path.name)
        num_str = num.group(1) if num else "0000"
        title = title_match.group(1).strip()
    else:
        num_str = title_match.group(1).strip()
        title = title_match.group(2).strip()

    # Status
    status_match = re.search(r'^\s*Status:\s*([A-Za-z]+)', content, re.MULTILINE | re.IGNORECASE)
    status = status_match.group(1).upper() if status_match else "PROPOSED"

    # Date
    date_match = re.search(r'^\s*Date:\s*([0-9-]+)', content, re.MULTILINE)
    date_str = date_match.group(1) if date_match else "Unknown"

    has_context = "## Context" in content
    has_decision = "## Decision" in content
    has_consequences = "## Consequences" in content

    return {
        "number": int(num_str) if num_str.isdigit() else 0,
        "number_str": num_str.zfill(4),
        "title": title,
        "status": status,
        "date": date_str,
        "file_name": file_path.name,
        "file_path": str(file_path),
        "valid_structure": has_context and has_decision and has_consequences,
    }


def list_adrs(adr_dir: Path) -> List[Dict[str, Any]]:
    """Lists all ADRs sorted by sequence number."""
    if not adr_dir.exists():
        return []
    records = []
    for f in adr_dir.glob("*.md"):
        record = parse_adr_file(f)
        if record:
            records.append(record)
    records.sort(key=lambda r: r["number"])
    return records


def update_readme_index(adr_dir: Path, records: List[Dict[str, Any]]):
    """Regenerates docs/adr/README.md with a table of all ADRs."""
    lines = []
    lines.append("# Architecture Decision Log\n")
    lines.append("This directory records all Architectural Decision Records (ADRs) for the project.\n")
    lines.append("| Number | Title | Status | Date |")
    lines.append("| :--- | :--- | :--- | :--- |")

    for r in records:
        link = f"[{r['title']}]({r['file_name']})"
        status_badge = f"`{r['status']}`"
        lines.append(f"| {r['number_str']} | {link} | {status_badge} | {r['date']} |")

    lines.append("\n---\n*Maintained via `agent-toolkit system-architect`.*")
    (adr_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def init_adr_repo(adr_dir: Path) -> Path:
    """Initializes docs/adr directory with 0000 record and index."""
    adr_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()

    record_0000 = adr_dir / "0000-record-architecture-decisions.md"
    if not record_0000.exists():
        content = f"""# 0000. Record Architecture Decisions

Date: {today}
Status: ACCEPTED

## Context & Problem Statement
We need to record architectural decisions made on this project so that past context,
evaluated trade-offs, and technical rationales are preserved and transparent for all
contributors and AI coding assistants.

## Decision Drivers
- Need for explicit architectural history and rationale.
- Prevent repeating past debates or accidentally violating established boundaries.
- Provide AI coding agents with verifiable design constraints.

## Considered Options
1. Informal commit messages or PR descriptions.
2. Architecture Decision Records (ADRs) stored in `docs/adr/`.

## Decision Outcome
Chosen option: **ADRs in `docs/adr/`**, because records are versioned in Git alongside
source code, lightweight to maintain in Markdown, and readable by both humans and AI.

### Positive Consequences
- Architectural rationale is preserved alongside codebase history.
- Structured ADR status lifecycle (`PROPOSED`, `ACCEPTED`, `SUPERSEDED`, `DEPRECATED`).

### Negative Consequences / Trade-offs
- Requires lightweight discipline to author an ADR when proposing architectural shifts.
"""
        record_0000.write_text(content, encoding="utf-8")
        print(f"✅ Created baseline {record_0000.name}")

    records = list_adrs(adr_dir)
    update_readme_index(adr_dir, records)
    print(f"✨ Initialized Architecture Decision Log in {adr_dir}")
    return record_0000


def create_new_adr(adr_dir: Path, title: str) -> Path:
    """Creates a new numbered ADR file."""
    if not adr_dir.exists():
        init_adr_repo(adr_dir)

    records = list_adrs(adr_dir)
    next_num = 1
    if records:
        next_num = max(r["number"] for r in records) + 1

    num_str = str(next_num).zfill(4)
    slug = slugify(title)
    file_name = f"{num_str}-{slug}.md"
    file_path = adr_dir / file_name

    today = datetime.date.today().isoformat()

    content = f"""# {num_str}. {title}

Date: {today}
Status: PROPOSED

## Context & Problem Statement
Describe the business or technical context and the problem we are solving. What
forces and constraints are influencing this design?

## Decision Drivers
- [Driver 1, e.g. latency budget < 100ms]
- [Driver 2, e.g. zero external infrastructure dependency]
- [Driver 3, e.g. team familiarity & operational simplicity]

## Considered Options
1. **Option 1**: [Description]
2. **Option 2**: [Description]
3. **Option 3**: [Description]

## Decision Outcome
Chosen option: **[Option X]**, because [concrete rationale].

### Positive Consequences
- [Positive consequence 1]
- [Positive consequence 2]

### Negative Consequences / Trade-offs
- [Trade-off or operational overhead 1]
- [Mitigation strategy]

## Compliance & Verification
- How will this architecture be verified in code reviews or test suites?
"""
    file_path.write_text(content, encoding="utf-8")
    print(f"✅ Created new ADR: {file_path}")

    # Refresh index
    records = list_adrs(adr_dir)
    update_readme_index(adr_dir, records)
    return file_path


def audit_adrs(adr_dir: Path) -> Dict[str, Any]:
    """Audits ADRs for sequence gaps, invalid statuses, or structural defects."""
    records = list_adrs(adr_dir)
    issues = []

    if not records:
        return {"status": "pass", "records_count": 0, "issues": []}

    expected_num = records[0]["number"]
    valid_statuses = {"PROPOSED", "ACCEPTED", "SUPERSEDED", "DEPRECATED"}

    for r in records:
        # Check sequence
        if r["number"] != expected_num:
            issues.append({
                "type": "sequence_gap",
                "severity": "WARNING",
                "file": r["file_name"],
                "message": f"Sequence gap: expected {str(expected_num).zfill(4)}, found {r['number_str']}",
            })
            expected_num = r["number"]
        expected_num += 1

        # Check status
        if r["status"] not in valid_statuses:
            issues.append({
                "type": "invalid_status",
                "severity": "CRITICAL",
                "file": r["file_name"],
                "message": f"Invalid status '{r['status']}'. Must be one of: {', '.join(sorted(valid_statuses))}",
            })

        # Check sections
        if not r["valid_structure"]:
            issues.append({
                "type": "missing_sections",
                "severity": "WARNING",
                "file": r["file_name"],
                "message": "Missing required ADR sections (Context, Decision, Consequences)",
            })

    # Always keep README updated
    update_readme_index(adr_dir, records)

    status = "fail" if any(i["severity"] == "CRITICAL" for i in issues) else "pass"
    return {
        "status": status,
        "records_count": len(records),
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Architecture Decision Record (ADR) Manager & Sentinel.")
    parser.add_argument("--dir", "--path", "--repo", dest="dir", type=str, default=None, help="Custom ADR directory path (default: docs/adr)")
    parser.add_argument("--init", action="store_true", help="Initialize docs/adr with baseline 0000 record")
    parser.add_argument("--new", type=str, default=None, help="Author a new ADR with specified title")
    parser.add_argument("--list", action="store_true", help="List all recorded ADRs and their statuses")
    parser.add_argument("--audit", action="store_true", help="Audit ADRs for structural defects and refresh index")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    repo_root = get_repo_root()
    adr_dir = get_adr_dir(repo_root, args.dir)

    if args.init:
        init_adr_repo(adr_dir)
        sys.exit(0)

    if args.new:
        create_new_adr(adr_dir, args.new)
        sys.exit(0)

    if args.audit:
        res = audit_adrs(adr_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"📐 ADR Audit for: {adr_dir}")
            print(f"   • Total ADRs: {res['records_count']}")
            print(f"   • Status: {'✅ PASSED' if res['status'] == 'pass' else '❌ FAILED'}")
            if res["issues"]:
                for iss in res["issues"]:
                    icon = "🚨" if iss["severity"] == "CRITICAL" else "⚠️"
                    print(f"   {icon} [{iss['severity']}] {iss['file']}: {iss['message']}")
            else:
                print(f"   • All ADRs sequentially ordered and structurally sound.")
        sys.exit(0 if res["status"] == "pass" else 1)

    # Default to list if --list or no flags provided
    records = list_adrs(adr_dir)
    if args.json:
        print(json.dumps(records, indent=2))
    else:
        if not records:
            print(f"ℹ️ No ADRs found in {adr_dir}. Run 'atk adr --init' to get started.")
        else:
            print(f"📐 Architecture Decision Log ({len(records)} records in {adr_dir}):\n")
            print(f"{'Number':<8} {'Status':<12} {'Date':<12} {'Title'}")
            print("-" * 65)
            for r in records:
                print(f"{r['number_str']:<8} {r['status']:<12} {r['date']:<12} {r['title']}")


if __name__ == "__main__":
    main()
