# Universal Technical Research & Documentation Standards

These rules govern technical research, external API verification, and context-isolated documentation synthesis.

---

## 1. Version-Pinned Verification
- Always inspect local dependency manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`) first to identify the exact target version of a library or SDK.
- Explicitly flag breaking changes or deprecations between versions when synthesizing documentation.

---

## 2. High-Signal Distillation
- Never dump raw, multi-thousand-line HTML or Markdown pages back to the calling agent.
- Distill findings into:
  1. **Exact Signatures & Types**: Function signatures, parameter types, and return payloads.
  2. **Minimal Working Example**: A 5–15 line idiomatic snippet demonstrating usage.
  3. **Gotchas & Rate Limits**: Thread-safety notes, error exceptions, timeouts, and quota constraints.
  4. **Citations**: Direct links or file paths to the primary source.
