"""
Main analysis orchestrator that coordinates all analysis tools.
"""

# Standard library imports
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Local imports
from .ai_language_scanner import AILanguageScanner
from .code_analyzer import CodeAnalyzer
from .cross_platform_analyzer import CrossPlatformAnalyzer
from .duplication_detector import DuplicationDetector
from .models import AnalysisResult, DuplicateTestAnalysisResult
from .pattern_detector import PatternDetector
from .test_analyzer import DuplicateTestAnalyzer


class AnalysisOrchestrator:
    """Coordinates all analysis tools for comprehensive code quality assessment."""

    def __init__(self, project_root: Optional[str] = None):
        """Initialize the analysis orchestrator."""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.code_analyzer = CodeAnalyzer()
        self.pattern_detector = PatternDetector()
        self.test_analyzer = DuplicateTestAnalyzer()

        # Initialize specialized analyzers
        self.ai_language_scanner = AILanguageScanner()
        self.duplication_detector = DuplicationDetector()
        self.cross_platform_analyzer = CrossPlatformAnalyzer()

        # Create reports directory
        self.reports_dir = self.project_root / "analysis_reports"
        self.reports_dir.mkdir(exist_ok=True)

    def run_full_analysis(self) -> Dict:
        """Run complete analysis of the codebase."""
        print("Starting comprehensive code quality analysis...")

        # Analyze source code
        print("Analyzing source code...")
        source_results = self._analyze_source_code()

        # Analyze test code
        print("Analyzing test suite...")
        test_results = self._analyze_test_code()

        # Generate comprehensive report
        print("Generating analysis report...")
        report = self._generate_comprehensive_report(source_results, test_results)

        # Save report
        report_file = self._save_report(report)
        print(f"Analysis complete. Report saved to: {report_file}")

        return report

    def _analyze_source_code(self) -> List[AnalysisResult]:
        """Analyze all source code files."""
        results = []

        # Find all Python files (excluding tests)
        for py_file in self.project_root.rglob("*.py"):
            # Skip test files, __pycache__, and other excluded directories
            if any(
                exclude in str(py_file)
                for exclude in [
                    "test_",
                    "__pycache__",
                    ".git",
                    ".pytest_cache",
                    "venv",
                    "env",
                    ".tox",
                    "build",
                    "dist",
                ]
            ):
                continue

            try:
                result = self.code_analyzer.analyze_file(str(py_file))
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")

        return results

    def _analyze_test_code(self) -> List[DuplicateTestAnalysisResult]:
        """Analyze all test files."""
        results = []

        # Find test directories
        test_dirs = []
        for test_dir in ["tests", "test"]:
            test_path = self.project_root / test_dir
            if test_path.exists():
                test_dirs.append(test_path)

        # If no standard test directories, look for test files anywhere
        if not test_dirs:
            test_files = list(self.project_root.rglob("test_*.py"))
        else:
            test_files = []
            for test_dir in test_dirs:
                test_files.extend(test_dir.rglob("test_*.py"))

        for test_file in test_files:
            try:
                result = self.test_analyzer.analyze_test_file(str(test_file))
                results.append(result)
            except Exception as e:
                print(f"Error analyzing test file {test_file}: {e}")

        # Find cross-file duplicates
        if results:
            cross_file_duplicates = self.test_analyzer.find_cross_file_duplicates(
                results
            )
            # Add cross-file duplicates to the first result for reporting
            if cross_file_duplicates and results:
                results[0].duplicate_tests.extend(cross_file_duplicates)

        return results

    def _generate_comprehensive_report(
        self,
        source_results: List[AnalysisResult],
        test_results: List[DuplicateTestAnalysisResult],
    ) -> Dict:
        """Generate a comprehensive analysis report."""
        # Collect file operation lists
        file_operations = self._collect_file_operations()

        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "summary": self._generate_summary(source_results, test_results),
            "source_code_analysis": self._summarize_source_analysis(source_results),
            "test_code_analysis": self._summarize_test_analysis(test_results),
            "optimization_recommendations": self._generate_optimization_recommendations(
                source_results, test_results
            ),
            "file_operations": file_operations,
            "detailed_results": {
                "source_files": [
                    self._serialize_analysis_result(r) for r in source_results
                ],
                "test_files": [self._serialize_test_result(r) for r in test_results],
            },
        }

        return report

    def _generate_summary(
        self,
        source_results: List[AnalysisResult],
        test_results: List[DuplicateTestAnalysisResult],
    ) -> Dict:
        """Generate high-level summary statistics."""
        total_files = len(source_results)
        total_test_files = len(test_results)

        total_issues = sum(len(r.issues) for r in source_results)
        ai_language_issues = sum(r.ai_language_count for r in source_results)

        total_tests = sum(r.test_count for r in test_results)
        duplicate_test_groups = sum(len(r.duplicate_tests) for r in test_results)

        return {
            "files_analyzed": total_files,
            "test_files_analyzed": total_test_files,
            "total_issues_found": total_issues,
            "ai_language_issues": ai_language_issues,
            "total_tests": total_tests,
            "duplicate_test_groups": duplicate_test_groups,
            "refactoring_opportunities": sum(
                len(r.refactoring_opportunities) for r in source_results
            ),
        }

    def _summarize_source_analysis(self, results: List[AnalysisResult]) -> Dict:
        """Summarize source code analysis results."""
        issue_counts = {}
        for result in results:
            for issue in result.issues:
                issue_type = issue.issue_type.value
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        return {
            "files_with_issues": len([r for r in results if r.issues]),
            "issue_breakdown": issue_counts,
            "total_lines_of_code": sum(r.metrics.lines_of_code for r in results),
            "average_complexity": (
                sum(r.metrics.complexity_score for r in results) / len(results)
                if results
                else 0
            ),
        }

    def _summarize_test_analysis(
        self, results: List[DuplicateTestAnalysisResult]
    ) -> Dict:
        """Summarize test analysis results."""
        return {
            "files_with_duplicates": len([r for r in results if r.duplicate_tests]),
            "total_unused_fixtures": sum(len(r.unused_fixtures) for r in results),
            "total_redundant_imports": sum(len(r.redundant_imports) for r in results),
            "test_efficiency_score": self._calculate_test_efficiency_score(results),
        }

    def _calculate_test_efficiency_score(
        self, results: List[DuplicateTestAnalysisResult]
    ) -> float:
        """Calculate a test efficiency score (0-100)."""
        if not results:
            return 100.0

        total_tests = sum(r.test_count for r in results)
        total_issues = sum(
            len(r.duplicate_tests) + len(r.unused_fixtures) + len(r.redundant_imports)
            for r in results
        )

        if total_tests == 0:
            return 100.0

        efficiency = max(0, 100 - (total_issues / total_tests * 100))
        return round(efficiency, 2)

    def _generate_optimization_recommendations(
        self,
        source_results: List[AnalysisResult],
        test_results: List[DuplicateTestAnalysisResult],
    ) -> List[Dict]:
        """Generate prioritized optimization recommendations."""
        recommendations = []

        # AI language cleanup
        ai_issues = sum(r.ai_language_count for r in source_results)
        if ai_issues > 0:
            recommendations.append(
                {
                    "priority": "High",
                    "category": "Language Cleanup",
                    "description": f"Remove {ai_issues} AI-generated language artifacts",
                    "impact": "Improves code professionalism and readability",
                    "effort": "Low",
                }
            )

        # Code duplication
        duplication_files = len(
            [
                r
                for r in source_results
                if any(i.issue_type.value == "duplication" for i in r.issues)
            ]
        )
        if duplication_files > 0:
            recommendations.append(
                {
                    "priority": "Medium",
                    "category": "Code Deduplication",
                    "description": f"Address code duplication in {duplication_files} files",
                    "impact": "Reduces maintenance burden and improves consistency",
                    "effort": "Medium",
                }
            )

        # Test optimization
        duplicate_tests = sum(len(r.duplicate_tests) for r in test_results)
        if duplicate_tests > 0:
            recommendations.append(
                {
                    "priority": "Medium",
                    "category": "Test Optimization",
                    "description": f"Consolidate {duplicate_tests} duplicate test groups",
                    "impact": "Improves test suite efficiency and maintainability",
                    "effort": "Low",
                }
            )

        return recommendations

    def _serialize_analysis_result(self, result: AnalysisResult) -> Dict:
        """Convert AnalysisResult to serializable dictionary."""
        return {
            "file_path": result.file_path,
            "issue_count": len(result.issues),
            "ai_language_count": result.ai_language_count,
            "refactoring_opportunities": len(result.refactoring_opportunities),
            "metrics": {
                "lines_of_code": result.metrics.lines_of_code,
                "complexity_score": result.metrics.complexity_score,
                "function_count": result.metrics.function_count,
                "class_count": result.metrics.class_count,
            },
        }

    def _serialize_test_result(self, result: DuplicateTestAnalysisResult) -> Dict:
        """Convert DuplicateTestAnalysisResult to serializable dictionary."""
        return {
            "test_file": result.test_file,
            "test_count": result.test_count,
            "duplicate_groups": len(result.duplicate_tests),
            "unused_fixtures": len(result.unused_fixtures),
            "redundant_imports": len(result.redundant_imports),
        }

    def _save_report(self, report: Dict) -> str:
        """Save analysis report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"analysis_report_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        return str(report_file)

    def run_optimization_analysis(self) -> Dict:
        """
        Run optimization analysis: Analyze current codebase for optimization opportunities.

        This includes:
        - AI language pattern detection and cleanup recommendations
        - Code duplication identification and consolidation opportunities
        - Cross-platform compatibility analysis for test suite
        """
        print("Starting optimization analysis...")

        # AI Language Pattern Analysis
        print("\nScanning for AI language patterns and artifacts...")
        ai_language_results = self._run_ai_language_analysis()

        # Code Duplication Analysis
        print("\nIdentifying code duplication and redundancies...")
        duplication_results = self._run_duplication_analysis()

        # Cross-Platform Test Analysis
        print("\nAnalyzing test suite for cross-platform compatibility...")
        cross_platform_results = self._run_cross_platform_analysis()

        # Generate comprehensive optimization report
        optimization_report = self._generate_optimization_report(
            ai_language_results, duplication_results, cross_platform_results
        )

        # Save optimization report
        report_file = self._save_optimization_report(optimization_report)
        print(f"\nOptimization analysis complete. Report saved to: {report_file}")

        return optimization_report

    def _run_ai_language_analysis(self) -> Dict:
        """Run AI language pattern analysis on all Python source files."""
        print("  Scanning Python files for AI language artifacts...")

        # Scan all Python source files (excluding tests)
        source_files = []
        for py_file in self.project_root.rglob("*.py"):
            if any(
                exclude in str(py_file)
                for exclude in [
                    "test_",
                    "__pycache__",
                    ".git",
                    ".pytest_cache",
                    "venv",
                    "env",
                    ".tox",
                    "build",
                    "dist",
                ]
            ):
                continue
            source_files.append(str(py_file))

        # Analyze each file
        file_reports = {}
        for file_path in source_files:
            try:
                report = self.ai_language_scanner.scan_file(file_path)
                file_reports[file_path] = report
                if report.total_matches > 0:
                    print(
                        f"    Found {report.total_matches} AI language patterns in {Path(file_path).name}"
                    )
            except Exception as e:
                print(f"    Error analyzing {file_path}: {e}")

        # Generate aggregate report
        aggregate_report = self.ai_language_scanner.generate_aggregate_report(
            file_reports
        )

        print("  AI Language Analysis Summary:")
        print(
            f"    Files scanned: {aggregate_report['summary']['total_files_scanned']}"
        )
        print(
            f"    Files with AI language: {aggregate_report['summary']['files_with_ai_language']}"
        )
        print(
            f"    Total AI patterns found: {aggregate_report['summary']['total_ai_patterns_found']}"
        )

        return {"file_reports": file_reports, "aggregate_report": aggregate_report}

    def _run_duplication_analysis(self) -> Dict:
        """Run code duplication analysis on all Python source files."""
        print("  Analyzing code duplication and redundancies...")

        # Analyze all Python source files
        source_files = []
        for py_file in self.project_root.rglob("*.py"):
            if any(
                exclude in str(py_file)
                for exclude in [
                    "__pycache__",
                    ".git",
                    ".pytest_cache",
                    "venv",
                    "env",
                    ".tox",
                    "build",
                    "dist",
                ]
            ):
                continue
            source_files.append(str(py_file))

        # Analyze each file
        file_reports = []
        for file_path in source_files:
            try:
                report = self.duplication_detector.analyze_file(file_path)
                file_reports.append(report)

                issues_count = (
                    len(report.validation_duplicates)
                    + len(report.import_analysis.unused_imports)
                    + len(report.duplicate_blocks)
                )
                if issues_count > 0:
                    print(
                        f"    Found {issues_count} duplication issues in {Path(file_path).name}"
                    )
            except Exception as e:
                print(f"    Error analyzing {file_path}: {e}")

        # Generate aggregate report
        aggregate_report = self.duplication_detector.generate_aggregate_report(
            file_reports
        )

        print("  Code Duplication Analysis Summary:")
        print(
            f"    Files analyzed: {aggregate_report['summary']['total_files_analyzed']}"
        )
        print(
            f"    Files with duplication: {aggregate_report['summary']['files_with_duplication']}"
        )
        print(
            f"    Total validation duplicates: {aggregate_report['summary']['total_validation_duplicates']}"
        )
        print(
            f"    Total unused imports: {aggregate_report['summary']['total_unused_imports']}"
        )

        return {"file_reports": file_reports, "aggregate_report": aggregate_report}

    def _run_cross_platform_analysis(self) -> Dict:
        """Run cross-platform compatibility analysis on test files."""
        print("  Analyzing test suite for cross-platform compatibility...")

        # Find test directories and files
        test_files = []
        for test_dir in ["tests", "test"]:
            test_path = self.project_root / test_dir
            if test_path.exists():
                test_files.extend(test_path.rglob("test_*.py"))

        # If no standard test directories, look for test files anywhere
        if not test_files:
            test_files = list(self.project_root.rglob("test_*.py"))

        # Analyze each test file
        file_reports = {}
        for test_file in test_files:
            if "__pycache__" in str(test_file):
                continue

            try:
                report = self.cross_platform_analyzer.analyze_file(str(test_file))
                file_reports[str(test_file)] = report

                total_issues = (
                    len(report.platform_issues)
                    + len(report.path_issues)
                    + len(report.temp_file_issues)
                    + len(report.missing_skip_markers)
                )
                if total_issues > 0:
                    print(
                        f"    Found {total_issues} compatibility issues in {test_file.name} (Score: {report.ci_compatibility_score}/100)"
                    )
            except Exception as e:
                print(f"    Error analyzing {test_file}: {e}")

        # Generate aggregate report
        aggregate_report = self.cross_platform_analyzer.generate_aggregate_report(
            file_reports
        )

        print("  Cross-Platform Analysis Summary:")
        print(
            f"    Test files analyzed: {aggregate_report['summary']['total_test_files']}"
        )
        print(
            f"    Files with issues: {aggregate_report['summary']['files_with_compatibility_issues']}"
        )
        print(
            f"    Average CI score: {aggregate_report['summary']['average_ci_compatibility_score']}/100"
        )

        return {"file_reports": file_reports, "aggregate_report": aggregate_report}

    def _generate_optimization_report(
        self, ai_results: Dict, duplication_results: Dict, cross_platform_results: Dict
    ) -> Dict:
        """Generate comprehensive optimization analysis report."""
        # Collect file operation lists
        file_operations = self._collect_file_operations()

        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "optimization_summary": {
                "ai_language_analysis": {
                    "files_scanned": ai_results["aggregate_report"]["summary"][
                        "total_files_scanned"
                    ],
                    "files_with_ai_language": ai_results["aggregate_report"]["summary"][
                        "files_with_ai_language"
                    ],
                    "total_patterns_found": ai_results["aggregate_report"]["summary"][
                        "total_ai_patterns_found"
                    ],
                    "category_breakdown": ai_results["aggregate_report"][
                        "category_breakdown"
                    ],
                    "recommendations": ai_results["aggregate_report"][
                        "recommendations"
                    ],
                },
                "duplication_analysis": {
                    "files_analyzed": duplication_results["aggregate_report"][
                        "summary"
                    ]["total_files_analyzed"],
                    "files_with_duplication": duplication_results["aggregate_report"][
                        "summary"
                    ]["files_with_duplication"],
                    "validation_duplicates": duplication_results["aggregate_report"][
                        "summary"
                    ]["total_validation_duplicates"],
                    "unused_imports": duplication_results["aggregate_report"][
                        "summary"
                    ]["total_unused_imports"],
                    "recommendations": duplication_results["aggregate_report"][
                        "recommendations"
                    ],
                },
                "cross_platform_analysis": {
                    "test_files_analyzed": cross_platform_results["aggregate_report"][
                        "summary"
                    ]["total_test_files"],
                    "files_with_issues": cross_platform_results["aggregate_report"][
                        "summary"
                    ]["files_with_compatibility_issues"],
                    "average_ci_score": cross_platform_results["aggregate_report"][
                        "summary"
                    ]["average_ci_compatibility_score"],
                    "platform_issues": cross_platform_results["aggregate_report"][
                        "summary"
                    ]["total_platform_issues"],
                    "path_issues": cross_platform_results["aggregate_report"][
                        "summary"
                    ]["total_path_issues"],
                    "recommendations": cross_platform_results["aggregate_report"][
                        "recommendations"
                    ],
                },
            },
            "file_operations": file_operations,
            "detailed_results": {
                "ai_language_analysis": ai_results,
                "duplication_analysis": duplication_results,
                "cross_platform_analysis": cross_platform_results,
            },
            "overall_recommendations": self._generate_overall_optimization_recommendations(
                ai_results, duplication_results, cross_platform_results
            ),
        }

    def _generate_overall_optimization_recommendations(
        self, ai_results: Dict, duplication_results: Dict, cross_platform_results: Dict
    ) -> List[str]:
        """Generate overall prioritized optimization recommendations."""
        recommendations = []

        # High priority items
        ai_high_severity = ai_results["aggregate_report"]["severity_breakdown"].get(
            "high", 0
        )
        if ai_high_severity > 0:
            recommendations.append(
                f"HIGH PRIORITY: Remove {ai_high_severity} high-severity AI language artifacts (marketing phrases)"
            )

        platform_issues = cross_platform_results["aggregate_report"]["summary"][
            "total_platform_issues"
        ]
        if platform_issues > 0:
            recommendations.append(
                f"HIGH PRIORITY: Fix {platform_issues} platform-specific compatibility issues in tests"
            )

        # Medium priority items
        validation_duplicates = duplication_results["aggregate_report"]["summary"][
            "total_validation_duplicates"
        ]
        if validation_duplicates > 10:
            recommendations.append(
                f"MEDIUM PRIORITY: Consolidate {validation_duplicates} duplicate validation patterns"
            )

        path_issues = cross_platform_results["aggregate_report"]["summary"][
            "total_path_issues"
        ]
        if path_issues > 5:
            recommendations.append(
                f"MEDIUM PRIORITY: Fix {path_issues} hardcoded path issues for cross-platform compatibility"
            )

        # Low priority items
        unused_imports = duplication_results["aggregate_report"]["summary"][
            "total_unused_imports"
        ]
        if unused_imports > 5:
            recommendations.append(
                f"LOW PRIORITY: Remove {unused_imports} unused import statements"
            )

        ai_total = ai_results["aggregate_report"]["summary"]["total_ai_patterns_found"]
        if ai_total > ai_high_severity and ai_total > 10:
            recommendations.append(
                f"LOW PRIORITY: Replace {ai_total - ai_high_severity} remaining AI language patterns with technical terms"
            )

        if not recommendations:
            recommendations.append(
                "Excellent code quality - no significant optimization opportunities detected"
            )

        return recommendations

    def _save_optimization_report(self, report: Dict) -> str:
        """Save optimization analysis report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"optimization_analysis_{timestamp}.json"

        # Create a simplified report for JSON serialization (exclude detailed file reports)
        simplified_report = {
            "analysis_timestamp": report["analysis_timestamp"],
            "project_root": report["project_root"],
            "optimization_summary": report["optimization_summary"],
            "overall_recommendations": report["overall_recommendations"],
        }

        with open(report_file, "w") as f:
            json.dump(simplified_report, f, indent=2)

        return str(report_file)

    def validate_cleanup_environment(self) -> Dict:
        """Validate environment setup for documentation cleanup process."""
        print("🔍 Validating cleanup environment...")

        results = {
            "validation_timestamp": datetime.now().isoformat(),
            "environment_checks": {},
            "cleanup_ready": True,
        }

        # Check test suite baseline
        results["environment_checks"]["test_suite"] = self._check_test_suite_baseline()

        # Check analysis tools functionality
        results["environment_checks"]["analysis_tools"] = (
            self._check_analysis_tools_ready()
        )

        # Check critical files
        results["environment_checks"]["critical_files"] = (
            self._check_critical_files_exist()
        )

        # Check for blocking issues
        blocking_issues = self._check_cleanup_blocking_issues()
        results["environment_checks"]["blocking_issues"] = blocking_issues

        # Determine if cleanup is ready
        results["cleanup_ready"] = len(blocking_issues.get("issues", [])) == 0

        # Save validation results
        self._save_cleanup_validation_results("environment_validation", results)

        return results

    def validate_cleanup_phase(self, phase: str) -> Dict:
        """Validate specific cleanup phase readiness."""
        print(f"🔍 Validating cleanup phase: {phase}")

        phase_validators = {
            "dependencies": self._validate_dependency_migration_phase,
            "ai_artifacts": self._validate_ai_artifacts_phase,
            "test_optimization": self._validate_test_optimization_phase,
        }

        if phase not in phase_validators:
            raise ValueError(f"Unknown cleanup phase: {phase}")

        results = phase_validators[phase]()
        self._save_cleanup_validation_results(f"{phase}_phase_validation", results)

        return results

    def _check_test_suite_baseline(self) -> Dict:
        """Check test suite baseline for cleanup validation."""
        try:
            import subprocess
            import sys

            # Check if pytest is available
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Count test files
            test_files = list(self.project_root.rglob("tests/**/test_*.py"))

            return {
                "status": "pass" if result.returncode == 0 else "fail",
                "pytest_available": result.returncode == 0,
                "total_test_files": len(test_files),
                "test_directories": [
                    str(d.relative_to(self.project_root))
                    for d in self.project_root.glob("tests/*")
                    if d.is_dir()
                ],
                "details": (
                    result.stdout.strip() if result.returncode == 0 else result.stderr
                ),
            }
        except Exception as e:
            return {
                "status": "fail",
                "error": str(e),
                "pytest_available": False,
                "total_test_files": 0,
            }

    def _check_analysis_tools_ready(self) -> Dict:
        """Check if analysis tools are ready for cleanup validation."""
        tools_status = {
            "ai_language_scanner": False,
            "duplication_detector": False,
            "cross_platform_analyzer": False,
            "pattern_detector": False,
        }

        try:
            # Test each tool
            tools_status["ai_language_scanner"] = hasattr(
                self.ai_language_scanner, "scan_file"
            )
            tools_status["duplication_detector"] = hasattr(
                self.duplication_detector, "analyze_file"
            )
            tools_status["cross_platform_analyzer"] = hasattr(
                self.cross_platform_analyzer, "analyze_file"
            )
            tools_status["pattern_detector"] = hasattr(
                self.pattern_detector, "detect_ai_language_in_text"
            )

            all_ready = all(tools_status.values())

            return {
                "status": "pass" if all_ready else "fail",
                "tools_ready": tools_status,
                "all_tools_available": all_ready,
            }
        except Exception as e:
            return {"status": "fail", "error": str(e), "tools_ready": tools_status}

    def _check_critical_files_exist(self) -> Dict:
        """Check if critical files exist for cleanup process."""
        critical_files = [
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "requirements-test.txt",
            "FollowWeb_Visualizor/__init__.py",
        ]

        missing_files = []
        existing_files = []

        for file_path in critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)

        return {
            "status": "pass" if not missing_files else "warn",
            "existing_files": existing_files,
            "missing_files": missing_files,
            "all_critical_present": len(missing_files) == 0,
        }

    def _check_cleanup_blocking_issues(self) -> Dict:
        """Check for issues that would block cleanup process."""
        issues = []

        # Check main package directory
        if not (self.project_root / "FollowWeb_Visualizor").exists():
            issues.append("Main package directory 'FollowWeb_Visualizor' not found")

        # Check tests directory
        if not (self.project_root / "tests").exists():
            issues.append("Tests directory not found")

        # Check analysis tools directory
        if not (self.project_root / "analysis_tools").exists():
            issues.append("Analysis tools directory not found")

        # Try importing main package
        try:
            import FollowWeb_Visualizor  # noqa: F401
        except ImportError as e:
            issues.append(f"Cannot import main package: {e}")

        return {
            "status": "pass" if not issues else "fail",
            "issues": issues,
            "blocking_issues_count": len(issues),
        }

    def _validate_dependency_migration_phase(self) -> Dict:
        """Validate dependency migration phase readiness."""
        results = {
            "phase": "dependency_migration",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # Check for autopep8 references
        results["checks"]["autopep8_references"] = self._find_autopep8_references()

        # Check ruff configuration
        results["checks"]["ruff_config"] = self._check_ruff_configuration()

        return results

    def _validate_ai_artifacts_phase(self) -> Dict:
        """Validate AI artifacts detection phase readiness."""
        results = {
            "phase": "ai_artifacts_detection",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # Use existing AI language scanner
        print("  🤖 Scanning for AI artifacts...")
        ai_scan_results = self._scan_ai_artifacts_for_cleanup()
        results["checks"]["ai_artifacts"] = ai_scan_results

        # Check for specific AI artifacts
        results["checks"]["specific_artifact"] = self._check_specific_ai_artifact()

        return results

    def _validate_test_optimization_phase(self) -> Dict:
        """Validate test optimization phase readiness."""
        results = {
            "phase": "test_optimization",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # Find pytest skip patterns
        results["checks"]["skip_patterns"] = self._find_pytest_skip_patterns()

        # Check for specific skip patterns
        results["checks"]["specific_skips"] = self._check_specific_skip_patterns()

        return results

    def _find_autopep8_references(self) -> Dict:
        """Find autopep8 references in configuration files."""
        config_files = [
            "setup.cfg",
            "tox.ini",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "requirements-test.txt",
        ]
        autopep8_refs = []

        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if "autopep8" in content.lower():
                        autopep8_refs.append(config_file)
                except Exception:
                    pass

        return {"files_with_autopep8": autopep8_refs, "count": len(autopep8_refs)}

    def _check_ruff_configuration(self) -> Dict:
        """Check existing ruff configuration."""
        ruff_configs = []

        # Check pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                if "[tool.ruff]" in content:
                    ruff_configs.append("pyproject.toml")
            except Exception:
                pass

        return {
            "config_files": ruff_configs,
            "has_ruff_config": len(ruff_configs) > 0,
        }

    def _scan_ai_artifacts_for_cleanup(self) -> Dict:
        """Scan for AI artifacts using existing scanner."""
        try:
            # Get all Python files
            python_files = []
            for py_file in self.project_root.rglob("*.py"):
                if any(
                    exclude in str(py_file)
                    for exclude in ["__pycache__", ".git", "venv", "env"]
                ):
                    continue
                python_files.append(str(py_file))

            # Use existing AI language scanner
            file_reports = {}
            total_artifacts = 0

            for file_path in python_files[:10]:  # Limit for validation
                try:
                    report = self.ai_language_scanner.scan_file(file_path)
                    if report.total_matches > 0:
                        file_reports[file_path] = report
                        total_artifacts += report.total_matches
                except Exception:
                    continue

            return {
                "total_files_scanned": len(python_files[:10]),
                "files_with_artifacts": len(file_reports),
                "total_artifacts_found": total_artifacts,
                "sample_files": list(file_reports.keys())[:5],
            }
        except Exception as e:
            return {"error": str(e), "total_artifacts_found": 0}

    def _check_specific_ai_artifact(self) -> Dict:
        """Check for specific AI artifacts in test files."""
        target_file = self.project_root / "test_ui_ux_performance_validation.py"
        target_pattern = (
            "# Create a small test dataset in the correct format (list of user objects)"
        )

        found = False
        line_number = None

        if target_file.exists():
            try:
                lines = target_file.read_text(encoding="utf-8").splitlines()
                for i, line in enumerate(lines, 1):
                    if target_pattern in line:
                        found = True
                        line_number = i
                        break
            except Exception:
                pass

        return {
            "target_file": str(target_file.name),
            "pattern_found": found,
            "line_number": line_number,
            "pattern": target_pattern,
        }

    def _find_pytest_skip_patterns(self) -> Dict:
        """Find pytest skip patterns in test files."""
        skip_patterns = ["pytest.skip", "@pytest.mark.skip", "skipif"]
        found_skips = []

        for test_file in self.project_root.rglob("tests/**/test_*.py"):
            try:
                content = test_file.read_text(encoding="utf-8")
                for pattern in skip_patterns:
                    if pattern in content:
                        found_skips.append(
                            {
                                "file": str(test_file.relative_to(self.project_root)),
                                "pattern": pattern,
                            }
                        )
                        break  # Only count each file once
            except Exception:
                continue

        return {"files_with_skips": found_skips, "count": len(found_skips)}

    def _check_specific_skip_patterns(self) -> Dict:
        """Check for specific skip patterns in test files."""
        specific_patterns = [
            "format_number_clean function not yet implemented",
            "LoggingState not yet implemented",
        ]

        found_patterns = []

        for test_file in self.project_root.rglob("tests/**/test_*.py"):
            try:
                content = test_file.read_text(encoding="utf-8")
                for pattern in specific_patterns:
                    if pattern in content:
                        found_patterns.append(
                            {
                                "file": str(test_file.relative_to(self.project_root)),
                                "pattern": pattern,
                            }
                        )
            except Exception:
                continue

        return {"specific_patterns_found": found_patterns, "count": len(found_patterns)}

    def _save_cleanup_validation_results(
        self, validation_type: str, results: Dict
    ) -> None:
        """Save cleanup validation results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.reports_dir / f"cleanup_{validation_type}_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"  💾 Validation results saved to: {results_file}")

    def _collect_file_operations(self) -> Dict:
        """Collect lists of files that would be operated on by various tools."""
        file_operations = {
            "cleanup_operations": {},
            "delete_operations": {},
        }

        # Get test output files that would be cleaned up by cleanup_test_outputs.py
        try:
            test_output_files = list(self.project_root.rglob("**/test_output_*.txt"))
            file_operations["cleanup_operations"]["test_outputs"] = [
                str(f) for f in test_output_files
            ]
        except Exception as e:
            file_operations["cleanup_operations"]["test_outputs"] = {"error": str(e)}

        return file_operations
