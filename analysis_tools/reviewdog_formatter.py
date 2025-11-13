"""
Reviewdog output formatter for analysis_tools.

This module provides utilities to format analysis_tools output in reviewdog-compatible
formats (rdjson, SARIF, GitHub Actions annotations).

Architecture:
- analysis_tools: Performs all code analysis
- reviewdog_formatter: Formats analysis results for reviewdog
- reviewdog: Orchestrates and displays results in GitHub
"""

import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional


class Severity(Enum):
    """Issue severity levels matching reviewdog expectations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReviewdogDiagnostic:
    """
    Reviewdog diagnostic in rdjson format.
    
    See: https://github.com/reviewdog/reviewdog/tree/master/proto/rdf
    """
    message: str
    location: Dict[str, Any]
    severity: str
    code: Optional[Dict[str, str]] = None
    suggestions: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "message": self.message,
            "location": self.location,
            "severity": self.severity
        }
        if self.code:
            result["code"] = self.code
        if self.suggestions:
            result["suggestions"] = self.suggestions
        return result


class ReviewdogFormatter:
    """Format analysis_tools results for reviewdog consumption."""
    
    def __init__(self, source_name: str):
        """
        Initialize formatter.
        
        Args:
            source_name: Name of the analysis tool (e.g., "ai-language", "duplication")
        """
        self.source_name = source_name
        self.diagnostics: List[ReviewdogDiagnostic] = []
    
    def add_issue(
        self,
        file_path: str,
        line: int,
        column: int,
        message: str,
        severity: Severity = Severity.WARNING,
        code: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Add an issue to the diagnostics list.
        
        Args:
            file_path: Path to the file with the issue
            line: Line number (1-indexed)
            column: Column number (1-indexed)
            message: Issue description
            severity: Issue severity level
            code: Optional issue code/identifier
            suggestion: Optional fix suggestion
        """
        location = {
            "path": str(file_path),
            "range": {
                "start": {"line": line, "column": column}
            }
        }
        
        code_dict = None
        if code:
            code_dict = {
                "value": code,
                "url": f"https://github.com/yourusername/FollowWeb/blob/main/docs/code-quality.md#{code}"
            }
        
        suggestions = None
        if suggestion:
            suggestions = [{
                "text": suggestion,
                "range": location["range"]
            }]
        
        diagnostic = ReviewdogDiagnostic(
            message=message,
            location=location,
            severity=severity.value,
            code=code_dict,
            suggestions=suggestions
        )
        self.diagnostics.append(diagnostic)
    
    def output_rdjson(self) -> str:
        """
        Output diagnostics in rdjson format.
        
        Returns:
            JSON string in reviewdog rdjson format
        """
        output = {
            "source": {
                "name": self.source_name,
                "url": "https://github.com/yourusername/FollowWeb"
            },
            "diagnostics": [d.to_dict() for d in self.diagnostics]
        }
        return json.dumps(output, indent=2)
    
    def output_sarif(self) -> str:
        """
        Output diagnostics in SARIF format for GitHub Code Scanning.
        
        Returns:
            JSON string in SARIF 2.1.0 format
        """
        results = []
        for diag in self.diagnostics:
            result = {
                "ruleId": diag.code["value"] if diag.code else self.source_name,
                "level": self._severity_to_sarif_level(diag.severity),
                "message": {"text": diag.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": diag.location["path"]
                        },
                        "region": {
                            "startLine": diag.location["range"]["start"]["line"],
                            "startColumn": diag.location["range"]["start"]["column"]
                        }
                    }
                }]
            }
            if diag.suggestions:
                result["fixes"] = [{
                    "description": {"text": diag.suggestions[0]["text"]}
                }]
            results.append(result)
        
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": self.source_name,
                        "informationUri": "https://github.com/yourusername/FollowWeb",
                        "version": "1.0.0"
                    }
                },
                "results": results
            }]
        }
        return json.dumps(sarif, indent=2)
    
    def output_github_actions(self) -> str:
        """
        Output diagnostics in GitHub Actions annotation format.
        
        Returns:
            String with GitHub Actions workflow commands
        """
        lines = []
        for diag in self.diagnostics:
            level = diag.severity
            file_path = diag.location["path"]
            line = diag.location["range"]["start"]["line"]
            col = diag.location["range"]["start"]["column"]
            message = diag.message
            
            # GitHub Actions annotation format
            # ::error file={name},line={line},col={col}::{message}
            annotation = f"::{level} file={file_path},line={line},col={col}::{message}"
            lines.append(annotation)
        
        return "\n".join(lines)
    
    @staticmethod
    def _severity_to_sarif_level(severity: str) -> str:
        """Convert reviewdog severity to SARIF level."""
        mapping = {
            "error": "error",
            "warning": "warning",
            "info": "note"
        }
        return mapping.get(severity, "warning")
    
    def save_to_analysis_reports(self, output_dir: Path, format_type: str = "rdjson"):
        """
        Save diagnostics to analysis_reports directory.
        
        Args:
            output_dir: Path to analysis_reports directory
            format_type: Output format ("rdjson", "sarif", or "github-actions")
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "rdjson":
            content = self.output_rdjson()
            extension = "json"
        elif format_type == "sarif":
            content = self.output_sarif()
            extension = "sarif"
        elif format_type == "github-actions":
            content = self.output_github_actions()
            extension = "txt"
        else:
            raise ValueError(f"Unknown format type: {format_type}")
        
        output_file = output_dir / f"reviewdog_{self.source_name}_{timestamp}.{extension}"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content)
        
        return output_file


def create_formatter(source_name: str) -> ReviewdogFormatter:
    """
    Create a reviewdog formatter instance.
    
    Args:
        source_name: Name of the analysis tool
        
    Returns:
        ReviewdogFormatter instance
    """
    return ReviewdogFormatter(source_name)


if __name__ == "__main__":
    # Example usage
    formatter = create_formatter("example-analyzer")
    formatter.add_issue(
        file_path="example.py",
        line=10,
        column=5,
        message="Example issue found",
        severity=Severity.WARNING,
        code="EX001",
        suggestion="Fix the issue like this"
    )
    
    print("=== RDJSON Format ===")
    print(formatter.output_rdjson())
    print("\n=== SARIF Format ===")
    print(formatter.output_sarif())
    print("\n=== GitHub Actions Format ===")
    print(formatter.output_github_actions())
