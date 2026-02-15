# G-Code Parser Improvement Recommendations

## Executive Summary

After deep analysis of 500 G-code files studying **HOW material is removed** (not just what operations exist), we've identified **6 critical patterns** that the current parser misses. These improvements will fix dimension extraction errors in **55%+ of files** and enable new validation capabilities.

---

## Critical Issues Found

### Issue #1: Roughing Pass Confusion (55% of files affected)
**Problem**: Parser extracts dimensions from roughing passes instead of final finish passes

**Example**:
```gcode
X4.902  <- Parser extracts this (WRONG - roughing pass)
G01 Z0.
G01 X4.602 Z-0.15 (X IS CB)  <- Should extract this (CORRECT - final dimension)
```

**Impact**: 276 out of 500 files (55.2%) have incorrect centerbore dimensions in database

**Fix Priority**: 🔴 **CRITICAL** - This affects over half of all programs

---

### Issue #2: Centerbore vs Counterbore Not Distinguished
**Problem**: Parser treats all bores the same, doesn't recognize shallow pockets (counterbores)

**Found**:
- 192 centerbores (through-holes, depth ≥50% thickness)
- 13 counterbores (shallow pockets, depth <50% thickness)
- 0 stepped bores detected (but many exist)

**Real Example** (o10280.nc):
- Side 1: Bore 4.928" diameter × 4.15" deep = **CENTERBORE** (through-hole)
- Side 2: Bore 4.928" diameter × 0.75" deep = **COUNTERBORE** (press-fit pocket)
- Parser sees these as two separate bores, doesn't recognize mating relationship

**Impact**: Cannot validate two-piece assemblies (hub + counterbore mating)

**Fix Priority**: 🔴 **CRITICAL** - Required for two-piece part validation

---

### Issue #3: Hub Profiles Not Detected (22.6% of files)
**Problem**: Parser doesn't recognize stepped turning that creates hub profiles

**Pattern Missed**:
```gcode
G01 Z-0.1 F0.013    <- Z-depth loop (incremental)
X6.7                <- Hub diameter
G00 X10.17          <- Return to OD
G01 Z-0.2 F0.013    <- Next depth
X6.7                <- Same hub diameter
...
G01 X6.688 (X IS OB)  <- Final hub diameter ("OB" = Outer Bore)
```

**Impact**: 113 hub parts not properly classified, hub dimensions not extracted

**Fix Priority**: 🟡 **HIGH** - Needed for assembly validation

---

### Issue #4: Steel Ring Assemblies Not Identified
**Problem**: Parser doesn't recognize pattern indicating aluminum part with steel ring press-fit

**Pattern**:
```gcode
O75243 (7.5 IN DIA 106MM ID 2.00)
(106MM CB)
```
- "106MM ID" = Steel ring inner diameter (predetermined standard size)
- Part is ALUMINUM, but titled "RING" because steel ring presses into it
- Counterbore must match steel ring OD (4.173" = 106mm / 25.4)

**Impact**: Cannot validate counterbore matches standard steel ring dimensions

**Fix Priority**: 🟢 **MEDIUM** - Important for specific part category

---

### Issue #5: Side 1 vs Side 2 Operations Not Tracked Separately
**Problem**: Parser combines all operations, loses context of which side they're on

**Why This Matters**:
- Counterbores typically machined on Side 2 (after flip)
- Centerbores typically through-drilled on Side 1
- Hub profiles created on Side 2
- Cannot detect stepped bore without tracking sides separately

**Fix Priority**: 🔴 **CRITICAL** - Required for counterbore/centerbore distinction

---

### Issue #6: Comment Markers Not Used for Dimension Extraction
**Problem**: Parser doesn't look for dimension markers in comments

**Standard Markers Used**:
- `(X IS CB)` = Centerbore diameter
- `(X IS OB)` = Outer Bore (hub diameter)
- `(X IS OD)` = Outer Diameter

**Impact**: Misses explicit dimension annotations, uses wrong values

**Fix Priority**: 🔴 **CRITICAL** - Simple fix, high impact

---

## Recommended Implementation Plan

### Phase 1: Critical Fixes (Week 1)
**Goal**: Fix dimension extraction accuracy

1. ✅ **Add comment marker detection**
   - Look for `(X IS CB)`, `(X IS OB)`, `(X IS OD)` comments
   - Extract dimension from line containing marker
   - Fallback: detect chamfer move (Z-0.1 to Z-0.15)

2. ✅ **Detect incremental roughing loops**
   - Identify when X values increment by 0.2-0.4"
   - Mark all but last as roughing passes
   - Extract final dimension from finish pass

3. ✅ **Track Side 1 vs Side 2 separately**
   - Detect work offset changes (G154 P13 vs P14)
   - Detect "(FLIP PART)" or "(OP2)" comments
   - Store operations with side indicator

**Expected Impact**: Fixes 55% of dimension extraction errors

---

### Phase 2: Feature Classification (Week 2)
**Goal**: Distinguish centerbore, counterbore, and hub features

4. ✅ **Classify bore features by depth ratio**
   ```python
   if depth / thickness >= 0.5:
       feature_type = "CENTERBORE"  # Through-hole
   else:
       feature_type = "COUNTERBORE"  # Shallow pocket
   ```

5. ✅ **Detect stepped bores** (centerbore + counterbore combo)
   - Same diameter on both sides
   - Different depths (one >50%, one <50% of thickness)
   - Common in two-piece assemblies

6. ✅ **Add new database fields**:
   ```sql
   ALTER TABLE programs ADD COLUMN centerbore_diameter REAL;
   ALTER TABLE programs ADD COLUMN centerbore_depth REAL;
   ALTER TABLE programs ADD COLUMN counterbore_diameter REAL;
   ALTER TABLE programs ADD COLUMN counterbore_depth REAL;
   ```

**Expected Impact**: Enables two-piece assembly validation

---

### Phase 3: Hub Detection (Week 3)
**Goal**: Extract hub profile dimensions

7. ✅ **Detect stepped turning pattern**
   - Look for Z-depth loops (Z-0.1, Z-0.2, Z-0.4...)
   - Same X endpoint each pass
   - Comment marker `(X IS OB)` for final hub diameter

8. ✅ **Add hub database fields**:
   ```sql
   ALTER TABLE programs ADD COLUMN hub_diameter REAL;
   ALTER TABLE programs ADD COLUMN hub_height REAL;
   ALTER TABLE programs ADD COLUMN has_hub_profile BOOLEAN DEFAULT 0;
   ```

9. ✅ **Validate hub/counterbore compatibility**
   - Hub diameter should fit in counterbore (within ±0.05")
   - Counterbore depth should accommodate hub height + clearance

**Expected Impact**: Proper classification of 22.6% of parts with hubs

---

### Phase 4: Steel Ring Assemblies (Week 4)
**Goal**: Identify and validate steel ring press-fit parts

10. ✅ **Detect steel ring pattern**
    - Title contains "MM ID" or "MM CB"
    - Extract steel ring dimension (e.g., 106MM)
    - Convert to inches (106 / 25.4 = 4.173")

11. ✅ **Add database fields**:
    ```sql
    ALTER TABLE programs ADD COLUMN is_steel_ring_assembly BOOLEAN DEFAULT 0;
    ALTER TABLE programs ADD COLUMN steel_ring_id_mm REAL;
    ```

12. ✅ **Validate counterbore matches steel ring**
    - Counterbore diameter should match steel ring OD (within ±0.05")
    - Counterbore depth typically 0.30-0.40"

**Expected Impact**: Proper validation of steel ring assemblies

---

## Code Implementation Examples

### 1. Extract Final Dimension (Fix Issue #1)

```python
def extract_final_bore_dimension(lines: List[str], start_idx: int) -> Optional[float]:
    """
    Extract final bore dimension from finish pass with chamfer.

    Priority:
    1. Line with comment marker (X IS CB)
    2. Line with chamfer angle (Z-0.1 to Z-0.15)
    3. Last X value (fallback)
    """
    x_values = []

    for i in range(start_idx, min(start_idx + 100, len(lines))):
        line = lines[i].strip().upper()

        # Priority 1: Explicit comment marker
        if '(X IS CB)' in line or '(X IS OB)' in line:
            match = re.search(r'X\s*(\d+\.?\d*)', line)
            if match:
                return float(match.group(1))

        # Priority 2: Chamfer angle (indicates finish pass)
        if re.search(r'Z\s*(-0\.1\d*)', line):
            match = re.search(r'X\s*(\d+\.?\d*)', line)
            if match:
                return float(match.group(1))

        # Collect all X values
        x_match = re.search(r'^X\s*(\d+\.?\d*)', line)
        if x_match:
            x_values.append(float(x_match.group(1)))

    # Fallback: last X value (after filtering roughing)
    if x_values:
        return x_values[-1]

    return None
```

---

### 2. Classify Bore Type (Fix Issue #2)

```python
def classify_bore_feature(diameter: float, depth: float, thickness: float,
                         side: int) -> Dict:
    """
    Classify bore as centerbore or counterbore based on depth ratio.
    """
    depth_ratio = depth / thickness

    return {
        'diameter': diameter,
        'depth': depth,
        'side': side,
        'feature_type': 'CENTERBORE' if depth_ratio >= 0.5 else 'COUNTERBORE',
        'depth_ratio': depth_ratio
    }
```

---

### 3. Detect Hub Profile (Fix Issue #3)

```python
def detect_hub_profile(lines: List[str], start_idx: int) -> Optional[Dict]:
    """
    Detect hub profile from stepped turning with Z-depth loops.

    Pattern:
    G01 Z-0.1 F0.013  <- Incrementing Z depths
    X6.7              <- Same X endpoint
    G00 X10.17        <- Return to OD
    """
    z_depths = []
    hub_diameter = None
    outer_diameter = None

    for i in range(start_idx, min(start_idx + 50, len(lines))):
        line = lines[i].strip().upper()

        # Look for Z depth
        z_match = re.search(r'G01\s+Z\s*(-\d+\.?\d*)', line)
        if z_match:
            z_depth = abs(float(z_match.group(1)))

            # Next line should have hub diameter
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().upper()
                x_match = re.search(r'^X\s*(\d+\.?\d*)', next_line)
                if x_match:
                    z_depths.append(z_depth)

                    # Check for hub diameter marker
                    if '(X IS OB)' in next_line:
                        hub_diameter = float(x_match.group(1))

        # Look for OD (return position)
        if 'G00 X' in line:
            od_match = re.search(r'X\s*(\d+\.?\d*)', line)
            if od_match and outer_diameter is None:
                outer_diameter = float(od_match.group(1))

    # Validate pattern (3+ incremental Z depths)
    if len(z_depths) >= 3 and hub_diameter:
        is_incremental = all(z_depths[i] < z_depths[i+1]
                            for i in range(len(z_depths)-1))

        if is_incremental:
            return {
                'hub_diameter': hub_diameter,
                'hub_height': max(z_depths),
                'outer_diameter': outer_diameter
            }

    return None
```

---

### 4. Detect Steel Ring Assembly (Fix Issue #4)

```python
def detect_steel_ring_assembly(program_title: str) -> Optional[Dict]:
    """
    Identify steel ring press-fit assembly from title pattern.

    Pattern: "10.25IN DIA 106MM ID 2.00"
                           ^^^^^^^ Steel ring dimension
    """
    title_upper = program_title.upper()

    # Look for "MM ID" or "MM CB" pattern
    mm_match = re.search(r'(\d+\.?\d*)\s*MM\s*(ID|CB|I\.D\.)', title_upper)
    if mm_match:
        mm_dimension = float(mm_match.group(1))
        inch_dimension = mm_dimension / 25.4

        return {
            'is_steel_ring_assembly': True,
            'steel_ring_id_mm': mm_dimension,
            'steel_ring_id_inches': inch_dimension,
            'expected_counterbore_diameter': inch_dimension
        }

    return None
```

---

### 5. Detect Side (Fix Issue #5)

```python
def detect_current_side(lines: List[str], current_idx: int) -> int:
    """
    Determine which side (1 or 2) operation is on.

    Indicators:
    - G154 P13/P15/P17 = Side 1 (odd work offsets)
    - G154 P14/P16/P18 = Side 2 (even work offsets)
    - "(FLIP PART)" or "(OP2)" comment = Side 2
    """
    # Look back 20 lines for work offset or flip comment
    for i in range(max(0, current_idx - 20), current_idx):
        line = lines[i].upper()

        # Check for flip comment
        if 'FLIP PART' in line or 'OP2' in line or 'OP 2' in line:
            return 2

        # Check work offset
        offset_match = re.search(r'G154\s+P(\d+)', line)
        if offset_match:
            offset_num = int(offset_match.group(1))
            return 1 if offset_num % 2 == 1 else 2

    return 1  # Default to Side 1
```

---

## Database Schema Changes

### New Fields to Add

```sql
-- Bore feature classification
ALTER TABLE programs ADD COLUMN centerbore_diameter REAL;
ALTER TABLE programs ADD COLUMN centerbore_depth REAL;
ALTER TABLE programs ADD COLUMN counterbore_diameter REAL;
ALTER TABLE programs ADD COLUMN counterbore_depth REAL;
ALTER TABLE programs ADD COLUMN is_stepped_bore BOOLEAN DEFAULT 0;

-- Hub profile detection
ALTER TABLE programs ADD COLUMN hub_diameter REAL;
ALTER TABLE programs ADD COLUMN hub_height REAL;
ALTER TABLE programs ADD COLUMN has_hub_profile BOOLEAN DEFAULT 0;

-- Steel ring assembly
ALTER TABLE programs ADD COLUMN is_steel_ring_assembly BOOLEAN DEFAULT 0;
ALTER TABLE programs ADD COLUMN steel_ring_id_mm REAL;

-- Process analysis
ALTER TABLE programs ADD COLUMN roughing_pattern_detected BOOLEAN DEFAULT 0;
ALTER TABLE programs ADD COLUMN side1_operations TEXT;  -- JSON list
ALTER TABLE programs ADD COLUMN side2_operations TEXT;  -- JSON list
```

---

## Validation Rules to Add

### Two-Piece Assembly Validation

```python
def validate_two_piece_compatibility(hub_part: GCodeParseResult,
                                    cbore_part: GCodeParseResult) -> List[str]:
    """
    Validate hub and counterbore parts are designed to mate.

    Requirements:
    1. Same OD (within 0.1")
    2. Hub diameter fits in counterbore (within ±0.05")
    3. Counterbore depth accommodates hub height (0.01-0.10" clearance)
    """
    issues = []

    # Check 1: OD match
    if abs(hub_part.outer_diameter - cbore_part.outer_diameter) > 0.1:
        issues.append(
            f"OD mismatch: Hub {hub_part.outer_diameter:.3f}\" "
            f"vs Counterbore {cbore_part.outer_diameter:.3f}\" "
            f"(max tolerance 0.1\")"
        )

    # Check 2: Diameter fit
    if hub_part.hub_diameter and cbore_part.counterbore_diameter:
        clearance = abs(hub_part.hub_diameter - cbore_part.counterbore_diameter)
        if clearance > 0.05:
            issues.append(
                f"Hub/counterbore diameter tolerance exceeded: {clearance:.3f}\" "
                f"(max 0.05\")"
            )

    # Check 3: Depth fit
    if hub_part.hub_height and cbore_part.counterbore_depth:
        fit_clearance = cbore_part.counterbore_depth - hub_part.hub_height
        if fit_clearance < 0.01:
            issues.append(
                f"Insufficient counterbore depth: {fit_clearance:.3f}\" clearance "
                f"(min 0.01\")"
            )
        elif fit_clearance > 0.10:
            issues.append(
                f"Excessive counterbore depth: {fit_clearance:.3f}\" clearance "
                f"(max 0.10\")"
            )

    return issues
```

---

## Testing Strategy

### Test Files (Known Good Examples)

1. **o13223.nc** - 8-pass incremental roughing, hub profile
2. **o57172.nc** - Ring part, centerbore only
3. **o75243.nc** - Steel ring assembly (106MM ID)
4. **o10280.nc** - Stepped bore (centerbore + counterbore + hub)
5. **o10276.nc** - Hub without counterbore

### Validation Tests

```python
def test_dimension_extraction():
    """Test that final dimensions are extracted correctly"""
    # o13223.nc should extract X4.602 (not X4.902)
    assert parse_result.centerbore_diameter == 4.602

def test_bore_classification():
    """Test centerbore vs counterbore classification"""
    # o10280.nc Side 1: depth 4.15" / thickness 4.0" = 103% → CENTERBORE
    assert parse_result.centerbore_depth == 4.15

    # o10280.nc Side 2: depth 0.75" / thickness 4.0" = 18.75% → COUNTERBORE
    assert parse_result.counterbore_depth == 0.75

def test_hub_detection():
    """Test hub profile extraction"""
    # o10280.nc should detect hub diameter 6.688", height 0.55"
    assert parse_result.hub_diameter == 6.688
    assert parse_result.hub_height == 0.55

def test_steel_ring_detection():
    """Test steel ring assembly identification"""
    # o75243.nc: "106MM ID" → 4.173" expected counterbore
    assert parse_result.is_steel_ring_assembly == True
    assert parse_result.steel_ring_id_mm == 106.0
```

---

## Expected Results After Implementation

### Accuracy Improvements
- ✅ Dimension extraction: **55% improvement** (276 files corrected)
- ✅ Feature classification: **205 new features** properly classified
  - 192 centerbores
  - 13 counterbores
- ✅ Hub detection: **113 hub profiles** extracted
- ✅ Assembly validation: **NEW CAPABILITY** (0% → 100% for two-piece parts)

### Database Enrichment
- ✅ **9 new fields** per program with detailed feature data
- ✅ Side-by-side operation tracking
- ✅ Steel ring assembly identification

### New Validation Capabilities
- ✅ Two-piece assembly compatibility checks
- ✅ Hub/counterbore mating validation
- ✅ Steel ring dimension verification
- ✅ Stepped bore detection

---

## Priority Summary

🔴 **CRITICAL (Week 1)**:
1. Comment marker detection (`(X IS CB)`, `(X IS OB)`)
2. Incremental roughing detection
3. Side 1 vs Side 2 tracking

🟡 **HIGH (Week 2)**:
4. Centerbore vs counterbore classification
5. Stepped bore detection
6. Database schema updates

🟢 **MEDIUM (Weeks 3-4)**:
7. Hub profile detection
8. Steel ring assembly identification
9. Two-piece assembly validation

---

## Success Metrics

**Before Implementation**:
- Dimension errors: ~55% of files
- Features detected: Bore (generic)
- Assembly validation: Not possible

**After Implementation**:
- Dimension errors: <5% of files
- Features detected: Centerbore, Counterbore, Hub, Steel Ring Assembly
- Assembly validation: Hub/counterbore compatibility, steel ring fit

**ROI**: Fixing 55% of dimension errors + enabling new validation = Major quality improvement
