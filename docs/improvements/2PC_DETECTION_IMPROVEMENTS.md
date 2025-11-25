# 2PC Detection Improvements - Analysis and Recommendations

## Overview

2PC (2-Piece) spacers consist of two components that fit together:
- **LUG**: The outer piece/receiver (typically thicker)
- **STUD**: The inner piece/insert (typically thinner)

**Current Status**: 810 2PC programs in database
- 2PC LUG: 408 (50.4%)
- 2PC STUD: 278 (34.3%)
- 2PC UNSURE: 124 (15.3%)

## Current Detection Logic

The parser classifies 2PC parts using these patterns:

```python
if '2PC' in combined_upper or '2 PC' in combined_upper:
    if 'LUG' in combined_upper:
        return '2PC LUG', confidence
    elif 'STUD' in combined_upper:
        return '2PC STUD', confidence
    else:
        return '2PC UNSURE', confidence
```

**Strengths**:
- Detects explicit "2PC" keyword (98.8% coverage)
- Differentiates LUG vs STUD when keywords present

**Weaknesses**:
- 124 files (15.3%) classified as "2PC UNSURE"
- Doesn't detect "IS 2PC" or "OS 2PC" patterns for STUD classification
- No automatic pairing logic

## Title Pattern Analysis

### Keyword Frequency in 2PC Titles

| Keyword | Count | Percentage |
|---------|-------|------------|
| 2PC | 800 | 98.8% |
| DIA | 514 | 63.5% |
| ID | 476 | 58.8% |
| LUG | 209 | 25.8% |
| STUD | 108 | 13.3% |
| HC | 85 | 10.5% |
| IS | 45 | 5.6% |
| OS | 21 | 2.6% |

### LUG Title Patterns

**Common patterns**:
1. Explicit "LUG" keyword (most common)
   - "6.25IN 74MM LUG 1.25--2PC"
   - "6.25 DIA 74.4MM LUG 0.9 2PC"

2. "IS 2PC" pattern (Inner Spacer / 2-Piece)
   - Some LUG parts use "IS 2PC" but less common

3. Format: `[OD] [CB]MM LUG [THICKNESS] 2PC`

**Characteristics**:
- Typically **thicker** (0.75" to 2.25")
- Receives the STUD component
- May have counterbore to accept STUD

### STUD Title Patterns

**Common patterns**:
1. Explicit "STUD" keyword
   - "6.00 IN DIA 71MM STUD-2PC"
   - "6.25IN 74MM STUD 1.5 2PC"

2. "IS 2PC" pattern (Inner Stud / 2-Piece) - **VERY COMMON**
   - "6.25 DIA 60MM ID .75 IS 2PC"
   - "6.25 DIA 71.6MM ID .75 IS 2PC"
   - This is a major pattern NOT currently used for classification!

3. "OS 2PC" pattern (Outer Stud / 2-Piece)
   - "6.25 DIA 38.1MM ID .75 OS 2PC"
   - "6.25 DIA 66.6MM ID .75 OS 2PC"

4. Format: `[OD] DIA [CB]MM ID [THICKNESS] IS/OS 2PC`

**Characteristics**:
- Typically **thinner** (0.55" to 1.5")
- Inserts into the LUG component
- May have raised stud/hub feature

### Pattern: "IS 2PC" vs "OS 2PC"

**IS (Inner Stud)**:
- Stud component that fits inside the LUG
- More common pattern (45 occurrences)

**OS (Outer Stud)**:
- Stud component on outer diameter
- Less common (21 occurrences)

## Pairing Logic

2PC components pair together based on matching dimensions:

### Matching Criteria:
1. **Same Outer Diameter (OD)** - Critical
2. **Same Center Bore (CB)** - Critical (within ±0.5mm)
3. **Different Thickness** - LUG typically thicker than STUD
4. **Compatible Interface** - One has counterbore, one has stud

### Example Paired Group:

**OD=6.25", CB=54.1mm**:
- **LUG**: o62636 "6.25 DIA 54.1MM ID 1.00 2PC LUG" (Thick=1.00")
- **STUD**: o62480 "6.25 DIA 54.1MM ID .75 IS 2PC" (Thick=0.75")
- **STUD**: o62631 "6.25 IN 54.1/63.4MM .75 HC 2PC STUD" (Thick=0.75")

**Total Paired Groups Found**: 100+ groups with both LUG and STUD

## Recommended Improvements

### 1. Improve STUD Detection with "IS" and "OS" Patterns

**Problem**: Many STUD parts classified as "2PC UNSURE" because they use "IS 2PC" or "OS 2PC" instead of "STUD" keyword.

**Solution**: Add pattern detection for IS/OS:

```python
if '2PC' in combined_upper or '2 PC' in combined_upper:
    if 'LUG' in combined_upper:
        return '2PC LUG', confidence
    elif 'STUD' in combined_upper:
        return '2PC STUD', confidence
    elif 'IS 2PC' in combined_upper or 'IS2PC' in combined_upper:
        # "IS 2PC" = Inner Stud / 2-Piece
        return '2PC STUD', 'MEDIUM'
    elif 'OS 2PC' in combined_upper or 'OS2PC' in combined_upper:
        # "OS 2PC" = Outer Stud / 2-Piece
        return '2PC STUD', 'MEDIUM'
    else:
        return '2PC UNSURE', confidence
```

**Impact**: ~45-66 files (IS + OS patterns) → classified as "2PC STUD"

### 2. Add Automatic Pairing Detection

**Concept**: Detect which LUG and STUD programs pair together

**Benefits**:
- Better understanding of 2PC assemblies
- Validation: paired parts should have compatible dimensions
- Manufacturing: know which parts go together

**Implementation**:

```python
def find_2pc_pairs(programs):
    """Find matching LUG/STUD pairs based on OD and CB"""
    pairs = []

    lugs = [p for p in programs if p.spacer_type == '2PC LUG']
    studs = [p for p in programs if p.spacer_type == '2PC STUD']

    for lug in lugs:
        for stud in studs:
            # Match criteria
            od_match = abs(lug.outer_diameter - stud.outer_diameter) < 0.1
            cb_match = abs(lug.center_bore - stud.center_bore) < 0.5

            if od_match and cb_match:
                pairs.append((lug, stud))

    return pairs
```

**Database Schema Addition**:
```sql
ALTER TABLE programs ADD COLUMN paired_program TEXT;
-- Stores the program number of the matching LUG/STUD pair
```

### 3. Add 2PC-Specific Validation Rules

**Problem**: Current validation compares title dimensions to G-code, but for 2PC:
- Title dimensions often refer to the INTERFACE between parts
- G-code dimensions are for THIS part's actual machining

**Solution**: Skip or modify validation for 2PC parts

**Already Implemented**: CB/OB/thickness validation skipped for 2PC (commit 87fcd3a)

**Additional Considerations**:
- LUG parts: May have counterbore to accept STUD
- STUD parts: May have raised hub/stud feature
- Interface dimensions in title may not match machined dimensions

### 4. Improve 2PC UNSURE Classification

**Current**: 124 files (15.3%) classified as "2PC UNSURE"

**Possible reasons**:
1. Missing "LUG" or "STUD" keyword
2. Missing "IS" or "OS" pattern
3. Ambiguous titles

**Solution**: Use heuristics to classify UNSURE parts:

```python
# If thickness is known, use it to guess type
if result.spacer_type == '2PC UNSURE' and result.thickness:
    if result.thickness >= 1.0:
        # Thicker parts are typically LUG (receiver)
        result.spacer_type = '2PC LUG'
        result.detection_confidence = 'LOW'
    else:
        # Thinner parts are typically STUD (insert)
        result.spacer_type = '2PC STUD'
        result.detection_confidence = 'LOW'
```

**Impact**: Classify more of the 124 UNSURE files

## Implementation Priority

### Priority 1: IS/OS Pattern Detection (High Impact, Easy)

**Code Change**: Lines 487-496 in improved_gcode_parser.py

**Before**:
```python
if 'LUG' in combined_upper:
    return '2PC LUG', confidence
elif 'STUD' in combined_upper:
    return '2PC STUD', confidence
else:
    return '2PC UNSURE', confidence
```

**After**:
```python
if 'LUG' in combined_upper:
    return '2PC LUG', confidence
elif 'STUD' in combined_upper:
    return '2PC STUD', confidence
elif 'IS 2PC' in combined_upper or 'IS2PC' in combined_upper:
    return '2PC STUD', 'MEDIUM'  # IS = Inner Stud
elif 'OS 2PC' in combined_upper or 'OS2PC' in combined_upper:
    return '2PC STUD', 'MEDIUM'  # OS = Outer Stud
else:
    return '2PC UNSURE', confidence
```

**Test Files**:
- o62003: "6.25 DIA 60MM ID .75 IS 2PC" → Should become "2PC STUD"
- o62368: "6.25 DIA 63.4MM ID .75 OS 2PC" → Should become "2PC STUD"

**Expected Impact**: ~45-66 files move from "2PC UNSURE" → "2PC STUD"

### Priority 2: Thickness-Based UNSURE Classification (Medium Impact, Easy)

Add heuristic classification for remaining UNSURE parts based on thickness.

**Expected Impact**: ~30-50 files classified with LOW confidence

### Priority 3: Automatic Pairing Logic (Low Impact, Complex)

Implement pairing detection and add paired_program column to database.

**Expected Impact**: Better understanding of assemblies, improved validation

## Summary

**Current 2PC Detection**:
- ✓ Detects "2PC" keyword (98.8%)
- ✓ Detects "LUG" and "STUD" keywords
- ✗ Misses "IS 2PC" and "OS 2PC" patterns for STUD
- ✗ 124 files (15.3%) classified as UNSURE
- ✗ No automatic pairing logic

**Recommended Improvements**:
1. **Add IS/OS pattern detection** → ~45-66 files better classified
2. **Add thickness heuristic** → ~30-50 files classified
3. **Add pairing logic** → Better assembly understanding

**Total Impact**: ~75-116 files (62-94% of UNSURE) → properly classified

**Next Step**: Implement IS/OS pattern detection (easiest, highest impact)
