"""
Entry point for running FollowWeb_Visualizor as a module.

This allows the package to be executed with:
    python -m FollowWeb_Visualizor config.json
"""

import os
import sys

from FollowWeb_Visualizor.main import main

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    sys.exit(main())
