---
name: dependency-auditor
description: >-
  Multi-ecosystem dependency security scanner and manifest auditor. Detects
  unpinned wildcards, dangerous package configurations, and license compliance
  hazards across Python, Node.js, Go, and Rust.
---

# Universal Dependency Auditor Skill

This skill guides AI agents and developers through inspecting, auditing, and maintaining third-party software dependencies. It flags non-reproducible wildcard pinnings, vulnerable package patterns, and license compliance risks across Python, Node.js, Go, and Rust ecosystems.

---

## 🏛️ Dependency Management Standards

1. **Deterministic Pinning**:
   - Production manifests must declare exact versions or bounded semantic version constraints (`~=` or `^`).
   - Wildcards (`*`, `latest`, unpinned package names) are prohibited in production dependencies.

2. **Lockfile Discipline**:
   - Always commit package lockfiles (`package-lock.json`, `poetry.lock`, `Cargo.lock`, `go.sum`) for standalone applications to guarantee identical production builds.

3. **License Compliance**:
   - Flag restrictive copyleft licenses (e.g. AGPL, SSPL) in proprietary/commercial environments to avoid viral licensing liabilities.

4. **Supply Chain Surface Reduction**:
   - Review transitive dependencies, prune unused dev dependencies, and eliminate deprecated or unmaintained packages.

---

## 🔄 Execution Workflow

```
[Detect Manifests (requirements.txt / package.json / Cargo.toml / go.mod)] ──► [Parse Dependencies & Specifiers] ──► [Audit Wildcards & Insecure Patterns] ──► [Report Prioritized Findings]
```

---

## 🛠️ Automated Dependency Auditor (`audit_deps.py`)

The skill provides an automated multi-manifest dependency inspector:

### Common Recipes

```bash
# 1. Audit all dependency manifests across the current repository:
python3 skills/dependency-auditor/scripts/audit_deps.py

# Or via global CLI:
atk dep audit

# 2. CI/CD Gate: Fail with exit code 1 if critical wildcard/security issues exist:
python3 skills/dependency-auditor/scripts/audit_deps.py --check
atk dep audit --check

# 3. Output audit results in machine-readable JSON:
python3 skills/dependency-auditor/scripts/audit_deps.py --json
```

---

## 🚨 Dependency Anti-Pattern Detection Matrix

| Finding ID | Severity | Anti-Pattern | Manifest Example | Hazard & Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `DEP-WILDCARD` | **CRITICAL** | Wildcard version pinning | `"lodash": "*"`<br>`requests==*` | Upstream releases automatically deploy breaking or compromised code. Pin explicit semver. |
| `DEP-UNPINNED` | **WARNING** | Missing version specifier | `flask`<br>`"express": ""` | Non-deterministic builds across developer machines and CI runners. Pin minimum version. |
| `DEP-DEPRECATED` | **WARNING** | Deprecated / dead package | `request` (Node)<br>`pycrypto` (Python) | Abandoned packages with unpatched vulnerabilities. Migrate to active alternatives (`axios`, `cryptography`). |
| `DEP-NO-LOCKFILE` | **WARNING** | Manifest present without lockfile | `package.json` without `package-lock.json` | Lockfile missing; build machines cannot guarantee exact dependency tree. Run install and commit lockfile. |
