# 🧰 Agent Toolkit — Detailed Component Reference

This document provides complete architectural specifications, capabilities, and workflows for all 18 progressive disclosure skills, 11 specialized subagents, lifecycle hooks, and Model Context Protocol (MCP) servers in `agent-toolkit`.

---

## 📋 Table of Contents
- [Core Skills](#-core-skills)
  - [1. context-optimizer](#1-context-optimizer-skill)
  - [2. session-starter](#2-session-starter-skill)
  - [3. session-closer](#3-session-closer-skill)
  - [4. pr-prep](#4-pr-prep-skill)
  - [5. code-reviewer](#5-code-reviewer-skill)
  - [6. test-engineer](#6-test-engineer-skill)
  - [7. system-architect](#7-system-architect-skill)
  - [8. debugger](#8-debugger-skill)
  - [9. security-auditor](#9-security-auditor-skill)
  - [10. database-engineer](#10-database-engineer-skill)
  - [11. container-engineer](#11-container-engineer-skill)
  - [12. ci-workflow](#12-ci-workflow-skill)
  - [13. dependency-auditor](#13-dependency-auditor-skill)
  - [14. release-manager](#14-release-manager-skill)
  - [15. memory-manager](#15-memory-manager-skill)
  - [16. dreamer](#16-dreamer-skill)
  - [17. doc-sync](#17-doc-sync-skill)
  - [18. sys-admin](#18-sys-admin-skill)
- [Specialized Subagents](#-specialized-subagents)
- [Lifecycle Hooks & Auto-Formatters](#-lifecycle-hooks--auto-formatters)
- [Native MCP Suite](#-native-mcp-suite)

---

## 🎯 Core Skills

### 1. `context-optimizer` (Skill)
Compresses codebase context and minimizes token consumption by **85–95%**:
- **Multi-Language AST Skeletonizer**: Extracts classes, interfaces, method signatures, types, and docstrings while stripping implementation bodies across Python, TypeScript/JavaScript, Swift, Go, and Rust.
- **Token Heatmap Profiler**: Analyzes token footprints across directories and flags oversized files or accidental lockfile/bundle bloat.
- **Repository Context Packer**: Bundles projects into high-density Markdown or XML prompts under configurable token budgets (e.g. `--budget 8000`).
- **Hybrid Mode**: Retains full content for key entry points (`README.md`, package manifests) while skeletonizing all underlying code.
- **Instruction**: [`skills/context-optimizer/SKILL.md`](../skills/context-optimizer/SKILL.md)

### 2. `session-starter` (Skill)
The orientation bookend to `session-closer`:
- **Branch & Hygiene Audit**: Verifies working tree cleanliness, active branch status, and recent commit history.
- **Handover Ingestion**: Ingests `SESSION_LOG.md` to surface previous accomplishments, validation proofs, and outstanding next steps.
- **Context Synchronization**: Checks bit-for-bit SHA-256 parity between `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`.
- **Memory Priming**: Automatically loads active repository patterns, anti-patterns, and rules into working context.
- **Baseline Establishment**: Runs project builds/tests before edits begin under Zero False Verification.
- **Instruction**: [`skills/session-starter/SKILL.md`](../skills/session-starter/SKILL.md)

### 3. `session-closer` (Skill)
Guides AI agents through a disciplined 5-step handover procedure at the end of every engineering session:
1. **Analyze Accomplishments**: Scans `git status --short` and `git diff --stat`.
2. **Record in `SESSION_LOG.md`**: Prepends a clean, dated markdown entry documenting the session goal, specific changes, validation proof, and next steps.
3. **Synchronize Context Files**: Keeps `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` bit-for-bit identical via SHA-256 validation.
4. **Verify Build & Tests**: Runs ecosystem-specific test commands under a strict Zero False Verification mandate (must return exit code 0).
5. **Deliver Handover Summary**: Provides an executive report summarizing completed work and immediate next actions.
- **Instruction**: [`skills/session-closer/SKILL.md`](../skills/session-closer/SKILL.md)

### 4. `pr-prep` (Skill)
Pre-flight pull request audit and description authoring:
- **Diff & Leak Audit**: Scans diffs for forgotten `console.log`, `print()`, `debugger`, and hardcoded secrets/API keys.
- **Build & Test Verification**: Guarantees test pass receipts before PR opening.
- **Generate PR Markdown**: Creates ready-to-copy PR summaries complete with test receipts and verification checklists.
- **Instruction**: [`skills/pr-prep/SKILL.md`](../skills/pr-prep/SKILL.md)

### 5. `code-reviewer` (Skill)
Automated diff inspection and adversarial code auditing (`review_code.py` / `atk review`):
- **5 Review Dimensions**: Security & Secrets, Concurrency & Thread Safety, Error Handling & Swallowing, Architecture & Scope, and Test Quality.
- **Automated Diff Inspection**: Detects silent error swallowing (`except: pass`), blocking sleeps in async context, and missing test coverage.
- **Structured Output**: Delivers actionable verdicts (`APPROVE`, `REQUEST CHANGES`) with severity ratings (`CRITICAL`, `WARNING`, `NIT`).
- **Instruction**: [`skills/code-reviewer/SKILL.md`](../skills/code-reviewer/SKILL.md)

### 6. `test-engineer` (Skill)
Deterministic test suite scaffolding and boundary coverage:
- **Flake-free determinism**: Employs condition-based polling and strict state isolation; bans arbitrary sleeps.
- **Red-Green verification**: Proves bug reproduction by verifying tests fail before the fix and pass cleanly after.
- **Comprehensive coverage**: Generates parameterized edge cases (empty states, boundary limits, unicode, overflow, timeouts) across Python, TypeScript, Go, and Rust.
- **Instruction**: [`skills/test-engineer/SKILL.md`](../skills/test-engineer/SKILL.md)

### 7. `system-architect` (Skill)
Architecture Decision Record (ADR) manager, interface contracts, and system boundary sentinel:
- **ADR Management**: Scaffolds, indexes, and audits Architecture Decision Records (`docs/adr/`) using MADR templates.
- **Interface Contract Design**: Formulates strict schema models and API boundary contracts.
- **Boundary Auditing**: Flags cyclic dependencies and architectural layer violations.
- **Instruction**: [`skills/system-architect/SKILL.md`](../skills/system-architect/SKILL.md)

### 8. `debugger` (Skill)
Root-cause debugging and regression isolation skill:
- **Trace Deobfuscation**: Parses raw stack traces across Python, TypeScript, Swift, and Go into clean call frame breakdowns.
- **Reproduction Harness**: Synthesizes standalone, self-contained reproduction scripts (`repro.sh` / `repro.py`) with zero external test runner overhead.
- **Automated Git Bisect**: Runs non-interactive binary bisection (`git bisect run`) to automatically pinpoint the exact commit that introduced a failure.
- **Instruction**: [`skills/debugger/SKILL.md`](../skills/debugger/SKILL.md)

### 9. `security-auditor` (Skill)
Static Application Security Testing (SAST) and vulnerability scanner:
- **Injection Vector Scanning**: Detects SQL injection, command execution, SSRF, path traversal, and unsafe deserialization.
- **Secret & Key Auditing**: Scans diffs and repos for committed API tokens, private keys, AWS credentials, and `.env` leaks.
- **Primitive Sentinel**: Flags dangerous primitives (`eval()`, `exec()`, `dangerouslySetInnerHTML`, `pickle.loads()`).
- **Instruction**: [`skills/security-auditor/SKILL.md`](../skills/security-auditor/SKILL.md)

### 10. `database-engineer` (Skill)
Zero-downtime database migration safety and reversible DDL validator:
- **Reversibility Proof**: Enforces explicit rollback paths (`down.sql` / downgrade methods) for every migration.
- **Lock Contention Sentinel**: Catches dangerous table locks (`ACCESS EXCLUSIVE`), full-table rewrites, and unindexed foreign keys.
- **Concurrent Indexing**: Validates that indexes are created non-blockingly (`CREATE INDEX CONCURRENTLY` in Postgres).
- **Instruction**: [`skills/database-engineer/SKILL.md`](../skills/database-engineer/SKILL.md)

### 11. `container-engineer` (Skill)
Hardened production containerization and multi-stage Dockerfile scaffolding:
- **Multi-Stage Scaffolding**: Generates minimal distroless or non-root multi-stage Dockerfiles across languages.
- **Security & Caching Auditing**: Flags root user execution (`DOCKER-ROOT-USER`), unpinned `:latest` tags, baked secrets, and cache-busting `COPY . .` commands.
- **Instruction**: [`skills/container-engineer/SKILL.md`](../skills/container-engineer/SKILL.md)

### 12. `ci-workflow` (Skill)
CI/CD pipeline synthesizer and workflow security sentinel:
- **Pipeline Synthesis**: Scaffolds GitHub Actions workflows (`.github/workflows/ci.yml`) wired to test matrices, security checks, and context synchronizers.
- **Supply-Chain Auditing**: Scans workflows for unpinned `@main` actions, missing job timeouts, and overly permissive default tokens.
- **Instruction**: [`skills/ci-workflow/SKILL.md`](../skills/ci-workflow/SKILL.md)

### 13. `dependency-auditor` (Skill)
Multi-ecosystem dependency security scanner and manifest auditor:
- **Wildcard Detection**: Catches dangerous wildcard dependencies (`*`, `latest`) in Python, Node, Go, and Rust.
- **Hygiene & Deprecation**: Flags missing lockfiles, unpinned packages, and known deprecated libraries.
- **Instruction**: [`skills/dependency-auditor/SKILL.md`](../skills/dependency-auditor/SKILL.md)

### 14. `release-manager` (Skill)
Semantic versioning and Conventional Commits changelog manager:
- **SemVer Calculation**: Analyzes commit history since the last tag and recommends major, minor, or patch version bumps.
- **Changelog & Notes**: Automatically compiles `CHANGELOG.md` sections and drafts GitHub Release notes.
- **Instruction**: [`skills/release-manager/SKILL.md`](../skills/release-manager/SKILL.md)

### 15. `memory-manager` (Skill)
Scoped developer memory store and recall engine:
- **Structured Categories**: Organizes institutional knowledge into `patterns/`, `anti-patterns/`, `rules/`, and `decisions/`.
- **Indexed Search & Integrity**: Sub-millisecond keyword, tag, and content recall with SHA-256 integrity audits.
- **Multi-Tool Persistence**: Accessible across Claude Code, Cursor, Antigravity, Gemini CLI, and Windsurf without context rot.
- **Instruction**: [`skills/memory-manager/SKILL.md`](../skills/memory-manager/SKILL.md)

### 16. `dreamer` (Skill)
Anthropic-style out-of-band offline memory consolidation skill:
- **Autonomous Transcript Digestion**: Parses session logs (`SESSION_LOG.md`) and conversation execution transcripts offline without distracting from active coding.
- **Pattern & Trap Extraction**: Detects recurring error loops, failing tests that were resolved, and winning solution sequences.
- **Human-in-the-Loop Gate**: Produces structured memory proposals with supporting rationale for one-click approval or auto-promotion.
- **Instruction**: [`skills/dreamer/SKILL.md`](../skills/dreamer/SKILL.md)

### 17. `doc-sync` (Skill)
Documentation, schema, and filesystem drift sentinel:
- **Parity Sentinel**: Enforces SHA-256 parity between `skills/*/scripts/` and root `scripts/`.
- **Link Integrity**: Catches broken markdown references and file path citations in documentation.
- **Catalog Verification**: Guarantees all skills and subagents on disk are actively cataloged.
- **Instruction**: [`skills/doc-sync/SKILL.md`](../skills/doc-sync/SKILL.md)

### 18. `sys-admin` (Skill)
Cross-platform system administration, infrastructure security hardening, and Principal SRE incident triage:
- **Deep Host & Endpoint Triage (`--health`, `--triage-logs`, `--audit-host`)**: Collects CPU load, RAM, disk, POSIX **inodes**, failed services across Linux (`systemd`), macOS (`launchd`), and Windows (`scm`), listening sockets, top processes/zombies/FDs (`--processes`), condensed log alerts/clusters, SSH/shadow/umask posture, batch endpoint manifests (`--check-endpoints`), and read-only SSH triage (`--ssh`).
- **Transactional Config Apply & Drift Snapshots (`--apply-safe`, `--snapshot`, `--diff-snapshot`)**: Previews unified diffs (`--dry-run`), records SHA-256 receipts, runs pre-reload syntax validators with automatic rollback on failure, and diffs host posture snapshots to isolate configuration drift.
- **Hybrid Hardening Auditor (`--audit`, `--native-lint`)**: Scans `sshd_config`, `systemd`, Nginx, **Caddyfile**, **Kubernetes**, **Docker Compose**, **sudoers**, **firewall** rules, Bash/PowerShell ops scripts, cron, `sysctl`, Terraform, and Ansible playbooks, with inline `# sysadmin-ignore:` suppressions, `--baseline` diffing, and opportunistic native validator delegation (`shellcheck`/`bash -n`, `systemd-analyze`, `caddy`, `ansible-lint`, `tflint`).
- **Template Scaffolder (`--scaffold`)**: Generates hardened `systemd`, `nginx`, `backup` (`.sh`), `backup-ps1` (`.ps1`), `cron`, `sshd`, operational `runbook`, and blameless `postmortem` templates.
- **Instruction**: [`skills/sys-admin/SKILL.md`](../skills/sys-admin/SKILL.md)

---

## 🤖 Specialized Subagents

Subagents are isolated system personas defined in `.agents/agents/` (and exported to `.codex/agents/*.toml` for OpenAI Codex) that can be invoked via Google Antigravity, OpenAI Codex, Claude Code, Cursor, or Roo Code:

| Subagent | Role | Primary Focus |
| :--- | :--- | :--- |
| **`software_engineer`** | Tech Lead & Orchestrator | Surgical coding, multi-agent decomposition, peer-review gating, and Zero False Verification. |
| **`code_reviewer`** | Adversarial Auditor | Read-only inspection for error swallowing, race conditions, security traps, and scope churn. |
| **`test_engineer`** | Test Specialist | Deterministic automated test suites, mocks, parameterizations, and Red-Green proof. |
| **`system_architect`** | Architecture Specialist | Modular boundaries, interface contract design, schema models, and ADR formulation. |
| **`context_optimizer`** | Token Specialist | Token heatmap profiling, AST skeletonization, and repository compression packaging. |
| **`debugger`** | Root-Cause Specialist | Stack trace analysis, standalone reproduction harnesses (`repro.sh`), and automated git bisect. |
| **`security_auditor`** | AppSec Specialist | SAST vulnerability scanning, injection audits, and credential leak detection. |
| **`database_engineer`** | Database Specialist | Reversible migrations, table lock auditing, zero-downtime DDL safety, and index optimization. |
| **`devops_engineer`** | DevOps Specialist | Multi-stage Dockerfiles, GitHub Actions pipelines, dependency security, and release notes. |
| **`research`** | Research Specialist | Isolated API documentation reading, RFC exploration, and version-pinned snippet extraction. |
| **`sys_admin`** | SysAdmin & Principal SRE | USE/RED triage, log condensation, live posture & IaC/K8s/Caddy audits, safe apply w/ rollback & drift snapshots. |

---

## 🪝 Lifecycle Hooks & Auto-Formatters

Defined in [`hooks/hooks.json`](../hooks/hooks.json) for Google Antigravity:
* **`PreToolUse` Safety Guard (`guard_command.py`)**: Intercepts terminal commands before execution and blocks dangerous operations (e.g., `rm -rf /`, force pushes to `main`, disk overwrites).
* **`PostToolUse` Auto-Formatter (`auto_format.py`)**: Automatically detects modified files and runs the appropriate formatter (`ruff`, `prettier`, `gofmt`, `swiftformat`) without requiring human intervention.

---

## 🔌 Native MCP Suite

Pre-packaged Model Context Protocol servers configured in [`mcp/mcp_config.json`](../mcp/mcp_config.json):
* **Playwright**: Headless browser automation, visual regression testing, and live DOM tree inspection.
* **GitHub**: Remote CI/CD log inspection (`gh run view`), issue lookup, and PR review triage.
* **SQLite**: Local SQL inspection, schema queries, and query execution plan auditing.
