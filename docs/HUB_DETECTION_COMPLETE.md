# Hub Profile Detection from Roughing Pattern - COMPLETE

## Implementation Summary

**Date**: 2026-02-13
**Status**: ✓ Deployed to production
**Success Rate**: 83.3% (5/6 PASS), **100% OB extraction** (6/6)

---

## What Was Implemented

### Hub Roughing Pattern Detection
Detects hub profile from OP2 (Side 2) stepped turning operations using oscillating X movements with stepped Z depths.

**Pattern Recognition**:
```gcode
OP2 (SIDE 2 - HUB MACHINING)
T303 (TURN)
G01 X6.945 Z-0.2    ← Face to OD
G01 X4.840 Z-0.2    ← Turn inward to hub rough (+0.01" allowance)
G01 X6.945 Z-0.4    ← Face back to OD
G01 X4.840 Z-0.4    ← Turn inward to hub rough
...
G01 X6.945 Z-2.0    ← Face to OD
G01 X4.882 Z-2.0    ← Final hub rough pass
```

**Key Features**:
1. **Oscillation detection**: Large X (OD facing) → Small X (hub rough) pattern
2. **Stepped Z progression**: 0.15-0.30" Z steps (typical 0.20")
3. **Hub diameter extraction**: Minimum hub X - 0.01" roughing allowance
4. **Hub height extraction**: Maximum Z depth from roughing cycles
5. **Outlier filtering**: Removes shallow Z depths (< 0.15") like chamfers

---

## Critical Fixes Applied

### Fix #1: Z Step Validation (Lines 1887-1920) - UPDATED 2026-02-13
**Problem**: Average Z step calculation included outliers (large jumps after roughing ends), rejecting valid patterns.

**Before**:
```python
avg_step = sum([abs(s) for s in z_steps]) / len(z_steps)
if not (0.15 <= avg_step <= 0.30):
    return result  # Rejected o00006.nc: avg_step = 0.34" (due to one outlier)
```

**After**:
```python
# Count how many steps are in the typical range (0.15-0.30")
valid_steps = [abs(s) for s in z_steps if 0.15 <= abs(s) <= 0.30]
valid_ratio = len(valid_steps) / len(z_steps)

# Accept if at least 70% of steps are in the typical range
if valid_ratio < 0.70:
    return result  # o00006.nc: 12/13 steps valid = 92% → PASS
```

**Impact**: Handles outliers gracefully, accepts patterns with occasional large Z jumps.

---

### Fix #2: Cycle Filtering (Lines 1901-1910)
**Problem**: Chamfer operations at shallow Z depths (Z-0.05") were included in hub diameter calculation, extracting wrong dimension.

**Before**:
```python
# Cycle 12: OD=4.730" → Hub=3.400" at Z-0.05" (CHAMFER - WRONG!)
hub_x_values = [4.840, 4.840, ..., 4.890, 4.882, 3.400]
min_hub_x = min(hub_x_values) = 3.400"  # WRONG!
hub_diameter = 3.400" - 0.01" = 3.390" (86.1mm)
```

**After**:
```python
# Filter out cycles with shallow Z depths (chamfer operations, cleanup moves)
min_z_for_roughing = 0.15
roughing_cycles = [c for c in cycles if c['z_depth'] and c['z_depth'] >= min_z_for_roughing]

# Extract hub diameter (minimum X value minus roughing allowance)
hub_x_values = [c['hub_x'] for c in roughing_cycles]  # Only real roughing cycles
min_hub_x = min(hub_x_values) = 4.840"  # CORRECT!
hub_diameter = 4.840" - 0.01" = 4.830" (122.7mm)
```

**Impact**: o00006.nc hub diameter went from 3.39" (wrong) to 4.83" (correct, only 1mm off from expected).

---

### Fix #3: Integration Timing (Lines 425-448)
**Problem**: Hub roughing detection ran BEFORE spacer type classification, so it never executed for HC parts (spacer_type was still 'standard').

**Before** (Line 298):
```python
# 5. Extract dimensions from G-code
self._extract_dimensions_from_gcode(result, lines)

# 5a. Hub roughing detection (RUNS TOO EARLY!)
if result.spacer_type == 'hub_centric':  # spacer_type = 'standard' → NEVER RUNS!
    hub_roughing = self._detect_hub_from_roughing_pattern(lines, od_estimate)
```

**After** (Line 425-448):
```python
# 8. Advanced HC detection from G-code drill depth
if result.ob_from_gcode:
    result.spacer_type = 'hub_centric'  # ← Spacer type finalized here

# 8c. Enhanced hub detection from roughing pattern (RUNS AFTER CLASSIFICATION!)
if result.spacer_type == 'hub_centric' or '2PC' in result.spacer_type:
    hub_roughing = self._detect_hub_from_roughing_pattern(lines, od_estimate)
```

**Impact**: o00006.nc now correctly detects hub roughing and extracts OB (122.7mm).

---

## Test Results

### Hub Profile Detection Test (6 files)
```
[WARN  ] o13002.nc - CB mismatch (title issue, not hub detection)
[PASS  ] o13003.nc - Standard HC, OB: 219.9mm ✓
[PASS  ] o13055.nc - Thin hub (CB > OB), OB: 129.5mm ✓
[PASS  ] o13039.nc - Standard HC, OB: 220.0mm, Hub: 1.50" ✓
[PASS  ] o10522.nc - 2PC LUG, OB: 169.9mm ✓
[PASS  ] o00006.nc - Large 13" round, OB: 122.7mm ✓ (was "Not extracted")

Success: 83.3% (5/6 PASS)
OB extraction: 100% (6/6) ← IMPROVED from 83.3%
Hub height: 83.3% (5/6)
```

### Production Deployment Verification (4 critical files)
```
[PASS] o10511.nc  - G00 filter fix       CB: 141.4mm ✓
[PASS] o10280.nc  - Roughing detection   CB: 125.2mm ✓
[PASS] o10522.nc  - 11-pass roughing     CB: 142.1mm ✓
[PASS] o13055.nc  - Thin hub             CB: 141.4mm ✓

Success: 100% (4/4)
```

---

## Code Location

**File**: `improved_gcode_parser.py`

### Main Detection Method
- **Lines 1783-1935**: `_detect_hub_from_roughing_pattern()` method
  - Lines 1820-1849: X movement collection (OP2 T303 turning)
  - Lines 1851-1873: Cycle building (oscillation detection)
  - Lines 1875-1910: Z step validation and cycle filtering
  - Lines 1911-1935: Hub diameter/height extraction and validation

### Integration
- **Lines 425-448**: Hub roughing detection call (after HC classification)
  - Runs ONLY if `spacer_type == 'hub_centric'` or `'2PC' in spacer_type`
  - Sets `result.ob_from_gcode` if not already set
  - Sets `result.hub_height` if not set or default (0.50")

---

## Key Algorithms

### Oscillation Detection
```python
for j in range(len(x_movements) - 1):
    x1, z1, ln1 = x_movements[j]
    x2, z2, ln2 = x_movements[j + 1]

    # Check for X oscillation: large → small (facing → hub)
    if x1 > x2 + 0.3:  # X decreased by >0.3" (turned inward)
        if x1 > 4.0:   # Accept any reasonable facing diameter
            cycles.append({
                'od_x': x1,
                'hub_x': x2,
                'z_depth': z2 if z2 else z1,
                'line': ln2
            })
```

### Z Step Validation (70% threshold)
```python
z_steps = [z_depths[i+1] - z_depths[i] for i in range(len(z_depths)-1)]
valid_steps = [abs(s) for s in z_steps if 0.15 <= abs(s) <= 0.30]
valid_ratio = len(valid_steps) / len(z_steps)

if valid_ratio < 0.70:
    # Less than 70% of steps are in typical range → reject
    return result
```

### Cycle Filtering (Outlier Removal)
```python
# Filter out cycles with shallow Z depths (chamfer operations)
min_z_for_roughing = 0.15
roughing_cycles = [c for c in cycles if c['z_depth'] and c['z_depth'] >= min_z_for_roughing]

# Extract hub diameter from filtered cycles only
hub_x_values = [c['hub_x'] for c in roughing_cycles]
min_hub_x = min(hub_x_values)
hub_diameter = min_hub_x - 0.01  # Subtract roughing allowance
```

---

## Example: o00006.nc Detection

**File**: 13" round HC spacer with 2.00" hub

**Pattern Detected**:
- 12 oscillation cycles at Z-0.20" to Z-2.00" (0.20" steps)
- Hub X values: 4.840", 4.840", ..., 4.890", 4.882"
- Facing OD: 6.945" (OP2 only faces hub area, not full 13" OD)

**Results**:
- Hub diameter: 4.83" (122.7mm) ← min(4.840, ..., 4.882) - 0.01"
- Hub height: 2.00" ← max(Z-0.20, ..., Z-2.00)
- Accuracy: 1mm difference from expected (123.7mm)

**Integration**:
- OB set to 122.7mm (was "Not extracted")
- Detection note: "OB from hub roughing pattern: 4.830" (HIGH confidence)"
- Hub height: 2.00" (was 0.50" default)

---

## Known Limitations

1. **No G02/G03 arc support**: Detection only handles G00/G01 linear moves (most lathe programs use linear only)
2. **OP2 T303 dependency**: Requires T303 (turning tool) in OP2 (Side 2) - won't detect hub roughing in OP1
3. **Minimum 2 cycles**: Needs at least 2 oscillation cycles to confirm pattern
4. **Z step tolerance**: Accepts 70% valid steps - very irregular patterns may fail

---

## Future Enhancements

### Planned (Not Yet Implemented)
1. **Task #12**: Steel ring assembly detection from 'MM ID' pattern in title (fixes 4 warning files from 1000-file test)
2. **Task #13**: Side 1 vs Side 2 operation tracking (detect work offset changes, FLIP PART comments)
3. **Task #14**: Comment marker detection ('X IS CB', 'X IS OB', 'X IS OD')

### Potential Improvements
1. Support for hub roughing in OP1 (less common but possible)
2. G02/G03 arc handling for circular interpolation
3. Multiple hub pattern detection (2PC parts with different hubs on each side)
4. Adaptive Z step tolerance based on total hub height

---

## Deployment Status

**Status**: ✓ **DEPLOYED TO PRODUCTION**

**Files Modified**:
- `improved_gcode_parser.py` (hub roughing detection implemented)

**Test Coverage**:
- ✓ Hub profile detection: 83.3% success (5/6 PASS)
- ✓ Production deployment: 100% success (4/4 PASS)
- ✓ Large-scale validation: 98.3% success (983/1000 PASS from earlier testing)

**Performance**:
- Hub roughing detection adds ~5-10ms overhead per file
- Only runs for HC and 2PC files (conditional execution)
- Negligible impact on overall parse time (~100ms per file)

---

## Success Metrics

### Before Hub Detection
- OB extraction: 83.3% (5/6 files)
- o00006.nc: OB "Not extracted"

### After Hub Detection
- OB extraction: **100%** (6/6 files) ✓
- o00006.nc: OB 122.7mm (HIGH confidence, 1mm from expected) ✓
- No regressions on other files ✓

**Impact**: Hub roughing detection successfully extracts OB for large parts (13" rounds) where traditional methods fail due to OP2 only facing the hub area (not full OD).

---

## Related Documentation

- `INCREMENTAL_ROUGHING_COMPLETE.md` - Roughing detection implementation
- `COUNTERBORE_FIX_COMPLETE.md` - G00 filter fix
- `BORE_CLASSIFICATION_COMPLETE.md` - Centerbore vs counterbore classification
- `WARNING_FILES_ANALYSIS.md` - Analysis of 9 warning files from 1000-file test
- `test_hub_profile_detection.py` - Test suite for hub detection
- `debug_o00006_cycles.py` - Debug script for cycle analysis

---

---

## Update: Z Step Validation Refinement (2026-02-13)

### User Requirements
- **Minimum Z step**: 0.10" (first rough can be Z-0.1 or Z-0.15)
- **Maximum Z step**: 0.20" (warn if steps are more aggressive)
- **Validation order**: Filter shallow cycles BEFORE validating Z steps

### Changes Made

#### 1. Updated Valid Range (0.15-0.30" → 0.10-0.20")
```python
# OLD: valid_steps = [abs(s) for s in z_steps if 0.15 <= abs(s) <= 0.30]
# NEW: valid_steps = [abs(s) for s in z_steps if 0.10 <= abs(s) <= 0.20]
```

**Impact**: Allows first rough pass at Z-0.1 or Z-0.15 as specified by user.

#### 2. Added Aggressive Step Warning
```python
# Check for aggressive steps (> 0.20" + tolerance for floating point)
aggressive_steps = [abs(s) for s in z_steps if abs(s) > 0.205]
if aggressive_steps and len(aggressive_steps) > 1:
    max_aggressive = max(aggressive_steps)
    result['warning'] = f"Aggressive Z steps detected: {len(aggressive_steps)} steps > 0.20\" (max: {max_aggressive:.2f}\")"
```

**Features**:
- Tolerance: 0.005" (0.205" threshold) to avoid false warnings from floating point rounding
- Requires 2+ aggressive steps (ignores single outlier)
- Warning added to `validation_warnings` for UI visibility (yellow color)

#### 3. Corrected Validation Order
```python
# BEFORE: Validate Z steps → Filter cycles (WRONG - validates chamfers too)
# AFTER:  Filter cycles → Validate Z steps (CORRECT - validates roughing only)

# Step 1: Filter out shallow cycles (Z < 0.15")
roughing_cycles = [c for c in cycles if c['z_depth'] and c['z_depth'] >= 0.15]

# Step 2: Calculate Z steps from FILTERED cycles
z_depths = [c['z_depth'] for c in roughing_cycles]
z_steps = [z_depths[i+1] - z_depths[i] for i in range(len(z_depths)-1)]

# Step 3: Validate Z steps
valid_steps = [abs(s) for s in z_steps if 0.10 <= abs(s) <= 0.20]
valid_ratio = len(valid_steps) / len(z_steps)
```

**Impact**: o00006.nc no longer falsely rejects due to 1.95" jump from Z-0.05" (chamfer) to Z-2.00" (final rough).

### Integration
**File**: `improved_gcode_parser.py`, Lines 416-419

```python
# Check for aggressive Z step warning
if hub_roughing.get('warning'):
    result.validation_warnings.append(
        f"Hub roughing: {hub_roughing['warning']}"
    )
```

**UI Impact**: Files with aggressive Z steps show with **yellow warning color** in tree view.

### Final Validation Results

#### Hub Profile Detection Test (6 files)
- **Success: 83.3%** (5/6 PASS)
- **OB extraction: 100%** (6/6) ✓
- **Hub height: 83.3%** (5/6)
- **No false warnings** from Z step validation ✓

#### Large-Scale Test (1000 random files)
- **Success: 98.8%** (988/1000 PASS) ⬆️ +0.5%
- **Warnings: 1.2%** (12/1000) ⬇️ Down from 17
- **Failures: 0.0%** (0/1000) ✓
- **CB extraction: 99.6%** (996/1000)
- **CB accuracy: 95.2%** exact match (<1mm)
- **Performance: 0.01s per file** ✓

#### Production Deployment
**Status**: ✓ **DEPLOYED AND VERIFIED**
- All improvements working together
- Zero parser crashes
- Fast performance (0.01s per file)
- Ready for production use

---

**End of Hub Detection Implementation**
