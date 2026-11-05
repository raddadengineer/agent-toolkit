#!/usr/bin/env python3
"""
Unit tests for manage_memory.py (memory-manager skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import manage_memory


class TestManageMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_memory_scaffolds_categories_and_index(self):
        mem_dir = manage_memory.init_memory(self.repo_root, scope="project")
        self.assertTrue(mem_dir.exists())
        self.assertTrue((mem_dir / "patterns").is_dir())
        self.assertTrue((mem_dir / "anti-patterns").is_dir())
        self.assertTrue((mem_dir / "rules").is_dir())
        self.assertTrue((mem_dir / "decisions").is_dir())
        self.assertTrue((mem_dir / "index.json").exists())
        self.assertTrue((mem_dir / "README.md").exists())

    def test_record_and_recall_memory(self):
        entry = manage_memory.record_memory(
            repo_root=self.repo_root,
            title="Always Pin Docker Dependencies",
            category="rules",
            content="Use exact sha256 digests or semver tags rather than latest.",
            tags=["docker", "containers", "security"],
            scope="project",
        )

        self.assertEqual(entry["title"], "Always Pin Docker Dependencies")
        self.assertEqual(entry["category"], "rules")
        self.assertTrue((self.repo_root / "memory" / entry["path"]).exists())

        # Recall by tag
        matches = manage_memory.recall_memories(
            repo_root=self.repo_root,
            query="docker security",
            scope="project",
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], entry["id"])
        self.assertGreater(matches[0]["score"], 0)

        # Recall by content substring
        matches_content = manage_memory.recall_memories(
            repo_root=self.repo_root,
            query="sha256 digests",
            scope="project",
        )
        self.assertEqual(len(matches_content), 1)

    def test_list_and_filter_memories(self):
        manage_memory.record_memory(
            repo_root=self.repo_root,
            title="Pattern A",
            category="patterns",
            content="Content A",
            tags=["tag1"],
            scope="project",
        )
        manage_memory.record_memory(
            repo_root=self.repo_root,
            title="Rule B",
            category="rules",
            content="Content B",
            tags=["tag2"],
            scope="project",
        )

        all_items = manage_memory.list_memories(self.repo_root, scope="project")
        self.assertEqual(len(all_items), 2)

        pattern_items = manage_memory.list_memories(self.repo_root, category="patterns", scope="project")
        self.assertEqual(len(pattern_items), 1)
        self.assertEqual(pattern_items[0]["title"], "Pattern A")

        tagged_items = manage_memory.list_memories(self.repo_root, tag="tag2", scope="project")
        self.assertEqual(len(tagged_items), 1)
        self.assertEqual(tagged_items[0]["title"], "Rule B")

    def test_audit_memory_detects_and_repairs_issues(self):
        entry = manage_memory.record_memory(
            repo_root=self.repo_root,
            title="Original Title",
            category="patterns",
            content="Original content",
            scope="project",
        )

        # Verify clean baseline audit
        audit_clean = manage_memory.audit_memory(self.repo_root, scope="project")
        self.assertEqual(audit_clean["issues_count"], 0)

        # Modify file out-of-band to introduce checksum mismatch
        file_path = self.repo_root / "memory" / entry["path"]
        file_path.write_text("Modified content out of band", encoding="utf-8")

        audit_dirty = manage_memory.audit_memory(self.repo_root, scope="project")
        self.assertEqual(audit_dirty["issues_count"], 1)
        self.assertEqual(audit_dirty["issues"][0]["type"], "checksum_mismatch")

        # Repair audit issues
        audit_repaired = manage_memory.audit_memory(self.repo_root, scope="project", repair=True)
        self.assertTrue(audit_repaired["repaired"])

        # Check clean after repair
        audit_after = manage_memory.audit_memory(self.repo_root, scope="project")
        self.assertEqual(audit_after["issues_count"], 0)

    def test_get_memory_stats(self):
        manage_memory.record_memory(
            repo_root=self.repo_root,
            title="Dec 1",
            category="decisions",
            content="ADR note",
            scope="project",
        )
        manage_memory.record_memory(
            repo_root=self.repo_root,
            title="Anti 1",
            category="anti-patterns",
            content="Trap note",
            scope="project",
        )

        stats = manage_memory.get_memory_stats(self.repo_root)
        self.assertTrue(stats["exists"])
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["categories"]["decisions"], 1)
        self.assertEqual(stats["categories"]["anti-patterns"], 1)
        self.assertEqual(stats["categories"]["rules"], 0)


if __name__ == "__main__":
    unittest.main()
