#!/usr/bin/env python3
import json
from pathlib import Path

reports_dir = Path("analysis_reports")
reports = sorted(reports_dir.glob("code_quality_analysis_*.json"), 
                key=lambda p: p.stat().st_mtime)
latest = reports[-1]

with open(latest) as f:
    data = json.load(f)

print(f"Cross-platform issues: {len(data['cross_platform_issues'])} files")
if data['cross_platform_issues']:
    print("\nFiles with cross-platform issues:")
    for issue in data['cross_platform_issues'][:10]:
        print(f"  {issue['file']}: {issue['issue_count']} issues (CI score: {issue['ci_score']:.2f})")
        for i in issue['issues'][:3]:
            print(f"    - Line {i['line']}: {i['type']}")
