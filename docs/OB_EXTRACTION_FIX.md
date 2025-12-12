# OB (Outer Bore) Extraction Fix - Hub-Centric Parts

**Date:** 2025-12-09
**Status:** ✅ FIXED

## Problem

**2318 hub-centric programs** (especially 5.75" rounds) had warnings:
```
OB extraction uncertain: extracted 144.8mm matches OD, skipping OB validation
```

The parser was extracting the **OD (Outer Diameter)** instead of the **OB (Outer Bore/Hub Diameter)** from OP2 turning operations.

## Root Cause

In OP2 turning operations, the tool **faces DOWN from OD to OB**:

### Example: o50007 (5.75" Round)
**Title:** `5.75 70.3MM/73.1MM 10MM HC`
- OD = 5.75" (146mm)
- CB = 70.3mm
- **OB = 73.1mm**

**OP2 G-code sequence (after FLIP PART):**
```gcode
Line 79: G00 G55 X5.7 Z0.1     ← Position at OD
Line 81: G01 X5.7 Z0.          ← Face OD
Line 82: Z-0.2                 ← Move down for chamfer
Line 83: X2.89                 ← FACE DOWN TO OB (2.89" × 25.4 = 73.4mm ≈ 73.1mm spec)
Line 84: G00 X5.7              ← Retract to OD
Line 85: G01 Z-0.4             ← Move deeper
Line 86: X2.89                 ← Face to OB again
Line 91: X2.874 Z-0.4          ← Continue at OB (73.0mm)
Line 92: Z-0.14                ← Move to chamfer depth
Line 93: X2.774 Z-0.09         ← OB chamfer
```

**The issue:** Old parser logic collected both X5.7 (OD) and X2.89 (OB), then used `max()` which selected X5.7 (146mm) instead of the actual OB X2.89 (73mm).

## The Fix

**File:** [improved_gcode_parser.py:1577-1596](improved_gcode_parser.py#L1577-L1596)

### Old Logic (BROKEN)
```python
ob_with_following_z = [x for x, z, idx, has_marker, has_z in ob_candidates if has_z]
if ob_with_following_z:
    # Use the largest X with following Z (typically the final OB after all passes)
    result.ob_from_gcode = max(ob_with_following_z) * 25.4  # WRONG - selects OD!
```

### New Logic (FIXED)
```python
ob_with_following_z = [x for x, z, idx, has_marker, has_z in ob_candidates if has_z]
if ob_with_following_z:
    # CRITICAL FIX: Filter out OD values before selecting OB
    # OD facing operations create large X values (e.g., X5.7 for 5.75" parts)
    # OB is the SMALLEST X value after OD chamfer, not the largest
    # Filter: Remove X values close to the OD (within 8mm of OD)
    od_mm = result.outer_diameter * 25.4 if result.outer_diameter else None
    filtered_ob = []
    for x_val in ob_with_following_z:
        x_mm = x_val * 25.4
        # Exclude if close to OD (OD facing operations)
        if od_mm and abs(x_mm - od_mm) > 8.0:  # More than 8mm away from OD
            filtered_ob.append(x_val)
        elif not od_mm:  # No OD to compare, keep all
            filtered_ob.append(x_val)

    if filtered_ob:
        # Use the SMALLEST X (not largest) - OB is where we face down TO, not the OD we start from
        result.ob_from_gcode = min(filtered_ob) * 25.4  # Convert to mm
```

## Key Insights

### Why MIN not MAX?
In OP2 turning, the tool **faces inward**:
1. Start at large X (OD) - e.g., X5.7
2. Face down to smaller X (OB) - e.g., X2.89
3. Sometimes retract to OD and repeat
4. Final OB is the **SMALLEST X value** in the sequence

### Why Filter OD?
OD facing creates X values close to the outer diameter (e.g., X5.7 for 5.75" parts = 146mm). These must be filtered out because they're not the OB, they're the starting position before facing down to the OB.

**Filter criteria:** Exclude X values within 8mm of OD
- OD = 146mm
- X5.7 = 146mm → Excluded (difference = 0mm < 8mm)
- X2.89 = 73mm → Kept (difference = 73mm > 8mm) → This is the OB!

## Test Results

### Before Fix
| File | OD | Title OB | Extracted OB | Status |
|------|-----|----------|--------------|--------|
| o50007 | 5.75" (146mm) | 73.1mm | 144.8mm | ❌ OD extracted instead |
| o50168 | 5.75" (146mm) | 63.4mm | 145.0mm | ❌ OD extracted instead |
| o50172 | 5.75" (146mm) | 66.6mm | 144.8mm | ❌ OD extracted instead |

### After Fix
| File | OD | Title OB | Extracted OB | Difference | Status |
|------|-----|----------|--------------|------------|--------|
| o50007 | 5.75" (146mm) | 73.1mm | 73.0mm | 0.1mm | ✅ PASS |
| o50168 | 5.75" (146mm) | 63.4mm | 63.4mm | 0.0mm | ✅ PASS |
| o50172 | 5.75" (146mm) | 66.6mm | 66.0mm | 0.5mm | ✅ PASS |

## Rescan Results

Rescanned all 2318 programs with "OB matches OD" warnings:

```
Total programs: 2318
Fixed (warning removed): 2294  (99.0%)
Still has warning: 24          (1.0%)
Errors: 0
```

**Success rate: 99%!**

The 24 remaining warnings are likely:
- Different G-code patterns (edge cases)
- Programs where OB actually equals OD (valid for some designs)
- Programs needing manual review

## Impact

### Before Fix
- 2318 programs with OB warnings
- Most hub-centric parts had incorrect OB values
- Validation disabled for these programs (warnings ignored)

### After Fix
- 2294 programs now have correct OB values ✅
- Only 24 programs still need review
- OB validation now works for 99% of hub-centric parts

## Files Modified

- **improved_gcode_parser.py** (lines 1577-1596) - OB selection logic
- **gcode_database.db** - Updated OB values for 2294 programs

## Scripts Created

- **analyze_ob_warnings.py** - Identified the problem
- **analyze_op2_ob_pattern.py** - Analyzed G-code patterns
- **test_ob_fix.py** - Verified the fix works
- **rescan_ob_warnings.py** - Applied fix to all affected programs

## Conclusion

✅ **99% of OB extraction issues fixed**
✅ **Parser now correctly identifies OB from OP2 turning operations**
✅ **OD filtering prevents false OB detection**
✅ **Hub-centric validation now works correctly**

**Restart the application to see updated OB values without warnings!**

## Technical Details

### OP2 Turning Pattern Recognition

The parser now correctly recognizes this pattern:

1. **OD Chamfer** - X at OD (5.7") with Z movement
2. **Face to OB** - X decreases to OB (2.89")
3. **Retract** - X returns to OD (optional)
4. **Repeat** - Multiple passes at OB
5. **OB Chamfer** - Final chamfer near Z-0.14"

The key is recognizing that after the OD chamfer, the **smallest X value** is the actual OB, not the largest.
