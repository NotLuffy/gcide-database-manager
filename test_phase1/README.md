# Phase 1 Test Environment - Pre-Import File Scanner

## Overview

This is an **isolated test environment** for Phase 1 of the development roadmap. It allows you to test the Pre-Import File Scanner feature without affecting the main application or database.

## Features Being Tested

1. **Pre-Import File Scanner**
   - Scan any G-code file before importing
   - Detect warnings and errors
   - Show program information and dimensions
   - View issues organized by category
   - Export scan reports

## Files in This Directory

```
test_phase1/
├── README.md                    # This file
├── file_scanner_test.py         # Main test application
├── test_files/                  # Sample test files (optional)
│   └── (place test .nc files here)
└── test_results/                # Exported scan reports
    └── (scan reports saved here)
```

## How to Run

### Method 1: Direct Python Execution

```bash
cd "l:\My Drive\Home\File organizer\test_phase1"
python file_scanner_test.py
```

### Method 2: From Parent Directory

```bash
cd "l:\My Drive\Home\File organizer"
python test_phase1/file_scanner_test.py
```

## How to Use

1. **Launch the test application** (see above)

2. **Click "Browse..."** to select a G-code file
   - You can browse to the `repository/` folder to test with real files
   - Or place test files in `test_files/` folder

3. **Click "🔍 Scan File"** to scan the selected file

4. **Review the results** in three tabs:
   - **Summary**: Overview of scan results with color-coded issues
   - **Issues Details**: Tree view of all warnings and errors grouped by category
   - **Raw Parse Data**: Complete parse result data for debugging

5. **Optional actions**:
   - **📄 View File**: Opens the file in your default text editor
   - **💾 Export Report**: Save scan results to a text file

## What Gets Detected

### Program Information
- Program number
- Title
- Round size (OD)
- Spacer type
- Material
- Tools used
- P-codes found

### Dimensions
- Outer diameter (OD)
- Thickness
- Center bore (CB)
- Hub diameter (OB)
- Hub height
- Counter bore diameter
- Counter bore depth

### Issues (Color-Coded)

#### 🔴 Errors (Red)
- Critical validation issues
- Parse errors
- Syntax errors

#### ⚠️ Warnings (Orange/Yellow)
- **Tool Home Position**: Z position too low for round size
- **Bore Dimensions**: CB/OB conflicts or mismatches
- **Dimensional**: P-code/thickness conflicts
- **Validation**: Sequence issues, missing commands

#### 🔵 Info (Blue)
- Missing dimensions (not critical but noted)

## Testing Scenarios

### Test Case 1: Clean File (No Issues)
- Expected: ✓ No issues found
- All dimensions detected
- Proper tool home positions

### Test Case 2: Tool Home Warning
- File with Z-13.0 tool home on 13" OD part (should be Z-10.0)
- Expected: ⚠️ Warning about tool home position

### Test Case 3: Missing Dimensions
- File without dimensions in title
- Expected: 🔵 Info messages about missing data

### Test Case 4: Invalid G-code
- Malformed or incomplete G-code file
- Expected: 🔴 Parse error

### Test Case 5: Multiple Issues
- File with several warnings of different types
- Expected: All issues listed and grouped by category

## Integration with Main Application

⚠️ **This is a TEST ENVIRONMENT ONLY**

- Does **NOT** modify the database
- Does **NOT** import files
- Does **NOT** affect the main application
- Safe to test with any files

Once testing is complete and the feature is validated, the scanner code will be integrated into the main `gcode_database_manager.py` application.

## What to Test

### Functionality Tests
- [ ] Can browse and select files
- [ ] Scan button works
- [ ] Results display correctly
- [ ] Color coding works (green/orange/red)
- [ ] All three tabs show data
- [ ] Issues grouped by category
- [ ] View file opens in editor
- [ ] Export report creates file

### Edge Cases
- [ ] Non-existent file
- [ ] Empty file
- [ ] Invalid G-code
- [ ] File without dimensions
- [ ] File with multiple warnings
- [ ] Very large file (1000+ lines)

### Performance
- [ ] Scan completes in reasonable time (< 5 seconds)
- [ ] UI remains responsive during scan
- [ ] Can scan multiple files consecutively

## Known Limitations

1. **Line Numbers**: Currently not extracted from warnings (showing `None`)
   - Future enhancement: Parse line numbers from issue messages
   - Future enhancement: Click issue to jump to line in file

2. **Auto-Fix**: Not implemented in test environment
   - Will be added when integrating into main app

3. **Batch Scanning**: Only scans one file at a time
   - Could add batch scanning in future

## Sample Test Files

Place test files in `test_files/` directory. Examples:

- `o13002.nc` - Standard spacer (should be clean)
- `o10247.nc` - File with tool home warning
- `o57139.nc` - Hub-centric spacer
- `invalid.nc` - Malformed file for error testing

## Export Reports

Scan reports are saved to `test_results/` by default. Report format:

```
================================================================================
G-CODE FILE SCAN RESULTS
================================================================================

File: o13002.nc
Path: l:\My Drive\Home\File organizer\repository\o13002.nc

✓ File parsed successfully

PROGRAM INFORMATION
--------------------------------------------------------------------------------
  Program Number:  o13002
  Title:           13.0 142/220MM 2.0 HC .5
  Round Size:      13.0"
  Spacer Type:     hub_centric
  Material:        6061-T6
  ...

[Full scan results with all details]
```

## Troubleshooting

### Import Error: Can't find improved_gcode_parser
**Solution**: Make sure you're running from the test_phase1 directory or that the parent directory path is correct.

### No Files Show When Browsing
**Solution**: The browse dialog defaults to the `repository/` folder if it exists. Navigate to where your test files are located.

### Scan Takes Too Long
**Solution**: The parser analyzes the entire file. Large files (5000+ lines) may take 5-10 seconds. This is normal.

### Colors Don't Show
**Solution**: The colored text uses tkinter text tags. If you're on a system with limited color support, the text may appear without colors but functionality remains the same.

## Feedback & Issues

As you test, note:
- [ ] What works well
- [ ] What's confusing
- [ ] What's missing
- [ ] Any bugs or errors
- [ ] Feature requests

## Next Steps

After successful testing:

1. **Phase 1.1 Complete** ✓ Pre-Import Scanner tested
2. **Phase 1.2**: Add Database File Monitor
3. **Phase 1.3**: Add Safety Warnings
4. **Phase 1.4**: Add Duplicate with Scan
5. **Integration**: Move scanner into main application

## Version

- **Version**: 1.0 (Initial test implementation)
- **Date**: 2026-02-04
- **Status**: ✅ Ready for testing
- **Phase**: Phase 1.1 - Pre-Import File Scanner

---

**Remember**: This is a safe, isolated test environment. Nothing you do here affects the main database or application!
