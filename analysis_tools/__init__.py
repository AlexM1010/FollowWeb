"""
Analysis tools for complete code quality assessment.

This package provides utilities for analyzing Python code, detecting patterns,
identifying optimization opportunities, and supporting safe refactoring operations.
It also includes a complete cleanup system for repository reorganization.
"""

# Local imports
from . import ast_utils
from .ai_language_scanner import AILanguageScanner
from .analyzer import AnalysisOrchestrator
from .code_analyzer import CodeAnalyzer
from .cross_platform_analyzer import CrossPlatformAnalyzer
from .duplication_detector import DuplicationDetector
from .pattern_detector import PatternDetector
from .test_analyzer import DuplicateTestAnalyzer

# Cleanup system imports
from . import cleanup

__all__ = [
    "AILanguageScanner",
    "AnalysisOrchestrator",
    "CodeAnalyzer",
    "CrossPlatformAnalyzer",
    "DuplicationDetector",
    "PatternDetector",
    "DuplicateTestAnalyzer",
    "ast_utils",
    "cleanup",
]
