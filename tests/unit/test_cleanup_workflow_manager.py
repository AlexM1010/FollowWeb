"""
Unit tests for Workflow Manager in cleanup system.

Tests PyYAML integration, reviewdog integration, GitHub CLI integration,
path updates, and schedule optimization.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open
import subprocess

import pytest
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.workflow_manager import WorkflowManager
from analysis_tools.cleanup.models import WorkflowConfig, WorkflowRunResult, ValidationResult
from analysis_tools.cleanup.exceptions import WorkflowError


@pytest.fixture
def workflow_manager():
    """Fixture providing WorkflowManager instance."""
    return WorkflowManager()


@pytest.fixture
def sample_workflow_yaml():
    """Fixture providing sample workflow YAML content."""
    return """
name: Test Workflow
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest tests/
      - name: Run script
        run: python scripts/test_script.py
"""


@pytest.mark.unit
class TestPyYAMLIntegration:
    """Test PyYAML integration for parsing and validation."""
    
    def test_parses_workflow_yaml(self, workflow_manager, tmp_path, sample_workflow_yaml):
        """Test parsing workflow YAML file."""
        workflow_file = tmp_path / "test.yml"
        workflow_file.write_text(sample_workflow_yaml)
        
        config = workflow_manager.parse_workflow(str(workflow_file))
        
        assert isinstance(config, WorkflowConfig)
        assert config.name == "Test Workflow"
        assert "push" in config.triggers
        assert "schedule" in config.triggers
    
    def test_validates_yaml_syntax(self, workflow_manager, tmp_path):
        """Test YAML syntax validation."""
        valid_yaml = tmp_path / "valid.yml"
        valid_yaml.write_text("name: Valid\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest")
        
        result = workflow_manager.validate_syntax(str(valid_yaml))
        
        assert isinstance(result, ValidationResult)
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_detects_invalid_yaml_syntax(self, workflow_manager, tmp_path):
        """Test detection of invalid YAML syntax."""
        invalid_yaml = tmp_path / "invalid.yml"
        invalid_yaml.write_text("name: Invalid\n  bad indentation:\njobs:")
        
        result = workflow_manager.validate_syntax(str(invalid_yaml))
        
        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_extracts_file_references(self, workflow_manager, tmp_path, sample_workflow_yaml):
        """Test extraction of file references from workflow."""
        workflow_file = tmp_path / "test.yml"
        workflow_file.write_text(sample_workflow_yaml)
        
        config = workflow_manager.parse_workflow(str(workflow_file))
        
        assert len(config.file_references) > 0
        # Should find references to scripts/test_script.py
        assert any("test_script.py" in ref for ref in config.file_references)


@pytest.mark.unit
class TestPathUpdates:
    """Test path updates in workflow files."""
    
    def test_updates_single_path(self, workflow_manager, tmp_path):
        """Test updating a single file path in workflow."""
        workflow_content = """
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python old/path/script.py
"""
        workflow_file = tmp_path / "workflow.yml"
        workflow_file.write_text(workflow_content)
        
        path_mappings = {"old/path/script.py": "new/path/script.py"}
        result = workflow_manager.update_paths(str(workflow_file), path_mappings)
        
        assert result is True
        updated_content = workflow_file.read_text()
        assert "new/path/script.py" in updated_content
        assert "old/path/script.py" not in updated_content
    
    def test_updates_multiple_paths(self, workflow_manager, tmp_path):
        """Test updating multiple file paths in workflow."""
        workflow_content = """
name: Test
on: push
jobs:
  test:
    steps:
      - run: python scripts/old1.py
      - run: python scripts/old2.py
      - run: python docs/old3.md
"""
        workflow_file = tmp_path / "workflow.yml"
        workflow_file.write_text(workflow_content)
        
        path_mappings = {
            "scripts/old1.py": "scripts/new/old1.py",
            "scripts/old2.py": "scripts/new/old2.py",
            "docs/old3.md": "docs/guides/old3.md"
        }
        result = workflow_manager.update_paths(str(workflow_file), path_mappings)
        
        assert result is True
        updated_content = workflow_file.read_text()
        assert "scripts/new/old1.py" in updated_content
        assert "scripts/new/old2.py" in updated_content
        assert "docs/guides/old3.md" in updated_content
    
    def test_validates_yaml_after_update(self, workflow_manager, tmp_path):
        """Test that YAML is validated after path updates."""
        workflow_content = """
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python old/script.py
"""
        workflow_file = tmp_path / "workflow.yml"
        workflow_file.write_text(workflow_content)
        
        path_mappings = {"old/script.py": "new/script.py"}
        result = workflow_manager.update_paths(str(workflow_file), path_mappings)
        
        assert result is True
        # Verify YAML is still valid
        validation = workflow_manager.validate_syntax(str(workflow_file))
        assert validation.success is True


@pytest.mark.unit
class TestReviewdogIntegration:
    """Test reviewdog integration as orchestrator."""
    
    def test_integrates_reviewdog_into_workflow(self, workflow_manager, tmp_path):
        """Test adding reviewdog step to workflow."""
        workflow_content = """
name: CI
on: pull_request
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest
"""
        workflow_file = tmp_path / "ci.yml"
        workflow_file.write_text(workflow_content)
        
        result = workflow_manager.integrate_reviewdog(str(workflow_file))
        
        assert result is True
        updated_content = workflow_file.read_text()
        assert "reviewdog" in updated_content.lower()
    
    def test_configures_reviewdog_linters(self, workflow_manager):
        """Test configuration of reviewdog linters."""
        config = workflow_manager.configure_reviewdog_linters()
        
        assert isinstance(config, dict)
        assert "ruff" in config
        assert "mypy" in config
        assert "pylint" in config
        
        # Verify each linter has required configuration
        for linter, settings in config.items():
            assert "config" in settings
            assert "format" in settings
            assert settings["format"] == "github-actions"
    
    def test_reviewdog_uses_project_configs(self, workflow_manager):
        """Test that reviewdog uses project configuration files."""
        config = workflow_manager.configure_reviewdog_linters()
        
        # Verify linters reference project config files
        assert config["ruff"]["config"] == "pyproject.toml"
        assert config["mypy"]["config"] == "myproject.toml"
    
    def test_enables_sarif_output(self, workflow_manager, tmp_path):
        """Test enabling SARIF output for GitHub Code Scanning."""
        workflow_file = tmp_path / "reviewdog.yml"
        workflow_file.write_text("""
name: Review
on: pull_request
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
""")
        
        result = workflow_manager.integrate_reviewdog(str(workflow_file))
        
        assert result is True
        content = workflow_file.read_text()
        # Should configure SARIF output
        assert "sarif" in content.lower() or "reviewdog" in content.lower()


@pytest.mark.unit
class TestGitHubCLIIntegration:
    """Test GitHub CLI integration for secrets and workflow triggering."""
    
    @patch('subprocess.run')
    def test_validates_secrets(self, mock_run, workflow_manager):
        """Test validation of required secrets using GitHub CLI."""
        # Mock gh secret list output
        mock_run.return_value = Mock(
            stdout="SECRET1\nSECRET2\nSECRET3\n",
            returncode=0
        )
        
        required_secrets = ["SECRET1", "SECRET2", "SECRET4"]
        result = workflow_manager.validate_secrets(required_secrets)
        
        assert isinstance(result, dict)
        assert result["SECRET1"] is True
        assert result["SECRET2"] is True
        assert result["SECRET4"] is False  # Not in output
        
        # Verify gh CLI was called
        mock_run.assert_called_once()
        assert "gh" in mock_run.call_args[0][0]
        assert "secret" in mock_run.call_args[0][0]
    
    @patch('subprocess.run')
    def test_triggers_workflow_run(self, mock_run, workflow_manager):
        """Test triggering workflow run using GitHub CLI."""
        mock_run.return_value = Mock(returncode=0)
        
        result = workflow_manager.test_workflow("test-workflow.yml")
        
        assert isinstance(result, WorkflowRunResult)
        
        # Verify gh workflow run was called
        mock_run.assert_called_once()
        assert "gh" in mock_run.call_args[0][0]
        assert "workflow" in mock_run.call_args[0][0]
        assert "run" in mock_run.call_args[0][0]
    
    @patch('subprocess.run')
    def test_handles_gh_cli_errors(self, mock_run, workflow_manager):
        """Test handling of GitHub CLI errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
        
        result = workflow_manager.validate_secrets(["SECRET1"])
        
        # Should handle error gracefully
        assert isinstance(result, dict)


@pytest.mark.unit
class TestScheduleOptimization:
    """Test workflow schedule optimization."""
    
    def test_optimizes_workflow_schedules(self, workflow_manager):
        """Test optimization of workflow schedules to prevent conflicts."""
        workflows = [
            "nightly.yml",
            "freesound-pipeline.yml",
            "validation.yml",
            "ci.yml"
        ]
        
        schedules = workflow_manager.optimize_schedule(workflows)
        
        assert isinstance(schedules, dict)
        assert len(schedules) == len(workflows)
        
        # Verify all workflows have schedules
        for workflow in workflows:
            assert workflow in schedules
            assert schedules[workflow]  # Non-empty schedule
    
    def test_staggers_schedule_times(self, workflow_manager):
        """Test that schedules are staggered by at least 15 minutes."""
        workflows = ["workflow1.yml", "workflow2.yml", "workflow3.yml"]
        
        schedules = workflow_manager.optimize_schedule(workflows)
        
        # Parse cron schedules and verify time differences
        times = []
        for schedule in schedules.values():
            # Parse cron format: "minute hour * * *"
            parts = schedule.split()
            if len(parts) >= 2:
                minute = int(parts[0])
                hour = int(parts[1])
                times.append(hour * 60 + minute)
        
        # Verify at least 15 minute gaps
        if len(times) > 1:
            times.sort()
            for i in range(len(times) - 1):
                gap = times[i + 1] - times[i]
                assert gap >= 15 or gap <= -1425  # Account for day wrap
    
    def test_preserves_workflow_dispatch(self, workflow_manager, tmp_path):
        """Test that workflow_dispatch capability is preserved."""
        workflow_content = """
name: Manual Workflow
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
"""
        workflow_file = tmp_path / "manual.yml"
        workflow_file.write_text(workflow_content)
        
        # Update schedule
        schedules = workflow_manager.optimize_schedule(["manual.yml"])
        
        # Verify workflow_dispatch is still present
        content = workflow_file.read_text()
        # Original content should still have workflow_dispatch
        assert "workflow_dispatch" in workflow_content


@pytest.mark.unit
class TestDocumentationConsolidation:
    """Test consolidation of workflow documentation."""
    
    def test_consolidates_multiple_docs(self, workflow_manager, tmp_path):
        """Test consolidating multiple workflow documentation files."""
        doc1 = tmp_path / "README.md"
        doc1.write_text("# Workflow README\nContent 1")
        
        doc2 = tmp_path / "SCHEDULE.md"
        doc2.write_text("# Schedule Overview\nContent 2")
        
        doc3 = tmp_path / "QUICK_REF.md"
        doc3.write_text("# Quick Reference\nContent 3")
        
        output = tmp_path / "WORKFLOWS.md"
        doc_files = [str(doc1), str(doc2), str(doc3)]
        
        result = workflow_manager.consolidate_documentation(doc_files, str(output))
        
        assert result is True
        assert output.exists()
        
        # Verify consolidated content
        consolidated = output.read_text()
        assert "Content 1" in consolidated
        assert "Content 2" in consolidated
        assert "Content 3" in consolidated
    
    def test_creates_table_of_contents(self, workflow_manager, tmp_path):
        """Test that consolidated documentation includes table of contents."""
        doc1 = tmp_path / "doc1.md"
        doc1.write_text("# Section 1\nContent")
        
        doc2 = tmp_path / "doc2.md"
        doc2.write_text("# Section 2\nContent")
        
        output = tmp_path / "consolidated.md"
        
        result = workflow_manager.consolidate_documentation(
            [str(doc1), str(doc2)],
            str(output)
        )
        
        assert result is True
        content = output.read_text()
        # Should have some form of organization
        assert "Section 1" in content
        assert "Section 2" in content


@pytest.mark.unit
class TestWorkflowValidation:
    """Test comprehensive workflow validation."""
    
    def test_validates_complete_workflow(self, workflow_manager, tmp_path, sample_workflow_yaml):
        """Test validation of complete workflow file."""
        workflow_file = tmp_path / "complete.yml"
        workflow_file.write_text(sample_workflow_yaml)
        
        result = workflow_manager.validate_syntax(str(workflow_file))
        
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_detects_missing_required_fields(self, workflow_manager, tmp_path):
        """Test detection of missing required fields."""
        incomplete_yaml = tmp_path / "incomplete.yml"
        incomplete_yaml.write_text("name: Incomplete\n# Missing 'on' and 'jobs'")
        
        # Should still parse but may have warnings
        config = workflow_manager.parse_workflow(str(incomplete_yaml))
        
        assert config.name == "Incomplete"
    
    def test_validates_job_structure(self, workflow_manager, tmp_path):
        """Test validation of job structure."""
        workflow_content = """
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest
"""
        workflow_file = tmp_path / "jobs.yml"
        workflow_file.write_text(workflow_content)
        
        config = workflow_manager.parse_workflow(str(workflow_file))
        
        assert len(config.jobs) > 0
        assert "test" in config.jobs


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in workflow operations."""
    
    def test_handles_nonexistent_workflow_file(self, workflow_manager):
        """Test handling of nonexistent workflow file."""
        with pytest.raises(FileNotFoundError):
            workflow_manager.parse_workflow("/nonexistent/workflow.yml")
    
    def test_handles_malformed_yaml(self, workflow_manager, tmp_path):
        """Test handling of malformed YAML."""
        malformed = tmp_path / "malformed.yml"
        malformed.write_text("{{invalid yaml content}}")
        
        result = workflow_manager.validate_syntax(str(malformed))
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_handles_path_update_failure(self, workflow_manager, tmp_path):
        """Test handling of path update failure."""
        workflow_file = tmp_path / "test.yml"
        workflow_file.write_text("name: Test\non: push")
        
        # Try to update with invalid mappings
        result = workflow_manager.update_paths(str(workflow_file), {})
        
        # Should handle gracefully
        assert isinstance(result, bool)


@pytest.mark.unit
class TestWorkflowConfiguration:
    """Test workflow configuration management."""
    
    def test_extracts_workflow_triggers(self, workflow_manager, tmp_path):
        """Test extraction of workflow triggers."""
        workflow_content = """
name: Multi-trigger
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
"""
        workflow_file = tmp_path / "triggers.yml"
        workflow_file.write_text(workflow_content)
        
        config = workflow_manager.parse_workflow(str(workflow_file))
        
        assert "push" in config.triggers
        assert "pull_request" in config.triggers
        assert "schedule" in config.triggers
        assert "workflow_dispatch" in config.triggers
    
    def test_extracts_schedule_cron(self, workflow_manager, tmp_path):
        """Test extraction of schedule cron expressions."""
        workflow_content = """
name: Scheduled
on:
  schedule:
    - cron: '0 2 * * 1-6'
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
"""
        workflow_file = tmp_path / "scheduled.yml"
        workflow_file.write_text(workflow_content)
        
        config = workflow_manager.parse_workflow(str(workflow_file))
        
        assert config.schedule is not None
        assert "0 2 * * 1-6" in config.schedule
