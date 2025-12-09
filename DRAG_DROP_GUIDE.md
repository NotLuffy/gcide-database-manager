# Drag & Drop File Import - User Guide

## Overview
The database manager now supports intelligent drag-and-drop file importing with comprehensive safety checks and smart detection features.

## Features

### 🎯 Smart Detection Features

1. **Exact Duplicate Detection**
   - Detects if dropped file is identical to existing file (content hash comparison)
   - Automatically skips exact duplicates
   - Shows which existing file is the duplicate of

2. **Filename Collision Warnings**
   - Detects when filename already exists but content is different
   - Offers auto-rename suggestion with incremented program number
   - Example: `o57000.nc` → `o57001.nc`
   - Updates internal program number to match new filename

3. **Program Number Mismatch Detection**
   - Compares filename program number with internal program number
   - Example: File named `o57000.nc` but contains `O58000` inside
   - Warns you before importing
   - Lets you decide whether to proceed or skip

4. **Program Number Conflict Detection**
   - Detects if program number already exists in database
   - Shows existing filename vs new filename
   - Lets you replace or skip

## How to Use

### Installation (Required for Drag & Drop)

The drag-drop feature requires the `tkinterdnd2` library:

```bash
pip install tkinterdnd2
```

**Note:** If tkinterdnd2 is not installed, the feature will fall back to the existing "Scan Folder" method.

### Using Drag & Drop

1. **Launch the Database Manager:**
   ```bash
   python gcode_database_manager.py
   ```

2. **Drag Files:**
   - Drag one or more G-code files from File Explorer
   - Drag directly onto the database manager window

3. **Visual Feedback:**
   - Window background changes when files are over it
   - Status message shows "Drop files here to import..."

4. **Drop Files:**
   - Release mouse to drop files
   - Smart detection begins automatically

5. **Review Warnings:**
   - Interactive dialogs for each issue found
   - Make decisions for each file

6. **View Summary:**
   - Final summary shows what was added/skipped
   - Status bar updates with import count

## Detection Scenarios

### Scenario 1: Exact Duplicate
```
File: o57000.nc
Status: Skipped (automatic)
Reason: Identical to existing o57000.nc in database
```

### Scenario 2: Filename Collision (Different Content)
```
File: o57000.nc
Existing: o57000.nc (different content)

Dialog:
  File already exists: o57000.nc
  In database as: o57000

  The file you're adding has DIFFERENT content.

  Options:
  • YES: Save with suggested name: o57001.nc
  • NO: Skip this file
  • CANCEL: Stop importing

  Suggested name will also update internal program number.
```

**If you select YES:**
- File is renamed to `o57001.nc`
- Internal program number is updated to `O57001`
- File is copied to target folder with new name
- Added to database as `o57001`

### Scenario 3: Program Number Mismatch
```
File: o57000.nc
Internal: O58000

Dialog:
  Warning: Filename and internal program number don't match!

  Filename: o57000.nc (o57000)
  Internal: O58000

  This file may have been renamed incorrectly.

  Add it anyway?
  (It will be stored as o57000 based on filename)
```

**Common Causes:**
- File was manually renamed
- File was copied with wrong name
- Internal program number wasn't updated after renaming

**If you select YES:**
- File is added as `o57000` (based on filename)
- Warning is logged in summary
- You may want to edit the file later to fix the mismatch

### Scenario 4: Program Number Already Exists
```
File: o57000.nc
Existing: o57000_OLD.nc

Dialog:
  Program number o57000 already exists!

  Existing: o57000_OLD.nc
  New file: o57000.nc

  These appear to be different files with the same program number.

  Add the new file anyway?
  (Will replace the existing entry)
```

**If you select YES:**
- Existing database entry for `o57000` is replaced
- Old file (`o57000_OLD.nc`) remains in folder but no longer in database
- New file (`o57000.nc`) becomes the database entry for `o57000`

### Scenario 5: All Checks Pass
```
File: o62500.nc
Status: Added successfully
```

## File Requirements

### Valid G-Code Files

Files must contain the pattern `o#####` (4 or more digits):
- ✅ `o57000.nc`
- ✅ `o62500.gcode`
- ✅ `O75647`
- ✅ `o12345678.txt`

Files without this pattern are rejected:
- ❌ `spacer.nc`
- ❌ `program.gcode`
- ❌ `test.txt`

## Auto-Rename Logic

When a filename collision is detected, the system suggests a new name:

**Original:** `o57000.nc`

**Suggestion Algorithm:**
1. Extract program number: `o57000`
2. Increment: `o57001`
3. Check if `o57001.nc` exists
4. If exists, try `o57002`
5. Continue until unique name found

**Examples:**
- `o57000.nc` → `o57001.nc`
- `o57000_V2.nc` → `o57001_V2.nc`
- `O62500.gcode` → `O62501.gcode`

## Summary Messages

After processing, you'll see a summary dialog:

```
Import Summary

Processed 5 file(s)
Added: 3

Details:
✅ Added: o57001.nc
✏️ Renamed: o57000.nc → o57002.nc
⚠️ Added with mismatch: o58000.nc (internal: O58001)
🔁 Duplicate: o62500.nc is identical to o62500.nc (already in database)
⏭️ Skipped: o75000.nc (filename collision)
```

### Status Icons:
- ✅ **Added** - Successfully imported
- ✏️ **Renamed** - Imported with auto-generated name
- ⚠️ **Added with mismatch** - Imported but filename ≠ internal program number
- 🔁 **Duplicate** - Skipped (exact copy already exists)
- ⏭️ **Skipped** - Not imported (user declined)
- ❌ **Error** - Failed to import

## Target Folder Requirement

Before using drag-drop, ensure you have a target folder configured:

1. Go to Settings (if available)
2. Set target folder path
3. This is where imported files are copied to

If no target folder is set, you'll see:
```
Error: No Target Folder
Please set a target folder in settings before importing files.
```

## Tips & Best Practices

### 1. **Review Before Dropping**
- Check filenames before dropping
- Ensure filenames match internal program numbers
- Avoid dropping large batches initially (test with 1-2 files first)

### 2. **Trust the Auto-Rename**
- Auto-rename suggestions are safe
- They increment program numbers logically
- They update internal program numbers automatically

### 3. **Handle Mismatches**
- If you see a mismatch warning, investigate the file
- Open the file to verify the internal program number
- Consider fixing the file before importing

### 4. **Use Batch Import Wisely**
- Drop multiple files at once
- System processes each file individually
- You can cancel mid-batch if needed

### 5. **Check the Summary**
- Always review the import summary
- Look for warnings and errors
- Verify expected files were added

## Fallback Method

If `tkinterdnd2` is not installed, use the existing "Scan Folder" button:
1. Click "Scan Folder" in the Database Management ribbon
2. Select folder containing G-code files
3. Same duplicate detection applies

## Troubleshooting

### Drag-Drop Not Working
```
[Drag & Drop] TkinterDnD2 not installed, using fallback method
```

**Solution:** Install tkinterdnd2
```bash
pip install tkinterdnd2
```

### Files Not Recognized
```
No G-Code files found in 3 dropped file(s).
G-Code files must contain pattern: o##### (4+ digits)
```

**Solution:** Ensure files have `o#####` pattern in filename

### No Target Folder Error
```
Error: No Target Folder
Please set a target folder in settings before importing files.
```

**Solution:** Configure target folder in settings or config file

## Technical Details

### Detection Methods

**1. Content Hash Comparison:**
```python
content_hash = hash(file_content)
if content_hash in existing_hashes:
    # Exact duplicate
```

**2. Filename Lookup:**
```python
filename_lower = filename.lower()
if filename_lower in existing_filenames:
    # Filename collision
```

**3. Program Number Extraction:**
```python
# From filename
file_prog_num = extract_from_filename(filename)

# From content
internal_prog_num = extract_from_content(content)

if file_prog_num != internal_prog_num:
    # Mismatch detected
```

### File Processing Flow

```
1. Drop files onto window
   ↓
2. Filter for G-code files (o##### pattern)
   ↓
3. For each file:
   a. Check exact duplicate → Skip if found
   b. Check filename collision → Offer rename
   c. Check program number mismatch → Warn
   d. Check program number exists → Confirm replace
   ↓
4. Copy approved files to target folder
   ↓
5. Parse and add to database
   ↓
6. Show summary dialog
   ↓
7. Refresh results table
```

## Implementation Files

**Modified:** [gcode_database_manager.py](gcode_database_manager.py)

**New Methods:**
- `setup_drag_drop()` - Initialize drag-drop handlers (line 931)
- `on_drag_enter()` - Visual feedback on drag (line 956)
- `on_drag_leave()` - Restore appearance (line 962)
- `on_drop()` - Handle dropped files (line 968)
- `process_dropped_files()` - Main processing logic (line 1028)
- `_suggest_unique_filename()` - Auto-rename logic (line 1190)
- `_extract_program_number_from_content()` - Parse internal program number (line 1215)
- `_import_files()` - Database insertion (line 1227)

## Future Enhancements

Potential improvements:
- Drag entire folders (not just files)
- Preview dropped files before importing
- Undo last import
- Batch rename multiple files
- Export/import file lists
