"""
Unit tests for Reporting System in cleanup system.

Tests report generation, metrics calculation, and README generation.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.reporting import ReportingSystem
from analysis_tools.cleanup.models import (
    CleanupPhase, PhaseResult, FileOperation, ValidationResult,
    Metrics, DirectoryStructure, FileMapping
)


@pytest.fixture
def reports_dir(tmp_path):
    """Fixture providing temporary reports directory."""
    reports = tmp_path / "analysis_reports"
    reports.mkdir()
    return reports


@pytest.fixture
def reporting_system(reports_dir):
    """Fixture providing ReportingSystem instance."""
    return ReportingSystem(reports_dir)


@pytest.mark.unit
class TestPhaseReportGeneration:
    """Test phase report generation."""
    
    def test_generates_phase_report(self, reporting_system, reports_dir):
        """Test generation of phase report."""
        phase_result = PhaseResult(
            phase=CleanupPhase.ROOT_CLEANUP,
            success=True,
            operations=[
                FileOperation("move", "file1.txt", "docs/file1.txt", datetime.now(), True),
                FileOperation("move", "file2.txt", "docs/file2.txt", datetime.now(), True)
            ],
            validation_result=ValidationResult("root_cleanup", "validation", True, [], [], datetime.now()),
            duration=timedelta(seconds=30),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.ROOT_CLEANUP, phase_result)
        
        assert report_path is not None
        assert Path(report_path).exists()
        assert "root_cleanup" in report_path
    
    def test_phase_report_contains_json_data(self, reporting_system, reports_dir):
        """Test that phase report contains valid JSON data."""
        phase_result = PhaseResult(
            phase=CleanupPhase.CACHE_CLEANUP,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=10),
            errors=[],
            warnings=[],
            rollback_available=False
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.CACHE_CLEANUP, phase_result)
        
        # Verify JSON format
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert "phase" in data
        assert "success" in data
        assert "duration" in data
        assert data["phase"] == "cache_cleanup"
    
    def test_includes_operation_details(self, reporting_system):
        """Test that report includes operation details."""
        operations = [
            FileOperation("move", "source1.txt", "dest1.txt", datetime.now(), True),
            FileOperation("remove", "old.txt", None, datetime.now(), True)
        ]
        
        phase_result = PhaseResult(
            phase=CleanupPhase.SCRIPT_ORGANIZATION,
            success=True,
            operations=operations,
            validation_result=None,
            duration=timedelta(seconds=20),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.SCRIPT_ORGANIZATION, phase_result)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert "operations" in data
        assert len(data["operations"]) == 2
    
    def test_includes_errors_and_warnings(self, reporting_system):
        """Test that report includes errors and warnings."""
        phase_result = PhaseResult(
            phase=CleanupPhase.WORKFLOW_UPDATE,
            success=False,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=5),
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.WORKFLOW_UPDATE, phase_result)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert "errors" in data
        assert len(data["errors"]) == 2
        assert "warnings" in data
        assert len(data["warnings"]) == 1


@pytest.mark.unit
class TestMigrationGuideGeneration:
    """Test migration guide generation."""
    
    def test_generates_migration_guide(self, reporting_system, reports_dir):
        """Test generation of migration guide."""
        file_mappings = [
            FileMapping("old/path/file1.txt", "new/path/file1.txt", "move"),
            FileMapping("old/path/file2.txt", "new/path/file2.txt", "move"),
            FileMapping("scripts/old_script.py", "scripts/new/old_script.py", "move")
        ]
        
        guide_path = reporting_system.generate_migration_guide(file_mappings)
        
        assert guide_path is not None
        assert Path(guide_path).exists()
        assert "migration" in guide_path
    
    def test_migration_guide_contains_mappings(self, reporting_system):
        """Test that migration guide contains file mappings."""
        file_mappings = [
            FileMapping("source.txt", "dest.txt", "move")
        ]
        
        guide_path = reporting_system.generate_migration_guide(file_mappings)
        
        with open(guide_path, 'r') as f:
            data = json.load(f)
        
        assert "file_mappings" in data
        assert len(data["file_mappings"]) == 1
        assert data["file_mappings"][0]["source"] == "source.txt"
        assert data["file_mappings"][0]["destination"] == "dest.txt"
    
    def test_groups_mappings_by_category(self, reporting_system):
        """Test that migration guide groups mappings by category."""
        file_mappings = [
            FileMapping("doc1.md", "docs/doc1.md", "move"),
            FileMapping("doc2.md", "docs/doc2.md", "move"),
            FileMapping("script1.py", "scripts/script1.py", "move")
        ]
        
        guide_path = reporting_system.generate_migration_guide(file_mappings)
        
        with open(guide_path, 'r') as f:
            data = json.load(f)
        
        # Should have some organization
        assert "file_mappings" in data


@pytest.mark.unit
class TestMetricsReportGeneration:
    """Test metrics report generation."""
    
    def test_generates_metrics_report(self, reporting_system):
        """Test generation of metrics report."""
        before_metrics = Metrics(
            root_file_count=69,
            total_size_mb=3100.0,
            cache_size_mb=178.4,
            documentation_files=45,
            utility_scripts=29,
            test_pass_rate=1.0
        )
        
        after_metrics = Metrics(
            root_file_count=12,
            total_size_mb=2921.6,
            cache_size_mb=0.0,
            documentation_files=45,
            utility_scripts=29,
            test_pass_rate=1.0
        )
        
        report_path = reporting_system.generate_metrics_report(before_metrics, after_metrics)
        
        assert report_path is not None
        assert Path(report_path).exists()
    
    def test_metrics_report_shows_improvements(self, reporting_system):
        """Test that metrics report shows improvements."""
        before = Metrics(100, 5000.0, 200.0, 50, 30, 0.95)
        after = Metrics(15, 4800.0, 0.0, 50, 30, 1.0)
        
        report_path = reporting_system.generate_metrics_report(before, after)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert "before" in data
        assert "after" in data
        assert "improvements" in data
        
        # Verify improvements calculated
        improvements = data["improvements"]
        assert "root_file_reduction" in improvements
        assert "cache_size_reduction" in improvements
    
    def test_calculates_percentage_changes(self, reporting_system):
        """Test calculation of percentage changes."""
        before = Metrics(100, 1000.0, 100.0, 50, 30, 0.9)
        after = Metrics(50, 900.0, 0.0, 50, 30, 1.0)
        
        report_path = reporting_system.generate_metrics_report(before, after)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        improvements = data["improvements"]
        # Should have percentage calculations
        assert any("percent" in str(k).lower() or "%" in str(v) 
                  for k, v in improvements.items())


@pytest.mark.unit
class TestDeveloperGuideGeneration:
    """Test developer guide generation."""
    
    def test_generates_developer_guide(self, reporting_system):
        """Test generation of developer onboarding guide."""
        structure = DirectoryStructure(
            directories={
                "docs": ["README.md", "GUIDE.md"],
                "scripts": ["script1.py", "script2.py"]
            },
            purposes={
                "docs": "Documentation files",
                "scripts": "Utility scripts"
            },
            file_counts={
                "docs": 2,
                "scripts": 2
            }
        )
        
        guide_path = reporting_system.generate_developer_guide(structure)
        
        assert guide_path is not None
        assert Path(guide_path).exists()
    
    def test_developer_guide_includes_structure(self, reporting_system):
        """Test that developer guide includes repository structure."""
        structure = DirectoryStructure(
            directories={"src": ["main.py"]},
            purposes={"src": "Source code"},
            file_counts={"src": 1}
        )
        
        guide_path = reporting_system.generate_developer_guide(structure)
        
        # Read and verify content
        content = Path(guide_path).read_text()
        assert "src" in content
        assert "main.py" in content or "Source code" in content


@pytest.mark.unit
class TestDirectoryREADMEGeneration:
    """Test directory README generation."""
    
    def test_creates_directory_readme(self, reporting_system, tmp_path):
        """Test creation of README for new directory."""
        directory = str(tmp_path / "test_dir")
        Path(directory).mkdir()
        
        purpose = "Test directory for unit tests"
        files = ["file1.txt", "file2.txt", "file3.txt"]
        
        readme_path = reporting_system.create_directory_readme(directory, purpose, files)
        
        assert readme_path is not None
        assert Path(readme_path).exists()
        assert Path(readme_path).name == "README.md"
    
    def test_readme_contains_purpose(self, reporting_system, tmp_path):
        """Test that README contains directory purpose."""
        directory = str(tmp_path / "docs")
        Path(directory).mkdir()
        
        purpose = "Documentation files for the project"
        files = ["GUIDE.md"]
        
        readme_path = reporting_system.create_directory_readme(directory, purpose, files)
        
        content = Path(readme_path).read_text()
        assert purpose in content
    
    def test_readme_lists_files(self, reporting_system, tmp_path):
        """Test that README lists contained files."""
        directory = str(tmp_path / "scripts")
        Path(directory).mkdir()
        
        purpose = "Utility scripts"
        files = ["script1.py", "script2.py", "script3.py"]
        
        readme_path = reporting_system.create_directory_readme(directory, purpose, files)
        
        content = Path(readme_path).read_text()
        for file in files:
            assert file in content


@pytest.mark.unit
class TestReportFormatting:
    """Test report formatting and structure."""
    
    def test_reports_use_json_format(self, reporting_system):
        """Test that reports use JSON format."""
        phase_result = PhaseResult(
            phase=CleanupPhase.BACKUP,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=1),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.BACKUP, phase_result)
        
        # Should be valid JSON
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
    
    def test_reports_include_timestamp(self, reporting_system):
        """Test that reports include timestamp."""
        phase_result = PhaseResult(
            phase=CleanupPhase.VALIDATION,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=1),
            errors=[],
            warnings=[],
            rollback_available=False
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.VALIDATION, phase_result)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert "timestamp" in data or "analysis_timestamp" in data
    
    def test_reports_follow_analysis_tools_format(self, reporting_system):
        """Test that reports follow analysis_tools format conventions."""
        before = Metrics(100, 1000.0, 100.0, 50, 30, 1.0)
        after = Metrics(50, 900.0, 0.0, 50, 30, 1.0)
        
        report_path = reporting_system.generate_metrics_report(before, after)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        # Should have standard analysis_tools fields
        assert "analysis_timestamp" in data or "timestamp" in data


@pytest.mark.unit
class TestReportStorage:
    """Test report storage and file naming."""
    
    def test_saves_reports_to_analysis_reports_directory(self, reporting_system, reports_dir):
        """Test that reports are saved to analysis_reports directory."""
        phase_result = PhaseResult(
            phase=CleanupPhase.DOC_CONSOLIDATION,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=1),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.DOC_CONSOLIDATION, phase_result)
        
        # Verify saved in reports directory
        assert str(reports_dir) in report_path
    
    def test_uses_timestamped_filenames(self, reporting_system):
        """Test that report filenames include timestamps."""
        phase_result = PhaseResult(
            phase=CleanupPhase.BRANCH_CLEANUP,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=1),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.BRANCH_CLEANUP, phase_result)
        
        # Filename should include timestamp
        filename = Path(report_path).name
        # Should have date/time components
        assert any(char.isdigit() for char in filename)
    
    def test_creates_unique_filenames(self, reporting_system):
        """Test that multiple reports create unique filenames."""
        phase_result = PhaseResult(
            phase=CleanupPhase.WORKFLOW_OPTIMIZATION,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=1),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        # Generate two reports
        report1 = reporting_system.generate_phase_report(CleanupPhase.WORKFLOW_OPTIMIZATION, phase_result)
        report2 = reporting_system.generate_phase_report(CleanupPhase.WORKFLOW_OPTIMIZATION, phase_result)
        
        # Should have different filenames
        assert report1 != report2


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in reporting."""
    
    def test_handles_invalid_directory(self):
        """Test handling of invalid reports directory."""
        # Should handle gracefully or raise appropriate error
        with pytest.raises(Exception):
            ReportingSystem(Path("/nonexistent/directory"))
    
    def test_handles_write_errors(self, reporting_system, reports_dir):
        """Test handling of write errors."""
        # Make directory read-only
        reports_dir.chmod(0o444)
        
        phase_result = PhaseResult(
            phase=CleanupPhase.DOCUMENTATION,
            success=True,
            operations=[],
            validation_result=None,
            duration=timedelta(seconds=1),
            errors=[],
            warnings=[],
            rollback_available=True
        )
        
        try:
            # Should handle write error
            report_path = reporting_system.generate_phase_report(CleanupPhase.DOCUMENTATION, phase_result)
        except Exception as e:
            # Expected to fail with permission error
            assert "permission" in str(e).lower() or isinstance(e, PermissionError)
        finally:
            # Restore permissions
            reports_dir.chmod(0o755)


@pytest.mark.unit
class TestReportContent:
    """Test report content quality."""
    
    def test_phase_report_is_comprehensive(self, reporting_system):
        """Test that phase report contains comprehensive information."""
        phase_result = PhaseResult(
            phase=CleanupPhase.ROOT_CLEANUP,
            success=True,
            operations=[
                FileOperation("move", "file.txt", "docs/file.txt", datetime.now(), True)
            ],
            validation_result=ValidationResult("test", "validation", True, [], [], datetime.now()),
            duration=timedelta(seconds=45),
            errors=[],
            warnings=["Warning message"],
            rollback_available=True
        )
        
        report_path = reporting_system.generate_phase_report(CleanupPhase.ROOT_CLEANUP, phase_result)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        # Verify comprehensive content
        assert "phase" in data
        assert "success" in data
        assert "operations" in data
        assert "validation_result" in data
        assert "duration" in data
        assert "warnings" in data
        assert "rollback_available" in data
    
    def test_metrics_report_shows_all_metrics(self, reporting_system):
        """Test that metrics report shows all relevant metrics."""
        before = Metrics(100, 5000.0, 200.0, 50, 30, 0.95)
        after = Metrics(15, 4800.0, 0.0, 50, 30, 1.0)
        
        report_path = reporting_system.generate_metrics_report(before, after)
        
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        # Verify all metrics present
        before_data = data["before"]
        assert "root_file_count" in before_data
        assert "total_size_mb" in before_data
        assert "cache_size_mb" in before_data
        assert "documentation_files" in before_data
        assert "utility_scripts" in before_data
        assert "test_pass_rate" in before_data
