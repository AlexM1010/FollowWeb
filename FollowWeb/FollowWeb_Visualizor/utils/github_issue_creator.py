"""
GitHub issue creation utilities for critical failures.

This module provides functionality to create GitHub issues with diagnostic
information when critical failures occur in CI/CD workflows.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class GitHubIssueCreator:
    """
    Creates GitHub issues for critical failures with diagnostic information.

    Issues include:
    - Error message and context
    - Workflow name and run ID
    - Checkpoint status
    - Logs and diagnostic data
    - Auto-close on successful recovery
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize GitHub issue creator.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def create_failure_issue(
        self,
        title: str,
        error_message: str,
        workflow_name: str,
        run_id: str,
        checkpoint_status: dict[str, Any],
        logs: Optional[str] = None,
        additional_info: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        Create a GitHub issue for a critical failure.

        Args:
            title: Issue title
            error_message: Error description
            workflow_name: Name of the workflow that failed
            run_id: GitHub Actions run ID
            checkpoint_status: Status of checkpoint/data preservation
            logs: Optional log content to include
            additional_info: Optional additional diagnostic information

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Build issue body
            body = self._build_issue_body(
                error_message=error_message,
                workflow_name=workflow_name,
                run_id=run_id,
                checkpoint_status=checkpoint_status,
                logs=logs,
                additional_info=additional_info,
            )

            # Get GitHub token from environment
            github_token = os.environ.get("GITHUB_TOKEN")
            if not github_token:
                self.logger.warning("GITHUB_TOKEN not found, cannot create issue")
                return False, "GITHUB_TOKEN not found"

            # Get repository info from environment
            repo = os.environ.get("GITHUB_REPOSITORY")
            if not repo:
                self.logger.warning("GITHUB_REPOSITORY not found, cannot create issue")
                return False, "GITHUB_REPOSITORY not found"

            # Create issue using GitHub CLI or API
            # For now, save issue data to file for workflow to create
            issue_data = {
                "title": title,
                "body": body,
                "labels": ["critical-failure", "automated"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Save to file for workflow to process
            issue_file = Path("data/freesound_library/pending_issue.json")
            issue_file.parent.mkdir(parents=True, exist_ok=True)

            with open(issue_file, "w") as f:
                json.dump(issue_data, f, indent=2)

            self.logger.info(f"✅ Issue data saved to {issue_file}")
            return True, f"Issue data saved to {issue_file}"

        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}")
            return False, f"Failed to create issue: {e}"

    def _build_issue_body(
        self,
        error_message: str,
        workflow_name: str,
        run_id: str,
        checkpoint_status: dict[str, Any],
        logs: Optional[str] = None,
        additional_info: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Build the issue body with diagnostic information.

        Args:
            error_message: Error description
            workflow_name: Name of the workflow that failed
            run_id: GitHub Actions run ID
            checkpoint_status: Status of checkpoint/data preservation
            logs: Optional log content
            additional_info: Optional additional diagnostic information

        Returns:
            Formatted issue body as markdown
        """
        body_parts = [
            "## Critical Failure Report",
            "",
            f"**Workflow:** {workflow_name}",
            f"**Run ID:** {run_id}",
            f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Error Details",
            "",
            f"```\n{error_message}\n```",
            "",
            "## Checkpoint Status",
            "",
        ]

        # Add checkpoint status
        for key, value in checkpoint_status.items():
            body_parts.append(f"- **{key}:** {value}")

        body_parts.append("")

        # Add additional info if provided
        if additional_info:
            body_parts.append("## Additional Information")
            body_parts.append("")
            for key, value in additional_info.items():
                body_parts.append(f"- **{key}:** {value}")
            body_parts.append("")

        # Add logs if provided
        if logs:
            body_parts.append("## Logs")
            body_parts.append("")
            body_parts.append("<details>")
            body_parts.append("<summary>Click to expand logs</summary>")
            body_parts.append("")
            body_parts.append(f"```\n{logs}\n```")
            body_parts.append("")
            body_parts.append("</details>")
            body_parts.append("")

        # Add recovery instructions
        body_parts.extend(
            [
                "## Recovery Instructions",
                "",
                "1. Check the checkpoint status above to determine if data was preserved",
                "2. Review the error message and logs for root cause",
                "3. If data was saved to permanent storage, it can be recovered",
                "4. If data was only saved to cache, manual backup may be needed",
                "5. Fix the underlying issue and re-run the workflow",
                "",
                "This issue will auto-close on successful recovery.",
            ]
        )

        return "\n".join(body_parts)

    def close_recovery_issue(self, issue_number: int) -> tuple[bool, str]:
        """
        Close an issue after successful recovery.

        Args:
            issue_number: GitHub issue number to close

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Save close request to file for workflow to process
            close_data = {
                "issue_number": issue_number,
                "comment": "✅ Workflow recovered successfully. Auto-closing issue.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            close_file = Path("data/freesound_library/close_issue.json")
            close_file.parent.mkdir(parents=True, exist_ok=True)

            with open(close_file, "w") as f:
                json.dump(close_data, f, indent=2)

            self.logger.info(f"✅ Issue close request saved for issue #{issue_number}")
            return True, f"Close request saved for issue #{issue_number}"

        except Exception as e:
            self.logger.error(f"Failed to close issue: {e}")
            return False, f"Failed to close issue: {e}"
