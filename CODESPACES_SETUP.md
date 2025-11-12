# GitHub Codespaces Dynamic Prebuild Setup

This repository is now configured with **intelligent prebuilds** that integrate with CI/CD pipelines for maximum efficiency.

## 🚀 What's Configured

### 1. Integrated CI/CD Prebuild System
- **File**: `.github/workflows/codespaces-prebuild.yml`
- **Integration**: Called by CI workflow as a reusable workflow
- **Triggers**: 
  - Automatically runs in parallel with CI smoke tests
  - Shared across all CI jobs (test matrix, security, build, performance, docs)
  - Manual workflow dispatch for testing
- **What it does**: Pre-installs Python 3.12, all dependencies, creates cached environment

### 2. Pipeline Architecture
```
CI Workflow Start
├── Prebuild (parallel) ──────┐
├── Smoke Test (parallel) ────┤
│                              ├──> All jobs use prebuild cache
├── Test Matrix ──────────────┤    - Full test suite
├── Security Scan ────────────┤    - Security checks
├── Format Check ─────────────┤    - Code quality
├── Build ────────────────────┤    - Package building
├── Performance ──────────────┤    - Benchmarks
└── Documentation ────────────┘    - Docs validation
```

### 3. Dev Container Configuration
- **File**: `.devcontainer/devcontainer.json`
- **Includes**:
  - Python 3.12 base image
  - Node.js LTS (for any JS tooling)
  - VS Code extensions (Python, Ruff, Mypy, Pylance)
  - Auto-formatting on save
  - Post-create command to install all dependencies

### 4. Dependency Management
- **File**: `.github/dependabot.yml`
- **Monitors**: Python packages, GitHub Actions, and devcontainer updates

## 📋 How It Works

### Automatic CI Integration

When you push code or create a PR:

1. **Prebuild starts immediately** (parallel with smoke test)
   - Installs all dependencies
   - Creates virtual environment
   - Caches everything for reuse

2. **Smoke test validates quickly** (parallel with prebuild)
   - Fast unit tests only
   - Gates all subsequent jobs

3. **All other jobs reuse prebuild cache**
   - Test matrix across Python versions and OS
   - Security scanning
   - Code quality checks
   - Package building
   - Performance benchmarks
   - Documentation validation

### For Codespaces

1. **Push your branch to GitHub**:
   ```bash
   git push origin your-branch-name
   ```

2. **Prebuild runs automatically with CI**:
   - Check Actions tab → CI workflow
   - Prebuild completes in ~2-3 minutes
   - Creates cached environment for your branch

3. **Open Codespace**:
   - Go to your branch on GitHub
   - Click "Code" → "Codespaces" → "Create codespace on [branch]"
   - Opens in seconds using the prebuild!

### Manual Prebuild Trigger

The prebuild is automatically triggered by CI, but you can also run it manually:

1. Go to **Actions** tab
2. Select **"Codespaces Prebuild"** workflow
3. Click **"Run workflow"**
4. Click **"Run workflow"** button

## 🎯 Benefits

### Performance
- **Fast CI runs**: Dependencies installed once, reused everywhere
- **Parallel execution**: Prebuild runs alongside smoke test
- **Cached environments**: 2-3 minute setup vs 5-10 minutes per job
- **Fast Codespaces**: 10-30 seconds to start vs 5-10 minutes

### Efficiency
- **Single source of truth**: One prebuild for CI and Codespaces
- **Reduced redundancy**: No duplicate dependency installations
- **Smart caching**: Automatic cache invalidation on dependency changes
- **Resource optimization**: Shared cache across all pipeline jobs

### Developer Experience
- **Zero configuration**: Works automatically for all branches
- **Consistent environments**: Same setup in CI and Codespaces
- **Quick feedback**: Smoke test validates while prebuild runs
- **Reliable builds**: Cached dependencies reduce network issues

## 🔧 Customization

### Add More Tools to Prebuild

Edit `.devcontainer/devcontainer.json`:

```json
"features": {
  "ghcr.io/devcontainers/features/node:1": {
    "version": "lts"
  },
  "ghcr.io/devcontainers/features/docker-in-docker:1": {}  // Add Docker
}
```

### Change Python Version

Update both files:
- `.devcontainer/devcontainer.json` → `"image": "mcr.microsoft.com/devcontainers/python:3.11"`
- `.github/workflows/codespaces-prebuild.yml` → `python-version: '3.11'`

### Modify Post-Install Commands

Edit `.devcontainer/devcontainer.json`:

```json
"postCreateCommand": "pip install -e 'FollowWeb/.[dev]' && make install-dev && make test-unit"
```

## 🐛 Troubleshooting

### Prebuild Failed
- Check Actions tab for error logs
- Common issues: dependency conflicts, test failures
- Fix the issue and push again - prebuild will retry

### Codespace Still Slow
- First Codespace on a new branch may be slower
- Wait for prebuild workflow to complete (check Actions tab)
- Subsequent opens will be fast

### Need to Clear Cache
- Re-run the prebuild workflow manually
- Or push a new commit to trigger automatic rebuild

## 📊 Monitoring Prebuilds

View all prebuilds:
1. Go to repository **Settings**
2. Click **Codespaces** in sidebar
3. See **Prebuild configuration** section
4. View prebuild history and logs

## 🎓 Learn More

- [GitHub Codespaces Prebuilds Documentation](https://docs.github.com/en/codespaces/prebuilding-your-codespaces)
- [Dev Container Specification](https://containers.dev/)
- [VS Code Remote Development](https://code.visualstudio.com/docs/remote/remote-overview)
