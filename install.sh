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
  -g, --global, --link     Install global 'atk' CLI launcher into ~/.local/bin
  -u, --update             Pull latest toolkit updates from origin main
  -l, --list               List available skills and agents
  -h, --help               Display this help message

Examples:
  $(basename "$0") --list
  $(basename "$0") --global
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

setup_global() {
    local bin_source="${SCRIPT_DIR}/bin/atk"
    local target_dir="${HOME}/.local/bin"
    if [ ! -f "${bin_source}" ]; then
        echo "❌ Global CLI launcher not found: ${bin_source}"
        exit 1
    fi
    mkdir -p "${target_dir}"
    ln -sf "${bin_source}" "${target_dir}/atk"
    ln -sf "${bin_source}" "${target_dir}/agent-toolkit"
    echo "✅ Successfully installed global 'atk' and 'agent-toolkit' into ${target_dir}"
    echo "   Ensure ${target_dir} is in your PATH."
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
    if [ -z "${TARGET_TOOL}" ] && [ "${INSTALL_ALL}" = false ] && [ -z "${INSTALL_SKILL}" ] && [ -z "${INSTALL_AGENT}" ] && [ "${INSTALL_GLOBAL}" = false ]; then
        exit 0
    fi
fi

if [ "${INSTALL_GLOBAL}" = true ]; then
    setup_global
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
