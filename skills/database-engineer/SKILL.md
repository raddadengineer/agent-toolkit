---
name: database-engineer
description: >-
  Database migration safety and zero-downtime schema engineering skill.
  Audits migrations for reversibility, dangerous table locks, and index contention
  before applying changes to staging or production.
---

# Universal Database Migration & Schema Safety Skill

This skill guarantees zero-downtime database modifications. It verifies that migrations have clean rollbacks and detects locking anti-patterns before code hits production.

---

## 📋 Standard Workflow

```
[1. Scan Migration Files] ──► [2. Check Downgrade/Rollback] ──► [3. Audit Lock Hazards] ──► [4. Validate Execution]
```

### Run Migration Safety Audit
```bash
python3 scripts/verify_migrations.py --check
```
* **Exit 0**: All migrations are reversible and free of table-locking anti-patterns.
* **Exit 1**: Dangerous migration detected (e.g. `ADD COLUMN NOT NULL` without `DEFAULT` or non-concurrent index).
