# Column Mapping Verification Report

**Date:** 2025-11-18
**Status:** ✓ VERIFIED - All mappings correct

## Database Schema

The database has 27 columns (indices 0-26):

| Index | Column Name | Type | Used In Tree | Used In Details |
|-------|-------------|------|--------------|-----------------|
| 0 | program_number | TEXT | ✓ | ✓ |
| 1 | title | TEXT | ✓ | ✓ |
| 2 | spacer_type | TEXT | ✓ | ✓ |
| 3 | outer_diameter | REAL | ✓ | ✓ |
| 4 | thickness | REAL | ✓ | ✓ |
| 5 | thickness_display | TEXT | ✓ | ✓ |
| 6 | center_bore | REAL | ✓ | ✓ |
| 7 | hub_height | REAL | ✓ | ✓ |
| 8 | hub_diameter | REAL | ✓ | ✓ |
| 9 | counter_bore_diameter | REAL | ✓ | ✓ |
| 10 | counter_bore_depth | REAL | - | ✓ |
| 11 | paired_program | TEXT | - | ✓ |
| 12 | material | TEXT | ✓ | ✓ |
| 13 | notes | TEXT | - | ✓ |
| 14 | date_created | TEXT | - | ✓ |
| 15 | last_modified | TEXT | - | ✓ |
| 16 | file_path | TEXT | ✓ | ✓ |
| 17 | detection_confidence | TEXT | - | ✓ |
| 18 | detection_method | TEXT | - | ✓ |
| 19 | validation_status | TEXT | ✓ | ✓ |
| 20 | validation_issues | TEXT | - | ✓ |
| 21 | validation_warnings | TEXT | - | ✓ |
| 22 | cb_from_gcode | REAL | - | ✓ |
| 23 | ob_from_gcode | REAL | - | ✓ |
| 24 | bore_warnings | TEXT | - | ✓ |
| 25 | dimensional_issues | TEXT | - | ✓ |
| 26 | lathe | TEXT | ✓ | ✓ |

## Tree View Column Order

The GUI displays 13 columns in this order:

1. **Program #** - `row[0]` - program_number
2. **Title** - `row[1]` - title
3. **Type** - `row[2]` - spacer_type
4. **Lathe** - `row[26]` - lathe ⭐ NEW
5. **OD** - `row[3]` - outer_diameter (formatted)
6. **Thick** - `row[5]` or `row[4]` - thickness_display or thickness
7. **CB** - `row[6]` - center_bore (formatted)
8. **Hub H** - `row[7]` - hub_height (hub_centric only)
9. **Hub D** - `row[8]` - hub_diameter (hub_centric only)
10. **CB Bore** - `row[9]` - counter_bore_diameter (step only)
11. **Material** - `row[12]` - material
12. **Status** - `row[19]` - validation_status
13. **File** - `os.path.basename(row[16])` - filename from file_path

## Details Window Display

### Basic Fields Section (0-16)
Displays program metadata in order:
- Program Number (0)
- Title (1)
- Spacer Type (2)
- Outer Diameter (3)
- Thickness (4)
- Thickness Display (5)
- Center Bore (6)
- Hub Height (7)
- Hub Diameter (8)
- Counter Bore Diameter (9)
- Counter Bore Depth (10)
- Paired Program (11)
- Material (12)
- Notes (13)
- Date Created (14)
- Last Modified (15)
- File Path (16)

### Validation Section (17-26)
Displays validation and detection info:
- Detection Confidence (17)
- Detection Method (18)
- **Lathe (26)** ⭐ NEW - Shows L1, L2, L3, or L2/L3
- Validation Status (19)
- CB from G-code (22)
- OB from G-code (23)
- Critical Issues (20) - JSON list
- Bore Warnings (24) - JSON list
- Dimensional Issues (25) - JSON list
- Warnings (21) - JSON list

## Test Results

### Sample Records Tested

**o57000** (hub_centric, L1):
- Tree: `o57000 | 5.75 70.3MM/73.1MM 10MM HC | hub_centric | L1 | 5.750 | 10MM | 70.3 | 0.50 | 73.1 | N/A | 6061-T6 | PASS | o57000`
- Details: All fields display correctly including Lathe: L1

**o57001** (step, L1):
- Tree: `o57001 | 5.75IN DIA 71/60MM ID 1.5 XX | step | L1 | 5.750 | 1.5 | 60.0 | N/A | N/A | 71.0 | 6061-T6 | PASS | o57001`
- Details: All fields display correctly including Lathe: L1

**o58179** (hub_centric, L2/L3):
- Tree: `o58179 | 7.0 IN DIA  60.1-83.4MM 1.50 HC | hub_centric | L2/L3 | 7.000 | 1.5 | 60.1 | 0.50 | 83.4 | N/A | 6061-T6 | CRITICAL | o58179`
- Details: All fields display correctly including Lathe: L2/L3

## Lathe Distribution

Total programs: 814
- **L1**: 790 programs (5.75", 6.0", 6.25", 6.5")
- **L2/L3**: 1 program (7.0", 7.5", 8.0", 8.5")
- **Unknown**: 23 programs (no OD or non-standard OD)

## Files Modified

1. **improved_gcode_parser.py**
   - Added lathe field to GCodeParseResult
   - Added lathe assignment logic
   - Added L2/L3 P-code table
   - Updated P-code validation

2. **gcode_database_manager.py**
   - Added lathe column to database schema
   - Added lathe to ProgramRecord dataclass
   - Updated INSERT/UPDATE statements
   - Added lathe to tree view display (column 4)
   - Added lathe to DetailsWindow validation section

3. **rescan_database.py**
   - Updated to populate lathe field during rescan

## Verification

✓ Database schema correct (27 columns)
✓ Tree view extraction correct (13 columns)
✓ Details window display correct (basic + validation fields)
✓ Lathe assignments working (L1, L2, L3, L2/L3)
✓ All test records display correctly
✓ Database rescan successful (814 programs updated)

---

**All column mappings verified and working correctly!**
