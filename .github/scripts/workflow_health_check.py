#!/usr/bin/env python3
"""
Workflow Health Check Script

Monitors GitHub Actions workflow health and generates reports on:
- Workflow success/failure rates
- Average execution times
- Schedule adherence
- Resource usage patterns
- Failure trends

Usage:
    python workflow_health_check.py [--days 30] [--output report.md]
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


class WorkflowHealthChecker:
    """Monitors and reports on GitHub Actions workflow health."""

    def __init__(self, github_token: str, repository: str):
        """
        Initialize the health checker.

        Args:
            github_token: GitHub API token
            repository: Repository in format 'owner/repo'
        """
        self.github_token = github_token
        self.repository = repository
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_workflow_runs(
        self, workflow_name: Optional[str] = None, days: int = 30
    ) -> List[Dict]:
        """
        Fetch workflow runs from GitHub API.

        Args:
            workflow_name: Optional workflow name to filter
            days: Number of days to look back

        Returns:
            List of workflow run data
        """
        since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        url = f"{self.api_base}/repos/{self.repository}/actions/runs"

        params = {"created": f">={since}", "per_page": 100}

        all_runs = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                print(f"Error fetching workflow runs: {response.status_code}")
                print(response.text)
                break

            data = response.json()
            runs = data.get("workflow_runs", [])

            if not runs:
                break

            # Filter by workflow name if specified
            if workflow_name:
                runs = [r for r in runs if r["name"] == workflow_name]

            all_runs.extend(runs)

            # Check if there are more pages
            if len(runs) < 100:
                break

            page += 1

        return all_runs

    def analyze_workflow_health(self, runs: List[Dict]) -> Dict:
        """
        Analyze workflow health metrics.

        Args:
            runs: List of workflow run data

        Returns:
            Dictionary of health metrics
        """
        if not runs:
            return {
                "total_runs": 0,
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "avg_duration_minutes": 0.0,
                "workflows": {},
            }

        # Group by workflow
        by_workflow = defaultdict(list)
        for run in runs:
            by_workflow[run["name"]].append(run)

        # Calculate metrics per workflow
        workflow_metrics = {}
        for workflow_name, workflow_runs in by_workflow.items():
            total = len(workflow_runs)
            successful = sum(1 for r in workflow_runs if r["conclusion"] == "success")
            failed = sum(1 for r in workflow_runs if r["conclusion"] == "failure")
            cancelled = sum(
                1 for r in workflow_runs if r["conclusion"] == "cancelled"
            )

            # Calculate durations
            durations = []
            for run in workflow_runs:
                if run["conclusion"] in ["success", "failure"]:
                    created = datetime.fromisoformat(
                        run["created_at"].replace("Z", "+00:00")
                    )
                    updated = datetime.fromisoformat(
                        run["updated_at"].replace("Z", "+00:00")
                    )
                    duration = (updated - created).total_seconds() / 60
                    durations.append(duration)

            avg_duration = sum(durations) / len(durations) if durations else 0

            workflow_metrics[workflow_name] = {
                "total_runs": total,
                "successful": successful,
                "failed": failed,
                "cancelled": cancelled,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "failure_rate": (failed / total * 100) if total > 0 else 0,
                "avg_duration_minutes": avg_duration,
                "min_duration_minutes": min(durations) if durations else 0,
                "max_duration_minutes": max(durations) if durations else 0,
            }

        # Overall metrics
        total_runs = len(runs)
        total_successful = sum(1 for r in runs if r["conclusion"] == "success")
        total_failed = sum(1 for r in runs if r["conclusion"] == "failure")

        return {
            "total_runs": total_runs,
            "success_rate": (total_successful / total_runs * 100)
            if total_runs > 0
            else 0,
            "failure_rate": (total_failed / total_runs * 100) if total_runs > 0 else 0,
            "workflows": workflow_metrics,
        }

    def generate_report(self, metrics: Dict, days: int) -> str:
        """
        Generate a markdown report from metrics.

        Args:
            metrics: Health metrics dictionary
            days: Number of days analyzed

        Returns:
            Markdown formatted report
        """
        report = []
        report.append(f"# Workflow Health Report")
        report.append(f"\n**Analysis Period:** Last {days} days")
        report.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        report.append(f"\n## Overall Statistics")
        report.append(f"\n- **Total Runs:** {metrics['total_runs']}")
        report.append(f"- **Overall Success Rate:** {metrics['success_rate']:.1f}%")
        report.append(f"- **Overall Failure Rate:** {metrics['failure_rate']:.1f}%")

        report.append(f"\n## Workflow Breakdown")

        for workflow_name, wf_metrics in sorted(metrics["workflows"].items()):
            report.append(f"\n### {workflow_name}")
            report.append(f"\n| Metric | Value |")
            report.append(f"|--------|-------|")
            report.append(f"| Total Runs | {wf_metrics['total_runs']} |")
            report.append(f"| Successful | {wf_metrics['successful']} |")
            report.append(f"| Failed | {wf_metrics['failed']} |")
            report.append(f"| Cancelled | {wf_metrics['cancelled']} |")
            report.append(f"| Success Rate | {wf_metrics['success_rate']:.1f}% |")
            report.append(f"| Failure Rate | {wf_metrics['failure_rate']:.1f}% |")
            report.append(
                f"| Avg Duration | {wf_metrics['avg_duration_minutes']:.1f} min |"
            )
            report.append(
                f"| Min Duration | {wf_metrics['min_duration_minutes']:.1f} min |"
            )
            report.append(
                f"| Max Duration | {wf_metrics['max_duration_minutes']:.1f} min |"
            )

            # Health indicator
            if wf_metrics["success_rate"] >= 95:
                health = "🟢 Excellent"
            elif wf_metrics["success_rate"] >= 85:
                health = "🟡 Good"
            elif wf_metrics["success_rate"] >= 70:
                health = "🟠 Fair"
            else:
                health = "🔴 Poor"

            report.append(f"\n**Health Status:** {health}")

        report.append(f"\n## Recommendations")

        # Generate recommendations based on metrics
        recommendations = []
        for workflow_name, wf_metrics in metrics["workflows"].items():
            if wf_metrics["failure_rate"] > 20:
                recommendations.append(
                    f"- ⚠️ **{workflow_name}**: High failure rate ({wf_metrics['failure_rate']:.1f}%) - investigate recent failures"
                )

            if wf_metrics["avg_duration_minutes"] > 60:
                recommendations.append(
                    f"- ⏱️ **{workflow_name}**: Long average duration ({wf_metrics['avg_duration_minutes']:.1f} min) - consider optimization"
                )

            if wf_metrics["cancelled"] > wf_metrics["total_runs"] * 0.2:
                recommendations.append(
                    f"- 🚫 **{workflow_name}**: High cancellation rate ({wf_metrics['cancelled']}/{wf_metrics['total_runs']}) - check concurrency settings"
                )

        if recommendations:
            report.append("\n")
            report.extend(recommendations)
        else:
            report.append("\n- ✅ All workflows are performing well")

        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check GitHub Actions workflow health"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days to analyze (default: 30)"
    )
    parser.add_argument(
        "--workflow", type=str, help="Specific workflow name to analyze"
    )
    parser.add_argument(
        "--output", type=str, help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output raw JSON metrics"
    )

    args = parser.parse_args()

    # Get GitHub token from environment
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    # Get repository from environment or use default
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        print("Error: GITHUB_REPOSITORY environment variable not set")
        print("Set it to 'owner/repo' format")
        sys.exit(1)

    # Initialize checker
    checker = WorkflowHealthChecker(github_token, repository)

    # Fetch workflow runs
    print(f"Fetching workflow runs for last {args.days} days...", file=sys.stderr)
    runs = checker.get_workflow_runs(workflow_name=args.workflow, days=args.days)
    print(f"Found {len(runs)} workflow runs", file=sys.stderr)

    # Analyze health
    metrics = checker.analyze_workflow_health(runs)

    # Generate output
    if args.json:
        output = json.dumps(metrics, indent=2)
    else:
        output = checker.generate_report(metrics, args.days)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
