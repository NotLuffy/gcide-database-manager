# --HC Thickness Detection Fix

**Date:** 2025-12-04
**Status:** ✅ COMPLETE

## Problem

Files with the pattern `##.## --HC ##.##` or `##.## -HC ##.##` were incorrectly parsing thickness and hub height values.

### Example Issue
**o50240:** `"5.75IN DIA 66.6/57.1    1.0 --HC 0.50"`
- Expected: thickness = 1.0, hub_height = 0.50
- Detected (before fix): thickness = 0.50, hub_height = 0.99

The parser was:
1. Not detecting the dashes in `--HC` and `-HC`
2. Capturing the wrong values (hub height instead of thickness)

## Root Cause

The regex pattern for detecting the dual HC format didn't account for dashes:
```python
# OLD (line 978):
dual_hc_match = re.search(r'(\d+\.?\d*)\s*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
```

This pattern didn't match `--HC` or `-HC`, causing the parser to:
1. Skip the proper thickness/hub height extraction
2. Fall back to other patterns that captured incorrect values

## Solution

Updated two regex patterns in [improved_gcode_parser.py](improved_gcode_parser.py):

### 1. Dual HC Pattern (Line 978)
```python
# NEW:
dual_hc_match = re.search(r'(\d+\.?\d*)\s*-*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
```
- Added `-*` to match zero or more dashes before HC
- Now matches: `HC`, `-HC`, `--HC`

### 2. Single Hub Height Pattern (Line 1000)
```python
# NEW:
hub_match = re.search(r'-*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
```
- Added `-*` to match optional dashes before HC
- Ensures hub height is detected even with dashes

## Files Fixed

### Direct Fixes (Re-parsed with updated parser)
1. **o50240:** `"5.75IN DIA 66.6/57.1    1.0 --HC 0.50"`
   - Fixed: thickness = 1.0, hub_height = 0.50

2. **o80056:** `"8IN DIA 106.1 /108 1.00 --HC 0.50"`
   - Fixed: thickness = 1.0, hub_height = 0.50

3. **o95500:** `"9.5IN 124.1-128 MM  6.0 -HC 1.0"`
   - Fixed: thickness = 6.0, hub_height = 1.0

4. **o96035:** `"9.5IN  125/142 MM ID 1.00 -HC 1."`
   - Fixed: thickness = 1.0, hub_height = 1.0

### Verification Results

Checked all 245 files with `--HC` or `-HC` in title:
- ✅ **20 files** with `##.## --HC ##.##` format - all parsing correctly
- ✅ **225 files** with other --HC variants (e.g., `"1.25MM --HC"`) - parsing correctly
- ✅ **0 files** with issues remaining

## Pattern Formats Supported

The parser now correctly handles all these formats:

1. **Dual value with dashes:**
   - `"1.0 --HC 0.50"` → thickness = 1.0, hub = 0.50
   - `"1.0 -HC 0.50"` → thickness = 1.0, hub = 0.50
   - `"6.0 -HC 1.0"` → thickness = 6.0, hub = 1.0

2. **Dual value without dashes:**
   - `"1.0 HC 0.50"` → thickness = 1.0, hub = 0.50
   - `"1.5 HC 1.0"` → thickness = 1.5, hub = 1.0

3. **Single value (thickness only):**
   - `"1.25MM --HC"` → thickness = 1.25 (from MM), hub = 0.50 (default)
   - `"1.0 --HC"` → thickness = 1.0, hub = 0.50 (default)
   - `"1.25IN THK --HCH"` → thickness = 1.25 (from THK), hub = 0.50 (default)

## Files Modified

1. **improved_gcode_parser.py**
   - Line 978: Updated dual HC pattern
   - Line 1000: Updated single hub height pattern

2. **fix_swapped_thickness.py** (Created)
   - Script to re-parse and fix the 3 initially identified files

3. **check_o96035.py** (Created)
   - Script to fix the 4th file found during verification

## Testing Scripts Created

1. **check_o50240.py** - Initial problem diagnosis
2. **find_wrong_thickness.py** - Found 3 files with swapped values
3. **find_all_hc_thickness_issues.py** - Comprehensive scan of all --HC files
4. **check_other_hc_files.py** - Analyzed non-standard --HC formats

## Impact

✅ **4 files corrected** with proper thickness/hub height values
✅ **245 files verified** to ensure all --HC variants parse correctly
✅ **Parser improved** to handle all --HC, -HC, and HC variants

## Next Steps

The fix is complete for --HC thickness detection. The user also mentioned there are other files missing thickness detection entirely. These files should be investigated separately to identify additional thickness detection patterns.
