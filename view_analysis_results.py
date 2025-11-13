#!/usr/bin/env python3
"""View code quality analysis results."""

import json
from pathlib import Path

# Find the latest report
reports_dir = Path("analysis_reports")
reports = list(reports_dir.glob("code_quality_analysis_*.json"))
if not reports:
    print("No analysis reports found")
    exit(1)

latest_report = max(reports, key=lambda p: p.stat().st_mtime)
print(f"Reading: {latest_report.name}\n")

with open(latest_report) as f:
    data = json.load(f)

print("=" * 80)
print("CODE QUALITY ANALYSIS SUMMARY")
print("=" * 80)
print(f"Files analyzed: {data['files_analyzed']}")
print(f"AI language issues: {data['summary']['ai_language_issues']} files")
print(f"Duplication issues: {data['summary']['duplication_issues']} files")
print(f"Cross-platform issues: {data['summary']['cross_platform_issues']} files")
print(f"Code quality issues: {data['summary']['code_quality_issues']} files")

print("\n" + "=" * 80)
print("TOP 10 FILES WITH AI LANGUAGE ISSUES")
print("=" * 80)
for i, issue in enumerate(data['ai_language_issues'][:10], 1):
    print(f"\n{i}. {issue['file']}")
    print(f"   Total matches: {issue['total_matches']}")
    print(f"   Categories: {', '.join(f'{k}: {v}' for k, v in issue['matches_by_category'].items())}")
    
    # Show first 3 matches
    for match in issue['matches'][:3]:
        print(f"   - Line {match['line']}: {match['matched_text'][:50]}...")
        if match['suggestion']:
            print(f"     Suggestion: {match['suggestion'][:50]}...")

print("\n" + "=" * 80)
print("REMEDIATION PRIORITIES")
print("=" * 80)

# Count total issues by category
category_counts = {}
for issue in data['ai_language_issues']:
    for category, count in issue['matches_by_category'].items():
        category_counts[category] = category_counts.get(category, 0) + count

print("\nIssues by category:")
for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {category}: {count} occurrences")

# Files with most issues
print("\nFiles with most issues:")
sorted_issues = sorted(data['ai_language_issues'], key=lambda x: x['total_matches'], reverse=True)
for issue in sorted_issues[:10]:
    print(f"  {issue['file']}: {issue['total_matches']} issues")
