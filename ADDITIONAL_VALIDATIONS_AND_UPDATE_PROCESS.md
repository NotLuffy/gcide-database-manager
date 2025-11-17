# Additional Multi-Method Validations & Update Process

## Current Multi-Method Validations ✓

We currently have these cross-validation methods working:

1. **Thickness Validation (3 methods)**
   - Title specification
   - P-code mapping (P13-P24 → thickness)
   - Drill depth calculation (drill - hub - 0.15)

2. **Hub Height Validation (3 methods)**
   - Title extraction (HC patterns)
   - OP2 Z-depth analysis (deepest facing cut)
   - Default 0.50" (standard hub height)

3. **CB Validation (2 methods)**
   - Title extraction (XX/YY or XXMM patterns)
   - G-code BORE operation (smallest X with Z depth)

4. **OB Validation (2 methods)**
   - Title extraction (XX/YY patterns for hub-centric)
   - G-code OP2 progressive facing (smallest X in facing sequence)

---

## Additional Multi-Method Validations We Can Add

### 1. **Outer Diameter (OD) Validation** 🎯 HIGH PRIORITY

**Current:** Only extracted from title

**Additional Methods:**
- **Method A: Maximum X Value in Facing Operations**
  - OD/2 = largest X value in turning operations
  - Typical pattern: Final facing pass goes to OD
  ```gcode
  T303 (TURN TOOL)
  X2.875  ← This is OD/2 = 2.875" → OD = 5.75"
  ```

- **Method B: Spindle Speed Analysis**
  - Surface feet per minute (SFM) is constant for aluminum
  - SFM = (OD × π × RPM) / 12
  - If we see RPM in G-code, can calculate OD
  ```gcode
  G97 S550  ← RPM = 550
  ; For 5.75" OD aluminum at 550 SFM
  ```

- **Method C: Filename Pattern**
  - Files often organized by OD (folders: 5.75, 6, etc.)
  - File path can hint at OD

**Benefits:**
- Validate title OD against actual machining operations
- Detect if wrong OD programmed
- Cross-check all 3 sources

**Implementation Difficulty:** 🟢 Easy (Method A), 🟡 Medium (Method B), 🟢 Easy (Method C)

---

### 2. **Material Validation from Feeds & Speeds** 🎯 HIGH PRIORITY

**Current:** Only keyword detection from title (Steel, Stainless, SS)

**Additional Methods:**
- **Method A: Feed Rate Analysis**
  - Aluminum: 0.006-0.012 IPR (inches per revolution)
  - Steel: 0.003-0.006 IPR (slower)
  - Stainless: 0.002-0.004 IPR (slowest)
  ```gcode
  G01 X2.5 Z-0.5 F0.006  ← F=0.006 IPR → likely Aluminum
  G01 X2.5 Z-0.5 F0.003  ← F=0.003 IPR → likely Steel
  ```

- **Method B: Spindle Speed (RPM)**
  - Aluminum: 600-1200 RPM for 5.75" OD
  - Steel: 300-600 RPM (slower)
  - Stainless: 200-400 RPM (slowest)

- **Method C: Tool Calls**
  - Steel programs may use different tool numbers
  - Carbide inserts vs HSS (high-speed steel)

**Benefits:**
- Detect material mismatches (title says aluminum but feeds are for steel)
- Prevent running wrong material at wrong speeds
- **Critical for part quality and tool life**

**Implementation Difficulty:** 🟡 Medium

---

### 3. **Counterbore Depth Validation (STEP Parts)** 🎯 MEDIUM PRIORITY

**Current:** Counterbore diameter extracted from title, depth not validated

**Additional Methods:**
- **Method A: OP1 Boring Z-Depth**
  - STEP parts have two bore depths
  - First depth = counterbore depth
  - Second depth = full thickness
  ```gcode
  T121 (BORE)
  G01 X3.307 Z-0.75   ← Counterbore depth = 0.75"
  G01 X2.795 Z-2.0    ← Full depth = 2.0"
  ```

- **Method B: Two-Stage Boring Pattern**
  - Detect two distinct X values with different Z depths
  - Larger X (counterbore) stops at shallower Z
  - Smaller X (CB) goes to full depth

**Benefits:**
- Ensure counterbore depth is correct
- Validate STEP part dimensions completely

**Implementation Difficulty:** 🟡 Medium

---

### 4. **Program Number Cross-Validation** 🎯 HIGH PRIORITY

**Current:** Only checks filename vs internal program number

**Additional Methods:**
- **Method A: Title Program Number**
  - Some titles include program number
  - Example: "o58436 - 5.75IN DIA..."

- **Method B: Comment Block Program Number**
  - Check multiple comment locations
  - First line, header block, end of file

- **Method C: Database Lookup**
  - Check if program number already exists
  - Flag duplicates or conflicts

**Benefits:**
- Prevent duplicate program numbers
- Ensure filename matches internal number
- Catch copy/paste errors

**Implementation Difficulty:** 🟢 Easy

---

### 5. **P-Code Consistency Validation** 🎯 MEDIUM PRIORITY

**Current:** Extract P-codes and use for thickness

**Additional Methods:**
- **Method A: P-Code Pairing Validation**
  - P-codes should come in pairs (P15/P16, P17/P18, etc.)
  - Odd P-code = OP1, Even P-code = OP2
  - Flag if only one found or mismatched pairs

- **Method B: P-Code vs Part Type**
  - P17/P18 should only be hub-centric (1.25" total)
  - P15/P16 should be standard (1.00" total)
  - P13/P14 or P23/P24 should be STEP
  - Flag if P-code doesn't match detected part type

- **Method C: Multiple P-Codes Found**
  - Should only be one pair per program
  - Multiple pairs indicate copy/paste error

**Benefits:**
- Ensure work offsets are correct
- Catch wrong P-code for part type
- Prevent setup errors on machine

**Implementation Difficulty:** 🟢 Easy

---

### 6. **2-Piece Part Matching** 🎯 LOW PRIORITY (Future)

**Current:** Detect 2PC parts, but don't match pairs

**Additional Methods:**
- **Method A: LUG+STUD Detection**
  - Find matching pairs with same OD/CB
  - LUG (thicker) + STUD (thinner)
  - Suggest which programs go together

- **Method B: Thickness Pairing**
  - 2PC parts typically: 0.75" + 0.25" = 1.00" total
  - Or 1.00" + 0.50" = 1.50" total
  - Find parts that add up correctly

- **Method C: Database Search**
  - Search for programs with matching OD/CB
  - Different thickness
  - Same customer/order (if tracked)

**Benefits:**
- Help find matching pairs
- Prevent running wrong combinations
- Assembly verification

**Implementation Difficulty:** 🔴 Hard (requires database queries and matching logic)

---

### 7. **Tolerance Stack-Up Analysis** 🎯 LOW PRIORITY (Advanced)

**Current:** Individual dimension tolerances only

**Additional Methods:**
- **Method A: Hub Fit Analysis (Hub-Centric)**
  - CB + bearing press fit tolerance
  - OB must clear hub by specific amount
  - Validate: `OB - CB > minimum_clearance`

- **Method B: Bolt Circle Diameter (BCD)**
  - For parts with bolt holes
  - Validate hole pattern vs OD
  - Ensure bolts don't interfere

- **Method C: Wall Thickness**
  - Minimum wall between CB and OD
  - Safety factor for strength
  - Flag dangerously thin walls

**Benefits:**
- Catch design errors before cutting
- Ensure part will function correctly
- Prevent structural failures

**Implementation Difficulty:** 🔴 Hard (requires engineering calculations)

---

## Update Process & Re-Scanning

### When to Re-Scan Files

**Option 1: Manual Re-Scan (Current Behavior)**
- User clicks "Scan Folder" button
- All files in folder are parsed
- Database is updated with new validation results
- **Use when:** You've fixed G-code files and want to verify

**Option 2: Automatic Re-Scan on File Change**
- Monitor file modification timestamps
- If `last_modified` in database < file's actual modification time → re-scan
- **Use when:** Files are being actively edited

**Option 3: Selective Re-Scan**
- Only re-scan files with ERROR status
- Or only files modified in last X days
- **Use when:** You have thousands of files and only want to check specific ones

### Current Implementation

**What happens during folder scan:**

1. **For Each File:**
   ```python
   # Check if program exists in database
   cursor.execute("SELECT program_number FROM programs WHERE program_number = ?", (prog_num,))
   exists = cursor.fetchone()

   if exists:
       # UPDATE existing record (including all validation fields)
       UPDATE programs SET spacer_type=?, OD=?, thickness=?, ..., validation_status=?, ... WHERE program_number=?
   else:
       # INSERT new record
       INSERT INTO programs VALUES (...)
   ```

2. **Database is Updated:**
   - Old validation results are **overwritten**
   - New parse results replace old data
   - Validation status changes from ERROR → PASS if file was fixed

3. **GUI Refreshes:**
   - Treeview is repopulated
   - Colors update based on new validation status
   - RED files become GREEN if fixed

### Recommended: Add "Re-Scan Changed Files" Button

**New Feature:**
```python
def rescan_changed_files(self):
    """Re-scan only files that have been modified since last scan"""
    cursor = self.conn.cursor()
    cursor.execute("SELECT program_number, file_path, last_modified FROM programs")

    updated = 0
    for row in cursor.fetchall():
        prog_num, file_path, db_modified = row

        if os.path.exists(file_path):
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

            # If file is newer than database record
            if file_modified > db_modified:
                # Re-parse and update
                result = self.parse_gcode_file(file_path)
                if result:
                    self.update_database_record(result)
                    updated += 1

    messagebox.showinfo("Re-Scan Complete", f"Updated {updated} changed files")
    self.refresh_list()
```

**Benefits:**
- Much faster than full folder scan
- Only processes files that changed
- Automatically detects which files need validation update

---

## Priority Implementation Order

### Phase 1: High Priority (Immediate Value) 🎯

1. **OD Validation from G-code (Method A: Max X value)**
   - Easy to implement
   - Catches major errors (wrong OD programmed)
   - Cross-validates title

2. **Material from Feeds & Speeds**
   - Critical for safety (wrong speeds destroy tools/parts)
   - Medium difficulty but high impact

3. **Program Number Cross-Validation**
   - Prevent duplicate program numbers
   - Easy to implement

4. **P-Code Consistency Validation**
   - Catch work offset errors before they cause crashes
   - Easy to implement

### Phase 2: Medium Priority (Quality Improvements) 🎯

5. **Counterbore Depth Validation (STEP parts)**
   - Complete STEP part validation

6. **"Re-Scan Changed Files" Button**
   - Improve workflow efficiency

### Phase 3: Low Priority (Advanced Features) 🎯

7. **2-Piece Part Matching**
   - Nice to have, not critical

8. **Tolerance Stack-Up Analysis**
   - Advanced engineering validation

---

## Example: OD Validation Implementation

```python
def _extract_od_from_gcode(self, lines: List[str]) -> Optional[float]:
    """
    Extract OD from maximum X value in turning operations
    OD = max(X) * 2 (since X is radius on lathe)
    """
    max_x = 0.0
    in_turning = False

    for line in lines:
        line_upper = line.upper()

        # Track turning operations (T303, T305, etc.)
        if re.search(r'T3\d{2}', line_upper) or 'TURN' in line_upper:
            in_turning = True
        elif re.search(r'T[12]\d{2}', line_upper):  # Boring/drilling
            in_turning = False

        if in_turning:
            # Extract X value
            x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
            if x_match:
                x_val = float(x_match.group(1))
                # Filter out small X values (those are boring/internal)
                if x_val > 2.0:  # Reasonable OD minimum
                    max_x = max(max_x, x_val)

    if max_x > 2.0:
        return round(max_x * 2, 2)  # Convert radius to diameter
    return None
```

**Then in validation:**
```python
# OD Validation
if result.outer_diameter and od_from_gcode:
    title_od = result.outer_diameter
    gcode_od = od_from_gcode
    diff = gcode_od - title_od

    if abs(diff) > 0.05:  # ±0.05" tolerance
        result.validation_issues.append(
            f'OD MISMATCH: Spec={title_od:.2f}", G-code={gcode_od:.2f}" ({diff:+.3f}") - G-CODE ERROR'
        )
```

---

## Summary

### What We Have ✓
- Thickness (3 methods)
- Hub Height (3 methods)
- CB (2 methods)
- OB (2 methods)

### What We Should Add Next 🎯
1. **OD validation** from max X value
2. **Material validation** from feeds & speeds
3. **P-code consistency** checks
4. **Program number** cross-validation
5. **Re-scan changed files** feature

### How Updates Work
- **Re-scan folder** → UPDATE all records in database
- **Validation status** automatically changes (RED → GREEN if fixed)
- **No manual status change** needed
- **Recommended:** Add "Re-Scan Changed Files" button for efficiency

Would you like me to implement any of these additional validations? I'd recommend starting with **OD validation** and **P-code consistency** as they're easy wins with high impact!
