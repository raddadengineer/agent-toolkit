#!/usr/bin/env python3
"""
auto_format.py — Antigravity PostToolUse Auto-Formatter Hook

Runs language-native code formatters (ruff, prettier, swiftformat, gofmt)
automatically on files modified by write_to_file or replace_file_content.

Input: JSON on stdin (with toolCall.args.TargetFile)
Output: JSON on stdout ({})
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def format_file(file_path_str: str):
    if not file_path_str:
        return

    path = Path(file_path_str)
    if not path.exists() or not path.is_file():
        return

    ext = path.suffix.lower()

    try:
        # Python: ruff format or black
        if ext == ".py":
            if shutil.which("ruff"):
                subprocess.run(["ruff", "format", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            elif shutil.which("black"):
                subprocess.run(["black", "-q", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

        # JS/TS/JSON/Markdown: prettier
        elif ext in [".js", ".ts", ".jsx", ".tsx", ".json", ".md"]:
            if shutil.which("prettier"):
                subprocess.run(["prettier", "--write", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

        # Swift: swiftformat
        elif ext == ".swift":
            if shutil.which("swiftformat"):
                subprocess.run(["swiftformat", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

        # Go: gofmt
        elif ext == ".go":
            if shutil.which("gofmt"):
                subprocess.run(["gofmt", "-w", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

        # Rust: rustfmt
        elif ext == ".rs":
            if shutil.which("rustfmt"):
                subprocess.run(["rustfmt", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

    except Exception:
        pass


def main():
    try:
        raw_input = sys.stdin.read()
        if raw_input.strip():
            payload = json.loads(raw_input)
            tool_call = payload.get("toolCall", {})
            args = tool_call.get("args", {})
            target_file = args.get("TargetFile") or args.get("target_file")
            if target_file:
                format_file(target_file)
    except Exception:
        pass

    # PostToolUse requires empty or valid JSON on stdout
    print(json.dumps({}))


if __name__ == "__main__":
    main()
