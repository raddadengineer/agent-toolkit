# ⚡ Agent Toolkit — Command-Line Interface (CLI) & Standalone Recipes

`agent-toolkit` provides a global launcher (`bin/atk` and `bin/atk.ps1`) as well as standalone Python script recipes that can be run from your terminal, integrated into CI pipelines, or triggered via git hooks.

---

## 📋 Table of Contents
- [Global CLI: `atk`](#-global-cli-atk)
- [Workflow & Orientation Recipes](#-workflow--orientation-recipes)
  - [Session Starter (`prime_session.py`)](#session-starter-prime_sessionpy)
  - [Session Closer & Context Sync (`sync_context.py`)](#session-closer--context-sync-sync_contextpy)
- [Memory & Learning Recipes](#-memory--learning-recipes)
  - [Memory Manager (`manage_memory.py`)](#memory-manager-manage_memorypy)
  - [Offline Dreamer (`dream_consolidator.py`)](#offline-dreamer-dream_consolidatorpy)
- [Optimization & Code Quality Recipes](#-optimization--code-quality-recipes)
  - [Context Optimizer (`compress_context.py`)](#context-optimizer-compress_contextpy)
  - [Adversarial Code Reviewer (`review_code.py`)](#adversarial-code-reviewer-review_codepy)
  - [Deterministic Test Scaffolder (`scaffold_tests.py`)](#deterministic-test-scaffolder-scaffold_testspy)
  - [PR Pre-Flight Auditor (`audit_pr.py`)](#pr-pre-flight-auditor-audit_prpy)
  - [Root-Cause Bisect Debugger (`bisect_debugger.py`)](#root-cause-bisect-debugger-bisect_debuggerpy)
- [Architecture & DevOps Recipes](#-architecture--devops-recipes)
  - [ADR Manager (`manage_adr.py`)](#adr-manager-manage_adrpy)
  - [Security SAST Scanner (`audit_security.py`)](#security-sast-scanner-audit_securitypy)
  - [Database Migration Validator (`verify_migrations.py`)](#database-migration-validator-verify_migrationspy)
  - [Container Hardener (`harden_docker.py`)](#container-hardener-harden_dockerpy)
  - [CI Pipeline Synthesizer (`synthesize_ci.py`)](#ci-pipeline-synthesizer-synthesize_cipy)
  - [Dependency Auditor (`audit_deps.py`)](#dependency-auditor-audit_depspy)
  - [Release Manager (`manage_release.py`)](#release-manager-manage_releasepy)
  - [Documentation Drift Sentinel (`check_doc_drift.py`)](#documentation-drift-sentinel-check_doc_driftpy)

---

## ⚡ Global CLI: `atk`

The `atk` launcher executes commands in any project directory without needing script paths:

```bash
# Core Lifecycle
atk start                       # Prime workspace, ingest handover notes & recall memory
atk close                       # Log completed session to SESSION_LOG.md and sync context
atk sync                        # Synchronize AGENTS.md, CLAUDE.md, and GEMINI.md
atk check                       # Verify SHA-256 parity across context files

# Memory & Dreaming
atk memory recall "<query>"     # Fast search across project & global memories
atk memory record --title "..." # Record a pattern, anti-pattern, rule, or decision
atk memory list                 # List all indexed memories
atk dream --analyze             # Run offline dreaming pass on transcripts & logs
atk dream --review              # Interactively review and approve candidate memories

# Optimization & Quality
atk profile                     # Profile repository token consumption across files
atk skeleton [file]             # Generate AST interface skeleton (85-95% token savings)
atk pack --budget 8000          # Pack repo into hybrid dense context map
atk review                      # Run adversarial code review on active diff
atk test-gen                    # Scaffold deterministic unit tests & boundary matrix
atk pr                          # Pre-flight diff audit & ready-to-copy PR description
atk debug                       # Stack trace analysis, repro script & git bisect

# Architecture & DevOps
atk adr new "Title"             # Create a new Architecture Decision Record
atk audit                       # SAST vulnerability and credential leak audit
atk db verify                   # Verify database migration safety & reversibility
atk docker audit                # Audit Dockerfiles for root execution & caching hazards
atk ci audit                    # Audit GitHub Actions workflows for security hazards
atk dep audit                   # Scan dependencies for wildcards & deprecations
atk release bump                # Calculate next SemVer bump from Conventional Commits
atk drift                       # Run documentation and schema drift sentinel
```

---

## 🧭 Workflow & Orientation Recipes

### Session Starter (`prime_session.py`)

```bash
# 1. View complete kickoff brief (branch status, sync status, previous handover, active memory):
python3 .agents/skills/session-starter/scripts/prime_session.py

# 2. Output only pending action items from the previous session:
python3 .agents/skills/session-starter/scripts/prime_session.py --handover-only

# 3. Output brief in structured JSON format:
python3 .agents/skills/session-starter/scripts/prime_session.py --json
```

### Session Closer & Context Sync (`sync_context.py`)

```bash
# 1. Verify all context files have identical SHA-256 hashes:
python3 .agents/skills/session-closer/scripts/sync_context.py --check

# 2. Sync all context files from the most recently modified:
python3 .agents/skills/session-closer/scripts/sync_context.py --sync

# 3. Initialize baseline context files and SESSION_LOG.md in a fresh repo:
python3 .agents/skills/session-closer/scripts/sync_context.py --init

# 4. Programmatically record a completed session entry:
python3 .agents/skills/session-closer/scripts/sync_context.py --log \
  --title "Implement user authentication" \
  --goal "Add OAuth2 and session token endpoints" \
  --change "Implemented POST /auth/login with bcrypt hashing" \
  --change "Added integration tests in tests/test_auth.py" \
  --validation "Ran 'pytest tests/test_auth.py' — all 12 tests passed (exit 0)" \
  --next-step "Implement password reset flow"

# 5. Record session entry and immediately trigger offline memory consolidation:
python3 .agents/skills/session-closer/scripts/sync_context.py --log --dream \
  --title "Database index optimization" \
  --goal "Optimize slow customer queries"
```

---

## 🧠 Memory & Learning Recipes

### Memory Manager (`manage_memory.py`)

```bash
# 1. Initialize persistent memory store:
python3 .agents/skills/memory-manager/scripts/manage_memory.py init

# 2. Recall memories by keyword, tag, or topic:
python3 .agents/skills/memory-manager/scripts/manage_memory.py recall "docker security"
python3 .agents/skills/memory-manager/scripts/manage_memory.py recall "import error" --category anti-patterns

# 3. Record a new pattern or rule:
python3 .agents/skills/memory-manager/scripts/manage_memory.py record \
  --category patterns \
  --title "Deterministic test isolation" \
  --content "Always use tempfile.TemporaryDirectory() context managers for file-based tests." \
  --tags "testing,fixtures,isolation"

# 4. Audit memory integrity and auto-repair checksum mismatches:
python3 .agents/skills/memory-manager/scripts/manage_memory.py audit --repair
```

### Offline Dreamer (`dream_consolidator.py`)

```bash
# 1. Analyze recent session logs and conversation transcripts offline:
python3 .agents/skills/dreamer/scripts/dream_consolidator.py --analyze

# 2. Interactively review candidates and save to memory:
python3 .agents/skills/dreamer/scripts/dream_consolidator.py --review

# 3. Auto-promote high-confidence candidates to repo memory:
python3 .agents/skills/dreamer/scripts/dream_consolidator.py --auto-promote

# 4. Export proposal to a Markdown report:
python3 .agents/skills/dreamer/scripts/dream_consolidator.py --output MEMORY_PROPOSAL.md
```

---

## ⚡ Optimization & Code Quality Recipes

### Context Optimizer (`compress_context.py`)

```bash
# 1. Profile repository token consumption across files:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --profile

# 2. Pack entire repository into an ultra-dense hybrid map under an 8,000 token budget:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --hybrid --budget 8000 --output REPO_MAP.md

# 3. Skeletonize a single large file (85-95% token savings):
python3 .agents/skills/context-optimizer/scripts/compress_context.py --file src/ComplexService.swift --skeleton

# 4. Generate pure AST skeleton representation for the entire repo:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --skeleton --output REPO_MAP.md

# 5. Output in XML format for LLM prompting:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --pack --format xml --budget 12000
```

### Adversarial Code Reviewer (`review_code.py`)

```bash
# 1. Audit active git diff against base branch (main):
python3 .agents/skills/code-reviewer/scripts/review_code.py --base main

# 2. Audit against HEAD:
python3 .agents/skills/code-reviewer/scripts/review_code.py

# 3. Output review report in JSON format:
python3 .agents/skills/code-reviewer/scripts/review_code.py --json
```

### Deterministic Test Scaffolder (`scaffold_tests.py`)

```bash
# 1. Scaffold deterministic test suite for a Python target:
python3 .agents/skills/test-engineer/scripts/scaffold_tests.py --file src/auth_service.py --lang python

# 2. Scaffold TypeScript test suite with boundary matrix:
python3 .agents/skills/test-engineer/scripts/scaffold_tests.py --file src/payment.ts --lang typescript
```

### PR Pre-Flight Auditor (`audit_pr.py`)

```bash
# 1. Audit diff for debug statements, secrets, and test proofs:
python3 .agents/skills/pr-prep/scripts/audit_pr.py --check

# 2. Generate a complete ready-to-copy Markdown PR description:
python3 .agents/skills/pr-prep/scripts/audit_pr.py --generate-desc --title "feat: user authentication"
```

### Root-Cause Bisect Debugger (`bisect_debugger.py`)

```bash
# 1. Deobfuscate raw stack trace log:
python3 .agents/skills/debugger/scripts/bisect_debugger.py --analyze-trace error.log

# 2. Generate standalone reproduction script:
python3 .agents/skills/debugger/scripts/bisect_debugger.py --repro "npm test" --output repro.sh

# 3. Run automated git bisect to isolate breaking commit:
python3 .agents/skills/debugger/scripts/bisect_debugger.py --bisect --test "./repro.sh" --good v1.0.0 --bad HEAD
```

---

## 📐 Architecture & DevOps Recipes

### ADR Manager (`manage_adr.py`)

```bash
# 1. Initialize ADR directory (docs/adr/):
python3 .agents/skills/system-architect/scripts/manage_adr.py --init

# 2. Create a new Architecture Decision Record:
python3 .agents/skills/system-architect/scripts/manage_adr.py --new "Adopt PostgreSQL Partitioning"

# 3. List and audit recorded ADRs:
python3 .agents/skills/system-architect/scripts/manage_adr.py --list
```

### Security SAST Scanner (`audit_security.py`)

```bash
# 1. Run SAST security and credential leak scan across workspace:
python3 .agents/skills/security-auditor/scripts/audit_security.py --dir .

# 2. Scan only staged diff before commit:
python3 .agents/skills/security-auditor/scripts/audit_security.py --staged
```

### Database Migration Validator (`verify_migrations.py`)

```bash
# 1. Verify migration reversibility and table locks:
python3 .agents/skills/database-engineer/scripts/verify_migrations.py --dir migrations/

# 2. Verify against a specific migration script:
python3 .agents/skills/database-engineer/scripts/verify_migrations.py --file migrations/003_add_index.sql
```

### Container Hardener (`harden_docker.py`)

```bash
# 1. Audit existing Dockerfile for non-root execution and caching hazards:
python3 .agents/skills/container-engineer/scripts/harden_docker.py --audit Dockerfile

# 2. Scaffold a hardened multi-stage Dockerfile:
python3 .agents/skills/container-engineer/scripts/harden_docker.py --scaffold python --output Dockerfile
```

### CI Pipeline Synthesizer (`synthesize_ci.py`)

```bash
# 1. Scaffold hardened GitHub Actions pipeline:
python3 .agents/skills/ci-workflow/scripts/synthesize_ci.py --scaffold python --output .github/workflows/ci.yml

# 2. Audit existing workflow for unpinned action hashes and permission hazards:
python3 .agents/skills/ci-workflow/scripts/synthesize_ci.py --audit .github/workflows/ci.yml
```

### Dependency Auditor (`audit_deps.py`)

```bash
# 1. Scan package manifests for wildcards and deprecations:
python3 .agents/skills/dependency-auditor/scripts/audit_deps.py --check

# 2. Output audit findings in JSON:
python3 .agents/skills/dependency-auditor/scripts/audit_deps.py --json
```

### Release Manager (`manage_release.py`)

```bash
# 1. Calculate next SemVer bump from Conventional Commits:
python3 .agents/skills/release-manager/scripts/manage_release.py --bump

# 2. Generate CHANGELOG.md update and GitHub release notes:
python3 .agents/skills/release-manager/scripts/manage_release.py --changelog
python3 .agents/skills/release-manager/scripts/manage_release.py --notes
```

### Documentation Drift Sentinel (`check_doc_drift.py`)

```bash
# 1. Verify that documented skills and agents match filesystem reality:
python3 .agents/skills/doc-sync/scripts/check_doc_drift.py --check

# 2. Synchronize scripts between skills/*/scripts/ and scripts/:
python3 .agents/skills/doc-sync/scripts/check_doc_drift.py --sync-scripts
```
