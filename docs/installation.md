# 🛠️ Agent Toolkit — Installation & Multi-Tool Setup Guide

This guide explains how `agent-toolkit` installs, links, and updates across different AI coding assistants and team environments.

---

## 📋 Table of Contents
- [How Installation Works](#-how-installation-works)
- [Installation Modes: Symlink vs. Copy](#-installation-modes-symlink-vs-copy)
- [Step-by-Step Installation](#-step-by-step-installation)
  - [Option A: Direct Web Install (1 Command)](#option-a-direct-web-install-recommended--1-command)
  - [Option B: Clone & Install Locally](#option-b-clone--install-locally)
- [Installing into Your Project](#-installing-into-your-project)
- [Assistant-Specific Recipes](#-assistant-specific-recipes)
- [Global Terminal CLI (`atk`)](#-global-terminal-cli-atk)
- [Updating `agent-toolkit` Across Projects](#-updating-agent-toolkit-across-projects)
- [Team Repositories & Git Hygiene](#-team-repositories--git-hygiene)

---

## ❓ How Installation Works

> [!IMPORTANT]
> **Do NOT copy this entire repository into your project.**
> `agent-toolkit` is designed to be cloned **once** into a central location on your machine (e.g., `~/agent-toolkit` or `~/.agent-toolkit`).
>
> You run `install.sh` from the toolkit pointing to your target project (`--target /path/to/my-project`), or use the global `atk` command inside your project. The installer then generates or symlinks *only* the specific configuration folders and agent skills needed by your chosen AI assistant(s) into your project.

```
┌──────────────────────────────────────────────┐
│  Central Toolkit (~/agent-toolkit)           │
│  ├── install.sh                              │
│  ├── skills/                                 │
│  ├── agents/                                 │
│  └── scripts/                                │
└──────────────────────┬───────────────────────┘
                       │
  ./install.sh --target /path/to/my-project --tool all
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Target Project (/path/to/my-project)        │
│  ├── .agents/skills/    (Antigravity/Codex)  │
│  ├── .codex/            (OpenAI Codex TOMLs) │
│  ├── .claude/commands/  (Claude Code)        │
│  ├── .cursor/rules/     (Cursor MDC)         │
│  ├── .github/prompts/   (Copilot)            │
│  ├── .roomodes          (Roo / Cline)        │
│  ├── .windsurfrules     (Windsurf)           │
│  └── SESSION_LOG.md     (Session Ledger)     │
└──────────────────────────────────────────────┘
```

---

## 📦 Installation Modes: Symlink vs. Copy

`install.sh` supports two distribution modes via `--mode <symlink|copy>`:

| Mode | Flag | How It Works | Best For |
| :--- | :--- | :--- | :--- |
| **Symlink** *(Default)* | `--mode symlink` | Creates symbolic links from your project back to your central `agent-toolkit` directory. | **Solo / Local Dev**: When you run `git pull` in `agent-toolkit`, all your projects immediately get the latest skills and agents without re-installing. |
| **Copy / Standalone** | `--mode copy` | Copies the physical files and scripts directly into your target project directory. | **Team Repos & CI/CD**: The target repository is 100% self-contained. Teammates and CI runners do not need `agent-toolkit` cloned on their machines. |

---

## 🚀 Step-by-Step Installation

### Option A: Direct Web Install (Recommended — 1 Command)
Install `agent-toolkit` and configure the global `atk` CLI launcher directly from the web without cloning manually:

**macOS / Linux (Bash / Zsh):**
```bash
curl -fsSL https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.sh | bash
```

*Or install directly into a specific project from the web:*
```bash
curl -fsSL https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.sh | bash -s -- --target /path/to/my-project --tool all
```

**Windows / Cross-Platform (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.ps1 | iex
```

*Or install directly into a specific project from PowerShell:*
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.ps1))) -Target "C:\path\to\my-project" -Tool all
```

### Option B: Clone & Install Locally
Alternatively, clone this repository once to a central folder on your machine:
```bash
git clone https://github.com/raddadengineer/agent-toolkit.git ~/agent-toolkit
cd ~/agent-toolkit

# For Bash / Zsh users (symlinks into ~/.local/bin and configures shell):
./install.sh --global

# For PowerShell users (cross-platform pwsh or Windows PowerShell):
.\install.ps1 -Global
```

---

## 🎯 Installing into Your Project

You can run the installer using any of the following approaches:

### Approach A: Using the Global `atk` CLI (Fastest):
```bash
cd ~/my-project

# Configure all AI tools at once (symlinks for local dev):
atk install

# Or copy physical files for a self-contained team repository:
atk install --mode copy
```

### Approach B: From the `agent-toolkit` directory (Specifying `--target`):
```bash
cd ~/agent-toolkit

# Configure all AI tools at once with symlinks:
./install.sh --target /path/to/my-project --tool all

# Or copy physical files:
./install.sh --target /path/to/my-project --tool all --mode copy
```

### Approach C: From inside your target project directory:
```bash
cd ~/my-project

# Run the installer directly pointing to your central toolkit location:
~/agent-toolkit/install.sh --tool all
```

---

## 🎯 Assistant-Specific Recipes

If you only use a specific AI assistant, you can install just its configuration:

```bash
# 1. Claude Code (.claude/commands/, CLAUDE.md):
./install.sh --target /path/to/my-project --tool claude
# (or 'atk install --tool claude' from inside your project)

# 2. Cursor (.cursor/rules/*.mdc, .cursorrules):
./install.sh --target /path/to/my-project --tool cursor
# (or 'atk install --tool cursor' from inside your project)

# 3. GitHub Copilot (.github/copilot-instructions.md, .github/prompts/):
./install.sh --target /path/to/my-project --tool copilot

# 4. Roo Code / Cline (.roomodes, .clinerules):
./install.sh --target /path/to/my-project --tool roo

# 5. Windsurf (.windsurfrules):
./install.sh --target /path/to/my-project --tool windsurf

# 6. Google Antigravity & Gemini CLI (.agents/, AGENTS.md, GEMINI.md):
./install.sh --target /path/to/my-project --tool antigravity
# (or ./install.sh --target /path/to/my-project --all)

# 7. OpenAI Codex (.codex/config.toml, .codex/agents/*.toml, .agents/skills/, AGENTS.md):
./install.sh --target /path/to/my-project --tool codex
# (or 'atk install --tool codex' from inside your project)

# 8. Utilities:
./install.sh --web          # Install or refresh central toolkit directly from web repository
./install.sh --global       # Symlink 'atk' into ~/.local/bin and configure shell profiles
./install.sh --powershell   # Explicitly configure PowerShell profile with 'atk' function
./install.sh --update       # Pull latest toolkit updates from origin main

# PowerShell equivalents:
.\install.ps1 -Web          # Install or refresh central toolkit directly from web repository
.\install.ps1 -Global       # Install global 'atk' launcher & configure PowerShell profile
.\install.ps1 -Update       # Pull latest updates and refresh configurations
```

To inspect all available skills, subagents, and supported assistants:
```bash
./install.sh --list         # Or '.\install.ps1 -List' in PowerShell
```

---

## ⚡ Global Terminal CLI (`atk`)

`agent-toolkit` includes unified global CLI launchers (`bin/atk` for Bash/Zsh, `bin/atk.ps1` for PowerShell) that make all skills, auditors, and installers accessible from **any** directory without typing script paths.

### 1. Enable Global Access (One-time setup):

**Bash / Zsh:**
```bash
cd ~/agent-toolkit
./bin/atk link
# (or ./install.sh --global)
```
*(Symlinks `atk` and `agent-toolkit` directly into `~/.local/bin`, and updates PowerShell profile if PowerShell is present).*

**PowerShell (Windows, macOS, Linux):**
```powershell
cd ~/agent-toolkit
.\install.ps1 -Global
# (or pwsh ./bin/atk.ps1 link)
```
*(Links `atk.ps1` into `~/.local/bin` and idempotently configures your `$PROFILE` with native `atk` and `agent-toolkit` functions).*

---

## 🔄 Updating `agent-toolkit` Across Projects

You can update `agent-toolkit` at any time:

### Option 1: Using the Global CLI (Fastest):
```bash
# Refresh current project:
atk update

# Or refresh ALL registered project installations across your system at once:
atk update --all

# Inspect all registered project installations:
atk installs
```
*(Every time you run `atk install` in a repository, it is automatically recorded in `~/.agent-toolkit/installs.json`. Running `atk update --all` pulls latest commits from `origin main` and automatically updates configurations across all registered projects in one shot).*

### Option 2: Using the Installer Script:
```bash
cd ~/agent-toolkit
./install.sh --update
```

### Manual Update by Mode:
* **If you installed with `--mode symlink` (default):**  
  Pull the latest changes in your central `agent-toolkit` repository:
  ```bash
  cd ~/agent-toolkit
  git pull origin main
  ```
  All linked projects immediately inherit updated skills, subagents, and hooks without needing re-installation.

* **If you installed with `--mode copy`:**  
  Pull updates in the central toolkit, then re-run the installer targeting your project:
  ```bash
  cd ~/agent-toolkit
  git pull origin main
  ./install.sh --target /path/to/my-project --tool all --mode copy
  ```

---

## 👥 Team Repositories & Git Hygiene

When sharing a project repository with a team:
* **Using `--mode copy` (Team Setup)**: Commit the generated `.agents/`, `.codex/`, `.cursor/`, `.claude/`, `.github/`, and `SESSION_LOG.md` files to version control so all team members and AI assistants share identical standards.
* **Using `--mode symlink` (Personal Local Setup)**: If teammates do not use `agent-toolkit`, you can add `.agents/`, `.codex/`, `.claude/`, and `.roomodes` to your repository's `.gitignore` or global `~/.gitignore_global`.
