# Two-Operation Drill Tolerance Analysis

## Summary

Analysis of 26 two-operation parts (drill depth > 4.2") in 13" round programs to determine appropriate tolerance for thickness validation.

## Key Findings

### Tolerance Distribution
- **Within ±0.10"**: 6 parts (23.1%)
- **Within ±0.20"**: 21 parts (80.8%) ✓ **Current tolerance covers most cases**
- **Within ±0.30"**: 22 parts (84.6%)
- **Beyond ±0.30"**: 4 parts (15.4%)

### Statistics
- **Minimum difference**: -0.350" (o13273 - under-drilling)
- **Maximum difference**: +1.900" (o13274 - FIXED by hub height correction)
- **Average difference**: +0.263"

## Major Fixes Applied

### 1. Hub Height Maximum Increased (2.0" → 3.5")

**Problem**: Files with hub heights > 2.0" were not being parsed correctly from title.

**Files affected**:
- **o13274**: "HC 2.25" → Was reading 0.5", now reads 2.25" ✓
- **o13183**: "HC 3.0" → Was reading 1.25", now reads 3.0" ✓
- **o13217**: "HC 2.5" → Was reading 1.25", now reads 2.5" ✓
- **o13090**: "HC 2.25" → Was reading 1.5", now reads 2.25" ✓
- **o13049**: "HC 2.25" → Was reading 2.0", now reads 2.25" ✓

**Fix**: Changed hub height maximum from 2.0" to 3.5" in three locations:
1. Line 869: Dual HC pattern (e.g., "3.0 HC 2.25")
2. Line 886: Single HC pattern (e.g., "HC 2.5")
3. Line 1329: Facing calculation validation range

**Result**: 4 out of 5 files now PASS (o13049 has legitimate under-drilling issue)

### 2. Hub Height Override Logic Fixed

**Problem**: Facing calculations were overriding valid title hub heights when `hub_height == 0.50`.

**Issue**: 0.50" is a VALID hub height value, not just a default placeholder.

**Fix**: Changed line 1331 from:
```python
if not result.hub_height or result.hub_height == 0.50:
```
To:
```python
if not result.hub_height:
```

**Result**: Title hub heights are now prioritized over calculated values.

## Parts with Extreme Differences (> ±0.30")

### o13274 (FIXED - Now PASS)
- **Title**: 13.0 170.1/220MM 3.0 HC 2.25
- **Drill**: OP1 Z-4.15 + OP2 Z-1.4 = 5.55"
- **Expected**: 3.0 + 2.25 + 0.15 = 5.40"
- **Difference**: +0.150" ✓ PASS
- **Before fix**: +1.900" (was using hub=0.5 instead of 2.25)

### o13183 (FIXED - Now PASS)
- **Title**: 13.0 142/220MM 1.25 HC 3.0
- **Drill**: OP1 Z-4.15 + OP2 Z-0.35 = 4.50"
- **Expected**: 1.25 + 3.0 + 0.15 = 4.40"
- **Difference**: +0.100" ✓ PASS
- **Before fix**: +1.850" (was using hub=1.25 instead of 3.0)

### o13121 (Legitimate over-drilling)
- **Title**: 13.0 121.3/220MM 5.0 HC .5
- **Drill**: OP1 Z-4.15 + OP2 Z-2.15 = 6.30"
- **Expected**: 5.0 + 0.5 + 0.15 = 5.65"
- **Difference**: +0.650" (CRITICAL)
- **Note**: Intentional over-drilling for punch-through? User indicated this is acceptable.

### o13273 (Under-drilling)
- **Title**: 13.0 170.1/220MM 3.5 HC 1.5
- **Drill**: OP1 Z-4.15 + OP2 Z-0.65 = 4.80"
- **Expected**: 3.5 + 1.5 + 0.15 = 5.15"
- **Difference**: -0.350" (CRITICAL)
- **Note**: Part is under-drilled by 0.35", may not fully separate.

## Recommendations

### Current Tolerance: ±0.20" for Two-Operation Parts

**Status**: **ADEQUATE** for 80.8% of parts

**Reasoning**:
1. Covers majority of parts (21 out of 26)
2. Flags genuine issues (o13121 +0.65", o13273 -0.35")
3. Hub height fix resolved 2 extreme outliers (+1.85" and +1.90")

### Files Exceeding ±0.20" Tolerance

**Beyond tolerance (4 files)**:
1. **o13121**: +0.650" over (user confirms acceptable for punch-through)
2. **o13273**: -0.350" under (REAL ERROR - under-drilling)
3. **o13158**: +0.250" over (slightly exceeds tolerance)
4. **o13049**: -0.250" under (slightly under-drilled)

**Action**: Keep ±0.20" tolerance. Files exceeding this should be reviewed:
- Over-drilling > +0.20": May be intentional, but flag for review
- Under-drilling < -0.20": **CRITICAL** - part may not separate properly

## Overall Validation Results (After Fixes)

### 13" Round Programs (334 total)
- **PASS**: 259 (77.5%)
- **DIMENSIONAL**: 44 (13.2%)
- **CRITICAL**: 28 (8.4%)
- **BORE_WARNING**: 3 (0.9%)

### Thickness Errors (After Fixes)
- **Current**: 12 files (3.6%)
- **Previous**: 14 files (4.2%)
- **Original**: ~50-60 files (~15-18%)
- **Improvement**: ~85% reduction in false positives

### Remaining Thickness Errors Breakdown
- **Under-drilling** (< -0.20"): 5 files (CRITICAL - won't separate)
- **Over-drilling** (> +0.20"): 5 files (Review needed)
- **Moderate** (±0.20" to ±0.30"): 2 files (Near tolerance)

## Conclusion

The ±0.20" tolerance for two-operation parts is appropriate:
- Covers 80.8% of parts automatically
- Correctly flags extreme cases for review
- Hub height fix eliminated 2 major false positives
- Remaining errors are mostly legitimate G-code issues requiring manual review

**No tolerance adjustment needed.** Current settings are working correctly.
