# Installation Guide - G-Code Database Manager

## System Requirements

- **Python:** 3.7 or higher
- **Operating System:** Windows, macOS, or Linux
- **Disk Space:** ~100MB for dependencies + your data

## Installation Steps

### Step 1: Verify Python Installation

Open a terminal/command prompt and run:

```bash
python --version
```

You should see: `Python 3.7.x` or higher

If not installed, download from: https://www.python.org/downloads/

---

### Step 2: Install Required Packages

#### Option A: Install All at Once (Recommended)

```bash
pip install -r requirements.txt
```

This installs:
- `openpyxl` (Excel export)
- `tkinterdnd2` (drag-and-drop)

#### Option B: Install Individually

**Required packages:**
```bash
pip install openpyxl
pip install tkinterdnd2
```

**Optional packages (for ML features):**
```bash
pip install pandas scikit-learn numpy
```

---

### Step 3: Verify Installation

Run the verification script:

```bash
python --version        # Check Python version
python -m tkinter       # Test tkinter (should open a window)
```

**Verify specific packages:**

```bash
python -c "import openpyxl; print('openpyxl:', openpyxl.__version__)"
python -c "import tkinterdnd2; print('tkinterdnd2:', tkinterdnd2.__version__)"
```

Expected output:
```
openpyxl: 3.x.x
tkinterdnd2: 0.4.x
```

---

## Troubleshooting

### Issue 1: tkinter not found (Linux)

**Error:**
```
ModuleNotFoundError: No module named '_tkinter'
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

---

### Issue 2: pip not found

**Error:**
```
'pip' is not recognized as an internal or external command
```

**Solution:**

**Windows:**
```bash
python -m pip install --upgrade pip
python -m pip install openpyxl tkinterdnd2
```

**macOS/Linux:**
```bash
python3 -m pip install --upgrade pip
python3 -m pip install openpyxl tkinterdnd2
```

---

### Issue 3: Permission denied

**Error:**
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solution:**

**Windows:** Run Command Prompt as Administrator

**macOS/Linux:**
```bash
pip install --user openpyxl tkinterdnd2
```

---

### Issue 4: SSL Certificate Error

**Error:**
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org openpyxl tkinterdnd2
```

---

### Issue 5: Multiple Python Versions

If you have multiple Python versions installed:

```bash
# Use specific version
python3.9 -m pip install openpyxl tkinterdnd2

# Or
py -3.9 -m pip install openpyxl tkinterdnd2
```

---

## Optional Features

### ML Dimension Prediction

For machine learning fallback features, install:

```bash
pip install pandas scikit-learn numpy
```

**Note:** These are large packages (~500MB). Only install if you want ML features.

**To enable:**
1. Uncomment lines 20-22 in `requirements.txt`
2. Run: `pip install -r requirements.txt`

---

### Advanced Features (Future)

For charts, barcodes, and image handling:

```bash
pip install matplotlib pillow qrcode python-barcode
```

---

## Quick Installation Script

### Windows: install_all.bat

Create `install_all.bat`:

```batch
@echo off
echo ========================================
echo Installing G-Code Database Manager
echo ========================================
echo.

echo Checking Python version...
python --version
echo.

echo Installing required packages...
pip install openpyxl tkinterdnd2
echo.

echo Installation complete!
echo.
pause
```

Run by double-clicking `install_all.bat`

---

### macOS/Linux: install_all.sh

Create `install_all.sh`:

```bash
#!/bin/bash
echo "========================================"
echo "Installing G-Code Database Manager"
echo "========================================"
echo

echo "Checking Python version..."
python3 --version
echo

echo "Installing required packages..."
pip3 install openpyxl tkinterdnd2
echo

echo "Installation complete!"
```

Run: `bash install_all.sh`

---

## Verifying Everything Works

### Test Script

Create `test_install.py`:

```python
"""Test all dependencies"""

print("Testing imports...")

# Test tkinter
try:
    import tkinter as tk
    print("✓ tkinter: OK")
except ImportError:
    print("✗ tkinter: MISSING")

# Test openpyxl
try:
    import openpyxl
    print(f"✓ openpyxl: {openpyxl.__version__}")
except ImportError:
    print("✗ openpyxl: MISSING")

# Test tkinterdnd2
try:
    import tkinterdnd2
    print(f"✓ tkinterdnd2: {tkinterdnd2.__version__}")
except ImportError:
    print("✗ tkinterdnd2: MISSING")

# Test optional ML packages
try:
    import pandas
    import sklearn
    import numpy
    print("✓ ML packages: OK (optional)")
except ImportError:
    print("○ ML packages: Not installed (optional)")

print("\nAll required packages installed successfully!")
```

Run: `python test_install.py`

---

## Running the Application

After installation:

```bash
python gcode_database_manager.py
```

You should see:
- Repository folders created
- Database initialized
- GUI window opens

---

## Package Versions

### Required (Minimum):

```
Python >= 3.7
openpyxl >= 3.0.0
tkinterdnd2 >= 0.4.0
```

### Optional (for ML):

```
pandas >= 1.3.0
scikit-learn >= 1.0.0
numpy >= 1.20.0
```

---

## Updating Packages

To update all packages to latest versions:

```bash
pip install --upgrade openpyxl tkinterdnd2
```

Or update everything:

```bash
pip install --upgrade -r requirements.txt
```

---

## Uninstallation

To remove packages:

```bash
pip uninstall openpyxl tkinterdnd2
```

To remove ML packages:

```bash
pip uninstall pandas scikit-learn numpy
```

---

## Platform-Specific Notes

### Windows

- Use Command Prompt or PowerShell
- May need to run as Administrator
- Python might be `python` or `py`

### macOS

- Use Terminal
- Python might be `python3` instead of `python`
- pip might be `pip3` instead of `pip`
- May need Xcode Command Line Tools

### Linux

- Use Terminal
- Install `python3-tk` separately
- May need `sudo` for system-wide install
- Or use `--user` flag for user-only install

---

## Getting Help

### Check Installation Status

```bash
pip list | grep -E "openpyxl|tkinterdnd2"
```

### Check Package Location

```bash
pip show openpyxl
pip show tkinterdnd2
```

### Reinstall Package

```bash
pip uninstall openpyxl
pip install openpyxl
```

---

## Summary

### Minimum Installation (Required):

```bash
pip install openpyxl tkinterdnd2
```

### Full Installation (Recommended):

```bash
pip install -r requirements.txt
```

### With ML Features:

```bash
pip install openpyxl tkinterdnd2 pandas scikit-learn numpy
```

---

## Next Steps

After installation:

1. ✓ Run `python test_install.py` to verify
2. ✓ Run `python gcode_database_manager.py` to launch
3. ✓ Check console for "[Repository] Initialized" message
4. ✓ Test drag-and-drop functionality

---

**Installation support:** If you encounter issues, check the Troubleshooting section above or create an issue in the repository.
