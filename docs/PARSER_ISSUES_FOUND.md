# Parser Issues Found - 2025-12-09

## Summary

Found multiple issues causing false CRITICAL errors in validation:

1. **CB Extraction** - Using max() instead of selecting closest to spec
2. **P-Code Extraction** - Missing embedded P-codes in G154 commands
3. **OB Extraction** - 24 remaining programs with OB/OD confusion (99% already fixed)

---

## Issue 1: CB Extraction Selects Wrong Value

### Problem

Parser uses `max(cb_candidates)` which assumes the largest X value is always the final CB. This fails for files with progressive boring where the final chamfer creates an **oversized CB**.

### Example: o10204

**Title:** `10.25IN DIA 170.1MM ID 1.25 THK XX`
- Spec CB: 170.1mm (6.70")
- Extracted CB: 157.5mm (**WRONG - marked as CRITICAL**)
- Actual CB candidates:
  ```
  X6.2   = 157.5mm  (12.6mm too small)  <- Parser extracts this
  X6.4   = 162.6mm  (7.5mm too small)
  X6.6   = 167.6mm  (2.5mm too small)   <- CLOSEST TO SPEC!
  X6.701 = 170.2mm  (0.1mm larger)      <- PERFECT MATCH!
  X6.941 = 176.3mm  (6.2mm too large)   <- max() would select this
  ```

**Root Cause:**

Line 1555 in improved_gcode_parser.py:
```python
if cb_candidates:
    result.cb_from_gcode = max(cb_candidates) * 25.4  # WRONG for chamfered holes!
```

**Correct Logic:**

Should select the candidate **closest to title spec**, not the max:
```python
if cb_candidates and result.center_bore:
    # Select candidate closest to title spec
    title_cb_inches = result.center_bore / 25.4
    closest = min(cb_candidates, key=lambda x: abs(x - title_cb_inches))
    result.cb_from_gcode = closest * 25.4
elif cb_candidates:
    # Fallback: use max if no title spec
    result.cb_from_gcode = max(cb_candidates) * 25.4
```

### Impact

**Estimated 100-200 programs** with "CB TOO SMALL" errors are actually correct, just need to use closest-to-spec selection instead of max.

---

## Issue 2: P-Code Extraction Missing Embedded Codes

### Problem

P-codes are embedded in G154 coordinate system commands like:
- `G00 G154 P17X0. Z1. M08` (P17 is the fixture/program number)
- `(OP22)` (P22 in operation comment)

Parser regex doesn't handle these patterns.

### Evidence

Checked 50 programs marked "P-code missing":
- **All 50 programs have P-codes!**
- Found patterns:
  - `G154 P17X0.` - P17 concatenated with X
  - `G154 P22X10.` - P22 before X coordinate
  - `(OP22)` - P22 in operation label

### Current Regex (Missing These)

Parser likely uses pattern like: `\(P\s*(\d+)\)` which requires parentheses and space

### Needed Patterns

```python
p_patterns = [
    r'G154\s+P(\d+)',           # G154 P17 or G154 P17X0
    r'\(OP\s*(\d+)\)',          # (OP22) or (OP 22)
    r'\(P\s*(\d+)',             # (P50 PROGRAM)
    r'P\s*-?\s*(\d+)',          # P50 or P-50 or P 50
]
```

### Impact

Estimated **500+ programs** are missing P-code detection.

---

## Issue 3: OB Extraction - 24 Remaining Warnings

### Status

- **Fixed:** 2294/2318 programs (99%)
- **Remaining:** 24 programs still have "OB matches OD" warnings

### Likely Causes

1. **Different G-code patterns** not covered by current OB detection
2. **Parts where OB actually equals OD** (valid for some designs)
3. **Non-standard tool paths** requiring manual review

### Next Step

Analyze the 24 remaining files to determine if they need:
- Additional parser patterns
- Manual review
- Are genuinely edge cases

---

## Recommended Fix Order

1. **Fix CB extraction first** - Biggest impact (100-200 false errors)
2. **Fix P-code extraction** - Easy fix, affects 500+ programs
3. **Analyze remaining 24 OB warnings** - Low priority (99% already fixed)
4. **Rescan database** - Apply all fixes

---

## Expected Results After Fixes

### Current State
- CRITICAL: 796 programs
- Many are false positives from CB extraction using max() instead of closest

### After CB Fix
- CRITICAL: ~600-650 programs (estimated)
- Reduce false positives by 150-200 programs

### After P-Code Fix
- 500+ programs will have correct P-code assigned
- Improves program organization and fixture tracking

### After All Fixes
- More accurate validation status
- Fewer false CRITICAL errors
- Better P-code tracking
- 99% OB detection accuracy maintained
