#!/usr/bin/env python3
"""
Automatically fix AI language issues in the codebase.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set


def load_latest_analysis():
    """Load the latest analysis report."""
    reports_dir = Path("analysis_reports")
    reports = list(reports_dir.glob("code_quality_analysis_*.json"))
    if not reports:
        print("No analysis reports found")
        return None
    
    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
    print(f"Loading: {latest_report.name}")
    
    with open(latest_report) as f:
        return json.load(f)


def get_replacement_map() -> Dict[str, str]:
    """Get mapping of AI language patterns to replacements."""
    return {
        # Overused adjectives
        "comprehensive": "complete",
        "Comprehensive": "Complete",
        "robust": "reliable",
        "Robust": "Reliable",
        "enhanced": "improved",
        "Enhanced": "Improved",
        "seamless": "smooth",
        "Seamless": "Smooth",
        "efficient": "fast",
        "Efficient": "Fast",
        "optimized": "tuned",
        "Optimized": "Tuned",
        "flexible": "adaptable",
        "Flexible": "Adaptable",
        "powerful": "capable",
        "Powerful": "Capable",
        "advanced": "complex",
        "Advanced": "Complex",
        "sophisticated": "complex",
        "Sophisticated": "Complex",
        "modular": "component-based",
        "Modular": "Component-based",
        
        # Marketing phrases - remove or replace
        "cutting-edge": "modern",
        "state-of-the-art": "current",
        "best-in-class": "high-quality",
        "industry-leading": "standard",
        "world-class": "high-quality",
        
        # Workflow references - be more specific
        "workflow": "process",
        "Workflow": "Process",
    }


def fix_file(file_path: Path, issues: List[Dict]) -> int:
    """Fix AI language issues in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            original_content = content
        
        replacement_map = get_replacement_map()
        fixes_applied = 0
        
        # Group issues by line to avoid conflicts
        issues_by_line = {}
        for issue in issues:
            line_num = issue['line']
            if line_num not in issues_by_line:
                issues_by_line[line_num] = []
            issues_by_line[line_num].append(issue)
        
        # Process line by line
        lines = content.split('\n')
        for line_num, line_issues in sorted(issues_by_line.items()):
            if line_num <= 0 or line_num > len(lines):
                continue
            
            line_idx = line_num - 1
            original_line = lines[line_idx]
            modified_line = original_line
            
            for issue in line_issues:
                matched_text = issue['matched_text']
                suggestion = issue.get('suggestion', '')
                
                # Skip if this is in the ai_language_scanner.py pattern definitions
                if 'ai_language_scanner.py' in str(file_path) and (
                    '"' in original_line or "'" in original_line
                ):
                    continue
                
                # Apply replacement if we have a suggestion
                if suggestion and matched_text in modified_line:
                    # Extract the actual replacement from suggestion
                    if suggestion in replacement_map.values():
                        modified_line = modified_line.replace(matched_text, suggestion)
                        fixes_applied += 1
                    elif matched_text in replacement_map:
                        replacement = replacement_map[matched_text]
                        modified_line = modified_line.replace(matched_text, replacement)
                        fixes_applied += 1
            
            if modified_line != original_line:
                lines[line_idx] = modified_line
        
        # Write back if changes were made
        if fixes_applied > 0:
            new_content = '\n'.join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return fixes_applied
        
        return 0
    
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return 0


def main():
    """Main function to fix AI language issues."""
    print("=" * 80)
    print("AI LANGUAGE ISSUE REMEDIATION")
    print("=" * 80)
    
    # Load analysis
    data = load_latest_analysis()
    if not data:
        return
    
    ai_issues = data.get('ai_language_issues', [])
    print(f"\nFound {len(ai_issues)} files with AI language issues")
    
    # Skip the ai_language_scanner.py file itself (it contains pattern definitions)
    files_to_fix = [
        issue for issue in ai_issues
        if 'ai_language_scanner.py' not in issue['file']
        and 'pattern_detector.py' not in issue['file']  # Also skip pattern definitions
    ]
    
    print(f"Fixing {len(files_to_fix)} files (excluding pattern definition files)")
    
    total_fixes = 0
    fixed_files = 0
    
    for issue in files_to_fix:
        file_path = Path(issue['file'])
        if not file_path.exists():
            print(f"  Skipping {file_path} (not found)")
            continue
        
        fixes = fix_file(file_path, issue['matches'])
        if fixes > 0:
            total_fixes += fixes
            fixed_files += 1
            print(f"  Fixed {file_path}: {fixes} issues")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {len(files_to_fix)}")
    print(f"Files modified: {fixed_files}")
    print(f"Total fixes applied: {total_fixes}")
    
    if fixed_files > 0:
        print("\nRecommendation: Run the analysis again to verify fixes")


if __name__ == "__main__":
    main()
