---
name: session-starter
description: >-
  Primes the engineering session by reading recent session history from SESSION_LOG.md,
  verifying repository state and branch hygiene, checking context file synchronization,
  and aligning on clear session goals and next steps. Use when starting a new session,
  resuming work on a project, or orienting in a repository.
---

# Universal Session Starter Skill

This skill guides the AI agent through a disciplined orientation and kick-off procedure at the beginning of any engineering session. It eliminates context amnesia, surfaces unmerged work or dirty working trees, verifies context synchronization, and establishes a clear agenda before any code is modified.

---

## 📋 Standard Workflow

```
[1. Check Working Tree] ──> [2. Ingest SESSION_LOG.md] ──> [3. Verify Context Sync] ──> [4. Establish Baseline] ──> [5. Deliver Kick-off Briefing]
```

---

### Step 1: Check Git Working Tree & Branch Health
1. Determine the active branch and inspect working tree state:
   ```bash
   git branch --show-current
   git status --short
   git log -1 --oneline
   ```
2. Identify:
   - Are there uncommitted changes left over from previous sessions?
   - Is the workspace detached from HEAD or on a temporary branch?
   - Are there untracked files or stash entries that need resolution?

---

### Step 2: Read Handover Ledger (`SESSION_LOG.md`)
1. Read the most recent session entry in `SESSION_LOG.md` (or run `prime_session.py`):
   ```bash
   python3 .agents/skills/session-starter/scripts/prime_session.py
   ```
2. Note:
   - What was accomplished in the last session?
   - What validation proofs were reported?
   - What were the recorded **Next Steps / Handover** action items?

---

### Step 3: Verify Context File Synchronization
1. Check that primary context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) exist and are in sync:
   ```bash
   python3 .agents/skills/session-closer/scripts/sync_context.py --check
   ```
2. If context files are missing or out of sync:
   - Run `--sync` from the most recent file, or `--init` if setting up a fresh repo.

---

### Step 4: Establish Green Baseline (Zero False Verification)
Before making code changes, run a quick build or test command to ensure the repository starts in a clean, passing state:
- **Node / TypeScript**: `npm test` or `npm run build`
- **Python**: `pytest` or `python -m unittest`
- **Rust**: `cargo check`
- **Go**: `go test ./...`
- **Swift**: `swift test`

> [!NOTE]
> Knowing whether tests pass *before* writing code prevents blaming previous breakages on current modifications.

---

### Step 5: Deliver Kick-off Briefing & Confirm Agenda
Present the developer with a concise orientation report:
1. **Repository & Branch**: Active branch and tree status.
2. **Previous Context**: Summary of the last session's handover items.
3. **Proposed Goal**: Concrete agenda for the current session based on the handover notes and user prompt.
4. **Action Plan**: Confirmation of the immediate first step.
