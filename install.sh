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

ORIGINAL_ARGS=("$@")

SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
SCRIPT_DIR=""
if [ -n "${SCRIPT_SOURCE}" ] && [ -e "${SCRIPT_SOURCE}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd)"
fi

SKILLS_DIR="${SCRIPT_DIR:+${SCRIPT_DIR}/skills}"
AGENTS_DIR="${SCRIPT_DIR:+${SCRIPT_DIR}/agents}"
EXPORT_SCRIPT="${SCRIPT_DIR:+${SCRIPT_DIR}/scripts/export_adapters.py}"

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
WEB_INSTALL=false
CUSTOM_INSTALL_DIR=""

if [ -z "${SCRIPT_DIR}" ] || [ ! -d "${SCRIPT_DIR}/skills" ]; then
    WEB_INSTALL=true
fi

print_usage() {
    cat <<EOF
Usage: $(basename "${0:-install.sh}") [options]

Options:
  -w, --web                Install directly from web repository (clones/updates ~/.agent-toolkit)
      --install-dir <path> Custom central toolkit directory for web install (default: ~/.agent-toolkit)
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
  # Direct web installation (one-liner via curl):
  curl -fsSL https://raw.githubusercontent.com/raddadengineer/agent-toolkit/main/install.sh | bash

  # Local commands:
  $(basename "${0:-install.sh}") --list
  $(basename "${0:-install.sh}") --global
  $(basename "${0:-install.sh}") --powershell
  $(basename "${0:-install.sh}") --update
  $(basename "${0:-install.sh}") --target /path/to/my-project --tool all
  $(basename "${0:-install.sh}") --target /path/to/my-project --tool claude
  $(basename "${0:-install.sh}") --target /path/to/my-project --tool cursor
  $(basename "${0:-install.sh}") --target /path/to/my-project --all
  $(basename "${0:-install.sh}") --target /path/to/my-project --skill session-closer
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

setup_shell_path() {
    local target_dir="${HOME}/.local/bin"
    case ":${PATH}:" in
        *":${target_dir}:"*)
            return 0
            ;;
    esac

    local profiles=()
    [ -f "${HOME}/.zshrc" ] && profiles+=("${HOME}/.zshrc")
    [ -f "${HOME}/.bashrc" ] && profiles+=("${HOME}/.bashrc")
    [ -f "${HOME}/.bash_profile" ] && profiles+=("${HOME}/.bash_profile")

    for prof in ${profiles[@]+"${profiles[@]}"}; do
        if [ -f "${prof}" ]; then
            if ! grep -q "\.local/bin" "${prof}" 2>/dev/null; then
                echo '' >> "${prof}"
                echo '# Added by agent-toolkit' >> "${prof}"
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${prof}"
                echo "🔄 Added ${target_dir} to PATH in ${prof}"
            fi
        fi
    done
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

    setup_shell_path
    setup_powershell
}

handle_web_install() {
    local install_dir="${CUSTOM_INSTALL_DIR:-}"
    if [ -z "${install_dir}" ]; then
        if [ -n "${AGENT_TOOLKIT_DIR:-}" ]; then
            install_dir="${AGENT_TOOLKIT_DIR}"
        elif [ -d "${HOME}/agent-toolkit/.git" ]; then
            install_dir="${HOME}/agent-toolkit"
        elif [ -d "${HOME}/.agent-toolkit/.git" ]; then
            install_dir="${HOME}/.agent-toolkit"
        elif [ -d "${HOME}/agent-toolkit" ]; then
            install_dir="${HOME}/agent-toolkit"
        else
            install_dir="${HOME}/.agent-toolkit"
        fi
    fi

    local repo_url="${AGENT_TOOLKIT_REPO:-https://github.com/raddadengineer/agent-toolkit.git}"
    local repo_branch="${AGENT_TOOLKIT_BRANCH:-main}"

    echo "🌐 agent-toolkit — Direct Web Installer"
    echo "📁 Installation directory: ${install_dir}"

    if command -v git >/dev/null 2>&1; then
        if [ -d "${install_dir}/.git" ]; then
            echo "🔄 Existing repository found at ${install_dir}. Updating..."
            git -C "${install_dir}" pull origin "${repo_branch}" || true
        else
            echo "📥 Cloning ${repo_url} (branch: ${repo_branch})..."
            mkdir -p "$(dirname "${install_dir}")"
            git clone --depth 1 -b "${repo_branch}" "${repo_url}" "${install_dir}"
        fi
    else
        echo "📥 Downloading repository archive (${repo_branch})..."
        mkdir -p "${install_dir}"
        local archive_url="https://github.com/raddadengineer/agent-toolkit/archive/refs/heads/${repo_branch}.tar.gz"
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL "${archive_url}" | tar -xz --strip-components=1 -C "${install_dir}"
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- "${archive_url}" | tar -xz --strip-components=1 -C "${install_dir}"
        else
            echo "❌ Error: Neither git, curl, nor wget was found. Cannot download agent-toolkit."
            exit 1
        fi
    fi

    local target_script="${install_dir}/install.sh"
    if [ ! -f "${target_script}" ]; then
        echo "❌ Error: ${target_script} not found after download."
        exit 1
    fi
    chmod +x "${target_script}"

    local forward_args=()
    local skip_next=false
    for arg in ${ORIGINAL_ARGS[@]+"${ORIGINAL_ARGS[@]}"}; do
        if [ "${skip_next}" = true ]; then
            skip_next=false
            continue
        fi
        case "$arg" in
            -w|--web)
                continue
                ;;
            --install-dir)
                skip_next=true
                continue
                ;;
            --install-dir=*)
                continue
                ;;
            *)
                forward_args+=("$arg")
                ;;
        esac
    done

    local has_action=false
    for farg in ${forward_args[@]+"${forward_args[@]}"}; do
        case "$farg" in
            -t|--target|-s|--skill|-a|--agent|--all|--tool|-g|--global|--link|-p|--powershell|-u|--update|-l|--list)
                has_action=true
                ;;
        esac
    done

    if [ "${has_action}" = false ]; then
        forward_args+=("--global")
    fi

    echo "🚀 Running local installer: ${target_script} ${forward_args[*]:-}"
    exec bash "${target_script}" ${forward_args[@]+"${forward_args[@]}"}
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -w|--web)
            WEB_INSTALL=true
            shift
            ;;
        --install-dir)
            CUSTOM_INSTALL_DIR="$2"
            shift 2
            ;;
        --install-dir=*)
            CUSTOM_INSTALL_DIR="${1#*=}"
            shift
            ;;
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

if [ "${WEB_INSTALL}" = true ]; then
    handle_web_install
    exit 0
fi

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

    if [ -f "${SCRIPT_DIR}/scripts/manage_installs.py" ]; then
        python3 "${SCRIPT_DIR}/scripts/manage_installs.py" --register "${TARGET_DIR}" --tool "antigravity" --mode "${MODE}" >/dev/null 2>&1 || true
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
