#!/usr/bin/env pwsh
<#
.SYNOPSIS
    install.ps1 — Installs, symlinks, or exports agent skills, subagents, and multi-tool adapters.

.DESCRIPTION
    PowerShell installer for Agent Toolkit across Google Antigravity, Claude Code, Cursor, Copilot, Roo, and Windsurf.
#>

[CmdletBinding()]
param(
    [Alias('t')]
    [string]$Target,

    [string]$Tool,

    [Alias('s')]
    [string]$Skill,

    [Alias('a')]
    [string]$Agent,

    [switch]$All,

    [Alias('m')]
    [ValidateSet('symlink', 'copy')]
    [string]$Mode = 'symlink',

    [Alias('g', 'link')]
    [switch]$Global,

    [Alias('u')]
    [switch]$Update,

    [Alias('l')]
    [switch]$List,

    [Alias('h')]
    [switch]$Help,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs = @()
)

$ErrorActionPreference = 'Stop'

# Pre-process remaining arguments for POSIX style flags (--target, --tool, etc.)
$i = 0
while ($i -lt $RemainingArgs.Count) {
    $arg = $RemainingArgs[$i]
    switch -Regex ($arg) {
        '^--target$'  { $Target = $RemainingArgs[++$i] }
        '^--tool$'    { $Tool   = $RemainingArgs[++$i] }
        '^--skill$'   { $Skill  = $RemainingArgs[++$i] }
        '^--agent$'   { $Agent  = $RemainingArgs[++$i] }
        '^--all$'     { $All    = $true }
        '^--mode$'    { $Mode   = $RemainingArgs[++$i] }
        '^--(global|link)$' { $Global = $true }
        '^--update$'  { $Update = $true }
        '^--list$'    { $List   = $true }
        '^--help$'    { $Help   = $true }
    }
    $i++
}

# Resolve Toolkit Directory
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
        $Tgt = $Item.Target
        if (-not [System.IO.Path]::IsPathRooted($Tgt)) {
            $Tgt = Join-Path (Split-Path -Parent $Item.FullName) $Tgt
        }
        $Item = Get-Item -LiteralPath $Tgt -ErrorAction SilentlyContinue
    }
    if ($Item) {
        $ScriptPath = $Item.FullName
    }
}

$ScriptDir = Split-Path -Parent $ScriptPath
$SkillsDir = Join-Path $ScriptDir "skills"
$AgentsDir = Join-Path $ScriptDir "agents"
$ExportScript = Join-Path $ScriptDir "scripts/export_adapters.py"

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

function Show-Usage {
    @"
Usage: install.ps1 [options]

Options:
  -Target <path>, -t       Target project repository path (default: current directory)
  -Tool <name>             Export configurations for a specific AI assistant:
                           all, claude, cursor, copilot, roo, windsurf, antigravity
  -Skill <name>, -s        Install specific skill by name (e.g., session-closer)
  -Agent <name>, -a        Install specific agent by name (e.g., software_engineer)
  -All                     Install all available skills and agents (.agents/)
  -Mode <symlink|copy>, -m Installation mode (default: symlink)
  -Global, -g, -link       Install global 'atk' CLI launcher & configure PowerShell profile
  -Update, -u              Pull latest toolkit updates from origin main
  -List, -l                List available skills and agents
  -Help, -h                Display this help message

Examples:
  .\install.ps1 -List
  .\install.ps1 -Global
  .\install.ps1 -Update
  .\install.ps1 -Target C:\path\to\my-project -Tool all
  .\install.ps1 -Target C:\path\to\my-project -Tool claude
  .\install.ps1 -Target C:\path\to\my-project -Tool cursor
  .\install.ps1 -Target C:\path\to\my-project -All
  .\install.ps1 -Target C:\path\to\my-project -Skill session-closer
"@
}

function Show-Components {
    Write-Host "📦 Agent Toolkit — Available Components:`n"
    Write-Host "Skills ($SkillsDir):"
    if (Test-Path $SkillsDir) {
        Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object {
            Write-Host "  • $($_.Name)"
        }
    } else {
        Write-Host "  (None found)"
    }

    Write-Host "`nSubagents ($AgentsDir):"
    if (Test-Path $AgentsDir) {
        Get-ChildItem -Path $AgentsDir -Directory | ForEach-Object {
            Write-Host "  • $($_.Name)"
        }
    } else {
        Write-Host "  (None found)"
    }

    Write-Host "`nSupported AI Tools (-Tool <name>):"
    Write-Host "  • all          (Configures all tools simultaneously)"
    Write-Host "  • claude       (Claude Code: .claude/commands/, CLAUDE.md)"
    Write-Host "  • cursor       (Cursor: .cursor/rules/*.mdc, .cursorrules)"
    Write-Host "  • copilot      (GitHub Copilot: .github/copilot-instructions.md, prompts/)"
    Write-Host "  • roo          (Roo Code / Cline / OpenCode: .roomodes, .clinerules)"
    Write-Host "  • windsurf     (Windsurf: .windsurfrules)"
    Write-Host "  • antigravity  (Google Antigravity & Gemini CLI: .agents/)"
}

function Install-Item {
    param(
        [string]$Src,
        [string]$DestDir,
        [string]$Name
    )

    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }

    $Dest = Join-Path $DestDir $Name

    if (Test-Path $Dest) {
        Remove-Item -LiteralPath $Dest -Recurse -Force
    }

    if ($Mode -eq 'symlink') {
        try {
            New-Item -ItemType SymbolicLink -Path $Dest -Target $Src -Force | Out-Null
            Write-Host "🔗 Symlinked $Name -> $Dest"
        } catch {
            Copy-Item -LiteralPath $Src -Destination $Dest -Recurse -Force
            Write-Host "📋 Copied $Name -> $Dest (symlink unavailable)"
        }
    } else {
        Copy-Item -LiteralPath $Src -Destination $Dest -Recurse -Force
        Write-Host "📋 Copied $Name -> $Dest"
    }
}

function Configure-PowerShellProfile {
    param([string]$ToolkitRoot)

    $profilePath = $PROFILE.CurrentUserCurrentHost
    if (-not $profilePath) {
        $profilePath = $PROFILE
    }
    if (-not $profilePath) {
        $homeDir = if ($env:HOME) { $env:HOME } else { $env:USERPROFILE }
        $profilePath = Join-Path $homeDir ".config/powershell/Microsoft.PowerShell_profile.ps1"
    }

    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }

    $atkPs1 = Join-Path $ToolkitRoot "bin/atk.ps1"
    $normalizedAtk = $atkPs1.Replace("\", "/")

    $startMarker = "# >>> agent-toolkit initialize >>>"
    $endMarker = "# <<< agent-toolkit initialize <<<"

    $block = @"
$startMarker
function atk { & "$normalizedAtk" @args }
function agent-toolkit { & "$normalizedAtk" @args }
$endMarker
"@

    $existingContent = ""
    if (Test-Path $profilePath) {
        $existingContent = Get-Content -LiteralPath $profilePath -Raw -Encoding utf8
    }

    if ($existingContent -and ($existingContent -match [regex]::Escape($startMarker))) {
        $pattern = "(?s)" + [regex]::Escape($startMarker) + ".*?" + [regex]::Escape($endMarker)
        $newContent = [regex]::Replace($existingContent, $pattern, $block.Trim())
        Set-Content -LiteralPath $profilePath -Value $newContent -Encoding utf8
        Write-Host "🔄 Updated PowerShell profile: $profilePath"
    } else {
        $newContent = if ($existingContent -and $existingContent.Trim().Length -gt 0) {
            $existingContent.TrimEnd() + "`n`n" + $block.Trim() + "`n"
        } else {
            $block.Trim() + "`n"
        }
        Set-Content -LiteralPath $profilePath -Value $newContent -Encoding utf8
        Write-Host "✅ Configured PowerShell profile: $profilePath"
    }
}

function Setup-Global {
    $binSource = Join-Path $ScriptDir "bin/atk"
    $binSourcePs1 = Join-Path $ScriptDir "bin/atk.ps1"
    $homeDir = if ($env:HOME) { $env:HOME } else { $env:USERPROFILE }
    $targetDir = Join-Path $homeDir ".local/bin"

    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    if (Test-Path $binSource) {
        $destAtk = Join-Path $targetDir "atk"
        $destAgentToolkit = Join-Path $targetDir "agent-toolkit"
        try {
            if (Test-Path $destAtk) { Remove-Item $destAtk -Force }
            New-Item -ItemType SymbolicLink -Path $destAtk -Target $binSource -Force | Out-Null
            if (Test-Path $destAgentToolkit) { Remove-Item $destAgentToolkit -Force }
            New-Item -ItemType SymbolicLink -Path $destAgentToolkit -Target $binSource -Force | Out-Null
        } catch {
            Copy-Item -LiteralPath $binSource -Destination $destAtk -Force
            Copy-Item -LiteralPath $binSource -Destination $destAgentToolkit -Force
        }
    }

    if (Test-Path $binSourcePs1) {
        $destAtkPs1 = Join-Path $targetDir "atk.ps1"
        $destAgentToolkitPs1 = Join-Path $targetDir "agent-toolkit.ps1"
        try {
            if (Test-Path $destAtkPs1) { Remove-Item $destAtkPs1 -Force }
            New-Item -ItemType SymbolicLink -Path $destAtkPs1 -Target $binSourcePs1 -Force | Out-Null
            if (Test-Path $destAgentToolkitPs1) { Remove-Item $destAgentToolkitPs1 -Force }
            New-Item -ItemType SymbolicLink -Path $destAgentToolkitPs1 -Target $binSourcePs1 -Force | Out-Null
        } catch {
            Copy-Item -LiteralPath $binSourcePs1 -Destination $destAtkPs1 -Force
            Copy-Item -LiteralPath $binSourcePs1 -Destination $destAgentToolkitPs1 -Force
        }
    }

    Write-Host "✅ Installed global 'atk' and 'agent-toolkit' into $targetDir"
    Configure-PowerShellProfile -ToolkitRoot $ScriptDir
}

if ($Help) {
    Show-Usage
    exit 0
}

if ($List) {
    Show-Components
    exit 0
}

if ($Update) {
    Write-Host "🔄 Updating agent-toolkit repository..."
    git -C $ScriptDir pull origin main
    Write-Host "✅ Repository updated."
    if (-not $Tool -and -not $All -and -not $Skill -and -not $Agent -and -not $Global) {
        exit 0
    }
}

if ($Global) {
    Setup-Global
    if (-not $Tool -and -not $All -and -not $Skill -and -not $Agent) {
        exit 0
    }
}

if (-not $Target) {
    $Target = (Get-Location).Path
}

# Resolve target path
if (-not (Test-Path $Target)) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
}
$Target = (Resolve-Path -Path $Target).Path
$TargetAgentsDir = Join-Path $Target ".agents"

# 1. Handle Tool adapter export
if ($Tool) {
    if (-not (Test-Path $ExportScript)) {
        Write-Error "❌ Export script not found: $ExportScript"
        exit 1
    }
    $py = Get-Python
    & $py $ExportScript --target $Target --tool $Tool --mode $Mode
    exit 0
}

# 2. Handle native .agents/ installation
Write-Host "🎯 Target repository: $Target"
Write-Host "⚙️ Mode: $Mode"

if ($All) {
    if (Test-Path $SkillsDir) {
        Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object {
            Install-Item -Src $_.FullName -DestDir (Join-Path $TargetAgentsDir "skills") -Name $_.Name
        }
    }
    if (Test-Path $AgentsDir) {
        Get-ChildItem -Path $AgentsDir -Directory | ForEach-Object {
            Install-Item -Src $_.FullName -DestDir (Join-Path $TargetAgentsDir "agents") -Name $_.Name
        }
    }

    $hooksFile = Join-Path $ScriptDir "hooks/hooks.json"
    if (Test-Path $hooksFile) {
        Install-Item -Src $hooksFile -DestDir $TargetAgentsDir -Name "hooks.json"
    }

    $mcpFile = Join-Path $ScriptDir "mcp/mcp_config.json"
    if (Test-Path $mcpFile) {
        Install-Item -Src $mcpFile -DestDir $TargetAgentsDir -Name "mcp_config.json"
    }

    $scriptsFolder = Join-Path $ScriptDir "scripts"
    if (Test-Path $scriptsFolder) {
        Install-Item -Src $scriptsFolder -DestDir $TargetAgentsDir -Name "scripts"
    }

    Write-Host "✅ Successfully installed all components to $Target/.agents"
    exit 0
}

if ($Skill) {
    $src = Join-Path $SkillsDir $Skill
    if (-not (Test-Path $src)) {
        Write-Error "❌ Skill '$Skill' not found in $SkillsDir"
        exit 1
    }
    Install-Item -Src $src -DestDir (Join-Path $TargetAgentsDir "skills") -Name $Skill
}

if ($Agent) {
    $src = Join-Path $AgentsDir $Agent
    if (-not (Test-Path $src)) {
        Write-Error "❌ Agent '$Agent' not found in $AgentsDir"
        exit 1
    }
    Install-Item -Src $src -DestDir (Join-Path $TargetAgentsDir "agents") -Name $Agent
}

if (-not $Skill -and -not $Agent) {
    Write-Warning "No action specified. Use -Tool <name>, -All, -Skill <name>, or -Agent <name>."
    Show-Usage
    exit 1
}

Write-Host "✨ Done."
