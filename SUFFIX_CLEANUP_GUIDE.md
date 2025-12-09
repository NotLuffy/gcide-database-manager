# Suffix Cleanup Guide - Fix Programs Like o00002(1)

## 🎯 Problem

You have programs with suffixes that haven't been cleaned up:
- **Program number:** `o00002(1)`, `o00004(1)`, `o00801(2)`, etc.
- **Filename:** `O00002_1.nc`, `O00004_1.nc`, but database points to wrong name
- **Actual file:** `O00002.nc` (exists but database has wrong path)

**Total:** ~50 programs with these issues

---

## 🔍 Why They Weren't Fixed

These programs have **TWO issues at once:**

1. **File Path Mismatch:**
   - Database says: `O00002_1.nc`
   - Actual file: `O00002.nc`
   - Batch rename can't find the file!

2. **Out-of-Range + Suffix:**
   - Program: `o00002(1)` with round size 5.25"
   - Should be in 5.75" range (o50000-o59999)
   - Needs batch rename to fix

**Why batch rename failed before:**
- It tried to read file at `O00002_1.nc`
- But file is actually `O00002.nc`
- Result: "File not found" error

---

## ✅ Complete Fix Sequence

Run these operations IN ORDER:

### Step 1: Repair File Paths ⭐ CRITICAL FIRST STEP

```
Repository tab → Click "🔧 Repair File Paths"
```

**What it does:**
- Scans repository for all `.nc` files
- Finds `O00002.nc` exists
- Updates database: `O00002_1.nc` → `O00002.nc`
- Now batch rename can find the files!

### Step 2: Fix Program Number Format

```
Repository tab → Click "🔢 Fix Program Number Format"
```

**What it does:**
- Fixes any missing leading zeros
- `o1000` → `o01000`
- Ensures all numbers are `o#####` format

### Step 3: Batch Rename Out-of-Range

```
Repository tab → Click "🔧 Batch Rename Out-of-Range"
OR
Repository tab → Click "📋 Program Number Registry" → "Batch Rename"
```

**What it does:**
- Renames `o00002(1)` → `o50000` (next available in 5.75" range)
- Renames file `O00002.nc` → `o50000.nc`
- Removes the (1) suffix
- Puts program in correct range

### Step 4: Sync Filenames with Database

```
Repository tab → Click "🔄 Sync Filenames with Database"
```

**What it does:**
- Final cleanup for any case mismatches
- `O50000.nc` → `o50000.nc` (lowercase)
- Ensures perfect sync

### Step 5: Verify

Check repository folder - all files should be:
- ✅ `o#####.nc` format (5 digits, lowercase)
- ✅ No suffixes like `_1`, `_2`, `(1)`, `(2)`
- ✅ In correct ranges for their round size

---

## 📊 Example: Fixing o00002(1)

### Before:

**Database:**
```
program_number: o00002(1)
file_path: O00002_1.nc  ← Wrong! File doesn't exist
round_size: 5.25"
in_correct_range: 0  ← Out of range
```

**Repository Files:**
```
O00002.nc  ← Actual file (database doesn't know about it)
```

**Problem:** Database points to non-existent file, can't rename!

### After Step 1 (Repair File Paths):

**Database:**
```
program_number: o00002(1)
file_path: O00002.nc  ← Fixed! Points to actual file
round_size: 5.25"
in_correct_range: 0
```

**Repository Files:**
```
O00002.nc  ← Same file, database now knows correct path
```

### After Step 3 (Batch Rename):

**Database:**
```
program_number: o50000  ← Suffix removed! In correct range!
file_path: o50000.nc  ← File renamed too!
round_size: 5.25"
in_correct_range: 1  ← Now in correct range
```

**Repository Files:**
```
o50000.nc  ← Renamed to match program number
```

---

## 🎯 Programs That Will Be Fixed

Here are the programs with suffixes that will be cleaned up:

### With Round Sizes (Out-of-Range - Fixed by Batch Rename):
```
o00001(3) → Will become o7#### (7.0" range)
o00002(1) → Will become o5#### (5.75" range for 5.25")
o00004(1) → Will become o7#### (7.0" range)
o00801(2) → Will become o85### (8.5" range)
o00805(1) → Will become o8#### (8.0" range)
o00918(1) → Will become o9#### (9.5" range)
o00918(2) → Will become o9#### (9.5" range)
... and ~43 more
```

### Without Round Sizes (Fixed by Fix Underscore Suffix):
```
These need round size detection first
Run "Detect Round Sizes" before cleanup
```

---

## ⚠️ Common Mistakes

### ❌ WRONG Order:
```
1. Batch Rename Out-of-Range (FAILS - can't find files)
2. Repair File Paths
Result: Batch rename failed, nothing fixed
```

### ✅ CORRECT Order:
```
1. Repair File Paths (Fixes database → actual files)
2. Fix Program Number Format (Adds leading zeros)
3. Batch Rename Out-of-Range (Now works - finds files!)
4. Sync Filenames (Final cleanup)
Result: All suffixes removed, files in correct ranges!
```

---

## 🛡️ Safety

All operations are safe:
- ✅ Preview before applying
- ✅ Can cancel anytime
- ✅ Non-destructive until you click "Apply"
- ✅ Database and files stay in sync

---

## 📋 Quick Checklist

- [ ] Step 1: Repair File Paths
- [ ] Step 2: Fix Program Number Format
- [ ] Step 3: Batch Rename Out-of-Range
- [ ] Step 4: Sync Filenames
- [ ] Step 5: Verify - Check repository folder

**Total Time:** ~5-10 minutes for ~50 programs

---

## 🎉 After Completion

Your repository will be:
- ✅ No suffixes (`_1`, `_2`, `(1)`, `(2)`)
- ✅ All programs in correct ranges
- ✅ All filenames match program numbers
- ✅ Consistent `o#####.nc` format
- ✅ Clean and organized

---

*Created: 2025-12-03*
*Related: BATCH_RENAME_FAILURE_FIX.md, REPAIR_FILE_PATHS_FEATURE.md*
