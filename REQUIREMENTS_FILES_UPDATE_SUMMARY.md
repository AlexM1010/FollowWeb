# Requirements Files Update Summary

## Overview
Updated all documentation and spec files to accurately reflect the multiple requirements.txt files located in the `FollowWeb/` directory and their usage across the CI pipeline.

## Requirements File Structure

All requirements files are located in the **`FollowWeb/` directory**, not at the repository root:

### 1. `FollowWeb/requirements.txt`
- **Purpose**: Production dependencies only
- **Usage**: Installed in production environments and as base for other requirements files
- **Contains**: Core dependencies (networkx, pandas, matplotlib, pyvis, joblib, freesound-api, etc.)
- **CI Usage**: Included via `-r requirements.txt` in other requirements files

### 2. `FollowWeb/requirements-ci.txt`
- **Purpose**: Comprehensive CI dependencies
- **Usage**: Primary requirements file for CI workflows
- **Contains**: 
  - `-r requirements.txt` (includes all production dependencies)
  - Testing framework (pytest, pytest-cov, pytest-xdist, pytest-benchmark)
  - Code quality tools (ruff, mypy)
  - Security scanning (bandit, pip-audit)
  - Build tools (build, twine, wheel, check-manifest)
- **CI Usage**: Used by most CI jobs for comprehensive testing

### 3. `FollowWeb/requirements-test.txt`
- **Purpose**: Testing and development dependencies
- **Usage**: Local development and testing
- **Contains**: Same as requirements-ci.txt but without pip version constraint
- **CI Usage**: Used in some workflows alongside requirements.txt

### 4. `FollowWeb/requirements-minimal.txt`
- **Purpose**: Minimal dependencies for format checking only
- **Usage**: Fast format-only CI jobs
- **Contains**: Only ruff and mypy
- **CI Usage**: Used by format-check jobs for faster execution

### 5. `FollowWeb/pyproject.toml`
- **Purpose**: Package metadata and optional dependency groups
- **Usage**: Package configuration and pip install with extras
- **Contains**: Project metadata, dependencies, optional groups ([dev], [cleanup])

## CI Workflow Usage Patterns

### Pattern 1: Comprehensive Testing (Most Common)
```bash
pip install -r FollowWeb/requirements-ci.txt -e .
```
**Used by**: ci.yml (test jobs), nightly.yml, docs.yml

### Pattern 2: Production + Testing
```bash
pip install -r FollowWeb/requirements.txt
pip install -r FollowWeb/requirements-test.txt
pip install -e .
```
**Used by**: release.yml, some validation workflows

### Pattern 3: Production Only
```bash
pip install -r FollowWeb/requirements.txt
pip install -e FollowWeb/
```
**Used by**: freesound-nightly-pipeline.yml, freesound-quick-validation.yml

### Pattern 4: Format Checking Only
```bash
pip install -r FollowWeb/requirements-minimal.txt
```
**Used by**: ci.yml (format-check job)

## Files Updated

### 1. `.kiro/specs/repository-cleanup/tasks.md`
**Task 2: Update dependencies and remove redundant code**

**Changes:**
- Expanded to list all four requirements files explicitly
- Added specific instructions for each file:
  - `requirements.txt`: Production dependencies (organize-tool, GitPython, github3.py, PyYAML)
  - `requirements-ci.txt`: CI-specific (includes -r requirements.txt, adds reviewdog, git-filter-repo)
  - `requirements-test.txt`: Testing dependencies (already comprehensive)
  - `requirements-minimal.txt`: No changes needed
  - `pyproject.toml`: Update [project.optional-dependencies] with cleanup group
- Added note about verifying consistency across all four files

### 2. `.kiro/specs/repository-cleanup/design.md`
**Dependencies Section**

**Changes:**
- Added comprehensive overview of all requirements files with their locations
- Specified which dependencies go in which file:
  - Production dependencies in `requirements.txt`
  - CI-specific in `requirements-ci.txt` (which includes requirements.txt)
  - Testing already comprehensive in `requirements-test.txt`
  - Minimal unchanged in `requirements-minimal.txt`
- Added note explaining file locations and CI workflow usage patterns
- Updated "Update Requirements Files" section to reference all four files with specific paths

### 3
. `.kiro/specs/repository-cleanup/requirements.md`
**Requirement 16: Dependency Management and Requirements Files**

**Changes:**
- Added note at the beginning explaining all files are in `FollowWeb/` directory
- Listed all four requirements files with their purposes
- Updated acceptance criteria to reference correct file paths
- Changed "all requirements files" to explicitly list all four files
- Added clarification about organizing dependencies within each file
- Updated verification criteria to check consistency across all four files

### 4. `.kiro/steering/tech.md`
**Build System and CI/CD Integration Sections**

**Changes:**
- Expanded Build System section to list all four requirements files with descriptions
- Added note that all files are in `FollowWeb/` directory
- Updated CI/CD Integration section to explain different usage patterns:
  - CI workflows use `requirements-ci.txt` for comprehensive testing
  - Format-only jobs use `requirements-minimal.txt` for speed
  - Production installs use `requirements.txt` only
- Clarified that `requirements-ci.txt` includes all production and testing dependencies

## Key Insights from CI Pipeline Analysis

### Dependency Installation Patterns
1. **Most CI jobs** use `requirements-ci.txt` which includes everything via `-r requirements.txt`
2. **Format checking** uses `requirements-minimal.txt` for faster execution (only ruff + mypy)
3. **Freesound workflows** use production dependencies only (`requirements.txt`)
4. **Release workflow** installs both `requirements.txt` and `requirements-test.txt` separately

### File Relationships
```
requirements-ci.txt
├── -r requirements.txt (production dependencies)
├── pytest, pytest-cov, pytest-xdist, pytest-benchmark
├── ruff, mypy
├── bandit, pip-audit
└── build, twine, wheel, check-manifest

requirements-test.txt
├── pytest, pytest-cov, pytest-xdist, pytest-benchmark
├── ruff, mypy
├── bandit, pip-audit
└── build, twine, wheel, check-manifest

requirements-minimal.txt
├── ruff
└── mypy

requirements.txt
└── (production dependencies only)
```

## Recommendations for Task 2 Implementation

When implementing Task 2, the cleanup system should:

1. **Update `FollowWeb/requirements.txt`** with production dependencies:
   - organize-tool>=3.0.0
   - gitpython>=3.1.0
   - github3.py>=3.2.0
   - pyyaml>=6.0

2. **Update `FollowWeb/requirements-ci.txt`** with CI-specific dependencies:
   - reviewdog>=0.17.0
   - git-filter-repo>=2.38.0
   - Keep existing `-r requirements.txt` reference

3. **Verify `FollowWeb/requirements-test.txt`** has no conflicts:
   - Already comprehensive with all testing tools
   - No changes needed unless conflicts found

4. **Leave `FollowWeb/requirements-minimal.txt`** unchanged:
   - Only contains ruff and mypy
   - Used for fast format checking only

5. **Update `FollowWeb/pyproject.toml`**:
   - Add [project.optional-dependencies] cleanup group
   - Include all cleanup-related dependencies

6. **Verify consistency** across all files:
   - Check for version conflicts
   - Ensure no duplicate dependencies
   - Validate that requirements-ci.txt properly includes requirements.txt

## Testing Verification

After updating requirements files, verify:
- [ ] All CI workflows still pass
- [ ] Format-check job works with requirements-minimal.txt
- [ ] Test jobs work with requirements-ci.txt
- [ ] Freesound workflows work with requirements.txt only
- [ ] No version conflicts between files
- [ ] All dependencies install successfully
- [ ] Package builds correctly with new dependencies

## Documentation Consistency

All documentation now consistently references:
- Correct file locations (`FollowWeb/` directory)
- All four requirements files by name
- Proper usage patterns for each file
- CI workflow installation patterns
- File relationships and dependencies

This ensures developers and CI systems have accurate information about dependency management across the project.
