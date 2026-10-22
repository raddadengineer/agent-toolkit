#!/usr/bin/env python3
"""
Unit tests for manage_release.py (release-manager skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import manage_release


class TestManageRelease(unittest.TestCase):
    def test_parse_semver(self):
        self.assertEqual(manage_release.parse_semver("v1.2.3"), (1, 2, 3))
        self.assertEqual(manage_release.parse_semver("0.10.5"), (0, 10, 5))
        self.assertEqual(manage_release.parse_semver("invalid"), (0, 0, 0))

    def test_compute_next_version(self):
        self.assertEqual(manage_release.compute_next_version("v1.2.3", "patch"), "v1.2.4")
        self.assertEqual(manage_release.compute_next_version("v1.2.3", "minor"), "v1.3.0")
        self.assertEqual(manage_release.compute_next_version("v1.2.3", "major"), "v2.0.0")

    def test_analyze_commits_feature_bump(self):
        commits = [
            {"hash": "abc1", "message": "feat: add user login API"},
            {"hash": "abc2", "message": "fix: resolve memory leak"},
        ]
        res = manage_release.analyze_commits(commits)
        self.assertEqual(res["bump"], "minor")
        self.assertEqual(len(res["features"]), 1)
        self.assertEqual(len(res["fixes"]), 1)

    def test_analyze_commits_breaking_bump(self):
        commits = [
            {"hash": "abc1", "message": "feat!: drop legacy python 3.8 support"},
            {"hash": "abc2", "message": "fix: bug fix"},
        ]
        res = manage_release.analyze_commits(commits)
        self.assertEqual(res["bump"], "major")
        self.assertEqual(len(res["breaking"]), 1)

    def test_generate_release_notes(self):
        commits = [
            {"hash": "abc1", "message": "feat: add new CLI runner"},
            {"hash": "abc2", "message": "fix: correct path traversal"},
        ]
        analysis = manage_release.analyze_commits(commits)
        notes = manage_release.generate_release_notes("v1.1.0", analysis)
        self.assertIn("## [v1.1.0]", notes)
        self.assertIn("### 🚀 Features", notes)
        self.assertIn("### 🐛 Bug Fixes", notes)


if __name__ == "__main__":
    unittest.main()
