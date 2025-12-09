# Duplicate Handling - Repository vs External Files

## Overview

This document explains how duplicate detection and handling works, and confirms that repository and external files are kept completely separate.

---

## 🎯 Two Different Duplicate Features

### 1. **Rename Duplicates** (During Scanning)
**When:** Happens automatically during folder scanning
**What:** Renames files with duplicate program numbers within the SAME scan
**Scope:** ONLY affects files in the current scan batch

### 2. **Delete Content Duplicates** (Repository Management)
**When:** Manual operation (button in Repository tab)
**What:** Finds and deletes files with identical content (same hash)
**Scope:** ONLY affects repository files (is_managed = 1)

---

## 📂 Feature 1: Rename Duplicates (During Scan)

### What It Does

When you scan a folder, if multiple files have the same program number (e.g., two files named `o12345.nc`), the system automatically renames them with suffixes:
- First file: `o12345` (no change)
- Second file: `o12345(1)`
- Third file: `o12345(2)`
- And so on...

### Code Location

**Lines 2616-2665** and **Lines 2335-2369**

```python
# Track which program numbers we've seen in this scan
seen_in_scan = {}  # program_number -> filepath

# Later, for each file:
if record.program_number in seen_in_scan:
    # Find next available suffix
    suffix = 1
    while f"{original_prog_num}({suffix})" in seen_in_scan:
        suffix += 1
    record.program_number = f"{original_prog_num}({suffix})"
```

### Scope and Safety

✅ **ONLY affects files in the current scan**
- `seen_in_scan` dictionary is created fresh for each scan operation
- Only tracks files being processed in this batch
- Does NOT look at existing database entries

✅ **Works for BOTH repository and external scans**
- If you choose "Repository" mode → renames apply to files being imported
- If you choose "External" mode → renames apply to files being referenced
- This is correct behavior - prevents database conflicts

✅ **Does NOT affect existing files**
- Does NOT rename files already in repository
- Does NOT rename files already in external database
- Does NOT modify any files on disk (only database entries)

### Example

**Scenario:** You scan a USB drive with these files:
```
o12345.nc
o12345_copy.nc  (same program number extracted: o12345)
o67890.nc
```

**Result:**
```
o12345     (first occurrence)
o12345(1)  (second occurrence - renamed in database)
o67890     (no conflict)
```

**Important:**
- If you already have `o12345` in repository from a previous scan, the NEW files will be renamed
- Existing repository file `o12345` is NOT touched
- The renaming happens DURING the scan, not AFTER

---

## 🧹 Feature 2: Delete Content Duplicates

### What It Does

Scans ALL repository files and finds files with **identical content** (same SHA256 hash), then allows you to delete the duplicates while keeping parent/original files.

### Code Location

**Lines 7760-8010**

```python
# Get all managed files from repository
cursor.execute("""
    SELECT program_number, file_path, duplicate_type, parent_file
    FROM programs
    WHERE is_managed = 1    # ← ONLY REPOSITORY FILES!
    ORDER BY program_number
""")
```

### Scope and Safety

✅ **ONLY affects repository files**
- SQL query explicitly filters: `WHERE is_managed = 1`
- External files (`is_managed = 0 or NULL`) are NEVER touched
- Even if external files have duplicate content, they're ignored

✅ **Protects parent files**
- Keeps files marked as `duplicate_type = 'parent'`
- Keeps files with no `parent_file` reference (originals)
- Only deletes child/duplicate copies

✅ **Preview before deletion**
- Shows exactly what will be kept vs deleted
- Requires confirmation
- Can cancel without changes

✅ **Physically deletes files**
- Removes files from `repository/` folder
- Removes database entries
- Does NOT touch external file locations

### Example

**Scenario:** Repository has these files with identical content:
```
o12345 (parent, hash: abc123)
o12345(1) (duplicate, hash: abc123)
o12345(2) (duplicate, hash: abc123)
```

**External files (NOT in repository):**
```
o12345 (hash: abc123, location: E:\USB\o12345.nc)
```

**Result:**
- Repository: KEEP `o12345`, DELETE `o12345(1)` and `o12345(2)`
- External: NOT TOUCHED (even though it has same content/hash)

---

## 🔒 Repository vs External Isolation

### How Files Are Separated

**Repository Files:**
- `is_managed = 1`
- Physical location: `repository/` folder
- Under your control
- Can be deleted, exported, managed

**External Files:**
- `is_managed = 0` or `NULL`
- Physical location: Original scan location (USB, network drive, etc.)
- NOT under your control
- Can only be removed from database (file stays in place)

### Which Features Affect Which Files

| Feature | Repository Files | External Files |
|---------|-----------------|----------------|
| **Rename Duplicates (during scan)** | ✅ Yes (within scan batch) | ✅ Yes (within scan batch) |
| **Delete Content Duplicates** | ✅ Yes | ❌ No (protected) |
| **Delete from Repository** | ✅ Yes | ❌ No (button disabled) |
| **Add to Repository** | ❌ No (already there) | ✅ Yes |
| **Remove from Database** | ❌ No (use Delete) | ✅ Yes |
| **Export Selected** | ✅ Yes | ❌ No |

---

## 💡 Common Questions

### Q1: If I scan a folder externally, will it rename my repository files?
**A: No.** The rename duplicates feature only affects files **within the current scan**. Your existing repository files are not touched.

### Q2: If I delete content duplicates, will it affect my external scans?
**A: No.** The delete content duplicates feature has `WHERE is_managed = 1`, so it ONLY looks at repository files.

### Q3: What if I scan a folder that has the same files as my repository?
**A: Depends on scan mode:**
- **Repository mode:** Files will be renamed with suffixes (e.g., o12345(1)) to avoid conflicts
- **External mode:** Files will be renamed with suffixes (e.g., o12345(1)) as external references

### Q4: Can external files have duplicate content with repository files?
**A: Yes,** and that's fine! They're separate:
- Repository file: `o12345` (in repository/, is_managed=1)
- External file: `o12345` (in E:\USB\, is_managed=0)
- Delete Content Duplicates will ONLY look at repository files

### Q5: Will "Rename Duplicates" change my filenames on disk?
**A: No.** It only changes the `program_number` in the database. The physical file names on disk are NOT changed.

---

## 🎯 Best Practices

### 1. Use Repository Mode for Files You Want to Manage
- Files you'll edit, version, and control
- Files that belong in your organized repository
- Files you want duplicate cleanup for

### 2. Use External Mode for Temporary Scans
- USB drive scans (quick lookup)
- Network drive references
- Files you don't want to copy
- Files you'll migrate later if needed

### 3. Run Delete Content Duplicates Periodically
- After importing many files
- To clean up repository storage
- Before creating backups
- When you notice duplicates

### 4. Don't Worry About Cross-Contamination
- Repository and external files are completely isolated
- Delete operations respect the boundary
- Rename operations only affect current scan

---

## 📊 Summary

### ✅ Rename Duplicates (Scan Time)
- **Affects:** Current scan batch only
- **Repository:** Yes (within scan)
- **External:** Yes (within scan)
- **Existing files:** No
- **Safety:** High (isolated to scan)

### ✅ Delete Content Duplicates (Repository Management)
- **Affects:** Repository files only
- **Repository:** Yes
- **External:** No (protected)
- **Existing files:** Yes (repository only)
- **Safety:** High (external files protected)

### ✅ Complete Isolation
- Repository files: Managed, organized, deletable
- External files: Referenced, temporary, protected
- No cross-contamination between the two areas
- Clear separation enforced by `is_managed` flag

---

**Conclusion:** Your repository files and external/scanned files are kept completely separate. You can safely use all duplicate features without worrying about accidentally affecting the wrong files!
