"""
Workflow Manager for cleanup operations.

Handles GitHub Actions workflow operations including YAML parsing, path updates,
syntax validation, reviewdog integration, and schedule optimization.
"""

import subprocess
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .exceptions import WorkflowError
from .models import CleanupPhase, ValidationResult, WorkflowConfig, WorkflowRunResult


class WorkflowManager:
    """
    Manages GitHub Actions workflow operations.
    
    Provides methods for parsing workflows, updating paths, validating syntax,
    integrating reviewdog, and optimizing schedules. Uses PyYAML for parsing
    and GitHub CLI for workflow operations.
    """

    def __init__(self):
        """
        Initialize Workflow Manager.
        
        Raises:
            WorkflowError: If PyYAML is not available
        """
        if not YAML_AVAILABLE:
            raise WorkflowError(
                phase=CleanupPhase.WORKFLOW_UPDATE,
                message="PyYAML is not installed. Install with: pip install pyyaml",
                recoverable=False,
            )
        
        self.reviewdog_config = self._load_reviewdog_config()
    
    def _load_reviewdog_config(self) -> dict[str, Any]:
        """
        Load reviewdog configuration.
        
        Returns:
            Reviewdog configuration dictionary
        """
        return {
            "version": "1",
            "linters": {
                "ruff": {
                    "config": "pyproject.toml",
                    "format": "github-actions",
                },
                "mypy": {
                    "config": "pyproject.toml",
                    "format": "github-actions",
                },
                "pylint": {
                    "config": ".pylintrc",
                    "format": "github-actions",
                },
            },
        }
    
    def parse_workflow(self, workflow_path: str) -> WorkflowConfig:
        """
        Parse workflow YAML file using PyYAML.
        
        Args:
            workflow_path: Path to workflow YAML file
            
        Returns:
            WorkflowConfig object
            
        Raises:
            WorkflowError: If parsing fails
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Extract workflow information
            name = data.get('name', Path(workflow_path).stem)
            triggers = list(data.get('on', {}).keys())
            schedule = data.get('on', {}).get('schedule')
            jobs = list(data.get('jobs', {}).keys())
            
            # Extract file references from workflow
            file_references = self._extract_file_references(data)
            
            return WorkflowConfig(
                name=name,
                path=workflow_path,
                triggers=triggers,
                schedule=str(schedule) if schedule else None,
                jobs=jobs,
                file_references=file_references,
            )
        except Exception as e:
            raise WorkflowError(
                phase=CleanupPhase.WORKFLOW_UPDATE,
                message=f"Failed to parse workflow: {e}",
                workflow_file=workflow_path,
            )
    
    def _extract_file_references(self, workflow_data: dict) -> list[str]:
        """
        Extract file path references from workflow data.
        
        Args:
            workflow_data: Parsed workflow YAML data
            
        Returns:
            List of file paths referenced in workflow
        """
        references = []
        
        # Recursively search for file paths in workflow
        def search_dict(d: Any):
            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, str):
                        # Look for common file path patterns
                        if any(ext in value for ext in ['.py', '.txt', '.md', '.json']):
                            references.append(value)
                    search_dict(value)
            elif isinstance(d, list):
                for item in d:
                    search_dict(item)
        
        search_dict(workflow_data)
        return references
    
    def update_paths(
        self,
        workflow_path: str,
        path_mappings: dict[str, str],
        dry_run: bool = False,
    ) -> bool:
        """
        Update file paths in workflow using PyYAML.
        
        Args:
            workflow_path: Path to workflow file
            path_mappings: Dictionary mapping old paths to new paths
            dry_run: If True, simulate without making changes
            
        Returns:
            True if paths were updated
            
        Raises:
            WorkflowError: If update fails
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update each path mapping
            updated_content = content
            for old_path, new_path in path_mappings.items():
                updated_content = updated_content.replace(old_path, new_path)
            
            # Validate YAML syntax
            yaml.safe_load(updated_content)
            
            # Write updated content if not dry run
            if updated_content != content and not dry_run:
                with open(workflow_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
            
            return updated_content != content
        except Exception as e:
            raise WorkflowError(
                phase=CleanupPhase.WORKFLOW_UPDATE,
                message=f"Failed to update paths: {e}",
                workflow_file=workflow_path,
            )
    
    def validate_syntax(self, workflow_path: str) -> ValidationResult:
        """
        Validate workflow YAML syntax using PyYAML.
        
        Args:
            workflow_path: Path to workflow file
            
        Returns:
            ValidationResult
        """
        from datetime import datetime
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            
            return ValidationResult(
                phase="workflow_validation",
                validation_type="yaml_syntax",
                success=True,
                errors=[],
                warnings=[],
                timestamp=datetime.now(),
            )
        except yaml.YAMLError as e:
            return ValidationResult(
                phase="workflow_validation",
                validation_type="yaml_syntax",
                success=False,
                errors=[str(e)],
                warnings=[],
                timestamp=datetime.now(),
            )
    
    def integrate_reviewdog(
        self, workflow_path: str, dry_run: bool = False
    ) -> bool:
        """
        Integrate reviewdog into CI workflow.
        
        Args:
            workflow_path: Path to workflow file
            dry_run: If True, simulate without making changes
            
        Returns:
            True if reviewdog was integrated
        """
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Add reviewdog step to workflow
            # This is a simplified implementation - actual integration
            # would need to be customized per workflow
            reviewdog_step = {
                'name': 'Run reviewdog',
                'uses': 'reviewdog/action-setup@v1',
                'with': {
                    'reviewdog_version': 'latest',
                },
            }
            
            # Add to first job (simplified)
            if 'jobs' in data and data['jobs']:
                first_job = list(data['jobs'].keys())[0]
                if 'steps' not in data['jobs'][first_job]:
                    data['jobs'][first_job]['steps'] = []
                
                # Check if reviewdog already exists
                has_reviewdog = any(
                    'reviewdog' in str(step).lower()
                    for step in data['jobs'][first_job]['steps']
                )
                
                if not has_reviewdog and not dry_run:
                    data['jobs'][first_job]['steps'].append(reviewdog_step)
                    
                    with open(workflow_path, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, default_flow_style=False)
                    
                    return True
            
            return False
        except Exception as e:
            raise WorkflowError(
                phase=CleanupPhase.CODE_REVIEW_INTEGRATION,
                message=f"Failed to integrate reviewdog: {e}",
                workflow_file=workflow_path,
            )
    
    def configure_reviewdog_linters(self) -> dict[str, Any]:
        """
        Configure reviewdog linters with project settings.
        
        Returns:
            Linter configuration dictionary
        """
        return self.reviewdog_config["linters"]
    
    def consolidate_documentation(
        self,
        doc_files: list[str],
        output: str,
        dry_run: bool = False,
    ) -> bool:
        """
        Consolidate multiple workflow docs into one.
        
        Args:
            doc_files: List of documentation files to consolidate
            output: Output file path
            dry_run: If True, simulate without making changes
            
        Returns:
            True if successful
        """
        try:
            consolidated_content = []
            
            for doc_file in doc_files:
                if Path(doc_file).exists():
                    with open(doc_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        consolidated_content.append(f"# {Path(doc_file).stem}\n\n{content}\n\n")
            
            if not dry_run and consolidated_content:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(consolidated_content))
            
            return len(consolidated_content) > 0
        except Exception as e:
            raise WorkflowError(
                phase=CleanupPhase.WORKFLOW_UPDATE,
                message=f"Failed to consolidate documentation: {e}",
            )
    
    def validate_secrets(self, required_secrets: list[str]) -> dict[str, bool]:
        """
        Validate required secrets using GitHub CLI.
        
        Args:
            required_secrets: List of required secret names
            
        Returns:
            Dictionary mapping secret names to availability
        """
        try:
            result = subprocess.run(
                ["gh", "secret", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                # GitHub CLI not available or not authenticated
                return {secret: False for secret in required_secrets}
            
            secrets_output = result.stdout
            return {
                secret: secret in secrets_output
                for secret in required_secrets
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # GitHub CLI not available
            return {secret: False for secret in required_secrets}
    
    def test_workflow(
        self, workflow_name: str, timeout: int = 300
    ) -> Optional[WorkflowRunResult]:
        """
        Trigger test run of workflow using GitHub CLI.
        
        Args:
            workflow_name: Name of workflow to test
            timeout: Timeout in seconds
            
        Returns:
            WorkflowRunResult or None if failed
        """
        from datetime import datetime, timedelta
        
        try:
            # Trigger workflow
            result = subprocess.run(
                ["gh", "workflow", "run", workflow_name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            if result.returncode != 0:
                return None
            
            # Note: This is simplified - actual implementation would need to
            # wait for workflow to complete and get results
            return WorkflowRunResult(
                workflow_name=workflow_name,
                run_id="unknown",
                status="triggered",
                duration=timedelta(seconds=0),
                logs=result.stdout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    def optimize_schedule(
        self,
        workflows: list[str],
        offset_minutes: int = 15,
    ) -> dict[str, str]:
        """
        Optimize workflow schedules to prevent conflicts.
        
        Args:
            workflows: List of workflow file paths
            offset_minutes: Minimum offset between workflows in minutes
            
        Returns:
            Dictionary mapping workflow paths to tuned schedules
        """
        schedules = {}
        current_hour = 1
        current_minute = 0
        
        for workflow_path in workflows:
            try:
                config = self.parse_workflow(workflow_path)
                
                # Generate staggered schedule
                schedule = f"{current_minute} {current_hour} * * *"
                schedules[workflow_path] = schedule
                
                # Increment time for next workflow
                current_minute += offset_minutes
                if current_minute >= 60:
                    current_minute = 0
                    current_hour += 1
                    if current_hour >= 24:
                        current_hour = 0
            except Exception:
                continue
        
        return schedules
