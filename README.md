# 🛠️ Agent Toolkit

A centralized, reusable library of high-leverage skills, specialized subagents, and automated developer workflows for AI pair programming assistants (**Google Antigravity**, **Gemini CLI**, **Claude Code**, **Cursor**, **GitHub Copilot**, and **Roo Code / Cline**).

Instead of recreating session scripts, agent definitions, and context rules across separate repositories, `agent-toolkit` provides a single source of truth that maintains project continuity, enforces engineering discipline, minimizes token consumption, and eliminates repetitive context synchronization.

---

## ⚡ 1-Command Quick Start

Install `agent-toolkit` globally and configure the unified `atk` CLI:

**macOS / Linux (Bash / Zsh):**
```bash
curl -fsSL https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.sh | bash
```

**Windows / Cross-Platform (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.ps1 | iex
```

**Configure Any Project in 5 Seconds:**
```bash
cd ~/my-project
atk install          # Symlinks configs for all AI tools into your project
atk start            # Prime session: branch check, context sync & memory recall
```

> 📖 *For complete setup options, manual cloning, and team copy modes, see the [Installation & Setup Guide](docs/installation.md).*

---

## 📚 Documentation & Deep Guides

| Guide | Description |
| :--- | :--- |
| **[🧰 Detailed Component Reference](docs/components.md)** | Deep dive into all 18 skills, 11 subagents, lifecycle hooks, and MCP servers. |
| **[⚡ CLI Commands & Terminal Recipes](docs/cli.md)** | Standalone terminal recipes for `atk`, token compression, memory, PR auditing, and debugging. |
| **[🛠️ Installation & Setup Guide](docs/installation.md)** | Assistant-specific recipes, symlink vs copy modes, global PATH configuration, and multi-project updating. |

---

## 🔄 The End-to-End Daily Workflow Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. SESSION KICKOFF                                                          │
│    atk start (or /session-starter)                                          │
│    • Ingests previous handover from SESSION_LOG.md                          │
│    • Verifies git branch health and working tree state                      │
│    • Validates context file sync (AGENTS.md, CLAUDE.md, GEMINI.md)          │
│    • Recalls active project patterns and anti-patterns                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 2. CONTEXT OPTIMIZATION (85–95% Token Savings)                              │
│    atk profile / atk pack (or /compress-context)                            │
│    • Profiles token consumption across directories                          │
│    • Extracts lightweight AST interface skeletons                           │
│    • Prevents context rot and stays within LLM attention limits             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 3. SURGICAL CODING, TESTING & ADVERSARIAL REVIEW                            │
│    • Software Engineer orchestrates surgical modifications                  │
│    • Test Engineer scaffolds deterministic Red-Green test proofs            │
│    • Code Reviewer audits diff for error swallowing, concurrency & security │
│    • Memory Manager recalls established rules (atk memory recall)           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 4. PRE-FLIGHT PR AUDIT & DISCIPLINED CLOSURE                                │
│    atk pr / atk close (or /session-closer)                                  │
│    • Audits diff for debug logs and leaked credentials                      │
│    • Enforces Zero False Verification (test exit code 0)                    │
│    • Prepends structured handover log to SESSION_LOG.md                     │
│    • Out-of-band Dreamer distills session learnings into memory store       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧭 Skills & Subagents Directory

All skills are delivered via **progressive disclosure** (`.agents/skills/`), and specialized subagents operate in isolated contexts (`.agents/agents/`):

### 🎯 Progressive Disclosure Skills (18 Skills)

| Skill | Primary Focus | CLI Shortcut | Reference |
| :--- | :--- | :--- | :--- |
| **[`session-starter`](skills/session-starter/SKILL.md)** | Session kickoff, handover ingestion & memory priming | `atk start` | [Docs](docs/components.md#2-session-starter-skill) |
| **[`session-closer`](skills/session-closer/SKILL.md)** | Handover ledger logging, context sync & verification | `atk close` | [Docs](docs/components.md#3-session-closer-skill) |
| **[`context-optimizer`](skills/context-optimizer/SKILL.md)** | Token heatmap profiling & AST interface skeletonizing | `atk profile` / `atk pack` | [Docs](docs/components.md#1-context-optimizer-skill) |
| **[`memory-manager`](skills/memory-manager/SKILL.md)** | Persistent scoped developer memory & SHA-256 recall | `atk memory` | [Docs](docs/components.md#15-memory-manager-skill) |
| **[`dreamer`](skills/dreamer/SKILL.md)** | Out-of-band offline transcript analysis & distillation | `atk dream` | [Docs](docs/components.md#16-dreamer-skill) |
| **[`pr-prep`](skills/pr-prep/SKILL.md)** | Pre-flight secret/log sanitization & PR descriptions | `atk pr` | [Docs](docs/components.md#4-pr-prep-skill) |
| **[`code-reviewer`](skills/code-reviewer/SKILL.md)** | 5-dimension adversarial code audit & verdicts | `atk review` | [Docs](docs/components.md#5-code-reviewer-skill) |
| **[`test-engineer`](skills/test-engineer/SKILL.md)** | Deterministic test scaffolding & boundary matrices | `atk test-gen` | [Docs](docs/components.md#6-test-engineer-skill) |
| **[`system-architect`](skills/system-architect/SKILL.md)** | Architecture Decision Records (ADRs) & boundaries | `atk adr` | [Docs](docs/components.md#7-system-architect-skill) |
| **[`debugger`](skills/debugger/SKILL.md)** | Stack trace deobfuscation, repro.sh & git bisect | `atk debug` | [Docs](docs/components.md#8-debugger-skill) |
| **[`security-auditor`](skills/security-auditor/SKILL.md)** | SAST vulnerability scanning & secret leak detection | `atk audit` | [Docs](docs/components.md#9-security-auditor-skill) |
| **[`database-engineer`](skills/database-engineer/SKILL.md)** | Reversible migrations & table lock contention checks | `atk db` | [Docs](docs/components.md#10-database-engineer-skill) |
| **[`container-engineer`](skills/container-engineer/SKILL.md)** | Hardened multi-stage Dockerfiles & caching linters | `atk docker` | [Docs](docs/components.md#11-container-engineer-skill) |
| **[`ci-workflow`](skills/ci-workflow/SKILL.md)** | GitHub Actions pipeline synthesis & action unpinning | `atk ci` | [Docs](docs/components.md#12-ci-workflow-skill) |
| **[`dependency-auditor`](skills/dependency-auditor/SKILL.md)** | Multi-ecosystem wildcard & deprecation auditing | `atk dep` | [Docs](docs/components.md#13-dependency-auditor-skill) |
| **[`release-manager`](skills/release-manager/SKILL.md)** | SemVer bump calculation & Conventional Commits changelogs | `atk release` | [Docs](docs/components.md#14-release-manager-skill) |
| **[`doc-sync`](skills/doc-sync/SKILL.md)** | Documentation, schema parity & broken link sentinel | `atk drift` | [Docs](docs/components.md#17-doc-sync-skill) |
| **[`sys-admin`](skills/sys-admin/SKILL.md)** | Host health triage, server/IaC hardening & SRE templates | `atk sysadmin` | [Docs](docs/components.md#18-sys-admin-skill) |

### 🤖 Specialized Subagents (11 Subagents)

| Subagent | Persona & Focus | Reference |
| :--- | :--- | :--- |
| **`software_engineer`** | Tech Lead orchestrator, surgical changes, peer-review gating, Zero False Verification. | [Docs](docs/components.md#-specialized-subagents) |
| **`code_reviewer`** | Read-only adversarial diff auditor (security, concurrency, error swallowing, churn). | [Docs](docs/components.md#-specialized-subagents) |
| **`test_engineer`** | Test automation specialist, deterministic fixtures, mocks, and Red-Green proof. | [Docs](docs/components.md#-specialized-subagents) |
| **`system_architect`** | Interface contract design, modular boundary enforcement, and ADR synthesis. | [Docs](docs/components.md#-specialized-subagents) |
| **`context_optimizer`** | Token consumption profiling, AST skeleton generation, and hybrid packing. | [Docs](docs/components.md#-specialized-subagents) |
| **`debugger`** | Root-cause analyzer, minimal reproduction scripts (`repro.sh`), automated git bisect. | [Docs](docs/components.md#-specialized-subagents) |
| **`security_auditor`** | Application security scanner, injection checks, and credential leak inspection. | [Docs](docs/components.md#-specialized-subagents) |
| **`database_engineer`** | Zero-downtime DDL, lock contention validation, and migration reversibility. | [Docs](docs/components.md#-specialized-subagents) |
| **`devops_engineer`** | Hardened Dockerfiles, GitHub Actions synthesis, and SemVer release management. | [Docs](docs/components.md#-specialized-subagents) |
| **`research`** | Isolated documentation reading, RFC exploration, and version-pinned snippet distillation. | [Docs](docs/components.md#-specialized-subagents) |
| **`sys_admin`** | USE/RED triage, log condensation, safe rollback apply, host drift & IaC hardening. | [Docs](docs/components.md#-specialized-subagents) |

---

## 🌐 Multi-Tool AI Ecosystem Support

`agent-toolkit` compiles your skills, instructions, and rules into the native configuration format of every leading AI coding assistant:

| Tool | Export Path | Native Integration |
| :--- | :--- | :--- |
| **Claude Code** | `.claude/commands/`<br>`CLAUDE.md` | 18 interactive slash commands (`/session-starter`, `/code-review`, `/memory-manager`, `/sys-admin`, etc.) |
| **Cursor** | `.cursor/rules/*.mdc`<br>`.cursorrules` | 18 Cursor 2.0 MDC rules with glob trigger conditions and engineering standards |
| **GitHub Copilot** | `.github/copilot-instructions.md`<br>`.github/prompts/` | Global repo instructions and 18 reusable `.prompt.md` slash templates |
| **Roo Code / Cline** | `.roomodes`<br>`.clinerules` | 11 multi-agent JSON personas (`software-engineer`, `code-reviewer`, `devops-engineer`, `sys-admin`, etc.) |
| **Windsurf** | `.windsurfrules` | Cascade rules for surgical modifications and session continuity |
| **Antigravity / Gemini CLI** | `.agents/skills/`<br>`.agents/agents/` | Native 18-skill progressive disclosure and 11 specialized subagents |

> 📖 *For assistant-specific recipes and setup commands, see the [Installation Guide](docs/installation.md#assistant-specific-recipes).*

---

## 📂 Repository Structure

```
agent-toolkit/
├── bin/
│   ├── atk                            # Unified global CLI launcher (Bash/Zsh)
│   └── atk.ps1                        # Unified global CLI launcher (PowerShell)
├── install.sh / install.ps1           # Multi-tool installers and symlink managers
├── skills/                            # 18 progressive disclosure skills
├── agents/                            # 11 specialized subagent configurations
├── memory/                            # Persistent repository memory (patterns, rules, ADRs)
├── docs/                              # Detailed component, CLI, and installation guides
│   ├── components.md                  # Comprehensive reference for skills & subagents
│   ├── cli.md                         # Standalone recipes & terminal commands
│   └── installation.md                # Multi-tool installation & registry guide
├── scripts/                           # Central CLI engines, adapters & sentinels
├── hooks/                             # Antigravity PreToolUse and PostToolUse hooks
├── mcp/                               # Native MCP suite: Playwright, GitHub, SQLite
└── tests/                             # 154 deterministic unit tests (Zero False Verification)
```

---

## 🧪 Running Tests

Verify the entire toolkit's synchronizers, auditors, adapters, and memory engines:
```bash
python3 -m unittest discover -s tests
```

---

## 📄 License
MIT License. Free to use across personal and commercial projects.
