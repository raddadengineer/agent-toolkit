---
name: test-engineer
description: >-
  Quality & test automation engineering skill. Scaffolds deterministic test suites,
  edge-case boundary matrices, parameterizations, and mocks across Python,
  TypeScript, Go, and Rust under a strict Zero False Verification mandate.
---

# Universal Test Engineer Skill

This skill guides AI agents and developers through designing and authoring **deterministic, high-coverage, and resilient** automated test suites. It eliminates flaky tests, establishes boundary coverage matrices, and guarantees that every verification command is genuinely executed with exit code `0`.

---

## 🏛️ The 5 Testing Pillars

1. **Determinism & Flake Prevention**:
   - Zero tolerance for `sleep()` or `Task.sleep()`. Use condition polling with timeouts or explicit async barriers.
   - Clean ephemeral test state per test case (temp directories, in-memory databases, clean teardown).
   - Seed random number generators so any probabilistic failures are 100% reproducible.

2. **Boundary & Negative Testing**:
   - Empty collections, `None` / `null` inputs, and omitted fields.
   - Numeric boundaries: 0, negative integers, maximum values, floats with precision limits.
   - Network timeouts, malformed payloads, disconnected sockets, and unauthorized tokens.

3. **High-Signal Assertions**:
   - Assert exact invariant states rather than vague truthiness (e.g. `assertEqual(res.status_code, 404)` instead of `assertTrue(res.error)`).
   - Provide clear failure messages in assertions to speed up CI debugging.

4. **Targeted Mocking & Boundary Hygiene**:
   - Mock only at architectural edges (external HTTP, payment gateways, file system), never internal domain models.
   - Prevent over-mocking that tests the mock framework rather than application logic.

5. **Zero False Verification (Core Mandate)**:
   - Never report that a test suite passed without executing the command in the CLI and observing exit code `0`.
   - When authoring a test for a bug fix, actively prove the **Red-Green** cycle: verify it fails before the fix and passes after.

---

## 🔄 Execution Lifecycle

```
[Analyze Target File] ──► [Extract AST Signatures] ──► [Generate Edge-Case Matrix] ──► [Scaffold Test Suite] ──► [Execute & Verify (Exit 0)]
```

---

## 🛠️ Automated Test Scaffolder (`scaffold_tests.py`)

The skill includes a multi-framework test generation and edge-case matrix generator:

### Common Recipes

```bash
# 1. Scaffold a unittest test suite from a Python source file:
python3 skills/test-engineer/scripts/scaffold_tests.py --file src/payment_service.py

# Or via global CLI:
atk test-gen src/payment_service.py

# 2. Scaffold a pytest test suite:
python3 skills/test-engineer/scripts/scaffold_tests.py --file src/auth.py --framework pytest

# 3. Generate a Markdown edge-case coverage matrix:
python3 skills/test-engineer/scripts/scaffold_tests.py --file src/auth.py --matrix

# 4. Write generated test suite directly to target file:
python3 skills/test-engineer/scripts/scaffold_tests.py --file src/auth.py --output tests/test_auth.py
```

---

## 📊 Boundary Coverage Matrix Template

When planning test suites for critical features, formulate an edge-case matrix before coding:

| Target Function / Endpoint | Scenario Category | Input Payload / State | Expected Behavior | Assertion |
| :--- | :--- | :--- | :--- | :--- |
| `process_payment(order)` | **Happy Path** | Valid credit card & positive amount | Payment accepted, transaction ID returned | `res.status == 'SUCCESS'` |
| `process_payment(order)` | **Boundary: Amount** | `amount = 0` or `amount = -1.00` | Rejects with `InvalidAmountError` | `assertRaises(InvalidAmountError)` |
| `process_payment(order)` | **Boundary: Missing**| Missing `currency` field | Validates required schema, returns 400 | `res.error == 'MISSING_FIELD'` |
| `process_payment(order)` | **Negative: Timeout**| Gateway timeout > 5000ms | Retries idempotently with backoff | `verify(gateway.retryCount == 2)` |
| `process_payment(order)` | **Concurrency** | Duplicate concurrent submission | Idempotency key blocks double charge | Only 1 charge executed |

---

## 🧪 Tech Stack Test Execution Guide

| Tech Stack | Test Framework | Execution Command |
| :--- | :--- | :--- |
| **Python** | `unittest` | `python3 -m unittest discover -s tests` |
| **Python** | `pytest` | `pytest -v --tb=short` |
| **Node / TS** | `vitest` / `jest` | `npm test` or `npx vitest run` |
| **Go** | `testing` | `go test -v -race ./...` |
| **Rust** | `cargo test` | `cargo test --all-targets` |
| **Swift** | `XCTest` / `Swift Testing` | `swift test` |
