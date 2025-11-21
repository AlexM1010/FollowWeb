#!/usr/bin/env python3
"""
End-to-End Data Flow Verification Script

This script verifies the complete workflow chain:
1. Nightly collection
2. Checkpoint upload to private repository
3. Cache save with all three files
4. Repair workflow receives and processes data
5. Validation workflow receives data from cache
6. Backup workflow creates backup
7. Visualization generated and deployed
8. Data persists across workflow chain

Usage:
    python scripts/validation/verify_e2e_flow.py --trigger-collection
    python scripts/validation/verify_e2e_flow.py --check-status <run_id>
    python scripts/validation/verify_e2e_flow.py --verify-all
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorkflowVerifier:
    """Verifies end-to-end workflow execution."""

    def __init__(self, repo: str, github_token: Optional[str] = None):
        """
        Initialize workflow verifier.

        Args:
            repo: GitHub repository (owner/name)
            github_token: GitHub token for API access
        """
        self.repo = repo
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in environment")

    def trigger_nightly_collection(
        self, max_requests: int = 100, discovery_mode: str = "search"
    ) -> tuple[bool, str]:
        """
        Trigger nightly collection workflow.

        Args:
            max_requests: Maximum API requests (circuit breaker)
            discovery_mode: Discovery strategy (search, relationships, mixed)

        Returns:
            Tuple of (success: bool, run_id: str)
        """
        logger.info("🚀 Triggering nightly collection workflow...")

        try:
            # Use gh CLI to trigger workflow
            cmd = [
                "gh",
                "workflow",
                "run",
                "freesound-nightly-pipeline.yml",
                "--repo",
                self.repo,
                "--ref",
                "main",
                "--field",
                f"max_requests={max_requests}",
                "--field",
                f"discovery_mode={discovery_mode}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info(f"✅ Workflow triggered: {result.stdout.strip()}")

            # Get the run ID from the most recent run
            time.sleep(5)  # Wait for workflow to appear
            run_id = self._get_latest_run_id("freesound-nightly-pipeline.yml")

            return True, run_id

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to trigger workflow: {e.stderr}")
            return False, ""

    def _get_latest_run_id(self, workflow_name: str) -> str:
        """Get the latest run ID for a workflow."""
        try:
            cmd = [
                "gh",
                "run",
                "list",
                "--repo",
                self.repo,
                "--workflow",
                workflow_name,
                "--limit",
                "1",
                "--json",
                "databaseId",
                "--jq",
                ".[0].databaseId",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get run ID: {e.stderr}")
            return ""

    def monitor_workflow_run(
        self, run_id: str, timeout: int = 7200
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Monitor workflow run until completion.

        Args:
            run_id: GitHub Actions run ID
            timeout: Maximum time to wait (seconds)

        Returns:
            Tuple of (success: bool, conclusion: str, details: dict)
        """
        logger.info(f"👀 Monitoring workflow run {run_id}...")

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                # Get run status
                cmd = [
                    "gh",
                    "run",
                    "view",
                    run_id,
                    "--repo",
                    self.repo,
                    "--json",
                    "status,conclusion,name,createdAt,updatedAt",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                run_data = json.loads(result.stdout)
                status = run_data.get("status")
                conclusion = run_data.get("conclusion")

                # Log status changes
                if status != last_status:
                    logger.info(f"  Status: {status}")
                    last_status = status

                # Check if completed
                if status == "completed":
                    logger.info(f"✅ Workflow completed: {conclusion}")
                    return True, conclusion, run_data

                # Wait before checking again
                time.sleep(30)

            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to get run status: {e.stderr}")
                return False, "error", {}

        logger.error("❌ Timeout waiting for workflow to complete")
        return False, "timeout", {}

    def verify_checkpoint_upload(self, run_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Verify checkpoint was uploaded to private repository.

        Args:
            run_id: GitHub Actions run ID

        Returns:
            Tuple of (success: bool, details: dict)
        """
        logger.info("📤 Verifying checkpoint upload to private repository...")

        # Check workflow logs for upload confirmation
        try:
            cmd = ["gh", "run", "view", run_id, "--repo", self.repo, "--log"]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logs = result.stdout

            # Look for upload success indicators
            upload_success = "Backup uploaded successfully" in logs
            verification_passed = "Backup verification passed" in logs

            details = {
                "upload_success": upload_success,
                "verification_passed": verification_passed,
                "run_id": run_id,
            }

            if upload_success and verification_passed:
                logger.info("✅ Checkpoint uploaded and verified")
                return True, details
            else:
                logger.error("❌ Checkpoint upload or verification failed")
                return False, details

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check logs: {e.stderr}")
            return False, {}

    def verify_cache_save(self, run_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Verify cache was saved with all three checkpoint files.

        Args:
            run_id: GitHub Actions run ID

        Returns:
            Tuple of (success: bool, details: dict)
        """
        logger.info("💾 Verifying cache save with all three files...")

        try:
            cmd = ["gh", "run", "view", run_id, "--repo", self.repo, "--log"]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logs = result.stdout

            # Look for cache save indicators
            cache_saved = (
                "Cache saved successfully" in logs or "actions/cache/save" in logs
            )

            # Look for file verification
            has_topology = "graph_topology.gpickle" in logs
            has_metadata_db = "metadata_cache.db" in logs
            has_checkpoint_meta = "checkpoint_metadata.json" in logs

            details = {
                "cache_saved": cache_saved,
                "has_topology": has_topology,
                "has_metadata_db": has_metadata_db,
                "has_checkpoint_meta": has_checkpoint_meta,
                "run_id": run_id,
            }

            all_files_present = has_topology and has_metadata_db and has_checkpoint_meta

            if cache_saved and all_files_present:
                logger.info("✅ Cache saved with all three files")
                return True, details
            else:
                logger.error("❌ Cache save incomplete or missing files")
                return False, details

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check logs: {e.stderr}")
            return False, {}

    def verify_downstream_workflows(
        self, collection_run_id: str, timeout: int = 3600
    ) -> dict[str, Any]:
        """
        Verify downstream workflows were triggered and completed.

        Args:
            collection_run_id: Collection workflow run ID
            timeout: Maximum time to wait for each workflow

        Returns:
            Dictionary with status of each downstream workflow
        """
        logger.info("🔗 Verifying downstream workflow chain...")

        results = {
            "repair": {"triggered": False, "success": False, "run_id": None},
            "validation": {"triggered": False, "success": False, "run_id": None},
            "backup": {"triggered": False, "success": False, "run_id": None},
        }

        # Wait for repair workflow to trigger
        logger.info("  Waiting for repair workflow...")
        time.sleep(60)  # Give time for workflow_run trigger

        repair_run_id = self._get_latest_run_id("freesound-data-repair.yml")
        if repair_run_id:
            results["repair"]["triggered"] = True
            results["repair"]["run_id"] = repair_run_id

            success, conclusion, _ = self.monitor_workflow_run(repair_run_id, timeout)
            results["repair"]["success"] = conclusion == "success"

            if results["repair"]["success"]:
                logger.info("  ✅ Repair workflow completed successfully")

                # Wait for validation workflow
                logger.info("  Waiting for validation workflow...")
                time.sleep(60)

                validation_run_id = self._get_latest_run_id(
                    "freesound-validation-visualization.yml"
                )
                if validation_run_id:
                    results["validation"]["triggered"] = True
                    results["validation"]["run_id"] = validation_run_id

                    success, conclusion, _ = self.monitor_workflow_run(
                        validation_run_id, timeout
                    )
                    results["validation"]["success"] = conclusion == "success"

                    if results["validation"]["success"]:
                        logger.info("  ✅ Validation workflow completed successfully")

                        # Wait for backup workflow
                        logger.info("  Waiting for backup workflow...")
                        time.sleep(60)

                        backup_run_id = self._get_latest_run_id("freesound-backup.yml")
                        if backup_run_id:
                            results["backup"]["triggered"] = True
                            results["backup"]["run_id"] = backup_run_id

                            success, conclusion, _ = self.monitor_workflow_run(
                                backup_run_id, timeout
                            )
                            results["backup"]["success"] = conclusion == "success"

                            if results["backup"]["success"]:
                                logger.info(
                                    "  ✅ Backup workflow completed successfully"
                                )

        return results

    def verify_visualization_deployed(self) -> tuple[bool, dict[str, Any]]:
        """
        Verify visualization was generated and deployed to GitHub Pages.

        Returns:
            Tuple of (success: bool, details: dict)
        """
        logger.info("Verifying visualization deployment...")

        try:
            # Check for recent commits to Output directory
            cmd = [
                "gh",
                "api",
                f"/repos/{self.repo}/commits",
                "--jq",
                ".[0] | {sha: .sha, message: .commit.message, date: .commit.author.date}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            commit_data = json.loads(result.stdout)

            # Check if commit message indicates visualization update
            is_viz_commit = "visualization" in commit_data.get("message", "").lower()

            details = {
                "latest_commit": commit_data.get("sha"),
                "commit_message": commit_data.get("message"),
                "commit_date": commit_data.get("date"),
                "is_visualization_commit": is_viz_commit,
            }

            if is_viz_commit:
                logger.info("✅ Visualization deployed to GitHub Pages")
                return True, details
            else:
                logger.warning("⚠️  Latest commit is not a visualization update")
                return False, details

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check commits: {e.stderr}")
            return False, {}

    def generate_report(
        self,
        collection_result: dict[str, Any],
        checkpoint_upload: dict[str, Any],
        cache_save: dict[str, Any],
        downstream_results: dict[str, Any],
        visualization: dict[str, Any],
    ) -> str:
        """
        Generate comprehensive verification report.

        Args:
            collection_result: Collection workflow results
            checkpoint_upload: Checkpoint upload verification
            cache_save: Cache save verification
            downstream_results: Downstream workflow results
            visualization: Visualization deployment verification

        Returns:
            Formatted report as markdown
        """
        report_lines = [
            "# End-to-End Data Flow Verification Report",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Summary",
            "",
        ]

        # Calculate overall success
        all_success = (
            collection_result.get("success", False)
            and checkpoint_upload.get("upload_success", False)
            and cache_save.get("cache_saved", False)
            and downstream_results.get("repair", {}).get("success", False)
            and downstream_results.get("validation", {}).get("success", False)
            and downstream_results.get("backup", {}).get("success", False)
            and visualization.get("is_visualization_commit", False)
        )

        if all_success:
            report_lines.append("✅ **All verification checks passed!**")
        else:
            report_lines.append("❌ **Some verification checks failed**")

        report_lines.extend(
            ["", "## Detailed Results", "", "### 1. Nightly Collection", ""]
        )

        if collection_result.get("success"):
            report_lines.append(f"- ✅ Status: {collection_result.get('conclusion')}")
            report_lines.append(f"- Run ID: `{collection_result.get('run_id')}`")
        else:
            report_lines.append(
                f"- ❌ Status: {collection_result.get('conclusion', 'failed')}"
            )

        report_lines.extend(["", "### 2. Checkpoint Upload", ""])

        if checkpoint_upload.get("upload_success"):
            report_lines.append("- ✅ Upload: Success")
            report_lines.append(
                f"- ✅ Verification: {'Passed' if checkpoint_upload.get('verification_passed') else 'Failed'}"
            )
        else:
            report_lines.append("- ❌ Upload: Failed")

        report_lines.extend(["", "### 3. Cache Save", ""])

        if cache_save.get("cache_saved"):
            report_lines.append("- ✅ Cache: Saved")
            report_lines.append(
                f"- {'✅' if cache_save.get('has_topology') else '❌'} graph_topology.gpickle"
            )
            report_lines.append(
                f"- {'✅' if cache_save.get('has_metadata_db') else '❌'} metadata_cache.db"
            )
            report_lines.append(
                f"- {'✅' if cache_save.get('has_checkpoint_meta') else '❌'} checkpoint_metadata.json"
            )
        else:
            report_lines.append("- ❌ Cache: Not saved")

        report_lines.extend(["", "### 4. Repair Workflow", ""])

        repair = downstream_results.get("repair", {})
        if repair.get("triggered"):
            report_lines.append(
                f"- ✅ Triggered: Yes (Run ID: `{repair.get('run_id')}`)"
            )
            report_lines.append(
                f"- {'✅' if repair.get('success') else '❌'} Success: {repair.get('success')}"
            )
        else:
            report_lines.append("- ❌ Triggered: No")

        report_lines.extend(["", "### 5. Validation Workflow", ""])

        validation = downstream_results.get("validation", {})
        if validation.get("triggered"):
            report_lines.append(
                f"- ✅ Triggered: Yes (Run ID: `{validation.get('run_id')}`)"
            )
            report_lines.append(
                f"- {'✅' if validation.get('success') else '❌'} Success: {validation.get('success')}"
            )
        else:
            report_lines.append("- ❌ Triggered: No")

        report_lines.extend(["", "### 6. Backup Workflow", ""])

        backup = downstream_results.get("backup", {})
        if backup.get("triggered"):
            report_lines.append(
                f"- ✅ Triggered: Yes (Run ID: `{backup.get('run_id')}`)"
            )
            report_lines.append(
                f"- {'✅' if backup.get('success') else '❌'} Success: {backup.get('success')}"
            )
        else:
            report_lines.append("- ❌ Triggered: No")

        report_lines.extend(["", "### 7. Visualization Deployment", ""])

        if visualization.get("is_visualization_commit"):
            report_lines.append("- ✅ Deployed: Yes")
            report_lines.append(
                f"- Commit: `{visualization.get('latest_commit', 'N/A')[:7]}`"
            )
            report_lines.append(f"- Date: {visualization.get('commit_date', 'N/A')}")
        else:
            report_lines.append("- ❌ Deployed: No recent visualization commit found")

        report_lines.extend(["", "## Conclusion", ""])

        if all_success:
            report_lines.extend(
                [
                    "✅ **End-to-end data flow verified successfully!**",
                    "",
                    "All workflow stages completed successfully:",
                    "1. Collection → 2. Upload → 3. Cache → 4. Repair → 5. Validation → 6. Backup → 7. Deployment",
                    "",
                    "The pipeline is functioning correctly and data persists across the entire workflow chain.",
                ]
            )
        else:
            report_lines.extend(
                [
                    "❌ **End-to-end verification failed**",
                    "",
                    "Please review the detailed results above to identify which stage failed.",
                    "Check workflow logs for error details and take corrective action.",
                ]
            )

        return "\n".join(report_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify end-to-end data flow across all workflows"
    )

    parser.add_argument(
        "--trigger-collection",
        action="store_true",
        help="Trigger nightly collection workflow",
    )

    parser.add_argument(
        "--check-status", metavar="RUN_ID", help="Check status of a specific run"
    )

    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="Trigger collection and verify entire workflow chain",
    )

    parser.add_argument(
        "--max-requests",
        type=int,
        default=100,
        help="Maximum API requests for collection (default: 100)",
    )

    parser.add_argument(
        "--discovery-mode",
        choices=["search", "relationships", "mixed"],
        default="search",
        help="Discovery strategy (default: search)",
    )

    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repository (owner/name)",
    )

    parser.add_argument(
        "--output",
        default="e2e_verification_report.md",
        help="Output report file (default: e2e_verification_report.md)",
    )

    args = parser.parse_args()

    if not args.repo:
        logger.error("❌ GITHUB_REPOSITORY not set and --repo not provided")
        sys.exit(1)

    try:
        verifier = WorkflowVerifier(args.repo)

        if args.trigger_collection:
            # Just trigger collection
            success, run_id = verifier.trigger_nightly_collection(
                max_requests=args.max_requests, discovery_mode=args.discovery_mode
            )

            if success:
                logger.info(f"✅ Collection triggered: Run ID {run_id}")
                logger.info(
                    f"Monitor with: python {sys.argv[0]} --check-status {run_id}"
                )
                sys.exit(0)
            else:
                logger.error("❌ Failed to trigger collection")
                sys.exit(1)

        elif args.check_status:
            # Check status of specific run
            success, conclusion, details = verifier.monitor_workflow_run(
                args.check_status
            )

            if success:
                logger.info(f"✅ Workflow completed: {conclusion}")
                logger.info(f"Details: {json.dumps(details, indent=2)}")
                sys.exit(0 if conclusion == "success" else 1)
            else:
                logger.error("❌ Workflow monitoring failed")
                sys.exit(1)

        elif args.verify_all:
            # Full end-to-end verification
            logger.info("🚀 Starting full end-to-end verification...")
            logger.info(f"   Max requests: {args.max_requests}")
            logger.info(f"   Discovery mode: {args.discovery_mode}")
            logger.info("")

            # Step 1: Trigger collection
            success, run_id = verifier.trigger_nightly_collection(
                max_requests=args.max_requests, discovery_mode=args.discovery_mode
            )

            if not success:
                logger.error("❌ Failed to trigger collection")
                sys.exit(1)

            # Step 2: Monitor collection
            success, conclusion, details = verifier.monitor_workflow_run(run_id)
            collection_result = {
                "success": (conclusion == "success"),
                "conclusion": conclusion,
                "run_id": run_id,
                "details": details,
            }

            # Step 3: Verify checkpoint upload
            checkpoint_upload = {}
            if collection_result["success"]:
                success, checkpoint_upload = verifier.verify_checkpoint_upload(run_id)

            # Step 4: Verify cache save
            cache_save = {}
            if collection_result["success"]:
                success, cache_save = verifier.verify_cache_save(run_id)

            # Step 5: Verify downstream workflows
            downstream_results = {}
            if collection_result["success"]:
                downstream_results = verifier.verify_downstream_workflows(run_id)

            # Step 6: Verify visualization deployment
            visualization = {}
            if downstream_results.get("validation", {}).get("success"):
                success, visualization = verifier.verify_visualization_deployed()

            # Generate report
            report = verifier.generate_report(
                collection_result=collection_result,
                checkpoint_upload=checkpoint_upload,
                cache_save=cache_save,
                downstream_results=downstream_results,
                visualization=visualization,
            )

            # Save report
            output_path = Path(args.output)
            output_path.write_text(report)
            logger.info(f"📄 Report saved to: {output_path}")

            # Print report
            print("\n" + "=" * 80)
            print(report)
            print("=" * 80 + "\n")

            # Exit with appropriate code
            all_success = (
                collection_result.get("success", False)
                and checkpoint_upload.get("upload_success", False)
                and cache_save.get("cache_saved", False)
                and downstream_results.get("repair", {}).get("success", False)
                and downstream_results.get("validation", {}).get("success", False)
                and downstream_results.get("backup", {}).get("success", False)
            )

            sys.exit(0 if all_success else 1)

        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
