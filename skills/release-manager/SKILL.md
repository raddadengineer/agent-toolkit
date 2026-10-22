---
name: release-manager
description: >-
  Release management and Semantic Versioning skill. Parses Conventional Commits
  between git tags, calculates next semver bumps (major/minor/patch), updates
  CHANGELOG.md, and generates release notes.
---

# Universal Release Manager Skill

This skill guides AI agents and maintainers through managing software releases, calculating semantic version bumps, compiling changelogs from Conventional Commits, and gating releases against uncommitted changes or broken test suites.

---

## 🏛️ Release & Versioning Principles

1. **Semantic Versioning (SemVer 2.0.0)**:
   - `MAJOR` (X.0.0): Breaking API or schema changes (indicated by `BREAKING CHANGE:` or `feat!:`).
   - `MINOR` (0.X.0): Backward-compatible new features (indicated by `feat:`).
   - `PATCH` (0.0.X): Backward-compatible bug fixes, security patches, or optimizations (`fix:`, `perf:`).

2. **Conventional Commits Parsing**:
   - Parse git commit logs since the last tag and categorize into structured release sections:
     - 🚀 Features (`feat:`)
     - 🐛 Bug Fixes (`fix:`)
     - ⚡ Performance (`perf:`)
     - ♻️ Refactoring (`refactor:`)
     - 🔧 Maintenance & Chores (`chore:`, `docs:`, `test:`)

3. **Changelog Integrity**:
   - Maintain `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com) standards.
   - Every release entry must include the release tag, date, and grouped bulleted lists.

4. **Release Gate Verification**:
   - Never tag a release on a dirty working tree or an unmerged branch.
   - Verify that test suites pass under the **Zero False Verification** rule before tagging.

---

## 🔄 Execution Workflow

```
[Inspect Git History & Tags] ──► [Parse Conventional Commits] ──► [Calculate SemVer Bump] ──► [Update CHANGELOG.md] ──► [Draft Release Notes]
```

---

## 🛠️ Automated Release Manager (`manage_release.py`)

The skill provides an automated release assistant and changelog compiler:

### Common Recipes

```bash
# 1. Inspect recent commits and calculate next recommended SemVer:
python3 skills/release-manager/scripts/manage_release.py --bump

# Or via global CLI:
atk release bump

# 2. Generate a ready-to-publish Markdown release summary:
python3 skills/release-manager/scripts/manage_release.py --notes
atk release notes

# 3. Update or initialize CHANGELOG.md with the latest release section:
python3 skills/release-manager/scripts/manage_release.py --changelog
atk release changelog

# 4. Verify release readiness (working tree is clean, branch is main/master):
python3 skills/release-manager/scripts/manage_release.py --check
atk release check
```

---

## 📄 Standard Release Note Template

```markdown
## [v1.2.0] — 2026-10-20

### 🚀 Features
- **cli**: Add global atk.ps1 runner for cross-platform PowerShell execution (#42)
- **skills**: Add container-engineer and ci-workflow skills (#45)

### 🐛 Bug Fixes
- **doc-sync**: Fix upward directory traversal in check_doc_drift (#40)
- **security**: Eliminate self-scan false positives on test fixtures (#41)

### 🔧 Maintenance & Chores
- **docs**: Synchronize context guidelines and update install recipes
```
