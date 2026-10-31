# agent-toolkit — Agent Guidelines & Project Context

Welcome to `agent-toolkit`, a centralized library of reusable skills, specialized subagents, and automated developer workflows across multiple AI coding assistants.

## 🏗️ Technology Stack & Environment
- **Runtime & Language**: Python 3.10+, Bash shell (`set -euo pipefail`).
- **AI Tool Ecosystem**: Google Antigravity & Gemini CLI (`agy`), Claude Code, Cursor 2.0 (MDC), GitHub Copilot, Roo Code / Cline, Windsurf.
- **Testing**: Python standard library `unittest` (`python3 -m unittest discover -s tests`).
- **Sentinels & Guards**: AST-based drift sentinel (`skills/doc-sync/scripts/check_doc_drift.py`), pre-tool safety guards (`scripts/guard_command.py`), post-tool auto-formatters (`scripts/auto_format.py`).

## 📂 Project Structure
- `skills/`: Progressive disclosure skills containing `SKILL.md` instructions and dedicated automation scripts.
  - `session-starter/`: Orientation workflow, branch hygiene checks, and handover note ingestion.
  - `session-closer/`: Handover workflow, context file synchronizer, and session ledger manager.
  - `context-optimizer/`: Token heatmap profiler and AST code skeletonizer (85–95% token savings).
  - `pr-prep/`: Pre-flight git diff auditor (secrets/debug logs) and PR markdown generator.
  - `code-reviewer/`: Adversarial diff auditor, error swallowing detector, and structured review verdicts.
  - `test-engineer/`: Deterministic test suite scaffolder, boundary coverage matrices, and mock fixtures.
  - `system-architect/`: Architecture Decision Record (ADR) manager, interface contracts, and boundary sentinel.
  - `debugger/`: Standalone reproduction harnesses (`repro.sh`) and automated git bisection.
  - `security-auditor/`: SAST vulnerability scanning and dependency hazard auditor.
  - `database-engineer/`: Reversible migration proof and zero-downtime DDL safety validator.
  - `container-engineer/`: Multi-stage Dockerfile scaffolding and security/caching linter.
  - `ci-workflow/`: Pipeline synthesizer (GitHub Actions) and workflow security auditor.
  - `dependency-auditor/`: Multi-ecosystem manifest auditor for wildcards and deprecations.
  - `release-manager/`: Semantic versioning calculator and Conventional Commits changelog generator.
  - `doc-sync/`: Filesystem vs documentation drift and broken link sentinel.
- `agents/`: Specialized subagent system prompts, persona configurations, and capability definitions.
- `scripts/`: Multi-tool configuration compilers (`export_adapters.py`), context compressors, hooks, and validators.
- `hooks/`: PreToolUse and PostToolUse lifecycle hook definitions (`hooks.json`).
- `mcp/`: Native Model Context Protocol server configurations (`mcp_config.json`).
- `tests/`: Deterministic unit tests validating synchronizers, compilers, compressors, and sentinels.
- `bin/`: Global CLI entry point launchers (`bin/atk`, `bin/atk.ps1`) for cross-project execution.
- `install.sh` / `install.ps1`: Multi-tool installers and symlink managers supporting Bash and PowerShell with direct web install (`curl` / `irm`), global linking (`--global`), and distribution modes (`--mode symlink` and `--mode copy`).

## 📜 Core Mandates & Engineering Discipline
- **Conventions over preferences**: Strictly adhere to established repository structures and naming patterns.
- **Evidence over assumption**: Base all diagnoses and claims on actual compiler traces, exit codes, and test outputs.
- **Zero false verification**: Never claim a test, build, or check passed without executing the command and verifying an exit code of `0`.
- **Session continuity**: Always begin with `session-starter` (reading `SESSION_LOG.md`) and conclude with `session-closer` (updating `SESSION_LOG.md` and keeping context files bit-for-bit identical via SHA-256).
