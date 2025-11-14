# GitHub Actions Workflow Troubleshooting Guide

This guide documents common pipeline issues and their solutions, based on real-world debugging experiences.

## Table of Contents

1. [Workflow File Syntax Errors](#workflow-file-syntax-errors)
2. [Path Reference Errors](#path-reference-errors)
3. [Duplicate Job Definitions](#duplicate-job-definitions)
4. [Heredoc Syntax Issues](#heredoc-syntax-issues)
5. [Pre-Commit Hook Issues](#pre-commit-hook-issues)

## Workflow File Syntax Errors

### Symptom
Workflow shows "workflow file issue" error in GitHub Actions UI.

### Diagnosis
```bash
# Validate YAML syntax locally
python -c "import yaml; yaml.safe_load(open('.github/workflows/WORKFLOW.yml', 'r', encoding='utf-8').read())"
```

### Common Causes

#### 1. Heredoc Syntax in YAML

**Problem:** Using bash heredocs (`<< 'EOF'`) in workflow `run:` blocks causes YAML parser errors because the heredoc content starts at column 0, breaking YAML indentation rules.

**Example of Broken Code:**
```yaml
- name: Run Python script
  run: |
    python3 << 'EOF'
import json
# This breaks YAML because 'import json' is at column 0
EOF
```

**Solution:** Use separate Python script files or `python3 -c` with proper quoting:

```yaml
# Option 1: Separate script file (RECOMMENDED)
- name: Run Python script
  run: |
    python3 .github/scripts/my_script.py

# Option 2: Inline with python -c (for short scripts)
- name: Run Python script
  run: |
    python3 -c '
import json
print("This works because it is inside the YAML string")
'
```

**Real-World Example:**
- **File:** `.github/workflows/freesound-data-remediation.yml`
- **Issue:** Heredoc syntax caused YAML parser to fail at line 221
- **Fix:** Created separate scripts:
  - `.github/scripts/regenerate_checkpoint_metadata.py`
  - `.github/scripts/rebuild_metadata_cache.py`

#### 2. Unclosed Quotes or Brackets

**Problem:** Missing closing quotes or brackets in multi-line strings.

**Diagnosis:**
```bash
# Check for unclosed quotes
grep -n "'" .github/workflows/WORKFLOW.yml | less
```

**Solution:** Ensure all quotes and brackets are properly closed.

## Path Reference Errors

### Symptom
Error: `No such file or directory: ci_helpers.py`

### Diagnosis
Check the working directory context and path used.

### Root Cause
The path to helper scripts depends on the working directory:
- From root: `.github/scripts/ci_helpers.py`
- From FollowWeb: `../.github/scripts/ci_helpers.py`

### Solution

**Correct Pattern:**
```yaml
# Job with working-directory: FollowWeb
jobs:
  my-job:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: FollowWeb
    steps:
      - name: My step
        run: |
          # Use relative path from FollowWeb directory
          python ../.github/scripts/ci_helpers.py success "Message"
```

```yaml
# Job without working-directory (runs from root)
jobs:
  my-job:
    runs-on: ubuntu-latest
    steps:
      - name: My step
        run: |
          # Use path from root directory
          python .github/scripts/ci_helpers.py success "Message"
```

### Validation
```bash
# Run validation script
python .github/scripts/validate_ci_helpers_path.py
```

**Real-World Example:**
- **File:** `.github/workflows/release.yml`
- **Issue:** Used `ci_helpers.py` instead of `../.github/scripts/ci_helpers.py`
- **Fix:** Updated to use correct relative path based on working directory

## Duplicate Job Definitions

### Symptom
Error: `Duplicate job name: job-name`

### Diagnosis
```bash
# Find duplicate job names
grep -r "^  [a-z-]*:" .github/workflows/*.yml | sort | uniq -d
```

### Root Cause
Two jobs in the same workflow file have the same name.

### Solution
1. Rename one of the jobs to be unique
2. Check for copy-paste errors
3. Ensure job names are descriptive and unique

### Prevention
- Use descriptive job names that reflect their purpose
- Review workflow files before committing
- Use pre-commit hooks to catch issues early

## Heredoc Syntax Issues

### Detailed Example

**Problem Code:**
```yaml
- name: Regenerate metadata
  run: |
    if [ "$condition" = "true" ]; then
      python3 << 'EOF'
import json
import pickle
# ... Python code ...
EOF
    fi
```

**Why It Fails:**
1. YAML parser expects all content in `run: |` block to be indented consistently
2. Heredoc content (`import json`) starts at column 0
3. YAML parser tries to parse `import json` as a YAML key
4. Error: "could not find expected ':'"

**Solution 1: Separate Script File (Recommended)**
```yaml
- name: Regenerate metadata
  run: |
    if [ "$condition" = "true" ]; then
      python3 .github/scripts/regenerate_metadata.py
    fi
```

**Solution 2: Python -c with Proper Quoting**
```yaml
- name: Regenerate metadata
  run: |
    if [ "$condition" = "true" ]; then
      python3 -c '
import json
import pickle
# Use double quotes inside for strings
print("This works")
'
    fi
```

**Solution 3: Indented Heredoc (Less Common)**
```yaml
- name: Regenerate metadata
  run: |
    if [ "$condition" = "true" ]; then
      python3 <<-'EOF'
      import json
      import pickle
      # Content must be indented
      EOF
    fi
```

## Pre-Commit Hook Issues

### Symptom
Pre-commit hooks fail or don't run.

### Common Issues

#### 1. Hooks Not Installed
```bash
# Install hooks
pre-commit install
```

#### 2. Hook Fails on Commit
```bash
# Run hooks manually to see full output
pre-commit run --all-files

# Run specific hook
pre-commit run actionlint --all-files
```

#### 3. Actionlint Not Found
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install --install-hooks
```

## Systematic Debugging Approach

When facing a pipeline failure, follow this systematic approach:

### 1. Identify the Failing Job
- Check GitHub Actions UI for red X
- Note the job name and step that failed

### 2. Review the Error Message
- Read the full error output
- Look for specific file names and line numbers
- Check for stack traces

### 3. Reproduce Locally
```bash
# For YAML syntax errors
python -c "import yaml; yaml.safe_load(open('.github/workflows/WORKFLOW.yml'))"

# For workflow validation
actionlint .github/workflows/WORKFLOW.yml

# For code quality issues
cd FollowWeb
ruff check FollowWeb_Visualizor tests
mypy FollowWeb_Visualizor
```

### 4. Fix the Issue
- Make the necessary changes
- Test locally before pushing
- Use pre-commit hooks to catch issues early

### 5. Verify the Fix
- Push changes and monitor the workflow
- Check that all jobs pass
- Review the workflow summary

## Prevention Strategies

### 1. Use Pre-Commit Hooks
```bash
pip install pre-commit
pre-commit install
```

### 2. Validate Before Pushing
```bash
# Validate workflows
actionlint .github/workflows/*.yml

# Validate Python code
cd FollowWeb
ruff check FollowWeb_Visualizor tests
ruff format --check FollowWeb_Visualizor tests
mypy FollowWeb_Visualizor
```

### 3. Test Workflows Manually
- Use `workflow_dispatch` triggers for manual testing
- Test with different input parameters
- Verify all branches and conditions

### 4. Keep Documentation Updated
- Document workflow changes in `.github/workflows/README.md`
- Update troubleshooting guide with new issues
- Share knowledge with team members

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Actionlint Documentation](https://github.com/rhysd/actionlint)
- [Pre-commit Documentation](https://pre-commit.com/)
- [YAML Specification](https://yaml.org/spec/)

## Getting Help

If you encounter an issue not covered in this guide:

1. Check GitHub Actions logs for detailed error messages
2. Search GitHub Issues for similar problems
3. Review recent workflow changes in git history
4. Ask team members who have worked on workflows
5. Create a detailed issue with:
   - Workflow file name
   - Error message
   - Steps to reproduce
   - Expected vs actual behavior
