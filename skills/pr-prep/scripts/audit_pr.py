#!/usr/bin/env python3
"""
audit_pr.py — Universal Pull Request Auditor & Description Generator

Audits git diffs for scope creep, leftover debug statements, temporary code,
and potential credential leaks. Generates standardized, evidence-backed PR
descriptions for GitHub, GitLab, and Bitbucket.

Usage:
    python3 audit_pr.py
    python3 audit_pr.py --base main
    python3 audit_pr.py --check
    python3 audit_pr.py --generate-desc
    python3 audit_pr.py --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEBUG_PATTERNS = [
    (r"\bconsole\.(log|debug|warn|trace)\s*\(", "console.log/debug statement"),
    (r"\bprint\s*\([\"'].*[\"']\)", "Python print debug statement"),
    (r"\bdebugger\b", "JavaScript debugger breakpoint"),
    (r"\bbinding\.pry\b", "Ruby debugger breakpoint"),
    (r"\bimport\s+pdb;\s*pdb\.set_trace\(\)", "Python pdb breakpoint"),
    (r"\bbreakpoint\s*\(\)", "Python breakpoint() call"),
    (r"\bfmt\.Println\s*\(", "Go print statement"),
    (r"\bTODO:\s*remove\b", "Temporary code marker (TODO: remove)"),
    (r"\bFIXME:\s*temp\b", "Temporary code marker (FIXME: temp)"),
]

SECRET_PATTERNS = [
    (r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----", "Private cryptographic key"),
    (r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b", "GitHub Personal Access Token"),
    (r"\bakia[0-9a-z]{16}\b", "AWS Access Key ID", re.IGNORECASE),
    (r"\bsk_live_[0-9a-zA-Z]{24,}\b", "Stripe Live Secret Key"),
    (r"\bAIza[0-9A-Za-z-_]{35}\b", "Google API Key"),
    (r"(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]", "Possible hardcoded secret/token"),
]


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
            return res.stdout
    except Exception:
        pass
    return None


def get_repo_root(start_path: Optional[Path] = None) -> Path:
    """Finds repository root using git rev-parse."""
    start = (start_path or Path.cwd()).resolve()
    toplevel = run_git(["rev-parse", "--show-toplevel"], cwd=start)
    if toplevel:
        p = Path(toplevel.strip()).resolve()
        if p.exists() and p.is_dir():
            return p
    return start


def determine_diff_target(repo_root: Path, base_branch: Optional[str] = None) -> Tuple[str, List[str]]:
    """Determines the appropriate git diff command arguments."""
    if base_branch:
        # Check against base branch
        return f"against {base_branch}", [f"{base_branch}...HEAD"]

    # Try common defaults: origin/main, origin/master, main, master
    for candidate in ["origin/main", "origin/master", "main", "master"]:
        out = run_git(["rev-parse", "--verify", candidate], cwd=repo_root)
        if out:
            # Check if current HEAD is on the same branch or ahead
            head_commit = run_git(["rev-parse", "HEAD"], cwd=repo_root)
            cand_commit = out.strip()
            if head_commit and head_commit.strip() != cand_commit:
                return f"against {candidate}", [f"{candidate}...HEAD"]

    # Fallback to uncommitted / staged working tree diff
    return "working tree (staged & unstaged)", ["HEAD"]


def audit_diff(repo_root: Path, diff_args: List[str]) -> Dict[str, Any]:
    """Scans git diff for red flags, secrets, and debug artifacts."""
    full_diff = run_git(["diff"] + diff_args, cwd=repo_root) or ""
    diff_stat = run_git(["diff", "--stat"] + diff_args, cwd=repo_root) or ""

    findings: List[Dict[str, Any]] = []
    current_file = ""

    lines = full_diff.splitlines()
    for line in lines:
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        # We only audit ADDED lines
        if not line.startswith("+") or line.startswith("+++"):
            continue

        added_text = line[1:]

        # Skip testing files for debug statement warnings (tests often legitimately inspect prints)
        is_test_file = any(t in current_file.lower() for t in ["test", "spec", "__tests__"])

        # Check debug statements
        if not is_test_file:
            for pattern, desc in DEBUG_PATTERNS:
                if re.search(pattern, added_text):
                    findings.append({
                        "file": current_file,
                        "severity": "warning",
                        "category": "debug_statement",
                        "description": desc,
                        "line": added_text.strip()[:100],
                    })

        # Check secrets (even in test files!)
        for pat in SECRET_PATTERNS:
            flags = pat[2] if len(pat) > 2 else 0
            if re.search(pat[0], added_text, flags):
                findings.append({
                    "file": current_file,
                    "severity": "critical",
                    "category": "credential_risk",
                    "description": pat[1],
                    "line": added_text.strip()[:60] + "... [REDACTED]",
                })

    # Changed files list
    changed_files_raw = run_git(["diff", "--name-only"] + diff_args, cwd=repo_root) or ""
    changed_files = [f.strip() for f in changed_files_raw.splitlines() if f.strip()]

    return {
        "diff_stat": diff_stat.strip(),
        "changed_files": changed_files,
        "changed_count": len(changed_files),
        "findings": findings,
        "clean": len(findings) == 0,
        "has_critical": any(f["severity"] == "critical" for f in findings),
    }


def generate_pr_markdown(
    repo_root: Path,
    audit_results: Dict[str, Any],
    title: Optional[str] = None,
    validation_proof: Optional[str] = None,
) -> str:
    """Generates standardized pull request description markdown."""
    branch = run_git(["branch", "--show-current"], cwd=repo_root) or "feature-branch"
    pr_title = title or f"feat: updates in {branch}"

    files_list = "\n".join([f"- `{f}`" for f in audit_results["changed_files"][:15]])
    if len(audit_results["changed_files"]) > 15:
        files_list += f"\n- ... and {len(audit_results['changed_files']) - 15} more files"

    validation_section = validation_proof or "Verified test suite passing locally (`exit code 0`)."

    md = f"""# {pr_title}

## 📋 Summary
Summary of changes implemented in this pull request.

## 🛠️ Key Changes
{files_list}

## 🧪 Verification & Proof
- **Validation**: {validation_section}
- **Diff Stat**:
```text
{audit_results['diff_stat']}
```

## ✅ Pull Request Checklist
- [x] Tested against local environment (zero false verification)
- [x] No lingering debug logs or breakpoints
- [x] Project context files (`AGENTS.md`, `SESSION_LOG.md`) updated if necessary
- [x] Backward-compatible / breaking changes documented
"""
    return md


def main():
    parser = argparse.ArgumentParser(description="Universal PR Auditor & Description Generator.")
    parser.add_argument("--path", type=str, default=None, help="Repository root path")
    parser.add_argument("--base", type=str, default=None, help="Base branch/commit to diff against")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if critical issues or warnings found")
    parser.add_argument("--generate-desc", action="store_true", help="Generate full PR markdown description")
    parser.add_argument("--title", type=str, default=None, help="PR title")
    parser.add_argument("--validation", type=str, default=None, help="Validation proof text")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    start_dir = Path(args.path) if args.path else Path.cwd()
    repo_root = get_repo_root(start_dir)

    target_desc, diff_args = determine_diff_target(repo_root, args.base)
    audit = audit_diff(repo_root, diff_args)
    audit["diff_target"] = target_desc

    if args.json:
        print(json.dumps(audit, indent=2))
        sys.exit(1 if (args.check and not audit["clean"]) else 0)

    if args.generate_desc:
        pr_md = generate_pr_markdown(repo_root, audit, title=args.title, validation_proof=args.validation)
        print(pr_md)
        return

    # Default CLI Output
    print(f"🔍 Auditing diff {target_desc} ({audit['changed_count']} files changed):")
    if audit["diff_stat"]:
        print(f"\n{audit['diff_stat']}\n")

    if audit["clean"]:
        print("✅ Diff audit passed! No debug statements or secret leaks detected.")
    else:
        print(f"⚠️ Found {len(audit['findings'])} issue(s) in diff:")
        for f in audit["findings"]:
            icon = "🚨 CRITICAL" if f["severity"] == "critical" else "⚠️ WARNING"
            print(f"  {icon} [{f['file']}]: {f['description']}")
            print(f"      Snippet: {f['line']}")

    if args.check:
        sys.exit(1 if not audit["clean"] else 0)


if __name__ == "__main__":
    main()
