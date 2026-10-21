---
name: debugger
description: >-
  Root-cause debugging and regression isolation skill. Analyzes stack traces,
  generates standalone reproduction harnesses (repro.sh / repro.py), and runs
  automated git bisection to pinpoint breaking commits.
---

# Universal Root-Cause Debugger & Git Bisect Skill

This skill enforces disciplined, evidence-based debugging. Instead of speculative trial-and-error fixes, it mandates stack trace deobfuscation, standalone reproduction harnesses, automated binary git bisection, and explicit Red-Green verification.

---

## 📋 Standard Workflow

```
[1. Trace Deobfuscation] ──► [2. Minimal Reproduction] ──► [3. Git Bisection] ──► [4. Red-Green Fix Proof]
```

---

### Step 1: Analyze & Deobfuscate Stack Traces

Deobfuscate raw error outputs to pinpoint originating call frames across Python, JavaScript/TypeScript, Swift, and Go:

```bash
# Using global atk CLI:
atk debug --analyze-trace /path/to/trace.log

# Or pass inline trace string:
atk debug --analyze-trace "Traceback (most recent call last): ..."

# Or direct Python invocation:
python3 .agents/skills/debugger/scripts/bisect_debugger.py --analyze-trace error.log
```

**Parsed Outputs**:
- Error classification and root exception message.
- Full call stack frame breakdown (file, line number, calling function).
- Originating culprit candidate file and line.

---

### Step 2: Generate a Minimal Reproduction Script

Before touching production code, generate a standalone reproduction harness that proves the bug exists:

```bash
# Shell harness (Linux / macOS):
atk debug --repro "pytest tests/test_orders.py -k test_checkout_flake" --output repro.sh

# PowerShell harness (Windows / pwsh):
atk debug --repro "pytest tests/test_orders.py -k test_checkout_flake" --output repro.ps1

# Python harness (cross-platform):
atk debug --repro "python3 -m unittest tests/test_orders.py" --output repro.py
```

* **The Red-Green Standard**:
  1. **Red (Reproduction)**: Run `./repro.sh` or `.\repro.ps1` on the buggy branch. It must fail and exit code `1`.
  2. **Green (Resolution)**: Implement the fix. Run the script again. It must succeed with exit code `0`.

---

### Step 3: Automated Git Bisection for Regressions

When a previously passing test or feature broke unexpectedly between commits:

```bash
# Automatically bisect commit history using a test command:
atk debug --bisect --test "pytest tests/test_feature.py" --good v2.1.0 --bad HEAD

# Using commit SHAs:
atk debug --bisect --test "npm test" --good a1b2c3d --bad HEAD
```

**How It Works**:
1. Starts `git bisect` and marks bounds.
2. Checks out the midpoint commit and runs the test command.
3. Steps forward or backward through history via binary search until the exact culprit commit is isolated.
4. Resets the git working tree cleanly to HEAD and reports the culprit commit SHA.
