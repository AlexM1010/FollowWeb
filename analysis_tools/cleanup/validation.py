"""
Validation Engine for cleanup operations.

This module provides comprehensive validation capabilities for cleanup operations,
leveraging existing analysis_tools components for code quality checks.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from ..ai_language_scanner import AILanguageScanner
from ..code_analyzer import CodeAnalyzer
from ..cross_platform_analyzer import CrossPlatformAnalyzer
from ..duplication_detector import DuplicationDetector
from ..pattern_detector import PatternDetector
from ..test_analyzer import DuplicateTestAnalyzer
from .models import FileOperation, TestResult, ValidationResult


class ValidationEngine:
    """
    Validation engine for cleanup operations.
    
    Integrates with existing analysis_tools components to provide comprehensive
    validation of code quality, imports, tests, and workflows.
    """

    def __init__(
        self,
        code_analyzer: Optional[CodeAnalyzer] = None,
        test_analyzer: Optional[DuplicateTestAnalyzer] = None,
    ):
        """
        Initialize validation engine with analysis tools.
        
        Args:
            code_analyzer: CodeAnalyzer instance for import validation
            test_analyzer: DuplicateTestAnalyzer instance for test validation
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.test_analyzer = test_analyzer or DuplicateTestAnalyzer()
        self.ai_scanner = AILanguageScanner()
        self.duplication_detector = DuplicationDetector()
        self.cross_platform_analyzer = CrossPlatformAnalyzer()
        self.pattern_detector = PatternDetector()

    def validate_imports(self, changed_files: List[str]) -> ValidationResult:
        """
        Validate Python imports using CodeAnalyzer.
        
        Args:
            changed_files: List of Python files to validate
            
        Returns:
            ValidationResult with import validation status
        """
        errors = []
        warnings = []
        
        for file_path in changed_files:
            path = Path(file_path)
            if not path.exists():
                errors.append(f"File not found: {file_path}")
                continue
                
            if not path.suffix == ".py":
                continue
                
            try:
                # Use CodeAnalyzer to analyze imports
                result = self.code_analyzer.analyze_file(file_path)
                
                # Check for import-related issues
                for issue in result.issues:
                    if "import" in issue.description.lower():
                        if issue.severity.value == "critical":
                            errors.append(
                                f"{file_path}:{issue.location.line}: {issue.description}"
                            )
                        else:
                            warnings.append(
                                f"{file_path}:{issue.location.line}: {issue.description}"
                            )
            except Exception as e:
                errors.append(f"Error analyzing {file_path}: {str(e)}")
        
        return ValidationResult(
            phase="import_validation",
            validation_type="imports",
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    def validate_code_quality(
        self, changed_files: List[str]
    ) -> ValidationResult:
        """
        Validate code quality using AILanguageScanner and PatternDetector.
        
        Args:
            changed_files: List of Python files to validate
            
        Returns:
            ValidationResult with code quality status
        """
        errors = []
        warnings = []
        
        for file_path in changed_files:
            path = Path(file_path)
            if not path.exists() or not path.suffix == ".py":
                continue
                
            try:
                # Scan for AI language patterns
                ai_report = self.ai_scanner.scan_file(file_path)
                if ai_report.total_matches > 0:
                    warnings.append(
                        f"{file_path}: Found {ai_report.total_matches} AI language patterns"
                    )
                
                # Detect generic patterns
                pattern_report = self.pattern_detector.analyze_file(file_path)
                if pattern_report.generic_messages:
                    warnings.append(
                        f"{file_path}: Found {len(pattern_report.generic_messages)} generic error messages"
                    )
                if pattern_report.redundant_validations:
                    warnings.append(
                        f"{file_path}: Found {len(pattern_report.redundant_validations)} redundant validations"
                    )
            except Exception as e:
                warnings.append(f"Error analyzing {file_path}: {str(e)}")
        
        return ValidationResult(
            phase="code_quality",
            validation_type="quality",
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    def validate_duplicates(self, changed_files: List[str]) -> ValidationResult:
        """
        Validate code duplicates using DuplicationDetector.
        
        Args:
            changed_files: List of Python files to validate
            
        Returns:
            ValidationResult with duplication status
        """
        errors = []
        warnings = []
        
        for file_path in changed_files:
            path = Path(file_path)
            if not path.exists() or not path.suffix == ".py":
                continue
                
            try:
                # Detect code duplication
                dup_report = self.duplication_detector.analyze_file(file_path)
                
                if dup_report.duplicate_blocks:
                    warnings.append(
                        f"{file_path}: Found {len(dup_report.duplicate_blocks)} duplicate code blocks"
                    )
                if dup_report.validation_duplicates:
                    warnings.append(
                        f"{file_path}: Found {len(dup_report.validation_duplicates)} duplicate validations"
                    )
            except Exception as e:
                warnings.append(f"Error analyzing {file_path}: {str(e)}")
        
        return ValidationResult(
            phase="duplication",
            validation_type="duplicates",
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    def validate_cross_platform(
        self, changed_files: List[str]
    ) -> ValidationResult:
        """
        Validate cross-platform compatibility using CrossPlatformAnalyzer.
        
        Args:
            changed_files: List of Python files to validate
            
        Returns:
            ValidationResult with cross-platform compatibility status
        """
        errors = []
        warnings = []
        
        for file_path in changed_files:
            path = Path(file_path)
            if not path.exists() or not path.suffix == ".py":
                continue
                
            try:
                # Analyze cross-platform compatibility
                cp_report = self.cross_platform_analyzer.analyze_file(file_path)
                
                if cp_report.platform_issues:
                    for issue in cp_report.platform_issues:
                        if issue.severity.value == "critical":
                            errors.append(
                                f"{file_path}:{issue.line_number}: {issue.description}"
                            )
                        else:
                            warnings.append(
                                f"{file_path}:{issue.line_number}: {issue.description}"
                            )
                
                if cp_report.path_issues:
                    warnings.append(
                        f"{file_path}: Found {len(cp_report.path_issues)} path compatibility issues"
                    )
            except Exception as e:
                warnings.append(f"Error analyzing {file_path}: {str(e)}")
        
        return ValidationResult(
            phase="cross_platform",
            validation_type="platform",
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    def run_test_suite(
        self, test_categories: Optional[List[str]] = None
    ) -> TestResult:
        """
        Execute test suite to verify functionality.
        
        Args:
            test_categories: Optional list of test categories to run
            
        Returns:
            TestResult with test execution status
        """
        try:
            # Build pytest command
            cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
            
            if test_categories:
                for category in test_categories:
                    cmd.extend(["-m", category])
            
            # Run tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            
            # Parse pytest output
            output = result.stdout + result.stderr
            
            # Extract test counts (simple parsing)
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            skipped = output.count(" SKIPPED")
            
            # Extract failed test names
            failed_tests = []
            for line in output.split("\n"):
                if "FAILED" in line:
                    # Extract test name from line like "test_file.py::test_name FAILED"
                    parts = line.split("::")
                    if len(parts) >= 2:
                        test_name = parts[1].split()[0]
                        failed_tests.append(test_name)
            
            return TestResult(
                total_tests=passed + failed + skipped,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=None,  # Could parse from pytest output
                failed_tests=failed_tests,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                duration=None,
                failed_tests=["Test suite timed out"],
            )
        except Exception as e:
            return TestResult(
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                duration=None,
                failed_tests=[f"Error running tests: {str(e)}"],
            )

    def validate_workflows(
        self, workflow_files: List[str]
    ) -> ValidationResult:
        """
        Validate workflow YAML syntax and configuration using PyYAML.
        
        Args:
            workflow_files: List of workflow YAML files to validate
            
        Returns:
            ValidationResult with workflow validation status
        """
        errors = []
        warnings = []
        
        for workflow_path in workflow_files:
            path = Path(workflow_path)
            if not path.exists():
                errors.append(f"Workflow file not found: {workflow_path}")
                continue
                
            try:
                with open(path, "r", encoding="utf-8") as f:
                    workflow_data = yaml.safe_load(f)
                
                # Basic validation checks
                if not isinstance(workflow_data, dict):
                    errors.append(f"{workflow_path}: Invalid workflow structure")
                    continue
                
                # Check for required fields
                if "name" not in workflow_data:
                    warnings.append(f"{workflow_path}: Missing 'name' field")
                
                if "on" not in workflow_data:
                    errors.append(f"{workflow_path}: Missing 'on' trigger field")
                
                if "jobs" not in workflow_data:
                    errors.append(f"{workflow_path}: Missing 'jobs' field")
                
            except yaml.YAMLError as e:
                errors.append(f"{workflow_path}: YAML syntax error - {str(e)}")
            except Exception as e:
                errors.append(f"{workflow_path}: Validation error - {str(e)}")
        
        return ValidationResult(
            phase="workflow_validation",
            validation_type="workflows",
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    def validate_file_operations(
        self, operations: List[FileOperation]
    ) -> ValidationResult:
        """
        Validate file operations completed successfully.
        
        Args:
            operations: List of file operations to validate
            
        Returns:
            ValidationResult with file operation status
        """
        errors = []
        warnings = []
        
        for op in operations:
            if not op.success:
                errors.append(
                    f"Failed operation: {op.operation} {op.source} -> {op.destination}"
                )
                continue
            
            # Verify destination exists for move/copy operations
            if op.operation in ["move", "copy"] and op.destination:
                dest_path = Path(op.destination)
                if not dest_path.exists():
                    errors.append(
                        f"Destination not found after {op.operation}: {op.destination}"
                    )
            
            # Verify source removed for move operations
            if op.operation == "move":
                source_path = Path(op.source)
                if source_path.exists():
                    warnings.append(
                        f"Source still exists after move: {op.source}"
                    )
        
        return ValidationResult(
            phase="file_operations",
            validation_type="operations",
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(),
        )

    def generate_validation_report(
        self, results: List[ValidationResult]
    ) -> str:
        """
        Generate comprehensive validation report.
        
        Args:
            results: List of validation results
            
        Returns:
            Formatted validation report as string
        """
        report_lines = [
            "=" * 80,
            "VALIDATION REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            "",
        ]
        
        # Summary
        total_validations = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total_validations - successful
        
        report_lines.extend([
            "SUMMARY",
            "-" * 80,
            f"Total Validations: {total_validations}",
            f"Successful: {successful}",
            f"Failed: {failed}",
            "",
        ])
        
        # Detailed results
        report_lines.extend([
            "DETAILED RESULTS",
            "-" * 80,
        ])
        
        for result in results:
            status = "✓ PASS" if result.success else "✗ FAIL"
            report_lines.extend([
                f"\n{status} - {result.phase} ({result.validation_type})",
                f"Timestamp: {result.timestamp.isoformat()}",
            ])
            
            if result.errors:
                report_lines.append(f"\nErrors ({len(result.errors)}):")
                for error in result.errors:
                    report_lines.append(f"  - {error}")
            
            if result.warnings:
                report_lines.append(f"\nWarnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    report_lines.append(f"  - {warning}")
        
        report_lines.extend([
            "",
            "=" * 80,
        ])
        
        return "\n".join(report_lines)
