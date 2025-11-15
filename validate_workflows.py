"""Validate workflow YAML files and embedded shell scripts."""
import sys
import subprocess
import tempfile
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

# Check if shellcheck binary is available (installed via shellcheck-py)
def check_shellcheck_available():
    """Check if shellcheck binary is available."""
    try:
        result = subprocess.run(
            ['shellcheck', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

SHELLCHECK_AVAILABLE = check_shellcheck_available()


def extract_shell_scripts(workflow_data, workflow_name):
    """Extract shell scripts from workflow YAML with shell type detection."""
    scripts = []
    
    def traverse(obj, path="", job_shell=None):
        """Recursively traverse YAML structure to find 'run' keys.
        
        Args:
            obj: Current YAML object being traversed
            path: Current path in the YAML structure
            job_shell: Default shell specified at job level
        """
        if isinstance(obj, dict):
            # Check for job-level default shell
            current_shell = job_shell
            if 'defaults' in obj and isinstance(obj['defaults'], dict):
                if 'run' in obj['defaults'] and isinstance(obj['defaults']['run'], dict):
                    current_shell = obj['defaults']['run'].get('shell', job_shell)
            
            # Check for step-level shell override
            step_shell = obj.get('shell', current_shell)
            
            for key, value in obj.items():
                if key == 'run' and isinstance(value, str):
                    # Check if it's a multi-line script (likely bash)
                    if '\n' in value or '|' in str(value):
                        scripts.append({
                            'content': value,
                            'path': f"{path}.{key}" if path else key,
                            'workflow': workflow_name,
                            'shell': step_shell or 'bash'  # Default to bash if not specified
                        })
                traverse(value, f"{path}.{key}" if path else key, current_shell)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                traverse(item, f"{path}[{i}]", job_shell)
    
    traverse(workflow_data)
    return scripts


def run_shellcheck(script_content, workflow_name, script_path, shell_type='bash'):
    """Run shellcheck on a shell script.
    
    Args:
        script_content: The shell script content to check
        workflow_name: Name of the workflow file
        script_path: Path within the workflow structure
        shell_type: Shell type (bash, sh, dash, ksh, etc.)
    """
    if not SHELLCHECK_AVAILABLE:
        return {'errors': [], 'warnings': [], 'notes': []}
    
    # Normalize line endings (remove carriage returns)
    script_content = script_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Skip scripts with GitHub Actions expressions (shellcheck doesn't understand them)
    if '${{' in script_content or '}}' in script_content:
        return {'errors': [], 'warnings': [], 'notes': []}
    
    # Create a temporary file with the script content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, encoding='utf-8', newline='\n') as f:
        f.write(script_content)
        temp_file = f.name
    
    try:
        # Determine shell flag based on shell type
        # Extract base shell name (e.g., 'bash' from 'bash -e' or '/bin/bash')
        base_shell = shell_type.split()[0].split('/')[-1] if shell_type else 'bash'
        
        # Map common shell types to shellcheck shell names
        shell_map = {
            'bash': 'bash',
            'sh': 'sh',
            'dash': 'dash',
            'ksh': 'ksh',
            'powershell': None,  # Skip PowerShell scripts
            'pwsh': None,        # Skip PowerShell Core scripts
            'python': None,      # Skip Python scripts
            'cmd': None,         # Skip Windows cmd scripts
        }
        
        shellcheck_shell = shell_map.get(base_shell, 'bash')
        
        # Skip non-POSIX shells
        if shellcheck_shell is None:
            return {'errors': [], 'warnings': [], 'notes': []}
        
        # Use shellcheck binary (installed via shellcheck-py package)
        # Exclude common GitHub Actions workflow patterns:
        # 
        # CRITICAL EXCLUSIONS (CI-specific):
        # SC2148 - missing shebang (GitHub Actions doesn't require shebangs)
        # SC1091 - not following sourced files (external files not available)
        # SC2164 - cd without error handling (CI stops on any failure)
        # 
        # Match actionlint's shellcheck configuration (used in CI)
        # This ensures local validation matches CI validation
        cmd = ['shellcheck', '-s', shellcheck_shell, '-f', 'gcc', '-e', 'SC2148,SC1091,SC2164', temp_file]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Parse shellcheck output and format it
            errors = []
            warnings = []
            notes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    # Replace temp filename with workflow context
                    line = line.replace(temp_file, f"{workflow_name}:{script_path}")
                    # Categorize by severity
                    if ': error:' in line:
                        errors.append(line)
                    elif ': warning:' in line:
                        warnings.append(line)
                    elif ': note:' in line:
                        notes.append(line)
                    else:
                        errors.append(line)  # Default to error if unknown
            return {'errors': errors, 'warnings': warnings, 'notes': notes}
        return {'errors': [], 'warnings': [], 'notes': []}
    except subprocess.TimeoutExpired:
        return {'errors': [f"{workflow_name}:{script_path}: shellcheck timeout"], 'warnings': [], 'notes': []}
    except Exception as e:
        return {'errors': [f"{workflow_name}:{script_path}: shellcheck error: {e}"], 'warnings': [], 'notes': []}
    finally:
        Path(temp_file).unlink(missing_ok=True)


def validate_workflows():
    """Validate all workflow YAML files and embedded shell scripts."""
    workflows_dir = Path('.github/workflows')
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    if not workflow_files:
        print("No workflow files found")
        return False
    
    yaml_errors = []
    shellcheck_errors = []
    shellcheck_warnings = []
    shellcheck_notes = []
    valid_count = 0
    
    # Check if shellcheck is available
    if not SHELLCHECK_AVAILABLE:
        print("⚠️  shellcheck-py not found - skipping shell script validation")
        print("   Install with: pip install shellcheck-py")
        print()
    
    # Validate YAML syntax
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = yaml.safe_load(f)
            
            valid_count += 1
            print(f"✓ {workflow_file.name}")
            
            # Extract and validate shell scripts if shellcheck is available
            if SHELLCHECK_AVAILABLE and workflow_data:
                scripts = extract_shell_scripts(workflow_data, workflow_file.name)
                for script in scripts:
                    results = run_shellcheck(
                        script['content'], 
                        script['workflow'], 
                        script['path'],
                        script.get('shell', 'bash')
                    )
                    if isinstance(results, dict):
                        if results.get('errors'):
                            shellcheck_errors.extend(results['errors'])
                        if results.get('warnings'):
                            shellcheck_warnings.extend(results['warnings'])
                        if results.get('notes'):
                            shellcheck_notes.extend(results['notes'])
                    else:
                        # Fallback for old format (shouldn't happen)
                        shellcheck_errors.extend(results if results else [])
                        
        except yaml.YAMLError as e:
            yaml_errors.append(f"✗ {workflow_file.name}: {e}")
        except Exception as e:
            yaml_errors.append(f"✗ {workflow_file.name}: {e}")
    
    print(f"\nValidated {valid_count}/{len(workflow_files)} workflows")
    
    # Report YAML errors
    if yaml_errors:
        print("\n❌ YAML Syntax Errors:")
        for error in yaml_errors:
            print(f"  {error}")
    
    # Report shellcheck errors
    if shellcheck_errors:
        print(f"\n❌ Shellcheck Errors ({len(shellcheck_errors)} found):")
        for error in shellcheck_errors:
            print(f"  {error}")
    
    # Report shellcheck warnings
    if shellcheck_warnings:
        print(f"\n⚠️  Shellcheck Warnings ({len(shellcheck_warnings)} found):")
        for warning in shellcheck_warnings:
            print(f"  {warning}")
    
    # Report shellcheck notes (informational only, don't fail)
    if shellcheck_notes:
        print(f"\n💡 Shellcheck Notes ({len(shellcheck_notes)} found):")
        for note in shellcheck_notes:
            print(f"  {note}")
    
    # Only fail on errors and warnings, not notes
    return len(yaml_errors) == 0 and len(shellcheck_errors) == 0 and len(shellcheck_warnings) == 0


if __name__ == '__main__':
    success = validate_workflows()
    sys.exit(0 if success else 1)
