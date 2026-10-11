---
name: context-optimizer
description: >-
  Optimizes token usage and compresses repository context. Profiles token footprints,
  extracts AST/interface skeletons (reducing token usage by 85-95%), and packages
  repositories under strict token budgets for AI assistants. Use when ingesting large
  codebases, profiling token consumption, or preparing dense, low-token context maps.
---

# Universal Context Optimizer & Token Compression Skill

This skill allows AI agents to inspect, explore, and ingest large codebases with maximum semantic density while minimizing token consumption by 85–95%. It eliminates bloated file dumps, minified file noise, and redundant lockfiles.

---

## 📋 Standard Workflow

```
[1. Profile Token Footprint] ──> [2. Select Compression Mode] ──> [3. Generate AST Skeletons] ──> [4. Pack under Token Budget]
```

---

### Step 1: Profile Token Footprint
Find where tokens are being spent across the repository:
```bash
python3 .agents/skills/context-optimizer/scripts/compress_context.py --profile
```
Identifies:
- Total repository token count.
- Top token-heavy files and percentage contribution.
- Accidental bloat (lockfiles, data bundles, oversized fixtures).

---

### Step 2: Skeletonize Specific Files
When reading complex classes or services without needing full implementation bodies:
```bash
python3 .agents/skills/context-optimizer/scripts/compress_context.py --file src/MyService.ts --skeleton
```
Extracts:
- **Python**: Class definitions, type-annotated method/function signatures, and docstrings.
- **TypeScript / JavaScript**: Exported types, interfaces, classes, and method signatures.
- **Swift**: Protocols, actors, structs, enums, public properties, and `func` signatures.
- **Go / Rust**: Structs, interfaces, traits, and exported function signatures.

*Token reduction is typically 85–95% compared to raw file contents.*

---

### Step 3: Generate Whole-Repo Compressed Context (`REPO_MAP.md`)
Pack the entire repository into a single high-density context map under a strict token budget:

```bash
# Hybrid mode: Full content for README & manifests, skeletons for all code (recommended)
python3 .agents/skills/context-optimizer/scripts/compress_context.py --hybrid --budget 8000 --output REPO_MAP.md

# Pure AST skeleton mode:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --skeleton --budget 4000 --output REPO_MAP.md

# XML format for Claude Code / Gemini prompts:
python3 .agents/skills/context-optimizer/scripts/compress_context.py --pack --format xml --budget 12000
```

---

### Step 4: Token Optimization Rules for Agents
When operating under tight context limits:
1. **Never cat whole directories**: Use `--profile` first to understand the landscape.
2. **Skeleton before deep dive**: Ingest the skeleton map to locate the exact 1–2 files that need surgical modification.
3. **Respect token budgets**: Keep injected repository summaries under 8,000 tokens.
