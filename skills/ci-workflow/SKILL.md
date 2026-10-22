---
name: ci-workflow
description: >-
  CI/CD pipeline synthesis and workflow security auditing skill. Scaffolds optimized
  GitHub Actions pipelines wired to agent-toolkit verification gates, and audits
  workflows for unpinned action hashes and permission hazards.
---

# Universal CI Workflow Skill

This skill guides AI agents and engineers through generating and hardening automated CI/CD pipelines. It connects repository verification gates (`atk audit --check`, `atk review --check`, test matrices, and doc drift sentinels) to GitHub Actions and audits workflow files for supply-chain security risks.

---

## 🏛️ CI/CD Pipeline Standards

1. **Explicit Principle of Least Privilege**:
   - Set top-level `permissions: read-all` (or `permissions: {}`). Explicitly declare elevated scopes only on jobs that write (e.g. releases or deployments).

2. **Action Pinning & Supply Chain Security**:
   - Pin third-party GitHub Actions to full commit SHAs or immutable semver tags rather than mutable `@main` or `@master` branches.

3. **Job Timeouts**:
   - Always declare `timeout-minutes: 15` (or lower) on every job to prevent stuck processes from consuming all runner minutes.

4. **Matrix Testing & Concurrency**:
   - Run tests across supported runtime versions and OS targets concurrently.
   - Configure workflow concurrency groups (`cancel-in-progress: true`) to abort redundant pipeline runs on rapid pushes.

5. **Integrated Toolkit Quality Gates**:
   - Run static audits (`audit_security.py --check`), code review checks (`review_code.py --check`), documentation drift sentinels, and unit tests as mandatory branch protection prerequisites.

---

## 🔄 Execution Workflow

```
[Detect Stack & Manifests] ──► [Synthesize CI Pipeline (.github/workflows/ci.yml)] ──► [Audit Action Pinning & Scopes] ──► [Validate YAML Syntax]
```

---

## 🛠️ Automated CI Synthesizer & Auditor (`synthesize_ci.py`)

The skill provides an automated workflow generator and security auditor:

### Common Recipes

```bash
# 1. Scaffolds a complete GitHub Actions CI pipeline for Python:
python3 skills/ci-workflow/scripts/synthesize_ci.py --init --stack python

# Or via global CLI:
atk ci init --stack python

# Supported stacks: python, node, go, rust, multi

# 2. Audit existing CI workflow files in .github/workflows/ for security anti-patterns:
python3 skills/ci-workflow/scripts/synthesize_ci.py --audit
atk ci audit

# 3. CI/CD Gate: Fail with exit code 1 if critical CI vulnerabilities exist:
python3 skills/ci-workflow/scripts/synthesize_ci.py --audit --check
atk ci audit --check

# 4. Output audit findings in JSON:
python3 skills/ci-workflow/scripts/synthesize_ci.py --audit --json
```

---

## 🚨 CI Anti-Pattern Detection Matrix

| Finding ID | Severity | Anti-Pattern | Hazard & Remediation |
| :--- | :--- | :--- | :--- |
| `CI-UNPINNED-ACTION` | **CRITICAL** | Using `@main` or mutable branch | Upstream compromise or breaking changes silently break CI. Pin to tag or SHA. |
| `CI-MISSING-TIMEOUT` | **WARNING** | Job without `timeout-minutes` | Hung jobs consume pipeline quotas and block deploy queues. |
| `CI-BROAD-PERMISSIONS` | **WARNING** | Missing top-level `permissions` | Default GITHUB_TOKEN has broad write privileges on some repositories. Add `permissions: read-all`. |
| `CI-PULL-REQUEST-TARGET`| **CRITICAL** | Dangerous `pull_request_target` | May grant PR forks access to repo secrets or write tokens. |
