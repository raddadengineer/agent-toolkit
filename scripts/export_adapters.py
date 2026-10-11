#!/usr/bin/env python3
"""
export_adapters.py — Universal Multi-Tool AI Adapter Generator

Compiles agent-toolkit skills, subagents, and engineering standards into native
configuration formats for:
  - Claude Code (.claude/commands/, CLAUDE.md)
  - Cursor (.cursor/rules/*.mdc, .cursorrules)
  - GitHub Copilot (.github/copilot-instructions.md, .github/prompts/*.prompt.md)
  - Roo Code / Cline / OpenCode (.roomodes, .clinerules)
  - Windsurf (.windsurfrules)
  - Google Antigravity & Gemini CLI (.agents/, AGENTS.md, GEMINI.md)

Usage:
    python3 export_adapters.py --target /path/to/project --tool all
    python3 export_adapters.py --target /path/to/project --tool claude
    python3 export_adapters.py --target /path/to/project --tool cursor
    python3 export_adapters.py --target /path/to/project --tool copilot
    python3 export_adapters.py --target /path/to/project --tool roo
    python3 export_adapters.py --target /path/to/project --tool windsurf
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional


def get_toolkit_dir() -> Path:
    """Finds the root of agent-toolkit."""
    return Path(__file__).resolve().parent.parent


def read_file_safe(path: Path) -> str:
    """Reads a file returning string content or empty string if missing."""
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


class AdapterExporter:
    def __init__(self, toolkit_dir: Path, target_dir: Path):
        self.toolkit_dir = toolkit_dir
        self.target_dir = target_dir

        # Read source definitions
        self.eng_standards = read_file_safe(
            toolkit_dir / "agents" / "software_engineer" / "rules" / "engineering-standards.md"
        )
        self.review_standards = read_file_safe(
            toolkit_dir / "agents" / "code_reviewer" / "rules" / "review-standards.md"
        )
        self.testing_standards = read_file_safe(
            toolkit_dir / "agents" / "test_engineer" / "rules" / "testing-standards.md"
        )
        self.arch_standards = read_file_safe(
            toolkit_dir / "agents" / "system_architect" / "rules" / "architecture-standards.md"
        )
        self.compression_standards = read_file_safe(
            toolkit_dir / "agents" / "context_optimizer" / "rules" / "compression-standards.md"
        )

    # --------------------------------------------------------------------------
    # 1. Claude Code
    # --------------------------------------------------------------------------
    def export_claude(self) -> List[str]:
        created = []
        commands_dir = self.target_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        commands = {
            "session-starter.md": """---
description: Ingest session history from SESSION_LOG.md and prime workspace
---

Execute the Universal Session Starter procedure:
1. Run `git status --short` and `git branch --show-current` to assess repository state.
2. Inspect `SESSION_LOG.md` for the latest session's accomplishments, validation, and outstanding **Next Steps / Handover** items.
3. Check that context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) are synchronized.
4. Establish a green baseline by running the project build/test suite before modifying code.
5. Provide a kick-off briefing and align on the immediate objective.
""",
            "session-closer.md": """---
description: Run session closer handover, record in SESSION_LOG.md, and sync context files
---

Execute the Universal Session Closer procedure:
1. Analyze accomplishments via `git status --short` and `git diff --stat`.
2. Record a structured entry in `SESSION_LOG.md` documenting Goal, Changes, Validation, and Next Steps.
3. Update and sync context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`).
4. Verify build and test suite under the Zero False Verification rule (must return exit code 0).
5. Deliver an executive handover summary.
""",
            "pr-prep.md": """---
description: Pre-flight audit for pull requests and generate PR description
---

Execute the Universal PR Preparation procedure:
1. Audit git diff for scope creep, leftover debug statements (`console.log`, `print()`, `debugger`), and potential credential leaks.
2. Verify all test suites and production builds pass cleanly.
3. Check that `SESSION_LOG.md` reflects current branch changes.
4. Generate a clean PR description with Summary, Key Changes, Test Verification receipts, and Checklist.
""",
            "code-review.md": """---
description: Adversarial senior code review of current diff or branch
---

Adopt the Universal Code Reviewer persona (read-only audit):
1. Review git diff against the base branch.
2. Systematically audit across 5 dimensions:
   - Security & Secrets (injection, unvalidated input, hardcoded keys)
   - Concurrency & Thread Safety (data races, async blocking, actor boundary leaks)
   - Error Handling (swallowed errors, bare catches, silent nil/null failures)
   - Scope Discipline (collateral churn, unnecessary refactors)
   - Test Quality (edge case coverage, brittle assertions)
3. Emit structured review report: Verdict (APPROVE / REQUEST CHANGES / COMMENT), prioritized findings (CRITICAL / WARNING / NIT), and verification assessment.
""",
            "compress-context.md": """---
description: Profile repository token footprint and generate compressed AST context map
---

Execute the Universal Context Optimizer procedure:
1. Run `python3 .agents/skills/context-optimizer/scripts/compress_context.py --profile` to identify token consumption.
2. If preparing codebase context, generate an AST skeleton map (`--hybrid` or `--skeleton`) to minimize token usage by 85-95%.
3. Ingest only the compressed map to locate the precise target files before reading full implementations.
""",
            "test-engineer.md": """---
description: Author deterministic automated test suites, mocks, and edge-case verification
---

Adopt the Universal Test Engineer persona:
1. Analyze target endpoints, services, or modules under test.
2. Identify failure modes, edge cases (boundaries, empty states, nulls, timeouts), and isolation needs.
3. Author deterministic test cases adhering to repository test frameworks (no flaky sleeps, high-signal assertions).
4. Execute test commands to verify red-green status and ensure exit code 0.
""",
            "system-architect.md": """---
description: Design system boundaries, interface contracts, schemas, and Architectural Decision Records (ADRs)
---

Adopt the Universal Systems Architect persona (read-only design):
1. Analyze directory layout, module boundaries, and dependency graphs.
2. Evaluate design trade-offs, performance budgets, and concurrency constraints.
3. Formulate clear interface contracts, schema models, and migration paths.
4. Produce Architectural Decision Records (ADRs) and step-by-step implementation roadmaps.
""",
        }

        for filename, content in commands.items():
            dest = commands_dir / filename
            dest.write_text(content.strip() + "\n", encoding="utf-8")
            created.append(str(dest.relative_to(self.target_dir)))

        # Ensure CLAUDE.md exists
        claude_md = self.target_dir / "CLAUDE.md"
        if not claude_md.exists():
            base_content = f"# Project Guidelines for Claude\n\n{self.eng_standards}\n"
            claude_md.write_text(base_content, encoding="utf-8")
            created.append("CLAUDE.md")

        return created

    # --------------------------------------------------------------------------
    # 2. Cursor
    # --------------------------------------------------------------------------
    def export_cursor(self) -> List[str]:
        created = []
        rules_dir = self.target_dir / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        rules = {
            "engineering-standards.mdc": f"""---
description: Universal Software Engineering Standards
globs: *
alwaysApply: true
---

{self.eng_standards.strip()}
""",
            "code-reviewer.mdc": f"""---
description: Adversarial Senior Code Review Standards & Anti-Patterns
globs: *
alwaysApply: false
---

# Code Review Standards

When conducting code reviews or auditing diffs, apply these rules:

{self.review_standards.strip()}
""",
            "session-workflows.mdc": """---
description: Universal Session Starter & Closer Workflows
globs: *
alwaysApply: false
---

# Session Lifecycle Workflows

## Session Kickoff
- Ingest `SESSION_LOG.md` before making edits to retrieve handover items.
- Verify repository branch hygiene and check for uncommitted changes.
- Establish green baseline before editing.

## Session Conclusion
- Record completed features, changes, validation receipts, and next steps into `SESSION_LOG.md`.
- Keep context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) synchronized.
- Never declare success without verifiable test pass (Zero False Verification).
""",
            "pr-prep.mdc": """---
description: Pre-flight Pull Request Audit and Description Generator
globs: *
alwaysApply: false
---

# PR Preparation Workflow

1. Audit diff for scope creep, debug prints, and secrets.
2. Run test suites to prove pass status.
3. Formulate structured PR descriptions with verifiable receipts.
""",
            "context-optimizer.mdc": """---
description: Token Footprint Profiling and AST Context Compression
globs: *
alwaysApply: false
---

# Context Optimization & Token Compression

When ingesting or exploring large codebases:
1. Run `compress_context.py --profile` to locate token-heavy files.
2. Generate an AST skeleton map (`--hybrid` or `--skeleton`) to reduce token overhead by 85-95%.
""",
            "test-engineer.mdc": f"""---
description: Universal Test Engineering & Quality Automation Standards
globs: *
alwaysApply: false
---

# Test Engineering Standards

When authoring automated tests, fixtures, mocks, or regression suites:

{self.testing_standards.strip()}
""",
            "system-architect.mdc": f"""---
description: Universal Systems Architecture Standards & Decision Framework
globs: *
alwaysApply: false
---

# Systems Architecture Standards

When designing system boundaries, schemas, or technical proposals:

{self.arch_standards.strip()}
""",
        }

        for filename, content in rules.items():
            dest = rules_dir / filename
            dest.write_text(content.strip() + "\n", encoding="utf-8")
            created.append(str(dest.relative_to(self.target_dir)))

        # Legacy fallback .cursorrules
        cursorrules = self.target_dir / ".cursorrules"
        if not cursorrules.exists():
            cursorrules.write_text(self.eng_standards.strip() + "\n", encoding="utf-8")
            created.append(".cursorrules")

        return created

    # --------------------------------------------------------------------------
    # 3. GitHub Copilot
    # --------------------------------------------------------------------------
    def export_copilot(self) -> List[str]:
        created = []
        github_dir = self.target_dir / ".github"
        prompts_dir = github_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copilot Instructions
        instructions_file = github_dir / "copilot-instructions.md"
        instructions_content = f"""# GitHub Copilot Instructions

## Core Mandates
- **Conventions over preferences**: Follow host repository patterns, naming styles, and architectures.
- **Evidence over assumption**: Base diagnoses on actual compiler errors and file contents.
- **Zero false verification**: Never claim a test passed without exit code 0.

{self.eng_standards.strip()}
"""
        instructions_file.write_text(instructions_content.strip() + "\n", encoding="utf-8")
        created.append(str(instructions_file.relative_to(self.target_dir)))

        # 2. Prompts
        prompts = {
            "session-starter.prompt.md": """---
name: session-starter
description: Ingest session history and prime development workspace
---

Inspect `SESSION_LOG.md` for previous handover action items and verify repository state before proceeding with development.
""",
            "session-closer.prompt.md": """---
name: session-closer
description: Record session handover in SESSION_LOG.md and verify tests
---

Summarize current changes, prepend a session record to `SESSION_LOG.md`, verify tests pass, and report handover notes.
""",
            "pr-prep.prompt.md": """---
name: pr-prep
description: Audit diff for scope creep and generate PR description
---

Review the diff against base branch for leftover debug logs or secrets, verify test results, and draft a pull request description.
""",
            "code-review.prompt.md": """---
name: code-review
description: Perform adversarial code review on active branch
---

Act as a senior code reviewer. Audit the current git diff for security vulnerabilities, concurrency hazards, swallowed errors, and test coverage gaps.
""",
            "compress-context.prompt.md": """---
name: compress-context
description: Profile token footprint and compress repository context into AST skeletons
---

Profile repository token usage and extract an ultra-dense AST skeleton context map to minimize token consumption.
""",
            "test-engineer.prompt.md": """---
name: test-engineer
description: Author deterministic unit tests, mocks, and edge-case test suites
---

Adopt the test engineering persona. Analyze the target code and construct deterministic, high-coverage automated tests with edge-case and boundary verification.
""",
            "system-architect.prompt.md": """---
name: system-architect
description: Formulate system architecture plans, schemas, interface contracts, and ADRs
---

Act as a principal systems architect. Analyze module boundaries, design interface contracts, document trade-offs in an ADR, and plan step-by-step implementation.
""",
        }

        for filename, content in prompts.items():
            dest = prompts_dir / filename
            dest.write_text(content.strip() + "\n", encoding="utf-8")
            created.append(str(dest.relative_to(self.target_dir)))

        return created

    # --------------------------------------------------------------------------
    # 4. Roo Code / Cline / OpenCode
    # --------------------------------------------------------------------------
    def export_roo(self) -> List[str]:
        created = []

        # .roomodes JSON configuration
        roomodes_file = self.target_dir / ".roomodes"
        roomodes_data = {
            "customModes": [
                {
                    "slug": "software-engineer",
                    "name": "Senior Software Engineer",
                    "roleDefinition": (
                        "Senior staff software engineer and Tech Lead orchestrator responsible for surgical, production-grade "
                        "code modifications, subagent delegation, peer-review gating, and zero-false-verification standards."
                    ),
                    "groups": ["read", "edit", "command"],
                    "customInstructions": (
                        "Conventions over preferences. Evidence over assumption. "
                        "Zero false verification: Never state a build/test passed without exit code 0. "
                        "Decompose complex work and coordinate specialized subagents when appropriate."
                    ),
                },
                {
                    "slug": "code-reviewer",
                    "name": "Code Reviewer",
                    "roleDefinition": (
                        "Adversarial senior code reviewer auditing code changes for security vulnerabilities, "
                        "concurrency hazards, error handling regressions, and scope discipline."
                    ),
                    "groups": ["read", "command"],
                    "customInstructions": (
                        "Read-only posture. Never modify code directly. Evaluate diffs against Security, "
                        "Concurrency, Error Handling, Scope Discipline, and Test Quality."
                    ),
                },
                {
                    "slug": "test-engineer",
                    "name": "Test & QA Engineer",
                    "roleDefinition": (
                        "Specialized Quality & Test Automation Engineer authoring deterministic test suites, "
                        "mocks, edge cases, and regression verifications."
                    ),
                    "groups": ["read", "edit", "command"],
                    "customInstructions": (
                        "Deterministic tests only. No arbitrary sleeps. Isolate test states. "
                        "Red-green verification: verify tests fail before fix and pass after. "
                        "Zero false verification: exit code 0 required."
                    ),
                },
                {
                    "slug": "system-architect",
                    "name": "System Architect",
                    "roleDefinition": (
                        "Principal systems architect analyzing system boundaries, interface contracts, "
                        "schemas, and architectural decision records (ADRs) without premature code edits."
                    ),
                    "groups": ["read"],
                    "customInstructions": (
                        "Read-only architecture and planning. Evaluate trade-offs, schemas, and boundaries. "
                        "Draft clear ADRs and phased implementation roadmaps."
                    ),
                },
                {
                    "slug": "context-optimizer",
                    "name": "Context Optimizer",
                    "roleDefinition": (
                        "Specialized token optimization and context compression agent extracting AST skeletons "
                        "and packaging repositories under strict token budgets."
                    ),
                    "groups": ["read", "command"],
                    "customInstructions": (
                        "Profile token footprints and skeletonize source files (85-95% token savings). "
                        "Never dump raw implementation files when AST signatures suffice."
                    ),
                },
            ]
        }
        roomodes_file.write_text(json.dumps(roomodes_data, indent=2) + "\n", encoding="utf-8")
        created.append(".roomodes")

        # .clinerules
        clinerules_file = self.target_dir / ".clinerules"
        clinerules_content = f"""# Cline & OpenCode Engineering Rules

{self.eng_standards.strip()}

---

## Session Ledger & Context
- At session start: Consult `SESSION_LOG.md` for recent handover notes.
- At session close: Update `SESSION_LOG.md` and keep context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) synchronized.
"""
        clinerules_file.write_text(clinerules_content.strip() + "\n", encoding="utf-8")
        created.append(".clinerules")

        return created

    # --------------------------------------------------------------------------
    # 5. Windsurf
    # --------------------------------------------------------------------------
    def export_windsurf(self) -> List[str]:
        created = []
        windsurf_file = self.target_dir / ".windsurfrules"
        content = f"""# Windsurf Rules & Development Standards

## Operating Principles
- **Conventions over preferences**: Follow existing styles and patterns in this repo.
- **Evidence over assumption**: Verify all diagnostic claims against real compiler/test output.
- **Zero false verification**: Never claim a test or build succeeded without an exit code 0.

{self.eng_standards.strip()}

---

## Session Handover Workflow
- When starting: Read `SESSION_LOG.md` for current context and priorities.
- When closing: Prepend session entry to `SESSION_LOG.md` and ensure context files are in sync.
"""
        windsurf_file.write_text(content.strip() + "\n", encoding="utf-8")
        created.append(".windsurfrules")
        return created

    # --------------------------------------------------------------------------
    # 6. Google Antigravity & Gemini CLI (.agents/)
    # --------------------------------------------------------------------------
    def export_antigravity(self, mode: str = "symlink") -> List[str]:
        created = []
        target_agents_dir = self.target_dir / ".agents"
        skills_dest = target_agents_dir / "skills"
        agents_dest = target_agents_dir / "agents"
        skills_dest.mkdir(parents=True, exist_ok=True)
        agents_dest.mkdir(parents=True, exist_ok=True)

        # Link/copy skills
        skills_src = self.toolkit_dir / "skills"
        if skills_src.exists():
            for s in skills_src.iterdir():
                if s.is_dir():
                    dest = skills_dest / s.name
                    if dest.exists() or dest.is_symlink():
                        dest.unlink() if dest.is_symlink() else shutil.rmtree(dest)
                    if mode == "symlink":
                        dest.symlink_to(s)
                    else:
                        shutil.copytree(s, dest)
                    created.append(f".agents/skills/{s.name}")

        # Link/copy agents
        agents_src = self.toolkit_dir / "agents"
        if agents_src.exists():
            for a in agents_src.iterdir():
                if a.is_dir():
                    dest = agents_dest / a.name
                    if dest.exists() or dest.is_symlink():
                        dest.unlink() if dest.is_symlink() else shutil.rmtree(dest)
                    if mode == "symlink":
                        dest.symlink_to(a)
                    else:
                        shutil.copytree(a, dest)
                    created.append(f".agents/agents/{a.name}")

        return created


def export_tool_adapters(toolkit_dir: Path, target_dir: Path, tool: str, mode: str = "symlink") -> Dict[str, List[str]]:
    """Exports configurations for specified tool or all tools."""
    exporter = AdapterExporter(toolkit_dir, target_dir)
    results = {}

    tool = tool.lower()

    if tool in ["claude", "all"]:
        results["Claude Code"] = exporter.export_claude()

    if tool in ["cursor", "all"]:
        results["Cursor"] = exporter.export_cursor()

    if tool in ["copilot", "github-copilot", "all"]:
        results["GitHub Copilot"] = exporter.export_copilot()

    if tool in ["roo", "opencode", "cline", "all"]:
        results["Roo Code / Cline / OpenCode"] = exporter.export_roo()

    if tool in ["windsurf", "all"]:
        results["Windsurf"] = exporter.export_windsurf()

    if tool in ["antigravity", "gemini", "all"]:
        results["Google Antigravity & Gemini CLI"] = exporter.export_antigravity(mode=mode)

    return results


def main():
    parser = argparse.ArgumentParser(description="Universal Multi-Tool AI Adapter Generator.")
    parser.add_argument("--target", type=str, default=".", help="Target project directory")
    parser.add_argument(
        "--tool",
        type=str,
        default="all",
        choices=["all", "claude", "cursor", "copilot", "roo", "opencode", "cline", "windsurf", "antigravity", "gemini"],
        help="Target AI tool ecosystem (default: all)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="symlink",
        choices=["symlink", "copy"],
        help="Installation mode for .agents/ (symlink or copy)",
    )
    parser.add_argument("--toolkit-dir", type=str, default=None, help="Path to agent-toolkit repository root")

    args = parser.parse_args()

    toolkit_dir = Path(args.toolkit_dir).resolve() if args.toolkit_dir else get_toolkit_dir()
    target_dir = Path(args.target).resolve()

    if not toolkit_dir.exists():
        print(f"❌ Error: Toolkit directory not found: {toolkit_dir}")
        sys.exit(1)

    print(f"📦 Exporting agent-toolkit adapters to: {target_dir}")
    print(f"⚙️ Target ecosystem: {args.tool.upper()}")

    results = export_tool_adapters(toolkit_dir, target_dir, args.tool, mode=args.mode)

    print("")
    for tool_name, files in results.items():
        print(f"✅ {tool_name}:")
        for f in files:
            print(f"   • {f}")

    print("\n✨ Multi-tool setup complete.")


if __name__ == "__main__":
    main()
