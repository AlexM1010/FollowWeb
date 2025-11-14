"""
Entry point for running cleanup module directly.

Usage:
    python -m analysis_tools.cleanup [command] [options]
    
Commands:
    analyze              Analyze repository for cleanup opportunities
    execute              Execute cleanup phases
    rollback             Rollback a cleanup phase
    validate             Validate cleanup environment
    list-phases          List all available cleanup phases
    create-config        Create default configuration file
    
Examples:
    python -m analysis_tools.cleanup analyze
    python -m analysis_tools.cleanup execute --all --dry-run
    python -m analysis_tools.cleanup rollback --phase root_cleanup
    python -m analysis_tools.cleanup validate
"""

import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
