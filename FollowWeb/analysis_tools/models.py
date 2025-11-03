"""
Data models for analysis results and reporting.
"""

# Standard library imports
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IssueType(Enum):
    """Types of code issues that can be detected."""

    AI_LANGUAGE = "ai_language"
    DUPLICATION = "duplication"
    DEAD_CODE = "dead_code"
    REDUNDANT_VALIDATION = "redundant_validation"
    IMPORT_ISSUES = "import_issues"
    ERROR_HANDLING = "error_handling"


class Severity(Enum):
    """Severity levels for detected issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationType(Enum):
    """Types of refactoring opportunities."""

    EXTRACT_UTILITY = "extract_utility"
    CONSOLIDATE_VALIDATION = "consolidate_validation"
    STANDARDIZE_IMPORTS = "standardize_imports"
    IMPROVE_ERROR_HANDLING = "improve_error_handling"
    REMOVE_DUPLICATION = "remove_duplication"


class DuplicateTestAction(Enum):
    """Actions that can be taken on duplicate tests."""

    REMOVE = "remove"
    CONSOLIDATE = "consolidate"
    KEEP_BEST = "keep_best"


@dataclass
class CodeLocation:
    """Represents a location in source code."""

    file_path: str
    line_number: int
    column: Optional[int] = None
    end_line: Optional[int] = None


@dataclass
class CodeIssue:
    """Represents a detected code quality issue."""

    issue_type: IssueType
    location: CodeLocation
    description: str
    severity: Severity
    fix_suggestion: Optional[str] = None
    context: Optional[str] = None


@dataclass
class OptimizationOpportunity:
    """Represents an opportunity for code refactoring."""

    opportunity_type: OptimizationType
    impact_level: str
    effort_required: str
    description: str
    implementation_plan: list[str]
    affected_files: list[str]


@dataclass
class CodeMetrics:
    """Code quality metrics for a file or module."""

    lines_of_code: int
    complexity_score: float
    duplication_percentage: float
    import_count: int
    function_count: int
    class_count: int


@dataclass
class AnalysisResult:
    """Complete analysis result for a file."""

    file_path: str
    issues: list[CodeIssue]
    refactoring_opportunities: list[OptimizationOpportunity]
    metrics: CodeMetrics
    ai_language_count: int = 0
    duplicate_code_blocks: list[str] = field(default_factory=list)


@dataclass
class DuplicateTestGroup:
    """Group of duplicate or similar tests."""

    test_names: list[str]
    similarity_score: float
    recommended_action: DuplicateTestAction
    primary_test: str
    file_paths: list[str]


@dataclass
class DuplicateTestAnalysisResult:
    """Analysis result for test files."""

    test_file: str
    duplicate_tests: list[DuplicateTestGroup]
    unused_fixtures: list[str]
    redundant_imports: list[str]
    test_count: int
    coverage_gaps: list[str] = field(default_factory=list)


# Removed BackupInfo class
