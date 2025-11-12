# Requirements Files Guide

This document explains the purpose and usage of each requirements file in the FollowWeb project.

## Requirements Files Overview

### `requirements.txt` - Production Dependencies
**Purpose:** Core dependencies needed to run FollowWeb in production.

**Usage:**
```bash
pip install -r requirements.txt
```

**Contains:**
- NetworkX (graph analysis)
- pandas (data manipulation)
- matplotlib (visualization)
- pyvis (interactive visualizations)
- nx-parallel (parallel processing, Python 3.11+)
- Other core runtime dependencies

**When to use:**
- Installing FollowWeb for production use
- Docker containers
- End-user installations

---

### `requirements-ci.txt` - CI/CD Dependencies
**Purpose:** Comprehensive dependencies for continuous integration and development.

**Usage:**
```bash
pip install -r requirements-ci.txt
```

**Contains:**
- All production dependencies (from requirements.txt)
- Testing tools (pytest, pytest-cov, pytest-xdist, pytest-benchmark)
- Code quality tools (ruff, mypy, bandit, pip-audit)
- Type stubs (types-python-dateutil, types-PyYAML, types-decorator)
- Build tools (build, twine, check-manifest)

**When to use:**
- GitHub Actions CI workflows
- Local development with full tooling
- Running all quality checks locally

---

### `requirements-test.txt` - Testing Dependencies Only
**Purpose:** Minimal dependencies needed to run tests.

**Usage:**
```bash
pip install -r requirements.txt -r requirements-test.txt
```

**Contains:**
- pytest and plugins (pytest-cov, pytest-xdist, pytest-benchmark)
- Testing utilities

**When to use:**
- Running tests in isolated environments
- Test-only containers
- Minimal test setups

---

### `requirements-minimal.txt` - Format Checking Only
**Purpose:** Absolute minimum dependencies for code formatting checks.

**Usage:**
```bash
pip install -r requirements-minimal.txt
```

**Contains:**
- ruff (linting and formatting)
- Minimal dependencies needed for ruff to work

**When to use:**
- Pre-commit hooks
- Quick format checks
- Lightweight CI jobs that only check formatting

---

## Dependency Management Best Practices

### Adding New Dependencies

1. **Production dependency:**
   - Add to `requirements.txt`
   - Update `pyproject.toml` dependencies section
   - Run `pip install -e .` to test

2. **Development/testing tool:**
   - Add to `requirements-ci.txt`
   - Document why it's needed

3. **Type stub:**
   - Add to `requirements-ci.txt`
   - Needed if mypy complains about missing stubs

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
pip install --upgrade -r requirements-ci.txt

# Check for outdated packages
pip list --outdated

# Test after updates
make test
make lint
make type-check
```

### Dependency Conflicts

If you encounter dependency conflicts:

1. Check `pyproject.toml` for version constraints
2. Use `pip install --upgrade --upgrade-strategy eager` to resolve
3. Consider using `pip-compile` for deterministic builds
4. Document any version pins with reasons

---

## CI/CD Usage

### GitHub Actions Workflows

**CI Workflow (`.github/workflows/ci.yml`):**
- Uses `requirements-ci.txt` for comprehensive testing
- Caches pip dependencies for faster runs
- Runs on multiple OS and Python versions

**Nightly Workflow (`.github/workflows/nightly.yml`):**
- Uses `requirements-ci.txt` for security scanning
- Tests with latest dependency versions
- Stricter security checks than CI

**Format Check Workflow:**
- Uses `requirements-minimal.txt` for fast format checks
- Minimal dependencies for quick feedback

---

## Local Development Setup

### Full Development Environment
```bash
# Install all development dependencies
pip install -r FollowWeb/requirements-ci.txt -e FollowWeb/

# Or use the Makefile
cd FollowWeb
make install-dev
```

### Quick Format Check
```bash
# Install minimal dependencies
pip install -r FollowWeb/requirements-minimal.txt

# Check formatting
cd FollowWeb
ruff format --check FollowWeb_Visualizor tests
ruff check FollowWeb_Visualizor tests
```

### Testing Only
```bash
# Install production + test dependencies
pip install -r FollowWeb/requirements.txt -r FollowWeb/requirements-test.txt -e FollowWeb/

# Run tests
cd FollowWeb
python tests/run_tests.py all
```

---

## Troubleshooting

### "Module not found" errors
- Ensure you've installed the correct requirements file
- Check if you need `requirements-ci.txt` instead of `requirements.txt`
- Verify editable install: `pip install -e FollowWeb/`

### Type checking failures
- Install type stubs: `pip install types-python-dateutil types-PyYAML types-decorator`
- These are included in `requirements-ci.txt`

### Security scan failures
- Install security tools: `pip install bandit pip-audit`
- These are included in `requirements-ci.txt`

### Dependency version conflicts
- Check `pyproject.toml` for version constraints
- Use `pip install --upgrade --upgrade-strategy eager`
- Consider creating a fresh virtual environment

---

## Version Pinning Strategy

**Current approach:** Flexible version ranges in `requirements.txt`
- Allows automatic security updates
- Tested in nightly builds with latest versions
- CI uses pip cache for consistency within workflow runs

**Future consideration:** Add `requirements-lock.txt` for deterministic builds
- Generated with `pip-compile`
- Pins exact versions for reproducibility
- Updated periodically and tested

---

## Related Documentation

- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - Installation instructions
- [Makefile](Makefile) - Development automation commands
- [pyproject.toml](pyproject.toml) - Package configuration
- [.github/workflows/](../.github/workflows/) - CI/CD workflows
