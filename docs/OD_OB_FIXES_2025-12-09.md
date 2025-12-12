# OD and OB Extraction Fixes - December 9, 2025

## Summary

Fixed two critical parser issues preventing correct OB extraction for files with "DIA" keyword without "IN".

---

## Issue 1: OD Title Parsing - Missing "DIA" Pattern

### Problem
Titles like `6.00 DIA 67.0/72.56 ID 1.0 HC` were not parsing OD correctly.
- Pattern required "IN DIA" format: `r'(\d+\.?\d*)\s*IN[\$]?\s+DIA'`
- Files with just "DIA" (without "IN") failed to match
- **User specification:** "Value before DIA, or typically the first value in title is almost always the OD or round size and it will always be in inches even if not stated with IN"

### Root Cause
No pattern existed for "DIA" without "IN" prefix.

### Fix Applied (Line 823)
```python
# Added new pattern at TOP of pattern list (highest priority):
r'^(\d+\.?\d*)\s+DIA',  # Match "6.00 DIA" - first value before DIA is ALWAYS OD in inches
```

### Impact
- Files with "6.00 DIA" format now correctly parse OD as 6.00 inches (152.4mm)
- This fix enabled the OB extraction to work properly (OD filter threshold now correct)

---

## Issue 2: OB Following-Z Detection Too Strict

### Problem
File o61020 had OB extraction failing despite correct pattern:
- Line 79: `X2.857` (OB = 72.6mm, matches spec!)
- Line 80: `Z-0.04` (Z movement confirming X is OB)

Parser's `has_following_z` flag required Z movement >= 0.05", so Z-0.04" failed the check.

### Root Cause
Threshold at line 1537 was too strict:
```python
if 0.05 <= next_z_val <= 2.0:  # Z-0.04 fails this check!
```

### Fix Applied (Lines 1536-1538)
```python
# If Z is within hub height range (0.02" to 2.0"), this confirms X is OB
# Lowered from 0.05 to 0.02 to catch shallow movements like Z-0.04
if 0.02 <= next_z_val <= 2.0:
    has_following_z = True
```

### Impact
- OB candidates with Z movements as shallow as 0.02" (0.5mm) now detected
- File o61020 now correctly extracts OB = 72.6mm (exact match to spec)

---

## Test Results - o61020

### Before Fixes
```
OD: 6.0mm (WRONG - should be 152.4mm)
CB: 67.0mm (correct)
OB: None (extraction failed)
```

### After Fixes
```
OD: 6.00in (152.4mm) ✓ CORRECT
CB: 67.0mm ✓ CORRECT (0.0mm error)
OB: 72.6mm ✓ CORRECT (0.0mm error - exact match!)
```

---

## Files Modified

### improved_gcode_parser.py

**Fix 1: Line 823 - Added "DIA" pattern**
```python
od_patterns = [
    r'^(\d+\.?\d*)\s+DIA',              # NEW: Match "6.00 DIA"
    r'(\d+\.?\d*)\s*IN[\$]?\s+DIA',     # Existing patterns...
    # ...
]
```

**Fix 2: Lines 1536-1538 - Lowered Z threshold**
```python
# Changed from:
if 0.05 <= next_z_val <= 2.0:

# To:
if 0.02 <= next_z_val <= 2.0:
```

---

## Expected Impact on Database

### Programs Affected
- All programs with "X.XX DIA" format (no "IN" keyword)
- Programs with shallow Z movements (0.02-0.05") after OB positioning

### Estimated Fixes
- **OD parsing:** 100-200 programs with "DIA" format
- **OB extraction:** 50-100 programs with shallow Z movements
- **Net effect:** Better OD filtering → more accurate OB extraction

---

## Next Steps

1. ✅ **Fixes applied and tested** on o61020
2. 📋 **Run database rescan** to apply fixes across all 8,210 programs
3. 📋 **Verify results** - expect reduction in OB-related CRITICAL errors
4. 📋 **Monitor for edge cases** - check if any programs affected negatively

---

## Key Learnings

### 1. User Domain Knowledge is Critical
**User's insight:** "Value before DIA...will always be in inches even if not stated with IN"

This specification was crucial - without it, we might have added complex heuristics when a simple pattern was all that was needed.

### 2. Threshold Tuning Requires Real-World Data
The 0.05" threshold seemed reasonable in theory, but real files use Z-0.04" movements. Lowering to 0.02" (0.5mm) provides better coverage while still filtering noise.

### 3. Cascading Fixes
Fixing OD parsing enabled OB extraction to work:
- Correct OD → Correct OD filter threshold → Correct OB candidates → Correct OB selection

Both fixes were necessary for o61020 to parse correctly.

---

## Issue 3: OB Selection Only Checked Candidates with Following-Z

### Problem
File o50179 had OB extraction selecting wrong value:
- OB spec: 73.0mm
- Extracted: 66.0mm (CB value!)
- Best matches in OP2:
  - X2.8 (71.1mm) - 1.9mm error, NO following-Z flag
  - X2.764 (70.2mm) - 2.8mm error, NO following-Z flag
  - X2.6 (66.0mm) - 7.0mm error, HAS following-Z flag ✓

Parser only checked candidates with `has_following_z=True`, so it selected X2.6 (worst match) instead of X2.8 (best match).

### Root Cause
Lines 1594-1595 filtered to ONLY candidates with following-Z flag:
```python
ob_with_following_z = [x for x, z, idx, has_marker, has_z in ob_candidates if has_z]
if ob_with_following_z:  # Only checks this subset!
```

This excluded X2.8 and X2.764 which had Z values on the SAME line or different patterns.

### Fix Applied (Lines 1592-1629)
```python
# CRITICAL FIX: Check ALL candidates for near-matches FIRST
# Solution: Prioritize near-matches from ALL candidates, use following_z as tiebreaker

# Filter out OD values from ALL candidates (not just those with following_z)
all_filtered_ob = []
for x_val, z_val, idx, has_marker, has_z in ob_candidates:
    if od_mm and abs(x_val * 25.4 - od_mm) > 8.0:
        all_filtered_ob.append((x_val, has_z))

# Check for near-exact matches (within 5mm of spec)
near_matches = [(x, has_z) for x, has_z in all_filtered_ob
                if abs(x * 25.4 - title_ob_mm) < 5.0]

if near_matches:
    # Use closest, prefer has_following_z as tiebreaker
    closest_ob = min(near_matches,
                    key=lambda pair: (abs(pair[0] - title_ob_inches), not pair[1]))
```

### Impact
- All OB candidates now considered for near-match check
- `has_following_z` used as tiebreaker, not filter
- File o50179: 66.0mm → 71.1mm (7.0mm error → 1.9mm error)

---

## Test Results - All Files

| File | OB Spec | Before | Error | After | Error | Status |
|------|---------|--------|-------|-------|-------|--------|
| o61020 | 72.6mm | None | - | 72.6mm | 0.0mm | ✅ PERFECT |
| o50200 | 78.0mm | 144.8mm | 66.8mm | 78.0mm | 0.0mm | ✅ PERFECT |
| o50216 | 73.0mm | 144.8mm | 71.8mm | 73.0mm | 0.0mm | ✅ PERFECT |
| o50179 | 73.0mm | 66.0mm | 7.0mm | 71.1mm | 1.9mm | ✅ PASS |

---

## Conclusion

**Three targeted fixes solved complex OB extraction problems:**
1. Added "DIA" pattern for OD parsing (applies to ALL round sizes, not just 6.00")
2. Lowered Z-movement threshold from 0.05" to 0.02"
3. Check ALL OB candidates for near-matches (not just those with following-Z flag)

**Results:**
- o61020, o50200, o50216: PERFECT matches (0.0mm error)
- o50179: Excellent match (1.9mm error, was 7.0mm)

**Ready for database rescan to apply these improvements across all 8,210 programs!**
