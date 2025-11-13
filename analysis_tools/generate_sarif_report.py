"""
Generate combined SARIF report from multiple reviewdog analysis results.

This script combines results from multiple analysis_tools analyzers into a single
SARIF report for GitHub Code Scanning integration.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def load_rdjson_files(input_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all reviewdog rdjson files from input directory.
    
    Args:
        input_dir: Directory containing reviewdog_*.json files
        
    Returns:
        List of parsed JSON objects
    """
    rdjson_files = list(input_dir.glob("reviewdog_*.json"))
    results = []
    
    for file_path in rdjson_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}", file=sys.stderr)
    
    return results


def convert_rdjson_to_sarif(rdjson_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert reviewdog rdjson format to SARIF 2.1.0 format.
    
    Args:
        rdjson_data: List of rdjson objects from analysis_tools
        
    Returns:
        SARIF report dictionary
    """
    all_results = []
    
    for rdjson in rdjson_data:
        source_name = rdjson.get("source", {}).get("name", "unknown")
        diagnostics = rdjson.get("diagnostics", [])
        
        for diag in diagnostics:
            # Convert severity
            severity = diag.get("severity", "warning")
            sarif_level = {
                "error": "error",
                "warning": "warning",
                "info": "note"
            }.get(severity, "warning")
            
            # Extract location
            location = diag.get("location", {})
            file_path = location.get("path", "unknown")
            range_info = location.get("range", {}).get("start", {})
            line = range_info.get("line", 1)
            column = range_info.get("column", 1)
            
            # Build SARIF result
            result = {
                "ruleId": diag.get("code", {}).get("value", source_name) if diag.get("code") else source_name,
                "level": sarif_level,
                "message": {"text": diag.get("message", "No message")},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": file_path,
                            "uriBaseId": "%SRCROOT%"
                        },
                        "region": {
                            "startLine": line,
                            "startColumn": column
                        }
                    }
                }]
            }
            
            # Add suggestions as fixes if available
            suggestions = diag.get("suggestions", [])
            if suggestions:
                result["fixes"] = [{
                    "description": {"text": suggestions[0].get("text", "")},
                    "artifactChanges": [{
                        "artifactLocation": {
                            "uri": file_path
                        },
                        "replacements": [{
                            "deletedRegion": suggestions[0].get("range", {}),
                            "insertedContent": {
                                "text": suggestions[0].get("text", "")
                            }
                        }]
                    }]
                }]
            
            all_results.append(result)
    
    # Build SARIF report
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "analysis_tools",
                    "informationUri": "https://github.com/yourusername/FollowWeb",
                    "version": "1.0.0",
                    "rules": []
                }
            },
            "results": all_results,
            "invocations": [{
                "executionSuccessful": True,
                "endTimeUtc": datetime.utcnow().isoformat() + "Z"
            }]
        }]
    }
    
    return sarif


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate combined SARIF report from reviewdog analysis results"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("analysis_reports"),
        help="Directory containing reviewdog_*.json files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis_reports/reviewdog_combined.sarif"),
        help="Output SARIF file path"
    )
    
    args = parser.parse_args()
    
    # Ensure input directory exists
    if not args.input_dir.exists():
        print(f"Error: Input directory {args.input_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Load rdjson files
    print(f"Loading reviewdog results from {args.input_dir}...")
    rdjson_data = load_rdjson_files(args.input_dir)
    
    if not rdjson_data:
        print("Warning: No reviewdog results found", file=sys.stderr)
        # Create empty SARIF report
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "analysis_tools",
                        "informationUri": "https://github.com/yourusername/FollowWeb",
                        "version": "1.0.0"
                    }
                },
                "results": []
            }]
        }
    else:
        print(f"Found {len(rdjson_data)} reviewdog result files")
        # Convert to SARIF
        sarif = convert_rdjson_to_sarif(rdjson_data)
        print(f"Generated SARIF report with {len(sarif['runs'][0]['results'])} issues")
    
    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Write SARIF report
    with open(args.output, 'w') as f:
        json.dump(sarif, f, indent=2)
    
    print(f"SARIF report saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
