# Version History Comparison Fix

**Date**: 2026-02-07
**Issue**: "Compare Version" button failed with error about not finding archive files
**Status**: ✅ FIXED

---

## Problem

When clicking "View Version" → "Compare to Current" for archived versions, you got an error message saying it couldn't find the version location.

### Root Cause

The version history system uses a **hybrid approach**:
- **Database**: `program_versions` table stores some versions
- **Archive**: `archive/` folder stores file-based versions

The bug: The comparison code only looked in the database (`program_versions` table), but **archive versions don't exist there** - they only exist as physical files in the `archive/` folder.

When you selected an archive version and clicked "Compare to Current", it tried to query the database for a version_id that didn't exist, causing the error.

---

## Solution Implemented

Updated two methods in `VersionHistoryWindow` class:

### 1. `compare_to_current()` - Line ~26223

**Now checks the version source first:**

```python
source = tags[0]  # 'database' or 'archive'
version_number = tags[1]

if source == 'database':
    # Get content from program_versions table
    query database for version content

elif source == 'archive':
    # Get content from archive/ folder
    search in: archive/YYYY-MM-DD/ folders
    find file: o#####_v1.0.nc (or .nc.gz if compressed)
    read and decompress if needed
```

### 2. `restore_version()` - Line ~26340

**Same fix applied:**
- Checks source (database vs archive)
- Retrieves content from correct location
- Creates backup before restoring
- Writes restored content to current file

---

## How It Works Now

### For Database Versions:
1. Query `program_versions` table
2. Get `file_content` column
3. Use for comparison/restore

### For Archive Versions:
1. Find `archive/` folder (next to `repository/`)
2. Search all date folders: `archive/YYYY-MM-DD/`
3. Look for: `o#####_v[version].nc` or `.nc.gz`
4. Read file (decompress if `.gz`)
5. Use for comparison/restore

---

## Archive File Location

**Expected structure:**
```
l:\My Drive\Home\File organizer\
├── repository/
│   └── o57508.nc (current version)
├── archive/
│   ├── 2026-02-06/
│   │   ├── o57508_v1.0.nc
│   │   ├── o57508_v2.0.nc
│   │   └── o13025_v1.0.nc.gz (compressed)
│   ├── 2026-02-05/
│   │   └── ...
│   └── [other dates]/
└── gcode_database.db
```

**File naming:**
- Pattern: `{program_number}_v{version_number}.nc`
- Example: `o57508_v1.0.nc`
- Compressed: `o57508_v1.0.nc.gz` (files >90 days old)

---

## What Changed

### Before (Broken):
```python
# Always looked in database only
cursor.execute("SELECT file_content FROM program_versions WHERE version_id = ?", ...)
# FAILED for archive versions - they don't have version_id in database!
```

### After (Fixed):
```python
# Check source first
if source == 'database':
    # Get from database
    cursor.execute("SELECT file_content FROM program_versions WHERE program_number = ? AND version_number = ?", ...)
elif source == 'archive':
    # Get from archive files
    find file in archive/YYYY-MM-DD/ folders
    read and decompress if needed
```

---

## Error Messages

The fix provides clear error messages if something goes wrong:

### Archive folder not found:
```
Archive folder not found:
l:\My Drive\Home\File organizer\archive\

Archive versions are stored in archive/ folder next to repository/
```

### Archive file not found:
```
Archive file not found for version 1.0

Expected location: l:\My Drive\Home\File organizer\archive/YYYY-MM-DD/
Filename: o57508_v1.0.nc
```

These help diagnose if the archive structure is incorrect.

---

## Testing

**To verify the fix:**

1. **View Version History** for a program that has archived versions
2. **Select an archive version** (shows "📦 Archive" in source column)
3. **Click "Compare to Current"**
   - Should open comparison window
   - Shows side-by-side diff
   - No errors!

4. **Try "Restore This Version"** (optional)
   - Creates backup first
   - Restores selected version
   - Should work for both database and archive versions

---

## Benefits

✅ **Works with both version sources** - database and archive
✅ **Handles compressed files** - automatic .gz decompression
✅ **Clear error messages** - helps diagnose archive issues
✅ **Safe restoration** - creates backup before overwriting
✅ **Unified interface** - no need to know where version is stored

---

## Files Modified

**gcode_database_manager.py**:
- Line ~26223: Fixed `compare_to_current()` method
  - Added source detection
  - Added archive file reading logic
  - Added gzip decompression support

- Line ~26340: Fixed `restore_version()` method
  - Same fixes as compare_to_current
  - Ensures restore works for archive versions

---

## Complete Fix Summary

The version history system now properly supports the hybrid architecture:
- Database versions: Retrieved from `program_versions` table
- Archive versions: Retrieved from `archive/YYYY-MM-DD/` folders
- Compressed archives: Automatically decompressed when read
- Both sources work seamlessly in the same interface

**Just restart the application and try "View Version" → "Compare to Current" again!**

---

**Fix Complete**: 2026-02-07
**Ready to Use**: Yes - restart application and test
