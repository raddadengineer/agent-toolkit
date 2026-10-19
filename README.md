# 🛠️ Agent Toolkit

A centralized, reusable library of high-leverage skills, specialized subagents, and automated developer workflows for AI pair programming assistants (**Google Antigravity**, **Gemini CLI**, **Claude Code**, **Cursor**, **GitHub Copilot**, and **Roo Code / Cline**).

Instead of recreating session scripts, agent definitions, and context rules across separate repositories, `agent-toolkit` provides a single source of truth that maintains project continuity, enforces engineering discipline, minimizes token consumption, and eliminates repetitive context synchronization.

---

## 📂 Repository Structure

```
agent-toolkit/
├── README.md                          # Documentation and comprehensive usage guide
├── bin/
│   └── atk                            # Global CLI launcher (symlinked to ~/.local/bin/atk)
├── install.sh                         # Multi-tool installer and symlink manager
├── skills/
│   ├── context-optimizer/             # Token optimization & AST context compression skill
│   │   ├── SKILL.md                   # Token profiling & skeletonization workflow
│   │   └── scripts/
│   │       └── compress_context.py    # Multi-language AST skeletonizer & context packer
│   ├── session-starter/               # Universal session kickoff & orientation skill
│   │   ├── SKILL.md                   # Orientation workflow & handover ingest
│   │   └── scripts/
│   │       └── prime_session.py       # Ledger reader & branch/context health auditor
│   ├── session-closer/                # Universal session conclusion & handover skill
│   │   ├── SKILL.md                   # Handover workflow & ledger prepender
│   │   └── scripts/
│   │       └── sync_context.py        # Multi-file context synchronizer & session ledger
│   ├── pr-prep/                       # Pre-flight PR auditor & description generator
│   │   ├── SKILL.md                   # PR preparation & sanitization workflow
│   │   └── scripts/
│   │       └── audit_pr.py            # Diff auditor (secrets, debug logs) & markdown generator
│   ├── debugger/                      # Stack trace analysis & automated git bisect skill
│   │   ├── SKILL.md                   # Root-cause investigation & repro workflow
│   │   └── scripts/
│   │       └── bisect_debugger.py     # Minimal reproduction harness & git bisect engine
│   ├── security-auditor/              # SAST code scanner & CVE dependency auditor skill
│   │   ├── SKILL.md                   # Pre-flight security & secret audit workflow
│   │   └── scripts/
│   │       └── audit_security.py      # AST vulnerability & credential leak scanner
│   ├── database-engineer/             # Reversible migration & zero-downtime schema skill
│   │   ├── SKILL.md                   # Migration safety & lock contention workflow
│   │   └── scripts/
│   │       └── verify_migrations.py   # DDL rollback proof & lock hazard validator
│   └── doc-sync/                      # Documentation & schema drift sentinel skill
│       ├── SKILL.md                   # Drift detection & link verification workflow
│       └── scripts/
│           └── check_doc_drift.py     # Filesystem vs README drift sentinel
├── scripts/
│   ├── compress_context.py            # Universal token optimizer & context packer
│   └── export_adapters.py             # Multi-tool AI assistant configuration compiler
├── agents/
│   ├── software_engineer/             # Tech Lead orchestrator & surgical engineering subagent
│   ├── code_reviewer/                 # Adversarial read-only senior code review subagent
│   ├── test_engineer/                 # Deterministic test automation & Red-Green proof subagent
│   ├── system_architect/              # High-level architecture, contracts & ADR subagent
│   ├── context_optimizer/             # Token profiling & AST skeleton compression subagent
│   ├── debugger/                      # Minimal reproduction (repro.sh) & git bisect subagent
│   ├── security_auditor/              # AppSec SAST scanner & credential leak subagent
│   └── database_engineer/             # Zero-downtime migration & lock contention subagent
├── hooks/
│   └── hooks.json                     # Antigravity PreToolUse safety guards & PostToolUse formatters
├── mcp/
│   └── mcp_config.json                # Native MCP suite: Playwright, GitHub, SQLite
└── tests/
    ├── test_atk_cli.py                # Unit tests for bin/atk global CLI
    ├── test_sync_context.py           # Unit tests for sync_context.py
    ├── test_prime_session.py          # Unit tests for prime_session.py
    ├── test_audit_pr.py               # Unit tests for audit_pr.py
    ├── test_export_adapters.py        # Unit tests for export_adapters.py
    ├── test_compress_context.py       # Unit tests for compress_context.py
    ├── test_bisect_debugger.py        # Unit tests for bisect_debugger.py
    ├── test_audit_security.py         # Unit tests for audit_security.py
    ├── test_verify_migrations.py      # Unit tests for verify_migrations.py
    └── test_check_doc_drift.py        # Unit tests for check_doc_drift.py
```

---

## 📖 How to Actually Use the Tools, Skills & Agents

Once you install `agent-toolkit` into your project (via `./install.sh --target ~/my-project --tool all`), here is how you interact with everything across your daily development loop.

### 🔄 The End-to-End Daily Workflow Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. 🌅 KICK OFF: Orient & read handover notes (/session-starter)              │
│ 2. ⚡ OPTIMIZE: Build 90% compressed AST repo map (compress_context.py)       │
│ 3. 🛠️ IMPLEMENT: Surgical coding & zero false verification (software_engineer)│
│ 4. 🛡️ AUDIT: Adversarial read-only code review (code_reviewer / /code-review) │
│ 5. 🚀 PRE-FLIGHT: Diff leak audit & PR description generator (/pr-prep)       │
│ 6. 🌙 WRAP UP: Record accomplishments & sync context files (/session-closer) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 1. In AI Chat Sessions (By Assistant)

Depending on which AI assistant you use, here is how to invoke the skills and agents:

#### A. Google Antigravity & Gemini CLI (`agy`)
Skills are loaded automatically via **progressive disclosure** from `.agents/skills/`, and subagents are defined in `.agents/agents/`:
* **Kick off a session**: Type `"Prime the workspace and orient me on previous handover items."` (triggers `session-starter`).
* **Optimize context**: Type `"Profile the repo token footprint and skeletonize the services."` (triggers `context-optimizer`).
* **Surgical coding**: Type `"Invoke software_engineer subagent to implement the Stripe webhook handler."` (triggers `software_engineer`).
* **Code review**: Type `"Have code_reviewer audit the uncommitted diff for concurrency and security issues."` (triggers `code_reviewer`).
* **Pre-flight PR**: Type `"Run pr-prep to audit the diff and draft the pull request description."` (triggers `pr-prep`).
* **Close the session**: Type `"Wrap up this session, record our progress in SESSION_LOG.md, and sync context files."` (triggers `session-closer`).

#### B. Claude Code (Anthropic CLI)
The toolkit exports native markdown slash commands to `.claude/commands/`:
* `/session-starter`: Ingests `SESSION_LOG.md`, verifies git branch, and establishes a clean baseline.
* `/compress-context`: Profiles token consumption and generates an AST skeleton map.
* `/code-review`: Adopts the read-only adversarial reviewer persona to audit the diff.
* `/pr-prep`: Scans diff for secrets and debug statements, verifies tests, and outputs a ready-to-copy PR.
* `/session-closer`: Prepens a structured ledger entry to `SESSION_LOG.md` and synchronizes `AGENTS.md` & `CLAUDE.md`.

#### C. Cursor
The toolkit exports Cursor 2.0 MDC rules to `.cursor/rules/`:
* **Always-On Discipline**: `engineering-standards.mdc` automatically enforces surgical modifications and zero false verification in every interaction.
* **On-Demand Skills**: In Cursor Chat / Composer, reference the rules directly:
  * `@session-workflows.mdc`: *"Run the session start procedure"* or *"Wrap up this session"*.
  * `@code-reviewer.mdc`: *"Review my recent changes in this branch against our review standards"*.
  * `@context-optimizer.mdc`: *"Generate an AST skeleton map for this repository"*.
  * `@pr-prep.mdc`: *"Audit my changes and write a pull request description"*.

#### D. GitHub Copilot (VS Code / JetBrains)
The toolkit exports prompt templates to `.github/prompts/` and repo rules to `.github/copilot-instructions.md`:
* Type `/session-starter` in Copilot Chat to ingest handover notes.
* Type `/compress-context` to summarize codebase architecture with minimal tokens.
* Type `/code-review` to inspect the active diff for concurrency and security edge cases.
* Type `/pr-prep` to prepare pull request documentation.
* Type `/session-closer` to update `SESSION_LOG.md`.

#### E. Roo Code / Cline / OpenCode
The toolkit exports custom multi-agent modes to `.roomodes` and `.clinerules`:
* **Senior Software Engineer mode**: Select from the mode dropdown for active feature implementation and test running (`read`, `edit`, `command` permissions).
* **Code Reviewer mode**: Select from the mode dropdown for safe, read-only code audits (`read`, `command` permissions only—cannot accidentally mutate code).

---

### 2. Standalone Terminal CLI Recipes

All core engines can also be run directly from your terminal or integrated into CI/CD and git hooks:

#### ⚡ Token Optimizer & Context Compressor (`compress_context.py`)
```bash
# 1. Profile repository token consumption (see where tokens are burned):
python3 .agents/skills/context-optimizer/scripts/compress_context.py --profile

# 2. Pack entire repository into an ultra-dense hybrid map under an 8,000 token budget:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --hybrid --budget 8000 --output REPO_MAP.md

# 3. Skeletonize a single large file to inspect its API without full bodies (85-95% token savings):
python3 .agents/skills/context-optimizer/scripts/compress_context.py --file src/ComplexService.swift --skeleton

# 4. Generate pure AST skeleton representation for the entire repo:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --skeleton --output REPO_MAP.md

# 5. Output in XML format for LLM prompting:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --pack --format xml --budget 12000
```

#### 🧭 Session Starter (`prime_session.py`)
```bash
# 1. View complete session kickoff brief (branch status, sync status, previous handover):
python3 .agents/skills/session-starter/scripts/prime_session.py

# 2. Output only pending action items from the previous session:
python3 .agents/skills/session-starter/scripts/prime_session.py --handover-only

# 3. Output brief in structured JSON (for script integration):
python3 .agents/skills/session-starter/scripts/prime_session.py --json
```

#### 🔄 Context Sync & Session Ledger (`sync_context.py`)
```bash
# 1. Verify all context files (AGENTS.md, CLAUDE.md, GEMINI.md) have identical SHA-256 hashes:
python3 .agents/skills/session-closer/scripts/sync_context.py --check

# 2. Sync all context files from the most recently modified (or specify source file):
python3 .agents/skills/session-closer/scripts/sync_context.py --sync
python3 .agents/skills/session-closer/scripts/sync_context.py --sync AGENTS.md

# 3. Check status and checksums of tracked files:
python3 .agents/skills/session-closer/scripts/sync_context.py --status

# 4. Initialize baseline context files and SESSION_LOG.md in a fresh repository:
python3 .agents/skills/session-closer/scripts/sync_context.py --init

# 5. Programmatically record a completed session entry:
python3 .agents/skills/session-closer/scripts/sync_context.py --log \
  --title "Payment Gateway Integration" \
  --goal "Add Stripe webhook verification" \
  --change "Implemented WebhookHandler.swift" \
  --change "Added signature verification unit tests" \
  --validation "All 24 unit tests passed (exit 0)" \
  --next-step "Configure webhook endpoint in Stripe dashboard"
```

#### 🚀 PR Pre-Flight Auditor (`audit_pr.py`)
```bash
# 1. Audit current diff against base branch (fails with exit code 1 if debug prints or secrets are found):
python3 .agents/skills/pr-prep/scripts/audit_pr.py --check

# 2. Audit against a specific base branch (e.g. main or staging):
python3 .agents/skills/pr-prep/scripts/audit_pr.py --base main --check

# 3. Generate a complete, ready-to-copy Markdown PR description:
python3 .agents/skills/pr-prep/scripts/audit_pr.py --generate-desc --title "feat: user authentication"

# 4. Output audit results in JSON format:
python3 .agents/skills/pr-prep/scripts/audit_pr.py --json
```

---

## 🧰 Detailed Component Reference

### 1. ⚡ `context-optimizer` (Skill)
Compresses codebase context and minimizes token consumption by **85–95%**:
- **Multi-Language AST Skeletonizer**: Extracts classes, interfaces, method signatures, types, and docstrings while stripping implementation bodies (`Python`, `TypeScript/JavaScript`, `Swift`, `Go`, `Rust`).
- **Token Heatmap Profiler**: Analyzes token footprint across directories and flags oversized files or accidental lockfile/bundle bloat.
- **Repository Context Packer**: Bundles projects into high-density Markdown or XML prompts under configurable token budgets (e.g. `--budget 8000`).
- **Hybrid Mode**: Retains full content for key entry points (`README.md`, package manifests) while skeletonizing all underlying code.

### 2. 🧭 `session-starter` (Skill)
The orientation bookend to `session-closer`. Ingests handover notes from the previous session, checks git branch health, verifies context synchronization, and establishes a clean baseline before touching code.

### 3. 🔄 `session-closer` (Skill)
Guides AI agents through a disciplined 5-step handover procedure at the end of a coding session:
1. **Analyze Accomplishments**: Scans `git status --short` and `git diff --stat`.
2. **Record in `SESSION_LOG.md`**: Prepends a clean, dated markdown entry documenting the session goal, specific changes, validation proof, and next steps.
3. **Synchronize Context Files**: Keeps `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` bit-for-bit identical via SHA-256 checks.
4. **Verify Build & Tests**: Runs ecosystem-specific test commands under a strict **Zero False Verification** policy.
5. **Deliver Handover Summary**: Provides an executive report summarizing completed work and immediate next actions.

### 4. 🚀 `pr-prep` (Skill)
Pre-flight pull request audit and description authoring:
- **Diff & Leak Audit**: Scans diffs for forgotten `console.log`, `print()`, `debugger`, and hardcoded secrets/API keys.
- **Build & Test Verification**: Guarantees test pass receipts before PR opening.
- **Generate PR Markdown**: Creates ready-to-copy PR summaries complete with test receipts and verification checklists.

### 5. 👨‍💻 `software_engineer` (Subagent & Tech Lead)
A surgical, senior staff software engineer and Tech Lead orchestrator:
- **Evidence over assumption**: Bases all diagnoses on compiler traces, test logs, and actual source code.
- **Conventions over preferences**: Strictly adopts host repository conventions rather than imposing external paradigms.
- **Zero false verification**: Refuses to claim a test or build succeeded without an exit code `0`.
- **Swarm Orchestration**: Leverages `invoke_subagent`, `define_subagent`, and `manage_subagents` to delegate isolated workstreams to `test_engineer`, `system_architect`, and `research`.
- **Peer-Review Gate**: Automatically audits diffs via `code_reviewer` before completing multi-component work.
- **Orchestrated Lifecycle**: `Analyze ──> Delegate/Research ──> Concurrent Dev & Tests ──> Peer Review Gate ──> Validate (Exit 0) ──> Report`.

### 6. 🛡️ `code_reviewer` (Subagent)
An adversarial, read-only senior code review persona:
- **Read-only mandate**: Focuses purely on analysis, critique, and security without direct edits.
- **5 Review Dimensions**: Security & Secrets, Concurrency & Thread Safety, Error Handling & Swallowing, Architecture & Scope, and Test Quality.
- **Structured Output**: Delivers actionable verdicts (`APPROVE`, `REQUEST CHANGES`, `COMMENT`) with severity ratings (`CRITICAL`, `WARNING`, `NIT`).

### 7. 🧪 `test_engineer` (Subagent)
A specialized quality and test automation subagent:
- **Flake-free determinism**: Employs condition-based polling and strict state isolation; bans arbitrary sleeps.
- **Red-Green verification**: Proves bug reproduction by verifying tests fail before the fix and pass cleanly after.
- **Comprehensive coverage**: Focuses on boundary conditions, malformed payloads, concurrent contention, and mocking at system boundaries.

### 8. 📐 `system_architect` (Subagent)
A principal systems architecture and technical planning subagent:
- **Read-only design posture**: Inspects dependency structures, module interfaces, and data models without premature code edits.
- **Contract & schema design**: Formulates strongly-typed schemas, interface boundaries, and backwards-compatible migrations.
- **Architectural Decision Records (ADRs)**: Documents problem statements, evaluated alternatives, and trade-off rationales.

### 9. ⚡ `context_optimizer` (Subagent & Skill)
A specialized token optimization and AST context compression subagent:
- **Token Profiling**: Profiles repository-wide token consumption and flags oversized bloat or accidental fixtures.
- **AST Skeleton Extraction**: Extracts class and method signatures for Python, TypeScript, Swift, Go, and Rust with 85–95% token savings.
- **Repo Map Packaging**: Packs multi-module projects into high-density Markdown/XML prompts (`REPO_MAP.md`) under strict token budgets.

### 10. 🔬 `debugger` (Subagent & Skill)
A root-cause investigation and regression bisection subagent:
- **Reproduction First**: Authors standalone reproduction harnesses (`repro.sh` / `repro.py`) that exit `1` on failure before touching production code.
- **Automated Git Bisect**: Runs binary search across commit history with an automated test command to isolate the exact breaking commit.
- **Stack Trace Deobfuscator**: Pinpoints originating call site from Python, JS/TS, Swift, and Go stack traces.

### 11. 🛡️ `security_auditor` (Subagent & Skill)
An application security (AppSec) and static analysis subagent:
- **SAST Scanner**: Flags SQL injection, command execution (`shell=True`, `eval`), and unsafe deserialization.
- **Secret & Key Hygiene**: Scans for leaked AWS keys, GitHub tokens, and private key blocks.
- **Dependency Audit**: Inspects package manifests (`package.json`, `requirements.txt`, `Cargo.toml`) for known CVE hazards.

### 12. 🗄️ `database_engineer` (Subagent & Skill)
A database reliability and zero-downtime schema subagent:
- **Reversibility Proof**: Enforces that every forward migration has an active, tested downgrade/rollback counterpart.
- **Lock Contention Prevention**: Blocks dangerous DDL anti-patterns like `ADD COLUMN NOT NULL` without `DEFAULT` and synchronous index creation.
- **Query Plan Optimization**: Guides `EXPLAIN ANALYZE` reviews for hot path database queries.

### 13. 📖 `doc-sync` (Skill)
A documentation and schema drift sentinel:
- **Drift Detection**: Verifies that documented skills, subagents, and slash commands match actual disk contents.
- **Broken Link Verification**: Flags broken internal markdown links across repository guides.

### 14. 🪝 Lifecycle Hooks & Auto-Formatters (`hooks.json`)
Native Antigravity lifecycle hooks:
- **`PreToolUse` Safety Guard**: Inspects shell commands before execution and blocks destructive actions (`rm -rf /`, force pushes to `main`, disk overwrites).
- **`PostToolUse` Auto-Formatter**: Runs language formatters (`ruff`, `prettier`, `swiftformat`, `gofmt`) automatically on modified files.

### 15. 🔌 Native MCP Suite (`mcp_config.json`)
Pre-packaged Model Context Protocol servers:
- **Playwright**: Headless browser automation, visual inspection, and live DOM testing.
- **GitHub**: Remote CI/CD log inspection (`gh run view`), issue lookup, and PR review triage.
- **SQLite**: Local SQL inspection and execution plan auditing.

---

## 🌐 Multi-Tool AI Ecosystem Support

`agent-toolkit` acts as the single source of truth across all major AI coding assistants. Use `./install.sh --tool <name>` to export native configurations:

| Tool | Export Path | Native Integration |
| :--- | :--- | :--- |
| **Claude Code** | `.claude/commands/`<br>`CLAUDE.md` | Interactive slash commands: `/session-starter`, `/session-closer`, `/pr-prep`, `/code-review`, `/compress-context` |
| **Cursor** | `.cursor/rules/*.mdc`<br>`.cursorrules` | Cursor 2.0 MDC rules with trigger conditions and engineering standards |
| **GitHub Copilot** | `.github/copilot-instructions.md`<br>`.github/prompts/` | Global repo instructions and reusable `.prompt.md` templates |
| **Roo Code / Cline** | `.roomodes`<br>`.clinerules` | Multi-agent JSON personas (`software-engineer`, `code-reviewer`) and rules |
| **Windsurf** | `.windsurfrules` | Cascade rules for surgical modifications and session continuity |
| **Antigravity / Gemini CLI** | `.agents/skills/`<br>`.agents/agents/` | Native skill progressive disclosure and subagent execution |

---

## 🚀 Quick Start & Installation

### ❓ How Installation Works (Do I copy the repository files?)

> [!IMPORTANT]
> **Do NOT copy this entire repository into your project.**
> `agent-toolkit` is designed to be cloned **once** into a central location on your machine (e.g., `~/Dev-Projects/agent-toolkit` or `~/.agent-toolkit`).
>
> You run `install.sh` from the toolkit pointing to your target project (`--target /path/to/my-project`), or run the script directly from inside your project. The installer then generates or symlinks *only* the specific configuration folders and agent skills needed by your chosen AI assistant(s) into your project.

```
┌──────────────────────────────────────────────┐
│  Central Toolkit (~/agent-toolkit)           │
│  ├── install.sh                              │
│  ├── skills/                                 │
│  ├── agents/                                 │
│  └── scripts/                                │
└──────────────────────┬───────────────────────┘
                       │
       ./install.sh --target ~/my-app --tool all
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Target Project (~/my-app)                   │
│  ├── .agents/skills/    (Antigravity/Gemini) │
│  ├── .claude/commands/  (Claude Code)        │
│  ├── .cursor/rules/     (Cursor MDC)         │
│  ├── .github/prompts/   (Copilot)            │
│  ├── .roomodes          (Roo / Cline)        │
│  ├── .windsurfrules     (Windsurf)           │
│  └── SESSION_LOG.md     (Session Ledger)     │
└──────────────────────────────────────────────┘
```

---

### 📦 Installation Modes: Symlink vs. Copy

`install.sh` supports two distribution modes via `--mode <symlink|copy>`:

| Mode | Flag | How It Works | Best For |
| :--- | :--- | :--- | :--- |
| **Symlink** *(Default)* | `--mode symlink` | Creates symbolic links from your project back to your central `agent-toolkit` directory. | **Solo / Local Dev**: When you run `git pull` in `agent-toolkit`, all your projects immediately get the latest skills and agents without re-installing. |
| **Copy / Standalone** | `--mode copy` | Copies the physical files and scripts directly into your target project directory. | **Team Repos & CI/CD**: The target repository is 100% self-contained. Teammates and CI runners do not need `agent-toolkit` cloned on their machines. |

---

### 🛠️ Step-by-Step Installation Guide

#### Step 1: Clone `agent-toolkit` & Enable Global CLI
Clone this repository once to a central tools or development folder on your machine:
```bash
git clone https://github.com/raddadengineer/agent-toolkit.git ~/Dev-Projects/agent-toolkit
cd ~/Dev-Projects/agent-toolkit

# Enable global 'atk' CLI launcher into ~/.local/bin (Recommended):
./install.sh --global
```

#### Step 2: Install into Your Target Project

You can run the installer using any of the following approaches:

**Approach A: Using the Global `atk` CLI (Fastest):**
```bash
cd ~/Dev-Projects/my-app

# Configure all AI tools at once (symlinks for local dev):
atk install

# Or copy physical files for a self-contained team repository:
atk install --mode copy
```

**Approach B: From the `agent-toolkit` directory (Specifying `--target`):**
```bash
cd ~/Dev-Projects/agent-toolkit

# Configure all AI tools at once with symlinks:
./install.sh --target ~/Dev-Projects/my-app --tool all

# Or copy physical files:
./install.sh --target ~/Dev-Projects/my-app --tool all --mode copy
```

**Approach C: From inside your target project directory:**
```bash
cd ~/Dev-Projects/my-app

# Run the installer directly pointing to your central toolkit location:
~/Dev-Projects/agent-toolkit/install.sh --tool all
```

---

### 🎯 Assistant-Specific Installation Recipes

If you only use a specific AI assistant, you can install just its configuration:

```bash
# 1. Claude Code (.claude/commands/, CLAUDE.md):
./install.sh --target ~/Dev-Projects/my-app --tool claude
# (or 'atk install --tool claude' from inside my-app)

# 2. Cursor (.cursor/rules/*.mdc, .cursorrules):
./install.sh --target ~/Dev-Projects/my-app --tool cursor
# (or 'atk install --tool cursor' from inside my-app)

# 3. GitHub Copilot (.github/copilot-instructions.md, .github/prompts/):
./install.sh --target ~/Dev-Projects/my-app --tool copilot

# 4. Roo Code / Cline (.roomodes, .clinerules):
./install.sh --target ~/Dev-Projects/my-app --tool roo

# 5. Windsurf (.windsurfrules):
./install.sh --target ~/Dev-Projects/my-app --tool windsurf

# 6. Google Antigravity & Gemini CLI (.agents/, AGENTS.md, GEMINI.md):
./install.sh --target ~/Dev-Projects/my-app --tool antigravity
# (or ./install.sh --target ~/Dev-Projects/my-app --all)

# 7. Global CLI & Repo Update Utilities:
./install.sh --global       # Symlink 'atk' into ~/.local/bin
./install.sh --update       # Pull latest toolkit updates from origin main
```

To inspect all available skills, subagents, and supported assistants:
```bash
./install.sh --list
```

---

### ⚡ Global Terminal CLI: `atk`

`agent-toolkit` includes a unified global CLI launcher (`bin/atk`) that makes all skills, auditors, and installers accessible from **any** directory in your terminal without typing repository paths.

#### 1. Enable Global Access (One-time setup):
```bash
cd ~/Dev-Projects/agent-toolkit
./bin/atk link
```
*(This symlinks `atk` and `agent-toolkit` directly into `~/.local/bin`, which is typically in your `$PATH`.)*

#### 2. Run Commands in Any Project:
```bash
cd ~/Dev-Projects/my-app

# Install all AI assistant configs into the current directory:
atk install

# Or install for a specific tool:
atk install --tool cursor
atk install --mode copy

# Daily development workflow shortcuts:
atk start        # Prime workspace and ingest recent handover notes
atk profile      # Analyze token hotspots across files
atk audit        # Scan diff and codebase for security/credential leaks
atk pr           # Audit diff and generate ready-to-copy PR description
atk sync         # Synchronize AGENTS.md, CLAUDE.md, and GEMINI.md
atk close        # Wrap up session and record in SESSION_LOG.md
```

> [!NOTE]
> **AI Agent Compatibility**: Enabling `atk` does **not** alter how AI coding assistants work. Inside chat interfaces, agents in Antigravity, Claude Code, Cursor, Copilot, and Roo continue discovering skills, rules, and subagents natively. In addition, agents can now run `atk` directly when executing bash commands without searching for script paths.

---

### 🏁 Step 3: Initialize Session Ledger & Context Baseline

After running `install.sh`, navigate to your target project and initialize your `SESSION_LOG.md` and baseline context files:

```bash
cd ~/Dev-Projects/my-app

# Initializes SESSION_LOG.md and synchronizes AGENTS.md, CLAUDE.md, and GEMINI.md:
python3 .agents/skills/session-closer/scripts/sync_context.py --init
```

> [!TIP]
> If your project already has an `AGENTS.md` or `CLAUDE.md`, `sync_context.py --init` preserves your existing guidelines and synchronizes them across all context files via SHA-256 validation.

---

### 🔄 Updating `agent-toolkit` Across Projects

You can update `agent-toolkit` at any time:

#### Option 1: Using the Global CLI (Fastest):
```bash
# In your target project (or anywhere):
atk update
```
*(This pulls the latest commits from `origin main` and automatically refreshes exported configurations if run inside a configured project).*

#### Option 2: Using the Installer Script:
```bash
cd ~/Dev-Projects/agent-toolkit
./install.sh --update
```

#### Manual Update by Mode:
- **If you installed with `--mode symlink` (default):**
  Pull the latest changes in your central `agent-toolkit` repository:
  ```bash
  cd ~/Dev-Projects/agent-toolkit
  git pull origin main
  ```
  All linked projects immediately inherit updated skills, subagents, and hooks without needing re-installation.

- **If you installed with `--mode copy`:**
  Pull updates in the central toolkit, then re-run the installer targeting your project:
  ```bash
  cd ~/Dev-Projects/agent-toolkit
  git pull origin main
  ./install.sh --target ~/Dev-Projects/my-app --tool all --mode copy
  ```

---

### 👥 Team Repositories & Git Hygiene

When sharing a project repository with a team:
- **Using `--mode copy` (Team Setup)**: Commit the generated `.agents/`, `.cursor/`, `.claude/`, `.github/`, and `SESSION_LOG.md` files to version control so all team members and AI assistants share identical standards.
- **Using `--mode symlink` (Personal Local Setup)**: If teammates do not use `agent-toolkit`, you can add `.agents/`, `.claude/`, and `.roomodes` to your repository's `.gitignore` or global `~/.gitignore_global`.

---

## 🧪 Running Tests

Verify the entire toolkit's synchronizers, auditors, adapters, and logging engines:
```bash
python3 -m unittest discover -s tests
```

---

## 📄 License
MIT License. Free to use across personal and professional projects.
