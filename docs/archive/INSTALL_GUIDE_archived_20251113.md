# FollowWeb Installation Guide

## Quick Installation

```bash
# 1. Install the package in development mode
pip install -e .

# 2. Test the installation
followweb --help

# 3. Run with fast configuration
followweb fast_config.json
```

## Alternative Installation Methods

### Method 1: Development Installation (Recommended)
```bash
pip install -e .
```
- Installs package in editable mode
- Changes to code are immediately available
- Creates `followweb` console command

### Method 2: Regular Installation
```bash
pip install .
```
- Standard installation
- Creates `followweb` console command

### Method 3: Dependencies Only
```bash
pip install -r requirements.txt
```
- Install dependencies without installing the package
- Run with `python FollowWeb/FollowWeb_Visualizor/main.py --config config.json`

## Running the Package

After installation, you can use any of these methods:

### Console Script (Easiest)
```bash
followweb --config config.json
followweb --config fast_config.json
```

### Python Module
```bash
python -m FollowWeb_Visualizor --config config.json
python -m FollowWeb_Visualizor --config fast_config.json
```

### Direct Script
```bash
python FollowWeb/FollowWeb_Visualizor/main.py --config config.json
```

## Testing the Improved Spacing

### Quick Test
```bash
# Install and test
pip install -e .
followweb fast_config.json
```

### Verification Test
```bash
# Run the test suite to verify installation
make test
# or
python tests/run_tests.py all
```

## Troubleshooting

### Command Not Found
If `followweb` command is not found after installation:
```bash
# Check if package is installed
pip list | grep FollowWeb

# Reinstall if needed
pip uninstall FollowWeb-Visualizor
pip install -e .
```

### Import Errors
If you get import errors:
```bash
# Install dependencies
pip install -r requirements.txt

# Reinstall package
pip install -e .
```

### Permission Issues
On some systems, you might need:
```bash
pip install --user -e .
```

## Verification

Test that everything works:
```bash
# Check help
followweb --help

# Test with sample config
followweb fast_config.json
```

The improved spacing configuration will generate PNG files with much better node separation and reduced overlap.