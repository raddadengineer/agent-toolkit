#!/usr/bin/env pwsh
<#
.SYNOPSIS
    atk — Global Agent Toolkit CLI launcher for PowerShell

.DESCRIPTION
    Global command-line runner for skills, subagents, and multi-tool adapters.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs = @()
)

$ErrorActionPreference = 'Stop'

# Resolve symlinks to find real toolkit directory
$ScriptPath = $PSCommandPath
if (-not $ScriptPath) {
    $ScriptPath = $MyInvocation.MyCommand.Path
}
if (-not $ScriptPath) {
    $ScriptPath = $MyInvocation.MyCommand.Definition
}

if ($ScriptPath) {
    $Item = Get-Item -LiteralPath $ScriptPath -ErrorAction SilentlyContinue
    while ($Item -and $Item.LinkType) {
        $Target = $Item.Target
        if (-not [System.IO.Path]::IsPathRooted($Target)) {
            $Target = Join-Path (Split-Path -Parent $Item.FullName) $Target
        }
        $Item = Get-Item -LiteralPath $Target -ErrorAction SilentlyContinue
    }
    if ($Item) {
        $ScriptPath = $Item.FullName
    }
}

$BinDir = Split-Path -Parent $ScriptPath
$ToolkitDir = Split-Path -Parent $BinDir

function Get-Python {
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        return "python3"
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    Write-Error "❌ Python 3 was not found in PATH."
    exit 1
}

function Show-Help {
    @"
🛠️  Agent Toolkit CLI (atk) [PowerShell]

Global command-line runner for skills, subagents, and multi-tool adapters.

Usage:
  atk <command> [options]

Core Commands:
  install [opts]       Install toolkit configurations into current project
                       (defaults to: install.ps1 -Target . -Tool all)
  start                Prime workspace and ingest recent handover notes (prime_session.py)
  close                Close session, update SESSION_LOG.md and sync context (sync_context.py)
  sync [file]          Synchronize AGENTS.md, CLAUDE.md, and GEMINI.md
  check                Check SHA-256 sync status of context files
  status               Display status and checksums of tracked context files

Optimization, Quality & Architecture:
  profile [opts]       Profile repository token consumption across files
  skeleton [file]      Generate AST skeleton without implementation bodies
  pack [opts]          Pack repo into hybrid high-density context map under token budget
  review [opts]        Run adversarial code review on active diff (review_code.py)
  test-gen [opts]      Scaffold deterministic tests & boundary matrix (scaffold_tests.py)
  adr [opts]           Manage & audit Architecture Decision Records (manage_adr.py)
  audit [opts]         Run SAST security and secret leak scan (audit_security.py)
  pr [opts]            Run pre-flight diff leak audit & PR description generator
  db [opts]            Verify database migration safety & rollback reversibility
  debug [opts]         Root-cause analysis, repro script & automated git bisect
  drift [opts]         Check documentation & schema drift sentinel (check_doc_drift.py)

DevOps, Release & Ecosystem:
  docker [opts]        Scaffold & audit hardened Dockerfiles (harden_docker.py)
  ci [opts]            Synthesize & audit CI/CD workflows (synthesize_ci.py)
  dep [opts]           Audit dependencies for wildcards & deprecations (audit_deps.py)
  release [opts]       Calculate semver bumps & draft release notes (manage_release.py)

Toolkit Management:
  list                 List available skills, subagents, and AI assistants
  installs             List all registered project installations across the system
  update [-All]        Pull latest toolkit updates (use -All to refresh all projects)
  test                 Run the test suite across all toolkit components
  link                 Configure PowerShell profile and global launcher
  version              Show current agent-toolkit version & directory
  help                 Show this help message

Examples:
  atk install                     # Setup all AI tools for current project
  atk install -Tool cursor        # Setup only Cursor MDC rules
  atk install -Mode copy          # Copy files for self-contained team repo
  atk start                       # Read handover and check git branch
  atk profile                     # Inspect token hotspots
  atk sync                        # Sync AGENTS.md -> CLAUDE.md & GEMINI.md
  atk link                        # Ensure 'atk' is globally accessible in PowerShell
"@
}

function Setup-Link {
    $installScript = Join-Path $ToolkitDir "install.ps1"
    if (Test-Path $installScript) {
        & $installScript -Global
    } else {
        Write-Error "❌ install.ps1 not found in $ToolkitDir"
        exit 1
    }
}

if (-not $Command -or $Command -in @('help', '-h', '--help')) {
    Show-Help
    exit 0
}

$py = Get-Python

switch ($Command) {
    'install' {
        $installScript = Join-Path $ToolkitDir "install.ps1"
        if (-not (Test-Path $installScript)) {
            Write-Error "❌ install.ps1 not found in $ToolkitDir"
            exit 1
        }
        $hasTarget = $false
        foreach ($a in $RemainingArgs) {
            if ($a -in @('-t', '-Target', '--target')) {
                $hasTarget = $true
                break
            }
        }
        $currentDir = (Get-Location).Path
        if (-not $RemainingArgs -or $RemainingArgs.Count -eq 0) {
            & $installScript -Target $currentDir -Tool all
        } else {
            $targetArg = if (-not $hasTarget) { "-Target '$currentDir'" } else { "" }
            $argString = ($RemainingArgs | ForEach-Object { if ($_ -match '[\s\$\`]') { "'$_'" } else { $_ } }) -join ' '
            Invoke-Expression "& '$installScript' $targetArg $argString"
        }
    }
    { $_ -in @('start', 'prime', 'session-starter') } {
        $script = Join-Path $ToolkitDir "skills/session-starter/scripts/prime_session.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('close', 'session-closer') } {
        $script = Join-Path $ToolkitDir "skills/session-closer/scripts/sync_context.py"
        & $py $script @RemainingArgs
    }
    'sync' {
        $script = Join-Path $ToolkitDir "skills/session-closer/scripts/sync_context.py"
        if ($RemainingArgs.Count -eq 0) {
            & $py $script --sync
        } else {
            & $py $script --sync $RemainingArgs[0]
        }
    }
    'check' {
        $script = Join-Path $ToolkitDir "skills/session-closer/scripts/sync_context.py"
        & $py $script --check @RemainingArgs
    }
    'status' {
        $script = Join-Path $ToolkitDir "skills/session-closer/scripts/sync_context.py"
        & $py $script --status @RemainingArgs
    }
    'profile' {
        $script = Join-Path $ToolkitDir "skills/context-optimizer/scripts/compress_context.py"
        & $py $script --profile @RemainingArgs
    }
    'skeleton' {
        $script = Join-Path $ToolkitDir "skills/context-optimizer/scripts/compress_context.py"
        if ($RemainingArgs.Count -eq 0) {
            & $py $script --skeleton
        } elseif (Test-Path $RemainingArgs[0]) {
            & $py $script --file $RemainingArgs[0] --skeleton
        } else {
            & $py $script --skeleton @RemainingArgs
        }
    }
    'pack' {
        $script = Join-Path $ToolkitDir "skills/context-optimizer/scripts/compress_context.py"
        & $py $script --hybrid @RemainingArgs
    }
    { $_ -in @('review', 'code-review') } {
        $script = Join-Path $ToolkitDir "skills/code-reviewer/scripts/review_code.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('test-gen', 'scaffold-tests') } {
        $script = Join-Path $ToolkitDir "skills/test-engineer/scripts/scaffold_tests.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('adr', 'architect') } {
        $script = Join-Path $ToolkitDir "skills/system-architect/scripts/manage_adr.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('audit', 'security') } {
        $script = Join-Path $ToolkitDir "skills/security-auditor/scripts/audit_security.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('pr', 'pr-prep') } {
        $script = Join-Path $ToolkitDir "skills/pr-prep/scripts/audit_pr.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('db', 'database') } {
        $script = Join-Path $ToolkitDir "skills/database-engineer/scripts/verify_migrations.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('debug', 'bisect', 'debugger') } {
        $script = Join-Path $ToolkitDir "skills/debugger/scripts/bisect_debugger.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('doc-check', 'drift') } {
        $script = Join-Path $ToolkitDir "skills/doc-sync/scripts/check_doc_drift.py"
        & $py $script --dir . --check @RemainingArgs
    }
    { $_ -in @('docker', 'container') } {
        $script = Join-Path $ToolkitDir "skills/container-engineer/scripts/harden_docker.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('ci', 'pipeline') } {
        $script = Join-Path $ToolkitDir "skills/ci-workflow/scripts/synthesize_ci.py"
        & $py $script @RemainingArgs
    }
    { $_ -in @('dep', 'deps', 'dependencies') } {
        $script = Join-Path $ToolkitDir "skills/dependency-auditor/scripts/audit_deps.py"
        & $py $script @RemainingArgs
    }
    'release' {
        $script = Join-Path $ToolkitDir "skills/release-manager/scripts/manage_release.py"
        & $py $script @RemainingArgs
    }
    'list' {
        $installScript = Join-Path $ToolkitDir "install.ps1"
        & $installScript -List
    }
    { $_ -in @('installs', 'list-installs', 'registry') } {
        $manageScript = Join-Path $ToolkitDir "scripts/manage_installs.py"
        & $py $manageScript --list @RemainingArgs
    }
    'update' {
        $updateAll = $false
        $remaining = @()
        foreach ($arg in $RemainingArgs) {
            if ($arg -in @('--all', '-a', '-All')) {
                $updateAll = $true
            } else {
                $remaining += $arg
            }
        }

        Write-Host "🔄 Updating agent-toolkit repository..."
        git -C $ToolkitDir pull origin main
        Write-Host "✅ Toolkit repository updated."

        $manageScript = Join-Path $ToolkitDir "scripts/manage_installs.py"
        if ($updateAll) {
            & $py $manageScript --update-all
        } else {
            if ((Test-Path ".agents") -or (Test-Path ".claude") -or (Test-Path ".cursor") -or (Test-Path ".github")) {
                Write-Host "📦 Refreshing configurations in current project..."
                $installScript = Join-Path $ToolkitDir "install.ps1"
                & $installScript -Target (Get-Location).Path -Tool all @remaining
            }
            & $py $manageScript --hint-summary 2>$null
        }
    }
    'test' {
        $testsDir = Join-Path $ToolkitDir "tests"
        & $py -m unittest discover -s $testsDir @RemainingArgs
    }
    { $_ -in @('link', 'setup') } {
        Setup-Link
    }
    { $_ -in @('version', '-v', '--version') } {
        Write-Host "agent-toolkit (atk) v1.0.0"
        Write-Host "Root: $ToolkitDir"
    }
    default {
        Write-Host "❌ Unknown command: $Command`n" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
