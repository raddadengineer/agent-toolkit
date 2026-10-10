---
name: session-closer
description: >-
  Summarizes the engineering session, updates the session ledger (SESSION_LOG.md),
  and ensures all project context files (AGENTS.md, CLAUDE.md, GEMINI.md) are
  updated and synchronized. Use when ending a session, closing a task, or when
  asked to wrap up and document progress.
---

# Universal Session Closer Skill

This skill guides the AI agent through a disciplined session closure procedure to ensure project continuity, up-to-date context files, clean verification, and clear handover notes for subsequent engineering sessions.

---

## 📋 Standard Workflow

```
[1. Analyze Git Diff] ──> [2. Record SESSION_LOG.md] ──> [3. Sync Context Files] ──> [4. Verify Build & Tests] ──> [5. Deliver Handover Report]
```

---

### Step 1: Analyze Session Accomplishments
1. Inspect git status, recent file changes, and diffs to capture all work performed during the session:
   ```bash
   git status --short
   git diff --stat
   ```
2. Catalogue:
   - New features, components, services, or APIs introduced.
   - Refactored code, bug fixes, or performance optimizations.
   - Architectural adjustments, new dependencies, or updated configuration files.
   - Files deleted, renamed, or migrated.

---

### Step 2: Record Session Entry in `SESSION_LOG.md`
1. Locate or create `SESSION_LOG.md` at the repository root.
2. Prepend a structured session record directly below the header:
   ```markdown
   ### Session [YYYY-MM-DD HH:MM] — <Clear Title/Goal>

   - **Goal**:
     - Concise statement of what the session aimed to achieve.
   - **Changes Completed**:
     - Bulleted list of specific changes, additions, and refactors with file paths.
   - **Validation**:
     - Concrete verification commands executed and results (tests, builds, linter runs).
   - **Next Steps / Handover**:
     - High-priority follow-up tasks, unresolved questions, or upcoming milestones.

   ---
   ```
3. *Alternative (Automated)*: You can use the `sync_context.py` CLI helper:
   ```bash
   python3 .agents/skills/session-closer/scripts/sync_context.py --log \
     --title "Feature Title" \
     --goal "Feature Goal" \
     --change "Added component X" \
     --change "Updated service Y" \
     --validation "All 18 tests passed" \
     --next-step "Deploy to staging"
   ```

---

### Step 3: Update & Synchronize Context Files
1. Review the primary AI context files in the repository:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `GEMINI.md`
   - *(or any custom files configured in `.sync-context.json`)*
2. Check if:
   - New files or directories were added to the project (update the directory tree).
   - New architectural patterns, paradigms, or services were introduced.
   - Development workflows, run commands, or environment variables changed.
3. Edit the primary context file (e.g. `AGENTS.md` or `GEMINI.md`).
4. Run the context synchronizer script to propagate changes bit-for-bit to all companion context files:
   ```bash
   python3 .agents/skills/session-closer/scripts/sync_context.py --sync AGENTS.md
   ```
5. Confirm that all context files match SHA-256 checksums:
   ```bash
   python3 .agents/skills/session-closer/scripts/sync_context.py --check
   ```

---

### Step 4: Verify Project Health & Build Integrity
Run the appropriate verification command for the repository's technology stack:

- **Node / TypeScript / JavaScript**:
  ```bash
  npm test          # or pnpm test / yarn test / bun test
  npm run build     # ensure production build passes
  ```
- **Python**:
  ```bash
  pytest            # or python -m unittest discover
  ruff check .      # or flake8 / mypy
  ```
- **Rust**:
  ```bash
  cargo check
  cargo test
  ```
- **Go**:
  ```bash
  go test ./...
  go vet ./...
  ```
- **Swift / iOS / macOS**:
  ```bash
  swift test        # for Swift packages
  # or xcodebuild for Xcode projects
  ```

> [!IMPORTANT]
> **Zero False Verification Rule**: Never report that a build, test, or linter succeeded unless the CLI tool was actually executed in this session and returned an exit code of `0`.

---

### Step 5: Deliver Handover Summary
Conclude the session by presenting the user with an executive handover report covering:
1. **Accomplishments**: High-level summary of what was built or fixed.
2. **Context & Ledger Status**: Confirmation that `SESSION_LOG.md` and context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) are updated and in sync.
3. **Verification Summary**: Exact test/build commands run and confirmation of passing status.
4. **Immediate Next Steps**: Recommended starting point for the next session.
