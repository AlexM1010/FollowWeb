#!/usr/bin/env python3
"""
Validate that ci_helpers.py path references are correct in all workflow files.

This script checks that all workflow files use the correct relative path to ci_helpers.py
based on their working directory context.
"""

import re
import sys
from pathlib import Path

def main():
    """Validate ci_helpers.py path references in workflow files."""
    workflows_dir = Path(".github/workflows")
    errors = []
    
    # Pattern to match ci_helpers.py references
    pattern = re.compile(r'python\s+([^\s]*ci_helpers\.py)')
    
    for workflow_file in workflows_dir.glob("*.yml"):
        with open(workflow_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Track working directory context for each line
        current_workdir = None
        in_job = False
        
        for line_num, line in enumerate(lines, 1):
            # Reset working directory at job boundaries
            if re.match(r'^\s{2}\w+:', line) and 'name:' not in line:
                # New job definition (2-space indent, ends with colon, not a 'name:' field)
                current_workdir = None
                in_job = True
            
            # Update working directory context within a job
            if 'working-directory:' in line:
                if 'FollowWeb' in line:
                    current_workdir = 'FollowWeb'
                else:
                    current_workdir = None
            
            # Check for ci_helpers.py references
            match = pattern.search(line)
            if match:
                path = match.group(1)
                
                # Expected path depends on current working directory
                if current_workdir == 'FollowWeb':
                    expected_path = '../.github/scripts/ci_helpers.py'
                else:
                    expected_path = '.github/scripts/ci_helpers.py'
                
                if path != expected_path:
                    errors.append(
                        f"{workflow_file.name}:{line_num}: Found '{path}', expected '{expected_path}' "
                        f"(working-directory: {current_workdir or 'root'})"
                    )
    
    if errors:
        print("❌ ci_helpers.py path validation FAILED:")
        print()
        for error in errors:
            print(f"  - {error}")
        print()
        print("Fix: Update workflow files to use correct relative paths")
        return 1
    else:
        print("✅ All ci_helpers.py path references are correct")
        return 0

if __name__ == "__main__":
    sys.exit(main())
