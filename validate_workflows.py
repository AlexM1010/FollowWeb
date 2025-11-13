"""Validate workflow YAML files."""
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

def validate_workflows():
    """Validate all workflow YAML files."""
    workflows_dir = Path('.github/workflows')
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    if not workflow_files:
        print("No workflow files found")
        return False
    
    errors = []
    valid_count = 0
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            valid_count += 1
            print(f"✓ {workflow_file.name}")
        except yaml.YAMLError as e:
            errors.append(f"✗ {workflow_file.name}: {e}")
        except Exception as e:
            errors.append(f"✗ {workflow_file.name}: {e}")
    
    print(f"\nValidated {valid_count}/{len(workflow_files)} workflows")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  {error}")
        return False
    
    return True

if __name__ == '__main__':
    success = validate_workflows()
    sys.exit(0 if success else 1)
