# Internal Program Number Update Fix

## 🐛 Problem

**Issue:** When renaming programs with suffixes in the database (like `o00002(1)`), the internal O-number in the file wasn't being updated correctly.

**User Report:** "lets make sure that once we rename a file we are rename the physical files and its internal program numbers"

### The Distinction:

**Filenames:** CAN have temporary suffixes as placeholders
- `o00002_1.nc` ← Temporary suffix to avoid duplicate filenames
- `o00002_2.nc` ← Second duplicate

**Internal O-numbers:** Should NEVER have suffixes
- File content: `O00002` ← Clean, no suffix
- NOT: `O00002_1` or `O00002(1)`

### What Was Happening:

1. **Database:** `o00002(1)` (with suffix)
2. **File content:** `O00002` (WITHOUT suffix - correct!)
3. **Rename function tried to find:** `O00002(1)` in file content
4. **Result:** ❌ Regex didn't match, internal O-number NOT updated!
5. **After rename:**
   - Filename: `o50000.nc` ✅ Updated
   - File content: `O00002` ❌ Still has OLD number!

---

## 🔍 Root Cause

### The Problematic Code (BEFORE FIX):

```python
# Update program number in file content
old_num_plain = program_number.replace('o', '').replace('O', '')  # "00002(1)"
new_num_plain = new_number.replace('o', '').replace('O', '')      # "50000"

# Pattern 1: O12345 or o12345 at start of line
updated_content = re.sub(
    rf'^[oO]{old_num_plain}\b',  # ❌ Looks for "O00002(1)"
    new_number.upper(),          # Replaces with "O50000"
    updated_content,
    flags=re.MULTILINE
)
```

**Why it failed:**
- Regex pattern: `^[oO]00002(1)\b`
- File content: `O00002` (no suffix)
- **NO MATCH!** The `(1)` suffix in the pattern prevents matching

---

## ✅ Solution Implemented

### Strip Suffix Before Matching:

```python
# Update program number in file content
import re

# Strip any suffix from old program number for matching internal content
# Database might have o00002(1) or o00002_1, but file content has O00002
old_num_plain = program_number.replace('o', '').replace('O', '')  # "00002(1)"

# Remove any suffix patterns: (1), (2), _1, _2, etc.
old_num_base = re.sub(r'[(_]\d+[\)]?$', '', old_num_plain)  # "00002" ✅

new_num_plain = new_number.replace('o', '').replace('O', '')  # "50000"

# Replace program number (common patterns)
updated_content = content

# Pattern 1: O12345 or o12345 at start of line
# Use the BASE number without suffix to match file content
updated_content = re.sub(
    rf'^[oO]{old_num_base}\b',  # ✅ Looks for "O00002" (no suffix)
    new_number.upper(),          # Replaces with "O50000"
    updated_content,
    flags=re.MULTILINE
)

# Pattern 2: In program number comments
# Use the BASE number without suffix to match file content
updated_content = re.sub(
    rf'\b[oO]{old_num_base}\b',  # ✅ Matches "O00002" anywhere
    new_number.upper(),           # Replaces with "O50000"
    updated_content
)
```

**Suffix Stripping Regex:** `r'[(_]\d+[\)]?$'`
- `[(_]` - Matches underscore or opening parenthesis
- `\d+` - One or more digits
- `[\)]?` - Optional closing parenthesis
- `$` - End of string

**Examples:**
```
"00002(1)" → "00002" ✅
"00002(2)" → "00002" ✅
"00002_1" → "00002" ✅
"00002_2" → "00002" ✅
"00002"   → "00002" ✅ (already clean)
```

---

## 📊 Before vs After

### Before Fix:

**Database:**
```
program_number: o00002(1)
file_path: O00002_1.nc
```

**File Content (O00002_1.nc):**
```gcode
O00002
(7IN DIA 5.25/6.25IN CENTER HOLDER)
G00 X0 Y0
...
```

**After Batch Rename (BROKEN):**
```
Filename: o50000.nc  ✅ Renamed
File content:
O00002  ❌ Still old number! Not updated!
(7IN DIA 5.25/6.25IN CENTER HOLDER)
G00 X0 Y0
...
```

**Result:** Filename and internal O-number don't match!

---

### After Fix:

**Database:**
```
program_number: o00002(1)
file_path: O00002_1.nc
```

**File Content (O00002_1.nc):**
```gcode
O00002
(7IN DIA 5.25/6.25IN CENTER HOLDER)
G00 X0 Y0
...
```

**After Batch Rename (WORKING):**
```
Filename: o50000.nc  ✅ Renamed
File content:
O50000  ✅ Updated! Now matches filename!
(RENAMED FROM O00002(1) ON 2025-12-03 - OUT OF RANGE)
(7IN DIA 5.25/6.25IN CENTER HOLDER)
G00 X0 Y0
...
```

**Result:** Filename and internal O-number match perfectly!

---

## 🎯 Why This Fix Is Critical

### 1. CNC Machine Compatibility

**CNC machines read the internal O-number:**
- Loads program by internal O-number
- Ignores filename
- **If mismatch:** Machine loads wrong program or fails

### 2. Program Integrity

**Files must be self-consistent:**
- Filename: `o50000.nc`
- Internal: `O50000`
- Database: `o50000`

**All three must match!**

### 3. Workflow Correctness

**Suffix handling:**
- ✅ **Temporary:** Filename can have suffix during duplicate resolution
- ✅ **Clean:** Internal O-number is always clean (no suffix)
- ✅ **Final:** Both filename and internal O-number get new clean number

### 4. Legacy Tracking

**Legacy comment added:**
```gcode
O50000
(RENAMED FROM O00002(1) ON 2025-12-03 - OUT OF RANGE)
```

Preserves rename history without affecting functionality.

---

## 🔧 Implementation Details

### Files Modified:

**gcode_database_manager.py**

### Function Modified:

**rename_to_correct_range()** (lines 1602-1631)

### Changes Made:

**1. Added suffix stripping** (lines 1605-1609)
```python
old_num_plain = program_number.replace('o', '').replace('O', '')
old_num_base = re.sub(r'[(_]\d+[\)]?$', '', old_num_plain)
```

**2. Updated Pattern 1 to use base number** (lines 1616-1623)
```python
updated_content = re.sub(
    rf'^[oO]{old_num_base}\b',  # Uses base without suffix
    new_number.upper(),
    updated_content,
    flags=re.MULTILINE
)
```

**3. Updated Pattern 2 to use base number** (lines 1625-1631)
```python
updated_content = re.sub(
    rf'\b[oO]{old_num_base}\b',  # Uses base without suffix
    new_number.upper(),
    updated_content
)
```

---

## ✅ Testing Checklist

### Test 1: Program with Parenthesis Suffix

```
Setup:
- Database: o00002(1)
- File content: O00002
- Filename: O00002_1.nc

Steps:
1. Run batch rename
2. Check new file content

Expected:
- Internal O-number updated: O00002 → O50000 ✅
- Filename updated: O00002_1.nc → o50000.nc ✅
- Both match ✅

Result: ✅ Pass
```

### Test 2: Program with Underscore Suffix

```
Setup:
- Database: o00002_1
- File content: O00002
- Filename: o00002_1.nc

Steps:
1. Run batch rename
2. Check new file content

Expected:
- Internal O-number updated: O00002 → O50000 ✅
- Filename updated: o00002_1.nc → o50000.nc ✅
- Both match ✅

Result: ✅ Pass
```

### Test 3: Program Without Suffix

```
Setup:
- Database: o00002
- File content: O00002
- Filename: o00002.nc

Steps:
1. Run batch rename
2. Check new file content

Expected:
- Internal O-number updated: O00002 → O50000 ✅
- Filename updated: o00002.nc → o50000.nc ✅
- Both match ✅

Result: ✅ Pass
```

### Test 4: Legacy Comment Added

```
After rename:
O50000
(RENAMED FROM O00002(1) ON 2025-12-03 - OUT OF RANGE)
(7IN DIA 5.25/6.25IN CENTER HOLDER)

Expected:
- Legacy comment present ✅
- Shows old number with suffix ✅
- Date stamp ✅
- Reason ✅

Result: ✅ Pass
```

---

## 🔄 Integration with Workflow

### Complete Workflow:

```
1. Files have temporary suffixes:
   - Filename: o00002_1.nc (suffix)
   - Internal: O00002 (clean) ✅ CORRECT!

2. Run Repair File Paths:
   - Database updated to point to correct files

3. Run Batch Rename Out-of-Range:
   - Database: o00002(1) → o50000
   - Filename: o00002_1.nc → o50000.nc
   - Internal: O00002 → O50000 ✅ NOW FIXED!

4. Result:
   - All three match: o50000, o50000.nc, O50000 ✅
```

---

## 🛡️ Safety Features

### 1. Base Number Extraction

Uses regex to safely strip suffixes:
```python
old_num_base = re.sub(r'[(_]\d+[\)]?$', '', old_num_plain)
```

Handles all suffix types:
- `(1)`, `(2)`, `(10)`
- `_1`, `_2`, `_10`
- Mixed patterns

### 2. Preserves Clean Numbers

If number has no suffix:
```python
"00002" → "00002"  # No change, works correctly
```

### 3. Multiple Pattern Matching

**Pattern 1:** Start of line (main program number)
```python
rf'^[oO]{old_num_base}\b'
```

**Pattern 2:** Anywhere in file (comments, sub-programs)
```python
rf'\b[oO]{old_num_base}\b'
```

Both patterns updated with clean base number.

---

## 📝 Key Principles

### Filenames vs Internal Numbers:

1. **Filenames:** Temporary suffixes OK
   - `o00002_1.nc` ← Placeholder during duplicates
   - Gets renamed to clean number later

2. **Internal O-numbers:** ALWAYS clean
   - `O00002` ← No suffix, ever
   - Never write `O00002_1` or `O00002(1)` to file

3. **Database:** May have suffixes temporarily
   - `o00002(1)` ← Tracks duplicate
   - Gets renamed to clean number later

4. **Final State:** All three match
   - Filename: `o50000.nc`
   - Internal: `O50000`
   - Database: `o50000`

---

## 🎉 Summary

**Problem:** Internal O-numbers not being updated when renaming programs with suffixes

**Cause:** Regex pattern included suffix, didn't match clean internal O-number

**Solution:**
1. Strip suffix from old program number before matching
2. Use base number (without suffix) in regex patterns
3. Match clean internal O-number in file
4. Update to new clean number

**Result:** Internal O-numbers now update correctly!

**Impact:**
- ✅ Filenames match internal O-numbers
- ✅ CNC machines load correct programs
- ✅ Database, filename, and internal number all synchronized
- ✅ Legacy comments preserve rename history

---

*Fixed: 2025-12-03*
*Function: rename_to_correct_range() (lines 1602-1631)*
*File: gcode_database_manager.py*
