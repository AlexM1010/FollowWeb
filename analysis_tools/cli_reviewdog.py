"""
CLI wrappers for analysis_tools analyzers with reviewdog output support.

This module provides command-line interfaces for each analyzer that can output
results in reviewdog-compatible formats (rdjson, SARIF, GitHub Actions).

Usage:
    python -m analysis_tools.ai_language_scanner --format=reviewdog --diff-only
    python -m analysis_tools.duplication_detector --format=reviewdog --output=report.json
    python -m analysis_tools.cross_platform_analyzer --format=sarif
    python -m analysis_tools.pattern_detector --format=github-actions
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .reviewdog_formatter import ReviewdogFormatter, Severity
from .ai_language_scanner import AILanguageScanner
from .duplication_detector import DuplicationDetector
from .cross_platform_analyzer import CrossPlatformAnalyzer
from .pattern_detector import PatternDetector


def get_changed_files() -> List[str]:
    """
    Get list of changed files in current git diff.
    
    Returns:
        List of file paths that have been modified
    """
    import subprocess
    
    try:
        # Get changed files from git diff
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        files = [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]
        return files
    except subprocess.CalledProcessError:
        # Fallback: analyze all Python files
        return []


def run_ai_language_scanner(
    files: Optional[List[str]] = None,
    format_type: str = "rdjson",
    output_file: Optional[Path] = None,
    diff_only: bool = False
) -> int:
    """
    Run AI Language Scanner with reviewdog output.
    
    Args:
        files: List of files to analyze (None = all Python files)
        format_type: Output format ("rdjson", "sarif", "github-actions")
        output_file: Output file path (None = stdout)
        diff_only: Only analyze changed files in git diff
        
    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    scanner = AILanguageScanner()
    formatter = ReviewdogFormatter("ai-language")
    
    # Determine files to analyze
    if diff_only:
        files = get_changed_files()
        if not files:
            print("No changed Python files found", file=sys.stderr)
            return 0
    elif files is None:
        # Analyze all Python files in FollowWeb package
        files = list(Path("FollowWeb/FollowWeb_Visualizor").rglob("*.py"))
        files = [str(f) for f in files]
    
    # Analyze each file
    for file_path in files:
        try:
            report = scanner.scan_file(file_path)
            
            # Add issues to formatter
            for match in report.all_matches:
                severity = Severity.WARNING if match.severity.value == "warning" else Severity.INFO
                formatter.add_issue(
                    file_path=file_path,
                    line=match.line_number,
                    column=match.column,
                    message=f"AI language pattern detected: {match.matched_text} ({match.category})",
                    severity=severity,
                    code=f"AI{match.category.upper()[:3]}",
                    suggestion=match.suggested_replacement
                )
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
    
    # Output results
    if format_type == "rdjson":
        output = formatter.output_rdjson()
    elif format_type == "sarif":
        output = formatter.output_sarif()
    elif format_type == "github-actions":
        output = formatter.output_github_actions()
    else:
        print(f"Unknown format: {format_type}", file=sys.stderr)
        return 1
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output)
    else:
        print(output)
    
    # Save to analysis_reports if not already saved
    if not output_file or not str(output_file).startswith("analysis_reports"):
        formatter.save_to_analysis_reports(Path("analysis_reports"), format_type)
    
    return 1 if formatter.diagnostics else 0


def run_duplication_detector(
    files: Optional[List[str]] = None,
    format_type: str = "rdjson",
    output_file: Optional[Path] = None,
    diff_only: bool = False
) -> int:
    """
    Run Duplication Detector with reviewdog output.
    
    Args:
        files: List of files to analyze (None = all Python files)
        format_type: Output format ("rdjson", "sarif", "github-actions")
        output_file: Output file path (None = stdout)
        diff_only: Only analyze changed files in git diff
        
    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    detector = DuplicationDetector()
    formatter = ReviewdogFormatter("duplication")
    
    # Determine files to analyze
    if diff_only:
        files = get_changed_files()
        if not files:
            return 0
    elif files is None:
        files = list(Path("FollowWeb/FollowWeb_Visualizor").rglob("*.py"))
        files = [str(f) for f in files]
    
    # Analyze each file
    for file_path in files:
        try:
            report = detector.analyze_file(file_path)
            
            # Add duplication issues to formatter
            for dup in report.get("duplicates", []):
                formatter.add_issue(
                    file_path=file_path,
                    line=dup.get("line", 1),
                    column=1,
                    message=f"Code duplication detected: {dup.get('description', 'Duplicate code')}",
                    severity=Severity.WARNING,
                    code="DUP001"
                )
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
    
    # Output results
    if format_type == "rdjson":
        output = formatter.output_rdjson()
    elif format_type == "sarif":
        output = formatter.output_sarif()
    elif format_type == "github-actions":
        output = formatter.output_github_actions()
    else:
        return 1
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output)
    else:
        print(output)
    
    if not output_file or not str(output_file).startswith("analysis_reports"):
        formatter.save_to_analysis_reports(Path("analysis_reports"), format_type)
    
    return 1 if formatter.diagnostics else 0


def run_cross_platform_analyzer(
    files: Optional[List[str]] = None,
    format_type: str = "rdjson",
    output_file: Optional[Path] = None,
    diff_only: bool = False
) -> int:
    """
    Run Cross-Platform Analyzer with reviewdog output.
    
    Args:
        files: List of files to analyze (None = all Python files)
        format_type: Output format ("rdjson", "sarif", "github-actions")
        output_file: Output file path (None = stdout)
        diff_only: Only analyze changed files in git diff
        
    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    analyzer = CrossPlatformAnalyzer()
    formatter = ReviewdogFormatter("cross-platform")
    
    # Determine files to analyze
    if diff_only:
        files = get_changed_files()
        if not files:
            return 0
    elif files is None:
        files = list(Path("FollowWeb/FollowWeb_Visualizor").rglob("*.py"))
        files = [str(f) for f in files]
    
    # Analyze each file
    for file_path in files:
        try:
            report = analyzer.analyze_file(file_path)
            
            # Add cross-platform issues to formatter
            for issue in report.get("issues", []):
                formatter.add_issue(
                    file_path=file_path,
                    line=issue.get("line", 1),
                    column=1,
                    message=f"Cross-platform issue: {issue.get('description', 'Platform-specific code')}",
                    severity=Severity.WARNING,
                    code="XPLAT001",
                    suggestion=issue.get("suggestion")
                )
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
    
    # Output results
    if format_type == "rdjson":
        output = formatter.output_rdjson()
    elif format_type == "sarif":
        output = formatter.output_sarif()
    elif format_type == "github-actions":
        output = formatter.output_github_actions()
    else:
        return 1
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output)
    else:
        print(output)
    
    if not output_file or not str(output_file).startswith("analysis_reports"):
        formatter.save_to_analysis_reports(Path("analysis_reports"), format_type)
    
    return 1 if formatter.diagnostics else 0


def run_pattern_detector(
    files: Optional[List[str]] = None,
    format_type: str = "rdjson",
    output_file: Optional[Path] = None,
    diff_only: bool = False
) -> int:
    """
    Run Pattern Detector with reviewdog output.
    
    Args:
        files: List of files to analyze (None = all Python files)
        format_type: Output format ("rdjson", "sarif", "github-actions")
        output_file: Output file path (None = stdout)
        diff_only: Only analyze changed files in git diff
        
    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    detector = PatternDetector()
    formatter = ReviewdogFormatter("patterns")
    
    # Determine files to analyze
    if diff_only:
        files = get_changed_files()
        if not files:
            return 0
    elif files is None:
        files = list(Path("FollowWeb/FollowWeb_Visualizor").rglob("*.py"))
        files = [str(f) for f in files]
    
    # Analyze each file
    for file_path in files:
        try:
            report = detector.analyze_file(file_path)
            
            # Add pattern issues to formatter
            for pattern in report.get("patterns", []):
                formatter.add_issue(
                    file_path=file_path,
                    line=pattern.get("line", 1),
                    column=1,
                    message=f"Pattern detected: {pattern.get('description', 'Code pattern')}",
                    severity=Severity.INFO,
                    code="PAT001"
                )
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
    
    # Output results
    if format_type == "rdjson":
        output = formatter.output_rdjson()
    elif format_type == "sarif":
        output = formatter.output_sarif()
    elif format_type == "github-actions":
        output = formatter.output_github_actions()
    else:
        return 1
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output)
    else:
        print(output)
    
    if not output_file or not str(output_file).startswith("analysis_reports"):
        formatter.save_to_analysis_reports(Path("analysis_reports"), format_type)
    
    return 1 if formatter.diagnostics else 0


def create_cli_parser(analyzer_name: str) -> argparse.ArgumentParser:
    """
    Create argument parser for analyzer CLI.
    
    Args:
        analyzer_name: Name of the analyzer
        
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description=f"Run {analyzer_name} with reviewdog output support"
    )
    parser.add_argument(
        "--format",
        choices=["rdjson", "sarif", "github-actions"],
        default="rdjson",
        help="Output format (default: rdjson)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--diff-only",
        action="store_true",
        help="Only analyze changed files in git diff"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to analyze (default: all Python files)"
    )
    return parser
