#!/usr/bin/env python3
"""
dream_consolidator.py — Solo Developer Out-of-Band Memory Consolidator ("Dreamer")

Analyzes session ledgers (SESSION_LOG.md), conversation transcripts, and execution logs
to autonomously extract patterns, anti-patterns, and operational rules offline.
Generates structured memory proposals for one-click human review and auto-promotion.

Usage:
    python3 dream_consolidator.py --analyze
    python3 dream_consolidator.py --review
    python3 dream_consolidator.py --auto-promote
    python3 dream_consolidator.py --transcript /path/to/transcript.jsonl
    python3 dream_consolidator.py --output MEMORY_PROPOSAL.md
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

try:
    from scripts.manage_memory import get_repo_root, record_memory, list_memories, VALID_CATEGORIES
except ImportError:
    try:
        from manage_memory import get_repo_root, record_memory, list_memories, VALID_CATEGORIES
    except ImportError:
        def get_repo_root(start_path: Optional[Path] = None) -> Path:
            start = (start_path or Path.cwd()).resolve()
            cur = start
            while cur != cur.parent:
                if (cur / ".git").exists() or (cur / "AGENTS.md").exists() or (cur / "skills").exists():
                    return cur
                cur = cur.parent
            return start


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Runs a shell command and returns output, or None on error."""
    try:
        res = subprocess.run(
            cmd,
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


def find_latest_transcript(repo_root: Path) -> Optional[Path]:
    """Searches for recent Antigravity, Gemini, or Claude transcript logs."""
    # 1. Check Antigravity / Gemini app data directories
    candidates = []
    gemini_brain = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if gemini_brain.exists():
        for t_file in gemini_brain.glob("*/.system_generated/logs/transcript.jsonl"):
            try:
                candidates.append((t_file.stat().st_mtime, t_file))
            except Exception:
                pass

    # 2. Check local repo logs
    for local_dir in [repo_root / ".agents" / "logs", repo_root / "logs"]:
        if local_dir.exists():
            for t_file in local_dir.glob("*.jsonl"):
                try:
                    candidates.append((t_file.stat().st_mtime, t_file))
                except Exception:
                    pass

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None


def parse_session_log(log_path: Path) -> List[Dict[str, Any]]:
    """Extracts recent sessions from SESSION_LOG.md."""
    if not log_path.exists():
        return []

    try:
        content = log_path.read_text(encoding="utf-8")
    except Exception:
        return []

    sessions = []
    matches = list(re.finditer(r"### Session \[(.*?)\] — (.*?)\n", content))
    for i, m in enumerate(matches):
        timestamp = m.group(1).strip()
        title = m.group(2).strip()
        start_idx = m.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start_idx:end_idx]

        goal_match = re.search(r"-\s+\*\*Goal\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", body)
        goal = "\n".join(re.findall(r"-\s+(.*)", goal_match.group(1))).strip() if goal_match else ""

        changes = []
        changes_match = re.search(r"-\s+\*\*Changes Completed\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", body)
        if changes_match:
            changes = [c.strip() for c in re.findall(r"-\s+(.*)", changes_match.group(1))]

        val_match = re.search(r"-\s+\*\*Validation\*\*:\s*\n((?:\s+-\s+.*(?:\n|$))+)", body)
        val = "\n".join(re.findall(r"-\s+(.*)", val_match.group(1))).strip() if val_match else ""

        sessions.append({
            "timestamp": timestamp,
            "title": title,
            "goal": goal,
            "changes": changes,
            "validation": val,
            "body": body,
        })
    return sessions


def parse_transcript_entries(transcript_path: Path) -> List[Dict[str, Any]]:
    """Reads JSON Lines transcript entries."""
    if not transcript_path.exists():
        return []

    entries = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return entries


def extract_candidates_from_transcript(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyzes transcript trajectory steps for error loops and winning sequences."""
    candidates = []
    error_patterns = [
        r"(AssertionError:[^\n\r]+)",
        r"(SyntaxError:[^\n\r]+)",
        r"(ImportError:[^\n\r]+)",
        r"(ModuleNotFoundError:[^\n\r]+)",
        r"(TypeError:[^\n\r]+)",
        r"(AttributeError:[^\n\r]+)",
        r"(KeyError:[^\n\r]+)",
        r"(Command exited with code [1-9]\d*)",
        r"(FileNotFoundError:[^\n\r]+)",
        r"(PermissionError:[^\n\r]+)",
    ]

    for i, entry in enumerate(entries):
        content = entry.get("content", "")
        if not isinstance(content, str):
            content = str(content)

        # Check for errors in tool outputs
        for pattern in error_patterns:
            match = re.search(pattern, content)
            if match:
                err_text = match.group(1).strip()
                # Clean error title
                clean_err_title = err_text.split("\n")[0][:60].strip()
                clean_err_title = re.sub(r"\s+", " ", clean_err_title).strip()
                clean_err_title = re.sub(r"[:\(\)]+$", "", clean_err_title).strip()

                # Inspect subsequent steps to see how the error was resolved
                resolution_step = ""
                for j in range(i + 1, min(i + 5, len(entries))):
                    next_content = entries[j].get("content", "")
                    if "Command exited with code 0" in next_content or "OK" in next_content:
                        res_lines = [l.strip() for l in next_content.splitlines() if l.strip() and not l.startswith("Created At") and not l.startswith("Completed At")]
                        resolution_step = "\n".join(res_lines[:5]).strip()
                        break

                candidates.append({
                    "category": "anti-patterns",
                    "title": f"Avoid {clean_err_title}",
                    "rationale": f"Encountered error during execution: '{err_text}'",
                    "content": f"## Error Context\n```\n{err_text}\n```\n\n## Resolution / Corrective Action\n"
                               f"{resolution_step or 'Ensure prerequisite checks or valid syntax are applied.'}\n",
                    "tags": ["runtime-error", "auto-extracted"],
                    "confidence": "HIGH" if resolution_step else "MEDIUM",
                })
                break
    return candidates


def extract_candidates_from_sessions(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extracts candidate patterns and rules from recent session logs."""
    candidates = []

    for s in sessions[:3]:  # Analyze 3 most recent sessions
        val = s.get("validation", "")
        goal = s.get("goal", "")
        title = s.get("title", "")
        changes = s.get("changes", [])

        # Look for verification patterns
        if "exit 0" in val or "Ran" in val or "passed" in val:
            val_cmds = [line for line in val.splitlines() if any(k in line for k in ["pytest", "unittest", "check", "test", "lint"])]
            cmd_summary = "; ".join(val_cmds[:2]) if val_cmds else val[:100]

            candidates.append({
                "category": "patterns",
                "title": f"Verification for {title[:40]}",
                "rationale": f"Session '{title}' successfully passed validation: {cmd_summary}",
                "content": f"## Context\nAccomplished goal: {goal or title}\n\n## Proven Verification\n"
                           f"Always verify with:\n```bash\n{cmd_summary or val}\n```\n",
                "tags": ["verification", "workflow", "session-validated"],
                "confidence": "HIGH",
            })

        # Look for security or architecture changes
        for ch in changes:
            ch_lower = ch.lower()
            if any(k in ch_lower for k in ["security", "harden", "auth", "token", "sha", "secret"]):
                candidates.append({
                    "category": "rules",
                    "title": f"Security rule from {title[:35]}",
                    "rationale": f"Security-relevant change recorded in session: {ch}",
                    "content": f"## Security Mandate\n{ch}\n\nEnforced as repository security rule.\n",
                    "tags": ["security", "rules", "best-practice"],
                    "confidence": "MEDIUM",
                })
    return candidates


def deduplicate_candidates(candidates: List[Dict[str, Any]], existing_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters out candidates that are duplicates or already exist in memory."""
    existing_titles = {m.get("title", "").lower() for m in existing_memories}
    existing_ids = {m.get("id", "").lower() for m in existing_memories}

    unique = []
    seen = set()

    for c in candidates:
        t_key = c.get("title", "").lower().strip()
        if not t_key or t_key in seen or t_key in existing_titles:
            continue
        # Also check if similar ID exists
        c_slug = re.sub(r"[^\w\s-]", "", t_key).replace(" ", "-")
        if c_slug in existing_ids:
            continue

        seen.add(t_key)
        unique.append(c)

    return unique


def dream_session_learnings(
    repo_root: Path,
    transcript_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Runs the solo dreaming consolidation pass."""
    t_path = transcript_path or find_latest_transcript(repo_root)
    log_path = repo_root / "SESSION_LOG.md"

    sessions = parse_session_log(log_path)
    entries = parse_transcript_entries(t_path) if t_path else []

    raw_candidates = []
    raw_candidates.extend(extract_candidates_from_sessions(sessions))
    if entries:
        raw_candidates.extend(extract_candidates_from_transcript(entries))

    try:
        existing = list_memories(repo_root)
    except Exception:
        existing = []

    candidates = deduplicate_candidates(raw_candidates, existing)

    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "transcript_source": str(t_path) if t_path else "None (used session ledger)",
        "sessions_analyzed": len(sessions),
        "transcript_steps_analyzed": len(entries),
        "total_candidates": len(candidates),
        "candidates": candidates,
    }


def format_proposal_markdown(dream_result: Dict[str, Any]) -> str:
    """Formats dream candidates as an actionable proposal document."""
    lines = [
        "# 🌙 Offline Memory Consolidation Proposal (Dreamer)",
        f"**Generated**: `{dream_result['timestamp']}`  ",
        f"**Transcript Source**: `{dream_result['transcript_source']}`  ",
        f"**Sessions Analyzed**: {dream_result['sessions_analyzed']}  ",
        f"**Candidates Proposed**: {dream_result['total_candidates']}\n",
        "---",
        "",
    ]

    if not dream_result["candidates"]:
        lines.append("✨ No new patterns or anti-patterns detected. Current memory store is up to date.\n")
        return "\n".join(lines)

    lines.append("## 📋 Proposed Memory Candidates for Review\n")

    for i, c in enumerate(dream_result["candidates"], 1):
        cat_badge = c.get("category", "patterns").upper()
        conf = c.get("confidence", "MEDIUM")
        lines.append(f"### {i}. [{cat_badge}] {c['title']} (`Confidence: {conf}`)")
        lines.append(f"**Rationale**: {c['rationale']}")
        if c.get("tags"):
            lines.append(f"**Tags**: `{'`, `'.join(c['tags'])}`")
        lines.append("\n**Proposed Content**:\n```markdown")
        lines.append(c["content"].strip())
        lines.append("```\n")

    lines.append("---\n")
    lines.append("### 🎯 Next Steps")
    lines.append("- To promote all high-confidence candidates: `atk dream --auto-promote`")
    lines.append("- To review interactively: `atk dream --review`\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Solo Developer Out-of-Band Memory Consolidator.")
    parser.add_argument("--analyze", action="store_true", help="Analyze logs and display candidate memories")
    parser.add_argument("--review", action="store_true", help="Interactively review and approve candidate memories")
    parser.add_argument("--auto-promote", action="store_true", help="Automatically promote high-confidence candidates")
    parser.add_argument("--transcript", type=str, help="Explicit path to transcript.jsonl")
    parser.add_argument("--output", type=str, help="Write markdown proposal to specified file path")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")

    args = parser.parse_args()
    repo_root = get_repo_root()

    t_path = Path(args.transcript).resolve() if args.transcript else None
    result = dream_session_learnings(repo_root, transcript_path=t_path)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    proposal_md = format_proposal_markdown(result)

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.write_text(proposal_md, encoding="utf-8")
        print(f"📄 Saved memory consolidation proposal to: {out_p}")

    if args.auto_promote:
        promoted = 0
        for c in result["candidates"]:
            if c.get("confidence") == "HIGH":
                try:
                    record_memory(
                        repo_root=repo_root,
                        title=c["title"],
                        category=c["category"],
                        content=c["content"],
                        tags=c.get("tags", []),
                        scope="project",
                    )
                    promoted += 1
                    print(f"✅ Auto-promoted [{c['category']}]: {c['title']}")
                except Exception as e:
                    print(f"⚠️ Failed to record candidate {c['title']}: {e}")
        print(f"\n✨ Successfully auto-promoted {promoted} candidate(s) to repo memory.")
        return

    if args.review:
        print(f"🌙 Reviewing {result['total_candidates']} memory candidates:\n")
        accepted = 0
        for i, c in enumerate(result["candidates"], 1):
            print(f"--------------------------------------------------")
            print(f"Candidate {i}/{result['total_candidates']}: [{c['category'].upper()}] {c['title']}")
            print(f"Rationale: {c['rationale']}")
            print(f"Tags: {', '.join(c.get('tags', []))}")
            print(f"Content:\n{c['content']}\n")

            try:
                choice = input("Accept and save to repo memory? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nReview cancelled.")
                break

            if choice in ["y", "yes"]:
                try:
                    record_memory(
                        repo_root=repo_root,
                        title=c["title"],
                        category=c["category"],
                        content=c["content"],
                        tags=c.get("tags", []),
                        scope="project",
                    )
                    accepted += 1
                    print("✅ Saved.")
                except Exception as e:
                    print(f"⚠️ Error saving: {e}")
            else:
                print("⏭️ Skipped.")
        print(f"\n✨ Review complete. Saved {accepted} new memory entries.")
        return

    # Default output: print formatted markdown proposal
    print(proposal_md)


if __name__ == "__main__":
    main()
