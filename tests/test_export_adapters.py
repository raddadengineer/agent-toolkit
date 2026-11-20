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
        self.assertTrue((commands_dir / "sys-admin.md").exists())
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
        self.assertTrue((rules_dir / "sys-admin.mdc").exists())
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
        self.assertTrue((prompts_dir / "sys-admin.prompt.md").exists())

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
        self.assertIn("sys-admin", slugs)

        self.assertTrue((self.target / ".clinerules").exists())

    def test_export_codex(self):
        for mode in ("copy", "symlink"):
            target_dir = self.target / f"codex_{mode}"
            target_dir.mkdir(parents=True, exist_ok=True)
            results = export_adapters.export_tool_adapters(self.toolkit, target_dir, "codex", mode=mode)
            self.assertIn("OpenAI Codex", results)

            config_toml = target_dir / ".codex" / "config.toml"
            agents_dir = target_dir / ".codex" / "agents"
            self.assertTrue(config_toml.exists())
            self.assertTrue((target_dir / ".agents" / "skills" / "sys-admin").exists())
            self.assertTrue((target_dir / ".agents" / "scripts").exists())
            self.assertTrue((target_dir / "AGENTS.md").exists())

            expected_agents = [
                "software_engineer",
                "code_reviewer",
                "test_engineer",
                "system_architect",
                "context_optimizer",
                "debugger",
                "security_auditor",
                "database_engineer",
                "devops_engineer",
                "research",
                "sys_admin",
            ]
            for name in expected_agents:
                self.assertTrue((agents_dir / f"{name}.toml").exists(), f"Missing {name}.toml")

            cfg_text = config_toml.read_text(encoding="utf-8")
            self.assertIn("[mcp_servers.playwright]", cfg_text)
            self.assertIn("[mcp_servers.github]", cfg_text)
            self.assertIn("[mcp_servers.sqlite]", cfg_text)

            reviewer_text = (agents_dir / "code_reviewer.toml").read_text(encoding="utf-8")
            sec_text = (agents_dir / "security_auditor.toml").read_text(encoding="utf-8")
            swe_text = (agents_dir / "software_engineer.toml").read_text(encoding="utf-8")
            sys_text = (agents_dir / "sys_admin.toml").read_text(encoding="utf-8")

            self.assertIn('sandbox_mode = "read-only"', reviewer_text)
            self.assertIn('sandbox_mode = "read-only"', sec_text)
            self.assertIn('sandbox_mode = "workspace-write"', swe_text)
            self.assertIn('sandbox_mode = "workspace-write"', sys_text)

            # Strict TOML parse when Python 3.11+ tomllib is present
            try:
                import tomllib  # type: ignore[import-not-found]
                parsed_cfg = tomllib.loads(cfg_text)
                self.assertIn("mcp_servers", parsed_cfg)
                for toml_path in agents_dir.glob("*.toml"):
                    parsed_agent = tomllib.loads(toml_path.read_text(encoding="utf-8"))
                    self.assertIn("name", parsed_agent)
                    self.assertIn("description", parsed_agent)
                    self.assertIn("developer_instructions", parsed_agent)
            except ImportError:
                for toml_path in agents_dir.glob("*.toml"):
                    content = toml_path.read_text(encoding="utf-8")
                    self.assertIn("name =", content)
                    self.assertIn("description =", content)
                    self.assertIn('developer_instructions = """\n', content)
                    self.assertTrue(content.endswith('\n"""\n'), f"Missing closing triple quotes in {toml_path.name}")
                    self.assertEqual(content.replace('\\"\\"\\"', '').count('"""'), 2, f"Unbalanced triple quotes in {toml_path.name}")

        # Verify custom user .codex/config.toml without marker is preserved
        custom_target = self.target / "codex_custom"
        (custom_target / ".codex").mkdir(parents=True)
        custom_cfg = custom_target / ".codex" / "config.toml"
        custom_cfg.write_text('model = "custom-user-model"\n', encoding="utf-8")
        export_adapters.export_tool_adapters(self.toolkit, custom_target, "codex")
        self.assertEqual(custom_cfg.read_text(encoding="utf-8"), 'model = "custom-user-model"\n')

    def test_export_all(self):
        results = export_adapters.export_tool_adapters(self.toolkit, self.target, "all")
        self.assertIn("Claude Code", results)
        self.assertIn("Cursor", results)
        self.assertIn("GitHub Copilot", results)
        self.assertIn("Roo Code / Cline / OpenCode", results)
        self.assertIn("Windsurf", results)
        self.assertIn("Google Antigravity & Gemini CLI", results)
        self.assertIn("OpenAI Codex", results)

        # Check antigravity hooks, mcp, and scripts
        agents_dir = self.target / ".agents"
        self.assertTrue((agents_dir / "hooks.json").exists())
        self.assertTrue((agents_dir / "mcp_config.json").exists())
        self.assertTrue((agents_dir / "scripts").exists())
        self.assertTrue((agents_dir / "skills" / "sys-admin").exists())
        self.assertTrue((agents_dir / "agents" / "sys_admin").exists())
        self.assertTrue((self.target / ".codex" / "config.toml").exists())
        self.assertTrue((self.target / ".codex" / "agents" / "sys_admin.toml").exists())


if __name__ == "__main__":
    unittest.main()
