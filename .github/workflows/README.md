# GitHub Actions Workflows

This directory contains all GitHub Actions workflow files for the FollowWeb project.

## Workflow Files

### CI/CD Workflows

- **ci.yml** - Main CI pipeline (tests, quality checks, security scans)
- **release.yml** - Package publishing to PyPI and TestPyPI
- **deploy-website.yml** - GitHub Pages deployment
- **docs.yml** - Documentation validation and quality checks

### Freesound Pipelines

#### Automated Pipelines
- **freesound-nightly-pipeline.yml** - Daily data collection (2 AM UTC Mon-Sat)
- **freesound-data-repair.yml** - Automated data validation and repair (runs after collection)
- **freesound-validation-visualization.yml** - Validation and visualization generation
- **freesound-backup.yml** - Checkpoint backup management (runs after validation)

#### Scheduled Validation
- **freesound-quick-validation.yml** - Weekly quick validation (Sunday 3 AM UTC, 300 samples)
- **freesound-full-validation.yml** - Monthly full validation (1st of month 4 AM UTC, all samples)

#### Maintenance
- **freesound-backup-maintenance.yml** - Backup cleanup and retention management
- **freesound-metrics-dashboard.yml** - Metrics dashboard generation

### Maintenance Workflows

- **nightly.yml** - Nightly dependency testing with latest versions

## Helper Scripts

All workflows use helper scripts located in `.github/scripts/`:

- **ci_helpers.py** - CI utilities for emoji formatting and status reporting
- **regenerate_checkpoint_metadata.py** - Regenerate checkpoint metadata from graph
- **rebuild_metadata_cache.py** - Rebuild SQLite cache from graph data
- **validate_ci_helpers_path.py** - Validate ci_helpers.py path references

### ci_helpers.py Path Convention

**IMPORTANT:** The path to `ci_helpers.py` depends on the working directory:

- **From root directory:** Use `.github/scripts/ci_helpers.py`
- **From FollowWeb directory:** Use `../.github/scripts/ci_helpers.py`

Most workflows use `working-directory: FollowWeb` for steps that need the package, so they use the relative path `../.github/scripts/ci_helpers.py`.

**Examples:**

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
          python .github/scripts/ci_helpers.py success "Message"
```

```yaml
# Step-level working-directory override
jobs:
  my-job:
    runs-on: ubuntu-latest
    steps:
      - name: My step
        working-directory: FollowWeb
        run: |
          python ../.github/scripts/ci_helpers.py success "Message"
```

## Workflow Dependencies

### CI Pipeline (ci.yml)

```
Phase 1 (Parallel):
├── environment-build
├── smoke-test
├── quality-check
├── security
└── build

Phase 2 (Parallel, depends on Phase 1):
├── test (matrix: 3 OS × Python versions)
├── performance
├── benchmarks
└── documentation (calls docs.yml)

Phase 3 (Final):
└── ci-success (depends on all Phase 2 jobs)
```

### Documentation Pipeline (docs.yml)

```
Parallel Jobs:
├── documentation-structure
└── docstring-coverage

Sequential Job (depends on both parallel jobs):
└── conventional-commits (non-critical, continue-on-error)
```

## Troubleshooting

### Workflow File Syntax Errors

If a workflow shows "workflow file issue" error:

1. Validate YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/workflows/WORKFLOW.yml'))"
   ```

2. Use actionlint (if installed):
   ```bash
   actionlint .github/workflows/WORKFLOW.yml
   ```

3. Check for common issues:
   - Heredoc syntax in bash scripts (use separate Python files instead)
   - Incorrect indentation in multi-line strings
   - Missing quotes around special characters

### ci_helpers.py Path Errors

If you get "No such file or directory" errors for ci_helpers.py:

1. Check the working directory context
2. Use the correct relative path (see convention above)
3. Run the validation script:
   ```bash
   python .github/scripts/validate_ci_helpers_path.py
   ```

### Duplicate Job Definitions

If you see "duplicate job" errors:

1. Check for jobs with the same name in the same workflow
2. Ensure job names are unique within each workflow file
3. Check for copy-paste errors

## Best Practices

1. **Use defaults for working-directory** when most steps need it
2. **Override at step level** for exceptions
3. **Keep helper scripts in .github/scripts/** for consistency
4. **Use relative paths** based on working directory
5. **Validate workflows** before committing (use pre-commit hooks)
6. **Document workflow changes** in this README
7. **Test workflows** with manual triggers before relying on schedules

## Pre-Commit Hooks

Pre-commit hooks automatically validate workflows before commit:

```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Hooks will run automatically on commit
# Includes actionlint for workflow validation
```

See `.pre-commit-config.yaml` and `.github/PRE_COMMIT_SETUP.md` for details.


## Job Dependency Audit (Last Updated: 2024-11-14)

### CI Workflow (ci.yml)

**Job Dependency Chain:**
- ✅ No circular dependencies
- ✅ No duplicate job names
- ✅ Clear phase separation (Phase 1 → Phase 2 → Phase 3)
- ✅ Proper use of `needs:` for dependencies
- ✅ `fail-fast: true` for matrix jobs
- ✅ `continue-on-error: false` for critical jobs

**Dependency Graph:**
```
environment-build ─┐
smoke-test ────────┼─→ test (matrix)
quality-check ─────┤   performance
security ──────────┤   benchmarks
build ─────────────┘   documentation → ci-success
```

### Documentation Workflow (docs.yml)

**Job Dependency Chain:**
- ✅ No circular dependencies
- ✅ No duplicate job names
- ✅ Parallel execution of independent jobs
- ✅ Sequential execution where needed
- ✅ `continue-on-error: true` for non-critical jobs

**Dependency Graph:**
```
documentation-structure ─┐
docstring-coverage ──────┴─→ conventional-commits (non-critical)
```

### Freesound Nightly Pipeline (freesound-nightly-pipeline.yml)

**Job Dependency Chain:**
- ✅ No circular dependencies
- ✅ No duplicate job names
- ✅ Simple linear dependency: smoke-test → freesound-pipeline

### Other Workflows

All other workflows have been reviewed and show:
- ✅ No circular dependencies
- ✅ No duplicate job definitions
- ✅ Proper dependency chains

## Validation

To validate workflow dependencies:

```bash
# Check for duplicate job names
grep -r "^  [a-z-]*:" .github/workflows/*.yml | sort | uniq -d

# Check for circular dependencies (manual review required)
# Look for jobs that depend on each other in a cycle
```
