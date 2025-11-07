"""
Entry point for running analysis_tools as a module.

Usage:
    python -m analysis_tools [options]
"""

import sys

from .analyzer import AnalysisOrchestrator


def main():
    """Main entry point for the analysis orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="Run code analysis on the project")
    parser.add_argument(
        "--optimize", action="store_true", help="Run optimization analysis"
    )
    parser.add_argument(
        "--validate-cleanup", action="store_true", help="Validate cleanup environment"
    )
    parser.add_argument(
        "--validate-phase",
        type=str,
        choices=["dependencies", "ai_artifacts", "test_optimization"],
        help="Validate specific cleanup phase",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = AnalysisOrchestrator(project_root=args.project_root)

    try:
        if args.optimize:
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

        print("\n✅ Analysis completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
