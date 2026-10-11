---
name: doc-sync
description: >-
  Documentation and schema drift sentinel. Validates that documented architecture,
  agents, skills, and API references match filesystem reality and catches broken links.
---

# Universal Documentation & Schema Drift Sentinel

This skill prevents documentation decay. It verifies that README files, architectural guides, and API documentation remain synchronized with actual source code and agents.

---

## 📋 Standard Workflow

```bash
python3 scripts/check_doc_drift.py --check
```
* **Exit 0**: All internal links resolve cleanly and all agents/skills are fully documented.
* **Exit 1**: Broken markdown links or major doc drift detected.
