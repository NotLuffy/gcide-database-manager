# Database Backup & Restore System

## Overview

The G-Code Database Manager includes a comprehensive backup and restore system that automatically saves database snapshots in your program folder.

## Backup Location

All backups are stored in:
```
File organizer/database_backups/
```

## Features

### 1. Manual Backup (💾 Backup Now)

**Location:** Backup tab in ribbon

**What it does:**
- Creates a timestamped backup of your current database
- Filename format: `gcode_db_backup_YYYY-MM-DD_HH-MM-SS.db`
- Stores in `database_backups` folder
- No limit on number of backups (you can keep as many as you want)

**Use this when:**
- Before making major changes to the database
- Before batch operations (rename, delete, etc.)
- After completing successful work you want to save
- Before rescanning with new parser updates

**Example:**
```
gcode_db_backup_2025-12-05_14-30-45.db
```

### 2. Automatic Backups

The system automatically creates backups before:
- **Rescan Database operations** - Protects against parser issues
- **Duplicate deletion** - Safety before removing files
- **Restore operations** - Saves current state as `before_restore_TIMESTAMP.db`

### 3. Restore from Backup (📂 Restore Backup)

**Location:** Backup tab in ribbon

**What it does:**
- Opens file browser to select a backup file
- Creates safety backup of current database first (`before_restore_TIMESTAMP.db`)
- Replaces current database with selected backup
- Requires application restart to load restored data

**Safety Features:**
- ⚠️ **Warning dialog** before restore
- **Automatic backup** of current state before restoration
- Cannot restore while database is being modified

**Steps:**
1. Click "📂 Restore Backup"
2. Select backup file from `database_backups` folder
3. Confirm restoration (read warning carefully!)
4. Current database backed up automatically
5. Selected backup replaces current database
6. Restart application to load restored data

### 4. View Backups (📋 View Backups)

**Location:** Backup tab in ribbon

**What it does:**
- Shows all available backups in a table
- Displays for each backup:
  - Filename
  - Record count (number of programs)
  - Date created
  - File size (MB)
- Allows direct restore or delete from the list

**Features:**
- **Refresh** - Update backup list
- **Restore** - Restore selected backup
- **Delete** - Remove selected backup file
- Sorted by date (newest first)

## Backup Storage Strategy

### What's Backed Up

The database file contains:
- All program records (O-numbers, titles, dimensions)
- File paths and metadata
- Validation status and issues
- Duplicate tracking information
- Version history
- Program registry
- User notes and modifications

### What's NOT Backed Up

- The actual .nc G-code files (only references to them)
- Repository folder structure
- Application settings (config.json)
- Machine Learning models

## Recommended Backup Workflow

### Daily Use
1. **Start of day:** Note current state (optional manual backup)
2. **Before major changes:** Create manual backup
3. **After successful work:** Create named backup for the milestone

### Before Risky Operations
- Before: **Rescan Database** (automatic)
- Before: **Delete Duplicates** (automatic)
- Before: **Batch Rename** (manual recommended)
- Before: **Fix Program Numbers** (manual recommended)

### Weekly Maintenance
- Review old backups in "View Backups"
- Keep important milestone backups
- Delete unnecessary intermediate backups

## Backup File Naming

### Manual Backups
```
gcode_db_backup_2025-12-05_14-30-45.db
```
- Format: `gcode_db_backup_YYYY-MM-DD_HH-MM-SS.db`
- Easy to identify by date/time

### Automatic Backups
```
before_restore_2025-12-05_14-35-20.db
before_load_20251205_143000.db
```
- Prefix indicates operation type
- Timestamp for tracking

## Restoring Data

### Quick Restore (Recent Backup)
1. Go to **Backup** tab
2. Click **View Backups**
3. Select desired backup
4. Click **Restore**
5. Confirm warning
6. Restart application

### Restore from File Browser
1. Go to **Backup** tab
2. Click **Restore Backup**
3. Navigate to backup file (or select from another location)
4. Confirm warning
5. Restart application

### Manual Restore (Advanced)
1. Close application completely
2. Navigate to `File organizer` folder
3. Rename current `gcode_database.db` to `gcode_database.db.old` (safety)
4. Copy backup file to `gcode_database.db`
5. Restart application

## Backup Best Practices

### DO:
✅ Create backup before major changes
✅ Keep backups of known-good states
✅ Label important backups clearly (rename file)
✅ Test restore occasionally to verify backups work
✅ Keep backups of milestone achievements

### DON'T:
❌ Delete all backups (keep at least a few recent ones)
❌ Restore without reading the warning
❌ Modify backup files manually
❌ Store backups in the repository folder (keep in `database_backups`)

## Storage Management

### Disk Space
- Each backup is ~5-50 MB depending on database size
- 10 backups ≈ 50-500 MB
- Monitor disk space if keeping many backups

### Cleanup
The system does NOT automatically delete old backups. You control retention:
- Use "View Backups" to see all backups
- Delete old/unnecessary backups manually
- Keep important milestone backups long-term

## Recovery Scenarios

### Scenario 1: "I deleted files by mistake"
1. Immediately stop work
2. Restore most recent backup before deletion
3. Lost data = changes after backup was created

### Scenario 2: "Parser update broke everything"
1. Restore backup from before rescan
2. Report parser issue
3. Wait for fix, then rescan again

### Scenario 3: "I want to test changes safely"
1. Create manual backup first
2. Make experimental changes
3. If successful: keep changes
4. If failed: restore backup

### Scenario 4: "Application won't start"
1. Close application
2. Manually restore backup (see Manual Restore above)
3. Restart application

## Technical Details

### Backup Format
- Standard SQLite database file (.db)
- Can be opened with any SQLite viewer
- Fully portable (can copy to another computer)

### Backup Process
1. Copy entire database file
2. Preserve file timestamps
3. Store in dedicated backup folder
4. No compression (for easy recovery)

### Restore Process
1. Create safety backup of current state
2. Replace current database with backup file
3. Preserve backup file (not deleted after restore)

## Integration with Other Features

### Works With:
- **Repository System** - Backs up file references
- **Version History** - Backs up all versions
- **Program Registry** - Backs up registry data
- **Duplicate Tracking** - Backs up duplicate groups

### Compatible With:
- **Database Profiles** (separate feature for switching between databases)
- **Export Repository** (exports files, not database)
- **Manual database edits** (via Edit Entry)

## Support

If you need to:
- **Recover from corruption:** Use most recent backup
- **Share database:** Copy backup file to another computer
- **Archive work:** Keep backup file in safe location
- **Compare states:** Open two backups in SQLite viewer

## Summary

The backup system is **already implemented** and ready to use:
- **Backup location:** `File organizer/database_backups/`
- **Access:** Backup tab in ribbon
- **Features:** Manual backup, automatic backup, restore, view/manage
- **Safety:** Always creates backup before restore

**You're already protected!** Just use the Backup tab when needed.
