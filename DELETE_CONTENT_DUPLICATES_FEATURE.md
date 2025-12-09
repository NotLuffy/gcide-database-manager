# Delete Content Duplicates Feature

## Overview

The "Delete Content Duplicates" feature helps you clean up your repository by finding and deleting files with identical content while keeping parent/original files safe.

## How It Works

### 1. Content Analysis
- Calculates SHA256 hash for every file in the repository
- Groups files with identical content (same hash)
- Identifies parent files vs duplicate files

### 2. Smart Duplicate Detection
The feature uses intelligent logic to determine which files to keep:

**Priority 1: Keep Parent Files**
- Files marked as `duplicate_type = 'parent'`
- Files with no `parent_file` reference (originals)

**Priority 2: Keep Lowest Program Number**
- If no parent is marked, keeps the file with the lowest program number
- Example: If o12345 and o12345(1) have same content, keeps o12345

### 3. Safe Deletion
- Shows detailed preview of what will be deleted
- Requires confirmation before deleting
- Only deletes duplicates, never the parent/original

## Usage

### Step 1: Access the Feature
1. Go to the **📁 Repository** tab
2. Click the **🧹 Delete Content Duplicates** button

### Step 2: Review Analysis
The tool will:
- Scan all files in repository
- Calculate content hashes
- Show duplicate groups
- Display what will be kept vs deleted

**Example Output:**
```
DUPLICATE GROUPS
================================================================================

Group (3 files with identical content):
  ✓ KEEP: o12345 (parent/original)
  ✗ DELETE: o12345(1) (duplicate child)
  ✗ DELETE: o12345(2) (duplicate child)

Group (2 files with identical content):
  ✓ KEEP: o67890 (lowest program number)
  ✗ DELETE: o67891

SUMMARY
================================================================================
Files to delete: 3
Files to keep: 2
```

### Step 3: Confirm or Cancel
- **✓ Confirm Delete** - Proceed with deletion
- **✗ Cancel** - Close without making changes

### Step 4: Review Results
After deletion:
- Shows count of successfully deleted files
- Lists any errors that occurred
- Automatically refreshes the view

## Safety Features

### ✅ Parent Protection
- **Always keeps parent files**
- Parent files are identified by `duplicate_type = 'parent'`
- Original files (no parent reference) are also protected

### ✅ Preview Before Delete
- Shows exactly what will be deleted
- Lists reason for each deletion
- No surprises - you see everything first

### ✅ Activity Logging
- All deletions are logged to `activity_log` table
- Includes timestamp, user, and count of deleted files
- Audit trail for accountability

### ✅ Error Handling
- Continues if individual file deletion fails
- Reports errors without stopping the process
- Shows final count of successes and errors

## Example Scenarios

### Scenario 1: Multiple Scans of Same File
**Situation:** You scanned the same file multiple times
```
o12345   - Original (hash: abc123)
o12345(1) - Duplicate scan (hash: abc123)
o12345(2) - Another duplicate (hash: abc123)
```

**Result:**
- **KEEP:** o12345 (parent/original)
- **DELETE:** o12345(1), o12345(2)

---

### Scenario 2: Files with Same Content, Different Names
**Situation:** Two files with different names but identical content
```
o10000 - First file (hash: def456)
o10001 - Same content (hash: def456)
```

**Result:**
- **KEEP:** o10000 (lowest program number)
- **DELETE:** o10001

---

### Scenario 3: Parent and Children
**Situation:** A parent with multiple children (variations)
```
o55000 - Parent (hash: ghi789, duplicate_type='parent')
o55001 - Child variation (hash: ghi789, parent_file='o55000')
o55002 - Another child (hash: ghi789, parent_file='o55000')
```

**Result:**
- **KEEP:** o55000 (marked as parent)
- **DELETE:** o55001, o55002

---

### Scenario 4: No Duplicates
**Situation:** All files have unique content

**Result:**
```
✓ No content duplicates found!

All files in repository have unique content.
```

## Technical Details

### Hash Algorithm
- Uses **SHA256** for content hashing
- Reads files in 4KB chunks for memory efficiency
- Produces 64-character hexadecimal hash

### Duplicate Detection Logic
```python
if parent_files:
    # Keep first parent (or lowest program number if multiple parents)
    keeper = sorted(parent_files)[0]
    delete_others = parent_files[1:] + child_files
else:
    # No parent files, keep lowest program number
    keeper = sorted(duplicates)[0]
    delete_others = duplicates[1:]
```

### Database Query
```sql
SELECT program_number, file_path, duplicate_type, parent_file
FROM programs
WHERE is_managed = 1
ORDER BY program_number
```

## Performance

### Speed
- **Small repositories** (< 100 files): < 5 seconds
- **Medium repositories** (100-1000 files): 10-30 seconds
- **Large repositories** (> 1000 files): 1-3 minutes

### Progress Updates
- Shows progress every 50 files during hash calculation
- Real-time updates during deletion
- Updates every 10 files deleted

## Limitations

### Only Works on Repository Files
- Only analyzes files with `is_managed = 1`
- External files are NOT included
- Reason: Only repository files are under your control

### Cannot Undo
- Deletion is permanent
- Files are removed from both database and disk
- **Recommendation:** Create a backup before running

### Missing Files
- Files that don't exist on disk are skipped
- Counted separately in analysis
- Not included in deletion

## Best Practices

### 1. Review Before Confirming
- Always read the preview carefully
- Check which files will be deleted
- Verify parent files are marked correctly

### 2. Regular Cleanup
- Run periodically to keep repository clean
- Especially useful after bulk imports
- Helps reduce storage usage

### 3. Backup First
- Use **File → Backup Database** before running
- Allows recovery if needed
- Good practice for any bulk operation

### 4. Check Activity Log
- Review the `activity_log` table after deletion
- Verify counts match expectations
- Useful for auditing

## Troubleshooting

### Issue: Parent File Gets Deleted
**Cause:** File not properly marked as parent
**Solution:** Before running, ensure `duplicate_type = 'parent'` is set correctly

### Issue: Wrong File Kept
**Cause:** No parent marked, so lowest program number kept
**Solution:** Mark the desired file as parent first

### Issue: Files Not Found
**Cause:** Database references invalid file paths
**Solution:** Run this query to find missing files:
```sql
SELECT program_number, file_path
FROM programs
WHERE is_managed = 1 AND (file_path IS NULL OR file_path = '')
```

### Issue: Deletion Fails
**Cause:** File permissions, file in use, or disk error
**Solution:**
- Check file permissions
- Close any programs using the files
- Check disk health

## Button Location

**Repository Tab → 🧹 Delete Content Duplicates**

Located in the second row of repository management buttons, below "Delete from Repository" and "Export Selected".

## Activity Logging

All deletions are logged:
```json
{
  "action_type": "delete_content_duplicates",
  "program_number": "batch",
  "details": {
    "deleted_count": 15,
    "error_count": 0
  },
  "timestamp": "2025-11-26 19:45:00"
}
```

## Summary

The Delete Content Duplicates feature:
- ✅ Finds files with identical content (same hash)
- ✅ Keeps parent/original files safe
- ✅ Shows detailed preview before deletion
- ✅ Requires confirmation
- ✅ Logs all activity
- ✅ Reports errors gracefully
- ✅ Saves storage space
- ✅ Cleans up repository efficiently

**Use this feature to maintain a clean, organized repository without duplicate content!**
