#!/usr/bin/env python3
"""
Unit tests for harden_docker.py (container-engineer skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import harden_docker


class TestHardenDocker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_scaffolds_hardened_files(self):
        harden_docker.init_stack(self.dir, "python")
        df = self.dir / "Dockerfile"
        di = self.dir / ".dockerignore"

        self.assertTrue(df.exists())
        self.assertTrue(di.exists())

        res = harden_docker.audit_dockerfile(df)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["critical_count"], 0)

    def test_detects_unpinned_latest_image(self):
        df = self.dir / "Dockerfile"
        df.write_text("FROM python:latest\nUSER appuser\nHEALTHCHECK CMD true\n", encoding="utf-8")
        (self.dir / ".dockerignore").write_text(".git\n", encoding="utf-8")

        res = harden_docker.audit_dockerfile(df)
        self.assertEqual(res["status"], "fail")
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("DOCKER-LATEST-TAG", ids)

    def test_detects_root_user_hazard(self):
        df = self.dir / "Dockerfile"
        df.write_text("FROM python:3.11-slim\nHEALTHCHECK CMD true\n", encoding="utf-8")
        (self.dir / ".dockerignore").write_text(".git\n", encoding="utf-8")

        res = harden_docker.audit_dockerfile(df)
        self.assertEqual(res["status"], "fail")
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("DOCKER-ROOT-USER", ids)

    def test_detects_secret_in_env(self):
        df = self.dir / "Dockerfile"
        df.write_text("FROM python:3.11-slim\nENV AWS_SECRET_KEY=1234567890\nUSER appuser\nHEALTHCHECK CMD true\n", encoding="utf-8")
        (self.dir / ".dockerignore").write_text(".git\n", encoding="utf-8")

        res = harden_docker.audit_dockerfile(df)
        self.assertEqual(res["status"], "fail")
        ids = [f["id"] for f in res["findings"]]
        self.assertIn("DOCKER-SECRET-ENV", ids)


if __name__ == "__main__":
    unittest.main()
