#!/usr/bin/env python3
"""
review_code.py — Automated Adversarial Code Reviewer & Diff Inspector

Audits active git diffs (working tree, staged, or branch comparison) for
anti-patterns including silent error swallowing, async blocking calls, resource
leaks, missing test coverage, and scope creep.

Usage:
    python3 review_code.py
    python3 review_code.py --staged
    python3 review_code.py --base main
    python3 review_code.py --check
    python3 review_code.py --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ANTI_PATTERNS = [
    {
        "id": "CRIT-SWALLOW-ERR",
        "severity": "CRITICAL",
        "category": "Error Handling",
        "description": "Silent error swallowing without logging or recovery",
        "patterns": [
            re.compile(r'except(?:\s+[A-Za-z0-9_.]*)?\s*:\s*(?:pass|return\s*(?:None|false|nil)?)\b'),
            re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}'),
            re.compile(r'\.catch\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>\s*\{\s*\}\)'),
            re.compile(r'\b_\s*,\s*_\s*=\s*[a-zA-Z0-9_.]+\(.*\)|^\s*_\s*=\s*err\b'),
            re.compile(r'\btry\?\s+(?:await\s+)?[a-zA-Z0-9_.]*(?:send|fetch|save|delete|execute|post|put)\('),
        ],
    },
    {
        "id": "CRIT-ASYNC-BLOCK",
        "severity": "CRITICAL",
        "category": "Concurrency",
        "description": "Synchronous blocking sleep or call detected in async context",
        "patterns": [
            re.compile(r'\btime\.sleep\s*\('),
            re.compile(r'\bThread\.sleep\s*\('),
        ],
        "require_async_context": True,
    },
    {
        "id": "CRIT-LEAK-RESOURCE",
        "severity": "CRITICAL",
        "category": "Resource Management",
        "description": "Unmanaged file open without context manager ('with' statement)",
        "patterns": [
            re.compile(r'^\s*(?!with\b)[a-zA-Z0-9_]+\s*=\s*open\s*\([^)]+\)\s*$'),
        ],
    },
]

CODE_EXTENSIONS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".swift", ".java", ".kt", ".c", ".cpp", ".cs"}
TEST_EXTENSIONS = {"test_", "_test", ".test.", ".spec.", "tests/"}


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
        return None
    except OSError as err:
        sys.stderr.write(f"Git command failed: {err}\n")
        return None


def get_diff(staged_only: bool = False, base_branch: Optional[str] = None, cwd: Optional[Path] = None) -> Tuple[str, List[str]]:
    """Retrieves diff and list of changed files."""
    if base_branch:
        diff_cmd = ["diff", f"{base_branch}...HEAD"]
        files_cmd = ["diff", "--name-only", f"{base_branch}...HEAD"]
    elif staged_only:
        diff_cmd = ["diff", "--cached"]
        files_cmd = ["diff", "--cached", "--name-only"]
    else:
        diff_cmd = ["diff", "HEAD"]
        files_cmd = ["diff", "--name-only", "HEAD"]

    diff_text = run_git(diff_cmd, cwd=cwd) or ""
    files_text = run_git(files_cmd, cwd=cwd) or ""
    changed_files = [f.strip() for f in files_text.splitlines() if f.strip()]
    return diff_text, changed_files


def is_test_file(path_str: str) -> bool:
    """Checks if a file path belongs to tests."""
    path_lower = path_str.lower()
    return any(t in path_lower for t in TEST_EXTENSIONS)


def review_diff(diff_text: str, changed_files: List[str]) -> Dict[str, Any]:
    """Performs adversarial static audit on git diff."""
    findings: List[Dict[str, Any]] = []

    # 1. Parse diff per file
    current_file = ""
    current_line_no = 0
    in_async_func = False
    in_except_block = False
    except_line_no = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            current_line_no = 0
            in_async_func = False
            in_except_block = False
            continue
        elif line.startswith("@@"):
            match = re.search(r'\+(\d+)', line)
            if match:
                current_line_no = int(match.group(1)) - 1
            in_except_block = False
            continue

        if not current_file:
            continue

        # Skip testing fixtures or documentation from certain rules
        ext = Path(current_file).suffix.lower()
        if ext not in CODE_EXTENSIONS and not is_test_file(current_file):
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current_line_no += 1
            code_line = line[1:].strip()

            # Track async context
            if re.search(r'\basync\s+def\b|\basync\s+function\b|\basync\s*\(', code_line):
                in_async_func = True
            elif code_line.startswith("def ") or code_line.startswith("class ") or code_line.startswith("func "):
                in_async_func = False

            # Don't flag anti-patterns inside test files themselves
            if is_test_file(current_file):
                continue

            # Check multi-line except -> pass/return
            if in_except_block:
                if code_line in ("pass", "return", "return None", "return false", "return nil", "..."):
                    findings.append({
                        "id": "CRIT-SWALLOW-ERR",
                        "severity": "CRITICAL",
                        "category": "Error Handling",
                        "file": current_file,
                        "line": except_line_no,
                        "snippet": f"except: ... -> {code_line}",
                        "description": "Silent error swallowing without logging or recovery",
                    })
                in_except_block = False

            if re.match(r'except(?:\s+[A-Za-z0-9_.]*)?\s*:\s*$', code_line):
                in_except_block = True
                except_line_no = current_line_no

            for rule in ANTI_PATTERNS:
                if rule.get("require_async_context") and not in_async_func:
                    continue

                for pat in rule["patterns"]:
                    if pat.search(code_line):
                        findings.append({
                            "id": rule["id"],
                            "severity": rule["severity"],
                            "category": rule["category"],
                            "file": current_file,
                            "line": current_line_no,
                            "snippet": code_line[:120],
                            "description": rule["description"],
                        })
                        break
        elif not line.startswith("-"):
            current_line_no += 1

    # 2. Scope Creep / Diff Size Analysis
    prod_files = [f for f in changed_files if Path(f).suffix.lower() in CODE_EXTENSIONS and not is_test_file(f)]
    test_files = [f for f in changed_files if is_test_file(f)]

    if len(changed_files) > 20:
        findings.append({
            "id": "WARN-SCOPE-CREEP",
            "severity": "WARNING",
            "category": "Architecture & Scope",
            "file": "Workspace",
            "line": 0,
            "snippet": f"{len(changed_files)} files modified in change set",
            "description": "Unusually broad change set. Consider decomposing into smaller, atomic pull requests.",
        })

    if prod_files and not test_files:
        findings.append({
            "id": "WARN-NO-TESTS",
            "severity": "WARNING",
            "category": "Test Quality",
            "file": prod_files[0],
            "line": 0,
            "snippet": f"Modified {len(prod_files)} production code files without test coverage delta",
            "description": "Production logic was modified but no corresponding test files were added or updated.",
        })

    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    warning_count = sum(1 for f in findings if f["severity"] == "WARNING")
    nit_count = sum(1 for f in findings if f["severity"] == "NIT")

    if critical_count > 0:
        verdict = "REQUEST CHANGES"
    elif warning_count > 0:
        verdict = "APPROVE (with recommendations)"
    else:
        verdict = "APPROVE"

    return {
        "verdict": verdict,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "nit_count": nit_count,
        "total_files_changed": len(changed_files),
        "changed_files": changed_files,
        "findings": findings,
    }


def format_report(audit_result: Dict[str, Any]) -> str:
    """Formats review findings into standardized Markdown review."""
    verdict = audit_result["verdict"]
    verdict_emoji = "✅" if verdict.startswith("APPROVE") else "🚨"

    lines = []
    lines.append(f"### 🚦 Verdict: `{verdict_emoji} {verdict}`\n")

    # Executive Summary
    lines.append("### 🔍 Executive Summary")
    crit = audit_result["critical_count"]
    warn = audit_result["warning_count"]
    total = audit_result["total_files_changed"]

    if crit > 0:
        lines.append(
            f"Review flagged **{crit} critical blocker(s)** and {warn} recommendation(s) across {total} changed files. "
            "Critical issues must be resolved before merging to protect code reliability and maintainability.\n"
        )
    elif warn > 0:
        lines.append(
            f"Diff is structurally sound across {total} changed files with **0 critical issues**. "
            f"Found {warn} recommendation(s) to improve test resilience or modular scope.\n"
        )
    else:
        lines.append(
            f"Clean audit across {total} changed files. No anti-patterns, error swallowing, concurrency hazards, "
            "or test omissions detected. Ready for merge.\n"
        )

    # Findings
    lines.append("### ⚠️ Findings & Concerns")
    if not audit_result["findings"]:
        lines.append("✨ No anti-patterns or quality concerns identified.\n")
    else:
        for f in audit_result["findings"]:
            icon = "🚨" if f["severity"] == "CRITICAL" else ("⚠️" if f["severity"] == "WARNING" else "💡")
            lines.append(f"- **{icon} [{f['severity']}] {f['id']}** ({f['category']}):")
            if f["file"] != "Workspace":
                loc = f"`{f['file']}:{f['line']}`" if f["line"] > 0 else f"`{f['file']}`"
                lines.append(f"  - **Location**: {loc}")
            lines.append(f"  - **Issue**: {f['description']}")
            if f["snippet"]:
                lines.append(f"  - **Code**: `{f['snippet']}`")
        lines.append("")

    # Test Assessment
    lines.append("### 🧪 Verification Assessment")
    changed = audit_result["changed_files"]
    test_files = [f for f in changed if is_test_file(f)]
    prod_files = [f for f in changed if Path(f).suffix.lower() in CODE_EXTENSIONS and not is_test_file(f)]

    lines.append(f"- **Production Files Changed**: {len(prod_files)}")
    lines.append(f"- **Test Files Updated/Added**: {len(test_files)}")
    if test_files:
        lines.append(f"- **Test Coverage Proof**: ✅ Active test delta present ({', '.join(test_files[:3])}{'...' if len(test_files) > 3 else ''})")
    else:
        lines.append("- **Test Coverage Proof**: ⚠️ No test files included in change set.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Automated Adversarial Code Reviewer & Diff Inspector.")
    parser.add_argument("--staged", action="store_true", help="Audit only staged changes")
    parser.add_argument("--base", type=str, default=None, help="Base branch to diff against (e.g. main)")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if CRITICAL findings exist")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--path", "--dir", "--repo", dest="path", type=str, default=None, help="Repository root path")

    args = parser.parse_args()

    repo_root = Path(args.path).resolve() if args.path else Path.cwd()

    diff_text, changed_files = get_diff(staged_only=args.staged, base_branch=args.base, cwd=repo_root)

    result = review_diff(diff_text, changed_files)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))

    if args.check and result["critical_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
