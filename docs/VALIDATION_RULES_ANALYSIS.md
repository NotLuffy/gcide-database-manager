# Validation Rules Analysis - Current State

## Overview

This document explains ALL current validation rules, which part sizes/types they apply to, and identifies gaps where rules should apply universally but don't.

---

## CURRENT RULES BY CATEGORY

### 1. **OD (Outer Diameter) Validation**

**Rule:** Validates G-code OD against title OD specification

**Size Dependency:** ✅ YES - Two tiers based on OD size

**Application:**
```
IF outer_diameter >= 10.0":
    error_tolerance = ±0.25"
    warning_tolerance = ±0.15"
ELSE:
    error_tolerance = ±0.1"
    warning_tolerance = ±0.15"
```

**Applies To:**
- ALL part types (standard, hub-centric, 2PC, STEP)
- ALL round sizes (5.75", 6", 7", 10.25", 13")

**Why Size-Dependent:**
- Large parts (10.25", 13") are harder to machine precisely
- Larger OD allows more thermal expansion
- Industry standard for large part tolerance

---

### 2. **Thickness Validation**

**Rule:** Validates calculated thickness from drill depth against title thickness

**Size Dependency:** ✅ YES - Two tiers based on drill depth

**Application:**
```
IF drill_depth > 4.2":
    critical_tolerance = ±0.30"
    warning_tolerance = ±0.25"
    (Two-operation drilling)
ELSE:
    critical_tolerance = ±0.12"
    warning_tolerance = ±0.08"
    (Standard single-operation drilling)
```

**Calculation by Type:**
```
Hub-Centric:
    calculated_thickness = drill_depth - hub_height - 0.15"

2PC with hub in title:
    calculated_thickness = drill_depth - hub_height - 0.15"

2PC without hub in title:
    1. Calculate implied_hub = drill_depth - title_thickness - 0.15"
    2. If 0.15" <= implied_hub <= 0.35":
        calculated_thickness = title_thickness (unstated hub detected)
        hub_height = implied_hub
    ELSE:
        calculated_thickness = drill_depth - 0.15"

Standard/STEP:
    calculated_thickness = drill_depth - 0.15"
```

**Applies To:**
- ALL part types (but calculation differs by type)
- ALL round sizes

**Why Size-Dependent (Drill Depth):**
- Deep drilling (>4.2") requires two operations (OP1 + OP2)
- OP2 intentionally over-drills to ensure breakthrough
- Extra tolerance needed for two-operation consistency

**P-Code Cross-Check for Hub-Centric:**
```
For hub-centric parts:
    pcode_thickness = pcode_total_height - hub_height

Compare pcode_thickness to calculated_thickness:
    If match (within 0.02") AND doesn't match title:
        Flag as "TITLE MISLABELED"
```

---

### 3. **CB/OB Title Parsing (Large Rounds)**

**Rule:** For large rounds, detect if CB value is in inches (not mm)

**Size Dependency:** ✅ YES - Large rounds ONLY

**Application:**
```
IF outer_diameter >= 10.0" AND
   first_value < 10 AND
   NOT first_has_mm AND
   second_has_mm:

    # First value is in inches - convert to mm
    first_val = first_val * 25.4
```

**Example:**
- Title: `13.0 6.25/220MM`
- Parser detects: 6.25" CB (158.75mm) / 220mm OB
- Converts 6.25 to 158.75mm automatically

**Applies To:**
- ONLY large parts (OD >= 10.0")
- Hub-centric and standard parts with mixed units

**Why Size-Dependent:**
- Large rounds often use mixed units (inches CB / mm OB)
- Small rounds don't have this pattern

---

### 4. **OB Extraction Range**

**Rule:** X value range for identifying OB candidates

**Size Dependency:** ❌ NO - Fixed range for all sizes

**Application:**
```
OB candidates: 2.0" < X < 10.5"
    (50mm to 267mm)
```

**Applies To:**
- ALL round sizes (5.75", 6", 7", 10.25", 13")
- ALL part types with OB (hub-centric, 2PC)

**Why NOT Size-Dependent:**
- Range is wide enough to cover all round sizes
- 2.0" minimum covers small 5.75" rounds (OB ~50-80mm)
- 10.5" maximum covers large 13" rounds (OB ~220mm)

**POTENTIAL GAP:** Could be size-dependent for better accuracy
- Small rounds (5.75"-7"): Expect OB 2.0"-4.0"
- Large rounds (10.25"-13"): Expect OB 4.0"-10.0"

---

### 5. **OB Z-Movement Detection**

**Rule:** Detects Z-movement after X to confirm OB

**Size Dependency:** ❌ NO - Fixed threshold for all sizes

**Application:**
```
IF 0.02" <= next_z_movement <= 2.0":
    has_following_z = True
```

**Applies To:**
- ALL round sizes
- ALL part types with OB

**Why NOT Size-Dependent:**
- Hub heights vary from 0.25" to 2.0" across all sizes
- Same Z-movement pattern applies universally

**POTENTIAL GAP:** Could be size-dependent
- Small rounds: Hubs typically 0.25"-0.75"
- Large rounds: Hubs typically 0.75"-2.0"

---

### 6. **CB Validation**

**Rule:** Validates extracted CB against title CB

**Size Dependency:** ❌ NO - Fixed tolerance for all sizes

**Application:**
```
tolerance = ±0.5mm (±0.020")
```

**Applies To:**
- ALL round sizes
- ALL part types with CB

**Why NOT Size-Dependent:**
- CB is a precision bore - tolerance doesn't scale with size
- Same ±0.5mm applies to 5.75" and 13" rounds

---

### 7. **OB Validation**

**Rule:** Validates extracted OB against title OB

**Size Dependency:** ❌ NO - Fixed tolerance for all sizes

**Application:**
```
tolerance = ±2.0mm (±0.079")
```

**Applies To:**
- ALL round sizes
- ALL part types with OB

**Why NOT Size-Dependent:**
- OB is a turned diameter - tolerance is consistent
- Same ±2.0mm applies to all sizes

---

### 8. **P-Code Validation**

**Rule:** Validates P-code consistency with thickness

**Size Dependency:** ❌ NO - But lathe-dependent

**Application:**
```
Lathe L1: Uses L1 P-code table
Lathe L2/L3: Uses L2/L3 P-code table

For hub-centric:
    expected_thickness = pcode_total_height - hub_height

For standard/2PC:
    expected_thickness = pcode_total_height
```

**Applies To:**
- ALL round sizes
- ALL part types
- Depends on lathe assignment (L1 vs L2/L3)

**Why Lathe-Dependent:**
- Different lathes use different P-code standards
- P-code tables map to specific total heights
- Not related to part size

---

## IDENTIFIED GAPS

### Gap 1: OD Pattern Recognition
**Issue:** "DIA" pattern recognition was missing (fixed in this session)

**Before Fix:**
- Only recognized "IN DIA" pattern
- Missed "6.00 DIA" format (no "IN" marker)

**After Fix:**
- Added pattern `r'^(\d+\.?\d*)\s+DIA'`
- NOW applies to ALL round sizes

---

### Gap 2: OB Range Too Restrictive
**Issue:** Minimum OB range excluded small values (fixed in this session)

**Before Fix:**
- Range: 2.2" < X < 10.5"
- Excluded X2.14 values (54mm)

**After Fix:**
- Range: 2.0" < X < 10.5"
- NOW applies to ALL round sizes including small OB values

---

### Gap 3: OB Selection Only Checked Following-Z
**Issue:** Best OB matches excluded if no following-Z flag (fixed in this session)

**Before Fix:**
- Only checked OB candidates with `has_following_z=True`
- Missed best matches that had Z on same line

**After Fix:**
- Checks ALL OB candidates for near-matches first
- Uses following_z as tiebreaker only
- NOW applies to ALL round sizes

---

### Gap 4: Thickness Validation for Large Rounds
**POTENTIAL ISSUE - USER CONCERN:**

**User Report:**
> "10.250 round pieces are ignoring the hubs to be added to overall thickness so it populates false dimensional warnings"

**Current Logic:**
```python
# For hub-centric parts
hub_h = result.hub_height if result.hub_height else 0.50
calculated_thickness = result.drill_depth - hub_h - 0.15

# For P-code validation
pcode_thickness = pcode_total_height - hub_h

# Compare calculated vs title
diff = calculated_thickness - title_thickness
```

**Question:** Is the comparison logic correct for ALL round sizes?

**Hypothesis:**
1. For small rounds (5.75"-7"): Logic works correctly
2. For large rounds (10.25"-13"): Might need different logic?

**Need Clarification:**
- Should thickness validation use DIFFERENT tolerances for large rounds?
- Should P-code comparison work differently for 10.25" vs 5.75" rounds?
- Is the hub height calculation correct for ALL sizes?

---

## RULE APPLICATION SUMMARY

### Rules That ARE Size/Type Dependent:
1. ✅ OD Validation - Two tiers (< 10" vs >= 10")
2. ✅ Thickness Validation - Two tiers (< 4.2" drill vs > 4.2" drill)
3. ✅ CB/OB Parsing - Large rounds only (>= 10")

### Rules That are NOT Size Dependent (But Could Be):
4. ❌ OB Extraction Range - Fixed 2.0"-10.5" for ALL
5. ❌ OB Z-Movement - Fixed 0.02"-2.0" for ALL
6. ❌ CB Validation - Fixed ±0.5mm for ALL
7. ❌ OB Validation - Fixed ±2.0mm for ALL
8. ❌ P-Code Validation - Lathe-dependent, not size-dependent

---

## QUESTIONS FOR USER

### Q1: Thickness Validation for 10.25" Rounds
**User said:** "10.250 round pieces are ignoring the hubs to be added to overall thickness"

**Current behavior:**
- Parser subtracts hub from drill depth: `thickness = drill - hub - 0.15`
- Parser subtracts hub from P-code total: `pcode_thickness = pcode_total - hub`
- Compares these two "body thickness" values

**Is this wrong?** Should we be comparing TOTAL heights instead?

**Example o10535:**
- Title: 1.5" thickness + 1.0" hub = 2.5" total
- P17 = 2.5" total height
- Drill: 2.65"
- Calculated thickness: 2.65 - 1.0 - 0.15 = 1.5" ✓

**This seems correct?** But user says there are false warnings.

### Q2: Are There Other Size-Specific Rules Needed?

Should any of these fixed rules become size-dependent?
- OB extraction range
- OB Z-movement threshold
- CB/OB tolerance values

---

## NEXT STEPS

1. **Clarify** user's concern about 10.25" thickness validation
2. **Check** if database has stale data (needs rescan)
3. **Identify** if new size-dependent logic is needed
4. **Test** with actual 10.25" programs showing issues
5. **Document** any new rules that should apply to all sizes

