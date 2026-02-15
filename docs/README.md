# G-Code Database Manager

A database management system for organizing and validating CNC G-code programs for spacer manufacturing.

## Features

- **Automatic Type Detection**: Detects spacer types (hub-centric, step, standard, metric, 2-piece)
- **Dimensional Extraction**: Extracts OD, thickness, CB, OB, hub height from G-code and title
- **5-Color Validation System**:
  - 🔴 **CRITICAL**: CB/OB dimensions way off spec (>0.25mm error)
  - 🟠 **BORE_WARNING**: Bore dimensions at tolerance limit (0.2-0.25mm error)
  - 🟣 **DIMENSIONAL**: P-code or thickness mismatches
  - 🟡 **WARNING**: General warnings (filename mismatches, etc.)
  - 🟢 **PASS**: All validations passed
- **Multi-Select Filters**: Filter by type, material, validation status
- **Status Breakdown**: Real-time count of files by validation status
- **Details Window**: View complete dimensional data and validation issues

## System Requirements

### Required
- **Python 3.7 or higher**
- **Operating System**: Windows, macOS, or Linux

### Dependencies
**All dependencies are included with Python - no external packages required!**

The application uses only Python standard library modules:
- `tkinter` - GUI framework (included with most Python installations)
- `sqlite3` - Database engine (included with Python)
- `re`, `os`, `sys` - Standard utilities (included with Python)
- `dataclasses`, `typing` - Data structures (Python 3.7+)
- `datetime` - Date/time handling (included with Python)

## Installation

### 1. Install Python

**Windows:**
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH" during installation
4. Complete the installation

**macOS:**
```bash
brew install python3
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3 python3-tk
```

### 2. Verify Installation

Open a terminal/command prompt and run:
```bash
python --version
```
You should see Python 3.7 or higher.

### 3. Verify tkinter

Test that tkinter is installed:
```bash
python -m tkinter
```
This should open a small test window. If it doesn't:

**Linux:**
```bash
sudo apt-get install python3-tk
```

**Windows/macOS:**
Reinstall Python from python.org and ensure the tcl/tk option is selected.

### 4. Copy Project Files

Copy these files to a folder on your computer:
```
File organizer/
├── gcode_database_manager.py    # Main GUI application
├── improved_gcode_parser.py     # G-code parsing engine
├── rescan_database.py           # Database rescan utility (optional)
└── README.md                    # This file
```

## Usage

### Starting the Application

**Windows:**
1. Open Command Prompt
2. Navigate to the folder:
   ```cmd
   cd "C:\path\to\File organizer"
   ```
3. Run the application:
   ```cmd
   python gcode_database_manager.py
   ```

**macOS/Linux:**
1. Open Terminal
2. Navigate to the folder:
   ```bash
   cd "/path/to/File organizer"
   ```
3. Run the application:
   ```bash
   python3 gcode_database_manager.py
   ```

### First Time Setup

1. The application window will open
2. Click the **"📂 Scan Directory"** button
3. Navigate to your G-code programs folder
   - Example: `I:\My Drive\NC Master\REVISED PROGRAMS\5.75`
4. Select the folder and click OK
5. Wait for parsing to complete (about 1-2 seconds per file)
6. The database (`gcode_database.db`) will be created in the application folder

### Using the Application

**Search and Filter:**
- **Program Number**: Type partial program name (e.g., "o570" finds o57000, o57001, etc.)
- **Type**: Click to select one or more spacer types (hub_centric, step, standard, etc.)
- **Material**: Click to select materials (6061-T6, 7075-T6, etc.)
- **Validation Status**: Click to select validation levels (CRITICAL, PASS, etc.)
- **Dimension Ranges**: Enter min/max values for OD, thickness, or CB
- Click **🔍 Search** to apply filters

**Results Table:**
- Click column headers to sort by that column
- Double-click any row to view detailed information
- Rows are color-coded by validation status

**Status Breakdown:**
The bottom-right corner shows a real-time count by status:
```
Results: 814 programs  |  CRITICAL: 256  BORE: 7  DIM: 11  WARN: 2  PASS: 538
```

**Details Window:**
Double-click a program to see:
- Complete title and file information
- All dimensional data (OD, thickness, CB, OB, hub height, etc.)
- G-code extracted dimensions
- All validation issues with detailed descriptions

### Additional Features

**Export Database:**
Click **"💾 Export All to CSV"** to create a spreadsheet of all programs.

**Rescan Files:**
If you add new files or update the parser logic:
```bash
python rescan_database.py
```

**Parse Single File:**
To test parsing on one file:
```bash
python improved_gcode_parser.py "path/to/o57000"
```

## Configuration

### Database Location
The database `gcode_database.db` is created in the same folder as the application.

### Changing G-Code Directory
To change the default G-code folder for rescanning:
1. Open `rescan_database.py` in a text editor
2. Find the line: `GCODE_DIR = r"I:\My Drive\NC Master\REVISED PROGRAMS\5.75"`
3. Change the path to your G-code folder
4. Save the file

## Understanding Validation

### Type Detection Priority

The parser uses a hierarchical detection system:

**1. HC Keyword (Highest Priority)**
- If "HC" appears in title → classified as `hub_centric`
- Example: "5.75 IN 71.6/71.6mm 1.5 HC L1"

**2. Hub-Centric Patterns**
- CB marker + OB after chamfer + chamfer found
- 2 or more progressive facing cycles

**3. STEP Patterns**
- Intermediate Z depths with X changes

**4. Other Types**
- Standard, metric_spacer, 2pc_part1, 2pc_part2

### Bore Tolerance Thresholds

**BORE_WARNING** (Orange):
- Difference > 0.2mm but within acceptable range

**CRITICAL** (Red):
- **CB**: Difference < -0.25mm or > +0.4mm
- **OB**: Difference < -0.4mm or > +0.25mm

### Special Cases

**Thin-Hub Shelf Pattern:**
- When CB and OB are within 5mm of each other
- `(X IS CB)` marker is valid even at partial depth
- Shelf created in OP1 to preserve hub material

**CB=Counterbore:**
- When title shows the same value for CB and Counterbore
- Example: 71.6/71.6mm
- Trust `(X IS CB)` marker at partial depth

### P-Code Validation

The parser validates that G-code work offsets match the title thickness:
- P7 = 17MM (0.669")
- P17/P18 = 1.25"
- P23/P24 = 2.0"
- Mismatch triggers DIMENSIONAL warning with detailed explanation

## Troubleshooting

### "Python is not recognized"
- Windows: Reinstall Python and check "Add Python to PATH"
- Restart your terminal/command prompt after installation

### "No module named 'tkinter'"
- **Linux**: `sudo apt-get install python3-tk`
- **Windows/macOS**: Reinstall Python with tcl/tk option enabled

### "Database is locked"
- Close any other programs accessing `gcode_database.db`
- Close any Python scripts or database viewers
- Restart the application

### "File not found" after rescan
- Update `GCODE_DIR` in `rescan_database.py` to match your G-code folder location
- Ensure the path uses the correct format for your OS

### Slow Performance
- Initial scan of 1000+ files takes several minutes
- Subsequent searches use the database and are fast
- Use filters to reduce the number of displayed results

### Incorrect Type Detection
- Check that the title contains correct keywords (HC, STEP, etc.)
- Test individual file parsing:
  ```bash
  python improved_gcode_parser.py "path/to/file"
  ```
- Review the detection logic priority in this README

### Missing Dimensions
- Ensure G-code follows expected format with comments
- Check that title includes dimensions in standard format
- Review the Details window to see what was extracted

## Database Schema

The SQLite database contains the following fields:

| Column | Type | Description |
|--------|------|-------------|
| program_number | TEXT | Program filename (e.g., "o57000") |
| title | TEXT | Title extracted from G-code |
| spacer_type | TEXT | hub_centric, step, standard, metric_spacer, 2pc_part1, 2pc_part2 |
| outer_diameter | REAL | OD in inches |
| thickness | REAL | Thickness in inches |
| thickness_display | TEXT | Original format (e.g., "10MM" or "1.25") |
| center_bore | REAL | CB in millimeters |
| hub_height | REAL | Hub height in inches (hub-centric only) |
| hub_diameter | REAL | OB in millimeters (hub-centric only) |
| counter_bore_diameter | REAL | Counterbore diameter in millimeters (step only) |
| counter_bore_depth | REAL | Counterbore depth in inches (step only) |
| material | TEXT | Material type (6061-T6, 7075-T6, etc.) |
| validation_status | TEXT | CRITICAL, BORE_WARNING, DIMENSIONAL, WARNING, PASS |
| validation_issues | TEXT | Critical errors (CB/OB way off spec) |
| bore_warnings | TEXT | Bore tolerance warnings |
| dimensional_issues | TEXT | P-code/thickness mismatches |
| cb_from_gcode | REAL | CB extracted from G-code |
| ob_from_gcode | REAL | OB extracted from G-code |
| file_path | TEXT | Full path to G-code file |
| detection_confidence | TEXT | HIGH, MEDIUM, LOW |
| detection_method | TEXT | BOTH, KEYWORD, PATTERN |

## File Structure

```
File organizer/
├── gcode_database_manager.py     # Main GUI application (1660 lines)
├── improved_gcode_parser.py      # G-code parser with validation (1490 lines)
├── rescan_database.py            # Database rescan utility
├── test_status_breakdown.py      # Test script for status counting
├── check_o57604.py               # Test script for specific file
├── check_types_sample.py         # Test script for type detection
├── fix_hc_priority.py            # Script that fixed HC priority (historical)
├── FUTURE_FEATURES.md            # Planned enhancements
├── README.md                     # This file
└── gcode_database.db             # SQLite database (auto-created)
```

## Version History

- **v1.3** (Current) - Added status breakdown counter in results label
- **v1.2** - Fixed type detection to prioritize HC keyword over STEP patterns
- **v1.1** - Added thin-hub shelf pattern detection and CB=Counterbore special case
- **v1.0** - Initial release with 5-color validation system

## Future Enhancements

See `FUTURE_FEATURES.md` for planned features:
- 3D model generation from database dimensions
- Lug and stud generator

## Support

For issues or questions:

1. **Test individual file parsing:**
   ```bash
   python improved_gcode_parser.py "path/to/file"
   ```
   This shows detailed parse information

2. **Check Details window:**
   Double-click a program to see all extracted data and validation issues

3. **Review validation rules:**
   See the "Understanding Validation" section above

4. **Check database contents:**
   Use a SQLite viewer or command line:
   ```bash
   python -c "import sqlite3; conn=sqlite3.connect('gcode_database.db'); print(conn.execute('SELECT COUNT(*) FROM programs').fetchone()[0], 'programs in database')"
   ```

## License

Internal tool for Bronson Generators.

---

**Questions? Run into issues? Check the Troubleshooting section or test individual files to diagnose the problem.**
