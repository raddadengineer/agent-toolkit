---
name: code-reviewer
description: >-
  Adversarial code review and diff inspection skill. Audits active git diffs
  and PR branches for error swallowing, concurrency race conditions, security
  hazards, missing boundary tests, and scope creep with structured verdicts
  (APPROVE / REQUEST CHANGES).
---

# Universal Code Reviewer Skill

This skill provides an automated, adversarial code review workflow to inspect active changes, pull request diffs, and staging branches before code is committed or merged. It systematically evaluates changes against five critical engineering pillars and generates actionable reports with prioritized findings.

---

## 📋 Review Dimensions

When evaluating diffs or codebases, systematically audit across these 5 pillars:

1. **Security & Secrets**:
   - Injection vulnerabilities (SQL, command injection, XSS).
   - Hardcoded secrets, API tokens, or leaked private keys.
   - Insecure deserialization, unvalidated inputs, or authorization bypasses.

2. **Concurrency & Thread Safety**:
   - Shared mutable state across threads or async tasks.
   - Blocking calls (e.g. synchronous I/O or `time.sleep`) inside async event loops.
   - Race conditions, deadlock potential, or unsynchronized collections.

3. **Error Handling & Failure Modes**:
   - Silent error swallowing (`except: pass`, empty `catch`, `_ = err`, `try?` on critical calls).
   - Missing nil/null checks, partial failure recovery in batch operations.
   - Network call timeouts and retry storm vulnerability.

4. **Architecture & Scope Discipline**:
   - Unintended scope creep or premature refactoring in unrelated files.
   - Violation of repository module boundaries or dependency coupling.
   - Breaking changes to public APIs or data serialization models.

5. **Test Quality & Verification**:
   - Are edge cases (empty states, boundary numbers, error responses) tested?
   - Are tests resilient or brittle to implementation details?
   - Zero-false-verification adherence: do tests actually pass?

---

## 🔄 Execution Workflow

```
[Inspect Diff] ──► [Trace Data Flow & Errors] ──► [Detect Anti-Patterns] ──► [Check Test Coverage] ──► [Emit Structured Verdict]
```

---

## 🛠️ Automated Diff Reviewer (`review_code.py`)

The skill provides an automated static inspection engine:

### Common Recipes

```bash
# 1. Review working tree (staged & unstaged changes against HEAD):
python3 skills/code-reviewer/scripts/review_code.py

# Or using global CLI:
atk review

# 2. Review only staged changes:
python3 skills/code-reviewer/scripts/review_code.py --staged
atk review --staged

# 3. Review changes against a base branch:
python3 skills/code-reviewer/scripts/review_code.py --base main
atk review --base main

# 4. CI/CD Gate: Fail with exit code 1 if CRITICAL anti-patterns are found:
python3 skills/code-reviewer/scripts/review_code.py --check
atk review --check

# 5. Output structured JSON:
python3 skills/code-reviewer/scripts/review_code.py --json
```

---

## 🚨 Anti-Pattern Detection Matrix

| Finding ID | Severity | Anti-Pattern | Language / Pattern | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `CRIT-SWALLOW-ERR` | **CRITICAL** | Silent error swallowing | `except Exception: pass`<br>`catch () {}`<br>`_ = err`<br>`try? criticalCall()` | Bubble up error, log contextual metadata, or map to domain error. |
| `CRIT-ASYNC-BLOCK` | **CRITICAL** | Blocking call in async function | `time.sleep()` in `async def`<br>`Thread.sleep()` in async | Use `await asyncio.sleep()`, `Task.sleep()`, or dispatch to worker thread pool. |
| `CRIT-LEAK-RESOURCE`| **CRITICAL** | Unclosed resource or unmanaged socket | `f = open(...)` without `with`<br>`conn = connect(...)` without defer/cleanup | Always use context managers (`with`), `defer`, or `using`. |
| `WARN-SCOPE-CREEP` | **WARNING** | High file modification count | Large diff with collateral churn across modules | Split into focused, atomic pull requests. |
| `WARN-NO-TESTS` | **WARNING** | Code changes without test coverage | Production logic modified without corresponding test file in diff | Author corresponding unit tests before merge. |

---

## 📊 Structured Report Format

The automated reviewer generates reports structured for clarity:

```markdown
### 🚦 Verdict: `[APPROVE | REQUEST CHANGES]`

### 🔍 Executive Summary
A concise evaluation of diff quality, architectural risk, and merge readiness.

### ⚠️ Findings & Concerns
- **🚨 CRITICAL (Must Fix Before Merge)**: Bugs, race conditions, security holes, error swallowing.
- **⚠️ WARNING (Recommended Improvement)**: Missing edge cases, fragile error handling, missing tests.
- **💡 NIT (Optional Polish)**: Minor idiomatic improvements.

### 🧪 Verification Assessment
Confirmation of test coverage delta and verification proof.
```
