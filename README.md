# 🛠️ Agent Toolkit

A centralized, reusable library of high-leverage skills, specialized subagents, and automated developer workflows for AI pair programming assistants (**Google Antigravity**, **Gemini CLI**, **Claude Code**, and **Cursor**).

Instead of recreating or copying session scripts and agent definitions across separate repositories, `agent-toolkit` provides a single home for tools that maintain project continuity, enforce engineering discipline, and eliminate repetitive context synchronization.

---

## 📂 Repository Structure

```
agent-toolkit/
├── README.md                      # Documentation and usage guide
├── install.sh                     # CLI script to symlink or copy tools into projects
├── skills/
│   └── session-closer/            # Universal session conclusion & handover skill
│       ├── SKILL.md               # Step-by-step workflow for agents
│       └── scripts/
│           └── sync_context.py    # Multi-file context synchronizer & session ledger
├── agents/
│   └── software_engineer/         # Universal Senior Software Engineer subagent
│       ├── agent.md               # Agent definition & execution lifecycle
│       └── rules/
│           └── engineering-standards.md # Surgical modification & verification rules
└── tests/
    └── test_sync_context.py       # Unit test suite verifying sync & ledger logic
```

---

## 🧰 Included Components

### 1. 🔄 `session-closer` (Skill)
Guides AI agents through a disciplined 5-step handover procedure at the end of a coding session:
1. **Analyze Accomplishments**: Scans `git status --short` and `git diff --stat` to detect all additions, refactors, and dependency changes.
2. **Record in `SESSION_LOG.md`**: Prepends a clean, dated markdown entry documenting the session goal, specific changes, validation proof, and next steps.
3. **Synchronize Context Files**: Keeps `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` (or custom files) bit-for-bit identical via SHA-256 checks.
4. **Verify Build & Tests**: Runs ecosystem-specific test commands (Swift, Node, Python, Rust, Go) under a strict **Zero False Verification** policy.
5. **Deliver Handover Summary**: Provides an executive report summarizing the completed work and immediate next actions.

#### `sync_context.py` CLI Options
```bash
# Verify all context files have matching SHA-256 checksums
python3 sync_context.py --check

# Checksum status of all tracked files
python3 sync_context.py --status

# Sync all context files from the most recently modified (or specify source)
python3 sync_context.py --sync
python3 sync_context.py --sync AGENTS.md

# Initialize baseline context files and SESSION_LOG.md in a fresh repository
python3 sync_context.py --init

# Programmatically log a completed session entry
python3 sync_context.py --log \
  --title "Payment Gateway Integration" \
  --goal "Add Stripe webhook verification" \
  --change "Implemented WebhookHandler.swift" \
  --change "Added signature verification unit tests" \
  --validation "All 24 unit tests passed (exit 0)" \
  --next-step "Configure webhook endpoint in Stripe dashboard"
```

---

### 2. 👨‍💻 `software_engineer` (Subagent)
A surgical, senior staff software engineer persona that works directly within any codebase:
- **Evidence over assumption**: Bases all diagnoses on compiler traces, test logs, and actual source code.
- **Conventions over preferences**: Strictly adopts host repository conventions rather than imposing external paradigms.
- **Zero false verification**: Refuses to claim a test or build succeeded without an exit code `0`.
- **6-Stage Lifecycle**: `Understand ──> Plan ──> Implement ──> Validate ──> Diff Review ──> Report`.

---

## 🚀 Quick Start & Installation

Use `install.sh` to link or copy skills and agents into any repository's `.agents/` folder.

### 1. List Available Components
```bash
./install.sh --list
```

### 2. Symlink into a Project (Recommended)
Symlinking allows any improvements made in `agent-toolkit` to immediately apply across all your projects:
```bash
# Symlink just the session-closer skill:
./install.sh --target ~/Dev-Projects/my-app --skill session-closer

# Or symlink all skills and agents:
./install.sh --target ~/Dev-Projects/my-app --all
```

### 3. Copy Mode (Standalone)
If you want an independent copy committed into a specific project repository:
```bash
./install.sh --target ~/Dev-Projects/my-app --skill session-closer --mode copy
```

---

## 🧪 Running Tests

Verify the synchronization and session logging engine:
```bash
python3 tests/test_sync_context.py
```

---

## 📄 License
MIT License. Free to use across personal and professional projects.
