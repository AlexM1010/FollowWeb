"""
Analysis tools for comprehensive code quality assessment.

This package provides utilities for analyzing Python code, detecting patterns,
identifying optimization opportunities, and supporting safe refactoring operations.
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

__all__ = [
    "AILanguageScanner",
    "AnalysisOrchestrator",
    "CodeAnalyzer",
    "CrossPlatformAnalyzer",
    "DuplicationDetector",
    "PatternDetector",
    "DuplicateTestAnalyzer",
    "ast_utils",
]
