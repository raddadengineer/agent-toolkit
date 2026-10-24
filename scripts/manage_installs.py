#!/usr/bin/env python3
"""
manage_installs.py — Global Project Installation Registry & Multi-Project Updater

Maintains a registry of all projects where agent-toolkit has been installed (~/.agent-toolkit/installs.json)
and provides batch updates across all registered repositories via 'atk update --all'.

Usage:
    python3 manage_installs.py --register /path/to/project [--tool all] [--mode symlink]
    python3 manage_installs.py --list
    python3 manage_installs.py --json
    python3 manage_installs.py --prune
    python3 manage_installs.py --unregister /path/to/project
    python3 manage_installs.py --update-all
    python3 manage_installs.py --hint-summary
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_toolkit_dir() -> Path:
    """Returns root directory of agent-toolkit."""
    return Path(__file__).resolve().parent.parent


def get_registry_path(custom_path: Optional[Path] = None) -> Path:
    """Returns path to registry file (~/.agent-toolkit/installs.json or custom override)."""
    if custom_path:
        return Path(custom_path).resolve()
    env_override = os.environ.get("AGENT_TOOLKIT_REGISTRY")
    if env_override:
        return Path(env_override).resolve()
    return Path.home() / ".agent-toolkit" / "installs.json"


def load_registry(registry_file: Optional[Path] = None) -> Dict[str, Any]:
    """Loads JSON registry from disk, returning default structure if missing."""
    reg_path = get_registry_path(registry_file)
    default_reg = {
        "version": "1.0.0",
        "installs": {},
    }
    if not reg_path.exists():
        return default_reg
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default_reg
        if "installs" not in data or not isinstance(data["installs"], dict):
            data["installs"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return default_reg


def save_registry(data: Dict[str, Any], registry_file: Optional[Path] = None):
    """Saves registry data to disk atomically."""
    reg_path = get_registry_path(registry_file)
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = reg_path.with_suffix(".tmp")
    temp_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp_file.replace(reg_path)


def is_temp_test_path(path_str: str) -> bool:
    """Returns True if the path looks like an automated unit test temporary directory."""
    markers = (
        "agent_toolkit_cli_test_",
        "agent_toolkit_pwsh_test_",
        "agent_toolkit_adapters_test_",
        "atk_test_installs_",
    )
    return any(m in path_str for m in markers)


def is_default_registry(registry_file: Optional[Path] = None) -> bool:
    """Returns True when operating on the user's real global registry."""
    return registry_file is None and not os.environ.get("AGENT_TOOLKIT_REGISTRY")


def detect_project_config(project_dir: Path) -> Optional[Tuple[str, str]]:
    """
    Inspects a directory for agent-toolkit installation markers.
    Returns (tool, mode) if detected, or None if not an agent-toolkit installation.
    """
    if not project_dir.is_dir():
        return None

    detected_tools = []
    if (
        (project_dir / ".agents" / "skills" / "session-starter").exists()
        or (project_dir / ".agents" / "skills" / "session-starter").is_symlink()
        or (project_dir / ".agents" / "hooks.json").exists()
        or (project_dir / ".agents" / "hooks.json").is_symlink()
    ):
        detected_tools.append("antigravity")
    if (project_dir / ".claude" / "commands" / "session-starter.md").exists():
        detected_tools.append("claude")
    if (project_dir / ".cursor" / "rules" / "engineering-standards.mdc").exists():
        detected_tools.append("cursor")
    if (project_dir / ".github" / "prompts" / "session-starter.prompt.md").exists():
        detected_tools.append("copilot")
    if (project_dir / ".roomodes").exists():
        detected_tools.append("roo")
    if (project_dir / ".windsurfrules").exists():
        detected_tools.append("windsurf")

    if not detected_tools:
        return None

    tool = "all" if len(detected_tools) > 1 else detected_tools[0]

    # Determine symlink vs copy mode from .agents artifacts if present
    mode = "symlink"
    hooks_path = project_dir / ".agents" / "hooks.json"
    starter_path = project_dir / ".agents" / "skills" / "session-starter"
    if hooks_path.is_symlink() or starter_path.is_symlink():
        mode = "symlink"
    elif hooks_path.exists() or starter_path.exists():
        mode = "copy"

    return tool, mode


def discover_projects(
    toolkit_dir: Path,
    search_dirs: Optional[List[Path]] = None,
    registry_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Scans sibling project directories (e.g. parent of toolkit_dir) for existing
    agent-toolkit installations and registers any missing projects.
    """
    if search_dirs is None:
        parent = toolkit_dir.resolve().parent
        search_dirs = [parent] if parent.is_dir() else []

    data = load_registry(registry_file)
    discovered = []

    for base_dir in search_dirs:
        if not base_dir.is_dir():
            continue
        try:
            children = sorted(base_dir.iterdir())
        except OSError:
            continue

        for child in children:
            if not child.is_dir() or child.name.startswith("."):
                continue
            try:
                resolved = str(child.resolve())
            except OSError:
                continue

            if is_default_registry(registry_file) and is_temp_test_path(resolved):
                continue

            if resolved in data["installs"]:
                continue

            detected = detect_project_config(child)
            if detected:
                tool, mode = detected
                entry = register_project(child, tool=tool, mode=mode, registry_file=registry_file)
                if entry:
                    discovered.append(entry)
                    data = load_registry(registry_file)

    return discovered


def register_project(
    target: Path,
    tool: str = "all",
    mode: str = "symlink",
    registry_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """Registers or updates a project in the global installation registry."""
    target_path = Path(target)
    if str(target).startswith("-") or not target_path.exists():
        return {}
    resolved_target = str(target_path.resolve())
    if is_default_registry(registry_file) and is_temp_test_path(resolved_target):
        return {}
    data = load_registry(registry_file)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    existing = data["installs"].get(resolved_target)
    installed_at = existing.get("installed_at", now_iso) if existing else now_iso

    entry = {
        "path": resolved_target,
        "tool": tool,
        "mode": mode,
        "installed_at": installed_at,
        "last_updated": now_iso,
    }
    data["installs"][resolved_target] = entry
    save_registry(data, registry_file)
    return entry


def unregister_project(target: Path, registry_file: Optional[Path] = None) -> bool:
    """Removes a project from the installation registry."""
    resolved_target = str(Path(target).resolve())
    data = load_registry(registry_file)
    if resolved_target in data["installs"]:
        del data["installs"][resolved_target]
        save_registry(data, registry_file)
        return True
    return False


def prune_registry(registry_file: Optional[Path] = None) -> List[str]:
    """Prunes project entries whose directories no longer exist on disk (or temp test paths in default registry)."""
    data = load_registry(registry_file)
    default_reg = is_default_registry(registry_file)
    pruned = []
    for path_str in list(data["installs"].keys()):
        if not Path(path_str).is_dir() or (default_reg and is_temp_test_path(path_str)):
            pruned.append(path_str)
            del data["installs"][path_str]
    if pruned:
        save_registry(data, registry_file)
    return pruned


def list_projects(registry_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns list of registered projects with an 'exists' indicator."""
    data = load_registry(registry_file)
    projects = []
    for path_str, entry in sorted(data["installs"].items()):
        rec = dict(entry)
        rec["exists"] = Path(path_str).is_dir()
        projects.append(rec)
    return projects


def update_single_project(
    project_path: Path,
    tool: str,
    mode: str,
    toolkit_dir: Path,
    registry_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Executes export_adapters.py for a registered project."""
    export_script = toolkit_dir / "scripts" / "export_adapters.py"
    if not export_script.exists():
        return False, f"Export script not found: {export_script}"

    cmd = [
        sys.executable,
        str(export_script),
        "--target",
        str(project_path),
        "--tool",
        tool,
        "--mode",
        mode,
    ]
    env = dict(os.environ)
    if registry_file is not None:
        env["AGENT_TOOLKIT_REGISTRY"] = str(Path(registry_file).resolve())
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
        if proc.returncode == 0:
            return True, "Updated successfully"
        err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Process failed with exit code {proc.returncode}"
        return False, err_msg
    except Exception as exc:
        return False, str(exc)


def update_all_projects(
    toolkit_dir: Path,
    registry_file: Optional[Path] = None,
    discover: Optional[bool] = None,
) -> Dict[str, Any]:
    """Updates all registered project installations across the machine."""
    pruned = prune_registry(registry_file)
    should_discover = is_default_registry(registry_file) if discover is None else discover
    discovered = discover_projects(toolkit_dir, registry_file=registry_file) if should_discover else []
    projects = list_projects(registry_file)

    results = {
        "total": len(projects),
        "updated": [],
        "failed": [],
        "pruned": pruned,
        "discovered": discovered,
    }

    if not projects:
        return results

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for proj in projects:
        target_path = Path(proj["path"])
        tool = proj.get("tool", "all")
        mode = proj.get("mode", "symlink")

        success, msg = update_single_project(target_path, tool, mode, toolkit_dir, registry_file=registry_file)
        if success:
            results["updated"].append({"path": str(target_path), "tool": tool, "mode": mode})
        else:
            results["failed"].append({"path": str(target_path), "error": msg})

    data = load_registry(registry_file)
    for item in results["updated"]:
        if item["path"] in data["installs"]:
            data["installs"][item["path"]]["last_updated"] = now_iso
    save_registry(data, registry_file)
    return results


def print_hint_summary(registry_file: Optional[Path] = None):
    """Prints a friendly one-line hint if there are registered projects."""
    if is_default_registry(registry_file):
        discover_projects(get_toolkit_dir(), registry_file=registry_file)
    projects = list_projects(registry_file)
    active_count = sum(1 for p in projects if p.get("exists", False))
    if active_count > 1:
        print(f"\n💡 Tip: You have {active_count} registered projects. Run 'atk update --all' to refresh all of them.")


def main():
    parser = argparse.ArgumentParser(description="Manage agent-toolkit project installation registry.")
    parser.add_argument("--register", metavar="PATH", help="Register a project installation path")
    parser.add_argument("--tool", default="all", help="Tool adapters installed (default: all)")
    parser.add_argument("--mode", default="symlink", choices=["symlink", "copy"], help="Installation mode (default: symlink)")
    parser.add_argument("--unregister", metavar="PATH", help="Unregister a project path")
    parser.add_argument("--discover", action="store_true", help="Auto-discover existing sibling project installations")
    parser.add_argument("--list", action="store_true", help="List all registered project installations")
    parser.add_argument("--json", action="store_true", help="Output registered projects in JSON format")
    parser.add_argument("--prune", action="store_true", help="Prune non-existent paths from registry")
    parser.add_argument("--update-all", action="store_true", help="Update all registered project installations")
    parser.add_argument("--hint-summary", action="store_true", help="Print hint summary if projects exist")
    parser.add_argument("--registry-file", metavar="FILE", help="Override default registry file path")

    args = parser.parse_args()
    custom_reg = Path(args.registry_file) if args.registry_file else None
    toolkit_dir = get_toolkit_dir()

    if args.register:
        target = Path(args.register)
        entry = register_project(target, tool=args.tool, mode=args.mode, registry_file=custom_reg)
        if entry:
            print("✅ Registered project in agent-toolkit registry:")
            print(f"   • Path: {entry['path']}")
            print(f"   • Tool: {entry['tool']}")
            print(f"   • Mode: {entry['mode']}")
        sys.exit(0)

    if args.unregister:
        target = Path(args.unregister)
        removed = unregister_project(target, registry_file=custom_reg)
        if removed:
            print(f"✅ Unregistered project: {target.resolve()}")
        else:
            print(f"⚠️ Project not found in registry: {target.resolve()}")
        sys.exit(0)

    if args.discover:
        discovered = discover_projects(toolkit_dir, registry_file=custom_reg)
        if discovered:
            print(f"🔍 Discovered and registered {len(discovered)} project(s):")
            for d in discovered:
                print(f"   • {d['path']} (tool: {d['tool']}, mode: {d['mode']})")
        else:
            print("ℹ️ No new unregistered sibling projects found.")
        sys.exit(0)

    if args.prune:
        pruned = prune_registry(registry_file=custom_reg)
        if pruned:
            print(f"🧹 Pruned {len(pruned)} dead installation(s) from registry:")
            for p in pruned:
                print(f"   • {p}")
        else:
            print("✨ All registered installations exist on disk. Nothing to prune.")
        sys.exit(0)

    if args.hint_summary:
        print_hint_summary(registry_file=custom_reg)
        sys.exit(0)

    if args.update_all:
        print("🔄 Updating all registered agent-toolkit installations across system...\n")
        results = update_all_projects(toolkit_dir, registry_file=custom_reg)

        if results.get("discovered"):
            print(f"🔍 Auto-discovered {len(results['discovered'])} existing project installation(s):")
            for d in results["discovered"]:
                print(f"   • {d['path']} (tool: {d['tool']}, mode: {d['mode']})")
            print("")

        if results["pruned"]:
            print(f"🧹 Pruned {len(results['pruned'])} removed project(s):")
            for p in results["pruned"]:
                print(f"   • {p}")
            print("")

        if results["total"] == 0:
            print("ℹ️ No registered projects found in registry (~/.agent-toolkit/installs.json).")
            print("   Run 'atk install' inside any project to register it.")
            sys.exit(0)

        for item in results["updated"]:
            print(f"✅ Updated: {item['path']} (tool: {item['tool']}, mode: {item['mode']})")

        for item in results["failed"]:
            print(f"❌ Failed:  {item['path']} — {item['error']}")

        print(f"\n✨ Completed: {len(results['updated'])}/{results['total']} projects updated successfully.")
        sys.exit(0 if not results["failed"] else 1)

    if is_default_registry(custom_reg):
        prune_registry(registry_file=custom_reg)
        discover_projects(toolkit_dir, registry_file=custom_reg)

    if args.json:
        projects = list_projects(registry_file=custom_reg)
        print(json.dumps(projects, indent=2))
        sys.exit(0)

    # Default to list
    projects = list_projects(registry_file=custom_reg)
    if not projects:
        print("ℹ️ No projects registered yet in ~/.agent-toolkit/installs.json.")
        print("   Run 'atk install' inside any project to register it.")
        sys.exit(0)

    print(f"📋 Registered agent-toolkit installations ({len(projects)}):\n")
    for proj in projects:
        status_icon = "✅" if proj["exists"] else "❌ (missing)"
        print(f"  {status_icon} {proj['path']}")
        print(f"     • Tool: {proj.get('tool', 'all')} | Mode: {proj.get('mode', 'symlink')}")
        print(f"     • Last Updated: {proj.get('last_updated', 'unknown')}")
    print("\nRun 'atk update --all' to refresh all registered installations.")


if __name__ == "__main__":
    main()
