#!/usr/bin/env python3
"""
Run code quality analysis to detect AI language patterns, duplicates, and cross-platform issues.
"""

import json
from datetime import datetime
from pathlib import Path
from analysis_tools.ai_language_scanner import AILanguageScanner
from analysis_tools.duplication_detector import DuplicationDetector
from analysis_tools.cross_platform_analyzer import CrossPlatformAnalyzer
from analysis_tools.code_analyzer import CodeAnalyzer


def main():
    """Run comprehensive code quality analysis."""
    project_root = Path.cwd()
    reports_dir = project_root / "analysis_reports"
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 80)
    print("CODE QUALITY REMEDIATION ANALYSIS")
    print("=" * 80)
    
    # Initialize analyzers
    ai_scanner = AILanguageScanner()
    duplication_detector = DuplicationDetector()
    cross_platform_analyzer = CrossPlatformAnalyzer()
    code_analyzer = CodeAnalyzer()
    
    # Collect all Python files
    python_files = []
    for pattern in ["FollowWeb/**/*.py", "analysis_tools/**/*.py", "scripts/**/*.py"]:
        python_files.extend(project_root.glob(pattern))
    
    # Filter out test files, cache directories, and virtual environments
    python_files = [
        f for f in python_files
        if "__pycache__" not in str(f)
        and ".pytest_cache" not in str(f)
        and ".mypy_cache" not in str(f)
        and ".ruff_cache" not in str(f)
        and "test_env" not in str(f)
        and ".venv" not in str(f)
        and "venv" not in str(f)
        and "env" not in str(f)
        and ".tox" not in str(f)
        and "site-packages" not in str(f)
        and "test_" not in f.name
    ]
    
    print(f"\nAnalyzing {len(python_files)} Python files...")
    
    # 1. AI Language Pattern Detection
    print("\n" + "=" * 80)
    print("1. AI LANGUAGE PATTERN DETECTION")
    print("=" * 80)
    
    ai_issues = []
    for py_file in python_files:
        try:
            report = ai_scanner.scan_file(str(py_file))
            if report.total_matches > 0:
                ai_issues.append({
                    "file": str(py_file.relative_to(project_root)),
                    "total_matches": report.total_matches,
                    "matches_by_category": report.matches_by_category,
                    "matches": [
                        {
                            "pattern": m.pattern,
                            "matched_text": m.matched_text,
                            "line": m.line_number,
                            "category": m.category,
                            "severity": m.severity.value,
                            "suggestion": m.suggested_replacement
                        }
                        for m in report.all_matches
                    ]
                })
        except Exception as e:
            print(f"  Error scanning {py_file}: {e}")
    
    print(f"\nFound AI language issues in {len(ai_issues)} files")
    for issue in ai_issues[:5]:  # Show top 5
        print(f"  - {issue['file']}: {issue['total_matches']} matches")
    
    # 2. Code Duplication Detection
    print("\n" + "=" * 80)
    print("2. CODE DUPLICATION DETECTION")
    print("=" * 80)
    
    duplication_issues = []
    for py_file in python_files:
        try:
            report = duplication_detector.analyze_file(str(py_file))
            if report.duplicate_count > 0:
                duplication_issues.append({
                    "file": str(py_file.relative_to(project_root)),
                    "duplicate_count": report.duplicate_count,
                    "duplicates": [
                        {
                            "type": d.duplicate_type,
                            "code": d.code_snippet,
                            "locations": d.locations
                        }
                        for d in report.duplicates
                    ]
                })
        except Exception as e:
            print(f"  Error analyzing {py_file}: {e}")
    
    print(f"\nFound code duplication in {len(duplication_issues)} files")
    for issue in duplication_issues[:5]:  # Show top 5
        print(f"  - {issue['file']}: {issue['duplicate_count']} duplicates")
    
    # 3. Cross-Platform Issues
    print("\n" + "=" * 80)
    print("3. CROSS-PLATFORM COMPATIBILITY ISSUES")
    print("=" * 80)
    
    cross_platform_issues = []
    for py_file in python_files:
        try:
            report = cross_platform_analyzer.analyze_file(str(py_file))
            # Count total issues
            total_issues = (
                len(report.platform_issues) +
                len(report.path_issues) +
                len(report.temp_file_issues) +
                len(report.missing_skip_markers)
            )
            
            if total_issues > 0:
                issues_list = []
                
                # Add platform issues
                for issue in report.platform_issues:
                    issues_list.append({
                        "type": "platform_specific",
                        "line": issue.line_number,
                        "code": issue.code_snippet,
                        "suggestion": issue.suggested_fix
                    })
                
                # Add path issues
                for issue in report.path_issues:
                    issues_list.append({
                        "type": "hardcoded_path",
                        "line": issue.line_number,
                        "code": issue.path_string,
                        "suggestion": issue.suggested_fix
                    })
                
                # Add temp file issues
                for issue in report.temp_file_issues:
                    issues_list.append({
                        "type": "temp_file",
                        "line": issue.line_number,
                        "code": issue.code_snippet,
                        "suggestion": issue.suggested_fix
                    })
                
                # Add missing skip markers
                for func_name, line, reason in report.missing_skip_markers:
                    issues_list.append({
                        "type": "missing_skip_marker",
                        "line": line,
                        "code": func_name,
                        "suggestion": f"Add @pytest.mark.skipif for {reason}"
                    })
                
                cross_platform_issues.append({
                    "file": str(py_file.relative_to(project_root)),
                    "issue_count": total_issues,
                    "ci_score": report.ci_compatibility_score,
                    "issues": issues_list
                })
        except Exception as e:
            pass  # Silently skip files that can't be analyzed
    
    print(f"\nFound cross-platform issues in {len(cross_platform_issues)} files")
    for issue in cross_platform_issues[:5]:  # Show top 5
        print(f"  - {issue['file']}: {issue['issue_count']} issues")
    
    # 4. Import and Code Quality Issues
    print("\n" + "=" * 80)
    print("4. IMPORT AND CODE QUALITY ISSUES")
    print("=" * 80)
    
    code_quality_issues = []
    for py_file in python_files:
        try:
            result = code_analyzer.analyze_file(str(py_file))
            issues = []
            # Check if result has the expected attributes
            if hasattr(result, 'unused_imports') and result.unused_imports:
                issues.append(f"{len(result.unused_imports)} unused imports")
            if hasattr(result, 'missing_imports') and result.missing_imports:
                issues.append(f"{len(result.missing_imports)} missing imports")
            if hasattr(result, 'circular_imports') and result.circular_imports:
                issues.append(f"{len(result.circular_imports)} circular imports")
            
            if issues:
                code_quality_issues.append({
                    "file": str(py_file.relative_to(project_root)),
                    "issues": issues,
                    "unused_imports": getattr(result, 'unused_imports', []),
                    "missing_imports": getattr(result, 'missing_imports', []),
                    "circular_imports": getattr(result, 'circular_imports', [])
                })
        except Exception as e:
            pass  # Silently skip files that can't be analyzed
    
    print(f"\nFound code quality issues in {len(code_quality_issues)} files")
    for issue in code_quality_issues[:5]:  # Show top 5
        print(f"  - {issue['file']}: {', '.join(issue['issues'])}")
    
    # Generate comprehensive report
    report = {
        "analysis_timestamp": datetime.now().isoformat(),
        "project_root": str(project_root),
        "files_analyzed": len(python_files),
        "summary": {
            "ai_language_issues": len(ai_issues),
            "duplication_issues": len(duplication_issues),
            "cross_platform_issues": len(cross_platform_issues),
            "code_quality_issues": len(code_quality_issues),
            "total_issues": len(ai_issues) + len(duplication_issues) + len(cross_platform_issues) + len(code_quality_issues)
        },
        "ai_language_issues": ai_issues,
        "duplication_issues": duplication_issues,
        "cross_platform_issues": cross_platform_issues,
        "code_quality_issues": code_quality_issues
    }
    
    # Save report
    report_file = reports_dir / f"code_quality_analysis_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files analyzed: {len(python_files)}")
    print(f"AI language issues: {len(ai_issues)} files")
    print(f"Duplication issues: {len(duplication_issues)} files")
    print(f"Cross-platform issues: {len(cross_platform_issues)} files")
    print(f"Code quality issues: {len(code_quality_issues)} files")
    print(f"\nReport saved to: {report_file}")
    
    return report


if __name__ == "__main__":
    main()
