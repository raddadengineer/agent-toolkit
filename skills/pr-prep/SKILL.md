---
name: pr-prep
description: >-
  Prepares clean, production-ready pull requests. Audits git diffs for scope creep,
  debug prints, secrets, and formatting issues, validates build and test status, and
  generates standardized PR title and markdown descriptions with verification proof.
---

# Universal Pull Request Preparation Skill

This skill guides the AI agent through a rigorous pre-flight checklist prior to creating or submitting a pull request. It ensures zero scope creep, sanitizes temporary debug code, guarantees test suite pass rates, and authors clean, reviewer-friendly PR descriptions.

---

## 📋 Standard Workflow

```
[1. Diff & Leak Audit] ──> [2. Verify Build & Tests] ──> [3. Check Context Ledger] ──> [4. Generate PR Description] ──> [5. Final Checklist]
```

---

### Step 1: Diff & Secret Leak Audit
1. Run the PR auditor script against the target base branch (or working tree):
   ```bash
   python3 .agents/skills/pr-prep/scripts/audit_pr.py --check
   ```
2. Manually verify:
   - **No scope creep**: No unrelated formatting or adjacent refactors.
   - **No leftover debug code**: No `console.log`, `print()`, `debugger`, or temporary breakpoints.
   - **No credentials or env variables**: No leaked API keys, tokens, or committed `.env` files.

---

### Step 2: Verify Build Integrity & Test Suite
Execute the project's verification suite under the strict **Zero False Verification** rule:
- **Node / TypeScript**: `npm test && npm run build`
- **Python**: `pytest`
- **Rust**: `cargo test`
- **Go**: `go test ./...`
- **Swift**: `swift test`

> [!IMPORTANT]
> Never state that tests passed without an actual exit code `0` returned by the test runner in the terminal.

---

### Step 3: Check Context & Session Ledger
1. Ensure `SESSION_LOG.md` reflects the changes in the branch.
2. Confirm context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) are updated if new commands or architecture rules were added.
3. Validate sync status:
   ```bash
   python3 .agents/skills/session-closer/scripts/sync_context.py --check
   ```

---

### Step 4: Generate PR Description
Generate a structured, evidence-backed PR description:
```bash
python3 .agents/skills/pr-prep/scripts/audit_pr.py --generate-desc --title "feat: descriptive title"
```

The generated description includes:
- **Summary**: Concise explanation of what the pull request achieves.
- **Key Changes**: Bulleted list of files and architectural updates.
- **Verification & Proof**: Exact test commands run, pass counts, and diff stats.
- **Checklist**: Confirmation of local testing, hygiene, and documentation updates.

---

### Step 5: Deliver Pull Request Summary
Provide the user with:
1. Recommended branch name (e.g. `feat/feature-name` or `fix/bug-name`).
2. Clean commit message suggestion following Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`).
3. The complete ready-to-copy markdown PR body.
