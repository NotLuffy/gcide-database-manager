# Repository File Management Analysis

## Current State

### Repository Statistics
- **Files in repository:** 9,301
- **Programs in database:** 8,210
- **Extra files (not in DB):** 1,091 files
- **All DB programs marked as managed:** 8,210 (100%)

### Issue Identified

**Problem:** The repository has **1,091 more files** than database entries. This means:
1. Old/duplicate files are accumulating
2. No automatic cleanup/archival system
3. Multiple versions of same program exist with different extensions

---

## File Issues Found

### 1. **Duplicate Extensions** (315 programs affected)

Many programs have multiple files with different extensions or case variations:

```
o00800: ['o00800', 'O00800.nc']
o01006: ['o01006', 'o01006.nc']
o10000: ['o10000', 'o10000.nc']
```

**Impact:** When a new file is imported:
- System doesn't delete old versions
- Both files remain in repository
- Database only tracks ONE file path

### 2. **"Copy of" Files** (2+ files)

Manual file copies exist in repository:
```
Copy of O61213
Copy of O73238
```

**Impact:** Manual copies are not tracked in database

### 3. **Case Sensitivity Issues**

Files with different case but same program number:
```
O00002.nc (uppercase O)
o00002.nc (lowercase o)
```

Windows treats these as different files, causing duplicates.

---

## Current File Management System

### What EXISTS:

**File Import System** (gcode_database_manager.py):
```python
def import_to_repository(self, source_file, program_number=None):
    """
    Import a file into the managed repository.

    Behavior:
    - Checks if file already exists
    - If identical content: keeps existing file
    - If different content: creates collision file (base_1.nc, base_2.nc)
    - Does NOT delete old files
    """
```

**File Migration System:**
```python
def migrate_file_to_repository(self, program_number):
    """
    Migrate external file to repository.

    Behavior:
    - Copies file to repository
    - Updates database path
    - Marks as managed (is_managed=1)
    """
```

### What DOES NOT EXIST:

❌ **No Automatic Cleanup**
- Old files are never removed
- Duplicates accumulate over time
- No orphan file detection

❌ **No Archive System**
- No archive folder for old versions
- No archive tracking table
- No date-based archival

❌ **No File Deletion on Update**
- When program updated, old file remains
- New file created with suffix (_1, _2, etc.)
- Both files exist indefinitely

---

## What Happens When Files Are Updated

### Scenario 1: **Same filename imported**

**Action:** Import "o10000.nc" when "o10000" already exists

**Current Behavior:**
1. Check if content is identical
2. If identical: Keep existing, skip import
3. If different: Create "o10000_1.nc"
4. Update database to point to "o10000_1.nc"
5. **OLD FILE REMAINS: "o10000" stays in repository**

**Result:** 2 files in repository, 1 entry in database

### Scenario 2: **New file with same program number**

**Action:** Add new version of o10535 from external source

**Current Behavior:**
1. Import to repository (collision handling creates o10535_2.nc)
2. Database updated with new path
3. **OLD FILES REMAIN: o10535, o10535_1.nc stay in repository**

**Result:** 3 files in repository, 1 entry in database

### Scenario 3: **Program deleted from database**

**Action:** Delete program entry from database

**Current Behavior:**
1. Database entry removed
2. **FILE REMAINS IN REPOSITORY** (by design for safety)

**Result:** Orphan file in repository

---

## Recommended Solutions

### 1. **Automatic Archive System** ⭐ PRIORITY

Create archive folder and move old files:

```python
def archive_old_file(self, old_file_path, program_number):
    """
    Move old file to archive folder before importing new version.

    Structure:
    repository/
        o10000.nc        (current version)
    archive/
        2025-12-10/
            o10000.nc    (archived version)
            o10535_old.nc
    """
    archive_folder = os.path.join(self.repository_path, 'archive',
                                   datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(archive_folder, exist_ok=True)

    # Move old file to archive
    archive_path = os.path.join(archive_folder, os.path.basename(old_file_path))
    shutil.move(old_file_path, archive_path)

    # Log to database
    self.log_activity('archive_file', program_number, {
        'old_path': old_file_path,
        'archive_path': archive_path
    })
```

**When to trigger:**
- Before importing new version of existing program
- When user explicitly archives
- Scheduled cleanup (weekly/monthly)

### 2. **Orphan File Cleanup**

Detect and handle files not in database:

```python
def detect_orphan_files(self):
    """Find files in repository not tracked in database"""
    cursor = self.conn.cursor()
    cursor.execute('SELECT file_path FROM programs')
    tracked_files = set(row[0] for row in cursor.fetchall())

    repo_files = set(os.listdir(self.repository_path))

    orphans = []
    for filename in repo_files:
        full_path = os.path.join(self.repository_path, filename)
        if full_path not in tracked_files:
            orphans.append(full_path)

    return orphans

def cleanup_orphans(self, action='archive'):
    """
    Handle orphan files

    action: 'archive' | 'delete' | 'list'
    """
    orphans = self.detect_orphan_files()

    if action == 'archive':
        for orphan in orphans:
            self.archive_old_file(orphan, 'orphan')
    elif action == 'delete':
        for orphan in orphans:
            os.remove(orphan)

    return len(orphans)
```

### 3. **Duplicate Extension Consolidation**

Standardize to single extension (.nc preferred):

```python
def consolidate_duplicates(self):
    """
    Find program numbers with multiple files and keep only one.

    Priority:
    1. .nc extension (standard)
    2. Newest file (by modification date)
    3. Largest file (most complete)
    """
    from collections import defaultdict

    file_groups = defaultdict(list)

    # Group files by program number
    for filename in os.listdir(self.repository_path):
        base = os.path.splitext(filename)[0].lower()
        file_groups[base].append(filename)

    # Handle duplicates
    for prog_num, files in file_groups.items():
        if len(files) > 1:
            # Choose best file
            best_file = self._choose_best_file(files)

            # Archive others
            for f in files:
                if f != best_file:
                    self.archive_old_file(
                        os.path.join(self.repository_path, f),
                        prog_num
                    )
```

### 4. **Archive Management UI**

Add to GUI:
- View archived files by date
- Restore archived file (promote back to repository)
- Permanently delete old archives (>6 months)
- Archive statistics (space saved, files archived)

### 5. **Automatic Cleanup Schedule**

Run weekly/monthly:
```python
def scheduled_cleanup(self):
    """Run all cleanup operations"""
    # 1. Consolidate duplicates
    duplicates_cleaned = self.consolidate_duplicates()

    # 2. Archive orphans
    orphans_archived = self.cleanup_orphans(action='archive')

    # 3. Delete old archives (>6 months)
    old_archives_deleted = self.delete_old_archives(days=180)

    # 4. Generate report
    return {
        'duplicates_cleaned': duplicates_cleaned,
        'orphans_archived': orphans_archived,
        'old_archives_deleted': old_archives_deleted
    }
```

---

## Immediate Action Items

### Critical (Do Now):

1. ✅ **Document current state** (this file)
2. ⚠️ **Create archive folder structure**
3. ⚠️ **Run orphan detection** (identify 1,091 extra files)
4. ⚠️ **Implement archive_old_file() function**

### High Priority (Do Soon):

5. ⚠️ **Add cleanup to import workflow** (archive before importing)
6. ⚠️ **Consolidate duplicate extensions** (fix 315 duplicates)
7. ⚠️ **Add archive management to GUI**

### Medium Priority (Do Later):

8. ⚠️ **Implement scheduled cleanup**
9. ⚠️ **Add archive restore functionality**
10. ⚠️ **Create archive cleanup policy** (delete >6 months)

---

## Safety Considerations

### When Archiving/Deleting Files:

**ALWAYS:**
- ✅ Create backup before bulk operations
- ✅ Log all file movements to activity_log
- ✅ Verify file integrity after move
- ✅ Provide "undo" option for recent archives
- ✅ Show confirmation dialog for destructive operations

**NEVER:**
- ❌ Delete files without archiving first
- ❌ Modify repository while database operations are running
- ❌ Remove files that are in edit_locks table
- ❌ Archive current version (only old versions)

---

## Storage Impact

### Current State:
- Repository folder: ~100MB (estimated 9,301 files)
- 1,091 orphan/duplicate files: ~12-15MB wasted

### After Cleanup:
- Repository: ~85MB (8,210 active files)
- Archive: ~15MB (moved old versions)
- **Benefit:** Cleaner repository, easier to navigate, faster file operations

---

## Questions to Answer

1. **Archive Retention:** How long to keep archived files?
   - Suggestion: 6 months, then prompt for deletion

2. **Duplicate Handling:** Which file to keep when duplicates exist?
   - Suggestion: .nc extension preferred, newest file as tiebreaker

3. **Orphan Files:** What to do with "Copy of" files?
   - Suggestion: Archive immediately, never needed

4. **User Control:** Should users manually trigger cleanup or automatic?
   - Suggestion: Automatic weekly, with manual option in GUI

5. **Archive Access:** Should archived files be searchable/viewable?
   - Suggestion: Yes, add "View Archives" tab in GUI

---

## Conclusion

**Current System:**
- ✅ File import works correctly
- ✅ Repository management exists
- ❌ No cleanup/archival automation
- ❌ Files accumulate indefinitely
- ❌ 1,091 extra files in repository

**Recommended Next Steps:**
1. Implement archive system (archive_old_file function)
2. Run one-time cleanup (consolidate 1,091 extra files)
3. Add archive step to import workflow
4. Create GUI for archive management
5. Schedule automatic cleanup

**Impact:** Cleaner repository, better performance, easier maintenance
