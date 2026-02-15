# Crash Type Filter - Quick Reference

**Date**: 2026-02-07
**Status**: ✅ COMPLETE

---

## What It Does

Adds a "Crash Type" dropdown filter in the main UI to quickly find files with specific crash issues.

---

## Filter Options

1. **G00 Rapid to Z** - Files with dangerous G00 rapid moves to negative Z (41 files)
   - Example: `G00 Z-0.400` (crashes into part)
   - These MUST be changed to `G01 Z-0.400 F0.008`

2. **Diagonal Rapid** - Files with diagonal G00 rapids that include negative Z
   - Example: `G00 X6.25 Z-0.5` (diagonal crash)

3. **Z Before Tool Home** - Files with negative Z before G53 tool home command
   - Crashes because tool tries to retract while still in the part

4. **Jaw Clearance** - Files where turning tool might hit chuck jaws
   - Warnings for T3xx tools only (not drills/bore bars)
   - Critical when total_height - 0.3" is violated

5. **All Crashes** - Shows any file with crash_issues populated
   - Includes all crash types plus other issues

---

## How to Use

### Quick Search for G00 Crash Files

1. Open the main database window
2. In the filter section (top row), find **"Crash Type:"** dropdown
3. Select **"G00 Rapid to Z"**
4. Tree view will filter to show only the 41 files with this issue

### Multi-Select

You can select multiple crash types at once:
- Click the dropdown
- Check multiple boxes
- Filter shows files matching ANY selected type

### Example Workflows

**Find all G00 rapid crashes:**
```
Crash Type: ☑ G00 Rapid to Z
Result: 41 files with dangerous rapids
```

**Find all crash-related issues:**
```
Crash Type: ☑ All Crashes
Result: 1,709 files with any crash detection
```

**Find G00 AND diagonal rapids:**
```
Crash Type: ☑ G00 Rapid to Z
            ☑ Diagonal Rapid
Result: All files with either type
```

---

## Filter Location

**UI Location**: Top filter section, Row 1, after "Dup Type" filter

**Filter Code**: Line ~11854 in `refresh_results()` method

---

## Technical Details

### UI Widget - Line ~7370
```python
# Crash Type
tk.Label(row1, text="Crash Type:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
crash_type_values = ["G00 Rapid to Z", "Diagonal Rapid", "Z Before Tool Home", "Jaw Clearance", "All Crashes"]
self.filter_crash_type = MultiSelectCombobox(row1, crash_type_values, self.bg_color, self.fg_color,
                                             self.input_bg, self.button_bg, width=18)
self.filter_crash_type.pack(side=tk.LEFT, padx=5)
```

### Filter Logic - Line ~11854
```python
# Crash Type filter
if hasattr(self, 'filter_crash_type'):
    selected_crash_types = self.filter_crash_type.get_selected()
    if selected_crash_types and len(selected_crash_types) < len(self.filter_crash_type.values):
        crash_conditions = []

        if "G00 Rapid to Z" in selected_crash_types:
            crash_conditions.append("crash_issues LIKE '%G00 rapid to Z%'")

        if "Diagonal Rapid" in selected_crash_types:
            crash_conditions.append("crash_issues LIKE '%diagonal%'")

        if "Z Before Tool Home" in selected_crash_types:
            crash_conditions.append("crash_issues LIKE '%Z before G53%' OR crash_issues LIKE '%negative Z before tool home%'")

        if "Jaw Clearance" in selected_crash_types:
            crash_conditions.append("crash_warnings LIKE '%jaw clearance%'")

        if "All Crashes" in selected_crash_types:
            crash_conditions.append("(crash_issues IS NOT NULL AND crash_issues != 'null' AND crash_issues != '[]')")

        if crash_conditions:
            query += f" AND ({' OR '.join(crash_conditions)})"
```

---

## Database Fields Used

- **crash_issues**: Critical crash detection (G00 rapids, tool home issues)
- **crash_warnings**: Warning-level issues (jaw clearance)

Both fields store JSON arrays of issue descriptions.

---

## Next Steps

### To Fix the 41 G00 Crash Files:

1. **Filter**: Select "G00 Rapid to Z" in Crash Type filter
2. **Review**: View each file to understand the context
3. **Fix**: Change `G00 Z-X.XXX` to `G01 Z-X.XXX F0.008` (or appropriate feedrate)
4. **Verify**: Re-scan the file to confirm crash is resolved

### Batch Fix Option

If you want to batch fix all 41 files, I can create a script that:
- Finds all G00 Z-negative commands
- Suggests appropriate feedrates based on tool type
- Creates backups before modifying
- Validates the fix with crash detection

**Let me know if you want the batch fix script!**

---

## Files Modified

**gcode_database_manager.py**:
- Line ~7370: Added Crash Type filter widget
- Line ~11854: Added Crash Type filter logic

---

**Feature Complete**: 2026-02-07
**Ready to Use**: Yes - restart application and try filtering by crash type!
