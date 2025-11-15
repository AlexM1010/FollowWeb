"""Validate GitHub Actions workflow files using actionlint.

Actionlint is a comprehensive static checker for GitHub Actions workflows that:
- Validates YAML syntax and structure
- Checks GitHub Actions-specific semantics (keys, inputs/outputs, reusable workflows)
- Detects security risks and best practice violations
- Integrates ShellCheck to analyze shell scripts in 'run:' steps
- Understands GitHub Actions expressions (${{ }}) to avoid false positives
- Catches workflow-specific errors beyond shell scripting issues

This provides complete workflow validation matching CI behavior.
"""
import sys
import subprocess
import platform
from pathlib import Path
import urllib.request
import tarfile
import zipfile
import os

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def check_actionlint_available():
    """Check if actionlint binary is available."""
    try:
        result = subprocess.run(
            ['actionlint', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def download_actionlint():
    """Download actionlint binary for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Map platform names
    if system == 'darwin':
        system = 'darwin'
    elif system == 'windows':
        system = 'windows'
    else:
        system = 'linux'
    
    # Map architecture names
    if machine in ['x86_64', 'amd64']:
        arch = 'amd64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'arm64'
    elif machine in ['i386', 'i686']:
        arch = '386'
    else:
        arch = 'amd64'
    
    # Construct download URL
    version = '1.7.1'
    if system == 'windows':
        filename = f'actionlint_{version}_windows_{arch}.zip'
        binary_name = 'actionlint.exe'
    else:
        filename = f'actionlint_{version}_{system}_{arch}.tar.gz'
        binary_name = 'actionlint'
    
    url = f'https://github.com/rhysd/actionlint/releases/download/v{version}/{filename}'
    
    print(f"Downloading actionlint from {url}...")
    
    try:
        # Download file
        download_path = Path(filename)
        urllib.request.urlretrieve(url, download_path)
        
        # Extract binary
        if system == 'windows':
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extract(binary_name)
        else:
            with tarfile.open(download_path, 'r:gz') as tar_ref:
                tar_ref.extract(binary_name)
        
        # Make executable on Unix-like systems
        if system != 'windows':
            os.chmod(binary_name, 0o755)
        
        # Clean up download
        download_path.unlink()
        
        print(f"✓ Downloaded actionlint to ./{binary_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to download actionlint: {e}")
        return False


def run_actionlint(workflow_files):
    """Run actionlint on workflow files."""
    # Determine actionlint binary name
    actionlint_cmd = 'actionlint.exe' if platform.system() == 'Windows' else './actionlint'
    if check_actionlint_available():
        actionlint_cmd = 'actionlint'  # Use system-installed version
    
    try:
        # Run actionlint on all workflow files
        cmd = [actionlint_cmd, '-format', '{{range $err := .}}{{$err.Filepath}}:{{$err.Line}}:{{$err.Column}}: {{$err.Kind}}: {{$err.Message}} [{{$err.Code}}]{{"\n"}}{{end}}']
        cmd.extend([str(f) for f in workflow_files])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        errors = []
        warnings = []
        notes = []
        
        if result.returncode != 0 or result.stdout:
            # Parse actionlint output
            for line in result.stdout.strip().split('\n'):
                if line:
                    # Categorize by severity
                    if ': error:' in line:
                        errors.append(line)
                    elif ': warning:' in line or ': style:' in line:
                        warnings.append(line)
                    elif ': note:' in line:
                        notes.append(line)
                    else:
                        # Default to warning for shellcheck issues
                        warnings.append(line)
        
        return errors, warnings, notes
        
    except subprocess.TimeoutExpired:
        return [f"actionlint timeout after 30 seconds"], [], []
    except Exception as e:
        return [f"actionlint error: {e}"], [], []


def validate_workflows():
    """Validate all GitHub Actions workflow files using actionlint."""
    workflows_dir = Path('.github/workflows')
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    if not workflow_files:
        print("No workflow files found")
        return False
    
    # Check if actionlint is available, download if needed
    if not check_actionlint_available():
        print("⚠️  actionlint not found - attempting to download...")
        if not download_actionlint():
            print("✗ Failed to download actionlint")
            print("  Install manually from: https://github.com/rhysd/actionlint")
            return False
    
    print(f"Validating {len(workflow_files)} workflow files with actionlint...\n")
    
    # Run actionlint on all workflows
    errors, warnings, notes = run_actionlint(workflow_files)
    
    # Count valid workflows
    valid_count = len(workflow_files)
    if errors:
        failed_files = set()
        for error in errors:
            if ':' in error:
                failed_files.add(error.split(':')[0])
        valid_count = len(workflow_files) - len(failed_files)
    
    # Print individual workflow status
    for workflow_file in workflow_files:
        workflow_name = workflow_file.name
        has_error = any(workflow_name in e for e in errors)
        if has_error:
            print(f"✗ {workflow_name}")
        else:
            print(f"✓ {workflow_name}")
    
    print(f"\nValidated {valid_count}/{len(workflow_files)} workflows")
    
    # Report errors
    if errors:
        print(f"\n❌ Errors ({len(errors)} found):")
        for error in errors:
            print(f"  {error}")
    
    # Report warnings
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)} found):")
        for warning in warnings:
            print(f"  {warning}")
    
    # Report notes (informational only, don't fail)
    if notes:
        print(f"\n💡 Notes ({len(notes)} found):")
        for note in notes:
            print(f"  {note}")
    
    # Only fail on errors and warnings, not notes
    return len(errors) == 0 and len(warnings) == 0


if __name__ == '__main__':
    success = validate_workflows()
    sys.exit(0 if success else 1)
