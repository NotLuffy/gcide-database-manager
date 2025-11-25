# 2PC Detection Improvements - Phase 2 Implementation

## Overview

Implemented advanced G-code analysis to improve 2PC LUG vs STUD classification using physical part characteristics and machining patterns.

## User-Specified Rules

### STUD Characteristics:
- Typically labeled as "1.00"" in title (0.75" thick + 0.25" hub ≈ 1.00" total)
- **Actual thickness**: 0.75" (max, never exceeds this)
- **Hub height**: ~0.25" (0.20" - 0.30" with tolerance)
- **Special case** (future): 0.5" hub with recess on opposite side

### LUG Characteristics:
- **Thickness**: 0.75" minimum, typically 1.0" or greater
- **Shelf/recess**: Z-0.31 to Z-0.35 depth in OP1 (support shelf)
- **Key rule**: If thickness > 0.75" with 0.25" hub → LUG (studs never exceed 0.75")
- **Function**: Receives the STUD insert

## Implementation Status: ✓ COMPLETE

All improvements implemented and tested successfully.

## Code Changes

### 1. New Method: _analyze_2pc_gcode() (Lines 976-1055)

**Location**: `improved_gcode_parser.py` lines 976-1055

**Purpose**: Advanced G-code analysis for LUG/STUD classification

**Detection Rules** (in priority order):

#### Rule 1: LUG Shelf Detection (HIGHEST CONFIDENCE)
```python
# Scan for Z-depths in range 0.31" - 0.35"
lug_shelf_depths = [z for z in z_depths if 0.31 <= z <= 0.35]
if lug_shelf_depths:
    return '2PC LUG', 'GCODE_SHELF_DEPTH', 'HIGH'
```
- **Confidence**: HIGH
- **Rationale**: Physical machining operation unique to LUG parts

#### Rule 2: Thickness > 0.75" = LUG
```python
if thickness > 0.75:
    if hub_height and 0.20 <= hub_height <= 0.30:
        return '2PC LUG', 'THICKNESS_HUB_COMBO', 'HIGH'
    else:
        return '2PC LUG', 'THICKNESS_ANALYSIS', 'MEDIUM'
```
- **Confidence**: HIGH (with hub), MEDIUM (without)
- **Rationale**: STUDs never exceed 0.75" thickness

#### Rule 3: Thickness ≈ 0.75" + Hub ≈ 0.25" = STUD
```python
if 0.70 <= thickness <= 0.80:
    if 0.20 <= hub_height <= 0.30:
        return '2PC STUD', 'THICKNESS_HUB_COMBO', 'HIGH'
```
- **Confidence**: HIGH
- **Rationale**: Classic STUD pattern (0.75" + 0.25" hub = 1.00" total)

#### Rule 4: Hub Height Alone
```python
if 0.20 <= hub_height <= 0.30:
    return '2PC STUD', 'HUB_HEIGHT_ANALYSIS', 'MEDIUM'
```
- **Confidence**: MEDIUM
- **Rationale**: 0.25" hub suggests STUD if no LUG indicators found

### 2. Integration Point (Lines 237-244)

**Location**: `improved_gcode_parser.py` lines 237-244

```python
# 5a. Advanced 2PC classification using G-code analysis
if result.spacer_type == '2PC UNSURE' and lines:
    twopc_analysis = self._analyze_2pc_gcode(lines, result.thickness, result.hub_height)
    if twopc_analysis['type']:
        result.spacer_type = twopc_analysis['type']
        result.detection_method = twopc_analysis['method']
        result.detection_confidence = twopc_analysis['confidence']
        result.detection_notes.append(twopc_analysis['note'])
```

**Execution Order**:
1. Keyword detection (LUG/STUD in title/comments)
2. G-code comment detection ("LUG PLATE" / "STUD PLATE")
3. **NEW: Advanced G-code analysis** ← Added here
4. Thickness heuristic (fallback)

### 3. Thickness Parsing Enhancement (Lines 818-819)

**Location**: `improved_gcode_parser.py` lines 818-819

**Problem**: Titles like "6.25  40MM INNER .75 TH  2PC" had unparsed thickness

**Solution**: Added patterns to recognize "TH" abbreviation

```python
(r'(\d*\.?\d+)\s+THK?(?:\s|$)', 'IN', False),  # "0.75 THK" or "0.75 TH"
(r'\.(\d+)\s+TH(?:\s|$)', 'DECIMAL', False),   # ".75 TH" without leading 0
```

**Special handling**:
```python
if unit == 'DECIMAL':
    thickness_val = float('0.' + thickness_val_str)  # ".75" → 0.75
```

## Test Results

**Test File**: `test_2pc_logic_improvements.py`

**Before**: 7 files classified as "2PC UNSURE"

**After improvements**:
- **3 files** → 2PC LUG (using shelf depth detection)
- **2 files** → 2PC STUD (using thickness + TH abbreviation fix)
- **2 files** → Still UNSURE (no thickness data available)

**Improvement**: 71.4% of UNSURE files now classified (5/7)

### Detailed Results:

| Program | Title | Old | New | Method | Confidence |
|---------|-------|-----|-----|--------|------------|
| o62260 | 6.25  40MM INNER .75 TH  2PC | UNSURE | **STUD** | THICKNESS_HEURISTIC | LOW |
| o62265 | 6.25IN HC 80.5MM OUTER 2PC | UNSURE | **LUG** | GCODE_SHELF_DEPTH | HIGH |
| o62528 | 6.25 IN 71MM 4.25 2PC | UNSURE | **LUG** | GCODE_SHELF_DEPTH | HIGH |
| o62688 | 6.25  40MM OUTER .75 TH  2PC | UNSURE | **STUD** | THICKNESS_HEURISTIC | LOW |
| o65031 | 6.5IN HC 73.1-80.5 OUTER 2PC | UNSURE | UNSURE | KEYWORD | MEDIUM |
| o70302 | 7.0 IN DIA 71.5MM ID 2PC  .55 HC | UNSURE | **LUG** | GCODE_SHELF_DEPTH | HIGH |
| o75038 | (empty title) | UNSURE | UNSURE | KEYWORD | LOW |

### Remaining UNSURE Files (2):

1. **o65031**: No thickness in title, no shelf pattern detected in G-code
2. **o75038**: Empty title, no data to parse

**Acceptable**: 2/7 remaining UNSURE (28.6%) is good given lack of data

## Detection Method Distribution

| Method | Count | Confidence | Notes |
|--------|-------|------------|-------|
| GCODE_SHELF_DEPTH | 3 | HIGH | Z-0.31 to Z-0.35 shelf pattern detected |
| THICKNESS_HEURISTIC | 2 | LOW | Thickness 0.75" = STUD (fallback method) |

**Key Success**: 3/5 classified files used HIGH confidence shelf depth detection

## Impact on Database (Projected)

**Current Status** (from database):
- Total programs: ~6,200
- 2PC LUG: ~492 files
- 2PC STUD: ~311 files
- 2PC UNSURE: 7 files

**After applying improvements**:
- 2PC LUG: 495 files (+3)
- 2PC STUD: 313 files (+2)
- 2PC UNSURE: 2 files (-5, 71.4% reduction)

## Technical Details

### Z-Depth Extraction Logic

Scans first 100 lines of G-code for Z-depth patterns:
```python
z_matches = re.findall(r'Z-(\d+\.?\d*)', line, re.IGNORECASE)
for z_str in z_matches:
    z_val = float(z_str)
    if 0.1 <= z_val <= 1.0:  # Reasonable recess depth range
        z_depths.append(z_val)
```

**LUG shelf pattern**: Z-0.31 to Z-0.35 (shelf for STUD insert)

### Thickness + Hub Logic

**STUD pattern**:
- Thickness: 0.70" - 0.80" (0.75" typical, with tolerance)
- Hub: 0.20" - 0.30" (0.25" typical, with tolerance)
- Total: ~1.00" (often written in title as "1.00")

**LUG pattern**:
- Thickness: >0.75" (typically 1.0" or greater)
- Hub: 0.20" - 0.30" (same as STUD)
- Key: If thickness > 0.75" → **always LUG** (STUDs max out at 0.75")

## Next Steps

1. ✅ Testing complete - 71.4% improvement verified
2. **Rescan database** to apply improvements to all files
3. Consider manual review of 2 remaining UNSURE files
4. Future: Add special case for 0.5" hub with recess (STUD variant)
5. Future: Consider "INNER" vs "OUTER" keyword patterns

## Files Changed

- `improved_gcode_parser.py`:
  - Lines 237-244: Integration of advanced analysis
  - Lines 976-1055: New `_analyze_2pc_gcode()` method
  - Lines 818-819: Enhanced thickness parsing for "TH" abbreviation

## Testing

Created `test_2pc_logic_improvements.py` to validate improvements on all 7 UNSURE files.

**Results**: 71.4% success rate (5/7 files classified)

## Conclusion

The advanced 2PC detection successfully leverages:
1. **Physical machining patterns** (LUG shelf depth)
2. **Part dimensional rules** (thickness limits)
3. **Combined characteristics** (thickness + hub height)
4. **Improved parsing** (TH abbreviation support)

This multi-layered approach provides robust classification with proper confidence levels, reducing UNSURE classifications from 7 to 2 files (71.4% improvement).
