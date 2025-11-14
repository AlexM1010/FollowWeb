"""
Entry point for running analysis_tools as a module.

Usage:
    python -m analysis_tools [options]
    
Analysis commands:
    python -m analysis_tools                    # Run full analysis
    python -m analysis_tools --optimize         # Run optimization analysis
    
Cleanup commands:
    python -m analysis_tools --cleanup-analyze  # Analyze repository for cleanup
    python -m analysis_tools --cleanup-execute  # Execute cleanup phases
    python -m analysis_tools --validate-cleanup # Validate cleanup environment
    python -m analysis_tools --cleanup-rollback # Rollback cleanup phase
"""

import sys
import os

from .analyzer import AnalysisOrchestrator

# Import EmojiFormatter from FollowWeb package if available
try:
    from FollowWeb.FollowWeb_Visualizor.output.formatters import EmojiFormatter
    
    # Auto-detect Windows and set appropriate fallback level
    if os.name == 'nt':
        # On Windows, use simple ASCII fallback to avoid encoding issues
        EmojiFormatter.set_fallback_level("simple")
except ImportError:
    # Fallback if FollowWeb package not available
    class EmojiFormatter:
        """Minimal fallback emoji formatter."""
        
        @classmethod
        def format(cls, emoji_key: str, message: str) -> str:
            """Format message without emojis."""
            return message
        
        @classmethod
        def safe_print(cls, emoji_key: str, message: str) -> None:
            """Print message without emojis."""
            print(message)


def main():
    """Main entry point for the analysis orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run code analysis and repository cleanup operations"
    )
    
    # Analysis commands
    analysis_group = parser.add_argument_group("analysis commands")
    analysis_group.add_argument(
        "--optimize", action="store_true", help="Run optimization analysis"
    )
    
    # Cleanup commands
    cleanup_group = parser.add_argument_group("cleanup commands")
    cleanup_group.add_argument(
        "--cleanup-analyze",
        action="store_true",
        help="Analyze repository structure and generate cleanup recommendations",
    )
    cleanup_group.add_argument(
        "--cleanup-execute",
        action="store_true",
        help="Execute cleanup phases (use with --phase to specify phase)",
    )
    cleanup_group.add_argument(
        "--validate-cleanup",
        action="store_true",
        help="Validate cleanup environment and prerequisites",
    )
    cleanup_group.add_argument(
        "--cleanup-rollback",
        action="store_true",
        help="Rollback a cleanup phase (use with --phase to specify phase)",
    )
    
    # Cleanup options
    cleanup_group.add_argument(
        "--phase",
        type=str,
        help="Specific cleanup phase to execute or rollback",
    )
    cleanup_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate cleanup operations without making changes",
    )
    
    # Legacy validation options (kept for backwards compatibility)
    parser.add_argument(
        "--validate-phase",
        type=str,
        choices=["dependencies", "ai_artifacts", "test_optimization"],
        help="Validate specific cleanup phase (legacy)",
    )
    
    # Common options
    parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = AnalysisOrchestrator(project_root=args.project_root)

    try:
        # Cleanup commands - delegate to cleanup CLI
        if args.cleanup_analyze:
            from .cleanup.cli import analyze_command
            return analyze_command(args)
            
        elif args.cleanup_execute:
            from .cleanup.cli import execute_command
            return execute_command(args)
            
        elif args.cleanup_rollback:
            from .cleanup.cli import rollback_command
            return rollback_command(args)
            
        # Analysis commands
        elif args.optimize:
            print("Running optimization analysis...")
            orchestrator.run_optimization_analysis()
        elif args.validate_cleanup:
            print("Validating cleanup environment...")
            orchestrator.validate_cleanup_environment()
        elif args.validate_phase:
            print(f"Validating cleanup phase: {args.validate_phase}")
            orchestrator.validate_cleanup_phase(args.validate_phase)
        else:
            print("Running full analysis...")
            orchestrator.run_full_analysis()

        EmojiFormatter.safe_print("success", "Analysis completed successfully!")
        return 0

    except Exception as e:
        EmojiFormatter.safe_print("error", f"Operation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
