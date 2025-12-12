# Decimal MM Thickness Fix (.##MM Pattern)

**Date:** 2025-12-04
**Status:** ✅ COMPLETE

## Problem

Files with thickness notation like `.75MM` (decimal without leading zero) were being incorrectly parsed as `75MM` (2.953 inches) instead of `0.75` inches.

### Example (o50408)
- **Title:** `"5.75IN DIA 66.9/73.1MM .75MM HC"`
- **Detected (before fix):** `75MM` (2.953 inches)
- **Should be:** `0.75` inches
- **Root cause:** Parser pattern `(\d+\.?\d*)` requires at least one digit before the decimal point, so it matched `75` and ignored the `.`

## Root Cause

The regex patterns for MM thickness detection didn't account for decimals without leading zeros:

```python
# OLD patterns (lines 841-844):
(r'(\d+\.?\d*)\s*MM\s+HC', 'MM', True),      # Requires digit before decimal
(r'(\d+\.?\d*)\s*MM\s+THK', 'MM', False),    # Requires digit before decimal
```

These patterns:
1. Required at least one `\d+` (digit) before the optional decimal `\.?`
2. Matched `75` from `.75MM` and ignored the leading `.`
3. Treated `75` as 75MM, converting to 2.953 inches

## Understanding the Pattern

When a title shows `.75MM`:
- **NOT** 75 millimeters (that would be 2.953 inches - way too thick!)
- **NOT** 0.75 millimeters (that would be 0.030 inches - way too thin!)
- **Actually** 0.75 inches (standard spacer thickness)

The `MM` suffix in `.75MM` is a notation error/typo - it should be `.75IN` or just `.75`, but the decimal point clearly indicates it's 0.75 inches, not 75MM.

## Solution

Added new patterns to detect decimal MM without leading zero and treat them as inches:

### Updated Patterns (improved_gcode_parser.py)

```python
thick_patterns = [
    # NEW: Decimal MM patterns (actually inches, despite MM notation)
    (r'\s+\.(\d+)\s*MM\s+HC', 'DECIMAL_MM', True),      # ".75MM HC"
    (r'\s+\.(\d+)\s*MM\s+THK', 'DECIMAL_MM', False),    # ".75MM THK"
    (r'\s+\.(\d+)\s*MM\s*$', 'DECIMAL_MM', False),      # ".75MM" at end
    (r'ID\s+\.(\d+)\s*MM\s+', 'DECIMAL_MM', False),     # "ID .75MM"

    # Existing MM patterns (for normal MM values)
    (r'(\d+\.?\d*)\s*MM\s+HC', 'MM', True),             # "15MM HC"
    (r'(\d+\.?\d*)\s*MM\s+THK', 'MM', False),           # "10MM THK"
    # ...
]
```

### Pattern Priority

The new `.##MM` patterns are placed **before** the regular MM patterns so they match first.

### Parsing Logic

Added `DECIMAL_MM` handling (lines 872-873):

```python
elif unit == 'DECIMAL_MM':
    thickness_val = float('0.' + thickness_val_str)  # ".75" → 0.75 inches
```

The `DECIMAL_MM` unit:
- Converts `.75` to `0.75` (adds leading zero)
- Treats as **inches**, not millimeters (despite the MM in the title)
- Display shows `0.75` (not `75MM`)

## Files Fixed

All **13 files** with `.75MM` pattern corrected:

| Program # | Title | Old Detection | New Detection |
|-----------|-------|---------------|---------------|
| o50274 | 5.75IN DIA 66.1/73.1MM .75MM HC L1 | 75MM (2.953") | 0.75 (0.750") |
| o50286 | 5.75IN DIA 66.1/72MM .75MM HC L1 | 75MM (2.953") | 0.75 (0.750") |
| o50305 | 5.75IN DIA 65.1/73.1MM .75MM HC L1 | 75MM (2.953") | 0.75 (0.750") |
| o50328 | 5.75IN DIA 65.1/71.6MM .75MM HC L1 | 75MM (2.953") | 0.75 (0.750") |
| o50408 | 5.75IN DIA 66.9/73.1MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |
| o50480 | 5.75IN DIA 57.1/72.5MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |
| o58239 | 5.75IN DIA 66.1/73.1MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |
| o58253 | 5.75IN DIA 66.1/72MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |
| o58278 | 5.75IN DIA 65.1/73.1MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |
| o58305 | 5.75IN DIA 65.1/71.6MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |
| o58405 | 5.75IN DIA 66.1/73.1MM .75MM HC L1 | 75MM (2.953") | 0.75 (0.750") |
| o58420 | 5.75IN DIA 66.9/73.1MM .75MM HC L1 | 75MM (2.953") | 0.75 (0.750") |
| o59001 | 5.75IN DIA 64.1/64.1MM .75MM HC | 75MM (2.953") | 0.75 (0.750") |

## Files Modified

1. **improved_gcode_parser.py**
   - Lines 841-848: Added 4 new `DECIMAL_MM` patterns
   - Lines 872-873: Added `DECIMAL_MM` unit handling

2. **fix_decimal_mm_thickness.py** (Created)
   - Re-parsed all 13 affected files
   - Updated thickness and thickness_display fields

## Testing Scripts Created

1. **check_o50408.py** - Initial diagnosis of the issue
2. **find_decimal_mm_issues.py** - First attempt to find affected files
3. **find_space_dot_mm.py** - Found all 13 files with `.##MM` pattern
4. **fix_decimal_mm_thickness.py** - Fixed all 13 files

## Pattern Examples Now Supported

| Pattern | Old Detection | New Detection | Correct? |
|---------|---------------|---------------|----------|
| `.75MM HC` | 75MM (2.953") | 0.75" | ✅ |
| `.5MM THK` | 5MM (0.197") | 0.5" | ✅ |
| `10MM HC` | 10MM (0.394") | 10MM (0.394") | ✅ (unchanged) |
| `15MM THK` | 15MM (0.591") | 15MM (0.591") | ✅ (unchanged) |
| `0.75 THK` | 0.75" | 0.75" | ✅ (unchanged) |

## Impact

✅ **13 files corrected** from massive 2.953" thickness to correct 0.75"
✅ **Parser improved** to handle decimal notation without leading zeros
✅ **No false positives** - regular MM patterns (10MM, 15MM) still work correctly
✅ **Prevents future issues** - new `.##MM` files will parse correctly

## Technical Notes

### Why Treat `.75MM` as Inches?

Physical reasoning:
- **75MM = 2.953 inches** - Way too thick for any normal spacer!
- **0.75MM = 0.030 inches** - Way too thin!
- **0.75 inches = 19.05MM** - Standard spacer thickness ✓

The decimal point `.75` clearly indicates a fractional inch value (3/4 inch), not millimeters. The `MM` suffix appears to be a notation error in the title.

### Pattern Matching Order

Critical that `.##MM` patterns come **before** `##MM` patterns in the list:
1. First try `.75MM` → matches `DECIMAL_MM`, returns 0.75"
2. If no match, try `75MM` → matches `MM`, converts 75/25.4 = 2.95"

Wrong order would always match the second pattern first!

## Conclusion

✅ All files with `.##MM` pattern now parse correctly
✅ Parser handles edge case of decimal without leading zero
✅ No regressions - normal MM patterns still work
✅ 13 files saved from having 4x incorrect thickness!
