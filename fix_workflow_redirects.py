#!/usr/bin/env python3
"""
Script to automatically fix SC2129 shellcheck warnings in GitHub Actions workflow files.
SC2129: Consider using { cmd1; cmd2; } >> file instead of individual redirects

This script identifies consecutive echo redirects to the same file and groups them.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_consecutive_redirects(lines: List[str], start_idx: int) -> Tuple[int, int, str]:
    """
    Find consecutive redirect statements to the same target file.
    
    Returns: (start_line, end_line, target_file) or (0, 0, "") if not found
    """
    # Pattern to match: echo "..." >> "$TARGET"
    redirect_pattern = r'^\s*(echo\s+.*?)\s*>>\s*["\']?\$(\w+)["\']?\s*$'
    
    match = re.match(redirect_pattern, lines[start_idx])
    if not match:
        return (0, 0, "")
    
    target_file = match.group(2)
    indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    
    # Find consecutive redirects to the same file with same indentation
    end_idx = start_idx
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        
        # Skip empty lines
        if not line.strip():
            continue
            
        # Check if this line has the same indentation
        line_indent = len(line) - len(line.lstrip())
        if line_indent != indent:
            break
            
        # Check if it's a redirect to the same file
        match = re.match(redirect_pattern, line)
        if match and match.group(2) == target_file:
            end_idx = i
        else:
            break
    
    # Only group if we have at least 2 consecutive redirects
    if end_idx > start_idx:
        return (start_idx, end_idx, target_file)
    
    return (0, 0, "")


def group_redirects(lines: List[str], start_idx: int, end_idx: int, target_file: str) -> List[str]:
    """
    Group consecutive redirect lines into a single brace group.
    """
    indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    indent_str = ' ' * indent
    
    # Extract the echo commands (without the redirect part)
    redirect_pattern = r'^\s*(echo\s+.*?)\s*>>\s*["\']?\$\w+["\']?\s*$'
    echo_commands = []
    
    for i in range(start_idx, end_idx + 1):
        match = re.match(redirect_pattern, lines[i])
        if match:
            echo_cmd = match.group(1).strip()
            echo_commands.append(f"{indent_str}  {echo_cmd}")
    
    # Create grouped version
    grouped = [
        f"{indent_str}{{",
        *echo_commands,
        f"{indent_str}}} >> \"${target_file}\""
    ]
    
    return grouped


def fix_workflow_file(filepath: Path) -> bool:
    """
    Fix SC2129 warnings in a workflow file.
    Returns True if changes were made.
    """
    print(f"Processing {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove trailing newlines but keep track of them
    lines = [line.rstrip('\n') for line in lines]
    
    changes_made = False
    i = 0
    new_lines = []
    
    while i < len(lines):
        # Check for consecutive redirects
        start_idx, end_idx, target_file = find_consecutive_redirects(lines, i)
        
        if start_idx > 0:
            # Found consecutive redirects - group them
            grouped = group_redirects(lines, start_idx, end_idx, target_file)
            new_lines.extend(grouped)
            i = end_idx + 1
            changes_made = True
            print(f"  Grouped {end_idx - start_idx + 1} redirects at line {start_idx + 1}")
        else:
            # No consecutive redirects - keep line as is
            new_lines.append(lines[i])
            i += 1
    
    if changes_made:
        # Write back to file
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(new_lines) + '\n')
        print(f"  ✓ Fixed {filepath.name}")
        return True
    else:
        print(f"  - No changes needed for {filepath.name}")
        return False


def main():
    """Main entry point."""
    workflows_dir = Path('.github/workflows')
    
    if not workflows_dir.exists():
        print(f"Error: {workflows_dir} not found")
        sys.exit(1)
    
    # Get all YAML workflow files
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    if not workflow_files:
        print(f"No workflow files found in {workflows_dir}")
        sys.exit(1)
    
    print(f"Found {len(workflow_files)} workflow files\n")
    
    total_fixed = 0
    for filepath in sorted(workflow_files):
        if fix_workflow_file(filepath):
            total_fixed += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: Fixed {total_fixed} out of {len(workflow_files)} files")
    print(f"{'='*60}")
    
    return 0 if total_fixed > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
