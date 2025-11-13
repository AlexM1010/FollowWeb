"""
Reporting System for cleanup operations.

This module provides complete reporting capabilities for cleanup operations,
generating phase reports, migration guides, metrics reports, and developer documentation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .models import (
    CleanupPhase,
    DirectoryStructure,
    FileMapping,
    Metrics,
    PhaseResult,
)


class ReportingSystem:
    """
    Reporting system for cleanup operations.
    
    Generates reports in JSON format consistent with analysis_tools standards,
    saving to the analysis_reports/ directory.
    """

    def __init__(self, reports_dir: Path):
        """
        Initialize reporting system.
        
        Args:
            reports_dir: Path to analysis_reports directory
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_phase_report(
        self, phase: CleanupPhase, result: PhaseResult
    ) -> str:
        """
        Generate report for single phase.
        
        Args:
            phase: Cleanup phase
            result: Phase execution result
            
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = (
            self.reports_dir / f"cleanup_phase_{phase.value}_{timestamp}.json"
        )
        
        report_data = {
            "report_type": "cleanup_phase",
            "phase": phase.value,
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "duration_seconds": result.duration.total_seconds() if result.duration else 0,
            "operations": [
                {
                    "operation": op.operation,
                    "source": op.source,
                    "destination": op.destination,
                    "timestamp": op.timestamp.isoformat(),
                    "success": op.success,
                }
                for op in result.operations
            ],
            "validation": {
                "phase": result.validation_result.phase if result.validation_result else None,
                "success": result.validation_result.success if result.validation_result else None,
                "errors": result.validation_result.errors if result.validation_result else [],
                "warnings": result.validation_result.warnings if result.validation_result else [],
            } if result.validation_result else None,
            "errors": result.errors,
            "warnings": result.warnings,
            "rollback_available": result.rollback_available,
        }
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        
        return str(report_file)

    def generate_migration_guide(
        self, file_mappings: List[FileMapping]
    ) -> str:
        """
        Generate migration guide with old->new path mappings.
        
        Args:
            file_mappings: List of file mappings
            
        Returns:
            Path to generated migration guide file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        guide_file = self.reports_dir / f"cleanup_migration_{timestamp}.json"
        
        # Group mappings by operation type
        moves = []
        copies = []
        removes = []
        
        for mapping in file_mappings:
            entry = {
                "source": mapping.source,
                "destination": mapping.destination,
            }
            
            if mapping.operation_type == "move":
                moves.append(entry)
            elif mapping.operation_type == "copy":
                copies.append(entry)
            elif mapping.operation_type == "remove":
                removes.append({"source": mapping.source})
        
        guide_data = {
            "report_type": "migration_guide",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_operations": len(file_mappings),
                "moves": len(moves),
                "copies": len(copies),
                "removes": len(removes),
            },
            "file_moves": moves,
            "file_copies": copies,
            "file_removes": removes,
            "import_path_updates": self._generate_import_updates(moves),
        }
        
        with open(guide_file, "w", encoding="utf-8") as f:
            json.dump(guide_data, f, indent=2)
        
        return str(guide_file)

    def _generate_import_updates(
        self, moves: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Generate import path update suggestions.
        
        Args:
            moves: List of file move operations
            
        Returns:
            List of import path updates
        """
        updates = []
        
        for move in moves:
            source = move["source"]
            destination = move["destination"]
            
            # Only process Python files
            if not source.endswith(".py"):
                continue
            
            # Convert file paths to module paths
            old_module = source.replace("/", ".").replace("\\", ".").replace(".py", "")
            new_module = destination.replace("/", ".").replace("\\", ".").replace(".py", "")
            
            updates.append({
                "old_import": f"from {old_module} import ...",
                "new_import": f"from {new_module} import ...",
                "file": source,
            })
        
        return updates

    def generate_metrics_report(
        self, before: Metrics, after: Metrics
    ) -> str:
        """
        Generate before/after metrics comparison.
        
        Args:
            before: Metrics before cleanup
            after: Metrics after cleanup
            
        Returns:
            Path to generated metrics report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.reports_dir / f"cleanup_metrics_{timestamp}.json"
        
        # Calculate improvements
        improvements = {
            "root_file_count": {
                "before": before.root_file_count,
                "after": after.root_file_count,
                "reduction": before.root_file_count - after.root_file_count,
                "reduction_percent": (
                    (before.root_file_count - after.root_file_count)
                    / before.root_file_count
                    * 100
                    if before.root_file_count > 0
                    else 0
                ),
            },
            "total_size_mb": {
                "before": before.total_size_mb,
                "after": after.total_size_mb,
                "reduction": before.total_size_mb - after.total_size_mb,
                "reduction_percent": (
                    (before.total_size_mb - after.total_size_mb)
                    / before.total_size_mb
                    * 100
                    if before.total_size_mb > 0
                    else 0
                ),
            },
            "cache_size_mb": {
                "before": before.cache_size_mb,
                "after": after.cache_size_mb,
                "reduction": before.cache_size_mb - after.cache_size_mb,
                "reduction_percent": (
                    (before.cache_size_mb - after.cache_size_mb)
                    / before.cache_size_mb
                    * 100
                    if before.cache_size_mb > 0
                    else 0
                ),
            },
            "documentation_files": {
                "before": before.documentation_files,
                "after": after.documentation_files,
                "change": after.documentation_files - before.documentation_files,
            },
            "utility_scripts": {
                "before": before.utility_scripts,
                "after": after.utility_scripts,
                "change": after.utility_scripts - before.utility_scripts,
            },
            "test_pass_rate": {
                "before": before.test_pass_rate,
                "after": after.test_pass_rate,
                "change": after.test_pass_rate - before.test_pass_rate,
            },
        }
        
        metrics_data = {
            "report_type": "cleanup_metrics",
            "timestamp": datetime.now().isoformat(),
            "before": {
                "root_file_count": before.root_file_count,
                "total_size_mb": before.total_size_mb,
                "cache_size_mb": before.cache_size_mb,
                "documentation_files": before.documentation_files,
                "utility_scripts": before.utility_scripts,
                "test_pass_rate": before.test_pass_rate,
            },
            "after": {
                "root_file_count": after.root_file_count,
                "total_size_mb": after.total_size_mb,
                "cache_size_mb": after.cache_size_mb,
                "documentation_files": after.documentation_files,
                "utility_scripts": after.utility_scripts,
                "test_pass_rate": after.test_pass_rate,
            },
            "improvements": improvements,
        }
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2)
        
        return str(metrics_file)

    def generate_developer_guide(
        self, structure: DirectoryStructure
    ) -> str:
        """
        Generate developer onboarding guide.
        
        Args:
            structure: Repository directory structure
            
        Returns:
            Path to generated developer guide file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        guide_file = self.reports_dir / f"cleanup_developer_guide_{timestamp}.json"
        
        guide_data = {
            "report_type": "developer_guide",
            "timestamp": datetime.now().isoformat(),
            "repository_structure": {
                "directories": structure.directories,
                "purposes": structure.purposes,
                "file_counts": structure.file_counts,
            },
            "navigation_guide": self._generate_navigation_guide(structure),
            "common_tasks": self._generate_common_tasks(structure),
        }
        
        with open(guide_file, "w", encoding="utf-8") as f:
            json.dump(guide_data, f, indent=2)
        
        return str(guide_file)

    def _generate_navigation_guide(
        self, structure: DirectoryStructure
    ) -> Dict[str, str]:
        """
        Generate navigation guide for common file types.
        
        Args:
            structure: Repository directory structure
            
        Returns:
            Dictionary mapping file types to locations
        """
        guide = {}
        
        for directory, purpose in structure.purposes.items():
            if "documentation" in purpose.lower():
                guide["Documentation"] = directory
            elif "script" in purpose.lower():
                guide["Utility Scripts"] = directory
            elif "test" in purpose.lower():
                guide["Tests"] = directory
            elif "analysis" in purpose.lower():
                guide["Analysis Tools"] = directory
        
        return guide

    def _generate_common_tasks(
        self, structure: DirectoryStructure
    ) -> Dict[str, str]:
        """
        Generate common task instructions.
        
        Args:
            structure: Repository directory structure
            
        Returns:
            Dictionary mapping tasks to instructions
        """
        tasks = {
            "Add Documentation": "Place new documentation in docs/ subdirectories based on type (reports/, guides/, analysis/)",
            "Add Utility Script": "Place new scripts in scripts/ subdirectories based on function (freesound/, backup/, validation/, etc.)",
            "Run Tests": "Execute 'pytest' from repository root",
            "Run Analysis": "Execute 'python -m analysis_tools' from repository root",
            "Update Workflows": "Edit files in .github/workflows/ and validate YAML syntax",
        }
        
        return tasks

    def create_directory_readme(
        self, directory: str, purpose: str, files: List[str]
    ) -> str:
        """
        Create README.md for new directory.
        
        Args:
            directory: Directory path
            purpose: Purpose description
            files: List of files in directory
            
        Returns:
            Path to created README file
        """
        readme_path = Path(directory) / "README.md"
        
        # Group files by extension
        files_by_ext = {}
        for file in files:
            ext = Path(file).suffix or "no_extension"
            if ext not in files_by_ext:
                files_by_ext[ext] = []
            files_by_ext[ext].append(file)
        
        # Generate README content
        content_lines = [
            f"# {Path(directory).name}",
            "",
            purpose,
            "",
            "## Contents",
            "",
        ]
        
        for ext, ext_files in sorted(files_by_ext.items()):
            content_lines.append(f"### {ext} files ({len(ext_files)})")
            content_lines.append("")
            for file in sorted(ext_files):
                content_lines.append(f"- `{Path(file).name}`")
            content_lines.append("")
        
        content_lines.extend([
            "## Usage",
            "",
            f"This directory contains {len(files)} files organized for {purpose.lower()}.",
            "",
        ])
        
        # Write README
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))
        
        return str(readme_path)
