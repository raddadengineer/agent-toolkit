---
name: security-auditor
description: >-
  Static Application Security Testing (SAST) and vulnerability scanner.
  Audits repositories for injection vectors, secret leaks, dangerous primitives,
  and insecure configurations before pull request or deployment.
---

# Universal Security Auditor Skill

This skill enforces strict pre-commit and pre-release security standards. It scans source code for OWASP Top 10 vulnerabilities, credential exposures, and dangerous execution patterns.

---

## 📋 Standard Workflow

```
[1. SAST Code Scan] ──► [2. Secret Leak Check] ──► [3. Manifest Audit] ──► [4. Generate Remediation Report]
```

### Run Full Repository Audit
```bash
python3 scripts/audit_security.py --check
```
* **Exit 0**: No CRITICAL or HIGH vulnerabilities detected.
* **Exit 1**: Immediate block. Action required before merge.

### Output JSON for Agent Ingestion
```bash
python3 scripts/audit_security.py --json
```
