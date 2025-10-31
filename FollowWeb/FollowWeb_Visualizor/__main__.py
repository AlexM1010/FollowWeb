"""
Entry point for running FollowWeb_Visualizor as a module.

This allows the package to be executed with:
    python -m FollowWeb_Visualizor config.json
"""

import os
import sys

try:
    from FollowWeb_Visualizor.main import main
except ImportError:
    # Fallback for development - main module not yet implemented in modular structure
    def main():
        print("FollowWeb_Visualizor main module not yet implemented in modular structure")
        return 1

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    sys.exit(main())
