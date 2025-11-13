"""
CLI entry point for AI Language Scanner with reviewdog support.

Usage:
    python -m analysis_tools.ai_language_scanner --format=reviewdog --diff-only
"""

import sys
from .cli_reviewdog import create_cli_parser, run_ai_language_scanner


def main():
    """Main entry point for AI Language Scanner CLI."""
    parser = create_cli_parser("AI Language Scanner")
    args = parser.parse_args()
    
    return run_ai_language_scanner(
        files=args.files if args.files else None,
        format_type=args.format,
        output_file=args.output,
        diff_only=args.diff_only
    )


if __name__ == "__main__":
    sys.exit(main())
