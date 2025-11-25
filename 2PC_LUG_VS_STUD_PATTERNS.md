# 2PC LUG vs STUD - Distinguishing Patterns

## Key Discovery: G-Code Comments as Strong Indicators

**LUG files**: 50% contain "(LUG PLATE. CUT X.XX)" comment
**STUD files**: 80% contain "(STUD PLATE. CUT X.XX)" comment

This is a **strong, reliable indicator** that can be used when title patterns are ambiguous!

## Complete Classification Strategy

### Priority 1: Title Keywords (Highest Confidence)

**LUG Indicators**:
- Explicit "LUG" keyword (most common)
- "2PC LUG" in title

**STUD Indicators**:
- Explicit "STUD" keyword
- "IS 2PC" (Inner Stud / 2-Piece) ← **ADD THIS**
- "OS 2PC" (Outer Stud / 2-Piece) ← **ADD THIS**
- "2PC STUD" in title

**Confidence**: HIGH (if in title), MEDIUM (if in comments)

### Priority 2: G-Code Comments (NEW - Strong Indicator)

**LUG Indicators**:
- "(LUG PLATE" in G-code comments
- Found in 50% of LUG files

**STUD Indicators**:
- "(STUD PLATE" in G-code comments
- Found in 80% of STUD files

**Confidence**: HIGH (very reliable when present)

### Priority 3: Thickness Heuristic (Low Confidence)

**LUG Characteristics**:
- Typically **thicker** (≥1.0")
- Receives the STUD component
- Example thickness range: 0.75" to 3.5"

**STUD Characteristics**:
- Typically **thinner** (<1.0")
- Inserts into the LUG component
- Example thickness range: 0.55" to 1.5"

**Confidence**: LOW (significant overlap in thickness ranges)

### Priority 4: Physical G-Code Features (Complex, Research Needed)

**LUG Features**:
- May have counterbore operation (step to receive STUD)
- Deeper drilling
- OP1 operations primarily

**STUD Features**:
- May have raised hub/stud feature (created in OP2)
- Shallower drilling
- OP2 facing operations to create raised stud

**Confidence**: MEDIUM (requires complex G-code analysis)

## Recommended Implementation

### Phase 1: Add IS/OS Pattern Detection (Immediate)

```python
if '2PC' in combined_upper or '2 PC' in combined_upper:
    if 'LUG' in combined_upper:
        return '2PC LUG', confidence
    elif 'STUD' in combined_upper:
        return '2PC STUD', confidence
    elif 'IS 2PC' in combined_upper or 'IS2PC' in combined_upper:
        # IS = Inner Stud / 2-Piece
        return '2PC STUD', 'MEDIUM'
    elif 'OS 2PC' in combined_upper or 'OS2PC' in combined_upper:
        # OS = Outer Stud / 2-Piece
        return '2PC STUD', 'MEDIUM'
    else:
        return '2PC UNSURE', confidence
```

**Impact**: ~45-66 files correctly classified as STUD

### Phase 2: Add G-Code Comment Detection (New Discovery!)

```python
# After checking title, check G-code comments
if result.spacer_type == '2PC UNSURE' and lines:
    # Scan first 20 lines for LUG/STUD PLATE comments
    for line in lines[:20]:
        line_upper = line.upper()

        if 'LUG PLATE' in line_upper or '(LUG' in line_upper:
            result.spacer_type = '2PC LUG'
            result.detection_method = 'GCODE_COMMENT'
            result.detection_confidence = 'HIGH'
            break
        elif 'STUD PLATE' in line_upper or '(STUD' in line_upper:
            result.spacer_type = '2PC STUD'
            result.detection_method = 'GCODE_COMMENT'
            result.detection_confidence = 'HIGH'
            break
```

**Impact**: Additional ~30-50 files classified with HIGH confidence

### Phase 3: Add Thickness Heuristic (Fallback)

```python
# If still UNSURE after title and comment checks, use thickness
if result.spacer_type == '2PC UNSURE' and result.thickness:
    if result.thickness >= 1.0:
        # Thicker parts typically LUG (receiver)
        result.spacer_type = '2PC LUG'
        result.detection_confidence = 'LOW'
    else:
        # Thinner parts typically STUD (insert)
        result.spacer_type = '2PC STUD'
        result.detection_confidence = 'LOW'
```

**Impact**: Remaining ~10-20 files classified with LOW confidence

## Expected Results

**Current 2PC UNSURE**: 124 files (15.3%)

**After Phase 1 (IS/OS patterns)**: ~58-79 UNSURE (7.2-9.8%)
- Improvement: 45-66 files → 2PC STUD

**After Phase 2 (G-code comments)**: ~8-49 UNSURE (1.0-6.0%)
- Improvement: 30-50 files → 2PC LUG/STUD (HIGH confidence)

**After Phase 3 (thickness heuristic)**: ~0-10 UNSURE (0-1.2%)
- Improvement: 10-20 files → 2PC LUG/STUD (LOW confidence)

**Total**: 114-124 files (92-100% of UNSURE) → properly classified

## Example Files

### LUG Examples

**o70865**: "7IN DIA 108MM ID 3.5 THK --2PC"
- Has "(LUG PLATE. CUT 1.29)" comment in G-code
- Thickness: 3.50" (thick = receiver)
- Drill depth: 3.65"
- Clear LUG characteristics

### STUD Examples

**o62470**: "6.25 DIA 64.1MM ID .55 OS 2PC*"
- Title has "OS 2PC" pattern (Outer Stud) ← **Would be caught by Phase 1**
- Has "(STUD PLATE. CUT 1.04)" comment in G-code ← **Would be caught by Phase 2**
- Thickness: 0.55" (thin = insert)
- Drill depth: 0.90"
- OP2 has facing operations (creates raised stud)
- Clear STUD characteristics

**o62521**: "6.25 DIA 56.1MM ID .75 IS 2PC"
- Title has "IS 2PC" pattern (Inner Stud) ← **Would be caught by Phase 1**
- Thickness: 0.75" (thin = insert)
- Clear STUD characteristics

## Physical Differences (for reference)

### LUG (Receiver):
```
     _______________
    |               |
    |   [Counterbore for STUD to fit]
    |       |   |   |
    |       |   |   | ← Thicker body
    |       |___|   |
    |               |
    |_______________|
         Center Bore
```

### STUD (Insert):
```
     _______________
    |   [Raised Stud fits in LUG]
    |       |^^^|
    |       |^^^| ← Thinner body
    |       |^^^|
    |_______|^^^|___|
         Center Bore
```

## Implementation Priority

1. **Phase 1** (IS/OS patterns): **CRITICAL** - Easy, high impact, 45-66 files
2. **Phase 2** (G-code comments): **HIGH** - New discovery, high confidence, 30-50 files
3. **Phase 3** (thickness heuristic): **MEDIUM** - Low confidence but handles remaining edge cases

## Conclusion

The combination of:
1. Title patterns (including IS/OS)
2. **G-code comments (NEW - very reliable!)**
3. Thickness heuristics

...will classify **92-100% of 2PC UNSURE files** with varying confidence levels.

The G-code comment detection is a **major new discovery** that provides HIGH confidence classification when present.
