"""
CLI entry point for Pattern Detector with reviewdog support.

Usage:
    python -m analysis_tools.pattern_detector --format=reviewdog --diff-only
"""

import sys
from .cli_reviewdog import create_cli_parser, run_pattern_detector


def main():
    """Main entry point for Pattern Detector CLI."""
    parser = create_cli_parser("Pattern Detector")
    args = parser.parse_args()
    
    return run_pattern_detector(
        files=args.files if args.files else None,
        format_type=args.format,
        output_file=args.output,
        diff_only=args.diff_only
    )


if __name__ == "__main__":
    sys.exit(main())
