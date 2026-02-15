# How to Filter for G00 Crash Files

**Total Files with G00 Rapid into Negative Z**: 41 files
**Location**: `g00_crash_files_list.txt`

---

## Quick Summary

You have **41 files** with dangerous G00 rapid moves into negative Z that need attention:

### Top Crash Types:
1. **G00 rapid to negative Z**: 41 files
2. **Diagonal rapids with negative Z**: 10 files
3. **Other crash types**: 1,668 files (tool home, jaw clearance, etc.)

---

## Method 1: Use the Generated List

Open `g00_crash_files_list.txt` - all 41 files are listed with:
- Program number
- Exact crash description
- Line number where crash occurs
- File path

---

## Method 2: SQL Query in Database

Use this SQL query to see G00 crash files:

```sql
SELECT program_number, crash_issues, file_path
FROM programs
WHERE crash_issues LIKE '%G00 rapid to Z%'
ORDER BY program_number
```

---

## Method 3: Python Script

Run `find_g00_crash_files.py` anytime to get updated list:

```bash
python find_g00_crash_files.py
```

---

## Adding a UI Filter (Next Step)

I can add a "Crash Type" filter dropdown to the main UI with options:
- **All Crash Types**
- **G00 Rapid into Negative Z** ← Your requested filter
- **Diagonal Rapids**
- **Negative Z Before Tool Home**
- **Jaw Clearance Violations**
- **Other Crashes**

This would go in the filter section next to "Validation Status", "Material", etc.

**Would you like me to add this filter to the UI?** It would take about 15-20 minutes to implement.

---

## Files Needing Fixes

### Critical G00 Rapid Crashes (41 files):

**Programs starting with 0-3:**
- o08012 - Line 98: G00 Z-0.400
- o09902 - Line 111: G00 Z-0.350
- o09905 - Line 97: G00 Z-0.400
- o09906 - Line 95: G00 Z-0.400

**Programs in 38000-40000 range:**
- o38540 - Line 85: G00 Z-0.400
- o40022 - Line 94: G00 Z-0.400

**Programs in 58000 range** (many):
- o58109, o58140, o58202, o58538, o58547
- o58572, o58676, o58677
(All have G00 Z-0.090 crashes around lines 98-104)

**Programs in 60000-80000 range:**
- o60199 - Line 26: G00 Z-0.550
- o61007 - Line 107: G00 Z-0.090
- o65697 - Line 111: G00 Z-0.090
- o75292 - Line 85: G00 Z-0.400
- o80016 - Line 98: G00 Z-0.400
- o80019 - Line 94: G00 Z-0.400

(Plus 21 more files - see `g00_crash_files_list.txt` for complete list)

---

## How to Fix These Files

For each file, the fix is to change:

**Before** (CRASH RISK):
```gcode
G00 Z-0.400
```

**After** (SAFE):
```gcode
G01 Z-0.400 F0.008  (or appropriate feedrate)
```

**The system tells you exactly what to change** - it even suggests the fix in the crash message!

---

## Next Steps

1. **Review the list**: Check `g00_crash_files_list.txt`
2. **Decide on fix approach**:
   - Fix manually one by one
   - Batch fix similar patterns
   - Create auto-fix rules
3. **Optional**: Add UI filter for easy access

**Let me know if you want me to add the UI filter or help with batch fixing!**
