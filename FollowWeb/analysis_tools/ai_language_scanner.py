"""
AI Language Pattern Scanner for detecting and reporting AI-generated language artifacts.

This module provides comprehensive scanning capabilities to identify overused adjectives,
marketing-style language, and generic AI-generated phrases in Python source code.
"""

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .models import Severity


@dataclass
class AILanguageMatch:
    """Represents a detected AI language pattern match."""

    pattern: str
    matched_text: str
    line_number: int
    column: int
    context: str
    category: str
    severity: Severity
    suggested_replacement: Optional[str] = None


@dataclass
class AILanguageReport:
    """Comprehensive report of AI language usage in a file."""

    file_path: str
    total_matches: int
    matches_by_category: Dict[str, int]
    matches_by_severity: Dict[str, int]
    all_matches: List[AILanguageMatch]
    summary: str


class AILanguageScanner:
    """Scanner for detecting AI-generated language patterns in Python code."""

    def __init__(self):
        """Initialize the AI language scanner with comprehensive pattern definitions."""
        self.ai_patterns = self._initialize_comprehensive_patterns()
        self.replacement_suggestions = self._initialize_replacements()
        self.python_keywords = self._get_python_keywords()

    def _get_python_keywords(self) -> set:
        """Get set of Python keywords and common programming terms to exclude from AI pattern matching."""
        return {
            # Python keywords
            "return",
            "yield",
            "pass",
            "break",
            "continue",
            "import",
            "from",
            "def",
            "class",
            "if",
            "else",
            "elif",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
            "as",
            "and",
            "or",
            "not",
            "in",
            "is",
            "lambda",
            "global",
            "nonlocal",
            "assert",
            "del",
            "raise",
            # Common programming terms that shouldn't be flagged
            "function",
            "method",
            "variable",
            "parameter",
            "argument",
            "value",
            "data",
            "result",
            "response",
            "request",
            "error",
            "exception",
            "status",
            "code",
            "message",
            "type",
            "object",
            "instance",
            "attribute",
            "property",
            "module",
            "package",
            "library",
            "framework",
            "application",
            "system",
            "process",
            "thread",
            "file",
            "path",
            "directory",
        }

    def _initialize_comprehensive_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize comprehensive AI language detection patterns."""
        return {
            "overused_adjectives": {
                "patterns": [
                    r"\bcomprehensive\b",
                    r"\benhanced\b",
                    r"\brobust\b",
                    r"\bseamless\b",
                    r"\bcutting-edge\b",
                    r"\bstate-of-the-art\b",
                    r"\bpowerful\b",
                    r"\badvanced\b",
                    r"\bsophisticated\b",
                    r"\boptimized\b",
                    r"\bstreamlined\b",
                    r"\befficient\b",
                    r"\bflexible\b",
                    r"\bscalable\b",
                    r"\binnovative\b",
                    r"\bversatile\b",
                    r"\bdynamic\b",
                    r"\bintelligent\b",
                    r"\belegant\b",
                    r"\bmodular\b",
                    r"\bextensible\b",
                    r"\bmaintainable\b",
                    r"\breliable\b",
                    r"\bperformant\b",
                    r"\buser-friendly\b",
                    r"\bintuitive\b",
                ],
                "severity": Severity.MEDIUM,
            },
            "marketing_phrases": {
                "patterns": [
                    r"best-in-class",
                    r"industry-leading",
                    r"world-class",
                    r"next-generation",
                    r"revolutionary",
                    r"game-changing",
                    r"breakthrough",
                    r"cutting edge",
                    r"state of the art",
                    r"enterprise-grade",
                    r"production-ready",
                    r"battle-tested",
                    r"mission-critical",
                ],
                "severity": Severity.HIGH,
            },
            "generic_descriptions": {
                "patterns": [
                    r"provides\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+functionality",
                    r"offers\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+capabilities",
                    r"delivers\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+performance",
                    r"ensures\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+quality",
                    r"enables\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+features",
                    r"facilitates\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+operations",
                    r"supports\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+requirements",
                    r"handles\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+scenarios",
                    r"manages\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+complexity",
                    r"optimizes\s+(?:comprehensive|enhanced|robust|advanced|sophisticated|powerful|flexible|scalable|innovative|versatile|dynamic|intelligent|elegant|modular|extensible|maintainable|reliable|performant|user-friendly|intuitive)\s+efficiency",
                ],
                "severity": Severity.LOW,
            },
            "redundant_qualifiers": {
                "patterns": [
                    r"fully.*compatible",
                    r"completely.*automated",
                    r"totally.*integrated",
                    r"entirely.*customizable",
                    r"highly.*configurable",
                    r"extremely.*flexible",
                    r"incredibly.*fast",
                    r"remarkably.*efficient",
                    r"exceptionally.*reliable",
                ],
                "severity": Severity.MEDIUM,
            },
            "vague_benefits": {
                "patterns": [
                    r"improves.*productivity",
                    r"increases.*efficiency",
                    r"reduces.*complexity",
                    r"enhances.*performance",
                    r"streamlines.*workflow",
                    r"simplifies.*process",
                    r"accelerates.*development",
                    r"maximizes.*potential",
                ],
                "severity": Severity.LOW,
            },
            "workflow_references": {
                "patterns": [
                    r"\bworkflow\s+\d+",
                    r"workflow\s+\w+",
                    r"this\s+workflow",
                    r"the\s+workflow",
                    r"workflow\s+is",
                    r"workflow\s+will",
                    r"workflow\s+should",
                    r"complete\s+workflow",
                    r"perform\s+workflow",
                    r"execute\s+workflow",
                    r"run\s+task",
                    r"task\s+execution",
                    r"task\s+completion",
                    r"task\s+management",
                    r"task\s+processing",
                ],
                "severity": Severity.HIGH,
            },
        }

    def _initialize_replacements(self) -> Dict[str, str]:
        """Initialize replacement suggestions for common AI phrases."""
        return {
            "comprehensive": "complete",
            "enhanced": "improved",
            "robust": "reliable",
            "seamless": "smooth",
            "cutting-edge": "modern",
            "state-of-the-art": "current",
            "powerful": "capable",
            "advanced": "complex",
            "sophisticated": "detailed",
            "optimized": "efficient",
            "streamlined": "simplified",
            "flexible": "adaptable",
            "scalable": "expandable",
            "innovative": "new",
            "versatile": "multi-purpose",
            "dynamic": "changing",
            "intelligent": "automated",
            "elegant": "clean",
            "modular": "component-based",
            "extensible": "expandable",
            "maintainable": "easy to maintain",
            "performant": "fast",
            "user-friendly": "easy to use",
            "intuitive": "straightforward",
        }

    def scan_file(self, file_path: str) -> AILanguageReport:
        """
        Scan a Python file for AI language patterns.

        Args:
            file_path: Path to the Python file to scan

        Returns:
            AILanguageReport: Comprehensive report of AI language usage
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return AILanguageReport(
                file_path=file_path,
                total_matches=0,
                matches_by_category={},
                matches_by_severity={},
                all_matches=[],
                summary=f"Error reading file: {e}",
            )

        all_matches = []

        # Scan docstrings and comments
        docstring_matches = self._scan_docstrings_and_comments(content, file_path)
        all_matches.extend(docstring_matches)

        # Scan string literals
        string_matches = self._scan_string_literals(content, file_path)
        all_matches.extend(string_matches)

        # Generate summary statistics
        matches_by_category = defaultdict(int)
        matches_by_severity = defaultdict(int)

        for match in all_matches:
            matches_by_category[match.category] += 1
            matches_by_severity[match.severity.value] += 1

        summary = self._generate_summary(file_path, all_matches, matches_by_category)

        return AILanguageReport(
            file_path=file_path,
            total_matches=len(all_matches),
            matches_by_category=dict(matches_by_category),
            matches_by_severity=dict(matches_by_severity),
            all_matches=all_matches,
            summary=summary,
        )

    def _scan_docstrings_and_comments(
        self, content: str, file_path: str
    ) -> List[AILanguageMatch]:
        """Scan docstrings and comments for AI language patterns."""
        matches = []
        lines = content.split("\n")

        in_docstring = False
        docstring_start = 0
        docstring_content = []

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Handle triple-quoted docstrings
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_start = line_num
                    docstring_content = [line]
                else:
                    in_docstring = False
                    docstring_content.append(line)

                    # Analyze complete docstring
                    full_docstring = "\n".join(docstring_content)
                    docstring_matches = self._find_patterns_in_text(
                        full_docstring, file_path, docstring_start
                    )
                    matches.extend(docstring_matches)

                    docstring_content = []
            elif in_docstring:
                docstring_content.append(line)

            # Handle single-line comments
            elif stripped.startswith("#"):
                comment_matches = self._find_patterns_in_text(line, file_path, line_num)
                matches.extend(comment_matches)

        return matches

    def _scan_string_literals(
        self, content: str, file_path: str
    ) -> List[AILanguageMatch]:
        """Scan string literals for AI language patterns using AST parsing."""
        matches = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Str):
                    # Python < 3.8 compatibility
                    string_value = node.s
                    line_num = node.lineno
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    # Python >= 3.8
                    string_value = node.value
                    line_num = node.lineno
                else:
                    continue

                # Skip very short strings
                if len(string_value.strip()) < 10:
                    continue

                string_matches = self._find_patterns_in_text(
                    string_value, file_path, line_num
                )
                matches.extend(string_matches)

        except SyntaxError:
            # If AST parsing fails, fall back to regex scanning
            matches.extend(self._scan_strings_with_regex(content, file_path))

        return matches

    def _scan_strings_with_regex(
        self, content: str, file_path: str
    ) -> List[AILanguageMatch]:
        """Fallback method to scan strings using regex when AST parsing fails."""
        matches = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Look for quoted strings
            string_patterns = [
                r'"""(.*?)"""',  # Triple double quotes
                r"'''(.*?)'''",  # Triple single quotes
                r'"([^"]*)"',  # Double quotes
                r"'([^']*)'",  # Single quotes
            ]

            for pattern in string_patterns:
                for match in re.finditer(pattern, line, re.DOTALL):
                    string_content = match.group(1)
                    if len(string_content.strip()) >= 10:
                        string_matches = self._find_patterns_in_text(
                            string_content, file_path, line_num
                        )
                        matches.extend(string_matches)

        return matches

    def _find_patterns_in_text(
        self, text: str, file_path: str, start_line: int
    ) -> List[AILanguageMatch]:
        """Find AI language patterns in a given text."""
        matches = []
        lines = text.split("\n")

        for line_offset, line in enumerate(lines):
            line_num = start_line + line_offset

            # Check each pattern category
            for category, config in self.ai_patterns.items():
                patterns = config["patterns"]
                severity = config["severity"]

                for pattern in patterns:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        matched_text = match.group()

                        # Skip matches that primarily contain Python keywords
                        if self._contains_primarily_python_keywords(matched_text):
                            continue

                        # Generate replacement suggestion
                        suggestion = self._get_replacement_suggestion(
                            matched_text, category
                        )

                        matches.append(
                            AILanguageMatch(
                                pattern=pattern,
                                matched_text=matched_text,
                                line_number=line_num,
                                column=match.start(),
                                context=line.strip(),
                                category=category,
                                severity=severity,
                                suggested_replacement=suggestion,
                            )
                        )

        return matches

    def _contains_primarily_python_keywords(self, text: str) -> bool:
        """Check if the matched text primarily contains Python keywords that should be excluded."""
        # Extract words from the matched text
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return False

        # Count how many words are Python keywords
        keyword_count = sum(1 for word in words if word in self.python_keywords)

        # If more than half the words are Python keywords, exclude this match
        return keyword_count > len(words) / 2

    def _get_replacement_suggestion(self, text: str, category: str) -> Optional[str]:
        """Get replacement suggestion for AI-generated text."""
        lower_text = text.lower().strip()

        # Direct replacement from dictionary
        if lower_text in self.replacement_suggestions:
            return self.replacement_suggestions[lower_text]

        # Category-specific suggestions
        if category == "marketing_phrases":
            return "Replace with specific technical description"
        elif category == "generic_descriptions":
            return "Replace with specific implementation details"
        elif category == "redundant_qualifiers":
            return "Remove qualifier or be more specific"
        elif category == "vague_benefits":
            return "Specify measurable benefits or outcomes"

        return "Replace with more specific technical terminology"

    def _generate_summary(
        self,
        file_path: str,
        matches: List[AILanguageMatch],
        category_counts: Dict[str, int],
    ) -> str:
        """Generate a summary of AI language usage in the file."""
        if not matches:
            return f"No AI language patterns detected in {Path(file_path).name}"

        total = len(matches)
        high_severity = len([m for m in matches if m.severity == Severity.HIGH])

        summary_parts = [
            f"Found {total} AI language pattern(s) in {Path(file_path).name}"
        ]

        if high_severity > 0:
            summary_parts.append(f"{high_severity} high-severity marketing phrases")

        if category_counts:
            top_categories = sorted(
                category_counts.items(), key=lambda x: x[1], reverse=True
            )[:3]
            category_summary = ", ".join(
                [f"{count} {cat.replace('_', ' ')}" for cat, count in top_categories]
            )
            summary_parts.append(f"Most common: {category_summary}")

        return "; ".join(summary_parts)

    def scan_directory(
        self, directory_path: str, exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, AILanguageReport]:
        """
        Scan all Python files in a directory for AI language patterns.

        Args:
            directory_path: Path to directory to scan
            exclude_patterns: List of patterns to exclude from scanning

        Returns:
            Dict mapping file paths to their AI language reports
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "__pycache__",
                ".git",
                ".pytest_cache",
                "venv",
                "env",
                ".tox",
                "build",
                "dist",
                ".mypy_cache",
            ]

        results = {}
        directory = Path(directory_path)

        for py_file in directory.rglob("*.py"):
            # Skip excluded patterns
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue

            try:
                report = self.scan_file(str(py_file))
                results[str(py_file)] = report
            except Exception as e:
                # Create error report for files that couldn't be scanned
                results[str(py_file)] = AILanguageReport(
                    file_path=str(py_file),
                    total_matches=0,
                    matches_by_category={},
                    matches_by_severity={},
                    all_matches=[],
                    summary=f"Scan error: {e}",
                )

        return results

    def generate_aggregate_report(
        self, scan_results: Dict[str, AILanguageReport]
    ) -> Dict:
        """
        Generate an aggregate report across all scanned files.

        Args:
            scan_results: Dictionary of file paths to their scan reports

        Returns:
            Dictionary containing aggregate statistics and recommendations
        """
        total_files = len(scan_results)
        files_with_issues = len(
            [r for r in scan_results.values() if r.total_matches > 0]
        )
        total_matches = sum(r.total_matches for r in scan_results.values())

        # Aggregate by category
        category_totals = defaultdict(int)
        severity_totals = defaultdict(int)

        for report in scan_results.values():
            for category, count in report.matches_by_category.items():
                category_totals[category] += count
            for severity, count in report.matches_by_severity.items():
                severity_totals[severity] += count

        # Find most problematic files
        problematic_files = sorted(
            [
                (path, report.total_matches)
                for path, report in scan_results.items()
                if report.total_matches > 0
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "summary": {
                "total_files_scanned": total_files,
                "files_with_ai_language": files_with_issues,
                "total_ai_patterns_found": total_matches,
                "average_patterns_per_file": (
                    round(total_matches / total_files, 2) if total_files > 0 else 0
                ),
            },
            "category_breakdown": dict(category_totals),
            "severity_breakdown": dict(severity_totals),
            "most_problematic_files": problematic_files,
            "recommendations": self._generate_cleanup_recommendations(
                category_totals, severity_totals
            ),
        }

    def _generate_cleanup_recommendations(
        self, category_totals: Dict[str, int], severity_totals: Dict[str, int]
    ) -> List[str]:
        """Generate prioritized cleanup recommendations."""
        recommendations = []

        high_severity_count = severity_totals.get("high", 0)
        if high_severity_count > 0:
            recommendations.append(
                f"HIGH PRIORITY: Remove {high_severity_count} marketing phrases - these significantly impact code professionalism"
            )

        overused_adj_count = category_totals.get("overused_adjectives", 0)
        if overused_adj_count > 10:
            recommendations.append(
                f"MEDIUM PRIORITY: Replace {overused_adj_count} overused adjectives with specific technical terms"
            )

        generic_desc_count = category_totals.get("generic_descriptions", 0)
        if generic_desc_count > 5:
            recommendations.append(
                f"LOW PRIORITY: Improve {generic_desc_count} generic descriptions with specific implementation details"
            )

        if not recommendations:
            recommendations.append(
                "No significant AI language issues detected - code language quality is good"
            )

        return recommendations
