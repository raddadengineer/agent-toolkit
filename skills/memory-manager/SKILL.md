---
name: memory-manager
description: >-
  Solo developer scoped memory manager and recall skill. Manages persistent
  repository-level and global developer memories (patterns, anti-patterns, rules,
  and architecture decisions) with indexed search and SHA-256 integrity verification.
---

# Universal Scoped Memory Manager Skill

This skill provides persistent, structured memory for AI coding sessions across multiple tools (Claude Code, Cursor, Google Antigravity, Gemini CLI, Windsurf). It eliminates context amnesia and context rot by replacing bloated static prompts with indexed, content-addressed memory stores.

---

## 📋 Standard Workflow

```
[1. Recall Relevant Memories] ──► [2. Apply Patterns / Avoid Gotchas] ──► [3. Record New Knowledge] ──► [4. Audit Integrity]
```

---

### Step 1: Recall Memories Before Executing Complex Work
Before modifying architecture, debugging tricky errors, or authoring tests, query the memory store for established project conventions and past pitfalls:

```bash
# Search memory by topic or keywords:
atk memory recall "test mock fixtures"

# Or search using Python directly:
python3 .agents/skills/memory-manager/scripts/manage_memory.py recall "database lock"

# Filter by category:
python3 .agents/skills/memory-manager/scripts/manage_memory.py recall "import error" --category anti-patterns
```

---

### Step 2: Record New Solutions and Anti-Patterns
When a non-trivial bug is solved, a tricky framework quirk is mastered, or an architectural rule is established, record it so future sessions never repeat the discovery cost:

```bash
# Record an anti-pattern (pitfall to avoid):
atk memory record \
  --category anti-patterns \
  --title "Avoid circular imports in AST visitor" \
  --content "When subclassing NodeVisitor, import parent classes from ast directly rather than re-exporting modules." \
  --tags "python,ast,architecture"

# Record a proven solution pattern:
atk memory record \
  --category patterns \
  --title "Deterministic unit test isolation" \
  --content "Always use tempfile.TemporaryDirectory() context managers for file-based tests to avoid workspace contamination." \
  --tags "testing,fixtures,isolation"
```

---

### Step 3: List & Inspect Stored Memories

```bash
# List all indexed memories:
atk memory list

# Filter by category (patterns, anti-patterns, rules, decisions):
atk memory list --category rules

# Show full contents of an entry:
atk memory show "avoid-circular-imports-in-ast-visitor"
```

---

### Step 4: Audit Memory Integrity & Staleness

```bash
# Verify checksums and detect orphaned files:
atk memory audit

# Repair any discrepancies automatically:
atk memory audit --repair
```

---

## 📂 Memory Store Architecture

Memories are organized cleanly in `<project-root>/memory/`:
- `patterns/`: Winning solution workflows and validated techniques.
- `anti-patterns/`: Known gotchas, tricky bugs, and failure modes to avoid.
- `rules/`: Concrete repo constraints and quality mandates.
- `decisions/`: Lightweight Architecture Decision Records.
- `index.json`: Fast search index with metadata, tags, and SHA-256 checksums.
