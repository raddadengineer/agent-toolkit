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
  - OpenAI Codex (.codex/config.toml, .codex/agents/*.toml, .agents/skills/, AGENTS.md)

Usage:
    python3 export_adapters.py --target /path/to/project --tool all
    python3 export_adapters.py --target /path/to/project --tool claude
    python3 export_adapters.py --target /path/to/project --tool cursor
    python3 export_adapters.py --target /path/to/project --tool copilot
    python3 export_adapters.py --target /path/to/project --tool codex
    python3 export_adapters.py --target /path/to/project --tool roo
    python3 export_adapters.py --target /path/to/project --tool windsurf
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _toml_basic_str(value: str) -> str:
    """Escapes a Python string as a single-line TOML basic string."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _toml_multiline_str(value: str) -> str:
    """Escapes a Python string as a multi-line TOML basic string."""
    normalized = value.replace("\r\n", "\n")
    escaped = normalized.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    escaped = re.sub(r'"+$', lambda m: '\\"' * len(m.group(0)), escaped)
    return f'"""\n{escaped}\n"""'


def _parse_agent_markdown(text: str, default_name: str) -> Tuple[Dict[str, Any], str]:
    """Parses YAML frontmatter (name, description, tools) and body from agent.md."""
    meta: Dict[str, Any] = {"name": default_name, "description": "", "tools": []}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta, text.strip()

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return meta, text.strip()

    frontmatter = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).strip()
    in_tools = False
    for raw in frontmatter:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if in_tools and stripped.startswith("- "):
            tool_name = stripped[2:].strip().strip("'\"")
            if tool_name:
                meta["tools"].append(tool_name)
            continue
        in_tools = False
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key == "tools":
                if val.startswith("[") and val.endswith("]"):
                    meta["tools"] = [t.strip().strip("'\"") for t in val[1:-1].split(",") if t.strip()]
                else:
                    in_tools = True
            elif key in {"name", "description"} and val:
                meta[key] = val
    return meta, body


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
        self.debug_standards = read_file_safe(
            toolkit_dir / "agents" / "debugger" / "rules" / "debugging-standards.md"
        )
        self.sec_standards = read_file_safe(
            toolkit_dir / "agents" / "security_auditor" / "rules" / "security-standards.md"
        )
        self.db_standards = read_file_safe(
            toolkit_dir / "agents" / "database_engineer" / "rules" / "database-standards.md"
        )
        self.devops_standards = read_file_safe(
            toolkit_dir / "agents" / "devops_engineer" / "rules" / "devops-standards.md"
        )
        self.research_standards = read_file_safe(
            toolkit_dir / "agents" / "research" / "rules" / "research-standards.md"
        )
        self.sysadmin_standards = read_file_safe(
            toolkit_dir / "agents" / "sys_admin" / "rules" / "sysadmin-standards.md"
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
            "debugger.md": """---
description: Root-cause debugging, minimal reproduction scripts (repro.sh), and git bisect
---

Execute the Universal Root-Cause Debugger procedure:
1. Analyze and deobfuscate stack traces using `python3 scripts/bisect_debugger.py --analyze-trace <log>`.
2. Generate a minimal reproduction script using `python3 scripts/bisect_debugger.py --repro "<cmd>" --output repro.sh`.
3. If investigating a regression, run automated git bisect using `python3 scripts/bisect_debugger.py --bisect --test "<cmd>" --good <tag> --bad HEAD`.
4. Apply the surgical fix and verify Red-Green proof (exit 0).
""",
            "security-audit.md": """---
description: SAST security scan, secret leak prevention, and dependency vulnerability audit
---

Execute the Universal Security Auditor procedure:
1. Run `python3 scripts/audit_security.py --check` across the repository.
2. Audit for OWASP Top 10 injection vectors (SQL, command execution, eval).
3. Verify zero hardcoded secrets or exposed private keys.
4. Report prioritized findings (CRITICAL / HIGH / MEDIUM).
""",
            "db-migrate.md": """---
description: Database migration safety, zero-downtime checks, and rollback reversibility audit
---

Execute the Universal Database Migration Safety procedure:
1. Run `python3 scripts/verify_migrations.py --check` across all migration directories.
2. Verify all migrations have valid downgrade/rollback procedures.
3. Audit for table-locking anti-patterns (ADD COLUMN NOT NULL without default, non-concurrent indexes).
4. Verify query plans using EXPLAIN ANALYZE for hot paths.
""",
            "doc-sync.md": """---
description: Documentation and schema drift sentinel to catch outdated docs and broken links
---

Execute the Universal Documentation Drift Sentinel procedure:
1. Run `python3 scripts/check_doc_drift.py --check`.
2. Verify all agents, skills, and tools on disk are accurately documented.
3. Fix any broken internal markdown references or missing descriptions.
""",
            "container-engineer.md": """---
description: Scaffold hardened multi-stage Dockerfiles and audit container security & layer caching
---

Execute the Universal Container Engineer procedure:
1. Run `python3 scripts/harden_docker.py --audit --check` to inspect existing Dockerfiles.
2. Or scaffold a hardened, non-root, multi-stage Dockerfile via `python3 scripts/harden_docker.py --init --stack <python|node|go|rust>`.
3. Verify zero `:latest` base image tags, no baked secrets, and deterministic dependency layer caching.
""",
            "ci-workflow.md": """---
description: Synthesize hardened GitHub Actions CI pipelines and audit workflow security
---

Execute the Universal CI/CD Workflow Engineer procedure:
1. Run `python3 scripts/synthesize_ci.py --audit --check` to scan `.github/workflows/` for unpinned actions, missing timeouts, and broad permissions.
2. Or scaffold a hardened pipeline via `python3 scripts/synthesize_ci.py --init --stack <python|node|go|rust>`.
""",
            "dependency-audit.md": """---
description: Audit multi-ecosystem dependency manifests for wildcards, missing lockfiles, and deprecations
---

Execute the Universal Dependency Auditor procedure:
1. Run `python3 scripts/audit_deps.py --check` across the repository.
2. Remediate any wildcard version specifiers (`*`, `latest`), deprecated packages, or missing lockfiles.
""",
            "release-manager.md": """---
description: Calculate SemVer version bumps from Conventional Commits and generate CHANGELOG.md
---

Execute the Universal Release Manager procedure:
1. Run `python3 scripts/manage_release.py --bump` to calculate the next Semantic Version from git commit history.
2. Run `python3 scripts/manage_release.py --changelog` or `--notes` to update `CHANGELOG.md` and draft GitHub release notes.
""",
            "memory-manager.md": """---
description: Manage and recall scoped developer memories, patterns, and anti-patterns
---

Execute the Universal Memory Manager procedure:
1. Before architectural changes or tricky debugging, recall established rules and gotchas: `python3 scripts/manage_memory.py recall "<topic>"`.
2. Record proven patterns and discovered anti-patterns: `python3 scripts/manage_memory.py record --category patterns --title "<title>" --content "<content>"`.
3. Audit memory integrity and clean checksums: `python3 scripts/manage_memory.py audit`.
""",
            "dreamer.md": """---
description: Run out-of-band offline memory consolidation across session logs and transcripts
---

Execute the Universal Dreamer procedure:
1. Synthesize recent session logs and transcripts: `python3 scripts/dream_consolidator.py --analyze`.
2. Interactively review or auto-promote candidate patterns and anti-patterns: `python3 scripts/dream_consolidator.py --review` (or `--auto-promote`).
3. Export consolidation proposal: `python3 scripts/dream_consolidator.py --output MEMORY_PROPOSAL.md`.
""",
            "sys-admin.md": """---
description: Principal SRE triage (health/inodes/logs/TLS), host/IaC hardening audit, safe transactional apply & drift snapshots
---

Execute the Universal System Administrator & Principal SRE procedure:
1. Run read-only USE/RED triage: `python3 scripts/sys_admin.py --health --ports --processes --json` and `python3 scripts/sys_admin.py --audit-host --json`.
2. Condense incident logs & probe endpoints: `python3 scripts/sys_admin.py --triage-logs <path>` and `--check-endpoints <manifest.json>`.
3. Audit server configs (SSH, systemd, Nginx, Caddy), K8s/Compose/sudoers/firewall, ops scripts, and Terraform/Ansible: `python3 scripts/sys_admin.py --audit . --native-lint --check`.
4. Apply config updates transactionally with validation & auto-rollback (`--apply-safe SRC DEST --validate-cmd "..." --dry-run`) and track host drift (`--snapshot` / `--diff-snapshot`).
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
            "debugger.mdc": f"""---
description: Universal Root-Cause Debugging & Git Bisect Standards
globs: *
alwaysApply: false
---

# Debugging Standards

When investigating bugs, failures, or regressions:

{self.debug_standards.strip()}
""",
            "security-auditor.mdc": f"""---
description: Universal Application Security & SAST Auditing Standards
globs: *
alwaysApply: false
---

# Security Auditing Standards

When auditing code, dependencies, or permissions:

{self.sec_standards.strip()}
""",
            "database-engineer.mdc": f"""---
description: Universal Database Migration Safety & Zero-Downtime Standards
globs: *
alwaysApply: false
---

# Database Migration Standards

When modifying database schemas, DDL, or migrations:

{self.db_standards.strip()}
""",
            "doc-sync.mdc": """---
description: Documentation & Schema Drift Sentinel
globs: *
alwaysApply: false
---

# Documentation Sync Standards

Ensure all agents, skills, and commands are accurately documented without broken internal references.
""",
            "container-engineer.mdc": f"""---
description: Container Hardening, Multi-Stage Dockerfiles & Layer Caching Standards
globs: Dockerfile*,*.dockerfile,.dockerignore,docker-compose*.yml
alwaysApply: false
---

# Container & Dockerfile Hardening Standards

When authoring or auditing Dockerfiles and container configurations:

{self.devops_standards.strip()}
""",
            "ci-workflow.mdc": f"""---
description: CI/CD Pipeline Synthesis & GitHub Actions Security Standards
globs: .github/workflows/*.yml,.github/workflows/*.yaml
alwaysApply: false
---

# CI/CD Workflow Security Standards

When authoring or auditing CI/CD pipelines:

{self.devops_standards.strip()}
""",
            "dependency-auditor.mdc": """---
description: Multi-Ecosystem Dependency Manifest Hygiene & Security Standards
globs: package.json,pyproject.toml,requirements*.txt,Cargo.toml,go.mod
alwaysApply: false
---

# Dependency Hygiene Standards

- Ban wildcard version specifiers (`*`, `latest`) in manifests.
- Commit deterministic lockfiles (`package-lock.json`, `Cargo.lock`, `go.sum`, `poetry.lock`).
- Replace deprecated libraries with actively maintained alternatives.
""",
            "release-manager.mdc": """---
description: Semantic Versioning & Conventional Commits Release Standards
globs: CHANGELOG.md
alwaysApply: false
---

# Release Management Standards

- Derive version bumps (`major`, `minor`, `patch`) deterministically from Conventional Commits (`feat`, `fix`, `perf`, `BREAKING CHANGE`).
- Keep `CHANGELOG.md` structured under Keep a Changelog sections (`Added`, `Fixed`, `Changed`, `Breaking Changes`).
""",
            "memory-manager.mdc": """---
description: Scoped Persistent Developer Memory & Anti-Pattern Standards
globs: *
alwaysApply: false
---

# Scoped Memory Management Standards

- Check repository memory (`memory/`) before major changes to recall known architecture decisions and pitfalls.
- Record proven solution patterns and tricky gotchas using `python3 scripts/manage_memory.py record`.
- Maintain content-addressed SHA-256 integrity and audit memory decay using `python3 scripts/manage_memory.py audit`.
""",
            "dreamer.mdc": """---
description: Autonomous Out-of-Band Memory Consolidation & Dreaming Standards
globs: *
alwaysApply: false
---

# Dreamer Consolidation Standards

- Run memory consolidation out-of-band at session conclusion or idle time to prevent context distraction during active coding.
- Ingest `SESSION_LOG.md` and conversation transcripts to extract recurring failure modes and winning patterns.
- Require explicit developer review before promoting candidate memories into permanent repo memory.
""",
            "sys-admin.mdc": f"""---
description: System Administration, Infrastructure Hardening & SRE Triage Standards
globs: *.sh,*.ps1,*.service,*.timer,*.conf,sshd_config*,nginx*,Caddyfile*,*.caddy,*.tf,*.tfvars,*ansible*.yml,*playbook*.yml,crontab*,docker-compose*.yml,compose*.yml,*sudoers*,*nftables*.conf,*.nft,*ufw*.rules,*iptables*.rules
alwaysApply: false
---

# System Administration & SRE Standards

When diagnosing host/network incidents or modifying server configs, ops scripts, and infrastructure manifests:

{self.sysadmin_standards.strip()}
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
            "debugger.prompt.md": """---
name: debugger
description: Root-cause debugging, minimal reproduction scripts, and automated git bisect
---

Act as a root-cause debugging specialist. Analyze error traces, construct a minimal reproduction harness (repro.sh), and isolate regressions.
""",
            "security-audit.prompt.md": """---
name: security-audit
description: Audit source code for SAST vulnerabilities and credential exposures
---

Act as an application security auditor. Scan source code and dependencies for injection vectors, secret exposures, and CVE vulnerabilities.
""",
            "db-migrate.prompt.md": """---
name: db-migrate
description: Audit database migrations for reversibility and zero-downtime safety
---

Act as a database reliability engineer. Validate migration rollback safety, detect table-locking anti-patterns, and verify query plans.
""",
            "doc-sync.prompt.md": """---
name: doc-sync
description: Verify documentation consistency and detect broken internal links
---

Scan documentation for drift against codebase reality and verify that all internal markdown references resolve correctly.
""",
            "container-engineer.prompt.md": """---
name: container-engineer
description: Scaffold hardened multi-stage Dockerfiles and audit container security
---

Act as a principal container engineer. Audit Dockerfiles for non-root execution, pinned image tags, secret hygiene, and optimal layer caching.
""",
            "ci-workflow.prompt.md": """---
name: ci-workflow
description: Synthesize hardened GitHub Actions workflows and audit pipeline security
---

Act as a CI/CD security engineer. Scaffold or audit GitHub Actions pipelines for explicit read-all permissions, pinned action versions, and job timeouts.
""",
            "dependency-audit.prompt.md": """---
name: dependency-audit
description: Audit dependency manifests for wildcards, missing lockfiles, and deprecations
---

Scan dependency manifests across Python, Node, Go, and Rust for wildcard version specifiers, deprecated packages, and lockfile hygiene.
""",
            "release-manager.prompt.md": """---
name: release-manager
description: Calculate SemVer version bumps and generate Conventional Commits changelogs
---

Analyze git commit history since the latest tag to determine the next Semantic Version bump and compile structured CHANGELOG.md release notes.
""",
            "memory-manager.prompt.md": """---
name: memory-manager
description: Recall, record, and inspect persistent scoped developer memories
---

Search indexed repository memory for past solutions, architecture decisions, and anti-patterns, or record newly solved challenges into persistent storage.
""",
            "dreamer.prompt.md": """---
name: dreamer
description: Run out-of-band offline memory consolidation and pattern distillation
---

Analyze session ledgers and execution transcripts to extract winning solution patterns, recurring error traps, and draft memory update proposals.
""",
            "sys-admin.prompt.md": """---
name: sys-admin
description: Principal SRE triage (health/logs/posture/TLS), server/IaC hardening audit, safe apply & drift snapshots
---

Act as a Principal Systems Administrator and SRE. Run read-only USE/RED triage (`--health --ports --processes`, `--triage-logs`, `--audit-host`), audit server/K8s/Compose/sudoers/firewall/IaC configs, apply changes safely with validation & rollback (`--apply-safe`), and track drift snapshots (`--snapshot` / `--diff-snapshot`).
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
                {
                    "slug": "debugger",
                    "name": "Root-Cause Debugger",
                    "roleDefinition": (
                        "Root-cause investigation and debugging specialist authoring minimal reproduction harnesses "
                        "(repro.sh) and isolating regressions via automated git bisection."
                    ),
                    "groups": ["read", "edit", "command"],
                    "customInstructions": (
                        "Reproduction precedes modification: never edit code without a failing repro. "
                        "Enforce deterministic Red-Green verification."
                    ),
                },
                {
                    "slug": "security-auditor",
                    "name": "Security Auditor",
                    "roleDefinition": (
                        "Principal AppSec auditor scanning source code and dependencies for SAST injection vectors, "
                        "hardcoded secrets, and supply chain vulnerabilities."
                    ),
                    "groups": ["read", "command"],
                    "customInstructions": (
                        "Read-only posture. Hard block on critical injection vectors or leaked credentials. "
                        "Deliver actionable, parameterized remediation snippets."
                    ),
                },
                {
                    "slug": "database-engineer",
                    "name": "Database Engineer",
                    "roleDefinition": (
                        "Principal database reliability engineer verifying migration rollback reversibility, "
                        "preventing table-locking hazards, and optimizing query plans."
                    ),
                    "groups": ["read", "edit", "command"],
                    "customInstructions": (
                        "Every migration must have a tested downgrade routine. Never add NOT NULL columns without default. "
                        "Ensure indexes are built concurrently."
                    ),
                },
                {
                    "slug": "devops-engineer",
                    "name": "DevOps & Release Engineer",
                    "roleDefinition": (
                        "Principal DevOps, container, CI/CD, and release engineer responsible for multi-stage Dockerfile "
                        "hardening, GitHub Actions pipeline synthesis, dependency manifest auditing, and SemVer releases."
                    ),
                    "groups": ["read", "edit", "command"],
                    "customInstructions": (
                        "Enforce non-root container execution, pinned image and action versions, explicit CI permissions, "
                        "zero wildcard dependencies, and Conventional Commits SemVer releases."
                    ),
                },
                {
                    "slug": "research",
                    "name": "Technical Researcher",
                    "roleDefinition": (
                        "Technical research and documentation sandbox specialist ingesting external API docs, "
                        "SDK specifications, and changelogs into concise engineering briefs."
                    ),
                    "groups": ["read", "command"],
                    "customInstructions": (
                        "Read-only sandbox posture. Verify installed library versions before researching. "
                        "Distill external docs into exact signatures, minimal working snippets, and citations."
                    ),
                },
                {
                    "slug": "sys-admin",
                    "name": "System Administrator & SRE",
                    "roleDefinition": (
                        "Principal systems administrator, infrastructure hardening specialist, and SRE responsible for "
                        "USE/RED host triage, log condensation, live posture audits, transactional config apply with rollback, "
                        "drift snapshots, server/K8s/IaC auditing, and operational runbooks."
                    ),
                    "groups": ["read", "edit", "command"],
                    "customInstructions": (
                        "Enforce Tier 0/1/2 blast-radius guardrails and read-only triage before mutation. Use --triage-logs, "
                        "--audit-host, --apply-safe with validation/rollback, and --snapshot/--diff-snapshot; verify exit code 0."
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

        # Link/copy hooks.json
        hooks_src = self.toolkit_dir / "hooks" / "hooks.json"
        if hooks_src.exists():
            dest_hooks = target_agents_dir / "hooks.json"
            if dest_hooks.exists() or dest_hooks.is_symlink():
                dest_hooks.unlink()
            if mode == "symlink":
                dest_hooks.symlink_to(hooks_src)
            else:
                shutil.copy2(hooks_src, dest_hooks)
            created.append(".agents/hooks.json")

        # Link/copy mcp_config.json
        mcp_src = self.toolkit_dir / "mcp" / "mcp_config.json"
        if mcp_src.exists():
            dest_mcp = target_agents_dir / "mcp_config.json"
            if dest_mcp.exists() or dest_mcp.is_symlink():
                dest_mcp.unlink()
            if mode == "symlink":
                dest_mcp.symlink_to(mcp_src)
            else:
                shutil.copy2(mcp_src, dest_mcp)
            created.append(".agents/mcp_config.json")

        # Link/copy scripts
        scripts_src = self.toolkit_dir / "scripts"
        if scripts_src.exists():
            dest_scripts = target_agents_dir / "scripts"
            if dest_scripts.exists() or dest_scripts.is_symlink():
                dest_scripts.unlink() if dest_scripts.is_symlink() else shutil.rmtree(dest_scripts)
            if mode == "symlink":
                dest_scripts.symlink_to(scripts_src)
            else:
                shutil.copytree(scripts_src, dest_scripts)
            created.append(".agents/scripts")

        # Ensure AGENTS.md and GEMINI.md exist
        agents_md = self.target_dir / "AGENTS.md"
        if not agents_md.exists():
            base_content = f"# Project Guidelines & Architecture\n\n{self.eng_standards}\n"
            agents_md.write_text(base_content, encoding="utf-8")
            created.append("AGENTS.md")

        gemini_md = self.target_dir / "GEMINI.md"
        if not gemini_md.exists():
            base_content = f"# Project Guidelines & Architecture\n\n{self.eng_standards}\n"
            gemini_md.write_text(base_content, encoding="utf-8")
            created.append("GEMINI.md")

        return created

    def _sync_dir_or_file(self, src: Path, dest: Path, mode: str) -> None:
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)
        if mode == "symlink":
            dest.symlink_to(src)
        elif src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

    # --------------------------------------------------------------------------
    # 7. OpenAI Codex (.codex/ & .agents/skills/ & AGENTS.md)
    # --------------------------------------------------------------------------
    def export_codex(self, mode: str = "symlink") -> List[str]:
        created = []
        codex_dir = self.target_dir / ".codex"
        agents_out_dir = codex_dir / "agents"
        agents_out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Export subagents to .codex/agents/<name>.toml
        agents_src = self.toolkit_dir / "agents"
        if agents_src.exists():
            for agent_dir in sorted(agents_src.iterdir()):
                if not agent_dir.is_dir():
                    continue
                agent_md = agent_dir / "agent.md"
                if not agent_md.is_file():
                    continue
                meta, body = _parse_agent_markdown(agent_md.read_text(encoding="utf-8"), agent_dir.name)
                instruction_parts = [body] if body else []
                rules_dir = agent_dir / "rules"
                if rules_dir.is_dir():
                    for rule_file in sorted(rules_dir.glob("*.md")):
                        rule_text = rule_file.read_text(encoding="utf-8").strip()
                        if rule_text:
                            instruction_parts.append(rule_text)
                developer_instructions = "\n\n---\n\n".join(instruction_parts)
                tools_set = set(meta.get("tools", []))
                sandbox_mode = "workspace-write" if (tools_set & {"replace_file_content", "write_to_file"}) else "read-only"

                toml_lines = [
                    "# Generated by agent-toolkit",
                    f"name = {_toml_basic_str(meta['name'])}",
                    f"description = {_toml_basic_str(meta.get('description') or meta['name'])}",
                    f"sandbox_mode = {_toml_basic_str(sandbox_mode)}",
                    f"developer_instructions = {_toml_multiline_str(developer_instructions)}",
                ]
                dest_toml = agents_out_dir / f"{agent_dir.name}.toml"
                dest_toml.write_text("\n".join(toml_lines) + "\n", encoding="utf-8")
                created.append(str(dest_toml.relative_to(self.target_dir)))

        # 2. Export .codex/config.toml (preserve user-customized configs lacking marker)
        config_marker = "# Generated by agent-toolkit"
        config_file = codex_dir / "config.toml"
        should_write_config = True
        if config_file.exists():
            existing_cfg = read_file_safe(config_file)
            if config_marker not in existing_cfg:
                should_write_config = False

        if should_write_config:
            cfg_lines = [
                config_marker,
                'project_doc_fallback_filenames = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]',
            ]
            mcp_src = self.toolkit_dir / "mcp" / "mcp_config.json"
            if mcp_src.exists():
                try:
                    mcp_data = json.loads(mcp_src.read_text(encoding="utf-8"))
                    servers = mcp_data.get("mcpServers", {})
                    for srv_name, srv_cfg in servers.items():
                        if not isinstance(srv_cfg, dict):
                            continue
                        safe_srv = srv_name if re.match(r"^[A-Za-z0-9_-]+$", srv_name) else _toml_basic_str(srv_name)
                        cfg_lines.append("")
                        cfg_lines.append(f"[mcp_servers.{safe_srv}]")
                        if srv_cfg.get("command"):
                            cfg_lines.append(f"command = {_toml_basic_str(str(srv_cfg['command']))}")
                        args_list = srv_cfg.get("args", [])
                        if isinstance(args_list, list):
                            formatted_args = ", ".join(_toml_basic_str(str(a)) for a in args_list)
                            cfg_lines.append(f"args = [{formatted_args}]")
                        env_map = srv_cfg.get("env", {})
                        if isinstance(env_map, dict) and env_map:
                            cfg_lines.append("")
                            cfg_lines.append(f"[mcp_servers.{safe_srv}.env]")
                            for ek, ev in env_map.items():
                                safe_ek = ek if re.match(r"^[A-Za-z0-9_-]+$", ek) else _toml_basic_str(ek)
                                cfg_lines.append(f"{safe_ek} = {_toml_basic_str(str(ev))}")
                except (OSError, ValueError) as exc:
                    sys.stderr.write(f"⚠️ Warning: Could not parse mcp_config.json for Codex config: {exc}\n")

            config_file.write_text("\n".join(cfg_lines) + "\n", encoding="utf-8")
            created.append(str(config_file.relative_to(self.target_dir)))

        # 3. Link/copy skills and scripts under .agents/ for native Codex skill discovery
        target_agents_dir = self.target_dir / ".agents"
        skills_dest = target_agents_dir / "skills"
        skills_dest.mkdir(parents=True, exist_ok=True)
        skills_src = self.toolkit_dir / "skills"
        if skills_src.exists():
            for s in sorted(skills_src.iterdir()):
                if s.is_dir():
                    dest = skills_dest / s.name
                    self._sync_dir_or_file(s, dest, mode)
                    created.append(f".agents/skills/{s.name}")

        scripts_src = self.toolkit_dir / "scripts"
        if scripts_src.exists():
            dest_scripts = target_agents_dir / "scripts"
            self._sync_dir_or_file(scripts_src, dest_scripts, mode)
            created.append(".agents/scripts")

        # 4. Ensure AGENTS.md exists
        agents_md = self.target_dir / "AGENTS.md"
        if not agents_md.exists():
            base_content = f"# Project Guidelines & Architecture\n\n{self.eng_standards}\n"
            agents_md.write_text(base_content, encoding="utf-8")
            created.append("AGENTS.md")

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

    if tool in ["codex", "openai-codex", "all"]:
        results["OpenAI Codex"] = exporter.export_codex(mode=mode)

    return results


def main():
    parser = argparse.ArgumentParser(description="Universal Multi-Tool AI Adapter Generator.")
    parser.add_argument("--target", type=str, default=".", help="Target project directory")
    parser.add_argument(
        "--tool",
        type=str,
        default="all",
        choices=["all", "claude", "cursor", "copilot", "codex", "openai-codex", "roo", "opencode", "cline", "windsurf", "antigravity", "gemini"],
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

    # Automatically register project in agent-toolkit registry
    try:
        try:
            from scripts.manage_installs import register_project
        except ImportError:
            from manage_installs import register_project
        register_project(target_dir, tool=args.tool, mode=args.mode)
    except Exception as exc:
        sys.stderr.write(f"⚠️ Warning: Could not register project in installation registry: {exc}\n")

    print("\n✨ Multi-tool setup complete.")


if __name__ == "__main__":
    main()
