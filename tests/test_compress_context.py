#!/usr/bin/env python3
"""
Unit tests for compress_context.py token optimizer & context compression engine.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
import sys

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import compress_context


class TestCompressContext(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="agent_toolkit_compress_test_")
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_estimate_tokens(self):
        text = "Hello world! This is a test string for token estimation."
        tokens = compress_context.estimate_tokens(text)
        self.assertGreater(tokens, 5)
        self.assertLess(tokens, 25)

    def test_skeletonize_python(self):
        code = '''"""Module docstring for test."""
import os
from typing import List

class DataProcessor:
    """Processes large datasets."""
    def __init__(self, name: str):
        self.name = name
        self.items = []
        for i in range(100):
            self.items.append(i * 2)

    def process(self, data: List[int]) -> bool:
        if not data:
            return False
        total = sum(data)
        return total > 100

def top_level_helper(x: int, y: int) -> int:
    result = x * 2 + y * 3
    print("Debug info")
    return result
'''
        skel = compress_context.skeletonize_python(code)
        self.assertIn("class DataProcessor:", skel)
        self.assertIn("def __init__(self, name: str): ...", skel)
        self.assertIn("def process(self, data: List[int]) -> bool: ...", skel)
        self.assertIn("def top_level_helper(x: int, y: int) -> int: ...", skel)
        self.assertNotIn("self.items.append", skel)
        self.assertNotIn("Debug info", skel)

        # Significant token reduction
        raw_tok = compress_context.estimate_tokens(code)
        skel_tok = compress_context.estimate_tokens(skel)
        self.assertLess(skel_tok, raw_tok)

    def test_skeletonize_typescript(self):
        code = '''import { User } from "./user";

export interface UserConfig {
    id: string;
    roles: string[];
}

export class UserService {
    private users: User[] = [];

    async getUser(id: string): Promise<User | null> {
        const found = this.users.find(u => u.id === id);
        console.log("fetching user", id);
        return found || null;
    }
}

export function validateConfig(config: UserConfig): boolean {
    return config.roles.length > 0;
}
'''
        skel = compress_context.skeletonize_typescript(code)
        self.assertIn("interface UserConfig", skel)
        self.assertIn("class UserService", skel)
        self.assertIn("validateConfig", skel)
        self.assertNotIn("console.log", skel)

    def test_skeletonize_swift(self):
        code = '''import Foundation

public struct UserProfile {
    public let id: String
    public var name: String

    public init(id: String, name: String) {
        self.id = id
        self.name = name
    }

    public func displayName() -> String {
        return "User: \(name)"
    }
}
'''
        skel = compress_context.skeletonize_swift(code)
        self.assertIn("struct UserProfile", skel)
        self.assertIn("func displayName() -> String", skel)
        self.assertNotIn("return \"User:", skel)

    def test_profile_repository(self):
        (self.root / "file1.py").write_text("def a(): pass\ndef b(): pass\n", encoding="utf-8")
        (self.root / "file2.ts").write_text("export const x = 1;\n", encoding="utf-8")

        prof = compress_context.profile_repository(self.root)
        self.assertEqual(2, prof["total_files"])
        self.assertGreater(prof["total_tokens"], 0)
        self.assertEqual(2, len(prof["files"]))

    def test_pack_repository_budget(self):
        # Create multiple files
        for i in range(10):
            content = f"# File {i}\n" + ("x = 100\n" * 50)
            (self.root / f"mod_{i}.py").write_text(content, encoding="utf-8")

        packed, stats = compress_context.pack_repository(
            self.root,
            mode="skeleton",
            token_budget=500,
        )
        self.assertLessEqual(stats["output_tokens"], 600)
        self.assertGreater(stats["tokens_saved"], 0)


if __name__ == "__main__":
    unittest.main()
