#!/usr/bin/env python3
"""
Unit tests for dream_consolidator.py (dreamer skill).
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import dream_consolidator
import manage_memory


class TestDreamConsolidator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp.name)
        manage_memory.init_memory(self.repo_root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_session_log(self):
        session_log = self.repo_root / "SESSION_LOG.md"
        session_log.write_text(
            "# Session Ledger\n\n"
            "### Session [2026-11-04 18:00] — Feature Authentication\n"
            "- **Goal**:\n"
            "  - Implement OAuth2 login provider\n"
            "- **Changes Completed**:\n"
            "  - Added JWT token verification service\n"
            "- **Validation**:\n"
            "  - Ran 45 unit tests (exit 0) and security audit\n"
            "- **Next Steps / Handover**:\n"
            "  - Deploy to staging\n\n---\n",
            encoding="utf-8",
        )

        sessions = dream_consolidator.parse_session_log(session_log)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "Feature Authentication")
        self.assertIn("OAuth2 login provider", sessions[0]["goal"])
        self.assertIn("Ran 45 unit tests (exit 0)", sessions[0]["validation"])

    def test_extract_candidates_from_transcript(self):
        transcript_path = self.repo_root / "transcript.jsonl"
        steps = [
            {"step_index": 1, "content": "Tool call failed: ModuleNotFoundError: No module named 'cryptography'"},
            {"step_index": 2, "content": "pip install cryptography\nCommand exited with code 0.\nSuccessfully installed cryptography"},
        ]
        with open(transcript_path, "w", encoding="utf-8") as f:
            for s in steps:
                f.write(json.dumps(s) + "\n")

        entries = dream_consolidator.parse_transcript_entries(transcript_path)
        candidates = dream_consolidator.extract_candidates_from_transcript(entries)

        self.assertGreaterEqual(len(candidates), 1)
        anti = candidates[0]
        self.assertEqual(anti["category"], "anti-patterns")
        self.assertIn("ModuleNotFoundError", anti["title"])
        self.assertEqual(anti["confidence"], "HIGH")

    def test_dream_session_learnings_end_to_end(self):
        session_log = self.repo_root / "SESSION_LOG.md"
        session_log.write_text(
            "### Session [2026-11-04 20:00] — Database Partitioning Migration\n"
            "- **Goal**:\n"
            "  - Migrate users table to monthly partitions\n"
            "- **Changes Completed**:\n"
            "  - Created reversible migration script with non-locking indexes\n"
            "- **Validation**:\n"
            "  - pytest tests/migrations (exit 0)\n"
            "- **Next Steps / Handover**:\n"
            "  - Benchmark query latency\n\n---\n",
            encoding="utf-8",
        )

        result = dream_consolidator.dream_session_learnings(self.repo_root)
        self.assertEqual(result["sessions_analyzed"], 1)
        self.assertGreaterEqual(result["total_candidates"], 1)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["category"], "patterns")
        self.assertIn("Database Partitioning Migration", candidate["title"])

        # Format proposal
        md = dream_consolidator.format_proposal_markdown(result)
        self.assertIn("Offline Memory Consolidation Proposal", md)
        self.assertIn("Database Partitioning Migration", md)


if __name__ == "__main__":
    unittest.main()
