---
name: debugger
description: >-
  Root-cause debugging and regression isolation skill. Analyzes stack traces,
  generates standalone reproduction harnesses (repro.sh / repro.py), and runs
  automated git bisection to pinpoint breaking commits.
---

# Universal Root-Cause Debugger & Git Bisect Skill

This skill enforces disciplined, evidence-based debugging. Instead of speculative trial-and-error fixes, it mandates minimal reproduction harnesses and binary regression bisection.

---

## 📋 Standard Workflow

```
[1. Trace Deobfuscation] ──► [2. Minimal Reproduction] ──► [3. Git Bisection] ──► [4. Red-Green Fix Proof]
```

### Step 1: Analyze & Deobfuscate Stack Traces
```bash
python3 scripts/bisect_debugger.py --analyze-trace /path/to/trace.log
```
Identifies:
- Error classification and root exception message.
- Top and bottom call stack frames.
- Precise originating file and line candidate.

### Step 2: Generate a Minimal Reproduction Script
Before editing code, produce a deterministic reproduction script:
```bash
python3 scripts/bisect_debugger.py --repro "pytest tests/test_orders.py -k test_checkout_flake" --output repro.sh
```
* **Red-Green Standard**: The script must exit `1` on the active buggy branch, and exit `0` only after the real fix is implemented.

### Step 3: Automated Git Bisection for Regressions
When a previously passing feature broke unexpectedly:
```bash
python3 scripts/bisect_debugger.py --bisect --test "pytest tests/test_feature.py" --good v2.1.0 --bad HEAD
```
* Automatically steps through commit history, executes the test command, and reports the exact culprit commit.
