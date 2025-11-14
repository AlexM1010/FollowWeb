# Pre-Commit Hooks Setup

This repository uses [pre-commit](https://pre-commit.com/) to run code quality checks before each commit, preventing issues from reaching CI.

## Quick Setup

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# (Optional) Run on all files to check current state
pre-commit run --all-files
```

## What Gets Checked

The pre-commit hooks run the same checks as CI:

### 1. **Ruff Linting** (`ruff check`)
- Catches code quality issues
- Auto-fixes many problems
- Replaces flake8, isort, and other linters

### 2. **Ruff Formatting** (`ruff format`)
- Ensures consistent code style
- Auto-formats Python code
- Replaces black formatter

### 3. **Mypy Type Checking** (`mypy`)
- Validates type hints
- Catches type-related bugs early
- Runs on `FollowWeb_Visualizor/` module only

### 4. **YAML Validation**
- Validates workflow files
- Prevents syntax errors in GitHub Actions

### 5. **Actionlint**
- Validates GitHub Actions workflows
- Catches workflow-specific issues

### 6. **General Checks**
- Trailing whitespace removal
- End-of-file fixing
- Large file detection
- Merge conflict detection
- JSON syntax validation

## Usage

### Automatic (Recommended)
Once installed, hooks run automatically on `git commit`:

```bash
git add file.py
git commit -m "feat: add new feature"
# Hooks run automatically before commit
```

### Manual Run
Run hooks on all files:

```bash
pre-commit run --all-files
```

Run specific hook:

```bash
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

### Skip Hooks (Emergency Only)
If you need to commit without running hooks:

```bash
git commit --no-verify -m "emergency fix"
```

**⚠️ Warning:** Skipping hooks means your commit will likely fail CI checks.

## Troubleshooting

### Hook Fails on Commit
1. Review the error message
2. Fix the issues (many are auto-fixed)
3. Stage the fixes: `git add .`
4. Commit again

### Mypy Errors
If mypy fails:
```bash
# Run mypy manually to see full output
cd FollowWeb
mypy FollowWeb_Visualizor
```

### Update Hooks
Update to latest hook versions:
```bash
pre-commit autoupdate
```

### Clear Hook Cache
If hooks behave strangely:
```bash
pre-commit clean
pre-commit install --install-hooks
```

## Benefits

✅ **Catch issues early** - Before they reach CI
✅ **Faster feedback** - No waiting for CI to fail
✅ **Consistent code** - Everyone uses same tools
✅ **Auto-fix** - Many issues fixed automatically
✅ **Save CI time** - Fewer failed builds

## CI Integration

Pre-commit hooks run the **same checks** as CI:
- CI runs: `ruff check`, `ruff format --check`, `mypy`
- Pre-commit runs: Same tools, same configuration
- If pre-commit passes, CI quality checks will pass

## Configuration

Hook configuration is in `.pre-commit-config.yaml` at repository root.

Tool-specific configuration:
- **Ruff**: `FollowWeb/pyproject.toml` → `[tool.ruff]`
- **Mypy**: `FollowWeb/pyproject.toml` → `[tool.mypy]`
- **Actionlint**: Uses default configuration

## Disabling Hooks

To temporarily disable hooks:
```bash
pre-commit uninstall
```

To re-enable:
```bash
pre-commit install
```

## For New Contributors

If you're new to the project:

1. **Install pre-commit** (one-time setup)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Make your changes**
   ```bash
   # Edit files
   git add .
   ```

3. **Commit** (hooks run automatically)
   ```bash
   git commit -m "feat: my changes"
   ```

4. **If hooks fail**
   - Review errors
   - Many are auto-fixed (just `git add .` and commit again)
   - For others, fix manually and commit again

## Additional Resources

- [Pre-commit documentation](https://pre-commit.com/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [Mypy documentation](https://mypy.readthedocs.io/)
- [Actionlint documentation](https://github.com/rhysd/actionlint)
