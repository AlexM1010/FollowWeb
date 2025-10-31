"""
Code Duplication Detection for identifying redundant code patterns and validation logic.

This module provides comprehensive analysis of code duplication including:
- Duplicate validation logic
- Redundant directory creation and file operations
- Similar error handling patterns
- Duplicate import statements and unused imports
"""

import ast
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .ast_utils import extract_all_exports, is_init_file
from .similarity_utils import SimilarityCalculator


@dataclass
class DuplicateCodeBlock:
    """Represents a duplicate code block found in the codebase."""

    content: str
    content_hash: str
    locations: List[Tuple[str, int, int]]  # (file_path, start_line, end_line)
    similarity_score: float
    block_type: (
        str  # 'validation', 'error_handling', 'file_operation', 'import', 'function'
    )


@dataclass
class ValidationPattern:
    """Represents a validation pattern found in code."""

    pattern_type: str
    variable_name: str
    condition: str
    file_path: str
    line_number: int
    full_statement: str


@dataclass
class ImportAnalysis:
    """Analysis of import statements in a file."""

    file_path: str
    used_imports: Set[str]
    unused_imports: Set[str]
    duplicate_imports: List[Tuple[str, List[int]]]  # (import_name, line_numbers)
    redundant_imports: List[str]


@dataclass
class DuplicationReport:
    """Comprehensive report of code duplication in a file or project."""

    file_path: str
    duplicate_blocks: List[DuplicateCodeBlock]
    validation_duplicates: List[ValidationPattern]
    import_analysis: ImportAnalysis
    error_handling_duplicates: List[DuplicateCodeBlock]
    file_operation_duplicates: List[DuplicateCodeBlock]
    summary: str


class DuplicationDetector:
    """Detector for various types of code duplication and redundancy."""

    def __init__(self):
        """Initialize the duplication detector."""
        self.validation_patterns = self._initialize_validation_patterns()
        self.error_handling_patterns = self._initialize_error_handling_patterns()
        self.file_operation_patterns = self._initialize_file_operation_patterns()

    def _initialize_validation_patterns(self) -> List[str]:
        """Initialize patterns for common validation logic (non-overlapping)."""
        return [
            # None checks (prioritize 'is None' over '== None')
            r"if\s+(\w+)\s+is\s+None:",
            r"if\s+(\w+)\s+is\s+not\s+None:",
            # Truthiness checks
            r"if\s+not\s+(\w+):",
            # Length checks
            r"if\s+len\((\w+)\)\s*==\s*0:",
            r"if\s+len\((\w+)\)\s*>\s*0:",
            # String emptiness checks
            r'if\s+(\w+)\s+==\s+["\'][\'"]:',
            r"if\s+not\s+(\w+)\.strip\(\):",
            # Type and attribute checks
            r"if\s+not\s+isinstance\((\w+),",
            r"if\s+not\s+hasattr\((\w+),",
            # Range checks
            r"if\s+(\w+)\s+<\s+0:",
            r"if\s+(\w+)\s+<=\s+0:",
            # Assertions (separate from if statements)
            r"assert\s+(\w+)\s+is\s+not\s+None",
            r"assert\s+(\w+)(?!\s+is)",  # Assert without 'is' to avoid overlap
        ]

    def _initialize_error_handling_patterns(self) -> List[str]:
        """Initialize patterns for error handling code."""
        return [
            r"try:\s*\n.*?except.*?:",
            r"raise\s+\w+Error\(",
            r"logging\.error\(",
            r"logger\.error\(",
            r"print\(.*error.*\)",
            r"return\s+False",
            r"return\s+None",
        ]

    def _initialize_file_operation_patterns(self) -> List[str]:
        """Initialize patterns for file operations."""
        return [
            r"os\.path\.exists\(",
            r"Path\(.*\)\.exists\(\)",
            r"os\.makedirs\(",
            r"Path\(.*\)\.mkdir\(",
            r"ensure_output_directory\(",
            r"with\s+open\(",
            r"\.write\(",
            r"\.read\(",
            r"json\.load\(",
            r"json\.dump\(",
        ]

    def analyze_file(self, file_path: str) -> DuplicationReport:
        """
        Analyze a single file for code duplication.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            DuplicationReport: Comprehensive duplication analysis
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return DuplicationReport(
                file_path=file_path,
                duplicate_blocks=[],
                validation_duplicates=[],
                import_analysis=ImportAnalysis(file_path, set(), set(), [], []),
                error_handling_duplicates=[],
                file_operation_duplicates=[],
                summary=f"Error reading file: {e}",
            )

        # Analyze different types of duplication
        validation_duplicates = self._analyze_validation_patterns(content, file_path)
        import_analysis = self._analyze_imports(content, file_path)
        error_handling_duplicates = self._analyze_error_handling(content, file_path)
        file_operation_duplicates = self._analyze_file_operations(content, file_path)

        # Find general duplicate code blocks
        duplicate_blocks = self._find_duplicate_blocks(content, file_path)

        summary = self._generate_summary(
            file_path,
            validation_duplicates,
            import_analysis,
            error_handling_duplicates,
            file_operation_duplicates,
            duplicate_blocks,
        )

        return DuplicationReport(
            file_path=file_path,
            duplicate_blocks=duplicate_blocks,
            validation_duplicates=validation_duplicates,
            import_analysis=import_analysis,
            error_handling_duplicates=error_handling_duplicates,
            file_operation_duplicates=file_operation_duplicates,
            summary=summary,
        )

    def _analyze_validation_patterns(
        self, content: str, file_path: str
    ) -> List[ValidationPattern]:
        """Analyze validation patterns in the code."""
        patterns = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            for pattern in self.validation_patterns:
                match = re.search(pattern, stripped)
                if match:
                    variable_name = match.group(1) if match.groups() else "unknown"

                    patterns.append(
                        ValidationPattern(
                            pattern_type=self._classify_validation_pattern(pattern),
                            variable_name=variable_name,
                            condition=stripped,
                            file_path=file_path,
                            line_number=line_num,
                            full_statement=line.rstrip(),
                        )
                    )

        return patterns

    def _classify_validation_pattern(self, pattern: str) -> str:
        """Classify the type of validation pattern."""
        if "None" in pattern:
            return "null_check"
        elif "len(" in pattern:
            return "length_check"
        elif "isinstance" in pattern:
            return "type_check"
        elif "hasattr" in pattern:
            return "attribute_check"
        elif "assert" in pattern:
            return "assertion"
        elif "<" in pattern or ">" in pattern:
            return "range_check"
        else:
            return "general_validation"

    def _analyze_imports(self, content: str, file_path: str) -> ImportAnalysis:
        """Analyze import statements for duplicates and unused imports."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return ImportAnalysis(file_path, set(), set(), [], [])

        # Collect all imports with location context
        imports = {}  # name -> line numbers
        import_aliases = {}  # alias -> original name
        nested_import_names = []  # imports inside functions/classes (just names)

        # First pass: collect top-level imports
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    if name not in imports:
                        imports[name] = []
                    imports[name].append(node.lineno)

                    if alias.asname:
                        import_aliases[alias.asname] = alias.name

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    full_name = f"{module}.{name}" if module else name

                    if name not in imports:
                        imports[name] = []
                    imports[name].append(node.lineno)

                    if alias.asname:
                        import_aliases[alias.asname] = full_name

        # Second pass: find imports inside functions/classes (for redundant import detection)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for child in ast.walk(node):
                    if (
                        isinstance(child, (ast.Import, ast.ImportFrom))
                        and child != node
                    ):
                        if isinstance(child, ast.Import):
                            nested_import_names.extend(
                                [alias.name for alias in child.names]
                            )
                        else:
                            module = child.module or ""
                            nested_import_names.extend(
                                [f"{module}.{alias.name}" for alias in child.names]
                            )

        # Find used names in the code
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle attribute access like module.function
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Special handling for __init__.py files: check __all__ list
        all_exports = set()
        init_file = is_init_file(file_path)

        if init_file:
            all_exports = extract_all_exports(tree)

        # Determine used and unused imports
        used_imports = set()
        unused_imports = set()

        for import_name in imports.keys():
            # Skip unused import check if this is an __init__.py file and the import is in __all__
            if init_file and import_name in all_exports:
                used_imports.add(import_name)
            elif import_name in used_names:
                used_imports.add(import_name)
            else:
                # Check if it's used through an alias
                original_name = import_aliases.get(import_name)
                if original_name and any(
                    name.startswith(original_name.split(".")[0]) for name in used_names
                ):
                    used_imports.add(import_name)
                else:
                    unused_imports.add(import_name)

        # Find duplicate imports (same name imported multiple times)
        duplicate_imports = [
            (name, lines) for name, lines in imports.items() if len(lines) > 1
        ]

        # Add nested imports to redundant imports list
        redundant_imports = list(unused_imports)
        redundant_imports.extend(nested_import_names)

        return ImportAnalysis(
            file_path=file_path,
            used_imports=used_imports,
            unused_imports=unused_imports,
            duplicate_imports=duplicate_imports,
            redundant_imports=redundant_imports,
        )

    def _analyze_error_handling(
        self, content: str, file_path: str
    ) -> List[DuplicateCodeBlock]:
        """Analyze error handling patterns for duplication."""
        blocks = []
        lines = content.split("\n")

        # Find try-except blocks
        try_blocks = []
        current_block = None

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith("try:"):
                current_block = {"start": line_num, "lines": [line], "in_except": False}
            elif current_block and (
                stripped.startswith("except") or stripped.startswith("finally")
            ):
                current_block["lines"].append(line)
                current_block["in_except"] = True
            elif (
                current_block
                and current_block["in_except"]
                and (line.startswith("    ") or stripped == "")
            ):
                current_block["lines"].append(line)
            elif current_block:
                # End of try-except block
                current_block["end"] = line_num - 1
                try_blocks.append(current_block)
                current_block = None

        # Compare try-except blocks for similarity
        for i, block1 in enumerate(try_blocks):
            for block2 in try_blocks[i + 1 :]:
                similarity = self._calculate_similarity(
                    block1["lines"], block2["lines"]
                )
                if similarity > 0.7:  # 70% similarity threshold
                    content_str = "\n".join(block1["lines"])
                    content_hash = hashlib.md5(content_str.encode()).hexdigest()

                    blocks.append(
                        DuplicateCodeBlock(
                            content=content_str,
                            content_hash=content_hash,
                            locations=[
                                (file_path, block1["start"], block1["end"]),
                                (file_path, block2["start"], block2["end"]),
                            ],
                            similarity_score=similarity,
                            block_type="error_handling",
                        )
                    )

        return blocks

    def _analyze_file_operations(
        self, content: str, file_path: str
    ) -> List[DuplicateCodeBlock]:
        """Analyze file operation patterns for duplication."""
        blocks = []
        lines = content.split("\n")

        # Find file operation patterns
        file_op_lines = []
        for line_num, line in enumerate(lines, 1):
            for pattern in self.file_operation_patterns:
                if re.search(pattern, line):
                    file_op_lines.append((line_num, line.strip(), pattern))
                    break

        # Group similar file operations
        pattern_groups = defaultdict(list)
        for line_num, line_content, pattern in file_op_lines:
            pattern_groups[pattern].append((line_num, line_content))

        # Find duplicates within each pattern group
        for pattern, occurrences in pattern_groups.items():
            if len(occurrences) > 1:
                # Group by similar content
                content_groups = defaultdict(list)
                for line_num, line_content in occurrences:
                    # Normalize the content for comparison
                    normalized = re.sub(
                        r'["\'].*?["\']', '""', line_content
                    )  # Replace string literals
                    normalized = re.sub(
                        r"\w+", "VAR", normalized
                    )  # Replace variable names
                    content_groups[normalized].append((line_num, line_content))

                for _normalized_content, group in content_groups.items():
                    if len(group) > 1:
                        content_str = f"Pattern: {pattern}\nOccurrences:\n" + "\n".join(
                            [content for _, content in group]
                        )
                        content_hash = hashlib.md5(content_str.encode()).hexdigest()

                        blocks.append(
                            DuplicateCodeBlock(
                                content=content_str,
                                content_hash=content_hash,
                                locations=[
                                    (file_path, line_num, line_num)
                                    for line_num, _ in group
                                ],
                                similarity_score=1.0,  # Exact pattern match
                                block_type="file_operation",
                            )
                        )

        return blocks

    def _find_duplicate_blocks(
        self, content: str, file_path: str
    ) -> List[DuplicateCodeBlock]:
        """Find general duplicate code blocks using AST analysis."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        blocks = []
        functions = []

        # Extract function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(content, node)
                if func_source:
                    functions.append(
                        {
                            "name": node.name,
                            "source": func_source,
                            "lineno": node.lineno,
                            "end_lineno": getattr(node, "end_lineno", node.lineno),
                        }
                    )

        # Compare functions for similarity
        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                similarity = self._calculate_similarity(
                    func1["source"].split("\n"), func2["source"].split("\n")
                )

                if similarity > 0.8:  # 80% similarity threshold
                    content_hash = hashlib.md5(func1["source"].encode()).hexdigest()

                    blocks.append(
                        DuplicateCodeBlock(
                            content=f"Similar functions:\n{func1['name']} and {func2['name']}",
                            content_hash=content_hash,
                            locations=[
                                (file_path, func1["lineno"], func1["end_lineno"]),
                                (file_path, func2["lineno"], func2["end_lineno"]),
                            ],
                            similarity_score=similarity,
                            block_type="function",
                        )
                    )

        return blocks

    def _calculate_similarity(self, lines1: List[str], lines2: List[str]) -> float:
        """Calculate similarity between two sets of code lines."""
        return SimilarityCalculator.calculate_line_similarity(lines1, lines2)

    def _generate_summary(
        self,
        file_path: str,
        validation_duplicates: List[ValidationPattern],
        import_analysis: ImportAnalysis,
        error_handling_duplicates: List[DuplicateCodeBlock],
        file_operation_duplicates: List[DuplicateCodeBlock],
        duplicate_blocks: List[DuplicateCodeBlock],
    ) -> str:
        """Generate a summary of duplication analysis."""
        issues = []

        if validation_duplicates:
            issues.append(f"{len(validation_duplicates)} validation patterns")

        if import_analysis.unused_imports:
            issues.append(f"{len(import_analysis.unused_imports)} unused imports")

        if import_analysis.duplicate_imports:
            issues.append(f"{len(import_analysis.duplicate_imports)} duplicate imports")

        if error_handling_duplicates:
            issues.append(
                f"{len(error_handling_duplicates)} duplicate error handling blocks"
            )

        if file_operation_duplicates:
            issues.append(f"{len(file_operation_duplicates)} duplicate file operations")

        if duplicate_blocks:
            issues.append(f"{len(duplicate_blocks)} duplicate code blocks")

        if not issues:
            return f"No significant code duplication detected in {Path(file_path).name}"

        return (
            f"Found duplication issues in {Path(file_path).name}: {', '.join(issues)}"
        )

    def analyze_cross_file_duplication(
        self, file_reports: List[DuplicationReport]
    ) -> List[DuplicateCodeBlock]:
        """Analyze duplication across multiple files."""
        cross_file_duplicates = []

        # Group validation patterns by type and content
        validation_groups = defaultdict(list)
        for report in file_reports:
            for pattern in report.validation_duplicates:
                key = f"{pattern.pattern_type}:{pattern.condition}"
                validation_groups[key].append((report.file_path, pattern))

        # Find cross-file validation duplicates
        for key, patterns in validation_groups.items():
            if len(patterns) > 1:
                content = f"Validation pattern: {key}"
                content_hash = hashlib.md5(content.encode()).hexdigest()

                locations = [
                    (file_path, pattern.line_number, pattern.line_number)
                    for file_path, pattern in patterns
                ]

                cross_file_duplicates.append(
                    DuplicateCodeBlock(
                        content=content,
                        content_hash=content_hash,
                        locations=locations,
                        similarity_score=1.0,
                        block_type="cross_file_validation",
                    )
                )

        return cross_file_duplicates

    def generate_aggregate_report(self, file_reports: List[DuplicationReport]) -> Dict:
        """Generate an aggregate duplication report across all files."""
        total_files = len(file_reports)
        files_with_duplicates = len(
            [
                r
                for r in file_reports
                if r.duplicate_blocks
                or r.validation_duplicates
                or r.import_analysis.unused_imports
            ]
        )

        total_validation_duplicates = sum(
            len(r.validation_duplicates) for r in file_reports
        )
        total_unused_imports = sum(
            len(r.import_analysis.unused_imports) for r in file_reports
        )
        total_duplicate_blocks = sum(len(r.duplicate_blocks) for r in file_reports)

        # Find cross-file duplicates
        cross_file_duplicates = self.analyze_cross_file_duplication(file_reports)

        return {
            "summary": {
                "total_files_analyzed": total_files,
                "files_with_duplication": files_with_duplicates,
                "total_validation_duplicates": total_validation_duplicates,
                "total_unused_imports": total_unused_imports,
                "total_duplicate_blocks": total_duplicate_blocks,
                "cross_file_duplicates": len(cross_file_duplicates),
            },
            "recommendations": self._generate_duplication_recommendations(
                total_validation_duplicates,
                total_unused_imports,
                total_duplicate_blocks,
                cross_file_duplicates,
            ),
        }

    def _generate_duplication_recommendations(
        self,
        validation_count: int,
        unused_imports: int,
        duplicate_blocks: int,
        cross_file_duplicates: List,
    ) -> List[str]:
        """Generate prioritized recommendations for addressing duplication."""
        recommendations = []

        if cross_file_duplicates:
            recommendations.append(
                f"HIGH PRIORITY: Extract {len(cross_file_duplicates)} common validation patterns into shared utilities"
            )

        if validation_count > 10:
            recommendations.append(
                f"MEDIUM PRIORITY: Consolidate {validation_count} validation patterns into reusable functions"
            )

        if unused_imports > 5:
            recommendations.append(
                f"LOW PRIORITY: Remove {unused_imports} unused import statements to clean up code"
            )

        if duplicate_blocks > 3:
            recommendations.append(
                f"MEDIUM PRIORITY: Refactor {duplicate_blocks} duplicate code blocks into shared functions"
            )

        if not recommendations:
            recommendations.append(
                "No significant code duplication detected - code organization is good"
            )

        return recommendations
