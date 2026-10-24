#!/usr/bin/env python3
"""
sync_context.py — Universal Context File Synchronizer & Session Ledger Helper

Keeps project context files (AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules, etc.)
bit-for-bit synchronized across AI development environments, and manages
structured session handover logs in SESSION_LOG.md.

Usage:
    python3 sync_context.py --check
    python3 sync_context.py --sync [SOURCE]
    python3 sync_context.py --status
    python3 sync_context.py --init
    python3 sync_context.py --log --title "Feature X" --goal "Add feature X" ...
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

DEFAULT_CANDIDATE_FILES = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]
CONFIG_FILE_NAMES = [".sync-context.json", ".agents/context-config.json"]


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

    # 1. Try git rev-parse
    git_toplevel = run_git_command(["rev-parse", "--show-toplevel"], cwd=start)
    if git_toplevel:
        p = Path(git_toplevel).resolve()
        if p.exists() and p.is_dir():
            return p

    # 2. Walk up directory tree searching for standard root markers
    markers = [
        ".git",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "project.yml",
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


def load_config(repo_root: Path) -> dict:
    """Loads optional project-specific context configuration if present."""
    for cfg_rel in CONFIG_FILE_NAMES:
        cfg_path = repo_root / cfg_rel
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Warning: Failed to read config {cfg_path}: {e}")
    return {}


def get_tracked_files(repo_root: Path, explicit_files: Optional[List[str]] = None) -> List[str]:
    """Determines list of context files to sync/check."""
    if explicit_files:
        return explicit_files

    cfg = load_config(repo_root)
    if "context_files" in cfg and isinstance(cfg["context_files"], list):
        return cfg["context_files"]

    # Auto-detect which default candidates exist in repo root
    existing = [f for f in DEFAULT_CANDIDATE_FILES if (repo_root / f).exists()]
    if existing:
        return existing

    # Default fallback to the standard triad
    return DEFAULT_CANDIDATE_FILES


def calculate_checksum(file_path: Path) -> str:
    """Calculates SHA-256 checksum for a file."""
    if not file_path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_sync(repo_root: Path, tracked_files: List[str]) -> bool:
    """Checks if all tracked context files exist and have identical contents."""
    checksums = {}
    missing = []

    for fname in tracked_files:
        p = repo_root / fname
        if not p.exists():
            missing.append(fname)
        else:
            checksums[fname] = calculate_checksum(p)

    if missing:
        print(f"❌ Missing context files: {', '.join(missing)}")
        if checksums:
            print(f"   Existing files:")
            for fname, cs in checksums.items():
                print(f"     {fname}: {cs[:16]}...")
        return False

    unique_hashes = set(checksums.values())
    if len(unique_hashes) == 1:
        print(f"✅ All context files ({', '.join(tracked_files)}) are in sync.")
        print(f"   SHA-256: {list(unique_hashes)[0][:16]}...")
        return True
    else:
        print("❌ Context files are OUT of sync:")
        for fname, cs in checksums.items():
            print(f"   {fname}: {cs[:16]}...")
        return False


def detect_latest_source(repo_root: Path, tracked_files: List[str]) -> str:
    """Detects which existing file was modified most recently."""
    latest_file = tracked_files[0]
    latest_mtime = -1.0
    for fname in tracked_files:
        p = repo_root / fname
        if p.exists():
            mtime = p.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file = fname
    return latest_file


def sync_files(repo_root: Path, tracked_files: List[str], source_name: Optional[str] = None):
    """Copies content from source file to all other tracked context files."""
    if not source_name:
        source_name = detect_latest_source(repo_root, tracked_files)

    source_path = repo_root / source_name
    if not source_path.exists():
        print(f"❌ Source file not found: {source_path}")
        sys.exit(1)

    with open(source_path, "rb") as f:
        content = f.read()

    print(f"🔄 Syncing from source: {source_name} ({len(content)} bytes)")
    for fname in tracked_files:
        if fname == source_name:
            continue
        dest_path = repo_root / fname
        # Ensure parent directories exist if relative paths include subdirs
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content)
        print(f"   ✅ Synced {fname}")

    check_sync(repo_root, tracked_files)


def get_project_name(repo_root: Path) -> str:
    """Infers project/repository name from git remote, package manifests, or directory name."""
    # 1. Try git remote
    git_remote = run_git_command(["config", "--get", "remote.origin.url"], cwd=repo_root)
    if git_remote:
        # e.g. git@github.com:user/repo.git or https://github.com/user/repo
        base = git_remote.rstrip("/").split("/")[-1]
        if base.endswith(".git"):
            base = base[:-4]
        if base:
            return base

    # 2. Try package.json
    pkg_json = repo_root / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "name" in data and data["name"]:
                    return str(data["name"])
        except Exception:
            pass

    # 3. Fallback to folder name
    return repo_root.name or "Project"


def log_session(
    repo_root: Path,
    title: str,
    goal: str,
    changes: List[str],
    validation: str,
    next_steps: List[str],
    log_filename: str = "SESSION_LOG.md",
):
    """Appends/prepends a structured session entry to SESSION_LOG.md."""
    log_file = repo_root / log_filename
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    project_name = get_project_name(repo_root)

    entry_lines = [
        f"\n### Session [{timestamp}] — {title}\n\n",
        f"- **Goal**:\n  - {goal}\n" if goal else "",
        "- **Changes Completed**:\n",
    ]
    for c in changes:
        entry_lines.append(f"  - {c}\n")

    if validation:
        entry_lines.append(f"- **Validation**:\n  - {validation}\n")

    if next_steps:
        entry_lines.append("- **Next Steps / Handover**:\n")
        for n in next_steps:
            entry_lines.append(f"  - {n}\n")

    entry_lines.append("\n---\n")
    entry_text = "".join(entry_lines)

    if not log_file.exists():
        initial_header = (
            f"# {project_name} — Session Log & Handover Ledger\n\n"
            "This ledger records engineering session summaries, completed features, "
            "architecture updates, and next steps to maintain continuity across development sessions.\n\n"
            "---\n"
        )
        content = initial_header + entry_text
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(log_file, "r", encoding="utf-8") as f:
            existing = f.read()

        header_end = existing.find("---\n")
        if header_end != -1:
            header_end += 4
            updated = existing[:header_end] + entry_text + existing[header_end:]
        else:
            updated = entry_text + existing

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(updated)

    print(f"✅ Successfully recorded session entry in {log_file}")


def init_project(repo_root: Path, tracked_files: List[str], log_filename: str = "SESSION_LOG.md"):
    """Initializes a new project with baseline context files and session log."""
    project_name = get_project_name(repo_root)
    print(f"🚀 Initializing session closer & context files for '{project_name}' at {repo_root}")

    # 1. Create primary context file if none exist
    existing = [f for f in tracked_files if (repo_root / f).exists()]
    if not existing:
        primary = tracked_files[0]
        primary_path = repo_root / primary
        primary_content = (
            f"# {project_name} — Agent Guidelines & Project Context\n\n"
            f"Welcome to {project_name}. This document maintains active project context, "
            f"architectural guidelines, tech stack details, and agent instructions.\n\n"
            "## 🏗️ Technology Stack & Environment\n"
            "- Specify core language, framework, runtime, and tools here.\n\n"
            "## 📂 Project Structure\n"
            "- Outline key directories and architectural entry points.\n"
        )
        with open(primary_path, "w", encoding="utf-8") as f:
            f.write(primary_content)
        print(f"   Created baseline {primary}")
        existing = [primary]

    # 2. Sync to all other tracked files
    sync_files(repo_root, tracked_files, source_name=existing[0])

    # 3. Create SESSION_LOG.md if missing
    log_path = repo_root / log_filename
    if not log_path.exists():
        initial_header = (
            f"# {project_name} — Session Log & Handover Ledger\n\n"
            "This ledger records engineering session summaries, completed features, "
            "architecture updates, and next steps to maintain continuity across development sessions.\n\n"
            "---\n"
        )
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(initial_header)
        print(f"   Created initial {log_filename}")
    else:
        print(f"   {log_filename} already exists")

    print("✨ Initialization complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Universal Context File Synchronizer & Session Ledger Helper."
    )
    parser.add_argument(
        "--path",
        "--dir",
        "--repo",
        dest="path",
        type=str,
        default=None,
        help="Path to repository root (defaults to auto-detected root)",
    )
    parser.add_argument(
        "--files",
        type=str,
        default=None,
        help="Comma-separated list of context files (e.g. AGENTS.md,CLAUDE.md,GEMINI.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if all context files are in sync",
    )
    parser.add_argument(
        "--sync",
        nargs="?",
        const="",
        default=None,
        help="Sync context files from source (default: auto-detect latest modified)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print checksum status of tracked context files",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize context files and SESSION_LOG.md in the repository",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Log a session entry to SESSION_LOG.md",
    )
    parser.add_argument("--title", type=str, default="Engineering Session", help="Session title")
    parser.add_argument("--goal", type=str, default="", help="Session goal")
    parser.add_argument(
        "--change",
        action="append",
        dest="changes",
        default=[],
        help="Change item (can be specified multiple times)",
    )
    parser.add_argument(
        "--validation",
        type=str,
        default="",
        help="Validation result (e.g., test suite or build verification status)",
    )
    parser.add_argument(
        "--next-step",
        action="append",
        dest="next_steps",
        default=[],
        help="Next step / handover item (can be specified multiple times)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="SESSION_LOG.md",
        help="Name of session log file (default: SESSION_LOG.md)",
    )

    args = parser.parse_args()

    start_dir = Path(args.path) if args.path else Path.cwd()
    repo_root = get_repo_root(start_dir)

    explicit_files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else None
    tracked_files = get_tracked_files(repo_root, explicit_files)

    if args.init:
        init_project(repo_root, tracked_files, args.log_file)
        sys.exit(0)

    if args.log:
        changes = args.changes if args.changes else ["Engineering updates completed."]
        next_steps = args.next_steps if args.next_steps else []
        log_session(
            repo_root=repo_root,
            title=args.title,
            goal=args.goal,
            changes=changes,
            validation=args.validation,
            next_steps=next_steps,
            log_filename=args.log_file,
        )
        sys.exit(0)

    if args.sync is not None:
        src = args.sync.strip() if args.sync.strip() else None
        sync_files(repo_root, tracked_files, source_name=src)
        sys.exit(0)

    if args.status:
        print(f"📁 Repository: {repo_root}")
        print(f"📄 Tracked context files ({len(tracked_files)}):")
        for fname in tracked_files:
            p = repo_root / fname
            cs = calculate_checksum(p)
            status = "FOUND" if p.exists() else "MISSING"
            print(f"   {fname:15} [{status}] : {cs[:24]}...")
        sys.exit(0)

    # Default action or --check
    in_sync = check_sync(repo_root, tracked_files)
    sys.exit(0 if in_sync else 1)


if __name__ == "__main__":
    main()
