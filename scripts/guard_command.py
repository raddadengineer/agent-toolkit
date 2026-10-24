#!/usr/bin/env python3
"""
guard_command.py — Antigravity PreToolUse Safety Guard Hook

Inspects shell commands before execution and blocks high-risk, destructive actions:
  - Recursive root or home deletion (rm -rf /, rm -r -f ~, rm --recursive --force $HOME)
  - Force pushing to protected branches (git push --force origin main, git push origin main -f)
  - Destructive git operations (git reset --hard origin/main, git clean -fdx, git branch -D main)
  - Destructive disk operations (mkfs, dd if=... of=/dev/...)
  - Unintended fork bombs or database drops

Input: JSON on stdin (with toolCall.args.CommandLine)
Output: JSON on stdout ({"decision": "allow"} or {"decision": "deny", "reason": "..."})
"""

import json
import re
import sys

DESTRUCTIVE_PATTERNS = [
    (
        re.compile(
            r'\brm\s+(?:-[rRfF]+\s+|--(?:recursive|force)\s+)+(?:/\*?|/\s|~/?|\$HOME/?|\$\{HOME\}/?)(?:\s|$|;|&|\|)'
        ),
        "Recursive deletion of root or home directory",
    ),
    (
        re.compile(
            r'\bgit\s+push\b(?=.*(?:--force(?!-with-lease)|-f\b))(?=.*\b(?:main|master|release|prod|production)\b)'
        ),
        "Force push to protected branch",
    ),
    (
        re.compile(r'\bgit\s+reset\s+--hard(?:\s+origin/(?:main|master))?\b'),
        "Hard reset discarding uncommitted changes",
    ),
    (
        re.compile(r'\bgit\s+clean\s+(?:-[a-zA-Z]*[fF][a-zA-Z]*|-f\s+-d|-d\s+-f)\b'),
        "Destructive git clean removing untracked files and directories",
    ),
    (
        re.compile(r'\bgit\s+branch\s+-D\s+(?:main|master|release|prod|production)\b'),
        "Force deletion of protected branch",
    ),
    (
        re.compile(r'\bdd\s+if=.*of=/dev/(?:sd|nvme|disk|hd|vd)[a-z0-9]*\b'),
        "Raw disk write overwrite hazard",
    ),
    (
        re.compile(r'\bmkfs(?:\.\w+)?\s+'),
        "Filesystem format hazard",
    ),
    (
        re.compile(r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:'),
        "Fork bomb detected",
    ),
    (
        re.compile(r'\bDROP\s+(?:DATABASE|SCHEMA)\b', re.IGNORECASE),
        "Destructive DROP DATABASE/SCHEMA statement detected",
    ),
]


def evaluate_command(command_line: str) -> dict:
    if not command_line:
        return {"decision": "allow"}

    clean_cmd = command_line.strip()
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(clean_cmd):
            return {
                "decision": "deny",
                "reason": f"Destructive command blocked by agent-toolkit safety guard: {reason} ('{clean_cmd}')",
            }

    return {"decision": "allow"}


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        args = tool_call.get("args", {})
        cmd = args.get("CommandLine") or args.get("command") or ""

        result = evaluate_command(cmd)
        print(json.dumps(result))
    except Exception as e:
        # In case of hook parsing error, allow execution with warning to not stall agent
        print(json.dumps({"decision": "allow", "reason": f"Guard hook warning: {e}"}))


if __name__ == "__main__":
    main()
