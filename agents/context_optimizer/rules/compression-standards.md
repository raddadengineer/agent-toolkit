# Context Optimization & Token Discipline Standards

These rules govern context ingestion and token efficiency when preparing codebases for AI agents.

---

## 1. Zero Waste Ingestion
- **Never cat whole directories or entire multi-thousand-line files** without profiling or skeletonizing first.
- Ingest AST skeletons to identify the precise lines or methods requiring changes before loading full implementations.

---

## 2. Hard Token Budgets
- Target an 85–95% reduction in token consumption compared to raw source code.
- Cap repository overviews at 8,000 tokens (`--budget 8000`) for standard tasks, or 4,000 tokens for rapid triage.

---

## 3. Preservation of Semantic Contracts
- Retain all class definitions, type aliases, interface definitions, method signatures, parameter types, return types, and docstrings.
- Strip implementation bodies (`...`, `pass`, or `// ...`) cleanly without altering syntax validity.
