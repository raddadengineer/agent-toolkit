#!/usr/bin/env python3
"""
manage_release.py — Semantic Versioning, Conventional Commits & Changelog Manager

Parses Conventional Commits since the last git tag, calculates SemVer bumps,
updates CHANGELOG.md, and drafts Markdown release notes.

Usage:
    python3 manage_release.py --bump
    python3 manage_release.py --notes
    python3 manage_release.py --changelog
    python3 manage_release.py --check
    python3 manage_release.py --json
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def run_git(cmd: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Runs a git command and returns stdout string, or None on failure."""
    try:
        res = subprocess.run(
            ["git"] + cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
        return None
    except OSError as err:
        sys.stderr.write(f"Git command failed: {err}\n")
        return None


def get_latest_tag(repo_root: Path) -> str:
    """Gets the most recent git tag or defaults to v0.0.0."""
    tag = run_git(["describe", "--tags", "--abbrev=0"], cwd=repo_root)
    if tag:
        return tag
    return "v0.0.0"


def parse_semver(tag_str: str) -> Tuple[int, int, int]:
    """Parses semver string (e.g. v1.2.3 or 1.2.3) into (major, minor, patch)."""
    clean = tag_str.lstrip("v").strip()
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', clean)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0


def get_commits_since_tag(repo_root: Path, tag: str) -> List[Dict[str, str]]:
    """Retrieves commits between tag and HEAD."""
    if tag == "v0.0.0":
        log_out = run_git(["log", "--pretty=format:%h|%s"], cwd=repo_root)
    else:
        log_out = run_git(["log", f"{tag}..HEAD", "--pretty=format:%h|%s"], cwd=repo_root)

    if not log_out:
        return []

    commits = []
    for line in log_out.splitlines():
        if "|" in line:
            h, msg = line.split("|", 1)
            commits.append({"hash": h.strip(), "message": msg.strip()})
    return commits


def analyze_commits(commits: List[Dict[str, str]]) -> Dict[str, Any]:
    """Categorizes commits and calculates recommended semver bump."""
    features = []
    fixes = []
    perf = []
    refactors = []
    chores = []
    breaking = []

    has_breaking = False
    has_feat = False

    for c in commits:
        msg = c["message"]
        h = c["hash"]

        # Check breaking
        if "BREAKING CHANGE:" in msg or re.search(r'^[a-z]+!(\([^)]+\))?:', msg):
            has_breaking = True
            breaking.append(f"{msg} ({h})")

        # Categorize
        if re.match(r'^feat(\([^)]+\))?:', msg):
            has_feat = True
            clean_msg = re.sub(r'^feat(\([^)]+\))?:\s*', '', msg)
            features.append(f"{clean_msg} ({h})")
        elif re.match(r'^fix(\([^)]+\))?:', msg):
            clean_msg = re.sub(r'^fix(\([^)]+\))?:\s*', '', msg)
            fixes.append(f"{clean_msg} ({h})")
        elif re.match(r'^perf(\([^)]+\))?:', msg):
            clean_msg = re.sub(r'^perf(\([^)]+\))?:\s*', '', msg)
            perf.append(f"{clean_msg} ({h})")
        elif re.match(r'^refactor(\([^)]+\))?:', msg):
            clean_msg = re.sub(r'^refactor(\([^)]+\))?:\s*', '', msg)
            refactors.append(f"{clean_msg} ({h})")
        else:
            chores.append(f"{msg} ({h})")

    if has_breaking:
        bump = "major"
    elif has_feat:
        bump = "minor"
    else:
        bump = "patch"

    return {
        "bump": bump,
        "breaking": breaking,
        "features": features,
        "fixes": fixes,
        "perf": perf,
        "refactors": refactors,
        "chores": chores,
        "total_commits": len(commits),
    }


def compute_next_version(current_tag: str, bump: str) -> str:
    """Computes next semver tag."""
    major, minor, patch = parse_semver(current_tag)
    has_v = current_tag.startswith("v")

    if bump == "major":
        next_ver = f"{major + 1}.0.0"
    elif bump == "minor":
        next_ver = f"{major}.{minor + 1}.0"
    else:
        next_ver = f"{major}.{minor}.{patch + 1}"

    return f"v{next_ver}" if has_v else next_ver


def generate_release_notes(next_tag: str, analysis: Dict[str, Any]) -> str:
    """Formats markdown release notes."""
    today = datetime.date.today().isoformat()
    lines = []
    lines.append(f"## [{next_tag}] — {today}\n")

    if analysis["breaking"]:
        lines.append("### 🚨 BREAKING CHANGES")
        for b in analysis["breaking"]:
            lines.append(f"- {b}")
        lines.append("")

    if analysis["features"]:
        lines.append("### 🚀 Features")
        for f in analysis["features"]:
            lines.append(f"- {f}")
        lines.append("")

    if analysis["fixes"]:
        lines.append("### 🐛 Bug Fixes")
        for f in analysis["fixes"]:
            lines.append(f"- {f}")
        lines.append("")

    if analysis["perf"]:
        lines.append("### ⚡ Performance Improvements")
        for p in analysis["perf"]:
            lines.append(f"- {p}")
        lines.append("")

    if analysis["refactors"]:
        lines.append("### ♻️ Refactoring")
        for r in analysis["refactors"]:
            lines.append(f"- {r}")
        lines.append("")

    if analysis["chores"]:
        lines.append("### 🔧 Maintenance & Chores")
        for c in analysis["chores"][:10]:
            lines.append(f"- {c}")
        if len(analysis["chores"]) > 10:
            lines.append(f"- ... and {len(analysis['chores']) - 10} more chore commits")
        lines.append("")

    if analysis["total_commits"] == 0:
        lines.append("- *(No commits recorded since last release)*\n")

    return "\n".join(lines).strip()


def update_changelog(repo_root: Path, notes: str, next_tag: str):
    """Prepends new release notes to CHANGELOG.md."""
    changelog_path = repo_root / "CHANGELOG.md"
    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n---\n\n"

    if not changelog_path.exists():
        content = header + notes + "\n"
        changelog_path.write_text(content, encoding="utf-8")
        print(f"✅ Created initial {changelog_path}")
    else:
        existing = changelog_path.read_text(encoding="utf-8")
        if f"[{next_tag}]" in existing:
            print(f"⚠️ Section for {next_tag} already exists in CHANGELOG.md. Skipping.")
            return

        sep = "---\n\n"
        if sep in existing:
            parts = existing.split(sep, 1)
            updated = parts[0] + sep + notes + "\n\n---\n\n" + parts[1]
        else:
            updated = header + notes + "\n\n---\n\n" + existing

        changelog_path.write_text(updated, encoding="utf-8")
        print(f"✅ Updated {changelog_path} with {next_tag}")


def check_release_readiness(repo_root: Path) -> Dict[str, Any]:
    """Verifies that repository is in a clean state ready for tagging."""
    status_out = run_git(["status", "--porcelain"], cwd=repo_root) or ""
    branch_out = run_git(["branch", "--show-current"], cwd=repo_root) or "detached"

    clean_tree = len(status_out.strip()) == 0
    on_main = branch_out in ("main", "master")

    issues = []
    if not clean_tree:
        issues.append("Working tree contains uncommitted changes. Stash or commit before release.")
    if not on_main:
        issues.append(f"Not on main/master branch (current: '{branch_out}').")

    ready = clean_tree and on_main
    return {
        "ready": ready,
        "branch": branch_out,
        "clean_tree": clean_tree,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description="Semantic Versioning, Conventional Commits & Changelog Manager.")
    parser.add_argument("--bump", action="store_true", help="Calculate recommended SemVer bump")
    parser.add_argument("--notes", action="store_true", help="Generate Markdown release notes")
    parser.add_argument("--changelog", action="store_true", help="Update or create CHANGELOG.md")
    parser.add_argument("--check", action="store_true", help="Verify release readiness (clean tree, main branch)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--dir", "--path", "--repo", dest="dir", type=str, default=None, help="Repository root path (default: current)")

    args = parser.parse_args()
    repo_root = Path(args.dir).resolve() if args.dir else Path.cwd()

    if args.check:
        readiness = check_release_readiness(repo_root)
        if args.json:
            print(json.dumps(readiness, indent=2))
        else:
            icon = "✅ READY" if readiness["ready"] else "❌ BLOCKED"
            print(f"🚀 Release Readiness Check: {icon}")
            print(f"   • Active Branch: {readiness['branch']}")
            print(f"   • Clean Working Tree: {'Yes' if readiness['clean_tree'] else 'No'}")
            if readiness["issues"]:
                print(f"\nBlockers:")
                for iss in readiness["issues"]:
                    print(f"   🚨 {iss}")
        sys.exit(0 if readiness["ready"] else 1)

    latest_tag = get_latest_tag(repo_root)
    commits = get_commits_since_tag(repo_root, latest_tag)
    analysis = analyze_commits(commits)
    next_tag = compute_next_version(latest_tag, analysis["bump"])

    if args.json:
        out = {
            "current_tag": latest_tag,
            "next_tag": next_tag,
            "bump": analysis["bump"],
            "total_commits": analysis["total_commits"],
            "analysis": analysis,
        }
        print(json.dumps(out, indent=2))
        sys.exit(0)

    if args.changelog:
        notes = generate_release_notes(next_tag, analysis)
        update_changelog(repo_root, notes, next_tag)
        sys.exit(0)

    if args.notes:
        notes = generate_release_notes(next_tag, analysis)
        print(notes)
        sys.exit(0)

    # Default to bump output
    print(f"🚀 Release Version Calculator")
    print(f"   • Current Tag: {latest_tag}")
    print(f"   • Commits Since Tag: {analysis['total_commits']}")
    print(f"   • Recommended Bump: {analysis['bump'].upper()}")
    print(f"   • Next Version: {next_tag}")


if __name__ == "__main__":
    main()
