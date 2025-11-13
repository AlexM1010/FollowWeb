"""Validate and update workflow file paths."""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


class WorkflowPathValidator:
    """Validates paths in GitHub Actions workflow files."""
    
    def __init__(self, workflows_dir: str = ".github/workflows"):
        """Initialize validator.
        
        Args:
            workflows_dir: Path to workflows directory
        """
        self.workflows_dir = Path(workflows_dir)
        self.issues = []
        self.validated_files = []
        
    def validate_all_workflows(self) -> Dict:
        """Validate all workflow files.
        
        Returns:
            Validation report dictionary
        """
        workflow_files = list(self.workflows_dir.glob("*.yml"))
        
        for workflow_file in workflow_files:
            if workflow_file.name in ["QUICK_REFERENCE.md", "README.md", 
                                     "SCHEDULE_OVERVIEW.md", "API_KEY_VERIFICATION.md"]:
                continue
            
            self._validate_workflow(workflow_file)
        
        return self._generate_report()
    
    def _validate_workflow(self, workflow_file: Path):
        """Validate a single workflow file.
        
        Args:
            workflow_file: Path to workflow file
        """
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse YAML
            try:
                workflow_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                self.issues.append({
                    "file": workflow_file.name,
                    "type": "yaml_error",
                    "message": f"YAML parsing error: {e}"
                })
                return
            
            # Check working-directory paths
            working_dirs = re.findall(r'working-directory:\s*(\S+)', content)
            for wd in working_dirs:
                if not self._validate_path(wd):
                    self.issues.append({
                        "file": workflow_file.name,
                        "type": "invalid_working_directory",
                        "path": wd,
                        "message": f"Working directory does not exist: {wd}"
                    })
            
            # Check cache-dependency-path
            cache_paths = re.findall(r"cache-dependency-path:\s*['\"]?([^'\"\\n]+)['\"]?", content)
            for cp in cache_paths:
                if not self._validate_path(cp):
                    self.issues.append({
                        "file": workflow_file.name,
                        "type": "invalid_cache_path",
                        "path": cp,
                        "message": f"Cache dependency path does not exist: {cp}"
                    })
            
            # Check file references in scripts
            file_refs = re.findall(r'(?:python|pip install -r)\s+([^\s]+\.(?:py|txt|toml))', content)
            for ref in file_refs:
                # Skip URLs and variables
                if ref.startswith('http') or '$' in ref or ref.startswith('-'):
                    continue
                if not self._validate_path(ref):
                    self.issues.append({
                        "file": workflow_file.name,
                        "type": "invalid_file_reference",
                        "path": ref,
                        "message": f"Referenced file does not exist: {ref}"
                    })
            
            self.validated_files.append(workflow_file.name)
            
        except Exception as e:
            self.issues.append({
                "file": workflow_file.name,
                "type": "validation_error",
                "message": f"Error validating workflow: {e}"
            })
    
    def _validate_path(self, path: str) -> bool:
        """Check if a path exists.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path exists or is a pattern
        """
        # Skip patterns and variables
        if '*' in path or '$' in path or path.startswith('~'):
            return True
        
        # Check if path exists
        full_path = Path(path)
        return full_path.exists()
    
    def _generate_report(self) -> Dict:
        """Generate validation report.
        
        Returns:
            Report dictionary
        """
        return {
            "timestamp": "2025-11-13T22:00:00Z",
            "summary": {
                "total_workflows": len(self.validated_files),
                "issues_found": len(self.issues),
                "status": "pass" if len(self.issues) == 0 else "fail"
            },
            "validated_files": self.validated_files,
            "issues": self.issues
        }


def main():
    """Main execution."""
    print("=" * 80)
    print("WORKFLOW PATH VALIDATION")
    print("=" * 80)
    
    validator = WorkflowPathValidator()
    
    print("\n1. Validating workflow files...")
    report = validator.validate_all_workflows()
    
    print(f"   Validated {report['summary']['total_workflows']} workflows")
    print(f"   Found {report['summary']['issues_found']} issues")
    
    if report['issues']:
        print("\n2. Issues found:")
        for issue in report['issues']:
            print(f"   - {issue['file']}: {issue['message']}")
    else:
        print("\n2. No issues found - all paths are valid!")
    
    # Save report
    report_path = Path("analysis_reports/workflow_path_validation.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n3. Report saved to: {report_path}")
    
    print("\n" + "=" * 80)
    print("WORKFLOW PATH VALIDATION COMPLETE")
    print("=" * 80)
    print(f"\nStatus: {report['summary']['status'].upper()}")
    
    return 0 if report['summary']['status'] == 'pass' else 1


if __name__ == "__main__":
    sys.exit(main())
