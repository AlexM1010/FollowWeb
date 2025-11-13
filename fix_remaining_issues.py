#!/usr/bin/env python3
"""
Fix remaining AI language issues with more targeted replacements.
"""

import json
from pathlib import Path


def load_latest_analysis():
    """Load the latest analysis report."""
    reports_dir = Path("analysis_reports")
    reports = list(reports_dir.glob("code_quality_analysis_*.json"))
    if not reports:
        return None
    
    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
    with open(latest_report) as f:
        return json.load(f)


def fix_specific_patterns(file_path: Path) -> int:
    """Fix specific patterns in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes = 0
        
        # Skip pattern definition files
        if 'ai_language_scanner.py' in str(file_path) or 'pattern_detector.py' in str(file_path):
            return 0
        
        # Fix "intelligent" -> "automated" (but not in comments defining patterns)
        if 'intelligent' in content and not ('"""' in content and 'intelligent' in content):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'intelligent' in line.lower() and not line.strip().startswith('#'):
                    # Skip if it's in a string literal defining patterns
                    if '"intelligent"' not in line and "'intelligent'" not in line:
                        lines[i] = line.replace('intelligent', 'automated').replace('Intelligent', 'Automated')
                        fixes += 1
            content = '\n'.join(lines)
        
        # Fix remaining overused adjectives in docstrings and comments
        replacements = {
            'powerful': 'capable',
            'Powerful': 'Capable',
            'sophisticated': 'complex',
            'Sophisticated': 'Complex',
            'cutting-edge': 'modern',
            'state-of-the-art': 'current',
            'best-in-class': 'high-quality',
            'industry-leading': 'standard',
        }
        
        for old, new in replacements.items():
            if old in content:
                # Only replace in docstrings and comments, not in code
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if (stripped.startswith('#') or 
                        stripped.startswith('"""') or 
                        stripped.startswith("'''") or
                        '"""' in line or
                        "'''" in line):
                        if old in line:
                            lines[i] = line.replace(old, new)
                            fixes += 1
                content = '\n'.join(lines)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fixes
        
        return 0
    
    except Exception as e:
        return 0


def main():
    """Main function."""
    print("=" * 80)
    print("TARGETED AI LANGUAGE ISSUE REMEDIATION")
    print("=" * 80)
    
    data = load_latest_analysis()
    if not data:
        print("No analysis data found")
        return
    
    ai_issues = data.get('ai_language_issues', [])
    
    # Focus on files with specific patterns we want to fix
    target_files = [
        issue['file'] for issue in ai_issues
        if 'ai_language_scanner.py' not in issue['file']
        and 'pattern_detector.py' not in issue['file']
    ]
    
    print(f"\nProcessing {len(target_files)} files...")
    
    total_fixes = 0
    fixed_files = 0
    
    for file_path_str in target_files:
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue
        
        fixes = fix_specific_patterns(file_path)
        if fixes > 0:
            total_fixes += fixes
            fixed_files += 1
            print(f"  Fixed {file_path}: {fixes} issues")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {len(target_files)}")
    print(f"Files modified: {fixed_files}")
    print(f"Total fixes applied: {total_fixes}")


if __name__ == "__main__":
    main()
