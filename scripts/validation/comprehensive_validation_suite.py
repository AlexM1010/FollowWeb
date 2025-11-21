"""Comprehensive Validation Suite for GitHub Actions Workflows.

This script validates all workflows by:
1. Checking workflow syntax and structure (actionlint)
2. Verifying workflow_dispatch triggers are present
3. Checking expected artifacts are defined
4. Generating a comprehensive validation report

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import json
import sys
import subprocess
import platform
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import yaml

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


@dataclass
class WorkflowArtifact:
    """Expected artifact for a workflow."""

    name: str
    condition: str
    required: bool


@dataclass
class WorkflowValidation:
    """Validation result for a single workflow."""

    name: str
    file_path: str
    syntax_valid: bool
    has_workflow_dispatch: bool
    expected_artifacts: List[WorkflowArtifact]
    found_artifacts: List[str]
    missing_artifacts: List[str]
    errors: List[str]
    warnings: List[str]
    notes: List[str]
    status: str  # "pass", "fail", "warning"


@dataclass
class ValidationReport:
    """Comprehensive validation report."""

    timestamp: str
    total_workflows: int
    passed: int
    failed: int
    warnings: int
    workflows: List[WorkflowValidation]
    overall_status: str  # "pass", "fail"


# Expected artifacts for each workflow
WORKFLOW_ARTIFACTS = {
    "ci.yml": [
        WorkflowArtifact("security-reports", "always()", False),
        WorkflowArtifact("python-package-distributions", "success", True),
        WorkflowArtifact("coverage-reports", "matrix.os == 'ubuntu-latest'", True),
        WorkflowArtifact("benchmark-results", "always()", False),
    ],
    "freesound-nightly-pipeline.yml": [
        WorkflowArtifact("checkpoint-backup-*", "always()", True),
        WorkflowArtifact("collection-logs-*", "always()", True),
    ],
    "freesound-backup.yml": [
        # Backup workflow uploads to private repo, not artifacts
    ],
    "freesound-quick-validation.yml": [
        WorkflowArtifact("quick-validation-report-*", "success", True),
        WorkflowArtifact("quick-validation-logs-*", "always()", True),
        WorkflowArtifact("checkpoint-backup-*", "failure()", False),
    ],
    "freesound-full-validation.yml": [
        WorkflowArtifact("full-validation-report-*", "success", True),
        WorkflowArtifact("full-validation-logs-*", "always()", True),
        WorkflowArtifact("checkpoint-backup-*", "failure()", False),
    ],
    "freesound-data-repair.yml": [
        WorkflowArtifact("repair-logs-*", "always()", True),
    ],
    "freesound-metrics-dashboard.yml": [
        WorkflowArtifact("metrics-dashboard", "success", False),
    ],
    "freesound-validation-visualization.yml": [
        # Deploys to GitHub Pages, not artifacts
    ],
    "deploy-website.yml": [
        # Deploys to GitHub Pages, not artifacts
    ],
    "nightly.yml": [
        # Nightly dependency check, no artifacts expected
    ],
    "reviewdog.yml": [
        WorkflowArtifact("reviewdog-analysis-reports", "always()", False),
    ],
    "release.yml": [
        WorkflowArtifact("python-package-distributions", "success", True),
    ],
    "docs.yml": [
        WorkflowArtifact("documentation-structure-reports", "always()", False),
        WorkflowArtifact("docstring-coverage-reports", "always()", False),
    ],
    "large-graph-analysis.yml": [
        WorkflowArtifact("graph-partitions", "success", True),
        WorkflowArtifact("partition-results-*", "success", True),
        WorkflowArtifact("final-analysis", "success", True),
    ],
    "freesound-data-remediation.yml": [
        WorkflowArtifact("remediation-artifacts", "always()", True),
    ],
    "freesound-backup-maintenance.yml": [
        # Maintenance workflow, no artifacts expected
    ],
    "pages.yml": [
        # GitHub Pages deployment, no artifacts
    ],
    "codespaces-prebuild.yml": [
        # Codespaces prebuild, no artifacts
    ],
}


def check_actionlint_available():
    """Check if actionlint binary is available."""
    try:
        result = subprocess.run(
            ["actionlint", "-version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_actionlint(
    workflow_files: List[Path],
) -> Tuple[List[str], List[str], List[str]]:
    """Run actionlint on workflow files and return errors, warnings, notes."""
    actionlint_cmd = (
        "actionlint.exe" if platform.system() == "Windows" else "./actionlint"
    )
    if check_actionlint_available():
        actionlint_cmd = "actionlint"

    try:
        config_file = Path(".github/actionlint.yaml")
        cmd = [actionlint_cmd]
        if config_file.exists():
            cmd.extend(["-config-file", str(config_file)])
        cmd.extend(
            [
                "-format",
                '{{range $err := .}}{{$err.Filepath}}:{{$err.Line}}:{{$err.Column}}: {{$err.Kind}}: {{$err.Message}} [{{$err.Code}}]{{"\n"}}{{end}}',
            ]
        )
        cmd.extend([str(f) for f in workflow_files])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        errors = []
        warnings = []
        notes = []

        if result.returncode != 0 or result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line:
                    if ": error:" in line:
                        errors.append(line)
                    elif ": warning:" in line or ": style:" in line:
                        warnings.append(line)
                    elif ": note:" in line:
                        notes.append(line)
                    else:
                        warnings.append(line)

        return errors, warnings, notes

    except subprocess.TimeoutExpired:
        return ["actionlint timeout after 30 seconds"], [], []
    except Exception as e:
        return [f"actionlint error: {e}"], [], []


def parse_workflow_yaml(workflow_path: Path) -> Optional[dict]:
    """Parse workflow YAML file."""
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error parsing {workflow_path}: {e}")
        return None


def check_workflow_dispatch(workflow_data: dict) -> bool:
    """Check if workflow has workflow_dispatch trigger."""
    if not workflow_data:
        return False

    on_section = workflow_data.get("on", {})
    if isinstance(on_section, dict):
        return "workflow_dispatch" in on_section
    elif isinstance(on_section, list):
        return "workflow_dispatch" in on_section

    return False


def extract_artifacts(workflow_data: dict) -> List[str]:
    """Extract artifact names from workflow."""
    artifacts = []

    if not workflow_data:
        return artifacts

    jobs = workflow_data.get("jobs", {})
    for job_name, job_data in jobs.items():
        if not isinstance(job_data, dict):
            continue

        steps = job_data.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue

            uses = step.get("uses", "")
            if "actions/upload-artifact" in uses:
                with_section = step.get("with", {})
                artifact_name = with_section.get("name", "")
                if artifact_name:
                    artifacts.append(artifact_name)

    return artifacts


def validate_workflow(
    workflow_path: Path,
    all_errors: List[str],
    all_warnings: List[str],
    all_notes: List[str],
) -> WorkflowValidation:
    """Validate a single workflow file."""
    workflow_name = workflow_path.name

    # Parse workflow
    workflow_data = parse_workflow_yaml(workflow_path)
    syntax_valid = workflow_data is not None

    # Check workflow_dispatch
    has_dispatch = check_workflow_dispatch(workflow_data)

    # Extract artifacts
    found_artifacts = extract_artifacts(workflow_data)

    # Get expected artifacts
    expected_artifacts = WORKFLOW_ARTIFACTS.get(workflow_name, [])

    # Check for missing required artifacts
    missing_artifacts = []
    for expected in expected_artifacts:
        if expected.required:
            # Check if any found artifact matches (handle wildcards)
            expected_name = expected.name.replace("*", "")
            matched = any(expected_name in found for found in found_artifacts)
            if not matched:
                missing_artifacts.append(expected.name)

    # Filter errors/warnings/notes for this workflow
    workflow_errors = [e for e in all_errors if workflow_name in e]
    workflow_warnings = [w for w in all_warnings if workflow_name in w]
    workflow_notes = [n for n in all_notes if workflow_name in n]

    # Determine status
    if workflow_errors or missing_artifacts:
        status = "fail"
    elif workflow_warnings:
        status = "warning"
    else:
        status = "pass"

    return WorkflowValidation(
        name=workflow_name,
        file_path=str(workflow_path),
        syntax_valid=syntax_valid,
        has_workflow_dispatch=has_dispatch,
        expected_artifacts=expected_artifacts,
        found_artifacts=found_artifacts,
        missing_artifacts=missing_artifacts,
        errors=workflow_errors,
        warnings=workflow_warnings,
        notes=workflow_notes,
        status=status,
    )


def generate_report(workflows: List[WorkflowValidation]) -> ValidationReport:
    """Generate comprehensive validation report."""
    passed = sum(1 for w in workflows if w.status == "pass")
    failed = sum(1 for w in workflows if w.status == "fail")
    warnings = sum(1 for w in workflows if w.status == "warning")

    overall_status = "pass" if failed == 0 else "fail"

    return ValidationReport(
        timestamp=datetime.now().isoformat(),
        total_workflows=len(workflows),
        passed=passed,
        failed=failed,
        warnings=warnings,
        workflows=workflows,
        overall_status=overall_status,
    )


def print_report(report: ValidationReport):
    """Print validation report to console."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE WORKFLOW VALIDATION REPORT")
    print("=" * 80)
    print(f"\nTimestamp: {report.timestamp}")
    print(f"Total Workflows: {report.total_workflows}")
    print(f"Passed: {report.passed}")
    print(f"Failed: {report.failed}")
    print(f"Warnings: {report.warnings}")
    print(f"Overall Status: {report.overall_status.upper()}")
    print("\n" + "-" * 80)

    # Print individual workflow results
    for workflow in report.workflows:
        status_icon = (
            "✓"
            if workflow.status == "pass"
            else "✗"
            if workflow.status == "fail"
            else "⚠"
        )
        print(f"\n{status_icon} {workflow.name} [{workflow.status.upper()}]")
        print(f"  Path: {workflow.file_path}")
        print(f"  Syntax Valid: {workflow.syntax_valid}")
        print(f"  Has workflow_dispatch: {workflow.has_workflow_dispatch}")

        if workflow.found_artifacts:
            print(f"  Found Artifacts: {', '.join(workflow.found_artifacts)}")

        if workflow.missing_artifacts:
            print(
                f"  ❌ Missing Required Artifacts: {', '.join(workflow.missing_artifacts)}"
            )

        if workflow.errors:
            print(f"  ❌ Errors ({len(workflow.errors)}):")
            for error in workflow.errors:
                print(f"    {error}")

        if workflow.warnings:
            print(f"  ⚠ Warnings ({len(workflow.warnings)}):")
            for warning in workflow.warnings:
                print(f"    {warning}")

        if workflow.notes:
            print(f"  💡 Notes ({len(workflow.notes)}):")
            for note in workflow.notes:
                print(f"    {note}")

    print("\n" + "=" * 80)


def save_report_json(report: ValidationReport, output_path: Path):
    """Save validation report as JSON."""
    # Convert dataclasses to dict
    report_dict = asdict(report)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    print(f"\n✓ Report saved to: {output_path}")


def main():
    """Run comprehensive validation suite."""
    print("Starting Comprehensive Workflow Validation Suite...")
    print("Requirements: 10.1, 10.2, 10.3, 10.4, 10.5\n")

    # Find all workflow files
    workflows_dir = Path(".github/workflows")
    workflow_files = list(workflows_dir.glob("*.yml"))

    if not workflow_files:
        print("❌ No workflow files found")
        return 1

    print(f"Found {len(workflow_files)} workflow files\n")

    # Check actionlint availability
    if not check_actionlint_available():
        print("⚠️ actionlint not found - syntax validation will be limited")
        print("  Install from: https://github.com/rhysd/actionlint\n")

    # Run actionlint on all workflows
    print("Running actionlint validation...")
    all_errors, all_warnings, all_notes = run_actionlint(workflow_files)
    print(f"  Errors: {len(all_errors)}")
    print(f"  Warnings: {len(all_warnings)}")
    print(f"  Notes: {len(all_notes)}\n")

    # Validate each workflow
    print("Validating individual workflows...")
    workflows = []
    for workflow_path in sorted(workflow_files):
        validation = validate_workflow(
            workflow_path, all_errors, all_warnings, all_notes
        )
        workflows.append(validation)
        status_icon = (
            "✓"
            if validation.status == "pass"
            else "✗"
            if validation.status == "fail"
            else "⚠"
        )
        print(f"  {status_icon} {validation.name}")

    # Generate report
    report = generate_report(workflows)

    # Print report
    print_report(report)

    # Save report as JSON
    output_dir = Path("scripts/validation/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        output_dir
        / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    save_report_json(report, output_path)

    # Return exit code based on overall status
    if report.overall_status == "pass":
        print("\n✅ All workflows passed validation!")
        return 0
    else:
        print(f"\n❌ Validation failed: {report.failed} workflow(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
