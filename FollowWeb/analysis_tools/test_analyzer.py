"""
Test analysis framework for detecting duplicate tests and refactoring opportunities.
"""

# Standard library imports
import ast
from pathlib import Path
from typing import Dict, List

# Local imports
from .models import (
    DuplicateTestAction,
    DuplicateTestAnalysisResult,
    DuplicateTestGroup,
)
from .similarity_utils import SimilarityCalculator, SimilarityMethod


class DuplicateTestAnalyzer:
    """Analyzes test files for duplicates, redundancies, and refactoring opportunities."""

    def __init__(self):
        self.test_patterns = self._initialize_test_patterns()

    def _initialize_test_patterns(self) -> Dict[str, str]:
        """Initialize patterns for identifying test components."""
        return {
            "test_function": r"^def\s+test_",
            "fixture": r"@pytest\.fixture",
            "parametrize": r"@pytest\.mark\.parametrize",
            "skip": r"@pytest\.mark\.skip",
            "assert": r"assert\s+",
            "mock": r"mock\.|Mock\(",
        }

    def analyze_test_file(self, test_file: str) -> DuplicateTestAnalysisResult:
        """Analyze a single test file for issues and refactoring opportunities."""
        path = Path(test_file)
        if not path.exists():
            raise ValueError(f"Test file not found: {test_file}")

        with open(path, encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Return minimal result for files with syntax errors
            return DuplicateTestAnalysisResult(
                test_file=test_file,
                duplicate_tests=[],
                unused_fixtures=[],
                redundant_imports=[],
                test_count=0,
            )

        # Extract test functions and their details
        test_functions = self._extract_test_functions(tree)

        # Find duplicate tests
        duplicate_groups = self._find_duplicate_tests(test_functions, test_file)

        # Find unused fixtures
        unused_fixtures = self._find_unused_fixtures(tree, content)

        # Find redundant imports
        redundant_imports = self._find_redundant_imports(tree, content)

        return DuplicateTestAnalysisResult(
            test_file=test_file,
            duplicate_tests=duplicate_groups,
            unused_fixtures=unused_fixtures,
            redundant_imports=redundant_imports,
            test_count=len(test_functions),
        )

    def analyze_test_directory(
        self, test_dir: str
    ) -> List[DuplicateTestAnalysisResult]:
        """Analyze all test files in a directory."""
        results = []
        test_path = Path(test_dir)

        for test_file in test_path.rglob("test_*.py"):
            try:
                result = self.analyze_test_file(str(test_file))
                results.append(result)
            except Exception as e:
                print(f"Error analyzing test file {test_file}: {e}")

        return results

    def find_cross_file_duplicates(
        self, test_results: List[DuplicateTestAnalysisResult]
    ) -> List[DuplicateTestGroup]:
        """Find duplicate tests across multiple files."""
        all_tests = []

        # Collect all test functions from all files
        for result in test_results:
            with open(result.test_file, encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)
                test_functions = self._extract_test_functions(tree)

                for test_func in test_functions:
                    all_tests.append(
                        {
                            "name": test_func["name"],
                            "body": test_func["body"],
                            "file": result.test_file,
                            "line": test_func["line"],
                            "args": test_func.get("args", []),
                            "decorators": test_func.get("decorators", []),
                        }
                    )
            except SyntaxError:
                continue

        # Find duplicates across files
        duplicates = []
        processed = set()

        for i, test1 in enumerate(all_tests):
            if i in processed:
                continue

            similar_tests = [test1]

            for j, test2 in enumerate(all_tests[i + 1 :], i + 1):
                if j in processed:
                    continue

                similarity = self._calculate_test_similarity(
                    test1["body"], test2["body"]
                )
                if similarity > 0.8:  # 80% similarity threshold
                    similar_tests.append(test2)
                    processed.add(j)

            if len(similar_tests) > 1:
                # Determine the best test to keep
                primary_test = self._select_primary_test(similar_tests)

                duplicates.append(
                    DuplicateTestGroup(
                        test_names=[test["name"] for test in similar_tests],
                        similarity_score=0.8,  # Minimum similarity that triggered this group
                        recommended_action=DuplicateTestAction.CONSOLIDATE,
                        primary_test=primary_test["name"],
                        file_paths=list({test["file"] for test in similar_tests}),
                    )
                )

                processed.add(i)

        return duplicates

    def _extract_test_functions(self, tree: ast.AST) -> List[Dict]:
        """Extract test function information from AST."""
        test_functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                # Extract function body as string for comparison
                body_lines = []
                for stmt in node.body:
                    body_lines.append(ast.dump(stmt))

                test_functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "body": "\n".join(body_lines),
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [ast.dump(dec) for dec in node.decorator_list],
                    }
                )

        return test_functions

    def _find_duplicate_tests(
        self, test_functions: List[Dict], file_path: str
    ) -> List[DuplicateTestGroup]:
        """Find duplicate tests within a single file."""
        duplicates = []
        processed = set()

        for i, test1 in enumerate(test_functions):
            if i in processed:
                continue

            similar_tests = [test1]

            for j, test2 in enumerate(test_functions[i + 1 :], i + 1):
                if j in processed:
                    continue

                similarity = self._calculate_test_similarity(
                    test1["body"], test2["body"]
                )
                if similarity > 0.8:
                    similar_tests.append(test2)
                    processed.add(j)

            if len(similar_tests) > 1:
                primary_test = self._select_primary_test(similar_tests)

                duplicates.append(
                    DuplicateTestGroup(
                        test_names=[test["name"] for test in similar_tests],
                        similarity_score=0.8,
                        recommended_action=DuplicateTestAction.CONSOLIDATE,
                        primary_test=primary_test["name"],
                        file_paths=[file_path],
                    )
                )

                processed.add(i)

        return duplicates

    def _calculate_test_similarity(self, body1: str, body2: str) -> float:
        """Calculate similarity between two test function bodies."""
        return SimilarityCalculator.calculate_similarity(
            body1, body2, SimilarityMethod.SEQUENCE_MATCHER
        )

    def _select_primary_test(self, similar_tests: List[Dict]) -> Dict:
        """Select the best test to keep from a group of similar tests."""

        # Prefer tests with more comprehensive names or more assertions
        def test_score(test):
            score = 0

            # Longer names often indicate more specific tests
            score += len(test["name"]) * 0.1

            # Count assertions in the body
            score += test["body"].count("assert") * 2

            # Prefer tests with parameters (more comprehensive)
            score += len(test["args"]) * 1

            # Prefer tests with decorators (might have important markers)
            score += len(test["decorators"]) * 0.5

            return score

        return max(similar_tests, key=test_score)

    def _find_unused_fixtures(self, tree: ast.AST, content: str) -> List[str]:
        """Find fixtures that are defined but not used."""
        fixtures = set()
        used_names = set()

        # Find all fixture definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Attribute)
                        and isinstance(decorator.value, ast.Name)
                        and decorator.value.id == "pytest"
                        and decorator.attr == "fixture"
                    ):
                        fixtures.add(node.name)
                    elif isinstance(decorator, ast.Name) and decorator.id == "fixture":
                        fixtures.add(node.name)

        # Find all name usage in test functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                # Check function parameters (fixture usage)
                for arg in node.args.args:
                    used_names.add(arg.arg)

                # Check function body for name usage
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        used_names.add(child.id)

        # Return fixtures that are defined but not used
        return list(fixtures - used_names)

    def _find_redundant_imports(self, tree: ast.AST, content: str) -> List[str]:
        """Find imports that are not used in the test file."""
        imports = set()
        used_names = set()

        # Collect all imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.add(name)

        # Collect all name usage
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Return imports that are not used
        return list(imports - used_names)
