---
name: container-engineer
description: >-
  Production containerization and Dockerfile hardening skill. Scaffolds hardened,
  non-root, multi-stage Dockerfiles and .dockerignore files, and audits existing
  container specifications for security and caching anti-patterns.
---

# Universal Container Engineer Skill

This skill guides AI agents and developers through designing, hardening, and verifying production-ready container images. It enforces multi-stage builds, non-root user execution, minimal attack surfaces, and optimized layer caching.

---

## 🏛️ Core Containerization Standards

1. **Multi-Stage Builds**:
   - Separate build-time dependencies (compilers, SDKs, dev headers) from runtime artifacts.
   - Use minimal runtime base images (Alpine, Debian-slim, or Distroless).

2. **Non-Root Execution**:
   - Never run containers as `root` (UID 0). Explicitly create a dedicated system user/group (`USER appuser`).

3. **Deterministic Pinning**:
   - Pin specific minor/patch tags or image SHA digests (e.g. `python:3.11.8-slim-bookworm`, not `python:latest` or `python:3`).

4. **Secret Hygiene**:
   - Never pass secrets via `ENV` or `ARG`. Secrets persist permanently in Docker image layers. Use buildkit secret mounts (`--mount=type=secret`) for credentials.

5. **Layer Caching Optimization**:
   - Copy dependency manifests (`package.json`, `requirements.txt`, `go.mod`) and install dependencies *before* copying full source code to preserve Docker layer caching.

6. **Container Health & Observability**:
   - Always define an explicit `HEALTHCHECK` directive for long-running services and web servers.

---

## 🔄 Execution Workflow

```
[Inspect Application Stack] ──► [Scaffold Multi-Stage Dockerfile] ──► [Generate .dockerignore] ──► [Audit Container Security] ──► [Verify Build & Run]
```

---

## 🛠️ Automated Container Hardener (`harden_docker.py`)

The skill provides an automated command-line tool to initialize, audit, and harden Dockerfiles:

### Common Recipes

```bash
# 1. Scaffold a hardened Dockerfile and .dockerignore for Python:
python3 skills/container-engineer/scripts/harden_docker.py --init --stack python

# Or via global CLI:
atk docker init --stack python

# Supported stacks: python, node, go, rust

# 2. Audit an existing Dockerfile for security and caching hazards:
python3 skills/container-engineer/scripts/harden_docker.py --audit Dockerfile
atk docker audit Dockerfile

# 3. CI/CD Gate: Fail with exit code 1 if CRITICAL container hazards are found:
python3 skills/container-engineer/scripts/harden_docker.py --audit Dockerfile --check
atk docker audit --check

# 4. Output audit results in JSON:
python3 skills/container-engineer/scripts/harden_docker.py --audit Dockerfile --json
```

---

## 🚨 Container Anti-Pattern Detection Matrix

| Finding ID | Severity | Anti-Pattern | Hazard & Remediation |
| :--- | :--- | :--- | :--- |
| `DOCKER-ROOT-USER` | **CRITICAL** | Running as root | Container breakout exploits root host privileges. Add `USER appuser`. |
| `DOCKER-LATEST-TAG` | **CRITICAL** | `latest` or unpinned base tag | Non-reproducible builds; breaking upstream changes. Pin specific version. |
| `DOCKER-SECRET-ENV` | **CRITICAL** | Hardcoded secrets in `ENV`/`ARG` | Passwords or tokens baked permanently into image layer history. |
| `DOCKER-CACHE-BUST` | **WARNING** | `COPY . .` before dependency install | Invalidates package cache on every code change, causing slow builds. |
| `DOCKER-NO-HEALTH` | **WARNING** | Missing `HEALTHCHECK` | Orchestrators cannot detect frozen or zombie service processes. |
| `DOCKER-NO-IGNORE` | **WARNING** | Missing `.dockerignore` file | Leaks `.git`, `.env`, keys, and temporary files into image context. |
