# GitHub Codespaces Configuration

This directory contains the configuration for GitHub Codespaces prebuilds.

## How It Works

The prebuild system automatically creates optimized development environments for **any branch** in this repository:

### Automatic Prebuilds
- **Trigger**: Runs on every push to any branch (`branches: ['**']`)
- **Pull Requests**: Also runs for PRs targeting any branch
- **Manual**: Can be triggered manually via workflow_dispatch

### What Gets Prebuilt
1. Python 3.12 environment
2. All development dependencies (`pip install -e ".[dev]"`)
3. CI dependencies (`requirements-ci.txt`)
4. Test data and caches
5. Quick validation (linting + fast unit tests)

### Benefits
- **Fast startup**: Codespaces open in seconds instead of minutes
- **Branch-specific**: Each branch gets its own prebuild
- **Always fresh**: Updates automatically on every push
- **No manual config**: Works for feature branches, main, and any other branch

## Usage

### Opening a Codespace
1. Navigate to any branch on GitHub
2. Click "Code" → "Codespaces" → "Create codespace on [branch]"
3. The prebuild will be used automatically if available
4. If no prebuild exists yet, it will be created on the next push

### Manual Prebuild Trigger
1. Go to Actions → "Codespaces Prebuild"
2. Click "Run workflow"
3. Select the branch you want to prebuild
4. Click "Run workflow"

## Configuration Files

- **`devcontainer.json`**: Defines the development container configuration
- **`.github/workflows/codespaces-prebuild.yml`**: Automates prebuild creation
- **`README.md`**: This file

## Customization

### Adding More Tools
Edit `devcontainer.json` → `features` section to add more development tools.

### Changing Python Version
Edit both:
- `devcontainer.json` → `image` property
- `.github/workflows/codespaces-prebuild.yml` → `python-version`

### Modifying Post-Create Commands
Edit `devcontainer.json` → `postCreateCommand` to change what runs after container creation.

## Troubleshooting

### Prebuild Failed
Check the Actions tab for the "Codespaces Prebuild" workflow to see error details.

### Codespace Slow to Start
The first Codespace on a new branch may be slower. Subsequent opens will use the prebuild.

### Cache Issues
Prebuilds include caching for pip packages and test data. If you need to clear caches, re-run the prebuild workflow.
