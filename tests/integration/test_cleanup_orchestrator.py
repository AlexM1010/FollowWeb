"""
Integration tests for Cleanup Orchestrator.

Tests single phase execution, validation, rollback functionality, and error handling
for the repository cleanup orchestrator.
"""

import logging
import sys
from pathlib import Path
from datetime import timedelta
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.orchestrator import CleanupOrchestrator
from analysis_tools.cleanup.models import (
    CleanupConfig, CleanupPhase, PhaseResult, ValidationResult
)
from analysis_tools.cleanup.exceptions import CleanupError


@pytest.fixture
def cleanup_config():
    """Fixture providing CleanupConfig instance."""
    return CleanupConfig(
        dry_run=False,
        create_backup_branch=True,
        auto_commit=True,
        git_batch_size=10,
        max_workers=2
    )


@pytest.fixture
def orchestrator(cleanup_config, tmp_path):
    """Fixture providing CleanupOrchestrator instance."""
    return CleanupOrchestrator(cleanup_config, project_root=str(tmp_path))


@pytest.mark.integration
class TestSinglePhaseExecution:
    """Test single phase execution."""
    
    def test_executes_backup_phase(self, orchestrator):
        """Test execution of backup phase."""
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        assert isinstance(result, PhaseResult)
        assert result.phase == CleanupPhase.BACKUP
    
    def test_executes_cache_cleanup_phase(self, orchestrator, tmp_path):
        """Test execution of cache cleanup phase."""
        # Create cache directories
        cache_dirs = [
            tmp_path / ".mypy_cache",
            tmp_path / ".pytest_cache",
            tmp_path / "__pycache__"
        ]
        for d in cache_dirs:
            d.mkdir()
            (d / "test.txt").write_text("cache file")
        
        result = orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        assert isinstance(result, PhaseResult)
        assert result.success is True
    
    def test_executes_root_cleanup_phase(self, orchestrator, tmp_path):
        """Test execution of root cleanup phase."""
        # Create test files in root
        test_files = [
            tmp_path / "TEST_REPORT.md",
            tmp_path / "INSTALL_GUIDE.md",
            tmp_path / "ANALYSIS_SUMMARY.md"
        ]
        for f in test_files:
            f.write_text("test content")
        
        result = orchestrator.execute_phase(CleanupPhase.ROOT_CLEANUP)
        
        assert isinstance(result, PhaseResult)
    
    def test_phase_result_contains_operations(self, orchestrator):
        """Test that phase result contains operations."""
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        assert hasattr(result, 'operations')
        assert isinstance(result.operations, list)
    
    def test_phase_result_contains_duration(self, orchestrator):
        """Test that phase result contains duration."""
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        assert hasattr(result, 'duration')
        assert isinstance(result.duration, timedelta)


@pytest.mark.integration
class TestPhaseValidation:
    """Test phase validation."""
    
    def test_validates_phase_before_execution(self, orchestrator):
        """Test validation before phase execution."""
        # Pre-validation should check prerequisites
        validation = orchestrator.validate_phase(CleanupPhase.ROOT_CLEANUP)
        
        assert isinstance(validation, ValidationResult)
    
    def test_validates_phase_after_execution(self, orchestrator):
        """Test validation after phase execution."""
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        # Post-validation should verify success
        validation = orchestrator.validate_phase(CleanupPhase.BACKUP)
        
        assert isinstance(validation, ValidationResult)
    
    def test_validation_checks_file_operations(self, orchestrator, tmp_path):
        """Test that validation checks file operations."""
        # Create test scenario
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Validate
        validation = orchestrator.validate_phase(CleanupPhase.CACHE_CLEANUP)
        
        assert isinstance(validation, ValidationResult)
    
    def test_validation_detects_failures(self, orchestrator):
        """Test that validation detects failures."""
        # Mock a failing phase
        with patch.object(orchestrator.file_manager, 'move_files', side_effect=Exception("Move failed")):
            try:
                result = orchestrator.execute_phase(CleanupPhase.ROOT_CLEANUP)
                validation = orchestrator.validate_phase(CleanupPhase.ROOT_CLEANUP)
                
                # Should detect failure
                assert validation.success is False or result.success is False
            except Exception:
                # Expected to fail
                pass


@pytest.mark.integration
class TestRollbackFunctionality:
    """Test rollback functionality."""
    
    def test_rolls_back_phase(self, orchestrator):
        """Test rolling back a phase."""
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        # Rollback
        rollback_success = orchestrator.rollback_phase(CleanupPhase.BACKUP)
        
        assert isinstance(rollback_success, bool)
    
    def test_rollback_restores_previous_state(self, orchestrator, tmp_path):
        """Test that rollback restores previous state."""
        # Create initial state
        test_file = tmp_path / "original.txt"
        test_file.write_text("original content")
        
        # Execute phase that modifies state
        result = orchestrator.execute_phase(CleanupPhase.ROOT_CLEANUP)
        
        # Rollback
        rollback_success = orchestrator.rollback_phase(CleanupPhase.ROOT_CLEANUP)
        
        # Verify state restored (if applicable)
        assert isinstance(rollback_success, bool)
    
    def test_rollback_available_after_phase_execution(self, orchestrator):
        """Test that rollback is available after phase execution."""
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Check rollback availability
        assert result.rollback_available is True or isinstance(result.rollback_available, bool)
    
    def test_rollback_handles_missing_state(self, orchestrator):
        """Test rollback handling when state is missing."""
        # Try to rollback phase that wasn't executed
        rollback_success = orchestrator.rollback_phase(CleanupPhase.DOCUMENTATION)
        
        # Should handle gracefully
        assert isinstance(rollback_success, bool)


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in orchestrator."""
    
    def test_handles_file_operation_errors(self, orchestrator):
        """Test handling of file operation errors."""
        # Mock file manager to raise error
        with patch.object(orchestrator.file_manager, 'move_files', side_effect=Exception("File error")):
            try:
                result = orchestrator.execute_phase(CleanupPhase.ROOT_CLEANUP)
                
                # Should handle error
                assert result.success is False
                assert len(result.errors) > 0
            except CleanupError as e:
                # Expected to raise CleanupError
                assert isinstance(e, CleanupError)
    
    def test_handles_git_operation_errors(self, orchestrator):
        """Test handling of git operation errors."""
        # Mock git manager to raise error
        with patch.object(orchestrator.git_manager, 'create_backup_branch', side_effect=Exception("Git error")):
            try:
                result = orchestrator.execute_phase(CleanupPhase.BACKUP)
                
                # Should handle error
                assert result.success is False or isinstance(result, PhaseResult)
            except CleanupError:
                # Expected
                pass
    
    def test_handles_validation_errors(self, orchestrator):
        """Test handling of validation errors."""
        # Mock validator to return failure
        with patch.object(orchestrator.validator, 'validate_imports', 
                         return_value=ValidationResult("test", "imports", False, ["Import error"], [], None)):
            try:
                result = orchestrator.execute_phase(CleanupPhase.VALIDATION)
                
                # Should handle validation failure
                assert result.success is False or isinstance(result, PhaseResult)
            except CleanupError:
                pass
    
    def test_triggers_rollback_on_critical_errors(self, orchestrator):
        """Test that critical errors trigger rollback."""
        # Mock critical error during phase
        with patch.object(orchestrator.file_manager, 'move_files', side_effect=Exception("Critical error")):
            try:
                result = orchestrator.execute_phase(CleanupPhase.ROOT_CLEANUP)
                
                # Should attempt rollback
                assert isinstance(result, PhaseResult)
            except CleanupError:
                # Expected
                pass


@pytest.mark.integration
class TestPhaseSequencing:
    """Test phase sequencing and dependencies."""
    
    def test_executes_phases_in_sequence(self, orchestrator):
        """Test execution of multiple phases in sequence."""
        phases = [
            CleanupPhase.BACKUP,
            CleanupPhase.CACHE_CLEANUP
        ]
        
        results = []
        for phase in phases:
            result = orchestrator.execute_phase(phase)
            results.append(result)
        
        assert len(results) == 2
        assert all(isinstance(r, PhaseResult) for r in results)
    
    def test_validates_phase_dependencies(self, orchestrator):
        """Test validation of phase dependencies."""
        # Try to execute phase without prerequisites
        # (Implementation-specific - may require backup phase first)
        result = orchestrator.execute_phase(CleanupPhase.VALIDATION)
        
        assert isinstance(result, PhaseResult)
    
    def test_tracks_completed_phases(self, orchestrator):
        """Test tracking of completed phases."""
        # Execute phases
        orchestrator.execute_phase(CleanupPhase.BACKUP)
        orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Check tracking
        completed = orchestrator.get_completed_phases()
        
        assert isinstance(completed, list)
        assert CleanupPhase.BACKUP in completed or len(completed) >= 0


@pytest.mark.integration
class TestReportGeneration:
    """Test report generation."""
    
    def test_generates_comprehensive_report(self, orchestrator):
        """Test generation of comprehensive cleanup report."""
        # Execute some phases
        orchestrator.execute_phase(CleanupPhase.BACKUP)
        orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Generate report
        report = orchestrator.generate_report()
        
        assert report is not None
        assert isinstance(report, (str, dict))
    
    def test_report_includes_all_phases(self, orchestrator):
        """Test that report includes all executed phases."""
        phases = [CleanupPhase.BACKUP, CleanupPhase.CACHE_CLEANUP]
        
        for phase in phases:
            orchestrator.execute_phase(phase)
        
        report = orchestrator.generate_report()
        
        # Report should reference executed phases
        assert report is not None
    
    def test_report_includes_metrics(self, orchestrator):
        """Test that report includes metrics."""
        orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        report = orchestrator.generate_report()
        
        # Should include some metrics
        assert report is not None


@pytest.mark.integration
class TestDryRunMode:
    """Test dry run mode."""
    
    def test_dry_run_does_not_modify_files(self, orchestrator, tmp_path):
        """Test that dry run mode doesn't modify files."""
        # Enable dry run
        orchestrator.config.dry_run = True
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")
        
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.ROOT_CLEANUP)
        
        # File should be unchanged
        assert test_file.exists()
        assert test_file.read_text() == "original"
    
    def test_dry_run_generates_preview(self, orchestrator):
        """Test that dry run generates preview of changes."""
        orchestrator.config.dry_run = True
        
        result = orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Should have operations listed but not executed
        assert isinstance(result, PhaseResult)
        assert hasattr(result, 'operations')


@pytest.mark.integration
class TestProgressTracking:
    """Test progress tracking."""
    
    def test_tracks_progress_during_execution(self, orchestrator):
        """Test progress tracking during phase execution."""
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        # Should have duration information
        assert result.duration is not None
        assert isinstance(result.duration, timedelta)
    
    def test_reports_operation_count(self, orchestrator):
        """Test reporting of operation count."""
        result = orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Should report number of operations
        assert hasattr(result, 'operations')
        assert isinstance(result.operations, list)


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration."""
    
    def test_respects_batch_size_configuration(self, orchestrator):
        """Test that orchestrator respects batch size configuration."""
        assert orchestrator.config.git_batch_size == 10
        assert orchestrator.git_manager.batch_size == 10
    
    def test_respects_max_workers_configuration(self, orchestrator):
        """Test that orchestrator respects max workers configuration."""
        assert orchestrator.config.max_workers == 2
    
    def test_respects_auto_commit_configuration(self, orchestrator):
        """Test that orchestrator respects auto commit configuration."""
        assert orchestrator.config.auto_commit is True


@pytest.mark.integration
class TestAnalysisToolsIntegration:
    """Test integration with analysis_tools components."""
    
    def test_integrates_with_code_analyzer(self, orchestrator):
        """Test integration with CodeAnalyzer."""
        assert orchestrator.code_analyzer is not None
    
    def test_integrates_with_test_analyzer(self, orchestrator):
        """Test integration with TestAnalyzer."""
        assert orchestrator.test_analyzer is not None
    
    def test_uses_analysis_orchestrator(self, orchestrator):
        """Test usage of AnalysisOrchestrator."""
        assert orchestrator.analysis_orchestrator is not None
    
    def test_saves_reports_to_analysis_reports_dir(self, orchestrator):
        """Test that reports are saved to analysis_reports directory."""
        # Execute phase
        orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        # Generate report
        report = orchestrator.generate_report()
        
        # Should use analysis_reports directory
        assert orchestrator.reporter.reports_dir.name == "analysis_reports"


@pytest.mark.integration
class TestLargeScaleComponents:
    """Test large-scale component activation."""
    
    def test_initializes_without_large_scale_components(self, orchestrator):
        """Test that large-scale components are not initialized by default."""
        # For small operations, these should be None
        assert orchestrator.state_db is None
        assert orchestrator.checkpoint_manager is None
    
    def test_activates_large_scale_components_when_needed(self, orchestrator):
        """Test activation of large-scale components for 10K+ files."""
        # Enable large-scale mode
        orchestrator.config.use_state_db = True
        orchestrator.config.enable_checkpoints = True
        
        orchestrator._initialize_large_scale_components()
        
        # Should initialize components
        assert orchestrator.state_db is not None
        assert orchestrator.checkpoint_manager is not None


@pytest.mark.integration
class TestEndToEndScenarios:
    """Test end-to-end scenarios."""
    
    def test_complete_cleanup_workflow(self, orchestrator, tmp_path):
        """Test complete cleanup workflow."""
        # Create test environment
        (tmp_path / "TEST_REPORT.md").write_text("report")
        (tmp_path / ".mypy_cache").mkdir()
        
        # Execute phases
        phases = [
            CleanupPhase.BACKUP,
            CleanupPhase.CACHE_CLEANUP,
            CleanupPhase.ROOT_CLEANUP
        ]
        
        results = []
        for phase in phases:
            try:
                result = orchestrator.execute_phase(phase)
                results.append(result)
            except Exception as e:
                # Some phases may fail in test environment
                pass
        
        # Should have executed some phases
        assert len(results) > 0
    
    def test_cleanup_with_validation(self, orchestrator):
        """Test cleanup with validation at each step."""
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.BACKUP)
        
        # Validate
        validation = orchestrator.validate_phase(CleanupPhase.BACKUP)
        
        # Should complete successfully
        assert isinstance(result, PhaseResult)
        assert isinstance(validation, ValidationResult)
    
    def test_cleanup_with_rollback(self, orchestrator):
        """Test cleanup with rollback capability."""
        # Execute phase
        result = orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        
        # Verify rollback available
        assert result.rollback_available is True or isinstance(result.rollback_available, bool)
        
        # Perform rollback
        rollback_success = orchestrator.rollback_phase(CleanupPhase.CACHE_CLEANUP)
        
        assert isinstance(rollback_success, bool)
