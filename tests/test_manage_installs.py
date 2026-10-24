#!/usr/bin/env python3
"""
Unit tests for manage_installs.py — Project Installation Registry & Multi-Project Updater.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.manage_installs import (
    detect_project_config,
    discover_projects,
    get_registry_path,
    list_projects,
    load_registry,
    prune_registry,
    register_project,
    save_registry,
    unregister_project,
    update_all_projects,
)

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent


class TestManageInstalls(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="atk_test_installs_")
        self.registry_file = Path(self.test_dir) / "installs.json"
        self.proj_a = Path(self.test_dir) / "project_a"
        self.proj_b = Path(self.test_dir) / "project_b"
        self.proj_a.mkdir()
        self.proj_b.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_empty_registry(self):
        reg = load_registry(self.registry_file)
        self.assertEqual(reg["version"], "1.0.0")
        self.assertEqual(reg["installs"], {})

    def test_register_and_list_project(self):
        entry = register_project(
            self.proj_a,
            tool="cursor",
            mode="copy",
            registry_file=self.registry_file,
        )
        self.assertEqual(entry["path"], str(self.proj_a.resolve()))
        self.assertEqual(entry["tool"], "cursor")
        self.assertEqual(entry["mode"], "copy")

        projects = list_projects(self.registry_file)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["path"], str(self.proj_a.resolve()))
        self.assertTrue(projects[0]["exists"])

    def test_unregister_project(self):
        register_project(self.proj_a, registry_file=self.registry_file)
        register_project(self.proj_b, registry_file=self.registry_file)
        self.assertEqual(len(list_projects(self.registry_file)), 2)

        removed = unregister_project(self.proj_a, registry_file=self.registry_file)
        self.assertTrue(removed)
        projects = list_projects(self.registry_file)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["path"], str(self.proj_b.resolve()))

        # Unregistering nonexistent returns False
        self.assertFalse(unregister_project(self.proj_a, registry_file=self.registry_file))

    def test_prune_registry(self):
        register_project(self.proj_a, registry_file=self.registry_file)
        dead_path = Path(self.test_dir) / "deleted_project"
        dead_path.mkdir()
        register_project(dead_path, registry_file=self.registry_file)

        # Delete the folder
        shutil.rmtree(dead_path)

        pruned = prune_registry(self.registry_file)
        self.assertEqual(len(pruned), 1)
        self.assertEqual(pruned[0], str(dead_path.resolve()))

        remaining = list_projects(self.registry_file)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["path"], str(self.proj_a.resolve()))

    def test_update_all_projects_live(self):
        # Register real projects in test dir
        register_project(self.proj_a, tool="claude", mode="copy", registry_file=self.registry_file)
        register_project(self.proj_b, tool="cursor", mode="copy", registry_file=self.registry_file)

        results = update_all_projects(TOOLKIT_ROOT, registry_file=self.registry_file)
        self.assertEqual(results["total"], 2)
        self.assertEqual(len(results["updated"]), 2)
        self.assertEqual(len(results["failed"]), 0)

        # Check that adapter files actually got created in target project dirs
        self.assertTrue((self.proj_a / ".claude").exists())
        self.assertTrue((self.proj_b / ".cursor").exists())

    def test_detect_and_discover_projects(self):
        workspace = Path(self.test_dir) / "workspace"
        workspace.mkdir()
        existing_proj = workspace / "existing_app"
        existing_proj.mkdir()
        (existing_proj / ".roomodes").write_text("{}", encoding="utf-8")
        (existing_proj / ".windsurfrules").write_text("# rules", encoding="utf-8")

        cfg = detect_project_config(existing_proj)
        self.assertEqual(cfg, ("all", "symlink"))

        discovered = discover_projects(TOOLKIT_ROOT, search_dirs=[workspace], registry_file=self.registry_file)
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0]["path"], str(existing_proj.resolve()))
        self.assertEqual(discovered[0]["tool"], "all")


if __name__ == "__main__":
    unittest.main()
