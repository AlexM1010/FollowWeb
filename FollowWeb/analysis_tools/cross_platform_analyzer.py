"""
Cross-Platform Test Compatibility Analyzer for identifying platform-specific issues.

This module analyzes test files for cross-platform compatibility issues including:
- Hardcoded path separators and platform-specific paths
- Improper temporary file and directory handling
- Tests that may fail on different operating systems
- Missing platform-specific conditionals and skip markers
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .models import Severity


@dataclass
class PlatformIssue:
    """Represents a platform compatibility issue."""

    issue_type: str
    file_path: str
    line_number: int
    column: int
    description: str
    problematic_code: str
    fix_suggestion: str
    affected_platforms: List[str]
    severity: Severity


@dataclass
class PathIssue:
    """Represents a path-related compatibility issue."""

    file_path: str
    line_number: int
    current_implementation: str
    issue_description: str
    fix_recommendation: str
    platforms_affected: List[str]


@dataclass
class TempFileIssue:
    """Represents a temporary file handling issue."""

    file_path: str
    line_number: int
    current_code: str
    issue_type: str  # 'hardcoded_path', 'no_cleanup', 'platform_specific'
    recommended_solution: str


@dataclass
class CrossPlatformReport:
    """Comprehensive cross-platform compatibility report."""

    file_path: str
    platform_issues: List[PlatformIssue]
    path_issues: List[PathIssue]
    temp_file_issues: List[TempFileIssue]
    missing_skip_markers: List[Tuple[str, int, str]]  # (function_name, line, reason)
    ci_compatibility_score: float
    summary: str


class CrossPlatformAnalyzer:
    """Analyzer for cross-platform test compatibility issues."""

    def __init__(self):
        """Initialize the cross-platform analyzer."""
        self.path_patterns = self._initialize_path_patterns()
        self.temp_file_patterns = self._initialize_temp_file_patterns()
        self.platform_specific_patterns = self._initialize_platform_patterns()
        self.ci_patterns = self._initialize_ci_patterns()

    def _initialize_path_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for detecting path-related issues."""
        return {
            "hardcoded_separators": [
                r'["\'][^"\']*\\[^"\']*["\']',  # Backslash in strings
                r'["\'][^"\']*\/[^"\']*["\']',  # Forward slash in strings (when not URL)
                r'\.split\(["\']\\["\']',  # split('\\')
                r'\.split\(["\']\/["\']',  # split('/')
                r'\.join\(["\']\\["\']',  # join('\\')
                r'\.join\(["\']\/["\']',  # join('/')
            ],
            "absolute_paths": [
                r'["\']\/[^"\']*["\']',  # Unix absolute paths
                r'["\'][A-Za-z]:\\[^"\']*["\']',  # Windows absolute paths
                r'["\']\/tmp\/[^"\']*["\']',  # /tmp/ paths
                r'["\']\/var\/[^"\']*["\']',  # /var/ paths
                r'["\']C:\\[^"\']*["\']',  # C:\ paths
            ],
            "problematic_paths": [
                r'["\']\.\.\/[^"\']*["\']',  # Relative paths with ../
                r'["\'][^"\']*~[^"\']*["\']',  # Home directory references
                r"os\.getcwd\(\)",  # Current working directory
                r"os\.chdir\(",  # Change directory
            ],
        }

    def _initialize_temp_file_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for temporary file handling issues."""
        return {
            "hardcoded_temp_paths": [
                r'["\']\/tmp\/[^"\']*["\']',
                r'["\']\/var\/tmp\/[^"\']*["\']',
                r'["\']C:\\temp\\[^"\']*["\']',
                r'["\']C:\\tmp\\[^"\']*["\']',
                r'["\']\.\/temp\/[^"\']*["\']',
                r'["\']\.\/tmp\/[^"\']*["\']',
            ],
            "missing_tempfile_usage": [
                r'open\(["\'][^"\']*temp[^"\']*["\']',
                r'open\(["\'][^"\']*tmp[^"\']*["\']',
                r'mkdir\(["\'][^"\']*temp[^"\']*["\']',
                r'mkdir\(["\'][^"\']*tmp[^"\']*["\']',
            ],
            "no_cleanup_patterns": [
                r"tempfile\.mktemp\(",
                r"tempfile\.mkdtemp\(",
                r"NamedTemporaryFile.*delete=False",
            ],
        }

    def _initialize_platform_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for platform-specific code."""
        return {
            "platform_checks": [
                r"sys\.platform",
                r"platform\.system\(\)",
                r"os\.name",
                r"platform\.platform\(\)",
            ],
            "windows_specific": [
                r'\.exe["\']',
                r"cmd\.exe",
                r"powershell",
                r'\.bat["\']',
                r'\.cmd["\']',
                r"HKEY_",
                r"winreg\.",
                r"_winapi\.",
            ],
            "unix_specific": [
                r'\/bin\/[^"\']*',
                r'\/usr\/[^"\']*',
                r'\/etc\/[^"\']*',
                r"chmod\(",
                r"os\.fork\(",
                r"signal\.",
                r"pwd\.",
                r"grp\.",
            ],
        }

    def _initialize_ci_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for CI/CD environment issues."""
        return {
            "ci_environment_vars": [
                r"GITHUB_ACTIONS",
                r"TRAVIS",
                r"CIRCLECI",
                r"JENKINS_URL",
                r"CI",
            ],
            "resource_intensive": [
                r"time\.sleep\([^)]*[5-9]\d+",  # Sleep > 50 seconds
                r"\.timeout\([^)]*[5-9]\d+",  # Timeout > 50 seconds
                r"range\([^)]*\d{4,}",  # Large ranges
                r"for.*in.*range\([^)]*\d{3,}",  # Large loops
            ],
        }

    def analyze_file(self, file_path: str) -> CrossPlatformReport:
        """
        Analyze a test file for cross-platform compatibility issues.

        Args:
            file_path: Path to the test file to analyze

        Returns:
            CrossPlatformReport: Comprehensive compatibility analysis
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return CrossPlatformReport(
                file_path=file_path,
                platform_issues=[],
                path_issues=[],
                temp_file_issues=[],
                missing_skip_markers=[],
                ci_compatibility_score=0.0,
                summary=f"Error reading file: {e}",
            )

        # Analyze different types of compatibility issues
        platform_issues = self._analyze_platform_issues(content, file_path)
        path_issues = self._analyze_path_issues(content, file_path)
        temp_file_issues = self._analyze_temp_file_issues(content, file_path)
        missing_skip_markers = self._analyze_missing_skip_markers(content, file_path)

        # Calculate CI compatibility score
        ci_score = self._calculate_ci_compatibility_score(
            platform_issues, path_issues, temp_file_issues, missing_skip_markers
        )

        summary = self._generate_summary(
            file_path,
            platform_issues,
            path_issues,
            temp_file_issues,
            missing_skip_markers,
            ci_score,
        )

        return CrossPlatformReport(
            file_path=file_path,
            platform_issues=platform_issues,
            path_issues=path_issues,
            temp_file_issues=temp_file_issues,
            missing_skip_markers=missing_skip_markers,
            ci_compatibility_score=ci_score,
            summary=summary,
        )

    def _analyze_platform_issues(
        self, content: str, file_path: str
    ) -> List[PlatformIssue]:
        """Analyze general platform-specific issues."""
        issues = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for Windows-specific code without platform checks
            for pattern in self.platform_specific_patterns["windows_specific"]:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Check if there's a platform check nearby
                    if not self._has_nearby_platform_check(lines, line_num - 1, 5):
                        issues.append(
                            PlatformIssue(
                                issue_type="windows_specific_without_check",
                                file_path=file_path,
                                line_number=line_num,
                                column=match.start(),
                                description=f"Windows-specific code without platform check: {match.group()}",
                                problematic_code=line.strip(),
                                fix_suggestion="Add platform check or use cross-platform alternative",
                                affected_platforms=["unix", "macos"],
                                severity=Severity.HIGH,
                            )
                        )

            # Check for Unix-specific code without platform checks
            for pattern in self.platform_specific_patterns["unix_specific"]:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    if not self._has_nearby_platform_check(lines, line_num - 1, 5):
                        issues.append(
                            PlatformIssue(
                                issue_type="unix_specific_without_check",
                                file_path=file_path,
                                line_number=line_num,
                                column=match.start(),
                                description=f"Unix-specific code without platform check: {match.group()}",
                                problematic_code=line.strip(),
                                fix_suggestion="Add platform check or use cross-platform alternative",
                                affected_platforms=["windows"],
                                severity=Severity.HIGH,
                            )
                        )

        return issues

    def _analyze_path_issues(self, content: str, file_path: str) -> List[PathIssue]:
        """Analyze path-related compatibility issues."""
        issues = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for hardcoded path separators
            for pattern in self.path_patterns["hardcoded_separators"]:
                matches = re.finditer(pattern, line)
                for match in matches:
                    # Skip URLs and regex patterns
                    matched_text = match.group()
                    if "http" in matched_text.lower() or "regex" in line.lower():
                        continue

                    issues.append(
                        PathIssue(
                            file_path=file_path,
                            line_number=line_num,
                            current_implementation=matched_text,
                            issue_description="Hardcoded path separator",
                            fix_recommendation="Use pathlib.Path or os.path.join() for cross-platform paths",
                            platforms_affected=["windows", "unix", "macos"],
                        )
                    )

            # Check for absolute paths
            for pattern in self.path_patterns["absolute_paths"]:
                matches = re.finditer(pattern, line)
                for match in matches:
                    matched_text = match.group()
                    if "http" in matched_text.lower():  # Skip URLs
                        continue

                    issues.append(
                        PathIssue(
                            file_path=file_path,
                            line_number=line_num,
                            current_implementation=matched_text,
                            issue_description="Hardcoded absolute path",
                            fix_recommendation="Use relative paths or platform-agnostic path construction",
                            platforms_affected=["windows", "unix", "macos"],
                        )
                    )

        return issues

    def _analyze_temp_file_issues(
        self, content: str, file_path: str
    ) -> List[TempFileIssue]:
        """Analyze temporary file handling issues."""
        issues = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for hardcoded temp paths
            for pattern in self.temp_file_patterns["hardcoded_temp_paths"]:
                matches = re.finditer(pattern, line)
                for _match in matches:
                    issues.append(
                        TempFileIssue(
                            file_path=file_path,
                            line_number=line_num,
                            current_code=line.strip(),
                            issue_type="hardcoded_path",
                            recommended_solution="Use tempfile.TemporaryDirectory() or tempfile.mkdtemp()",
                        )
                    )

            # Check for missing tempfile module usage
            for pattern in self.temp_file_patterns["missing_tempfile_usage"]:
                matches = re.finditer(pattern, line)
                for _match in matches:
                    issues.append(
                        TempFileIssue(
                            file_path=file_path,
                            line_number=line_num,
                            current_code=line.strip(),
                            issue_type="missing_tempfile_usage",
                            recommended_solution="Use tempfile module for cross-platform temporary file handling",
                        )
                    )

            # Check for potential cleanup issues
            for pattern in self.temp_file_patterns["no_cleanup_patterns"]:
                matches = re.finditer(pattern, line)
                for _match in matches:
                    issues.append(
                        TempFileIssue(
                            file_path=file_path,
                            line_number=line_num,
                            current_code=line.strip(),
                            issue_type="no_cleanup",
                            recommended_solution="Use context managers or ensure proper cleanup of temporary files",
                        )
                    )

        return issues

    def _analyze_missing_skip_markers(
        self, content: str, file_path: str
    ) -> List[Tuple[str, int, str]]:
        """Analyze for missing pytest skip markers on platform-specific tests."""
        missing_markers = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return missing_markers

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                # Check if function has platform-specific code
                func_source = ast.get_source_segment(content, node)
                if not func_source:
                    continue

                has_platform_code = False
                has_skip_marker = False

                # Check for platform-specific patterns in function
                for category, patterns in self.platform_specific_patterns.items():
                    if category == "platform_checks":
                        continue
                    for pattern in patterns:
                        if re.search(pattern, func_source, re.IGNORECASE):
                            has_platform_code = True
                            break
                    if has_platform_code:
                        break

                # Check for existing skip markers
                if node.decorator_list:
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Attribute):
                            if (
                                isinstance(decorator.value, ast.Name)
                                and decorator.value.id == "pytest"
                                and decorator.attr in ["skip", "skipif"]
                            ):
                                has_skip_marker = True
                                break
                        elif isinstance(decorator, ast.Call):
                            if (
                                isinstance(decorator.func, ast.Attribute)
                                and isinstance(decorator.func.value, ast.Name)
                                and decorator.func.value.id == "pytest"
                                and decorator.func.attr in ["skip", "skipif"]
                            ):
                                has_skip_marker = True
                                break

                # Report missing skip marker
                if has_platform_code and not has_skip_marker:
                    missing_markers.append(
                        (
                            node.name,
                            node.lineno,
                            "Function contains platform-specific code but lacks pytest.skipif marker",
                        )
                    )

        return missing_markers

    def _has_nearby_platform_check(
        self, lines: List[str], line_index: int, search_range: int
    ) -> bool:
        """Check if there's a platform check within the specified range."""
        start = max(0, line_index - search_range)
        end = min(len(lines), line_index + search_range + 1)

        for i in range(start, end):
            line = lines[i]
            for pattern in self.platform_specific_patterns["platform_checks"]:
                if re.search(pattern, line):
                    return True

        return False

    def _calculate_ci_compatibility_score(
        self,
        platform_issues: List[PlatformIssue],
        path_issues: List[PathIssue],
        temp_file_issues: List[TempFileIssue],
        missing_skip_markers: List[Tuple],
    ) -> float:
        """Calculate a CI/CD compatibility score (0-100)."""
        total_issues = (
            len(platform_issues)
            + len(path_issues)
            + len(temp_file_issues)
            + len(missing_skip_markers)
        )

        if total_issues == 0:
            return 100.0

        # Weight different types of issues
        weighted_score = 0
        weighted_score -= len(platform_issues) * 15  # High impact
        weighted_score -= len(path_issues) * 10  # Medium impact
        weighted_score -= len(temp_file_issues) * 8  # Medium impact
        weighted_score -= len(missing_skip_markers) * 5  # Lower impact

        # Start from 100 and subtract penalties
        score = max(0, 100 + weighted_score)
        return round(score, 1)

    def _generate_summary(
        self,
        file_path: str,
        platform_issues: List[PlatformIssue],
        path_issues: List[PathIssue],
        temp_file_issues: List[TempFileIssue],
        missing_skip_markers: List[Tuple],
        ci_score: float,
    ) -> str:
        """Generate a summary of cross-platform compatibility analysis."""
        issues = []

        if platform_issues:
            issues.append(f"{len(platform_issues)} platform-specific issues")

        if path_issues:
            issues.append(f"{len(path_issues)} path compatibility issues")

        if temp_file_issues:
            issues.append(f"{len(temp_file_issues)} temporary file issues")

        if missing_skip_markers:
            issues.append(f"{len(missing_skip_markers)} missing skip markers")

        if not issues:
            return f"Excellent cross-platform compatibility in {Path(file_path).name} (Score: {ci_score}/100)"

        return f"Cross-platform issues in {Path(file_path).name}: {', '.join(issues)} (Score: {ci_score}/100)"

    def analyze_directory(
        self, directory_path: str, test_pattern: str = "test_*.py"
    ) -> Dict[str, CrossPlatformReport]:
        """
        Analyze all test files in a directory for cross-platform compatibility.

        Args:
            directory_path: Path to directory containing test files
            test_pattern: Pattern to match test files

        Returns:
            Dict mapping file paths to their compatibility reports
        """
        results = {}
        directory = Path(directory_path)

        # Find test files
        test_files = list(directory.rglob(test_pattern))

        for test_file in test_files:
            # Skip __pycache__ and other excluded directories
            if any(
                exclude in str(test_file)
                for exclude in ["__pycache__", ".git", ".pytest_cache"]
            ):
                continue

            try:
                report = self.analyze_file(str(test_file))
                results[str(test_file)] = report
            except Exception as e:
                results[str(test_file)] = CrossPlatformReport(
                    file_path=str(test_file),
                    platform_issues=[],
                    path_issues=[],
                    temp_file_issues=[],
                    missing_skip_markers=[],
                    ci_compatibility_score=0.0,
                    summary=f"Analysis error: {e}",
                )

        return results

    def generate_aggregate_report(
        self, reports: Dict[str, CrossPlatformReport]
    ) -> Dict:
        """Generate an aggregate cross-platform compatibility report."""
        total_files = len(reports)
        files_with_issues = len(
            [
                r
                for r in reports.values()
                if r.platform_issues
                or r.path_issues
                or r.temp_file_issues
                or r.missing_skip_markers
            ]
        )

        total_platform_issues = sum(len(r.platform_issues) for r in reports.values())
        total_path_issues = sum(len(r.path_issues) for r in reports.values())
        total_temp_issues = sum(len(r.temp_file_issues) for r in reports.values())
        total_missing_markers = sum(
            len(r.missing_skip_markers) for r in reports.values()
        )

        average_ci_score = (
            sum(r.ci_compatibility_score for r in reports.values()) / total_files
            if total_files > 0
            else 0
        )

        # Find most problematic files
        problematic_files = sorted(
            [(path, report.ci_compatibility_score) for path, report in reports.items()],
            key=lambda x: x[1],
        )[:10]

        return {
            "summary": {
                "total_test_files": total_files,
                "files_with_compatibility_issues": files_with_issues,
                "average_ci_compatibility_score": round(average_ci_score, 1),
                "total_platform_issues": total_platform_issues,
                "total_path_issues": total_path_issues,
                "total_temp_file_issues": total_temp_issues,
                "total_missing_skip_markers": total_missing_markers,
            },
            "most_problematic_files": problematic_files,
            "recommendations": self._generate_compatibility_recommendations(
                total_platform_issues,
                total_path_issues,
                total_temp_issues,
                total_missing_markers,
            ),
        }

    def _generate_compatibility_recommendations(
        self,
        platform_issues: int,
        path_issues: int,
        temp_issues: int,
        missing_markers: int,
    ) -> List[str]:
        """Generate prioritized recommendations for improving cross-platform compatibility."""
        recommendations = []

        if platform_issues > 0:
            recommendations.append(
                f"HIGH PRIORITY: Fix {platform_issues} platform-specific issues by adding proper platform checks or using cross-platform alternatives"
            )

        if path_issues > 5:
            recommendations.append(
                f"HIGH PRIORITY: Replace {path_issues} hardcoded paths with pathlib.Path or os.path.join() for cross-platform compatibility"
            )

        if temp_issues > 0:
            recommendations.append(
                f"MEDIUM PRIORITY: Fix {temp_issues} temporary file handling issues using the tempfile module"
            )

        if missing_markers > 0:
            recommendations.append(
                f"LOW PRIORITY: Add {missing_markers} pytest.skipif markers for platform-specific tests"
            )

        if not recommendations:
            recommendations.append(
                "Excellent cross-platform compatibility - no significant issues detected"
            )

        return recommendations
