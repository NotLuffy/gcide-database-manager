# Color-Coded Validation System

## Overview

The validation system now uses **5 distinct color codes** to categorize issues by severity and type, making it easier to prioritize which programs need attention.

---

## Color Codes & Priority

### 🔴 **RED - CRITICAL** (Highest Priority)
**Status:** `CRITICAL`

**What It Means:**
- **Critical dimensional errors** that will produce wrong parts
- CB or OB dimensions way outside tolerance (>0.2-0.3mm off)
- Thickness errors beyond ±0.02"
- Part **cannot be used** without G-code correction

**Examples:**
- `CB TOO SMALL: Spec=71.0mm, G-code=66.0mm (-4.96mm) - CRITICAL ERROR`
- `OB TOO SMALL: Spec=64.1mm, G-code=61.5mm (-2.63mm) - CRITICAL ERROR`
- `THICKNESS ERROR: Spec=0.75", Calculated=0.80" (+0.05") - CRITICAL ERROR`

**Action Required:** **IMMEDIATE FIX NEEDED**
- Stop production
- Fix G-code before running
- These errors will cause part failures or machine crashes

---

### 🟠 **ORANGE - BORE WARNING** (High Priority)
**Status:** `BORE_WARNING`

**What It Means:**
- **Bore dimensions at tolerance limits** (CB/OB within 0.1-0.2mm)
- Part is still within spec but close to the edge
- May cause fit issues in assembly

**Examples:**
- `CB at tolerance limit: Spec=38.1mm, G-code=38.2mm (+0.10mm)`
- `OB at tolerance limit: Spec=64.1mm, G-code=64.2mm (+0.10mm)`

**Action Required:** **VERIFY CAREFULLY**
- Check dimensions carefully during setup
- Verify first article measurement
- Part is technically acceptable but borderline
- Consider adjusting G-code for better margin

---

### 🟣 **PURPLE - DIMENSIONAL** (Medium Priority)
**Status:** `DIMENSIONAL`

**What It Means:**
- **P-code and thickness mismatches** - Setup dimension issues
- Drill depth calculations slightly off (±0.01-0.02")
- Work offsets don't match part thickness

**Examples:**
- `P-CODE MISMATCH: Thickness 1.00" expects P15/P16, but found [17, 18]`
- `Thickness mismatch: Spec=0.75", Calculated=0.76" (+0.01")`

**Action Required:** **REVIEW SETUP**
- Check work offset (P-code) settings
- Verify drill depth matches part thickness
- Part may run but could have setup issues
- Update P-codes or drill depth to match

---

### 🟡 **YELLOW - WARNING** (Low Priority)
**Status:** `WARNING`

**What It Means:**
- **General warnings** that don't affect critical dimensions
- P-code pairing issues (missing OP1 or OP2)
- Multiple P-codes found (possible copy/paste error)
- OD slightly off (non-critical)

**Examples:**
- `P-CODE PAIRING: P15 found but P16 missing`
- `MULTIPLE P-CODES: Found [15, 16, 17, 18] - should only have one pair`
- `OD tolerance check: Spec=5.75", G-code=5.71" (-0.04")`

**Action Required:** **REVIEW WHEN CONVENIENT**
- Check for copy/paste errors
- Verify P-code pairing
- Not urgent but should be fixed eventually

---

### 🟢 **GREEN - PASS** (No Issues)
**Status:** `PASS`

**What It Means:**
- All validations passed
- Dimensions within spec
- P-codes match thickness
- **Ready to run**

**Action Required:** None - Good to go!

---

## Priority Matrix

| Color | Status | Severity | Production Impact | Action Timeline |
|-------|--------|----------|-------------------|----------------|
| 🔴 RED | CRITICAL | **CRITICAL** | Part failure/crash | **IMMEDIATE** |
| 🟠 ORANGE | BORE_WARNING | HIGH | Possible fit issues | Before first article |
| 🟣 PURPLE | DIMENSIONAL | MEDIUM | Setup errors | Before production run |
| 🟡 YELLOW | WARNING | LOW | Minor issues | When convenient |
| 🟢 GREEN | PASS | NONE | None | N/A |

---

## Validation Logic

### How Status is Determined (Priority Order)

The system checks validations in this order:

```
1. CRITICAL errors found?          → RED
   ↓ No
2. BORE warnings found?             → ORANGE
   ↓ No
3. DIMENSIONAL issues found?        → PURPLE
   ↓ No
4. General WARNINGS found?          → YELLOW
   ↓ No
5. All validations passed           → GREEN
```

**Note:** Status is based on **most severe** issue found. A program with both BORE_WARNING and general WARNING will show ORANGE.

---

## What Each Category Contains

### CRITICAL (RED)
```python
validation_issues = [
    "CB TOO SMALL: ...",
    "CB TOO LARGE: ...",
    "OB TOO SMALL: ...",
    "OB TOO LARGE: ...",
    "THICKNESS ERROR: ...",
    "OD MISMATCH: ..." (if >±0.1"),
    "FILENAME MISMATCH: ..."
]
```

### BORE_WARNING (ORANGE)
```python
bore_warnings = [
    "CB at tolerance limit: ...",
    "OB at tolerance limit: ..."
]
```

### DIMENSIONAL (PURPLE)
```python
dimensional_issues = [
    "P-CODE MISMATCH: ...",
    "Thickness mismatch: ..." (±0.01-0.02")
]
```

### WARNING (YELLOW)
```python
validation_warnings = [
    "P-CODE PAIRING: ...",
    "MULTIPLE P-CODES: ...",
    "OD tolerance check: ..." (±0.05-0.1")
]
```

---

## Examples by Part Type

### Hub-Centric Example (o58436)

**Extracted Values:**
- Title CB: 56.1mm
- G-code CB: 56.2mm → diff = +0.10mm
- Title OB: 64.1mm
- G-code OB: 61.5mm → diff = -2.63mm

**Result:** 🔴 **RED (CRITICAL)**
```
CRITICAL ERRORS:
  - OB TOO SMALL: Spec=64.1mm, G-code=61.5mm (-2.63mm) - CRITICAL ERROR
```

**Why RED?** OB is -2.63mm off, way beyond -0.3mm error threshold

---

### Standard Example (o57500)

**Extracted Values:**
- Title CB: 38.1mm
- G-code CB: 38.2mm → diff = +0.10mm
- P-codes: [15, 16]
- Thickness: 1.00"

**Result:** 🟠 **ORANGE (BORE_WARNING)**
```
BORE WARNINGS:
  - CB at tolerance limit: Spec=38.1mm, G-code=38.2mm (+0.10mm)
```

**Why ORANGE?** CB is exactly at +0.10mm tolerance limit

---

### Hypothetical P-Code Mismatch

**Extracted Values:**
- Thickness: 1.00"
- P-codes: [17, 18] (expects P15/P16)
- All bore dimensions OK

**Result:** 🟣 **PURPLE (DIMENSIONAL)**
```
DIMENSIONAL ISSUES:
  - P-CODE MISMATCH: Thickness 1.00" expects P15/P16, but found [17, 18]
```

**Why PURPLE?** Wrong P-code for thickness (setup error)

---

### Hypothetical P-Code Pairing Issue

**Extracted Values:**
- P-codes: [15] (missing P16)
- All dimensions OK

**Result:** 🟡 **YELLOW (WARNING)**
```
WARNINGS:
  - P-CODE PAIRING: P15 found but P16 missing
```

**Why YELLOW?** Missing OP2 P-code, but not critical

---

## GUI Display

### Treeview Colors

| Status | Background | Foreground | Hex Colors |
|--------|-----------|------------|------------|
| 🔴 CRITICAL | Dark Red | Bright Red | `#4d1f1f` / `#ff6b6b` |
| 🟠 BORE_WARNING | Dark Orange | Orange | `#4d3520` / `#ffa500` |
| 🟣 DIMENSIONAL | Dark Purple | Purple | `#3d1f4d` / `#da77f2` |
| 🟡 WARNING | Dark Yellow | Yellow | `#4d3d1f` / `#ffd43b` |
| 🟢 PASS | Dark Green | Green | `#1f4d2e` / `#69db7c` |

### Status Column

The "Status" column in the treeview shows:
- `CRITICAL` (red text)
- `BORE_WARNING` (orange text)
- `DIMENSIONAL` (purple text)
- `WARNING` (yellow text)
- `PASS` (green text)

---

## Tolerance Reference

### CB (Center Bore)
- **Acceptable:** title_cb to (title_cb + 0.1mm)
- **Orange:** ±0.1 to ±0.2mm or ±0.3mm
- **Red:** < -0.2mm or > +0.3mm

### OB (Outer Bore / Hub Diameter)
- **Acceptable:** (title_ob - 0.1mm) to title_ob
- **Orange:** ±0.1 to ±0.2mm or ±0.3mm
- **Red:** < -0.3mm or > +0.2mm

### Thickness
- **Acceptable:** ±0.01"
- **Purple:** ±0.01 to ±0.02"
- **Red:** > ±0.02"

### OD (Outer Diameter)
- **Acceptable:** ±0.05"
- **Yellow:** ±0.05 to ±0.1"
- **Red:** > ±0.1"

---

## Workflow Integration

### Daily Production Workflow

1. **Morning:** Scan production folders
   ```
   File organizer → Scan Folder → Select 5.75 folder
   ```

2. **Prioritize by Color:**
   - 🔴 **RED files:** Fix immediately, don't run
   - 🟠 **ORANGE files:** Check carefully during setup
   - 🟣 **PURPLE files:** Verify P-codes before running
   - 🟡 **YELLOW files:** Note for later review
   - 🟢 **GREEN files:** Run normally

3. **Fix Process:**
   - Double-click RED file → View Details
   - See exact error (e.g., "CB TOO SMALL -4.96mm")
   - Open G-code in editor
   - Fix dimension
   - Save file
   - Re-scan folder (status updates automatically)

---

## Database Schema

### New Columns Added

```sql
CREATE TABLE programs (
    ...
    validation_status TEXT,      -- 'CRITICAL', 'BORE_WARNING', 'DIMENSIONAL', 'WARNING', 'PASS'
    validation_issues TEXT,      -- JSON: Critical errors (RED)
    validation_warnings TEXT,    -- JSON: General warnings (YELLOW)
    bore_warnings TEXT,          -- JSON: Bore warnings (ORANGE)
    dimensional_issues TEXT,     -- JSON: Dimensional issues (PURPLE)
    ...
);
```

### Re-Scanning Updates Status

When you re-scan a folder:
- OLD status: `CRITICAL` (file had CB error)
- Fix the G-code CB value
- Re-scan folder
- NEW status: `PASS` (error fixed)
- Color automatically changes: RED → GREEN

---

## Benefits

### Before (3 Colors)
- 🔴 RED: All errors lumped together
- 🟡 YELLOW: All warnings lumped together
- 🟢 GREEN: Pass

**Problem:** Can't tell if RED is critical (stop production) or minor (fix later)

### After (5 Colors)
- 🔴 **RED:** Critical - stop production
- 🟠 **ORANGE:** Bore warning - check carefully
- 🟣 **PURPLE:** Dimensional - verify setup
- 🟡 **YELLOW:** Minor - fix when convenient
- 🟢 **GREEN:** Pass - run normally

**Benefit:** **Clear prioritization** - know exactly which files need immediate attention!

---

## Testing

Test files and their expected colors:

| File | Issues | Expected Color |
|------|--------|---------------|
| o58436 | OB -2.63mm | 🔴 RED (CRITICAL) |
| o57500 | CB +0.10mm | 🟠 ORANGE (BORE_WARNING) |
| o57415 | CB -4.96mm | 🔴 RED (CRITICAL) |
| (Example) | Wrong P-code | 🟣 PURPLE (DIMENSIONAL) |
| (Example) | Missing P16 | 🟡 YELLOW (WARNING) |
| (Example) | All pass | 🟢 GREEN (PASS) |

---

## Files Modified

1. **[improved_gcode_parser.py](improved_gcode_parser.py):**
   - Added `bore_warnings` list
   - Added `dimensional_issues` list
   - Updated validation logic to categorize by severity

2. **[gcode_database_manager.py](gcode_database_manager.py):**
   - Added `bore_warnings` and `dimensional_issues` columns
   - Added 5 color tags (critical, bore_warning, dimensional, warning, pass)
   - Updated status determination logic
   - Updated INSERT/UPDATE statements

---

## Status: PRODUCTION READY ✅

The new color-coded system is fully implemented and tested. To use:

1. Launch GUI: `python gcode_database_manager.py`
2. Scan folders (database auto-upgrades with new columns)
3. Files display with new color codes
4. Fix RED files first, then ORANGE, then PURPLE, etc.

**Prioritization is now visual and automatic!**
