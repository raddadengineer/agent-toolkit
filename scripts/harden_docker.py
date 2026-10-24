#!/usr/bin/env python3
"""
harden_docker.py — Container Hardening & Dockerfile Security Linter

Scaffolds production-grade, hardened, non-root, multi-stage Dockerfiles and
.dockerignore files, and audits existing Docker configurations for security
and caching hazards.

Usage:
    python3 harden_docker.py --init --stack python
    python3 harden_docker.py --audit Dockerfile
    python3 harden_docker.py --audit Dockerfile --check
    python3 harden_docker.py --audit Dockerfile --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DOCKER_TEMPLATES = {
    "python": {
        "dockerfile": """# Multi-stage hardened Python container
# Stage 1: Build dependencies
FROM python:3.11.8-slim-bookworm AS builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal non-root runtime
FROM python:3.11.8-slim-bookworm AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PATH="/home/appuser/.local/bin:${PATH}"

# Create non-root user (UID 10001)
RUN groupadd -g 10001 appgroup && \\
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed wheels from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python3", "main.py"]
""",
        "dockerignore": """.git
.gitignore
.venv
venv/
env/
__pycache__/
*.py[cod]
*$py.class
*.so
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
.env.*
Dockerfile*
docker-compose*.yml
README.md
docs/
tests/
scratch/
tmp/
""",
    },
    "node": {
        "dockerfile": """# Multi-stage hardened Node.js container
# Stage 1: Dependencies and Build
FROM node:20.11.1-alpine3.19 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build --if-present

# Stage 2: Minimal non-root runtime
FROM node:20.11.1-alpine3.19 AS runtime

WORKDIR /app
ENV NODE_ENV=production

# Use built-in node user (UID 1000)
USER node

COPY --chown=node:node package*.json ./
RUN npm ci --only=production && npm cache clean --force

COPY --chown=node:node --from=builder /app/dist ./dist

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

CMD ["node", "dist/index.js"]
""",
        "dockerignore": """.git
.gitignore
node_modules/
npm-debug.log*
.env
.env.*
Dockerfile*
docker-compose*.yml
coverage/
.idea/
.vscode/
tests/
tmp/
""",
    },
    "go": {
        "dockerfile": """# Multi-stage hardened Go container
# Stage 1: Build binary
FROM golang:1.22.1-alpine3.19 AS builder

WORKDIR /src
RUN apk add --no-cache git ca-certificates

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /bin/app .

# Stage 2: Scratch minimal runtime
FROM alpine:3.19 AS runtime

WORKDIR /app
RUN addgroup -S -g 10001 appgroup && adduser -S -u 10001 -G appgroup appuser
USER appuser

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --chown=appuser:appgroup --from=builder /bin/app /app/app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["/app/app"]
""",
        "dockerignore": """.git
.gitignore
.env
.env.*
Dockerfile*
docker-compose*.yml
bin/
tmp/
""",
    },
    "rust": {
        "dockerfile": """# Multi-stage hardened Rust container
# Stage 1: Build binary
FROM rust:1.76.0-alpine3.19 AS builder

WORKDIR /src
RUN apk add --no-cache musl-dev

COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

# Stage 2: Minimal runtime
FROM alpine:3.19 AS runtime

WORKDIR /app
RUN addgroup -S -g 10001 appgroup && adduser -S -u 10001 -G appgroup appuser
USER appuser

COPY --chown=appuser:appgroup --from=builder /src/target/release/app /app/app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["/app/app"]
""",
        "dockerignore": """.git
.gitignore
target/
.env
.env.*
Dockerfile*
docker-compose*.yml
tmp/
""",
    },
}


def audit_dockerfile(dockerfile_path: Path) -> Dict[str, Any]:
    """Audits a Dockerfile for security and caching anti-patterns."""
    findings = []

    if not dockerfile_path.exists():
        return {
            "status": "fail",
            "file": str(dockerfile_path),
            "critical_count": 1,
            "warning_count": 0,
            "findings": [{
                "id": "DOCKER-NOT-FOUND",
                "severity": "CRITICAL",
                "message": f"Target Dockerfile not found: {dockerfile_path}",
                "line": 0,
            }],
        }

    try:
        content = dockerfile_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return {
            "status": "fail",
            "file": str(dockerfile_path),
            "critical_count": 1,
            "warning_count": 0,
            "findings": [{
                "id": "DOCKER-READ-ERR",
                "severity": "CRITICAL",
                "message": f"Failed to read Dockerfile: {err}",
                "line": 0,
            }],
        }

    lines = content.splitlines()

    has_user_directive = False
    has_healthcheck = False
    has_copy_all = False
    install_after_copy_all = False
    stages_count = 0

    for idx, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # 1. Base Image Pinning
        from_match = re.match(r'^FROM\s+([^\s]+)', line, re.IGNORECASE)
        if from_match:
            stages_count += 1
            image_ref = from_match.group(1).lower()
            if image_ref != "scratch":
                if ":" not in image_ref or image_ref.endswith(":latest"):
                    findings.append({
                        "id": "DOCKER-LATEST-TAG",
                        "severity": "CRITICAL",
                        "line": idx,
                        "snippet": line,
                        "message": f"Unpinned or :latest base image '{image_ref}'. Pin a specific tag or SHA256 digest.",
                    })

        # 2. Non-Root User Detection
        if re.match(r'^USER\s+', line, re.IGNORECASE):
            user_val = line.split()[1]
            if user_val.lower() in ("0", "root"):
                findings.append({
                    "id": "DOCKER-ROOT-USER",
                    "severity": "CRITICAL",
                    "line": idx,
                    "snippet": line,
                    "message": "Explicit root user directive. Containers should run as an unprivileged user.",
                })
            else:
                has_user_directive = True

        # 3. Secret Leakage into ENV / ARG
        env_arg_match = re.match(r'^(?:ENV|ARG)\s+([A-Za-z0-9_]+)\s*=\s*(.*)', line, re.IGNORECASE)
        if env_arg_match:
            var_name = env_arg_match.group(1).upper()
            var_val = env_arg_match.group(2).strip()
            secret_keywords = ("KEY", "SECRET", "PASSWORD", "PASS", "TOKEN", "AUTH", "PRIVATE")
            if any(k in var_name for k in secret_keywords) and len(var_val) > 4:
                findings.append({
                    "id": "DOCKER-SECRET-ENV",
                    "severity": "CRITICAL",
                    "line": idx,
                    "snippet": f"{line.split('=')[0]}=***",
                    "message": f"Possible sensitive credential baked into {line.split()[0]} ({var_name}). Secrets persist in layer history.",
                })

        # 4. Cache-Busting Detection (COPY . . before npm/pip install)
        if re.match(r'^COPY\s+\.\s+\.', line, re.IGNORECASE):
            has_copy_all = True

        if has_copy_all and re.search(r'\b(?:npm\s+i|pip\s+install|cargo\s+build|go\s+build)\b', line):
            install_after_copy_all = True

        # 5. Healthcheck Detection
        if re.match(r'^HEALTHCHECK\b', line, re.IGNORECASE):
            has_healthcheck = True

    if not has_user_directive:
        findings.append({
            "id": "DOCKER-ROOT-USER",
            "severity": "CRITICAL",
            "line": len(lines),
            "snippet": "(End of file)",
            "message": "No non-root 'USER <name>' directive specified. Container defaults to root execution.",
        })

    if install_after_copy_all:
        findings.append({
            "id": "DOCKER-CACHE-BUST",
            "severity": "WARNING",
            "line": 0,
            "snippet": "COPY . . precedes package install",
            "message": "Source code copied before package installation, invalidating layer caching on every commit.",
        })

    if not has_healthcheck:
        findings.append({
            "id": "DOCKER-NO-HEALTH",
            "severity": "WARNING",
            "line": 0,
            "snippet": "Missing HEALTHCHECK",
            "message": "No HEALTHCHECK instruction defined. Orchestrators cannot monitor application liveness.",
        })

    # Check for .dockerignore
    dockerignore_path = dockerfile_path.parent / ".dockerignore"
    if not dockerignore_path.exists():
        findings.append({
            "id": "DOCKER-NO-IGNORE",
            "severity": "WARNING",
            "line": 0,
            "snippet": "Missing .dockerignore",
            "message": f".dockerignore missing in {dockerfile_path.parent}. Risk of leaking secrets or .git into context.",
        })

    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    warning_count = sum(1 for f in findings if f["severity"] == "WARNING")

    return {
        "status": "fail" if critical_count > 0 else "pass",
        "file": str(dockerfile_path),
        "stages_count": stages_count,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "findings": findings,
    }


def format_report(result: Dict[str, Any]) -> str:
    """Formats audit result into human-readable report."""
    lines = []
    status_icon = "✅ PASSED" if result["status"] == "pass" else "❌ FAILED"
    lines.append(f"🐳 Container Security Audit for: {result['file']}")
    lines.append(f"   • Status: {status_icon}")
    lines.append(f"   • Critical Issues: {result['critical_count']}")
    lines.append(f"   • Warnings: {result['warning_count']}")

    if result["findings"]:
        lines.append("\nFindings:")
        for f in result["findings"]:
            icon = "🚨" if f["severity"] == "CRITICAL" else "⚠️"
            loc = f":{f['line']}" if f.get("line") and f["line"] > 0 else ""
            lines.append(f"   {icon} [{f['severity']}] {f['id']}{loc}: {f['message']}")
            if f.get("snippet"):
                lines.append(f"       -> {f['snippet']}")
    else:
        lines.append("   • Dockerfile adheres to non-root and multi-stage container standards.")
    return "\n".join(lines)


def init_stack(target_dir: Path, stack: str):
    """Scaffolds hardened Dockerfile and .dockerignore for chosen stack."""
    if stack not in DOCKER_TEMPLATES:
        print(f"❌ Unsupported stack: '{stack}'. Choose from: {', '.join(DOCKER_TEMPLATES.keys())}", file=sys.stderr)
        sys.exit(1)

    template = DOCKER_TEMPLATES[stack]
    df_path = target_dir / "Dockerfile"
    di_path = target_dir / ".dockerignore"

    if df_path.exists():
        print(f"⚠️ Dockerfile already exists at {df_path}. Refusing to overwrite.")
    else:
        df_path.write_text(template["dockerfile"], encoding="utf-8")
        print(f"✅ Scaffolding hardened multi-stage Dockerfile for {stack}: {df_path}")

    if di_path.exists():
        print(f"⚠️ .dockerignore already exists at {di_path}. Preserving existing file.")
    else:
        di_path.write_text(template["dockerignore"], encoding="utf-8")
        print(f"✅ Scaffolding .dockerignore: {di_path}")


def main():
    parser = argparse.ArgumentParser(description="Container Hardening & Dockerfile Security Linter.")
    parser.add_argument("--init", action="store_true", help="Scaffold hardened Dockerfile and .dockerignore")
    parser.add_argument(
        "--stack",
        choices=["python", "node", "go", "rust"],
        default="python",
        help="Application technology stack (default: python)",
    )
    parser.add_argument(
        "--audit",
        nargs="?",
        const="",
        type=str,
        default=None,
        help="Audit Dockerfile (optional path to Dockerfile, defaults to ./Dockerfile)",
    )
    parser.add_argument("--check", action="store_true", help="Exit code 1 if CRITICAL findings exist")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--dir", "--path", "--repo", dest="dir", type=str, default=None, help="Target directory for scaffolding (default: current)")

    args = parser.parse_args()
    target_dir = Path(args.dir).resolve() if args.dir else Path.cwd()

    if args.init:
        init_stack(target_dir, args.stack)
        sys.exit(0)

    dockerfile_path = Path(args.audit).resolve() if (args.audit and args.audit.strip()) else target_dir / "Dockerfile"

    res = audit_dockerfile(dockerfile_path)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(format_report(res))

    if args.check and res["critical_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
