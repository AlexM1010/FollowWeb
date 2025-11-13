"""
CLI entry point for Cross-Platform Analyzer with reviewdog support.

Usage:
    python -m analysis_tools.cross_platform_analyzer --format=reviewdog --diff-only
"""

import sys
from .cli_reviewdog import create_cli_parser, run_cross_platform_analyzer


def main():
    """Main entry point for Cross-Platform Analyzer CLI."""
    parser = create_cli_parser("Cross-Platform Analyzer")
    args = parser.parse_args()
    
    return run_cross_platform_analyzer(
        files=args.files if args.files else None,
        format_type=args.format,
        output_file=args.output,
        diff_only=args.diff_only
    )


if __name__ == "__main__":
    sys.exit(main())
