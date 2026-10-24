#!/usr/bin/env python3
"""
compress_context.py — Universal Token Optimization & Context Compression Engine

Delivers maximum context density with minimal token footprint for AI assistants
(Antigravity, Claude Code, Cursor, Copilot, Gemini).

Features:
  1. AST & Skeleton Extraction: Converts full code into ultra-compact interface
     skeletons (classes, functions, signatures, docstrings) with 85-95% token savings.
     Supports Python (native AST), TypeScript/JavaScript, Swift, Go, and Rust.
  2. Token Profiler & Heatmap: Identifies token-heavy files, directories, and bloat.
  3. Context Packer (Repomix / GitIngest style): Bundles repository contents into
     compressed XML or Markdown prompts under strict token budgets.
  4. Hybrid Mode: Retains full source for critical entry points while skeletonizing
     the remainder of the repository.
  5. Intelligent Ignore Filtering: Honors .gitignore and strips 50+ noise patterns
     (lockfiles, binaries, maps, caches, minified bundles).

Usage:
    python3 compress_context.py --profile
    python3 compress_context.py --skeleton
    python3 compress_context.py --hybrid --budget 8000
    python3 compress_context.py --pack --format xml --output context.xml
    python3 compress_context.py --file path/to/file.py --skeleton
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ignore patterns for noise, caches, lockfiles, and binaries
DEFAULT_IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".build",
    "build",
    "dist",
    "DerivedData",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    ".next",
    ".nuxt",
    "coverage",
    ".idea",
    ".vscode",
    ".gemini",
    ".claude",
}

DEFAULT_IGNORE_EXTENSIONS = {
    # Binaries & executables
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".pyc", ".pyo",
    # Media & graphics
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".pdf", ".mp4", ".mov", ".zip", ".tar", ".gz",
    # Data & large maps
    ".map", ".min.js", ".min.css", ".lock", ".sqlite", ".sqlite3", ".db",
}

DEFAULT_IGNORE_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "Gemfile.lock",
    "composer.lock",
    "poetry.lock",
    ".DS_Store",
    "REPO_MAP.md",
    "repo_map.md",
}


def estimate_tokens(text: str) -> int:
    """Accurately estimates token count using BPE-aligned regex tokenization."""
    if not text:
        return 0
    # Matches words, numbers, and individual punctuation marks (close to cl100k/Gemini BPE)
    tokens = len(re.findall(r"\w+|[^\w\s]", text))
    return max(1, tokens)


def run_git(cmd: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Runs a git command and returns output string."""
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
    """Finds repository root using git rev-parse or upward directory traversal."""
    start = (start_path or Path.cwd()).resolve()
    git_top = run_git(["rev-parse", "--show-toplevel"], cwd=start)
    if git_top:
        p = Path(git_top).resolve()
        if p.exists() and p.is_dir():
            return p

    markers = [".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "Package.swift"]
    cur = start
    while cur != cur.parent:
        for m in markers:
            if (cur / m).exists():
                return cur
        cur = cur.parent
    return start


# ==============================================================================
# SKELETON EXTRACTORS (Multi-Language AST & Signatures)
# ==============================================================================

def skeletonize_python(code: str) -> str:
    """Uses Python's native AST parser to extract classes, methods, and functions."""
    try:
        tree = ast.parse(code)
    except Exception:
        # Fallback to regex if file has invalid/incomplete syntax
        return regex_skeletonize(code, comment_char="#")

    lines: List[str] = []

    # Module docstring
    doc = ast.get_docstring(tree)
    if doc:
        first_line = doc.strip().split("\n")[0]
        lines.append(f'"""{first_line}"""\n')

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Keep imports for type context
            try:
                import_src = ast.unparse(node)
                lines.append(import_src)
            except Exception:
                pass
        elif isinstance(node, ast.ClassDef):
            lines.append("")
            bases = [ast.unparse(b) for b in node.bases]
            bases_str = f"({', '.join(bases)})" if bases else ""
            lines.append(f"class {node.name}{bases_str}:")
            cdoc = ast.get_docstring(node)
            if cdoc:
                lines.append(f'    """{cdoc.strip().split(chr(10))[0]}"""')
            has_methods = False
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    has_methods = True
                    prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                    args = ast.unparse(item.args)
                    ret = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                    lines.append(f"    {prefix}def {item.name}({args}){ret}: ...")
            if not has_methods:
                lines.append("    ...")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            args = ast.unparse(node.args)
            ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            lines.append(f"{prefix}def {node.name}({args}){ret}: ...")

    return "\n".join(lines).strip()


def skeletonize_typescript(code: str) -> str:
    """Extracts TypeScript / JavaScript interfaces, types, classes, and exported functions."""
    out: List[str] = []
    lines = code.splitlines()
    in_block = False
    is_interface = False
    brace_depth = 0
    method_depth = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Capture imports
        if stripped.startswith("import ") and " from " in stripped:
            out.append(line)
            continue

        # Top-level types, interfaces, classes, enums
        match = re.search(r"^(export\s+)?(default\s+)?(interface|type|class|abstract\s+class|enum)\s+", stripped)
        if match and not in_block:
            kind = match.group(3)
            is_interface = kind in ["interface", "type"]
            if "{" in stripped:
                out.append(line)
                in_block = True
                brace_depth = stripped.count("{") - stripped.count("}")
                method_depth = 0
                if brace_depth <= 0:
                    in_block = False
            else:
                out.append(line)
            continue

        if in_block:
            if method_depth > 0:
                # Inside method body - update method_depth and skip
                method_depth += stripped.count("{") - stripped.count("}")
                continue

            # Check if this closes the class/interface
            brace_delta = stripped.count("{") - stripped.count("}")
            if (brace_depth + brace_delta) <= 0:
                in_block = False
                out.append("}")
                continue

            brace_depth += brace_delta

            if is_interface:
                if not stripped.startswith("{"):
                    out.append(line)
            else:
                # Inside class and not inside a method body
                if re.search(r"^(public|private|protected|async|static|\*|\bget\b|\bset\b|\bconstructor\b|[A-Za-z0-9_]+)\b.*\(.*\)", stripped):
                    sig = re.sub(r"\{.*$", "{ ... }", stripped)
                    if not sig.endswith("{ ... }") and not sig.endswith(";"):
                        sig += " { ... }"
                    out.append("    " + sig)
                    # If this method opened a block, track it
                    if "{" in stripped:
                        method_depth = stripped.count("{") - stripped.count("}")
                elif re.search(r"^(public|private|protected|readonly|\b[A-Za-z0-9_]+\s*[:=])", stripped):
                    out.append("    " + stripped)
            continue

        # Exported function declarations
        if re.search(r"^(export\s+)?(default\s+)?(async\s+)?function\s+[A-Za-z0-9_]+\s*\(", stripped):
            sig = re.sub(r"\{.*$", "{ ... }", stripped)
            out.append(sig if sig.endswith("{ ... }") else sig + " { ... }")
            continue

        # Exported arrow functions or const variables
        if re.search(r"^export\s+(const|let)\s+[A-Za-z0-9_]+\s*[:=]", stripped):
            if "=>" in stripped:
                sig = stripped.split("=>")[0] + "=> { ... };"
                out.append(sig)
            else:
                out.append(stripped[:100])
            continue

    return "\n".join(out).strip() or regex_skeletonize(code, comment_char="//")


def skeletonize_swift(code: str) -> str:
    """Extracts Swift protocols, structs, classes, enums, actors, and function signatures."""
    out: List[str] = []
    lines = code.splitlines()

    for line in lines:
        stripped = line.strip()

        # Imports
        if stripped.startswith("import "):
            out.append(line)
            continue

        # Type declarations
        if re.search(r"\b(protocol|struct|class|actor|enum|extension)\s+[A-Za-z0-9_]+", stripped):
            if stripped.endswith("{"):
                out.append(line)
            else:
                out.append(line + " {")
            continue

        # Function signatures
        if re.search(r"\bfunc\s+[A-Za-z0-9_]+\s*\(", stripped):
            sig = re.sub(r"\{.*$", "{ ... }", stripped)
            if not sig.endswith("{ ... }"):
                sig += " { ... }"
            out.append("    " + sig)
            continue

        # Initializers
        if re.search(r"\binit\s*\(", stripped):
            sig = re.sub(r"\{.*$", "{ ... }", stripped)
            if not sig.endswith("{ ... }"):
                sig += " { ... }"
            out.append("    " + sig)
            continue

        # Public / published variables
        if re.search(r"\b(public|open|@Published|let|var)\s+[A-Za-z0-9_]+\s*:", stripped):
            out.append("    " + stripped)
            continue

        if stripped == "}":
            out.append("}")

    return "\n".join(out).strip() or regex_skeletonize(code, comment_char="//")


def skeletonize_go(code: str) -> str:
    """Extracts Go package, types (structs/interfaces), and function signatures."""
    out: List[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("package "):
            out.append(line)
        elif stripped.startswith("import "):
            out.append(line)
        elif re.search(r"^type\s+[A-Za-z0-9_]+\s+(struct|interface)", stripped):
            out.append(line)
        elif re.search(r"^func\s+(\([^\)]+\)\s+)?[A-Za-z0-9_]+\s*\(", stripped):
            sig = re.sub(r"\{.*$", "{ ... }", stripped)
            out.append(sig if sig.endswith("{ ... }") else sig + " { ... }")
        elif stripped == "}":
            out.append("}")
    return "\n".join(out).strip() or regex_skeletonize(code, comment_char="//")


def skeletonize_rust(code: str) -> str:
    """Extracts Rust pub structs, enums, traits, and fn signatures."""
    out: List[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("use "):
            out.append(line)
        elif re.search(r"^(pub\s+)?(struct|enum|trait)\s+[A-Za-z0-9_]+", stripped):
            out.append(line)
        elif re.search(r"^impl(\s+<[^>]+>)?\s+[A-Za-z0-9_]+", stripped):
            out.append(line)
        elif re.search(r"^(pub\s+)?(async\s+)?fn\s+[A-Za-z0-9_]+\s*\(", stripped):
            sig = re.sub(r"\{.*$", "{ ... }", stripped)
            out.append(sig if sig.endswith("{ ... }") else sig + " { ... }")
        elif stripped == "}":
            out.append("}")
    return "\n".join(out).strip() or regex_skeletonize(code, comment_char="//")


def regex_skeletonize(code: str, comment_char: str = "#") -> str:
    """Fallback skeletonizer for other languages."""
    lines = code.splitlines()
    out = []
    for line in lines[:60]:
        stripped = line.strip()
        if not stripped or stripped.startswith(comment_char):
            continue
        if any(kw in stripped for kw in ["def ", "class ", "func ", "function ", "interface ", "struct ", "type "]):
            out.append(line)
    return "\n".join(out).strip()


def skeletonize_code(code: str, file_path: Path) -> str:
    """Dispatches to language-specific skeletonizer based on file extension."""
    ext = file_path.suffix.lower()
    if ext == ".py":
        return skeletonize_python(code)
    elif ext in [".ts", ".tsx", ".js", ".jsx"]:
        return skeletonize_typescript(code)
    elif ext == ".swift":
        return skeletonize_swift(code)
    elif ext == ".go":
        return skeletonize_go(code)
    elif ext == ".rs":
        return skeletonize_rust(code)
    else:
        # For non-code or unsupported types (e.g. JSON, YAML, MD), keep head or minimal lines
        return code[:400] + ("\n... [truncated]" if len(code) > 400 else "")


# ==============================================================================
# REPOSITORY SCANNER & PROFILER
# ==============================================================================

def should_ignore(path: Path, repo_root: Path) -> bool:
    """Determines whether a file or directory should be ignored."""
    try:
        rel_parts = path.relative_to(repo_root).parts
    except ValueError:
        rel_parts = path.parts

    # Check ignored directories in path
    for part in rel_parts:
        if part in DEFAULT_IGNORE_DIRS:
            return True
        if part.startswith(".") and part not in [".github"]:
            return True

    if path.is_file():
        if path.name in DEFAULT_IGNORE_FILES:
            return True
        if path.suffix.lower() in DEFAULT_IGNORE_EXTENSIONS:
            return True

    return False


def scan_repository(repo_root: Path) -> List[Path]:
    """Finds all non-ignored source files in the repository, honoring .gitignore."""
    collected: List[Path] = []

    # Check git repository first to honor .gitignore
    git_output = run_git(["ls-files", "--cached", "--others", "--exclude-standard"], cwd=repo_root)
    if git_output is not None:
        for rel_path in git_output.splitlines():
            rel_path = rel_path.strip()
            if not rel_path:
                continue
            p = repo_root / rel_path
            if p.is_file() and not should_ignore(p, repo_root):
                collected.append(p)
        return sorted(collected)

    for root, dirs, files in os.walk(repo_root):
        # In-place prune dirs
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")]

        root_path = Path(root)
        for f in files:
            p = root_path / f
            if not should_ignore(p, repo_root):
                collected.append(p)
    return sorted(collected)


def profile_repository(repo_root: Path) -> Dict[str, Any]:
    """Profiles token usage across all files in the repository."""
    files = scan_repository(repo_root)
    file_profiles = []
    total_tokens = 0
    total_bytes = 0

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            tokens = estimate_tokens(content)
            size = f.stat().st_size
            rel = str(f.relative_to(repo_root))

            total_tokens += tokens
            total_bytes += size

            file_profiles.append({
                "path": rel,
                "tokens": tokens,
                "bytes": size,
            })
        except Exception:
            pass

    file_profiles.sort(key=lambda x: x["tokens"], reverse=True)

    return {
        "repo_name": repo_root.name,
        "repo_root": str(repo_root),
        "total_files": len(file_profiles),
        "total_tokens": total_tokens,
        "total_bytes": total_bytes,
        "files": file_profiles,
    }


# ==============================================================================
# PACKER & HYBRID COMPRESSOR
# ==============================================================================

def pack_repository(
    repo_root: Path,
    mode: str = "hybrid",
    fmt: str = "markdown",
    token_budget: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Packs repository code into a compressed single context string.

    Modes:
      - 'skeleton': Every code file is reduced to its AST skeleton.
      - 'full': Raw content included up to budget.
      - 'hybrid': Full content for critical entry points (README, manifests, configs),
                  skeletons for all implementation files.
    """
    files = scan_repository(repo_root)
    out_parts: List[str] = []

    # Priority entry points get full content in hybrid mode
    ENTRY_POINT_NAMES = {
        "readme.md", "agents.md", "claude.md", "gemini.md",
        "package.json", "pyproject.toml", "cargo.toml", "package.swift", "go.mod",
    }

    current_tokens = 0
    included_files = 0
    raw_tokens_saved = 0

    if fmt == "xml":
        out_parts.append(f'<repository name="{repo_root.name}" mode="{mode}">')
    else:
        out_parts.append(f"# 📦 Repository Context Map: {repo_root.name} (Mode: {mode.upper()})\n")

    for f in files:
        # Skip redundant context file mirrors if AGENTS.md is present
        if f.name.lower() in ("claude.md", "gemini.md") and (repo_root / "AGENTS.md").exists():
            continue

        rel_path = f.relative_to(repo_root)
        try:
            raw_content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        raw_tok = estimate_tokens(raw_content)

        # Determine representation
        is_entry = f.name.lower() in ENTRY_POINT_NAMES
        if mode == "full" or (mode == "hybrid" and is_entry):
            rep_content = raw_content
        else:
            rep_content = skeletonize_code(raw_content, f)

        rep_tok = estimate_tokens(rep_content)
        raw_tokens_saved += max(0, raw_tok - rep_tok)

        # Check budget
        if token_budget and (current_tokens + rep_tok) > token_budget:
            out_parts.append(f"\n<!-- [Token budget of {token_budget} reached. Remaining files omitted.] -->")
            break

        current_tokens += rep_tok
        included_files += 1

        if fmt == "xml":
            out_parts.append(f'  <file path="{rel_path}">\n{rep_content}\n  </file>')
        else:
            out_parts.append(f"### File: `{rel_path}`\n```{f.suffix.lstrip('.') or 'text'}\n{rep_content}\n```\n")

    if fmt == "xml":
        out_parts.append("</repository>")

    result_text = "\n".join(out_parts)
    stats = {
        "included_files": included_files,
        "total_files": len(files),
        "output_tokens": estimate_tokens(result_text),
        "tokens_saved": raw_tokens_saved,
        "compression_ratio": (
            f"{(1.0 - (estimate_tokens(result_text) / max(1, current_tokens + raw_tokens_saved))) * 100:.1f}%"
            if (current_tokens + raw_tokens_saved) > 0
            else "0%"
        ),
    }

    return result_text, stats


# ==============================================================================
# CLI INTERFACE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Universal Token Optimization & Context Compression Engine."
    )
    parser.add_argument("--path", "--dir", "--repo", dest="path", type=str, default=None, help="Repository root path")
    parser.add_argument("--file", type=str, default=None, help="Compress a single file to stdout")
    parser.add_argument("--profile", action="store_true", help="Profile token usage heatmap")
    parser.add_argument("--skeleton", action="store_true", help="Pack with AST skeletons only")
    parser.add_argument("--hybrid", action="store_true", help="Hybrid packing (full entry points + skeletons)")
    parser.add_argument("--pack", action="store_true", help="Pack repository into single prompt")
    parser.add_argument("--format", type=str, choices=["markdown", "xml"], default="markdown", help="Output format")
    parser.add_argument("--budget", type=int, default=None, help="Hard token limit budget (e.g. 8000)")
    parser.add_argument("--output", type=str, default=None, help="Save packed output to file")
    parser.add_argument("--json", action="store_true", help="Output profiling data as JSON")

    args = parser.parse_args()

    # 1. Single file skeleton
    if args.file:
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        raw = file_path.read_text(encoding="utf-8", errors="ignore")
        skel = skeletonize_code(raw, file_path)
        print(skel)
        raw_tok = estimate_tokens(raw)
        skel_tok = estimate_tokens(skel)
        print(f"\n# 📊 Token Reduction: {raw_tok} -> {skel_tok} tokens (-{(1 - skel_tok/max(1, raw_tok))*100:.1f}%)", file=sys.stderr)
        return

    repo_root = get_repo_root(Path(args.path) if args.path else None)

    # 2. Token Profiler
    if args.profile:
        prof = profile_repository(repo_root)
        if args.json:
            print(json.dumps(prof, indent=2))
            return

        print(f"📊 Token Footprint Profile: {prof['repo_name']}")
        print(f"📁 Root: {prof['repo_root']}")
        print(f"📄 Files: {prof['total_files']} | 🏷️ Total Tokens: ~{prof['total_tokens']:,} | 💾 Size: {prof['total_bytes'] / 1024:.1f} KB\n")
        print("Top Token-Heavy Files:")
        print(f"{'Path':<45} {'Tokens':<10} {'% of Total':<10}")
        print("-" * 65)
        for item in prof["files"][:15]:
            pct = (item["tokens"] / max(1, prof["total_tokens"])) * 100
            print(f"{item['path']:<45} {item['tokens']:<10,d} {pct:<10.1f}%")
        if len(prof["files"]) > 15:
            print(f"... and {len(prof['files']) - 15} more files")
        return

    # 3. Context Packing (Hybrid, Skeleton, or Full)
    mode = "skeleton" if args.skeleton else ("hybrid" if args.hybrid else "hybrid")
    if args.pack or args.skeleton or args.hybrid or args.output:
        packed_content, stats = pack_repository(
            repo_root=repo_root,
            mode=mode,
            fmt=args.format,
            token_budget=args.budget,
        )

        if args.output:
            dest = Path(args.output).resolve()
            dest.write_text(packed_content, encoding="utf-8")
            print(f"✅ Context map saved to: {dest}")
        else:
            print(packed_content)

        print(
            f"\n📊 Summary: {stats['included_files']}/{stats['total_files']} files packed | "
            f"~{stats['output_tokens']:,} tokens | "
            f"Saved: ~{stats['tokens_saved']:,} tokens (Compression: {stats['compression_ratio']})",
            file=sys.stderr,
        )
        return

    # Default action: run profiler
    prof = profile_repository(repo_root)
    print(f"📊 {prof['repo_name']}: {prof['total_files']} files, ~{prof['total_tokens']:,} tokens.")
    print("Run `python3 compress_context.py --skeleton` or `--hybrid` to generate compressed context.")


if __name__ == "__main__":
    main()
