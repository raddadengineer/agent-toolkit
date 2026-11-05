#!/usr/bin/env python3
"""
manage_memory.py — Solo Developer Scoped Memory Manager

Manages persistent repository-level and global developer memories across sessions.
Implements indexed, content-addressed storage for patterns, anti-patterns, rules,
and architectural decisions with fast keyword and tag recall.

Usage:
    python3 manage_memory.py init
    python3 manage_memory.py record --category patterns --title "Title" --content "..."
    python3 manage_memory.py recall "query string"
    python3 manage_memory.py list
    python3 manage_memory.py audit
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VALID_CATEGORIES = ["patterns", "anti-patterns", "rules", "decisions"]
VALID_SCOPES = ["project", "global"]


def get_repo_root(start_path: Optional[Path] = None) -> Path:
    """Finds repository root using git or marker files."""
    start = (start_path or Path.cwd()).resolve()
    cur = start
    while cur != cur.parent:
        if (cur / ".git").exists() or (cur / "AGENTS.md").exists() or (cur / "skills").exists():
            return cur
        cur = cur.parent
    return start


def get_global_memory_dir() -> Path:
    """Returns the global memory directory path (~/.agents/memory)."""
    return Path.home() / ".agents" / "memory"


def get_memory_base_dir(repo_root: Path, scope: str = "project") -> Path:
    """Resolves base memory directory for project or global scope."""
    if scope == "global":
        return get_global_memory_dir()
    return repo_root / "memory"


def slugify(text: str) -> str:
    """Generates a clean URL/filename slug from title."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "untitled"


def file_sha256(path: Path) -> str:
    """Calculates SHA-256 checksum for a file."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_index(memory_dir: Path) -> Dict[str, Any]:
    """Loads index.json from memory directory or creates a fresh structure."""
    index_file = memory_dir / "index.json"
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "version": "1.0",
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "entries": {},
    }


def save_index(memory_dir: Path, index_data: Dict[str, Any]) -> None:
    """Persists index.json atomically."""
    memory_dir.mkdir(parents=True, exist_ok=True)
    index_file = memory_dir / "index.json"
    index_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp_file = memory_dir / "index.json.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, sort_keys=True)
    temp_file.replace(index_file)


def init_memory(repo_root: Path, scope: str = "project") -> Path:
    """Initializes memory directories and empty index."""
    mem_dir = get_memory_base_dir(repo_root, scope=scope)
    for cat in VALID_CATEGORIES:
        (mem_dir / cat).mkdir(parents=True, exist_ok=True)

    index_data = load_index(mem_dir)
    save_index(mem_dir, index_data)

    readme_file = mem_dir / "README.md"
    if not readme_file.exists():
        readme_file.write_text(
            f"# Persistent Agent Memory ({scope.capitalize()} Scope)\n\n"
            "This directory contains structured, indexed memory for AI coding sessions.\n\n"
            "## Categories\n"
            "- `patterns/`: Proven solution patterns and workflows that succeeded.\n"
            "- `anti-patterns/`: Tricky bugs, gotchas, and failure modes to avoid.\n"
            "- `rules/`: Concrete operational constraints and repository guidelines.\n"
            "- `decisions/`: Architecture Decision Records and technical choices.\n\n"
            "Managed via `atk memory` and `manage_memory.py`.\n",
            encoding="utf-8",
        )
    return mem_dir


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML-like frontmatter and body from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    frontmatter_raw = parts[1]
    body = parts[2].lstrip("\r\n")

    metadata: Dict[str, Any] = {}
    for line in frontmatter_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                items = [i.strip().strip('"').strip("'") for i in val[1:-1].split(",") if i.strip()]
                metadata[key] = items
            else:
                metadata[key] = val
    return metadata, body


def format_markdown_memory(
    memory_id: str,
    title: str,
    category: str,
    scope: str,
    tags: List[str],
    content: str,
    created_at: str,
    updated_at: str,
) -> str:
    """Formats full markdown document with frontmatter."""
    tags_formatted = f"[{', '.join(tags)}]"
    lines = [
        "---",
        f"id: {memory_id}",
        f'title: "{title}"',
        f"category: {category}",
        f"scope: {scope}",
        f"tags: {tags_formatted}",
        f"created_at: {created_at}",
        f"updated_at: {updated_at}",
        "---",
        "",
        f"# {title}",
        "",
        content.strip(),
        "",
    ]
    return "\n".join(lines)


def record_memory(
    repo_root: Path,
    title: str,
    category: str,
    content: str,
    tags: Optional[List[str]] = None,
    scope: str = "project",
    memory_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Records or updates a memory entry and updates index.json."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of {VALID_CATEGORIES}")
    if scope not in VALID_SCOPES:
        raise ValueError(f"Invalid scope '{scope}'. Must be one of {VALID_SCOPES}")

    mem_dir = init_memory(repo_root, scope=scope)
    cat_dir = mem_dir / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    mid = memory_id or slugify(title)
    file_path = cat_dir / f"{mid}.md"
    rel_path = f"{category}/{mid}.md"

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    created_at = now_iso
    access_count = 0

    index = load_index(mem_dir)
    if rel_path in index["entries"]:
        existing = index["entries"][rel_path]
        created_at = existing.get("created_at", now_iso)
        access_count = existing.get("access_count", 0)

    clean_tags = sorted(list({t.strip().lower() for t in (tags or []) if t.strip()}))

    md_text = format_markdown_memory(
        memory_id=mid,
        title=title,
        category=category,
        scope=scope,
        tags=clean_tags,
        content=content,
        created_at=created_at,
        updated_at=now_iso,
    )
    file_path.write_text(md_text, encoding="utf-8")
    checksum = file_sha256(file_path)

    entry = {
        "id": mid,
        "title": title,
        "category": category,
        "scope": scope,
        "tags": clean_tags,
        "path": rel_path,
        "checksum": checksum,
        "created_at": created_at,
        "updated_at": now_iso,
        "access_count": access_count,
        "last_accessed": now_iso,
    }
    index["entries"][rel_path] = entry
    save_index(mem_dir, index)
    return entry


def recall_memories(
    repo_root: Path,
    query: str,
    category: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Searches memory across index and content, returning ranked matches."""
    scopes_to_search = [scope] if scope else ["project", "global"]
    tokens = [t.lower() for t in re.split(r"\W+", query) if len(t) > 1]

    results = []

    for sc in scopes_to_search:
        mem_dir = get_memory_base_dir(repo_root, scope=sc)
        if not mem_dir.exists():
            continue
        index = load_index(mem_dir)
        index_updated = False

        for rel_path, entry in index["entries"].items():
            if category and entry.get("category") != category:
                continue

            file_path = mem_dir / rel_path
            if not file_path.exists():
                continue

            title = entry.get("title", "").lower()
            tags = [t.lower() for t in entry.get("tags", [])]
            entry_cat = entry.get("category", "").lower()

            score = 0.0
            matched_terms = []

            # Exact query match in title
            if query.lower() in title:
                score += 15.0
                matched_terms.append("title-exact")

            # Token matches in title, tags, category
            for token in tokens:
                if token in title:
                    score += 5.0
                    matched_terms.append(f"title:{token}")
                if token in tags:
                    score += 7.0
                    matched_terms.append(f"tag:{token}")
                if token == entry_cat:
                    score += 3.0
                    matched_terms.append(f"category:{token}")

            # Content scan
            try:
                content = file_path.read_text(encoding="utf-8")
                content_lower = content.lower()
                for token in tokens:
                    count = content_lower.count(token)
                    if count > 0:
                        score += min(count * 1.5, 6.0)
                        matched_terms.append(f"content:{token}")
            except Exception:
                content = ""

            if score > 0.0 or not tokens:
                # Update access stats
                entry["access_count"] = entry.get("access_count", 0) + 1
                entry["last_accessed"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                index_updated = True

                match_item = dict(entry)
                match_item["score"] = score
                match_item["matched_terms"] = list(set(matched_terms))
                match_item["file_path"] = str(file_path)
                match_item["snippet"] = content[:300].strip() if content else ""
                results.append(match_item)

        if index_updated:
            save_index(mem_dir, index)

    results.sort(key=lambda x: (x["score"], x.get("updated_at", "")), reverse=True)
    return results[:limit]


def list_memories(
    repo_root: Path,
    category: Optional[str] = None,
    scope: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists all memories matching optional category, scope, and tag filters."""
    scopes_to_search = [scope] if scope else ["project", "global"]
    items = []

    for sc in scopes_to_search:
        mem_dir = get_memory_base_dir(repo_root, scope=sc)
        if not mem_dir.exists():
            continue
        index = load_index(mem_dir)
        for rel_path, entry in index["entries"].items():
            if category and entry.get("category") != category:
                continue
            if tag and tag.lower() not in [t.lower() for t in entry.get("tags", [])]:
                continue
            entry_copy = dict(entry)
            entry_copy["memory_dir"] = str(mem_dir)
            entry_copy["full_path"] = str(mem_dir / rel_path)
            items.append(entry_copy)

    items.sort(key=lambda x: (x.get("category", ""), x.get("title", "")))
    return items


def audit_memory(repo_root: Path, scope: str = "project", repair: bool = False) -> Dict[str, Any]:
    """Audits memory directory for broken checksums, orphaned files, and decay."""
    mem_dir = get_memory_base_dir(repo_root, scope=scope)
    if not mem_dir.exists():
        return {
            "scope": scope,
            "status": "empty",
            "message": "Memory directory does not exist.",
            "issues": [],
        }

    index = load_index(mem_dir)
    issues = []
    repaired_count = 0

    indexed_paths = set(index["entries"].keys())
    disk_paths = set()

    # Check files on disk
    for cat in VALID_CATEGORIES:
        cat_dir = mem_dir / cat
        if not cat_dir.exists():
            continue
        for md_file in cat_dir.glob("*.md"):
            rel_path = f"{cat}/{md_file.name}"
            disk_paths.add(rel_path)

            cur_checksum = file_sha256(md_file)
            if rel_path in index["entries"]:
                stored_checksum = index["entries"][rel_path].get("checksum")
                if stored_checksum and stored_checksum != cur_checksum:
                    issues.append({
                        "type": "checksum_mismatch",
                        "path": rel_path,
                        "expected": stored_checksum,
                        "found": cur_checksum,
                    })
                    if repair:
                        index["entries"][rel_path]["checksum"] = cur_checksum
                        repaired_count += 1
            else:
                # Orphaned file on disk not in index
                issues.append({"type": "orphaned_file", "path": rel_path})
                if repair:
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        fm, body = parse_frontmatter(content)
                        title = fm.get("title", md_file.stem.replace("-", " ").title())
                        tags = fm.get("tags", [])
                        index["entries"][rel_path] = {
                            "id": md_file.stem,
                            "title": title,
                            "category": cat,
                            "scope": scope,
                            "tags": tags,
                            "path": rel_path,
                            "checksum": cur_checksum,
                            "created_at": fm.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                            "updated_at": fm.get("updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                            "access_count": 0,
                            "last_accessed": None,
                        }
                        repaired_count += 1
                    except Exception as e:
                        issues.append({"type": "repair_failure", "path": rel_path, "error": str(e)})

    # Missing files in index but gone from disk
    for ip in indexed_paths:
        if ip not in disk_paths:
            issues.append({"type": "missing_file", "path": ip})
            if repair:
                del index["entries"][ip]
                repaired_count += 1

    if repair and repaired_count > 0:
        save_index(mem_dir, index)

    return {
        "scope": scope,
        "total_indexed": len(index["entries"]),
        "total_on_disk": len(disk_paths),
        "issues_count": len(issues),
        "issues": issues,
        "repaired": repair and repaired_count > 0,
        "repaired_count": repaired_count,
    }


def get_memory_stats(repo_root: Path) -> Dict[str, Any]:
    """Returns memory summary statistics for priming and dashboards."""
    mem_dir = get_memory_base_dir(repo_root, scope="project")
    counts: Dict[str, int] = {cat: 0 for cat in VALID_CATEGORIES}
    if not mem_dir.exists():
        return {"exists": False, "total": 0, "categories": counts}

    index = load_index(mem_dir)
    for entry in index["entries"].values():
        cat = entry.get("category", "")
        if cat in counts:
            counts[cat] += 1

    return {
        "exists": True,
        "total": len(index["entries"]),
        "categories": counts,
        "path": str(mem_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Solo Developer Scoped Memory Manager.")
    subparsers = parser.add_subparsers(dest="command", help="Memory command")

    # init
    init_p = subparsers.add_parser("init", help="Initialize memory directory")
    init_p.add_argument("--scope", choices=VALID_SCOPES, default="project")

    # record
    rec_p = subparsers.add_parser("record", help="Record a new memory")
    rec_p.add_argument("--title", required=True, help="Memory title")
    rec_p.add_argument("--category", required=True, choices=VALID_CATEGORIES, help="Memory category")
    rec_p.add_argument("--content", help="Inline markdown content")
    rec_p.add_argument("--file", help="Path to file containing markdown content")
    rec_p.add_argument("--tags", help="Comma-separated tags")
    rec_p.add_argument("--scope", choices=VALID_SCOPES, default="project")
    rec_p.add_argument("--id", help="Optional explicit memory slug/ID")

    # recall
    rec_q = subparsers.add_parser("recall", help="Recall memories by search query")
    rec_q.add_argument("query", help="Search query string")
    rec_q.add_argument("--category", choices=VALID_CATEGORIES, help="Filter by category")
    rec_q.add_argument("--scope", choices=VALID_SCOPES, help="Filter by scope")
    rec_q.add_argument("--limit", type=int, default=5, help="Max results to return")
    rec_q.add_argument("--json", action="store_true", help="Output JSON format")

    # list
    list_p = subparsers.add_parser("list", help="List stored memories")
    list_p.add_argument("--category", choices=VALID_CATEGORIES, help="Filter by category")
    list_p.add_argument("--scope", choices=VALID_SCOPES, help="Filter by scope")
    list_p.add_argument("--tag", help="Filter by tag")
    list_p.add_argument("--json", action="store_true", help="Output JSON format")

    # show
    show_p = subparsers.add_parser("show", help="Show full content of a memory entry")
    show_p.add_argument("id", help="Memory ID or slug")
    show_p.add_argument("--scope", choices=VALID_SCOPES, default="project")

    # audit
    audit_p = subparsers.add_parser("audit", help="Audit memory integrity and checksums")
    audit_p.add_argument("--scope", choices=VALID_SCOPES, default="project")
    audit_p.add_argument("--repair", action="store_true", help="Automatically repair detected issues")
    audit_p.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()
    repo_root = get_repo_root()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        mem_dir = init_memory(repo_root, scope=args.scope)
        print(f"✨ Initialized memory store in: {mem_dir}")
        return

    if args.command == "record":
        content = args.content or ""
        if args.file:
            content = Path(args.file).read_text(encoding="utf-8")
        if not content:
            print("❌ Error: Memory content must be provided via --content or --file")
            sys.exit(1)

        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        entry = record_memory(
            repo_root=repo_root,
            title=args.title,
            category=args.category,
            content=content,
            tags=tags,
            scope=args.scope,
            memory_id=args.id,
        )
        print(f"✅ Recorded {entry['category']}: {entry['title']} ({entry['path']})")
        return

    if args.command == "recall":
        matches = recall_memories(
            repo_root=repo_root,
            query=args.query,
            category=args.category,
            scope=args.scope,
            limit=args.limit,
        )
        if args.json:
            print(json.dumps(matches, indent=2))
            return

        if not matches:
            print(f"🔍 No memories found matching '{args.query}'.")
            return

        print(f"🧠 Found {len(matches)} relevant memories for '{args.query}':\n")
        for m in matches:
            scope_badge = f"[{m.get('scope', 'project')}]"
            cat_badge = f"[{m.get('category')}]"
            print(f"• {scope_badge} {cat_badge} {m.get('title')} (score: {m.get('score', 0):.1f})")
            if m.get("tags"):
                print(f"  Tags: {', '.join(m.get('tags', []))}")
            if m.get("snippet"):
                snip_lines = m["snippet"].splitlines()[:3]
                for sl in snip_lines:
                    print(f"  | {sl}")
            print(f"  Path: {m.get('path')}\n")
        return

    if args.command == "list":
        items = list_memories(
            repo_root=repo_root,
            category=args.category,
            scope=args.scope,
            tag=args.tag,
        )
        if args.json:
            print(json.dumps(items, indent=2))
            return

        if not items:
            print("📭 No memories currently stored.")
            return

        print(f"📚 Stored Memories ({len(items)} items):\n")
        curr_cat = None
        for it in items:
            cat = it.get("category", "other")
            if cat != curr_cat:
                curr_cat = cat
                print(f"📂 {cat.upper()}:")
            tags_str = f" ({', '.join(it.get('tags', []))})" if it.get("tags") else ""
            print(f"   • [{it.get('scope', 'project')}] {it.get('title')}{tags_str} — {it.get('path')}")
        return

    if args.command == "show":
        mem_dir = get_memory_base_dir(repo_root, scope=args.scope)
        index = load_index(mem_dir)
        target_entry = None
        for rel_path, entry in index["entries"].items():
            if entry.get("id") == args.id or rel_path.endswith(f"{args.id}.md"):
                target_entry = (rel_path, entry)
                break

        if not target_entry:
            print(f"❌ Memory not found: {args.id}")
            sys.exit(1)

        rel_path, entry = target_entry
        full_path = mem_dir / rel_path
        if not full_path.exists():
            print(f"❌ Memory file missing from disk: {full_path}")
            sys.exit(1)

        print(full_path.read_text(encoding="utf-8"))
        return

    if args.command == "audit":
        report = audit_memory(repo_root=repo_root, scope=args.scope, repair=args.repair)
        if args.json:
            print(json.dumps(report, indent=2))
            return

        print(f"🔍 Memory Audit ({report['scope']} scope):")
        print(f"   • Total Indexed: {report.get('total_indexed', 0)}")
        print(f"   • Total on Disk: {report.get('total_on_disk', 0)}")
        print(f"   • Issues Found: {report.get('issues_count', 0)}")

        if report.get("issues"):
            print("\n⚠️ Issues:")
            for iss in report["issues"]:
                print(f"   - [{iss.get('type')}] {iss.get('path')} {iss.get('error', '')}")

        if report.get("repaired"):
            print(f"\n✅ Repaired {report['repaired_count']} issue(s).")
        elif report.get("issues_count", 0) == 0:
            print("✨ Memory integrity is clean.")
        return


if __name__ == "__main__":
    main()
