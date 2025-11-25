# Quick Start Guide

## Installation (5 minutes)

### Step 1: Install Python
- Download from [python.org](https://www.python.org/downloads/)
- ✅ Check "Add Python to PATH" during installation
- Click "Install Now"

### Step 2: Verify Installation
Open Command Prompt (Windows) or Terminal (Mac/Linux) and type:
```bash
python --version
```
You should see Python 3.7 or higher.

### Step 3: Test tkinter
```bash
python -m tkinter
```
A small test window should appear. If not:
- **Linux**: `sudo apt-get install python3-tk`
- **Windows/Mac**: Reinstall Python with tcl/tk enabled

## Running the Application

### Windows
1. Open Command Prompt
2. Navigate to the folder:
   ```cmd
   cd "C:\path\to\File organizer"
   ```
3. Run:
   ```cmd
   python gcode_database_manager.py
   ```

### Mac/Linux
1. Open Terminal
2. Navigate to the folder:
   ```bash
   cd "/path/to/File organizer"
   ```
3. Run:
   ```bash
   python3 gcode_database_manager.py
   ```

## First Time Setup

1. Click **"📂 Scan Directory"**
2. Browse to your G-code folder (e.g., `I:\My Drive\NC Master\REVISED PROGRAMS\5.75`)
3. Click OK
4. Wait for scanning to complete (1-2 seconds per file)
5. Database is created automatically

## Basic Usage

### Search for Programs
- Type program number in search box (e.g., "o570")
- Click **🔍 Search**

### Filter Results
- **Type**: Click to select hub_centric, step, standard, etc.
- **Material**: Click to select 6061-T6, 7075-T6, etc.
- **Status**: Click to select CRITICAL, PASS, etc.

### View Details
- Double-click any row to see complete information
- View dimensional data, validation issues, and G-code extractions

### Status Breakdown
Bottom-right shows count by validation status:
```
Results: 814 programs  |  CRITICAL: 256  BORE: 7  DIM: 11  WARN: 2  PASS: 538
```

### Color Coding
- 🔴 **Red** - CRITICAL errors (CB/OB way off spec)
- 🟠 **Orange** - BORE_WARNING (at tolerance limit)
- 🟣 **Purple** - DIMENSIONAL (P-code mismatches)
- 🟡 **Yellow** - WARNING (minor issues)
- 🟢 **Green** - PASS (all checks passed)

## Common Tasks

### Export to Excel
Click **"💾 Export All to CSV"** - opens in Excel

### Rescan After Changes
```bash
python rescan_database.py
```

### Test Single File
```bash
python improved_gcode_parser.py "path/to/o57000"
```

## Troubleshooting

### "Python is not recognized"
- Reinstall Python with "Add to PATH" checked
- Restart Command Prompt/Terminal

### "Database is locked"
- Close all other programs using the database
- Restart the application

### Application won't start
- Run: `python -m tkinter` to test GUI
- Check Python version: `python --version`

## Need Help?

See full **README.md** for:
- Detailed installation instructions
- Complete feature documentation
- Validation rules and type detection
- Database schema
- Advanced configuration

---

**That's it! You're ready to manage your G-code database.**
