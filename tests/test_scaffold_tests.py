#!/usr/bin/env python3
"""
Unit tests for scaffold_tests.py (test-engineer skill).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import scaffold_tests


class TestScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sample_file = Path(self.tmp.name) / "calculator.py"
        self.sample_file.write_text(
            """
class Calculator:
    \"\"\"Basic arithmetic calculator.\"\"\"
    def __init__(self, precision: int = 2):
        self.precision = precision

    def add(self, a: float, b: float) -> float:
        \"\"\"Adds two numbers.\"\"\"
        return round(a + b, self.precision)

def compute_tax(total: float, rate: float = 0.05) -> float:
    \"\"\"Calculates sales tax.\"\"\"
    return total * rate
""",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_ast_analysis(self):
        functions, classes = scaffold_tests.analyze_file(self.sample_file)
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions[0]["name"], "compute_tax")
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]["name"], "Calculator")
        method_names = [m["name"] for m in classes[0]["methods"]]
        self.assertIn("add", method_names)

    def test_generate_unittest_suite(self):
        functions, classes = scaffold_tests.analyze_file(self.sample_file)
        suite = scaffold_tests.generate_unittest_suite(self.sample_file, functions, classes)
        self.assertIn("class TestCalculator(unittest.TestCase):", suite)
        self.assertIn("def test_compute_tax_happy_path(self):", suite)
        self.assertIn("def test_compute_tax_boundary_empty(self):", suite)
        self.assertIn("def test_calculator_add_success(self):", suite)

    def test_generate_pytest_suite(self):
        functions, classes = scaffold_tests.analyze_file(self.sample_file)
        suite = scaffold_tests.generate_pytest_suite(self.sample_file, functions, classes)
        self.assertIn("def test_compute_tax_happy_path(isolated_env):", suite)
        self.assertIn("@pytest.mark.parametrize", suite)
        self.assertIn("class TestCalculator:", suite)

    def test_generate_matrix(self):
        functions, classes = scaffold_tests.analyze_file(self.sample_file)
        matrix = scaffold_tests.generate_coverage_matrix("calculator.py", functions, classes)
        self.assertIn("# 📊 Boundary Coverage Matrix", matrix)
        self.assertIn("`compute_tax()`", matrix)
        self.assertIn("`Calculator.add()`", matrix)


if __name__ == "__main__":
    unittest.main()
