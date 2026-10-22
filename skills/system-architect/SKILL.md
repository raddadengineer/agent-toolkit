---
name: system-architect
description: >-
  System architecture, interface contract design, and Architecture Decision Record (ADR)
  management skill. Scaffolds and indexes ADRs (docs/adr/), audits schema models,
  and enforces system boundaries.
---

# Universal Systems Architect Skill

This skill guides AI agents and system architects through establishing **robust system boundaries, resilient data contracts, and scalable architectural plans**. It includes an automated Architecture Decision Record (ADR) management and validation engine to prevent architectural drift over time.

---

## 🏛️ Core Architectural Pillars

1. **Single Responsibility & High Cohesion**:
   - Every module, service, or class must have a single reason to change.
   - Keep business logic decoupled from transport protocols (HTTP, gRPC, CLI) and storage engines (PostgreSQL, Redis, S3).

2. **Dependency Inversion & Minimal Interfaces**:
   - Depend upon abstractions, not concrete implementations.
   - Keep interfaces minimal and focused on client requirements rather than exposing kitchen-sink API surfaces.

3. **Explicit Data & Schema Contracts**:
   - Define unambiguous data transfer schemas with validation rules before implementing service boundaries.
   - Maintain backwards compatibility for external APIs and persisted schemas. Plan explicit migration pathways for schema changes.

4. **Architectural Decision Records (ADRs)**:
   - Document all non-trivial technical choices in `docs/adr/` with problem context, evaluated alternatives, decision rationale, and trade-off consequences.

---

## 🔄 ADR Lifecycle

```
[Draft Proposal] ──► [PROPOSED] ──► [Evaluate Alternatives] ──► [ACCEPTED] ──► (Future: [SUPERSEDED] / [DEPRECATED])
```

| Status | Meaning |
| :--- | :--- |
| **`PROPOSED`** | Architectural proposal under active review and team evaluation. |
| **`ACCEPTED`** | Approved architecture decision; actively enforced across code reviews. |
| **`SUPERSEDED`** | Obsoleted and replaced by a newer numbered ADR (includes bidirectional link). |
| **`DEPRECATED`** | Retired architecture or deprecated library without a direct replacement. |

---

## 🛠️ Automated ADR Manager (`manage_adr.py`)

The skill provides an automated command-line tool to initialize, create, list, and audit Architectural Decision Records:

### Common Recipes

```bash
# 1. Initialize docs/adr/ directory with baseline 0000 record and README index:
python3 skills/system-architect/scripts/manage_adr.py --init

# Or via global CLI:
atk adr init

# 2. Author a new sequentially numbered ADR:
python3 skills/system-architect/scripts/manage_adr.py --new "Adopt SQLite for Embedded Caching"
atk adr new "Adopt SQLite for Embedded Caching"

# 3. List all recorded ADRs and their statuses:
python3 skills/system-architect/scripts/manage_adr.py --list
atk adr list

# 4. Audit ADR integrity (checks sequence gaps, missing sections, and regenerates index table):
python3 skills/system-architect/scripts/manage_adr.py --audit
atk adr audit

# 5. Output ADR records in JSON:
python3 skills/system-architect/scripts/manage_adr.py --list --json
```

---

## 📄 Standard ADR Document Structure

Every ADR generated adheres to the Michael Nygard template structure:

```markdown
# [Number]. [Title]

Date: YYYY-MM-DD
Status: [PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED]

## Context & Problem Statement
What is the business or technical context? What problem are we solving?

## Decision Drivers
- Performance requirements
- Operational complexity
- Team familiarity & maintenance overhead

## Considered Options
1. Option A (e.g. In-memory dictionary)
2. Option B (e.g. Redis cluster)
3. Option C (e.g. SQLite local file)

## Decision Outcome
Chosen option: **Option C**, because [rationale].

### Positive Consequences
- Zero external infrastructure dependency
- Deterministic test isolation

### Negative Consequences / Trade-offs
- File locking under high concurrent multi-process writes
```
