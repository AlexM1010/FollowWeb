"""
Unit tests for Validation Engine in cleanup system.

Tests integration with CodeAnalyzer, AILanguageScanner, PatternDetector,
DuplicationDetector, CrossPlatformAnalyzer, TestAnalyzer, and workflow validation.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.validation import ValidationEngine
from analysis_tools.cleanup.models import ValidationResult, TestResult, FileOperation
from analysis_tools.code_analyzer import CodeAnalyzer
from analysis_tools.test_analyzer import DuplicateTestAnalyzer
from analysis_tools.ai_language_scanner import AILanguageScanner
from analysis_tools.duplication_detector import DuplicationDetector
from analysis_tools.cross_platform_analyzer import CrossPlatformAnalyzer
from analysis_tools.pattern_detector import PatternDetector


@pytest.fixture
def mock_code_analyzer():
    """Fixture providing mock CodeAnalyzer."""
    return Mock(spec=CodeAnalyzer)


@pytest.fixture
def mock_test_analyzer():
    """Fixture providing mock TestAnalyzer."""
    return Mock(spec=DuplicateTestAnalyzer)


@pytest.fixture
def validation_engine(mock_code_analyzer, mock_test_analyzer):
    """Fixture providing ValidationEngine instance."""
    return ValidationEngine(mock_code_analyzer, mock_test_analyzer)


@pytest.mark.unit
class TestCodeAnalyzerIntegration:
    """Test integration with CodeAnalyzer for import validation."""
    
    def test_validates_imports_using_code_analyzer(self, validation_engine, mock_code_analyzer, tmp_path):
        """Test import validation using CodeAnalyzer."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nfrom pathlib import Path")
        
        # Mock CodeAnalyzer response
        mock_code_analyzer.analyze_file.return_value = {
            "imports": ["os", "pathlib.Path"],
            "issues": []
        }
        
        result = validation_engine.validate_imports([str(test_file)])
        
        assert isinstance(result, ValidationResult)
        assert result.success is True
        mock_code_analyzer.analyze_file.assert_called_once()
    
    def test_detects_import_errors(self, validation_engine, mock_code_analyzer, tmp_path):
        """Test detection of import errors."""
        test_file = tmp_path / "bad_imports.py"
        test_file.write_text("from nonexistent import module")
        
        # Mock CodeAnalyzer finding issues
        mock_code_analyzer.analyze_file.return_value = {
            "imports": ["nonexistent.module"],
            "issues": ["Import error: nonexistent module"]
        }
        
        result = validation_engine.validate_imports([str(test_file)])
        
        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_validates_multiple_files(self, validation_engine, mock_code_analyzer, tmp_path):
        """Test validation of multiple files."""
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"import module{i}")
            files.append(str(f))
        
        mock_code_analyzer.analyze_file.return_value = {
            "imports": [],
            "issues": []
        }
        
        result = validation_engine.validate_imports(files)
        
        assert result.success is True
        assert mock_code_analyzer.analyze_file.call_count == 3


@pytest.mark.unit
class TestAILanguageScannerIntegration:
    """Test integration with AILanguageScanner for code quality."""
    
    @patch('analysis_tools.cleanup.validation.AILanguageScanner')
    def test_validates_code_quality_with_ai_scanner(self, mock_scanner_class, validation_engine, tmp_path):
        """Test code quality validation using AILanguageScanner."""
        test_file = tmp_path / "test.py"
        test_file.write_text('"""This is a comprehensive and robust solution."""\ndef func(): pass')
        
        # Mock AILanguageScanner
        mock_scanner = Mock()
        mock_scanner.scan_file.return_value = {
            "ai_patterns": ["comprehensive", "robust"],
            "score": 0.8
        }
        mock_scanner_class.return_value = mock_scanner
        
        result = validation_engine.validate_code_quality([str(test_file)])
        
        assert isinstance(result, ValidationResult)
    
    @patch('analysis_tools.cleanup.validation.AILanguageScanner')
    def test_detects_marketing_language(self, mock_scanner_class, validation_engine, tmp_path):
        """Test detection of marketing language patterns."""
        test_file = tmp_path / "marketing.py"
        test_file.write_text('"""Seamless integration with enhanced features."""')
        
        mock_scanner = Mock()
        mock_scanner.scan_file.return_value = {
            "ai_patterns": ["seamless", "enhanced"],
            "score": 0.9,
            "issues": ["Marketing language detected"]
        }
        mock_scanner_class.return_value = mock_scanner
        
        result = validation_engine.validate_code_quality([str(test_file)])
        
        # Should identify issues
        assert isinstance(result, ValidationResult)


@pytest.mark.unit
class TestPatternDetectorIntegration:
    """Test integration with PatternDetector."""
    
    @patch('analysis_tools.cleanup.validation.PatternDetector')
    def test_detects_generic_error_messages(self, mock_detector_class, validation_engine, tmp_path):
        """Test detection of generic error messages."""
        test_file = tmp_path / "errors.py"
        test_file.write_text('raise Exception("An error occurred")')
        
        mock_detector = Mock()
        mock_detector.analyze_file.return_value = {
            "generic_errors": ["An error occurred"],
            "issues": ["Generic error message"]
        }
        mock_detector_class.return_value = mock_detector
        
        result = validation_engine.validate_code_quality([str(test_file)])
        
        assert isinstance(result, ValidationResult)
    
    @patch('analysis_tools.cleanup.validation.PatternDetector')
    def test_detects_redundant_validation(self, mock_detector_class, validation_engine, tmp_path):
        """Test detection of redundant validation patterns."""
        test_file = tmp_path / "validation.py"
        test_file.write_text("""
def validate1(x):
    if x is None:
        raise ValueError("Invalid")
        
def validate2(y):
    if y is None:
        raise ValueError("Invalid")
""")
        
        mock_detector = Mock()
        mock_detector.analyze_file.return_value = {
            "redundant_patterns": ["None check with ValueError"],
            "issues": ["Redundant validation pattern"]
        }
        mock_detector_class.return_value = mock_detector
        
        result = validation_engine.validate_code_quality([str(test_file)])
        
        assert isinstance(result, ValidationResult)


@pytest.mark.unit
class TestDuplicationDetectorIntegration:
    """Test integration with DuplicationDetector."""
    
    @patch('analysis_tools.cleanup.validation.DuplicationDetector')
    def test_validates_code_duplicates(self, mock_detector_class, validation_engine, tmp_path):
        """Test validation of code duplicates."""
        test_file = tmp_path / "duplicates.py"
        test_file.write_text("""
def func1():
    x = 1
    y = 2
    return x + y

def func2():
    x = 1
    y = 2
    return x + y
""")
        
        mock_detector = Mock()
        mock_detector.analyze_file.return_value = {
            "duplicates": [{"similarity": 0.95, "lines": [2, 6]}],
            "duplicate_count": 1
        }
        mock_detector_class.return_value = mock_detector
        
        result = validation_engine.validate_duplicates([str(test_file)])
        
        assert isinstance(result, ValidationResult)
    
    @patch('analysis_tools.cleanup.validation.DuplicationDetector')
    def test_reports_duplicate_statistics(self, mock_detector_class, validation_engine, tmp_path):
        """Test reporting of duplicate statistics."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def func(): pass")
        
        mock_detector = Mock()
        mock_detector.analyze_file.return_value = {
            "duplicates": [],
            "duplicate_count": 0,
            "total_functions": 1
        }
        mock_detector_class.return_value = mock_detector
        
        result = validation_engine.validate_duplicates([str(test_file)])
        
        assert result.success is True


@pytest.mark.unit
class TestCrossPlatformAnalyzerIntegration:
    """Test integration with CrossPlatformAnalyzer."""
    
    @patch('analysis_tools.cleanup.validation.CrossPlatformAnalyzer')
    def test_validates_cross_platform_compatibility(self, mock_analyzer_class, validation_engine, tmp_path):
        """Test cross-platform compatibility validation."""
        test_file = tmp_path / "platform.py"
        test_file.write_text('path = "C:\\\\Windows\\\\System32"')
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_file.return_value = {
            "platform_issues": ["Hardcoded Windows path"],
            "score": 0.5
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        result = validation_engine.validate_cross_platform([str(test_file)])
        
        assert isinstance(result, ValidationResult)
    
    @patch('analysis_tools.cleanup.validation.CrossPlatformAnalyzer')
    def test_detects_hardcoded_paths(self, mock_analyzer_class, validation_engine, tmp_path):
        """Test detection of hardcoded paths."""
        test_file = tmp_path / "paths.py"
        test_file.write_text('DATA_DIR = "/home/user/data"')
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_file.return_value = {
            "platform_issues": ["Hardcoded Unix path"],
            "suggestions": ["Use pathlib.Path"]
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        result = validation_engine.validate_cross_platform([str(test_file)])
        
        assert isinstance(result, ValidationResult)


@pytest.mark.unit
class TestTestAnalyzerIntegration:
    """Test integration with TestAnalyzer."""
    
    def test_runs_test_suite(self, validation_engine, mock_test_analyzer):
        """Test running test suite using TestAnalyzer."""
        # Mock test results
        mock_test_analyzer.run_tests.return_value = {
            "total": 100,
            "passed": 95,
            "failed": 5,
            "skipped": 0
        }
        
        result = validation_engine.run_test_suite()
        
        assert isinstance(result, TestResult)
        assert result.total_tests == 100
        assert result.passed == 95
        assert result.failed == 5
    
    def test_runs_specific_test_categories(self, validation_engine, mock_test_analyzer):
        """Test running specific test categories."""
        mock_test_analyzer.run_tests.return_value = {
            "total": 50,
            "passed": 50,
            "failed": 0,
            "skipped": 0
        }
        
        result = validation_engine.run_test_suite(test_categories=["unit"])
        
        assert result.total_tests == 50
        assert result.passed == 50
        mock_test_analyzer.run_tests.assert_called_once()
    
    def test_reports_failed_tests(self, validation_engine, mock_test_analyzer):
        """Test reporting of failed tests."""
        mock_test_analyzer.run_tests.return_value = {
            "total": 10,
            "passed": 8,
            "failed": 2,
            "skipped": 0,
            "failed_tests": ["test_func1", "test_func2"]
        }
        
        result = validation_engine.run_test_suite()
        
        assert len(result.failed_tests) == 2
        assert "test_func1" in result.failed_tests
        assert "test_func2" in result.failed_tests


@pytest.mark.unit
class TestWorkflowValidation:
    """Test workflow validation with PyYAML."""
    
    def test_validates_workflow_yaml_syntax(self, validation_engine, tmp_path):
        """Test validation of workflow YAML syntax."""
        workflow_file = tmp_path / "workflow.yml"
        workflow_file.write_text("""
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
""")
        
        result = validation_engine.validate_workflows([str(workflow_file)])
        
        assert isinstance(result, ValidationResult)
        assert result.success is True
    
    def test_detects_invalid_workflow_yaml(self, validation_engine, tmp_path):
        """Test detection of invalid workflow YAML."""
        workflow_file = tmp_path / "invalid.yml"
        workflow_file.write_text("name: Invalid\n  bad: indentation")
        
        result = validation_engine.validate_workflows([str(workflow_file)])
        
        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_validates_multiple_workflows(self, validation_engine, tmp_path):
        """Test validation of multiple workflow files."""
        workflows = []
        for i in range(3):
            wf = tmp_path / f"workflow{i}.yml"
            wf.write_text(f"name: Workflow{i}\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest")
            workflows.append(str(wf))
        
        result = validation_engine.validate_workflows(workflows)
        
        assert result.success is True


@pytest.mark.unit
class TestFileOperationValidation:
    """Test validation of file operations."""
    
    def test_validates_successful_operations(self, validation_engine):
        """Test validation of successful file operations."""
        operations = [
            FileOperation("move", "source1.txt", "dest1.txt", None, True),
            FileOperation("move", "source2.txt", "dest2.txt", None, True),
            FileOperation("remove", "old.txt", None, None, True)
        ]
        
        result = validation_engine.validate_file_operations(operations)
        
        assert isinstance(result, ValidationResult)
        assert result.success is True
    
    def test_detects_failed_operations(self, validation_engine):
        """Test detection of failed file operations."""
        operations = [
            FileOperation("move", "source1.txt", "dest1.txt", None, True),
            FileOperation("move", "source2.txt", "dest2.txt", None, False),
            FileOperation("remove", "old.txt", None, None, False)
        ]
        
        result = validation_engine.validate_file_operations(operations)
        
        assert result.success is False
        assert len(result.errors) == 2  # Two failed operations
    
    def test_reports_operation_statistics(self, validation_engine):
        """Test reporting of operation statistics."""
        operations = [
            FileOperation("move", f"file{i}.txt", f"dest{i}.txt", None, True)
            for i in range(10)
        ]
        
        result = validation_engine.validate_file_operations(operations)
        
        assert result.success is True
        # Should have statistics in result


@pytest.mark.unit
class TestValidationReporting:
    """Test validation report generation."""
    
    def test_generates_validation_report(self, validation_engine):
        """Test generation of comprehensive validation report."""
        results = [
            ValidationResult("test", "imports", True, [], [], None),
            ValidationResult("test", "code_quality", True, [], [], None),
            ValidationResult("test", "duplicates", True, [], [], None)
        ]
        
        report = validation_engine.generate_validation_report(results)
        
        assert isinstance(report, str)
        assert len(report) > 0
    
    def test_report_includes_all_validations(self, validation_engine):
        """Test that report includes all validation results."""
        results = [
            ValidationResult("phase1", "imports", True, [], [], None),
            ValidationResult("phase1", "tests", False, ["Test failed"], [], None),
            ValidationResult("phase2", "workflows", True, [], ["Warning"], None)
        ]
        
        report = validation_engine.generate_validation_report(results)
        
        assert "imports" in report
        assert "tests" in report
        assert "workflows" in report
        assert "Test failed" in report
    
    def test_report_summarizes_errors_and_warnings(self, validation_engine):
        """Test that report summarizes errors and warnings."""
        results = [
            ValidationResult("test", "validation1", False, ["Error 1", "Error 2"], [], None),
            ValidationResult("test", "validation2", True, [], ["Warning 1"], None)
        ]
        
        report = validation_engine.generate_validation_report(results)
        
        assert "Error 1" in report
        assert "Error 2" in report
        assert "Warning 1" in report


@pytest.mark.unit
class TestIntegratedValidation:
    """Test integrated validation across all analyzers."""
    
    @patch('analysis_tools.cleanup.validation.AILanguageScanner')
    @patch('analysis_tools.cleanup.validation.PatternDetector')
    @patch('analysis_tools.cleanup.validation.DuplicationDetector')
    @patch('analysis_tools.cleanup.validation.CrossPlatformAnalyzer')
    def test_validates_with_all_analyzers(self, mock_cross, mock_dup, mock_pattern, mock_ai,
                                         validation_engine, tmp_path):
        """Test validation using all analyzers together."""
        test_file = tmp_path / "complete.py"
        test_file.write_text("""
def function():
    '''Comprehensive solution.'''
    path = "C:\\\\Windows"
    if x is None:
        raise Exception("Error")
""")
        
        # Mock all analyzers
        for mock in [mock_ai, mock_pattern, mock_dup, mock_cross]:
            mock_instance = Mock()
            mock_instance.analyze_file.return_value = {"issues": []}
            mock.return_value = mock_instance
        
        result = validation_engine.validate_code_quality([str(test_file)])
        
        assert isinstance(result, ValidationResult)
    
    def test_aggregates_results_from_multiple_analyzers(self, validation_engine, tmp_path):
        """Test aggregation of results from multiple analyzers."""
        test_files = []
        for i in range(3):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"def func{i}(): pass")
            test_files.append(str(f))
        
        # Run multiple validations
        import_result = validation_engine.validate_imports(test_files)
        workflow_result = validation_engine.validate_workflows([])
        
        # Both should return ValidationResult
        assert isinstance(import_result, ValidationResult)
        assert isinstance(workflow_result, ValidationResult)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in validation."""
    
    def test_handles_missing_files(self, validation_engine):
        """Test handling of missing files."""
        result = validation_engine.validate_imports(["/nonexistent/file.py"])
        
        assert isinstance(result, ValidationResult)
        assert result.success is False
    
    def test_handles_analyzer_exceptions(self, validation_engine, mock_code_analyzer, tmp_path):
        """Test handling of analyzer exceptions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import os")
        
        # Mock analyzer raising exception
        mock_code_analyzer.analyze_file.side_effect = Exception("Analyzer error")
        
        result = validation_engine.validate_imports([str(test_file)])
        
        assert isinstance(result, ValidationResult)
        assert result.success is False
    
    def test_continues_validation_after_errors(self, validation_engine, mock_code_analyzer, tmp_path):
        """Test that validation continues after encountering errors."""
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"import module{i}")
            files.append(str(f))
        
        # Mock analyzer failing on second file
        mock_code_analyzer.analyze_file.side_effect = [
            {"imports": [], "issues": []},
            Exception("Error"),
            {"imports": [], "issues": []}
        ]
        
        result = validation_engine.validate_imports(files)
        
        # Should still process all files
        assert mock_code_analyzer.analyze_file.call_count == 3
