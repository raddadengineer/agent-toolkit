---
name: dreamer
description: >-
  Solo developer out-of-band memory consolidation skill. Ingests session ledgers
  and execution transcripts offline, extracts patterns and anti-patterns, and
  presents memory proposals for one-click human review and auto-promotion.
---

# Universal Dreamer (Out-of-Band Memory Consolidation) Skill

This skill implements Anthropic's **"Dreaming"** memory architecture for solo developers. Instead of competing for cognitive attention during in-band coding, the Dreamer runs out-of-band—analyzing past session logs, transcripts, and command traces to extract learnings, detect recurring failure modes, and compound personal engineering leverage.

---

## 📋 Standard Workflow

```
[1. Ingest Transcripts & Ledger] ──► [2. Extract Patterns & Traps] ──► [3. Generate Proposal] ──► [4. Human Sign-Off / Promotion]
```

---

### Step 1: Run Dream Consolidation Analysis

Execute the dreamer pass to synthesize recent learnings across session transcripts and `SESSION_LOG.md`:

```bash
# Analyze recent session and output proposed memory updates:
atk dream --analyze

# Or via Python directly:
python3 .agents/skills/dreamer/scripts/dream_consolidator.py --analyze

# Specify an explicit transcript file:
python3 .agents/skills/dreamer/scripts/dream_consolidator.py --transcript /path/to/transcript.jsonl
```

---

### Step 2: Review Proposed Candidates Interactively

Inspect candidate memories one by one and accept or skip with a single keystroke:

```bash
atk dream --review
```

The system displays:
- Proposed Category (`patterns` or `anti-patterns`)
- Candidate Title & Rationale
- Extracted Code Snippet or Resolution
- Interactive prompt: `Accept and save to repo memory? [y/N]`

---

### Step 3: Auto-Promote High-Confidence Memories

Directly promote high-confidence candidates extracted from verified, passing sessions:

```bash
atk dream --auto-promote
```

---

### Step 4: Export Proposal Document

Generate a structured markdown proposal report for offline review:

```bash
atk dream --output MEMORY_PROPOSAL.md
```
