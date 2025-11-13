#!/usr/bin/env python3
import json
from pathlib import Path

reports_dir = Path("analysis_reports")
reports = sorted(reports_dir.glob("code_quality_analysis_*.json"), 
                key=lambda p: p.stat().st_mtime)
latest = reports[-1]

with open(latest) as f:
    data = json.load(f)

print(f"Duplication issues: {len(data['duplication_issues'])} files")
if data['duplication_issues']:
    print("\nFiles with duplicates:")
    for issue in data['duplication_issues'][:10]:
        print(f"  {issue['file']}: {issue['duplicate_count']} duplicates")
