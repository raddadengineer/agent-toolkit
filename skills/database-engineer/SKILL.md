---
name: database-engineer
description: >-
  Database migration safety and zero-downtime schema engineering skill.
  Audits migrations for reversibility, dangerous table locks, and index contention
  before applying changes to staging or production.
---

# Universal Database Migration & Schema Safety Skill

This skill guarantees zero-downtime database modifications. It audits migrations for reversibility, prevents exclusive table-locking anti-patterns, and guides safe, phased schema evolution before DDL changes hit staging or production environments.

---

## 📋 Standard Workflow

```
[1. Scan Migration Files] ──► [2. Check Downgrade/Rollback] ──► [3. Audit Lock Hazards] ──► [4. Validate Execution]
```

---

### Step 1: Run Migration Safety Audit

Run the migration safety validator against the active migrations directory:

```bash
# Using global atk CLI:
atk db --check

# Or direct Python invocation:
python3 .agents/skills/database-engineer/scripts/verify_migrations.py --check

# Output structured JSON for agent analysis:
atk db --json
```

* **Exit 0**: All migrations are reversible and free of dangerous table locks.
* **Exit 1**: Dangerous DDL or missing rollback routine detected. Action required.

---

### Step 2: Recognized Hazard Anti-Patterns

| Hazard ID | Severity | Description | Safe Alternative |
| :--- | :--- | :--- | :--- |
| `MIG-LOCK-ADD-NOT-NULL` | **CRITICAL** | `ADD COLUMN NOT NULL` without `DEFAULT` rewrites table and locks writes. | Add column as nullable or with a default value, backfill in batches, then apply `NOT NULL`. |
| `MIG-LOCK-NON-CONCURRENT-INDEX` | **HIGH** | `CREATE INDEX` without `CONCURRENTLY` holds exclusive write lock. | Use `CREATE INDEX CONCURRENTLY` (PostgreSQL) or run via background schema tool (gh-ost/pt-osc for MySQL). |
| `MIG-BREAK-DROP-COLUMN` | **HIGH** | `DROP COLUMN` causes immediate failures in active application pods. | Deploy code that ignores the column first, wait for all instances to cycle, then drop column in a later release. |
| `MIG-BREAK-DROP-TABLE` | **HIGH** | `DROP TABLE` breaks running services holding active queries. | Verify all code references and foreign keys are purged across services before dropping table. |
| `MIG-LOCK-ALTER-TYPE` | **HIGH** | `ALTER COLUMN TYPE` triggers a full table rewrite and table lock. | Create new column with target type, dual-write in application, backfill data, switch reads, drop old column. |
| `MIG-IRREVERSIBLE` | **HIGH** | Migration lacks an active `downgrade()` implementation. | Provide tested, symmetric rollback routines for all forward operations. |
| `MIG-LOCK-RENAME` | **MEDIUM** | `RENAME TABLE/COLUMN` immediately breaks active queries. | Use phased expand-and-contract migration rather than immediate in-place rename. |

---

### Step 3: Phased Expand-and-Contract Recipe

When modifying existing production columns or tables, execute across phased releases:

1. **Phase 1 (Expand)**: Add the new column/table as nullable. Deploy code with dual-writing (writes to both old and new columns).
2. **Phase 2 (Backfill)**: Run an asynchronous background job to backfill legacy rows in small batches (`LIMIT 1000`).
3. **Phase 3 (Contract Read)**: Switch application reads from the old column to the new column.
4. **Phase 4 (Contract Write)**: Stop dual-writing; write only to the new column.
5. **Phase 5 (Cleanup)**: Drop the old column/table in a dedicated migration.

---

### Step 4: Engine-Specific Considerations

* **PostgreSQL**: Always create indexes with `CONCURRENTLY`. Never run `CREATE INDEX CONCURRENTLY` inside a multi-statement transaction block.
* **MySQL / MariaDB**: Adding columns or changing types can trigger table copies. For large tables (>10M rows), verify online DDL algorithm (`ALGORITHM=INPLACE, LOCK=NONE`) or use external online schema change tools.
* **SQLite**: Many alter operations require recreating the table. Verify temporary table backup and atomic rename.
