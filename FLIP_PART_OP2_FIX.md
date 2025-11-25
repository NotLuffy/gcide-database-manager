# FLIP PART OP2 Detection Fix

## Issue Discovered

File o61541 was showing a thickness error even though it had correct two-operation drilling:
- **Title**: "6.00 IN DIA 70.6/70.3 ID 4.00 HC"
- **Thickness**: 4.00"
- **Hub**: 0.5" (default)
- **Expected drill**: 4.00 + 0.50 + 0.15 = 4.65"
- **Actual drilling**: OP1 Z-4.15 + OP2 Z-0.65 = 4.80" ✓

**Error shown**: "THICKNESS ERROR: Spec=4.00", Calculated from drill=3.50" (-0.500")"

## Root Cause

The drill depth extraction function (`_extract_drill_depth`) only looked for these OP2 markers:
- `"OP2"` in line
- `"(OP2)"` in line

But **did NOT check for `"FLIP"` or `"FLIP PART"`**, which are very common OP2 markers in the codebase.

File o61541 uses `"(FLIP PART)"` on line 70 to mark OP2, so the OP2 drill (Z-0.65) was not being detected.

## Fix Applied

**File**: [improved_gcode_parser.py](improved_gcode_parser.py:1619)
**Line**: 1619

**Before**:
```python
# Detect OP2 section
if 'OP2' in line_upper or '(OP2)' in line_upper:
    in_op2 = True
```

**After**:
```python
# Detect OP2 section
# Check for various OP2 markers: "OP2", "(OP2)", "FLIP PART", "FLIP", etc.
if 'OP2' in line_upper or '(OP2)' in line_upper or 'FLIP' in line_upper:
    in_op2 = True
```

## Test Results

### o61541 - FIXED ✓

**Before**:
- Drill Depth: 4.15" (missing OP2 drill)
- Hub Height: 0.50" (default)
- Error: THICKNESS ERROR (-0.500")

**After**:
- Drill Depth: 4.80" (4.15 + 0.65) ✓
- Hub Height: 0.65" (calculated from drill depth)
- No errors ✓

## Impact Estimation

### Files Likely Affected

Based on database query, files with:
- 4.0" thickness
- Exactly -0.500" shortage
- Hub-centric type

**Likely fixed by this change**:
- o61541 (6.00" round) ✓ CONFIRMED FIXED
- o58718 (5.75" round) - Needs verification
- o70039 (7.0" round) - Needs verification
- o90157 (9.5" round) - Needs verification
- o90173 (9.5" round) - Needs verification

**Total estimated**: 5-10 files

### Files NOT Fixed

Files with different shortage amounts likely have:
- Real under-drilling issues (need manual G-code review)
- Incorrect title specifications
- Different root causes

Examples:
- o13273: -0.350" (real under-drilling)
- o13009: -1.000" (missing OP2 drill entirely)
- o58442: -1.050" (real under-drilling)

## Consistency with Rest of Parser

This fix aligns the `_extract_drill_depth` function with the OP2 detection used elsewhere in the parser:

**Other parts of parser** (line 576):
```python
elif 'FLIP' in line_upper:
    in_flip = True
```

**Now drill extraction** (line 1619):
```python
if 'OP2' in line_upper or '(OP2)' in line_upper or 'FLIP' in line_upper:
    in_op2 = True
```

Both now consistently detect "FLIP" as an OP2 marker.

## OP2 Marker Patterns in Codebase

Common OP2 markers found in G-code files:
1. `(OP2)` - Explicit OP2 label
2. `OP2` - Plain text OP2
3. `(FLIP PART)` - Part flipping instruction
4. `(FLIP)` - Short flip marker
5. `FLIP PART` - Without parentheses
6. `(REMOVE & CLEAN JAWS)` followed by `(FLIP PART)` - Common pattern

The fix now catches all "FLIP" variants.

## Two-Operation Drilling Logic

The parser detects two-operation drilling when:
1. OP1 has a drill between 4.1" and 4.2" (typically 4.15")
2. OP2 has a drill operation (any depth)
3. Total depth = OP1 + OP2 (direct sum)

**Example** (o61541):
- OP1: Z-4.15 (max machine depth)
- OP2: Z-0.65 (remaining depth)
- Total: 4.80"
- Part spec: 4.0" thick + 0.5" hub + 0.15" clearance = 4.65"
- Overage: +0.15" (acceptable for punch-through)

## Recommendations

### 1. Verify Other Affected Files

Check files showing -0.500" shortage with 4.0" thickness:
```bash
python improved_gcode_parser.py "path/to/o58718"
python improved_gcode_parser.py "path/to/o70039"
python improved_gcode_parser.py "path/to/o90157"
python improved_gcode_parser.py "path/to/o90173"
```

If they now show correct drill depths → fixed!
If they still show errors → different root cause

### 2. Rescan Database

Run full database rescan to apply fix:
```bash
python rescan_all_programs.py
```

Expected results:
- **5-10 files** move from CRITICAL → PASS
- Drill depths now include OP2 operations
- Hub heights may update (calculated from drill depth)

### 3. Review Remaining Thickness Errors

After rescan, remaining thickness errors likely indicate:
- Real under-drilling (G-code needs fixing)
- Title specification errors
- Other edge cases requiring manual review

## Conclusion

The "FLIP PART" OP2 marker was not being detected in drill depth extraction, causing the parser to miss OP2 drilling operations.

**Fix applied**: Added `'FLIP' in line_upper` to OP2 detection

**Impact**: 5-10 files estimated to move from CRITICAL → PASS

**Consistency**: Now matches OP2 detection used elsewhere in parser

**Next action**: Rescan database to apply fix across all files
