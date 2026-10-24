# Changelog

All notable changes to this project will be documented in this file.

---

## [v1.1.0] — 2026-10-23

### 🚀 Features
- enforce script parity sentinel, standardize CLI flags, and harden hooks (c02eb2f)
- add --all-projects alias to atk install and atk.ps1 install (61855dc)
- add global installation registry and multi-project updater via atk update --all (1919e00)

### 🐛 Bug Fixes
- use safe parameter expansion ${1:-} in bin/atk to prevent nounset unbound variable error (d697f3f)

### 🔧 Maintenance & Chores
- Add DevOps and research agent integrations (8d9672f)

---

## [v1.0.0] — 2026-10-21

### 🚀 Features
- expand toolkit with 7 specialized engineering skills, CLI commands, and test suites (2350ae6)
- add global atk CLI launcher, enhance install.sh with global linking, and update install docs (ea3835f)
- export scripts and guidelines for Antigravity, fix root deletion regex in guard (27fca51)

### 🔧 Maintenance & Chores
- Add PowerShell support and expand toolkit audits (1d8fa1d)
- chore: record session handover and update context guidelines (130f1cc)
- docs: replace /Dev-Projects paths with generic /path/to/my-project and ~/agent-toolkit (e67fa2f)
- docs(readme): update repository url, global install steps, and update workflows (68324f1)
- Add specialized engineering agents and tooling (7fcf79a)
- Add multi-tool AI agent toolkit (749f078)
- Initial commit: Universal session-closer skill, software_engineer subagent, and installer (bc80f63)
