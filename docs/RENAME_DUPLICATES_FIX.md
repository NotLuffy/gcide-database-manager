# Rename Name Duplicates - Bug Fix

## 🐛 Problem Identified

The **"✏️ Rename Name Duplicates"** button was incorrectly renaming Type 1 duplicates (name conflicts) by putting ALL files into the highest program number range (typically 7.5" range).

---

## ❌ What Was Wrong

### Old Logic (Lines 10145-10150):
```python
# WRONG APPROACH - Found MAX program number across ALL files
cursor.execute("SELECT MAX(CAST(REPLACE(program_number, 'o', '') AS INTEGER)) FROM programs WHERE program_number LIKE 'o%'")
result = cursor.fetchone()
max_num = int(result[0]) if result[0] else 0
new_num = max_num + 1 + len(renames_to_apply)
new_prog_num = f"o{new_num}"
```

### Why This Was Wrong:
- Found the **highest program number** in the entire database (e.g., o75000 in 7.5" range)
- Assigned the **next sequential number** after that
- This put **ALL duplicates** into the highest range, regardless of their actual round size
- Example: o62000(1) with 5.75" round size would be renamed to o75001 (7.5" range) ❌

---

## ✅ What It Does Now (Fixed)

### New Logic (Lines 10144-10166):
```python
# CORRECT APPROACH - Uses round size to find correct range
# Get round size for this duplicate file
cursor.execute("SELECT round_size FROM programs WHERE program_number = ?", (prog_num,))
round_result = cursor.fetchone()
round_size = round_result[0] if round_result and round_result[0] else None

if round_size:
    # Find next available number in CORRECT range for this round size
    new_prog_num = self.find_next_available_number(round_size)
    if new_prog_num:
        renames_to_apply.append((prog_num, new_prog_num, round_size))
    else:
        # Skip - no available numbers in that range
else:
    # No round size - use free range (o1000-o9999)
    cursor.execute("SELECT MIN(program_number) FROM program_number_registry WHERE status = 'AVAILABLE' AND CAST(REPLACE(program_number, 'o', '') AS INTEGER) BETWEEN 1000 AND 9999")
    free_result = cursor.fetchone()
    if free_result and free_result[0]:
        new_prog_num = free_result[0]
        renames_to_apply.append((prog_num, new_prog_num, None))
```

### Why This Is Correct:
1. **Reads the round_size** from the database for each duplicate file
2. **Uses `find_next_available_number(round_size)`** to get a number in the **correct range**
3. **Respects round size ranges**:
   - 5.75" duplicate → o50000-o59999 range ✅
   - 6.25" duplicate → o62500-o62999 range ✅
   - 7.5" duplicate → o75000-o79999 range ✅
4. **Falls back to free range (o1000-o9999)** if no round size detected
5. **Updates registry** to mark old number as AVAILABLE, new number as IN_USE

---

## 🔄 How It Works Now

### Example Scenario:

**Input:**
```
Duplicate Group: o62000
  - o62000      (5.75" spacer) - KEEP
  - o62000(1)   (5.75" spacer - different dimensions) - RENAME
  - o62000(2)   (5.75" spacer - old version) - RENAME
```

**Old Behavior (WRONG):**
```
✓ KEEP: o62000
✏️ RENAME: o62000(1) → o75001  (Put in 7.5" range - WRONG!)
✏️ RENAME: o62000(2) → o75002  (Put in 7.5" range - WRONG!)
```

**New Behavior (CORRECT):**
```
✓ KEEP: o62000
✏️ RENAME: o62000(1) → o57500 (5.75") - Correct range!
✏️ RENAME: o62000(2) → o57501 (5.75") - Correct range!
```

---

## 📋 Additional Improvements

### 1. Registry Updates
Added automatic registry updates during rename:
```python
# Update registry: mark old number as AVAILABLE, new number as IN_USE
cursor.execute("UPDATE program_number_registry SET status = 'AVAILABLE', file_path = NULL WHERE program_number = ?", (old_num,))
cursor.execute("UPDATE program_number_registry SET status = 'IN_USE', file_path = ? WHERE program_number = ?", (new_file_path, new_num))
```

### 2. Round Size Display
Now shows round size in rename preview:
```
✏️ RENAME: o62000(1) → o57500 (5.75") - 5.75 SPACER
```

### 3. Free Range Fallback
If no round size detected, uses free range o1000-o9999:
```
✏️ RENAME: o12345(1) → o1234 (free range) - UNKNOWN PART
```

---

## 🎯 Type 1 Duplicate Workflow (Fixed)

### What Type 1 Duplicates Are:
- **Same base name, different content**
- Created during scanning when multiple files have same program number
- Example: o12345, o12345(1), o12345(2) with different dimensions/revisions

### How the Button Handles Them Now:
```
1. Identifies duplicate groups: o12345, o12345(1), o12345(2)
   ↓
2. Keeps first file: o12345
   ↓
3. For each duplicate (o12345(1), o12345(2)):
   a. Reads round_size from database
   b. Finds next available number in CORRECT range
   c. Renames file (filename + internal O-number)
   d. Updates database program_number and file_path
   e. Updates registry (old=AVAILABLE, new=IN_USE)
   ↓
4. Result: Each duplicate in its correct range!
```

---

## ✅ Testing Recommendations

### Test 1: Type 1 Duplicates with Known Round Sizes
```
Before:
- o62000 (5.75") - Keep
- o62000(1) (5.75") - Should rename to o57500-o59999 range
- o62000(2) (6.25") - Should rename to o62500-o62999 range

After clicking "✏️ Rename Name Duplicates":
- Verify o62000(1) is in 5.75" range (o57500-o59999)
- Verify o62000(2) is in 6.25" range (o62500-o62999)
```

### Test 2: Type 1 Duplicates with No Round Size
```
Before:
- o12345 (no round size) - Keep
- o12345(1) (no round size) - Should rename to free range o1000-o9999

After:
- Verify o12345(1) is in free range (o1000-o9999)
```

### Test 3: Registry Updates
```
After renaming:
1. Check registry shows old numbers as AVAILABLE
2. Check registry shows new numbers as IN_USE
3. Verify file_path updated in registry
```

---

## 🚀 Current Status

✅ **Fixed** - Rename Name Duplicates now correctly assigns program numbers based on round size
✅ **Registry Updates** - Automatically updates registry during rename
✅ **Round Size Display** - Shows round size in preview and execution
✅ **Free Range Fallback** - Handles files with no round size detected

---

## 📝 Summary

**Before:** All duplicates renamed to highest range (7.5") regardless of round size
**After:** Each duplicate renamed to correct range based on its round size

**Impact:** Type 1 duplicates now properly organized by round size ranges instead of all being incorrectly placed in the highest range.

---

*Fixed: 2025-12-03*
*Lines Modified: 10129-10274 in gcode_database_manager.py*
