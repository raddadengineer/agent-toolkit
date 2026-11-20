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
from typing import Any, Dict

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
    # SysAdmin lockout & high-blast-radius infrastructure guards
    (
        re.compile(
            r'\bip6?tables\b(?=.*(?:-F\b|--flush\b|-X\b|--delete-chain\b|-P\s+(?:INPUT|OUTPUT)\s+DROP\b))'
        ),
        "Firewall flush or default DROP policy lockout hazard",
    ),
    (
        re.compile(r'\bufw\s+(?:--force\s+)?(?:reset|disable)\b'),
        "UFW firewall reset or disable hazard",
    ),
    (
        re.compile(r'\bnft\s+flush\s+ruleset\b'),
        "nftables full ruleset flush hazard",
    ),
    (
        re.compile(
            r'\bsystemctl\s+(?:stop|disable|mask)\s+(?:ssh|sshd|networking|systemd-networkd|NetworkManager)(?:\.service)?\b'
        ),
        "Stopping or disabling critical remote-access or network service",
    ),
    (
        re.compile(
            r'\b(?:chmod|chown)\b(?=.*(?:-R\b|--recursive\b)).*\s+(?:/\*?|/(?:etc|usr|var|bin|sbin|lib|boot|sys|proc)(?:/[^\s;|&]*)?)(?:\s|$|;|&|\|)'
        ),
        "Recursive permission or ownership change on system root path",
    ),
    (
        re.compile(
            r'(?:^|&&|\|\||[;|&])\s*(?:sudo\s+)?(?:shutdown|reboot|halt|poweroff|init\s+[06]|systemctl\s+(?:reboot|poweroff|halt))\b'
        ),
        "Host shutdown, halt, or reboot command",
    ),
    (
        re.compile(r'\bcrontab\b(?:\s+-u\s+\S+)?\s+-[a-zA-Z]*r[a-zA-Z]*(?:\s|$|;|&|\|)'),
        "Crontab wipe (-r) removes all scheduled jobs",
    ),
    (
        re.compile(r'\busermod\b(?=.*\s-G\b)(?!.*\s(?:-[a-zA-Z]*a[a-zA-Z]*|--append)\b)'),
        "usermod -G without -a/--append overwrites existing supplementary groups",
    ),
    (
        re.compile(r'(?:>{1,2}\s*|tee\s+(?:-a\s+)?)/etc/sudoers(?:\s|$|;|&|\|)'),
        "Direct write to /etc/sudoers bypassing visudo validation",
    ),
]

READ_ONLY_SEGMENT_RE = re.compile(
    r'^(?:sudo\s+)?(?:'
    r'df|du|free|vm_stat|uptime|ps|ss|lsof|netstat|dig|nslookup|journalctl|'
    r'uname|hostname|whoami|id|cat|head|tail|grep|egrep|fgrep|wc|sort|uniq|awk|'
    r'systemctl\s+(?:status|--failed|is-active)|'
    r'ufw\s+status|ip6?tables\s+-L|nginx\s+-t|sshd\s+-t|visudo\s+-c|crontab\s+-l|'
    r'git\s+(?:status|diff|log)'
    r')(?:\s|$)'
)

_SYSADMIN_TOOL_RE = re.compile(r'^(?:python3?|atk)\s+.*?(?:sys_admin\.py|sysadmin|sys|ops)\b')
_SYSADMIN_MUTATING_FLAGS = (
    "--apply-safe",
    "--scaffold",
    "--init",
    "--write-baseline",
    "--snapshot",
)
_SYSADMIN_READONLY_FLAGS = (
    "--health",
    "--audit",
    "--check-tls",
    "--check-port",
    "--check-dns",
    "--triage-logs",
    "--audit-host",
    "--diff-snapshot",
    "--check-endpoints",
    "--list-templates",
    "--help",
    "-h",
)


def _is_readonly_segment(seg: str) -> bool:
    if READ_ONLY_SEGMENT_RE.match(seg):
        return True
    if _SYSADMIN_TOOL_RE.match(seg):
        if any(flag in seg for flag in _SYSADMIN_MUTATING_FLAGS):
            return False
        if any(flag in seg for flag in _SYSADMIN_READONLY_FLAGS):
            return True
    return False


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


def classify_command_tier(command_line: str) -> Dict[str, Any]:
    """Classifies a shell command into Tier 0 (READ_ONLY), Tier 1 (STANDARD_MUTATION), or Tier 2 (HIGH_BLAST_RADIUS)."""
    clean_cmd = (command_line or "").strip()
    if not clean_cmd:
        return {"tier": 0, "label": "READ_ONLY", "decision": "allow"}

    evaluation = evaluate_command(clean_cmd)
    if evaluation["decision"] == "deny":
        return {
            "tier": 2,
            "label": "HIGH_BLAST_RADIUS",
            "decision": "deny",
            "reason": evaluation["reason"],
        }

    # Check for non-null output redirections which indicate mutation
    stripped_null_redir = re.sub(r'(?:[12&]?>{1,2}|&>)\s*/dev/null', '', clean_cmd)
    if ">" in stripped_null_redir:
        return {"tier": 1, "label": "STANDARD_MUTATION", "decision": "allow"}

    segments = [seg.strip() for seg in re.split(r'\s*(?:&&|\|\||[;|])\s*', stripped_null_redir) if seg.strip()]
    if segments and all(_is_readonly_segment(seg) for seg in segments):
        return {"tier": 0, "label": "READ_ONLY", "decision": "allow"}

    return {"tier": 1, "label": "STANDARD_MUTATION", "decision": "allow"}


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
