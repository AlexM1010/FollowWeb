#!/usr/bin/env python3
"""
Wrapper script for detect_milestone.py in scripts/analysis/
This maintains backward compatibility with the GitHub Actions workflow.
"""
import sys
from pathlib import Path

# Load environment variables from .env file (optional, for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available (e.g., in CI/CD), skip loading .env file
    pass

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts" / "analysis"
sys.path.insert(0, str(scripts_dir))

# Import and run the actual script
if __name__ == '__main__':
    # Import the main function from the actual script
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "detect_milestone",
        scripts_dir / "detect_milestone.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Run the main function
    sys.exit(module.main())
