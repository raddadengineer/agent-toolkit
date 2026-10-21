---
name: security-auditor
description: >-
  Static Application Security Testing (SAST) and vulnerability scanner.
  Audits repositories for injection vectors, secret leaks, dangerous primitives,
  and insecure configurations before pull request or deployment.
---

# Universal Security Auditor Skill

This skill enforces strict pre-commit and pre-release security standards. It scans source code for OWASP Top 10 vulnerabilities, credential exposures, dangerous execution primitives, and insecure configurations across multi-language projects.

---

## 📋 Standard Workflow

```
[1. SAST Code Scan] ──► [2. Secret Leak Check] ──► [3. Manifest Audit] ──► [4. Generate Remediation Report]
```

---

### Step 1: Run Full Security Audit

Run the static security analyzer against the repository:

```bash
# Using global atk CLI:
atk audit --check

# Or direct Python invocation:
python3 .agents/skills/security-auditor/scripts/audit_security.py --check

# Output structured JSON for security dashboards:
atk audit --json
```

* **Exit 0**: No CRITICAL or HIGH vulnerabilities detected.
* **Exit 1**: Immediate block. Action required before merge.

---

### Step 2: Recognized Vulnerability Rules

| Rule ID | Severity | Category | Description | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `SEC-SQLI` | **CRITICAL** | Injection | SQL injection via raw string interpolation (`f"SELECT..."`). | Use parameterized queries or ORM query builders (`cursor.execute("... %s", (val,))`). |
| `SEC-CMDI` | **CRITICAL** | Command Exec | Command injection via `shell=True` or `os.system()`. | Pass argument list directly without invoking shell (`subprocess.run(["cmd", arg])`). |
| `SEC-EVAL` | **CRITICAL** | Code Exec | Arbitrary code execution via `eval()` or `exec()`. | Use safe alternatives (`ast.literal_eval()`, `json.loads()`). |
| `SEC-SECRET-AWS` | **CRITICAL** | Secrets | Hardcoded AWS Access Key ID (`AKIA...`). | Move to environment variables (`AWS_ACCESS_KEY_ID`) or cloud secret managers. |
| `SEC-SECRET-GH` | **CRITICAL** | Secrets | Hardcoded GitHub Token (`ghp_...` or `github_pat_...`). | Revoke token immediately and inject via CI/CD secrets. |
| `SEC-SECRET-PK` | **CRITICAL** | Secrets | Hardcoded Private Key (`BEGIN PRIVATE KEY`). | Remove from repository, rotate key pair, and load from secure vault. |
| `SEC-DESER` | **HIGH** | Deserialization | Insecure deserialization via `pickle` or `yaml.Loader`. | Use `yaml.safe_load()` or strictly typed JSON serialization. |
| `SEC-PERM-777` | **HIGH** | Permissions | Overly permissive file permissions (`0777`). | Restrict permissions to `0755` for executables or `0644` for files. |

---

### Step 3: Multi-Language & Manifest Coverage

* **Source File Coverage**: Scans `.py`, `.ts`, `.js`, `.swift`, `.go`, `.rs`, `.sh`, `.ps1`, `.env`, `.yml`, `.yaml`, and `.json`.
* **Dependency Manifests**: Discovers and logs `package.json`, `requirements.txt`, `Pipfile`, `Cargo.toml`, and `go.mod` for vulnerability auditing.
* **Ignore Filtering**: Excludes test fixtures, node_modules, build directories, and virtual environments from false alarms.
