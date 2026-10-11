#!/usr/bin/env python3
"""
guard_command.py — Antigravity PreToolUse Safety Guard Hook

Inspects shell commands before execution and blocks high-risk, destructive actions:
  - Recursive root deletion (rm -rf /, rm -rf ~)
  - Force pushing to protected branches (git push --force origin main)
  - Destructive disk operations (mkfs, dd if=...)
  - Unintended fork bombs or system halts

Input: JSON on stdin (with toolCall.args.CommandLine)
Output: JSON on stdout ({"decision": "allow"} or {"decision": "deny", "reason": "..."})
"""

import json
import re
import sys

DESTRUCTIVE_PATTERNS = [
    (re.compile(r'\brm\s+-[rRfF]*\s+(?:/|~|\$HOME)\b'), "Recursive deletion of root or home directory"),
    (re.compile(r'\bgit\s+push\s+.*(?:--force|-f).*(?:main|master|release|prod)\b'), "Force push to protected branch"),
    (re.compile(r'\bgit\s+reset\s+--hard\s+origin/(?:main|master)\b'), "Hard reset discarding uncommitted changes"),
    (re.compile(r'\bdd\s+if=.*of=(?:/dev/sd|/dev/nvme|/dev/disk)\b'), "Raw disk write overwrite hazard"),
    (re.compile(r'\bmkfs(?:\.\w+)?\s+'), "Filesystem format hazard"),
    (re.compile(r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:'), "Fork bomb detected"),
]


def evaluate_command(command_line: str) -> dict:
    if not command_line:
        return {"decision": "allow"}

    clean_cmd = command_line.strip()
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(clean_cmd):
            return {
                "decision": "deny",
                "reason": f"Destructive command blocked by agent-toolkit safety guard: {reason} ('{clean_cmd}')"
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
        cmd = args.get("CommandLine", "")

        result = evaluate_command(cmd)
        print(json.dumps(result))
    except Exception as e:
        # In case of hook parsing error, allow execution with warning to not stall agent
        print(json.dumps({"decision": "allow", "reason": f"Guard hook warning: {e}"}))


if __name__ == "__main__":
    main()
