---
name: doc-sync
description: >-
  Documentation and schema drift sentinel. Validates that documented architecture,
  agents, skills, and API references match filesystem reality and catches broken links.
---

# Universal Documentation & Schema Drift Sentinel

This skill prevents documentation decay. It verifies that README files, architectural guides, skills, subagents, and API documentation match actual filesystem reality and catches broken internal markdown links before PR merge.

---

## 📋 Standard Workflow

```
[1. Scan Filesystem Assets] ──► [2. Cross-Reference Documentation] ──► [3. Validate Internal Links] ──► [4. Report Drift]
```

---

### Step 1: Run Documentation Drift Audit

Run the drift sentinel from your project root:

```bash
# Using global atk CLI:
atk drift

# Or direct Python invocation:
python3 .agents/skills/doc-sync/scripts/check_doc_drift.py --check

# Output structured JSON for automated pipelines:
atk drift --json
```

* **Exit 0**: All internal links resolve cleanly, and all skills and subagents on disk are documented.
* **Exit 1**: Broken markdown links or undocumented agents/skills detected. Action required.

---

### Step 2: What the Sentinel Verifies

1. **Skill Discovery**: Every directory in `skills/` (or `.agents/skills/`) must have a corresponding entry in `README.md`.
2. **Subagent Discovery**: Every directory in `agents/` (or `.agents/agents/`) must have a corresponding entry in `README.md`.
3. **Broken Link Sentinel**: Parses all Markdown link syntax (`[text](relative/path)` and `[text](file:///path)`) in documentation and asserts that target files and directories exist on disk.
4. **Context File Alignment**: Ensures guidelines in `README.md` mirror the active agent instructions in `AGENTS.md`.

---

### Step 3: Drift Remediation Guide

* **Undocumented Skill / Subagent**:
  When creating a new skill or agent, add its title, purpose, and relative path to the Repository Structure tree and Component Reference table in `README.md`.
* **Broken Markdown Link**:
  If a file was renamed or reorganized, update all markdown references pointing to the old location. Check anchors (`#section-name`) to ensure headers match.
* **Pre-Commit Integration**:
  Run `atk drift` as part of your local pre-push checks or GitHub Actions CI workflows to keep docs perpetually fresh.
