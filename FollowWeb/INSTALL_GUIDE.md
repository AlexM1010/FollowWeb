# FollowWeb Installation Guide

## Quick Installation

```bash
pip install followweb-visualizor
```

## Using FollowWeb

After installation, you can use FollowWeb in two ways:

### Method 1: Direct Command (Recommended)
```bash
followweb --help
```

### Method 2: Python Module (Always Works)
```bash
python -m FollowWeb_Visualizor --help
```

## If `followweb` Command Not Found

On some systems, the `followweb` command might not be immediately available. This happens when the Python Scripts directory isn't in your PATH.

### Quick Fix Options

**Option 1: Use the full module command (always works)**
```bash
python -m FollowWeb_Visualizor --help
```

**Option 2: Install system-wide (requires admin privileges)**
```bash
# Windows (as Administrator)
pip install followweb-visualizor

# macOS/Linux (with sudo)
sudo pip install followweb-visualizor
```

**Option 3: Add Scripts directory to PATH**

#### Windows
```powershell
# Find Scripts directory
python -c "import site; from pathlib import Path; print(Path(site.getusersitepackages()).parent / 'Scripts')"

# Add to user PATH (replace with actual path)
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Users\YourName\AppData\Roaming\Python\Python3XX\Scripts", [EnvironmentVariableTarget]::User)
```

#### macOS/Linux
```bash
# Find bin directory
python -c "import site; from pathlib import Path; print(Path(site.getuserbase()) / 'bin')"

# Add to shell profile (~/.bashrc, ~/.zshrc, or ~/.profile)
echo 'export PATH="$PATH:~/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

## Verification

Test that installation worked:

```bash
# Direct command (after PATH setup)
followweb --help

# Alternative (always works)
python -m FollowWeb_Visualizor --help
```

## Installation Options

### System-wide Installation

```bash
# Requires admin/sudo privileges
pip install followweb-visualizor

# On macOS/Linux
sudo pip install followweb-visualizor
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/followweb/followweb-visualizor.git
cd followweb-visualizor/FollowWeb

# Install in development mode
pip install -e .
```

### Virtual Environment (Recommended for Development)

```bash
# Create virtual environment
python -m venv followweb-env

# Activate (Windows)
followweb-env\Scripts\activate

# Activate (macOS/Linux)
source followweb-env/bin/activate

# Install
pip install followweb-visualizor
```

## Troubleshooting

### Command Not Found

If `followweb` command is not found:

1. **Check installation:**
   ```bash
   pip show followweb-visualizor
   ```

2. **Use full module path:**
   ```bash
   python -m FollowWeb_Visualizor --help
   ```

3. **Check your PATH:**
   ```bash
   # Windows
   echo $env:PATH
   
   # macOS/Linux  
   echo $PATH
   ```

### Permission Issues

If you get permission errors:

```bash
# Use user installation
pip install --user followweb-visualizor

# Or use virtual environment
python -m venv myenv
source myenv/bin/activate  # or myenv\Scripts\activate on Windows
pip install followweb-visualizor
```

### Dependencies

If you encounter dependency issues:

```bash
# Update pip first
python -m pip install --upgrade pip

# Install with verbose output
pip install -v followweb-visualizor

# Force reinstall
pip install --force-reinstall followweb-visualizor
```

## Requirements

- Python 3.9+ (recommended)
- Minimum Python 3.8
- NetworkX >= 2.8.0
- pandas >= 1.5.0
- matplotlib >= 3.5.0
- pyvis >= 0.3.0

## Next Steps

After installation, see the [User Guide](USER_GUIDE.md) for usage examples and tutorials.