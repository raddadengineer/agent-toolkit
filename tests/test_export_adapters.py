#!/usr/bin/env python3
"""
Unit tests for export_adapters.py multi-tool adapter generator.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import export_adapters


class TestExportAdapters(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_adapters_test_")
        self.target = Path(self.test_dir)
        self.toolkit = Path(__file__).resolve().parent.parent

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_export_claude(self):
        results = export_adapters.export_tool_adapters(self.toolkit, self.target, "claude")
        self.assertIn("Claude Code", results)

        commands_dir = self.target / ".claude" / "commands"
        self.assertTrue((commands_dir / "session-starter.md").exists())
        self.assertTrue((commands_dir / "session-closer.md").exists())
        self.assertTrue((commands_dir / "pr-prep.md").exists())
        self.assertTrue((commands_dir / "code-review.md").exists())
        self.assertTrue((commands_dir / "compress-context.md").exists())
        self.assertTrue((commands_dir / "test-engineer.md").exists())
        self.assertTrue((commands_dir / "system-architect.md").exists())
        self.assertTrue((commands_dir / "debugger.md").exists())
        self.assertTrue((commands_dir / "security-audit.md").exists())
        self.assertTrue((commands_dir / "db-migrate.md").exists())
        self.assertTrue((commands_dir / "doc-sync.md").exists())
        self.assertTrue((commands_dir / "container-engineer.md").exists())
        self.assertTrue((commands_dir / "ci-workflow.md").exists())
        self.assertTrue((commands_dir / "dependency-audit.md").exists())
        self.assertTrue((commands_dir / "release-manager.md").exists())
        self.assertTrue((self.target / "CLAUDE.md").exists())

    def test_export_cursor(self):
        results = export_adapters.export_tool_adapters(self.toolkit, self.target, "cursor")
        self.assertIn("Cursor", results)

        rules_dir = self.target / ".cursor" / "rules"
        self.assertTrue((rules_dir / "engineering-standards.mdc").exists())
        self.assertTrue((rules_dir / "code-reviewer.mdc").exists())
        self.assertTrue((rules_dir / "test-engineer.mdc").exists())
        self.assertTrue((rules_dir / "system-architect.mdc").exists())
        self.assertTrue((rules_dir / "debugger.mdc").exists())
        self.assertTrue((rules_dir / "security-auditor.mdc").exists())
        self.assertTrue((rules_dir / "database-engineer.mdc").exists())
        self.assertTrue((rules_dir / "doc-sync.mdc").exists())
        self.assertTrue((rules_dir / "container-engineer.mdc").exists())
        self.assertTrue((rules_dir / "ci-workflow.mdc").exists())
        self.assertTrue((rules_dir / "dependency-auditor.mdc").exists())
        self.assertTrue((rules_dir / "release-manager.mdc").exists())
        self.assertTrue((rules_dir / "session-workflows.mdc").exists())
        self.assertTrue((rules_dir / "context-optimizer.mdc").exists())
        self.assertTrue((self.target / ".cursorrules").exists())

    def test_export_copilot(self):
        results = export_adapters.export_tool_adapters(self.toolkit, self.target, "copilot")
        self.assertIn("GitHub Copilot", results)

        self.assertTrue((self.target / ".github" / "copilot-instructions.md").exists())
        prompts_dir = self.target / ".github" / "prompts"
        self.assertTrue((prompts_dir / "session-starter.prompt.md").exists())
        self.assertTrue((prompts_dir / "code-review.prompt.md").exists())
        self.assertTrue((prompts_dir / "compress-context.prompt.md").exists())
        self.assertTrue((prompts_dir / "test-engineer.prompt.md").exists())
        self.assertTrue((prompts_dir / "system-architect.prompt.md").exists())
        self.assertTrue((prompts_dir / "debugger.prompt.md").exists())
        self.assertTrue((prompts_dir / "security-audit.prompt.md").exists())
        self.assertTrue((prompts_dir / "db-migrate.prompt.md").exists())
        self.assertTrue((prompts_dir / "doc-sync.prompt.md").exists())
        self.assertTrue((prompts_dir / "container-engineer.prompt.md").exists())
        self.assertTrue((prompts_dir / "ci-workflow.prompt.md").exists())
        self.assertTrue((prompts_dir / "dependency-audit.prompt.md").exists())
        self.assertTrue((prompts_dir / "release-manager.prompt.md").exists())

    def test_export_roo_clinerules(self):
        results = export_adapters.export_tool_adapters(self.toolkit, self.target, "roo")
        self.assertIn("Roo Code / Cline / OpenCode", results)

        roomodes = self.target / ".roomodes"
        self.assertTrue(roomodes.exists())
        data = json.loads(roomodes.read_text(encoding="utf-8"))
        self.assertIn("customModes", data)
        slugs = [m["slug"] for m in data["customModes"]]
        self.assertIn("software-engineer", slugs)
        self.assertIn("code-reviewer", slugs)
        self.assertIn("test-engineer", slugs)
        self.assertIn("system-architect", slugs)
        self.assertIn("context-optimizer", slugs)
        self.assertIn("debugger", slugs)
        self.assertIn("security-auditor", slugs)
        self.assertIn("database-engineer", slugs)
        self.assertIn("devops-engineer", slugs)
        self.assertIn("research", slugs)

        self.assertTrue((self.target / ".clinerules").exists())

    def test_export_all(self):
        results = export_adapters.export_tool_adapters(self.toolkit, self.target, "all")
        self.assertIn("Claude Code", results)
        self.assertIn("Cursor", results)
        self.assertIn("GitHub Copilot", results)
        self.assertIn("Roo Code / Cline / OpenCode", results)
        self.assertIn("Windsurf", results)
        self.assertIn("Google Antigravity & Gemini CLI", results)

        # Check antigravity hooks, mcp, and scripts
        agents_dir = self.target / ".agents"
        self.assertTrue((agents_dir / "hooks.json").exists())
        self.assertTrue((agents_dir / "mcp_config.json").exists())
        self.assertTrue((agents_dir / "scripts").exists())


if __name__ == "__main__":
    unittest.main()
