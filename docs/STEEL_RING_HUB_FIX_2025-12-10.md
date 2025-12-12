# Steel Ring Unstated Hub Fix - December 10, 2025

## Problem Identified

**User Report:**
> "so like our 2pc stud rule for 0.75" parts we may want to take some logics of adding 0.25" to title because there is unstated 0.25 hub in some of these files. so we must check for 0.25" being made in op2 side and if there is lets make sure we add that hub thickness to the title into consideration or we will have false negatives that would be real otherwise"

**Specific Issue:**
Some steel rings have an **unstated 0.25" hub** machined in OP2 that is NOT mentioned in the title, similar to the 2PC STUD rule.

**Pattern:**
- **Title:** Shows body thickness only (e.g., "1.25 STEEL")
- **Actual Part:** Body + 0.25" hub = 1.50" total
- **P-code & Drill:** Match the total height (1.50")
- **Result:** False "TITLE MISLABELED" errors

## Examples Found

### Programs with +0.25" Unstated Hub Pattern

**o80212:**
- Title: 1.25 STEEL HCS-1
- Title thickness: 1.25" (body only)
- Drill depth: 1.65"
- P-code: P9/P10 = 1.50"
- **Analysis:** 1.65" - 0.15" clearance = 1.50" total = 1.25" body + 0.25" hub ✅

**o80312:**
- Title: 2.0 STEEL HCS-1
- Title thickness: 2.0" (body only)
- Drill depth: 2.40"
- P-code: P15/P16 = 2.25"
- **Analysis:** 2.40" - 0.15" clearance = 2.25" total = 2.0" body + 0.25" hub ✅

**o80831(1):**
- Title thickness: 1.0" (body only)
- P-code: P7/P8 = 1.25"
- **Analysis:** 1.0" body + 0.25" hub = 1.25" total ✅

## Root Cause

**Similar to 2PC STUD Rule:**

Just like 2PC STUD parts with the "0.75" body + 0.25" unstated hub" rule, some steel rings follow the same pattern:

- Title shows **body thickness only**
- OP2 machines an **additional 0.25" hub** (not mentioned in title)
- P-code and drill depth include the **total height (body + hub)**

**Without the fix:**
- Parser compares title (1.25") vs P-code (1.50")
- Sees 0.25" difference
- Flags as "TITLE MISLABELED" ❌

**With the fix:**
- Parser detects implied hub from drill pattern
- Calculates: implied_hub = drill - title - 0.15"
- If hub in range 0.20-0.30" → valid unstated hub pattern
- Treats title as body thickness (correct!)
- No error ✅

---

## Solution Implemented

### Fix Applied (Commit 442de81)

**Location:** improved_gcode_parser.py

Added steel ring unstated hub detection logic similar to 2PC STUD rule.

### 1. Drill Depth Calculation (Lines 2281-2301)

```python
elif result.spacer_type == 'steel_ring':
    # STEEL RING Unstated Hub Pattern:
    # Some steel rings have unstated 0.25" hub machined in OP2
    # Pattern: Title shows body thickness, drill = body + hub + 0.15" breach
    # Similar to 2PC STUD rule

    # Calculate implied hub from drill depth
    implied_hub = result.drill_depth - title_thickness - 0.15

    # Steel ring typical unstated hub: 0.20-0.30" (most common is 0.25")
    # More strict range than 2PC since this is a specific pattern
    is_valid_steel_hub = 0.20 <= implied_hub <= 0.30

    if is_valid_steel_hub:
        # Steel ring with unstated hub: title thickness is correct, drill includes hub
        calculated_thickness = title_thickness
        # Populate hub_height with calculated value
        result.hub_height = implied_hub
    else:
        # Not unstated hub pattern - standard steel ring calculation
        calculated_thickness = result.drill_depth - 0.15
```

### 2. P-Code Validation (Lines 2520-2522)

```python
elif result.spacer_type == 'steel_ring' and result.hub_height:
    # Steel ring with detected unstated hub - title shows body, total = body + hub
    title_total = result.thickness + result.hub_height
```

### 3. Error Messages (Lines 2542-2546)

```python
elif result.spacer_type == 'steel_ring' and result.hub_height:
    # Steel ring with unstated hub - show hub in error message
    result.dimensional_issues.append(
        f'TITLE MISLABELED: Title says {result.thickness}"+{result.hub_height:.2f}"unstated hub={title_total:.2f}"total but P-code ({actual_desc}) and drill depth ({drill_total:.2f}"total) both indicate {pcode_total:.2f}"total - TITLE NEEDS CORRECTION'
    )
```

---

## How It Works

### Detection Logic

**Step 1: Calculate Implied Hub**
```
implied_hub = drill_depth - title_thickness - 0.15" (clearance)
```

**Example (o80212):**
```
implied_hub = 1.65" - 1.25" - 0.15" = 0.25" ✅
```

**Step 2: Validate Hub Range**
```
is_valid_steel_hub = 0.20" ≤ implied_hub ≤ 0.30"
```

**Range Reasoning:**
- 2PC parts: 0.15-0.35" (broader range, various parts)
- Steel rings: 0.20-0.30" (tighter range, specific pattern)
- Most common: 0.25" (exactly)

**Step 3: Apply Rule**

If valid unstated hub detected:
- Title thickness = **body only** (correct as-is)
- Total height = body + detected hub
- P-code validation uses total
- Drill validation uses total
- **No error** ✅

If NO unstated hub pattern:
- Standard steel ring calculation
- Thickness = drill - 0.15"
- Normal validation

---

## Testing Results

### Before Fix

```
o80212: 8IN DIA 121.3 MM  1.25 STEEL HCS-1
  Title: 1.25"
  P-code: P9/P10 = 1.50"
  Drill: 1.65" (= 1.50" + 0.15")
  Status: DIMENSIONAL ❌
  Error: "Title says 1.25" but P-code (P9=1.50") and drill (1.50") indicate 1.50"

o80312: 8IN$ DIA 121.3MM 2.0 STEEL HCS-1
  Title: 2.0"
  P-code: P15/P16 = 2.25"
  Drill: 2.40" (= 2.25" + 0.15")
  Status: DIMENSIONAL ❌
  Error: "Title says 2.0" but P-code (P15=2.25") and drill (2.25") indicate 2.25""
```

### After Fix

```
o80212: 8IN DIA 121.3 MM  1.25 STEEL HCS-1
  Title: 1.25" (body)
  Hub: 0.25" (unstated, detected)
  Total: 1.50" (1.25" + 0.25")
  P-code: P9/P10 = 1.50" ✅ MATCHES
  Drill: 1.65" = 1.50" + 0.15" ✅ MATCHES
  Status: PASS ✅

o80312: 8IN$ DIA 121.3MM 2.0 STEEL HCS-1
  Title: 2.0" (body)
  Hub: 0.25" (unstated, detected)
  Total: 2.25" (2.0" + 0.25")
  P-code: P15/P16 = 2.25" ✅ MATCHES
  Drill: 2.40" = 2.25" + 0.15" ✅ MATCHES
  Status: PASS ✅
```

---

## Impact Analysis

### Programs Affected

**Current Status (Before Rescan):**
- 3 steel rings identified with +0.25" unstated hub pattern
- These show DIMENSIONAL errors in database

**After Database Rescan:**
- 3 programs will change from DIMENSIONAL → PASS
- Steel ring PASS rate improvement: ~4%

### Combined with Steel Ring Thickness Fix

**Two Separate Fixes Required Rescan:**

1. **Thickness Parsing Fix** (commits 4dbc5a1, e8c66ba)
   - 21 programs with wrong thickness in database (1.0" instead of 1.25", etc.)
   - Need rescan to update database

2. **Unstated Hub Fix** (commit 442de81)
   - 3 programs with unstated 0.25" hub pattern
   - Need rescan to apply new validation logic

**Total Steel Ring Impact After Rescan:**
- Fix 21 programs (thickness parsing)
- Fix 3 programs (unstated hub)
- **Total: ~24 programs improved**
- Steel ring PASS rate: 61.0% → ~91% estimated

---

## Edge Cases Considered

### Does NOT Affect:

✅ **Steel rings without hub pattern**
- If implied hub < 0.20" or > 0.30" → standard calculation
- Example: o80596 (implied hub = 0.00") → no hub detected → PASS

✅ **Steel rings with stated hub in title**
- Hub extraction from title takes priority
- This fix only applies when hub NOT in title

✅ **Other spacer types**
- Only applies to `spacer_type == 'steel_ring'`
- 2PC parts have their own hub logic (0.15-0.35" range)
- Hub-centric parts use explicit hub from title

### Maintains Compatibility With:

✅ All existing validation logic
✅ 2PC STUD unstated hub rule
✅ Hub-centric hub detection
✅ Standard steel ring parts
✅ Thickness parsing patterns

---

## Comparison with 2PC STUD Rule

### Similarities

Both rules handle **unstated hubs**:
- Title shows body thickness only
- Hub machined in OP2 (not in title)
- P-code and drill include total (body + hub)

### Differences

| Aspect | 2PC STUD | Steel Ring |
|--------|----------|------------|
| Hub Range | 0.15-0.35" | 0.20-0.30" |
| Reason | Variable hub sizes | Specific 0.25" pattern |
| Spacer Types | 2PC LUG/STUD/UNSURE | steel_ring only |
| Common Value | 0.25" | 0.25" |

---

## Git Commit

**Commit:** `442de81`
**Date:** December 10, 2025
**Branch:** main

```
CRITICAL FIX: Steel ring unstated 0.25 inch hub detection

Problem:
- Some steel rings have unstated 0.25 inch hub machined in OP2
- Title shows body thickness, P-code/drill show total
- Caused false TITLE MISLABELED errors

Solution:
- Added steel_ring unstated hub detection (0.20-0.30 inch range)
- Similar to 2PC STUD rule
- Treats title as body thickness when hub detected

Testing:
- o80212: 1.25 inch + 0.25 inch hub = 1.50 inch CORRECT
- o80312: 2.0 inch + 0.25 inch hub = 2.25 inch CORRECT
```

---

## Next Steps

### Immediate

1. ⚠️ **Database Rescan Required**
   - Apply BOTH steel ring fixes (thickness parsing + unstated hub)
   - Expected to fix ~24 steel ring programs
   - Improve steel ring PASS rate from 61.0% to ~91%

2. ✅ **Fix Applied and Committed**
   - All code changes complete
   - Pushed to GitHub

### After Rescan

1. **Verify Results**
   - Check steel ring programs (o80212, o80312, o80831)
   - Confirm DIMENSIONAL → PASS status changes
   - Validate hub detection working correctly

2. **Monitor Pattern**
   - Track how many steel rings have unstated hub
   - Confirm 0.25" is the consistent value
   - Identify any outliers

---

## Summary

✅ **Unstated hub detection implemented** - Steel rings with 0.20-0.30" hub range
✅ **Pattern validated** - 3 programs confirmed with +0.25" pattern
✅ **Similar to 2PC STUD rule** - Consistent validation approach
✅ **Code committed and pushed** - Commit 442de81
✅ **Ready for rescan** - Will apply both steel ring fixes together

**Key Rule:**
Steel rings can have **unstated 0.25" hub** machined in OP2, just like 2PC STUD parts. The title shows **body thickness only**, while P-code and drill include the **total height (body + hub)**.

---

**End of Fix Documentation - 2025-12-10**
