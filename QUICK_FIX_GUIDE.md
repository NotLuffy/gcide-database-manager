# Quick Fix Guide - Common Issues

## 🚨 When Batch Rename Fails

### Symptom:
```
Batch rename failing with "File not found" errors
Failed: 27
Skipped: 23
```

### Fix:
```
1. Repository tab → Click "🔧 Repair File Paths"
2. Review preview
3. Click "✓ Apply Repairs"
4. Try batch rename again → Works!
```

**Why:** Database file_path entries don't match actual files on disk.

**Doc:** [BATCH_RENAME_FAILURE_FIX.md](BATCH_RENAME_FAILURE_FIX.md)

---

## 🚨 When Sync Filenames Shows "Already Exists"

### Symptom:
```
Processing: O95163.nc → o95163.nc
⚠️ SKIP: o95163.nc already exists
```

### Fix:
**Already fixed!** This was a Windows case-insensitivity issue. The fix now handles case-only changes automatically using a two-step rename.

Just run sync filenames again and it will work.

**Why:** Windows treats `O95163.nc` and `o95163.nc` as the same file.

**Doc:** [SYNC_FILENAMES_FEATURE.md](SYNC_FILENAMES_FEATURE.md) (Updated)

---

## 🚨 When Files Still Have Suffixes (_1, _2, (1), (2))

### Symptom:
```
Files like: o00004_1.nc, o00801(2).nc
Database program_number: o00004(1), o00801(2)
```

### Fix:
```
1. Repository tab → Click "🔍 Manage Duplicates"
2. Click "Fix Underscore Suffix Files" (Pass 3)
3. Review preview
4. Click "Confirm Rename"
```

**Why:** Files need suffix cleanup from duplicate resolution.

**Doc:** [MISSING_COMMITS_FIX.md](MISSING_COMMITS_FIX.md)

---

## 🚨 When Filenames Don't Match Program Numbers

### Symptom:
```
Filename: o85260_1.nc
Database program_number: o85000
File content: O85000
```

### Fix:
```
1. Repository tab → Click "🔄 Sync Filenames with Database"
2. Review preview
3. Click "✓ Confirm Rename"
```

**Why:** Batch rename updated database but didn't rename files (fixed now, but old files still need sync).

**Doc:** [SYNC_FILENAMES_FEATURE.md](SYNC_FILENAMES_FEATURE.md)

---

## 🚨 Database Locked Errors

### Symptom:
```
sqlite3.OperationalError: database is locked
```

### Fix:
**Already fixed!** All registry updates now commit immediately to avoid holding locks.

If you still see this error, close all windows and try again.

**Why:** Long-running transactions were holding write locks.

**Doc:** [DATABASE_LOCK_FIX.md](DATABASE_LOCK_FIX.md)

---

## 🚨 "No Available Numbers" Error

### Symptom:
```
Error: No available numbers in 8.5" range
(Even though thousands are available)
```

### Fix:
**Already fixed!** The `fix_underscore_suffix_files()` function now commits immediately after marking numbers as IN_USE.

Just try the operation again and it will work.

**Why:** Missing `conn.commit()` statements prevented registry updates from being visible.

**Doc:** [MISSING_COMMITS_FIX.md](MISSING_COMMITS_FIX.md)

---

## 🚨 Program Numbers Missing Leading Zeros

### Symptom:
```
Files named: o1.nc, o100.nc, o1000.nc
Should be:   o00001.nc, o00100.nc, o01000.nc
```

### Fix:
```
1. Repository tab → Click "🔢 Fix Program Number Format"
2. Review preview (shows o1 → o00001, etc.)
3. Click "✓ Apply Fixes"
```

**Why:** Program numbers must be exactly 6 characters: `o` + 5 digits with leading zeros.

**Doc:** [PROGRAM_NUMBER_FORMAT_FIX.md](PROGRAM_NUMBER_FORMAT_FIX.md)

---

## 🚨 UNIQUE Constraint Errors

### Symptom:
```
sqlite3.IntegrityError: UNIQUE constraint failed: programs.program_number
```

### Fix:
**Already fixed!** The rename functions now double-check the programs table before assigning numbers.

Just try the operation again and it will work.

**Why:** Registry said number was available, but it existed in programs table.

**Doc:** [UNIQUE_CONSTRAINT_FIX.md](UNIQUE_CONSTRAINT_FIX.md)

---

## 🚨 Duplicate Number Assignment

### Symptom:
```
Multiple files getting assigned the same program number:
o10286_1 → o10003
o10293_1 → o10003  ← DUPLICATE!
o10301_1 → o10003  ← DUPLICATE!
```

### Fix:
**Already fixed!** All rename functions now use session-level tracking to prevent duplicate assignments.

Just try the operation again and it will work.

**Why:** Loop was reusing same number because registry updates weren't committed.

**Doc:** [DUPLICATE_NUMBER_ASSIGNMENT_FIX.md](DUPLICATE_NUMBER_ASSIGNMENT_FIX.md)

---

## 📦 How to Export Repository

### What It Does:
Creates organized copy of repository with files sorted by round size into folders.

### Usage:
```
1. Repository tab → Click "📦 Export Repository by Round Size"
2. Select destination folder
3. Wait for export to complete
4. Use exported copy for CNC machines, customers, etc.
```

**Features:**
- Standard folders: 5.75, 6.0, 6.25, 6.5, 7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0
- Unusual sizes mapped to nearest standard folder
- Non-destructive (original repository unchanged)

**Doc:** [EXPORT_REPOSITORY_FEATURE.md](EXPORT_REPOSITORY_FEATURE.md)

---

## 🔧 Complete Workflow (Recommended Order)

```
1. 📂 Scan Folder
   → Import files to database

2. 🔄 Sync Registry
   → Mark program numbers as IN_USE

3. 🎯 Detect Round Sizes
   → Identify round sizes for each program

4. 📁 Add to Repository
   → Copy files to managed repository folder

5. 🔍 Manage Duplicates (Complete ALL 3 passes)
   → Pass 1: Delete Content Duplicates (Type 2 & 3)
   → Pass 2: Review/Rename Name Conflicts (Type 1)
   → Pass 3: Fix Underscore Suffixes

6. 🔧 Repair File Paths (if batch rename fails)
   → Fix database file_path entries to match actual files

7. 🔧 Batch Rename Out-of-Range
   → Rename programs to correct ranges

8. 🔄 Sync Filenames with Database
   → Fix any remaining filename mismatches

9. ✓ Verify Repository
   → All files have clean names
   → All filenames match program numbers
   → All database paths are correct

10. 📦 Export Repository by Round Size (optional)
    → Create organized copy for distribution

11. ✅ Done!
```

---

## 🛠️ Available Buttons

### Repository Tab:

**Row 1:**
- **📊 View Repository** - View managed files
- **📁 Add to Repository** - Copy selected files to repository

**Row 2:**
- **🔍 Manage Duplicates** - Three-pass duplicate resolution
- **🔄 Sync Filenames with Database** - Fix filename mismatches

**Row 3:**
- **🎯 Detect Round Sizes** - Identify round sizes
- **🔧 Batch Rename Out-of-Range** - Fix programs in wrong ranges

**Row 4:**
- **📦 Export Repository by Round Size** - Create organized export
- **🔧 Repair File Paths** - Fix database path mismatches

---

## 📚 All Documentation

1. **UNIQUE_CONSTRAINT_FIX.md** - Fix for UNIQUE constraint errors
2. **DUPLICATE_NUMBER_ASSIGNMENT_FIX.md** - Fix for duplicate number assignment
3. **DATABASE_LOCK_FIX.md** - Fix for database locked errors
4. **MISSING_COMMITS_FIX.md** - Fix for "no available numbers" errors
5. **FILENAME_RENAME_FIX.md** - Fix for batch rename file operations
6. **SYNC_FILENAMES_FEATURE.md** - Sync filenames feature (with case fix)
7. **EXPORT_REPOSITORY_FEATURE.md** - Export repository feature
8. **REPAIR_FILE_PATHS_FEATURE.md** - Repair file paths feature
9. **BATCH_RENAME_FAILURE_FIX.md** - Fix for batch rename failures
10. **PROGRAM_NUMBER_FORMAT_FIX.md** - Fix for missing leading zeros
11. **COMPLETE_FIX_SUMMARY_2025-12-03.md** - Complete summary
12. **QUICK_FIX_GUIDE.md** - This document

---

## 🎯 Most Common Issues (Quick Reference)

| Issue | Button to Click | Location |
|-------|----------------|----------|
| Batch rename fails | 🔧 Repair File Paths | Repository tab, Row 4 |
| Filenames have suffixes | 🔍 Manage Duplicates → Pass 3 | Repository tab, Row 2 |
| Filenames don't match DB | 🔄 Sync Filenames with Database | Repository tab, Row 2 |
| Missing leading zeros (o1, o100) | 🔢 Fix Program Number Format | Repository tab, Row 4 |
| Want to export | 📦 Export Repository by Round Size | Repository tab, Row 4 |
| Database locked | (Fixed - just retry) | - |
| No available numbers | (Fixed - just retry) | - |
| UNIQUE constraint | (Fixed - just retry) | - |

---

*All fixes completed: 2025-12-03*
*System status: 🟢 Fully Operational*
