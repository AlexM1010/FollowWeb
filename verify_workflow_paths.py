"""Verify file paths referenced in workflows exist."""
import sys
from pathlib import Path
import re

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

def extract_file_references(data, refs=None):
    """Recursively extract file path references from workflow data."""
    if refs is None:
        refs = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                # Look for file paths (common extensions)
                if any(ext in value for ext in ['.py', '.txt', '.md', '.json', '.yml', '.yaml', '.toml', '.ini']):
                    # Skip URLs and actions
                    if not value.startswith(('http://', 'https://', 'git://', 'actions/')):
                        refs.append(value)
            extract_file_references(value, refs)
    elif isinstance(data, list):
        for item in data:
            extract_file_references(item, refs)
    
    return refs

def verify_workflow_paths():
    """Verify all file paths in workflows exist."""
    workflows_dir = Path('.github/workflows')
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    all_refs = []
    missing_files = []
    checked_files = set()
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            refs = extract_file_references(data)
            all_refs.extend([(workflow_file.name, ref) for ref in refs])
        except Exception as e:
            print(f"Error processing {workflow_file.name}: {e}")
    
    print(f"Found {len(all_refs)} file references in workflows\n")
    
    # Check if files exist
    for workflow_name, ref in all_refs:
        # Clean up the reference
        ref_clean = ref.strip()
        
        # Skip patterns and wildcards
        if '*' in ref_clean or '${{' in ref_clean:
            continue
        
        # Skip if already checked
        if ref_clean in checked_files:
            continue
        
        checked_files.add(ref_clean)
        
        # Check relative to root
        file_path = Path(ref_clean)
        if not file_path.exists():
            # Try relative to FollowWeb directory (common working directory)
            followweb_path = Path('FollowWeb') / ref_clean
            if not followweb_path.exists():
                missing_files.append((workflow_name, ref_clean))
    
    if missing_files:
        print("Missing files:")
        for workflow_name, ref in missing_files:
            print(f"  {workflow_name}: {ref}")
        return False
    else:
        print("✓ All referenced files exist")
        return True

if __name__ == '__main__':
    success = verify_workflow_paths()
    sys.exit(0 if success else 1)
