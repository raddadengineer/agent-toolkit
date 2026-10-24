#!/usr/bin/env python3
"""
prime_session.py — Universal Session Primer & Orientation Helper

Inspects repository status, git branch state, context file synchronization,
and extracts recent handover notes from SESSION_LOG.md to prime an AI agent
or developer at the start of a coding session.

Usage:
    python3 prime_session.py
    python3 prime_session.py --json
    python3 prime_session.py --handover-only
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONTEXT_FILES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]


def run_git_command(cmd: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Runs a git command and returns stripped stdout, or None on failure."""
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
    except Exception:
        pass
    return None


def get_repo_root(start_path: Optional[Path] = None) -> Path:
    """Finds repository root using git rev-parse or by traversing upward for markers."""
    start = (start_path or Path.cwd()).resolve()
    git_toplevel = run_git_command(["rev-parse", "--show-toplevel"], cwd=start)
    if git_toplevel:
        p = Path(git_toplevel).resolve()
        if p.exists() and p.is_dir():
            return p

    markers = [
        ".git",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        ".agents",
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
    ]
    cur = start
    while cur != cur.parent:
        for marker in markers:
            if (cur / marker).exists():
                return cur
        cur = cur.parent

    return start


def calculate_checksum(file_path: Path) -> str:
    """Calculates SHA-256 checksum for a file."""
    if not file_path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_context_sync(repo_root: Path) -> Dict[str, Any]:
    """Inspects context files and reports sync status."""
    existing_files = [f for f in DEFAULT_CONTEXT_FILES if (repo_root / f).exists()]
    if not existing_files:
        return {
            "status": "missing_all",
            "files": {},
            "in_sync": False,
            "message": "No standard context files found (AGENTS.md, CLAUDE.md, GEMINI.md).",
        }

    hashes = {}
    for f in existing_files:
        hashes[f] = calculate_checksum(repo_root / f)

    unique_hashes = set(hashes.values())
    in_sync = (len(unique_hashes) == 1) and (len(existing_files) == len(DEFAULT_CONTEXT_FILES))

    return {
        "status": "ok" if in_sync else "out_of_sync",
        "files": hashes,
        "existing_count": len(existing_files),
        "total_expected": len(DEFAULT_CONTEXT_FILES),
        "in_sync": in_sync,
    }


def parse_last_session(log_file: Path) -> Optional[Dict[str, Any]]:
    """Parses the most recent session entry from SESSION_LOG.md."""
    if not log_file.exists():
        return None

    try:
        content = log_file.read_text(encoding="utf-8")
    except Exception:
        return None

    # Match pattern: ### Session [YYYY-MM-DD HH:MM] — <Title>
    session_header_match = re.search(r"### Session \[(.*?)\] — (.*?)\n", content)
    if not session_header_match:
        return None

    timestamp = session_header_match.group(1).strip()
    title = session_header_match.group(2).strip()
    start_pos = session_header_match.end()

    # Find next session or separator
    next_session = content.find("### Session [", start_pos)
    sep_match = content.find("\n---\n", start_pos)
    end_pos = len(content)
    if next_session != -1 and (sep_match == -1 or next_session < sep_match):
        end_pos = next_session
    elif sep_match != -1:
        end_pos = sep_match

    session_body = content[start_pos:end_pos]

    # Extract Goal
    goal = ""
    goal_match = re.search(r"-\s+\*\*Goal\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", session_body)
    if goal_match:
        goal = "\n".join(re.findall(r"-\s+(.*)", goal_match.group(1))).strip()

    # Extract Changes Completed
    changes = []
    changes_match = re.search(r"-\s+\*\*Changes Completed\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", session_body)
    if changes_match:
        changes = [c.strip() for c in re.findall(r"-\s+(.*)", changes_match.group(1))]

    # Extract Validation
    validation = ""
    val_match = re.search(r"-\s+\*\*Validation\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", session_body)
    if val_match:
        validation = "\n".join(re.findall(r"-\s+(.*)", val_match.group(1))).strip()

    # Extract Next Steps / Handover
    next_steps = []
    next_match = re.search(r"-\s+\*\*Next Steps / Handover\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", session_body)
    if next_match:
        next_steps = [n.strip() for n in re.findall(r"-\s+(.*)", next_match.group(1))]

    return {
        "timestamp": timestamp,
        "title": title,
        "goal": goal,
        "changes": changes,
        "validation": validation,
        "next_steps": next_steps,
    }


def get_git_state(repo_root: Path) -> Dict[str, Any]:
    """Inspects the git status of the repository."""
    branch = run_git_command(["branch", "--show-current"], cwd=repo_root) or "detached/unknown"
    status_short = run_git_command(["status", "--short"], cwd=repo_root) or ""
    last_commit = run_git_command(["log", "-1", "--oneline"], cwd=repo_root) or "No commits yet"

    lines = [line.strip() for line in status_short.splitlines() if line.strip()]
    modified = [l for l in lines if not l.startswith("??")]
    untracked = [l for l in lines if l.startswith("??")]

    return {
        "branch": branch,
        "clean": len(lines) == 0,
        "modified_count": len(modified),
        "untracked_count": len(untracked),
        "last_commit": last_commit,
        "status_lines": lines,
    }


def gather_session_brief(repo_root: Path) -> Dict[str, Any]:
    """Gathers complete orientation info for the session."""
    git_state = get_git_state(repo_root)
    context_sync = check_context_sync(repo_root)
    last_session = parse_last_session(repo_root / "SESSION_LOG.md")

    return {
        "repo_root": str(repo_root),
        "repo_name": repo_root.name,
        "git": git_state,
        "context_sync": context_sync,
        "last_session": last_session,
    }


def format_markdown_brief(brief: Dict[str, Any]) -> str:
    """Formats the brief as a human and agent-readable orientation report."""
    lines = []
    lines.append(f"# 🧭 Session Primer: {brief['repo_name']}")
    lines.append(f"**Path**: `{brief['repo_root']}`\n")

    # 1. Git & Workspace Status
    git = brief["git"]
    lines.append("## 🌿 Repository Status")
    lines.append(f"- **Current Branch**: `{git['branch']}`")
    lines.append(f"- **Latest Commit**: {git['last_commit']}")
    if git["clean"]:
        lines.append("- **Working Tree**: ✨ Clean (no uncommitted changes)")
    else:
        lines.append(
            f"- **Working Tree**: ⚠️ Dirty ({git['modified_count']} modified/staged, {git['untracked_count']} untracked)"
        )
        if git["status_lines"]:
            lines.append("  ```text")
            for sl in git["status_lines"][:8]:
                lines.append(f"  {sl}")
            if len(git["status_lines"]) > 8:
                lines.append(f"  ... and {len(git['status_lines']) - 8} more")
            lines.append("  ```")

    # 2. Context Files Synchronization
    cs = brief["context_sync"]
    lines.append("\n## 📄 Context Synchronization")
    if cs["in_sync"]:
        lines.append(f"- ✅ All {cs['existing_count']} context files are bit-for-bit in sync.")
    else:
        lines.append(
            f"- ⚠️ Context files are out of sync or missing ({cs.get('existing_count', 0)}/{cs.get('total_expected', 3)} found)."
        )
        lines.append("  *Tip: Run `python3 sync_context.py --sync` to synchronize context files.*")

    # 3. Last Session Handover
    ls = brief["last_session"]
    lines.append("\n## 📋 Last Session Handover")
    if ls:
        lines.append(f"- **Session**: {ls['title']} (`{ls['timestamp']}`)")
        if ls["goal"]:
            lines.append(f"- **Previous Goal**: {ls['goal']}")
        if ls["validation"]:
            lines.append(f"- **Previous Validation**: {ls['validation']}")
        if ls["next_steps"]:
            lines.append("- **Recommended Next Steps / Agenda**:")
            for ns in ls["next_steps"]:
                lines.append(f"  - [ ] {ns}")
        else:
            lines.append("- **Next Steps**: (None recorded in previous session)")
    else:
        lines.append("- *No prior session log found in `SESSION_LOG.md`.*")

    lines.append("\n---")
    lines.append("🎯 **Ready to proceed**: Align on the immediate goal and execute.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Universal Session Primer & Orientation Helper.")
    parser.add_argument("--path", "--dir", "--repo", dest="path", type=str, default=None, help="Repository root path")
    parser.add_argument("--json", action="store_true", help="Output raw JSON brief")
    parser.add_argument(
        "--handover-only",
        action="store_true",
        help="Print only the next steps / handover items from previous session",
    )

    args = parser.parse_args()
    start_dir = Path(args.path) if args.path else Path.cwd()
    repo_root = get_repo_root(start_dir)

    brief = gather_session_brief(repo_root)

    if args.json:
        print(json.dumps(brief, indent=2))
        return

    if args.handover_only:
        ls = brief.get("last_session")
        if ls and ls.get("next_steps"):
            for step in ls["next_steps"]:
                print(f"- {step}")
        else:
            print("No previous handover next steps found.")
        return

    print(format_markdown_brief(brief))


if __name__ == "__main__":
    main()
