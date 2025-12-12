# 2PC and HC Dimension Parsing Fix

**Date:** 2025-12-04
**Status:** ✅ COMPLETE

## Problems Fixed

### 1. 2PC Files with HC Dimensions Not Parsing
**Impact:** 74 files affected

#### Problem
Files with both "2PC" and "HC" in the title (e.g., "13.0 8.7IN/220MM 1. HC 1.5 2PC") were classified as "2PC LUG" instead of parsing HC dimensions. This meant:
- HC thickness/hub patterns were ignored
- Thickness and hub height often swapped or missing
- Hub diameter not detected

#### Example (o13960)
- **Title:** "13.0 8.7IN/220MM 1. HC 1.5 2PC"
- **BEFORE:** thickness=1.5", hub=1.0", hub_diameter=NULL (SWAPPED!)
- **AFTER:** thickness=1.0", hub=1.5", hub_diameter=220.98mm (CORRECT!)

### 2. Decimal HC Patterns Not Recognized
**Impact:** Many files with `.XX HC` or `X. HC` patterns

#### Problem
The HC pattern regex `(\d+\.?\d*)` required a digit BEFORE the decimal point, failing to match:
- **`.75 HC`** → Was matching as "75 HC" (interpreted as 75MM!)
- **`1. HC`** → Not matching at all

#### Examples
- **o63078:** ".75 HC 2PC" → Was parsed as 75MM thickness, now correctly 0.75"
- **o70013:** ".55 HC 2PC" → Was parsed as 55MM thickness, now correctly 0.55"
- **o13643:** "1. HC 1.5" → Was not matching, now correctly 1.0" + 1.5" hub

### 3. Hub Diameter Missing for 13" Round Files
**Impact:** 30+ files with "IN/MM" pattern

#### Problem
Files with hub diameter specified in inches (e.g., "8.7IN/220MM") weren't extracting the hub diameter value.

#### Example
- **Title:** "13.0 8.7IN/220MM 1. HC 1.5 2PC"
- **Pattern:** 8.7IN/220MM means hub_diameter=8.7" (220.98mm)
- **BEFORE:** hub_diameter=NULL
- **AFTER:** hub_diameter=220.98mm ✓

### 4. "2PC" Being Matched as Hub Height
**Impact:** Files like ".75 HC 2PC STUD"

#### Problem
Single HC pattern `r'-*HC\s*(\d*\.?\d+)'` was matching "HC 2" and extracting "2" from "2PC" as the hub height.

#### Example
- **Title:** ".75 HC 2PC STUD"
- **BEFORE:** thickness=0.75", hub=2.0" (2 from "2PC"!)
- **AFTER:** thickness=0.75", hub=0.5" (calculated from drill depth) ✓

## Solutions Implemented

### Fix 1: Remove Spacer Type Restriction for HC Parsing

**Location:** [improved_gcode_parser.py:980-991](improved_gcode_parser.py#L980-L991)

**Before:**
```python
# Hub height (for hub-centric)
if result.spacer_type == 'hub_centric':
    dual_hc_match = re.search(r'(\d+\.?\d*)\s*-*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
```

**After:**
```python
# Hub height extraction - works for ALL files with HC in title (hub-centric, 2PC, etc.)
if 'HC' in title.upper():
    dual_hc_match = re.search(r'(\d+\.?\d*|\d*\.\d+)\s*-*HC\s*(\d+\.?\d*|\d*\.\d+)(?!\s*PC)', title, re.IGNORECASE)
```

**Changes:**
1. Removed `if result.spacer_type == 'hub_centric'` check → HC dimensions extracted for ALL files
2. Updated regex to handle BOTH leading and trailing decimals using alternation: `(\d+\.?\d*|\d*\.\d+)`
   - `\d+\.?\d*` → matches "1." or "1.75" (digit required before decimal)
   - `\d*\.\d+` → matches ".75" or "0.75" (digit required after decimal)
3. Added negative lookahead `(?!\s*PC)` to avoid matching "2" from "2PC"

### Fix 2: Update Single HC Pattern

**Location:** [improved_gcode_parser.py:1010-1016](improved_gcode_parser.py#L1010-L1016)

**Before:**
```python
hub_match = re.search(r'-*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
```

**After:**
```python
hub_match = re.search(r'-*HC\s*(\d+\.?\d*|\d*\.\d+)(?!\s*PC)', title, re.IGNORECASE)
```

**Changes:**
1. Updated regex to handle leading/trailing decimals using same alternation pattern
2. Added negative lookahead `(?!\s*PC)` to prevent matching "2" from "2PC"

### Fix 3: Add "IN/MM" Pattern for Hub Diameter

**Location:** [improved_gcode_parser.py:903-939](improved_gcode_parser.py#L903-L939)

**Added to CB/OB patterns list:**
```python
cb_ob_patterns = [
    r'(\d+\.?\d*)\s*IN\s*/\s*(\d+\.?\d*)\s*MM',  # 8.7IN/220MM (NEW!)
    # ... existing patterns
]
```

**Added special handling:**
```python
# Check for special "IN/MM" pattern (e.g., "8.7IN/220MM")
matched_pattern = cb_ob_match.group(0)
first_has_in = 'IN' in matched_pattern.split('/')[0].upper()
second_has_mm = 'MM' in matched_pattern.split('/')[1].upper()

if first_has_in and second_has_mm:
    # first_val = hub diameter in inches
    # second_val = OB in mm
    result.hub_diameter = first_val * 25.4  # Convert inches to mm
```

## Results

### Files Fixed: 74

**Breakdown:**
- **3 files** with swapped thickness/hub (1. HC pattern)
- **41 files** with missing hub diameter (13" rounds with IN/MM pattern)
- **30 files** with decimal thickness patterns (.XX HC or X. HC)

### Test Results

All test files now parse correctly:

| File | Title | Thickness | Hub Height | Hub Diameter | Status |
|------|-------|-----------|------------|--------------|--------|
| o13960 | 13.0 8.7IN/220MM 1. HC 1.5 2PC | 1.0" | 1.5" | 220.98mm | ✅ PASS |
| o13959 | 13.0 8.7IN/220MM 1. HC .5 2PC | 1.0" | 0.5" | 220.98mm | ✅ PASS |
| o13643 | 13.0 221/220MM 1. HC 1.5 2PC | 1.0" | 1.5" | 221.0mm | ✅ PASS |
| o63078 | 6.25 IN DIA 60.1/73.1 .75 HC 2PC STUD | 0.75" | 0.5" | - | ✅ PASS |
| o70013 | 7.0 IN 71.5MM .55 HC 2PC STUD | 0.55" | 0.45" | - | ✅ PASS |

All drill depths match expected values (thickness + hub + 0.15" breach)!

## Files Modified

1. **[improved_gcode_parser.py](improved_gcode_parser.py)**
   - Line 980-991: Removed spacer type restriction, updated dual HC regex
   - Line 1016: Updated single HC regex with negative lookahead
   - Line 905: Added IN/MM pattern to cb_ob_patterns
   - Line 925-939: Added IN/MM special handling for hub diameter

2. **Database**
   - 74 files updated with correct thickness, hub_height, hub_diameter values
   - Validation statuses updated (many files now PASS instead of CRITICAL)

## Impact on Critical Errors

Before this fix, many of the 74 affected files showed CRITICAL errors due to:
- Swapped thickness/hub causing drill depth mismatches
- Missing dimensions causing validation failures

After this fix:
- Files with correct HC dimensions now validate properly
- Drill depth calculations match title specifications
- Hub diameter now available for 13" round files with IN/MM pattern

## Regex Pattern Explanation

### Decimal Alternation Pattern
```python
(\d+\.?\d*|\d*\.\d+)
```

This pattern uses alternation (`|`) to match EITHER:

1. **`\d+\.?\d*`** - Digit required before decimal
   - Matches: "1", "1.", "1.75"
   - Doesn't match: ".75"

2. **`\d*\.\d+`** - Digit required after decimal
   - Matches: ".75", "0.75"
   - Doesn't match: "1."

Together, they match ALL decimal formats:
- "1" → first pattern
- "1." → first pattern
- ".75" → second pattern
- "1.75" → first pattern (greedy, matches entire number)

### Negative Lookahead
```python
(?!\s*PC)
```

Ensures the matched number is NOT followed by "PC" (with optional whitespace).

**Example:** ".75 HC 2PC STUD"
- Without lookahead: matches ".75 HC 2" → hub=2.0 ✗
- With lookahead: matches ".75 HC" only → hub=default or calculated ✓

## Testing

Created test scripts:
- `test_o13960_parsing.py` - Test specific file parsing
- `test_75hc_pattern.py` - Test decimal HC patterns
- `test_negative_lookahead.py` - Test regex pattern behavior
- `analyze_2pc_hc_files.py` - Analyze all affected files
- `rescan_2pc_hc_files.py` - Rescan and update database

## Rescan Results

```
Files processed: 140
  Successfully rescanned: 140
  Values changed (fixed): 74
  Errors: 0
```

## Conclusion

✅ 2PC files with HC dimensions now parse correctly
✅ Decimal HC patterns (.75 HC, 1. HC) now work
✅ 13.0 round files now extract hub diameter from "IN/MM" pattern
✅ Negative lookahead prevents "2PC" from being matched as hub height
✅ 74 files fixed with correct dimensions
✅ All test files pass validation

**Restart the application to see updated values in the GUI.**
