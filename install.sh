#!/usr/bin/env bash
#
# install.sh — Installs, symlinks, or exports agent skills, subagents, and multi-tool adapters.
#
# Usage:
#   ./install.sh --list
#   ./install.sh --target /path/to/my-repo --tool all
#   ./install.sh --target /path/to/my-repo --tool claude
#   ./install.sh --target /path/to/my-repo --tool cursor
#   ./install.sh --target /path/to/my-repo --all
#   ./install.sh --target /path/to/my-repo --skill session-closer
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SCRIPT_DIR}/skills"
AGENTS_DIR="${SCRIPT_DIR}/agents"
EXPORT_SCRIPT="${SCRIPT_DIR}/scripts/export_adapters.py"

TARGET_DIR=""
MODE="symlink" # "symlink" or "copy"
INSTALL_SKILL=""
INSTALL_AGENT=""
INSTALL_ALL=false
TARGET_TOOL=""
LIST_ONLY=false
INSTALL_GLOBAL=false
INSTALL_POWERSHELL=false
UPDATE_REPO=false

print_usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -t, --target <path>      Target project repository path (default: current directory)
      --tool <name>        Export configurations for a specific AI assistant:
                           all, claude, cursor, copilot, roo, windsurf, antigravity
  -s, --skill <name>       Install specific skill by name (e.g., session-closer)
  -a, --agent <name>       Install specific agent by name (e.g., software_engineer)
      --all                Install all available skills and agents (.agents/)
  -m, --mode <symlink|copy>
                           Installation mode (default: symlink)
  -g, --global, --link     Install global 'atk' CLI launcher into ~/.local/bin and configure shell profiles
  -p, --powershell         Configure PowerShell profile with 'atk' and 'agent-toolkit' functions
  -u, --update             Pull latest toolkit updates from origin main
  -l, --list               List available skills and agents
  -h, --help               Display this help message

Examples:
  $(basename "$0") --list
  $(basename "$0") --global
  $(basename "$0") --powershell
  $(basename "$0") --update
  $(basename "$0") --target /path/to/my-project --tool all
  $(basename "$0") --target /path/to/my-project --tool claude
  $(basename "$0") --target /path/to/my-project --tool cursor
  $(basename "$0") --target /path/to/my-project --all
  $(basename "$0") --target /path/to/my-project --skill session-closer
EOF
}

list_components() {
    echo "📦 Agent Toolkit — Available Components:"
    echo ""
    echo "Skills (${SKILLS_DIR}):"
    if [ -d "${SKILLS_DIR}" ]; then
        for s in "${SKILLS_DIR}"/*; do
            if [ -d "$s" ]; then
                name="$(basename "$s")"
                desc=$(grep -m 1 "^description:" "$s/SKILL.md" 2>/dev/null | sed -e 's/^description:[[:space:]]*//' -e 's/>-//' || echo "No description")
                echo "  • ${name}"
            fi
        done
    else
        echo "  (None found)"
    fi

    echo ""
    echo "Subagents (${AGENTS_DIR}):"
    if [ -d "${AGENTS_DIR}" ]; then
        for a in "${AGENTS_DIR}"/*; do
            if [ -d "$a" ]; then
                name="$(basename "$a")"
                echo "  • ${name}"
            fi
        done
    else
        echo "  (None found)"
    fi

    echo ""
    echo "Supported AI Tools (--tool <name>):"
    echo "  • all          (Configures all tools simultaneously)"
    echo "  • claude       (Claude Code: .claude/commands/, CLAUDE.md)"
    echo "  • cursor       (Cursor: .cursor/rules/*.mdc, .cursorrules)"
    echo "  • copilot      (GitHub Copilot: .github/copilot-instructions.md, prompts/)"
    echo "  • roo          (Roo Code / Cline / OpenCode: .roomodes, .clinerules)"
    echo "  • windsurf     (Windsurf: .windsurfrules)"
    echo "  • antigravity  (Google Antigravity & Gemini CLI: .agents/)"
}

install_item() {
    local src="$1"
    local dest_dir="$2"
    local name="$3"
    local dest="${dest_dir}/${name}"

    mkdir -p "${dest_dir}"

    if [ -e "${dest}" ] || [ -L "${dest}" ]; then
        echo "⚠️ Target already exists: ${dest}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping ${name}."
            return
        fi
        rm -rf "${dest}"
    fi

    if [ "${MODE}" = "symlink" ]; then
        ln -s "${src}" "${dest}"
        echo "🔗 Symlinked ${name} -> ${dest}"
    else
        cp -R "${src}" "${dest}"
        echo "📋 Copied ${name} -> ${dest}"
    fi
}

setup_powershell() {
    local pwsh_bin=""
    if command -v pwsh >/dev/null 2>&1; then
        pwsh_bin="pwsh"
    elif command -v powershell >/dev/null 2>&1; then
        pwsh_bin="powershell"
    fi

    local profile_path=""
    if [ -n "${pwsh_bin}" ]; then
        profile_path=$(${pwsh_bin} -NoProfile -Command '$PROFILE' 2>/dev/null || echo "")
    fi

    if [ -z "${profile_path}" ]; then
        if [ -d "${HOME}/.config/powershell" ] || [ "${INSTALL_POWERSHELL}" = true ]; then
            profile_path="${HOME}/.config/powershell/Microsoft.PowerShell_profile.ps1"
        else
            return 0
        fi
    fi

    local atk_ps1="${SCRIPT_DIR}/bin/atk.ps1"
    if [ ! -f "${atk_ps1}" ]; then
        atk_ps1="${SCRIPT_DIR}/bin/atk"
    fi

    local profile_dir="$(dirname "${profile_path}")"
    mkdir -p "${profile_dir}"

    local start_marker="# >>> agent-toolkit initialize >>>"
    local end_marker="# <<< agent-toolkit initialize <<<"

    python3 -c "
import sys, re
path = sys.argv[1]
atk_script = sys.argv[2]
start = sys.argv[3]
end = sys.argv[4]

block = f'''{start}
function atk {{ & \"{atk_script}\" @args }}
function agent-toolkit {{ & \"{atk_script}\" @args }}
{end}'''

content = ''
try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    pass

pattern = re.escape(start) + r'.*?' + re.escape(end)
if re.search(pattern, content, flags=re.DOTALL):
    new_content = re.sub(pattern, block.strip(), content, flags=re.DOTALL)
    print(f'🔄 Updated PowerShell profile: {path}')
else:
    if content.strip():
        new_content = content.rstrip() + '\n\n' + block.strip() + '\n'
    else:
        new_content = block.strip() + '\n'
    print(f'✅ Configured PowerShell profile: {path}')

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
" "${profile_path}" "${atk_ps1}" "${start_marker}" "${end_marker}"
}

setup_global() {
    local bin_source="${SCRIPT_DIR}/bin/atk"
    local bin_source_ps1="${SCRIPT_DIR}/bin/atk.ps1"
    local target_dir="${HOME}/.local/bin"
    if [ ! -f "${bin_source}" ]; then
        echo "❌ Global CLI launcher not found: ${bin_source}"
        exit 1
    fi
    mkdir -p "${target_dir}"
    ln -sf "${bin_source}" "${target_dir}/atk"
    ln -sf "${bin_source}" "${target_dir}/agent-toolkit"
    if [ -f "${bin_source_ps1}" ]; then
        ln -sf "${bin_source_ps1}" "${target_dir}/atk.ps1"
        ln -sf "${bin_source_ps1}" "${target_dir}/agent-toolkit.ps1"
    fi
    echo "✅ Successfully installed global 'atk' and 'agent-toolkit' into ${target_dir}"
    echo "   Ensure ${target_dir} is in your PATH."

    setup_powershell
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_DIR="$2"
            shift 2
            ;;
        --tool)
            TARGET_TOOL="$2"
            shift 2
            ;;
        -s|--skill)
            INSTALL_SKILL="$2"
            shift 2
            ;;
        -a|--agent)
            INSTALL_AGENT="$2"
            shift 2
            ;;
        --all)
            INSTALL_ALL=true
            shift
            ;;
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -g|--global|--link)
            INSTALL_GLOBAL=true
            shift
            ;;
        -p|--powershell)
            INSTALL_POWERSHELL=true
            shift
            ;;
        -u|--update)
            UPDATE_REPO=true
            shift
            ;;
        -l|--list)
            LIST_ONLY=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

if [ "${UPDATE_REPO}" = true ]; then
    echo "🔄 Updating agent-toolkit repository..."
    git -C "${SCRIPT_DIR}" pull origin main
    echo "✅ Repository updated."
    if [ -z "${TARGET_TOOL}" ] && [ "${INSTALL_ALL}" = false ] && [ -z "${INSTALL_SKILL}" ] && [ -z "${INSTALL_AGENT}" ] && [ "${INSTALL_GLOBAL}" = false ] && [ "${INSTALL_POWERSHELL}" = false ]; then
        exit 0
    fi
fi

if [ "${INSTALL_GLOBAL}" = true ]; then
    setup_global
    if [ -z "${TARGET_TOOL}" ] && [ "${INSTALL_ALL}" = false ] && [ -z "${INSTALL_SKILL}" ] && [ -z "${INSTALL_AGENT}" ] && [ "${INSTALL_POWERSHELL}" = false ]; then
        exit 0
    fi
fi

if [ "${INSTALL_POWERSHELL}" = true ]; then
    setup_powershell
    if [ -z "${TARGET_TOOL}" ] && [ "${INSTALL_ALL}" = false ] && [ -z "${INSTALL_SKILL}" ] && [ -z "${INSTALL_AGENT}" ]; then
        exit 0
    fi
fi

if [ "${LIST_ONLY}" = true ]; then
    list_components
    exit 0
fi

if [ -z "${TARGET_DIR}" ]; then
    TARGET_DIR="$(pwd)"
fi

TARGET_DIR="$(cd "${TARGET_DIR}" && pwd)"
TARGET_AGENTS_DIR="${TARGET_DIR}/.agents"

# 1. Handle --tool adapter export
if [ -n "${TARGET_TOOL}" ]; then
    if [ ! -f "${EXPORT_SCRIPT}" ]; then
        echo "❌ Export script not found: ${EXPORT_SCRIPT}"
        exit 1
    fi
    python3 "${EXPORT_SCRIPT}" --target "${TARGET_DIR}" --tool "${TARGET_TOOL}" --mode "${MODE}"
    exit 0
fi

# 2. Handle native .agents/ installation
echo "🎯 Target repository: ${TARGET_DIR}"
echo "⚙️ Mode: ${MODE}"

if [ "${INSTALL_ALL}" = true ]; then
    # Install all skills
    if [ -d "${SKILLS_DIR}" ]; then
        for s in "${SKILLS_DIR}"/*; do
            if [ -d "$s" ]; then
                name="$(basename "$s")"
                install_item "$s" "${TARGET_AGENTS_DIR}/skills" "$name"
            fi
        done
    fi

    # Install all agents
    if [ -d "${AGENTS_DIR}" ]; then
        for a in "${AGENTS_DIR}"/*; do
            if [ -d "$a" ]; then
                name="$(basename "$a")"
                install_item "$a" "${TARGET_AGENTS_DIR}/agents" "$name"
            fi
        done
    fi

    # Install hooks, MCP configuration, and shared scripts
    if [ -f "${SCRIPT_DIR}/hooks/hooks.json" ]; then
        install_item "${SCRIPT_DIR}/hooks/hooks.json" "${TARGET_AGENTS_DIR}" "hooks.json"
    fi
    if [ -f "${SCRIPT_DIR}/mcp/mcp_config.json" ]; then
        install_item "${SCRIPT_DIR}/mcp/mcp_config.json" "${TARGET_AGENTS_DIR}" "mcp_config.json"
    fi
    if [ -d "${SCRIPT_DIR}/scripts" ]; then
        install_item "${SCRIPT_DIR}/scripts" "${TARGET_AGENTS_DIR}" "scripts"
    fi

    echo "✅ Successfully installed all components to ${TARGET_DIR}/.agents"
    exit 0
fi

if [ -n "${INSTALL_SKILL}" ]; then
    src="${SKILLS_DIR}/${INSTALL_SKILL}"
    if [ ! -d "${src}" ]; then
        echo "❌ Skill '${INSTALL_SKILL}' not found in ${SKILLS_DIR}"
        exit 1
    fi
    install_item "${src}" "${TARGET_AGENTS_DIR}/skills" "${INSTALL_SKILL}"
fi

if [ -n "${INSTALL_AGENT}" ]; then
    src="${AGENTS_DIR}/${INSTALL_AGENT}"
    if [ ! -d "${src}" ]; then
        echo "❌ Agent '${INSTALL_AGENT}' not found in ${AGENTS_DIR}"
        exit 1
    fi
    install_item "${src}" "${TARGET_AGENTS_DIR}/agents" "${INSTALL_AGENT}"
fi

if [ -z "${INSTALL_SKILL}" ] && [ -z "${INSTALL_AGENT}" ]; then
    echo "⚠️ No action specified. Use --tool <name>, --all, --skill <name>, or --agent <name>."
    print_usage
    exit 1
fi

echo "✨ Done."
