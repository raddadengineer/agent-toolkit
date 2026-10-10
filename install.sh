#!/usr/bin/env bash
#
# install.sh — Installs or symlinks agent skills and subagents into target repositories.
#
# Usage:
#   ./install.sh --list
#   ./install.sh --target /path/to/my-repo --skill session-closer
#   ./install.sh --target /path/to/my-repo --all
#   ./install.sh --target /path/to/my-repo --mode copy --all
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SCRIPT_DIR}/skills"
AGENTS_DIR="${SCRIPT_DIR}/agents"

TARGET_DIR=""
MODE="symlink" # "symlink" or "copy"
INSTALL_SKILL=""
INSTALL_AGENT=""
INSTALL_ALL=false
LIST_ONLY=false

print_usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -t, --target <path>      Target project repository path (default: current directory)
  -s, --skill <name>       Install specific skill by name (e.g., session-closer)
  -a, --agent <name>       Install specific agent by name (e.g., software_engineer)
      --all                Install all available skills and agents
  -m, --mode <symlink|copy>
                           Installation mode (default: symlink)
  -l, --list               List available skills and agents
  -h, --help               Display this help message

Examples:
  $(basename "$0") --list
  $(basename "$0") --target ~/Dev-Projects/my-app --skill session-closer
  $(basename "$0") --target ~/Dev-Projects/my-app --all --mode copy
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

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_DIR="$2"
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

if [ "${LIST_ONLY}" = true ]; then
    list_components
    exit 0
fi

if [ -z "${TARGET_DIR}" ]; then
    TARGET_DIR="$(pwd)"
fi

TARGET_DIR="$(cd "${TARGET_DIR}" && pwd)"
TARGET_AGENTS_DIR="${TARGET_DIR}/.agents"

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
    echo "⚠️ No action specified. Use --all, --skill <name>, or --agent <name>."
    print_usage
    exit 1
fi

echo "✨ Done."
