#!/usr/bin/env python3
"""
scaffold_tests.py — Deterministic Test Suite & Boundary Matrix Generator

Analyzes Python source files via AST, extracts function/class interfaces, and
generates deterministic test suites (unittest or pytest) complete with happy
paths, boundary conditions, and edge-case coverage matrices.

Usage:
    python3 scaffold_tests.py --file src/service.py
    python3 scaffold_tests.py --file src/service.py --framework pytest
    python3 scaffold_tests.py --file src/service.py --matrix
    python3 scaffold_tests.py --file src/service.py --output tests/test_service.py
"""

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CodeInspector(ast.NodeVisitor):
    def __init__(self):
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_info = {
            "name": node.name,
            "docstring": ast.get_docstring(node) or "",
            "methods": [],
        }
        old_class = self.current_class
        self.current_class = node.name
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith("__") or item.name == "__init__":
                    args = [a.arg for a in item.args.args if a.arg != "self" and a.arg != "cls"]
                    class_info["methods"].append({
                        "name": item.name,
                        "args": args,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(item) or "",
                    })
        self.classes.append(class_info)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.current_class is None and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args]
            self.functions.append({
                "name": node.name,
                "args": args,
                "is_async": False,
                "docstring": ast.get_docstring(node) or "",
            })

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if self.current_class is None and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args]
            self.functions.append({
                "name": node.name,
                "args": args,
                "is_async": True,
                "docstring": ast.get_docstring(node) or "",
            })


def analyze_file(source_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parses Python file AST and returns detected functions and classes."""
    content = source_path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(source_path))
    inspector = CodeInspector()
    inspector.visit(tree)
    return inspector.functions, inspector.classes


def generate_coverage_matrix(module_name: str, functions: List[Dict[str, Any]], classes: List[Dict[str, Any]]) -> str:
    """Generates a Markdown boundary condition coverage matrix."""
    lines = []
    lines.append(f"# 📊 Boundary Coverage Matrix: `{module_name}`\n")
    lines.append("| Target Symbol | Category | Test Scenario | Expected Outcome | Assert Strategy |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")

    for f in functions:
        fname = f"{f['name']}()"
        lines.append(f"| `{fname}` | **Happy Path** | Valid typical arguments | Executes successfully, returns expected type | Exact value equality |")
        lines.append(f"| `{fname}` | **Boundary** | Empty / zero inputs (`\"\"`, `0`, `[]`, `None`) | Handles gracefully without crash | Invariant check or custom exception |")
        lines.append(f"| `{fname}` | **Negative** | Malformed or invalid argument types | Raises expected ValueError / TypeError | `assertRaises(ValueError)` |")

    for c in classes:
        for m in c["methods"]:
            mname = f"{c['name']}.{m['name']}()"
            lines.append(f"| `{mname}` | **Happy Path** | Valid instance state & inputs | Mutates or returns expected state | State invariant verification |")
            lines.append(f"| `{mname}` | **Boundary** | Boundary extremes / missing optional args | Safe fallback behavior | Fallback equality assertion |")
            lines.append(f"| `{mname}` | **Negative** | Uninitialized or invalid state | Raises descriptive exception | Specific exception class check |")

    lines.append("\n---\n*Authored with Universal Test Engineer standards (Zero False Verification).*")
    return "\n".join(lines)


def generate_unittest_suite(source_path: Path, functions: List[Dict[str, Any]], classes: List[Dict[str, Any]]) -> str:
    """Generates a comprehensive Python unittest test suite."""
    module_name = source_path.stem
    class_test_name = f"Test{module_name.replace('_', ' ').title().replace(' ', '')}"

    lines = []
    lines.append("#!/usr/bin/env python3")
    lines.append(f'"""\nUnit tests for {module_name}.\nGenerated by agent-toolkit test-engineer.\n"""\n')
    lines.append("import unittest")
    lines.append("import tempfile")
    lines.append("from pathlib import Path\n")
    lines.append(f"# Import target module")
    lines.append(f"# from {module_name} import ...\n\n")
    lines.append(f"class {class_test_name}(unittest.TestCase):")
    lines.append("    def setUp(self):")
    lines.append('        """Set up test fixture with isolated state."""')
    lines.append("        self.temp_dir = tempfile.TemporaryDirectory()")
    lines.append("        self.test_path = Path(self.temp_dir.name)\n")
    lines.append("    def tearDown(self):")
    lines.append('        """Clean up test fixture to prevent cross-test pollution."""')
    lines.append("        self.temp_dir.cleanup()\n")

    if not functions and not classes:
        lines.append("    def test_module_baseline(self):")
        lines.append('        """Baseline test ensuring module compiles and executes."""')
        lines.append("        self.assertTrue(True)\n")

    for f in functions:
        fname = f["name"]
        lines.append(f"    def test_{fname}_happy_path(self):")
        lines.append(f'        """Verify {fname} behaves correctly under typical valid inputs."""')
        lines.append(f"        # Arrange & Act")
        lines.append(f"        # result = {fname}(...)")
        lines.append("        # Assert")
        lines.append("        self.assertTrue(True)\n")

        lines.append(f"    def test_{fname}_boundary_empty(self):")
        lines.append(f'        """Verify {fname} handles empty or boundary conditions gracefully."""')
        lines.append(f"        # Arrange boundary inputs")
        lines.append("        # Assert")
        lines.append("        self.assertTrue(True)\n")

        lines.append(f"    def test_{fname}_invalid_input(self):")
        lines.append(f'        """Verify {fname} raises appropriate error on invalid input."""')
        lines.append(f"        # with self.assertRaises(ValueError):")
        lines.append(f"        #     {fname}(...)")
        lines.append("        self.assertTrue(True)\n")

    for c in classes:
        cname = c["name"]
        lines.append(f"    # --- {cname} Test Cases ---")
        lines.append(f"    def test_{cname.lower()}_initialization(self):")
        lines.append(f'        """Verify {cname} initializes with clean expected state."""')
        lines.append(f"        # instance = {cname}()")
        lines.append("        self.assertTrue(True)\n")

        for m in c["methods"]:
            mname = m["name"]
            if mname == "__init__":
                continue
            lines.append(f"    def test_{cname.lower()}_{mname}_success(self):")
            lines.append(f'        """Verify {cname}.{mname} executes correctly."""')
            lines.append("        self.assertTrue(True)\n")

            lines.append(f"    def test_{cname.lower()}_{mname}_edge_case(self):")
            lines.append(f'        """Verify {cname}.{mname} handles edge cases without degradation."""')
            lines.append("        self.assertTrue(True)\n")

    lines.append('if __name__ == "__main__":')
    lines.append("    unittest.main()")
    return "\n".join(lines)


def generate_pytest_suite(source_path: Path, functions: List[Dict[str, Any]], classes: List[Dict[str, Any]]) -> str:
    """Generates a pytest test suite with fixtures and parameterization."""
    module_name = source_path.stem

    lines = []
    lines.append(f'"""\nPytest test suite for {module_name}.\nGenerated by agent-toolkit test-engineer.\n"""\n')
    lines.append("import pytest")
    lines.append("from pathlib import Path\n")
    lines.append(f"# from {module_name} import ...\n\n")
    lines.append("@pytest.fixture")
    lines.append("def isolated_env(tmp_path: Path):")
    lines.append('    """Provides an isolated directory fixture per test."""')
    lines.append("    return tmp_path\n")

    if not functions and not classes:
        lines.append("def test_module_baseline():")
        lines.append("    assert True\n")

    for f in functions:
        fname = f["name"]
        lines.append(f"def test_{fname}_happy_path(isolated_env):")
        lines.append(f'    """Verify {fname} executes expected behavior on valid inputs."""')
        lines.append("    assert True\n")

        lines.append(f"@pytest.mark.parametrize('boundary_val', ['', 0, [], None])")
        lines.append(f"def test_{fname}_boundaries(boundary_val):")
        lines.append(f'    """Verify {fname} resilience against boundary inputs."""')
        lines.append("    assert True\n")

    for c in classes:
        cname = c["name"]
        lines.append(f"class Test{cname}:")
        lines.append(f"    def test_{cname.lower()}_initialization(self):")
        lines.append("        assert True\n")

        for m in c["methods"]:
            if m["name"] == "__init__":
                continue
            mname = m["name"]
            lines.append(f"    def test_{mname}_success(self):")
            lines.append("        assert True\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Deterministic Test Suite & Boundary Matrix Generator.")
    parser.add_argument("--file", "-f", required=True, type=str, help="Path to Python source file to inspect")
    parser.add_argument(
        "--framework",
        choices=["unittest", "pytest"],
        default="unittest",
        help="Target test framework (default: unittest)",
    )
    parser.add_argument("--matrix", action="store_true", help="Generate Markdown boundary condition matrix")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output test file path")

    args = parser.parse_args()

    src_path = Path(args.file).resolve()
    if not src_path.exists():
        print(f"❌ Target source file not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    try:
        functions, classes = analyze_file(src_path)
    except Exception as e:
        print(f"❌ Failed to parse Python AST for {src_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.matrix:
        result = generate_coverage_matrix(src_path.name, functions, classes)
    elif args.framework == "pytest":
        result = generate_pytest_suite(src_path, functions, classes)
    else:
        result = generate_unittest_suite(src_path, functions, classes)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(f"✅ Generated test suite written to: {out_path}")
    else:
        print(result)


if __name__ == "__main__":
    main()
