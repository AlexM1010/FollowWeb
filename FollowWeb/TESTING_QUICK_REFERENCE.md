# Testing Quick Reference

## Auto-Fix Code Issues (Fastest!)
```bash
python tests/run_tests.py fix              # ONLY fix issues (no checks)
python tests/run_tests.py quality --autofix # Fix + verify
python tests/run_tests.py all --autofix     # Fix + run all checks
```

## Run Full CI Pipeline Locally
```bash
python tests/run_tests.py all
```

## Individual Check Categories
```bash
python tests/run_tests.py quality      # Format, lint, type check
python tests/run_tests.py security     # Bandit + pip-audit
python tests/run_tests.py unit         # Unit tests (parallel)
python tests/run_tests.py integration  # Integration tests (parallel)
python tests/run_tests.py performance  # Performance tests (sequential)
python tests/run_tests.py benchmark    # Benchmarks (sequential)
python tests/run_tests.py build        # Package validation
```

## Manual Fixes (if needed)
```bash
ruff format FollowWeb_Visualizor tests              # Fix formatting
ruff check --fix FollowWeb_Visualizor tests         # Fix linting
mypy FollowWeb_Visualizor --show-error-codes        # Check types
```

## Recommended Workflow
- **Quick fix**: `python tests/run_tests.py fix`
- **During development**: `python tests/run_tests.py unit`
- **Before committing**: `python tests/run_tests.py all --autofix`
- **Before pushing**: `python tests/run_tests.py quality security`

See `tests/README.md` for complete documentation.
