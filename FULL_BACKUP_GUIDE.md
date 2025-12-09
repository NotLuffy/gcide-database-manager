# Full Backup Feature Guide

## Overview

The **Full Backup** feature creates a complete snapshot of your entire G-Code repository, including both the database and all actual .nc files. You can save this backup anywhere you choose.

## What's Included

### Full Backup (📦 Full Backup)
Includes:
- ✅ **Database file** (gcode_database.db) - all metadata, dimensions, validation
- ✅ **All .nc files** - actual G-code files from repository
- ✅ **Folder structure** - maintains organization
- ✅ **Backup info file** - details about backup contents

### Database Backup (💾 Backup DB)
Includes:
- ✅ **Database file only** - metadata and file references
- ❌ No actual .nc files

## How to Use Full Backup

### Creating a Full Backup

1. **Open application** → **Backup tab** in ribbon
2. Click **📦 Full Backup** (green button)
3. **Choose save location** (desktop, external drive, cloud folder, etc.)
4. Wait for backup to complete (progress bar shows status)
5. **Backup complete!** You'll see:
   - Location of backup
   - Number of files copied
   - Any missing files

### Backup Structure

When you create a full backup, it creates a folder like:
```
GCode_Full_Backup_2025-12-05_14-30-45/
├── gcode_database.db          (database file)
├── repository/                 (all .nc files)
│   ├── 6.0/
│   │   ├── o60001.nc
│   │   ├── o60002.nc
│   │   └── ...
│   ├── 6.25/
│   │   ├── o62500.nc
│   │   └── ...
│   ├── 13.0/
│   │   └── ...
│   └── ...
└── BACKUP_INFO.txt            (backup details)
```

## When to Use Full Backup

### Use Full Backup When:
✅ **Archiving complete work** - Save entire project state
✅ **Transferring to another computer** - Move everything at once
✅ **Before major system changes** - OS upgrade, disk replacement
✅ **Creating offsite backup** - External drive, cloud storage
✅ **Sharing repository** - Send complete copy to someone
✅ **End of project milestone** - Preserve completed work

### Use Database Backup When:
✅ **Quick safety backup** - Before testing changes
✅ **Testing parser updates** - Don't need files, just metadata
✅ **Daily snapshots** - Faster, smaller backups
✅ **Tracking database changes** - Version control for metadata

## Backup Locations

### Recommended Locations

**Local Backups:**
- Desktop - Quick access, easy to find
- Documents folder - Organized storage
- External drive - Safe from computer failures

**Offsite Backups:**
- Cloud storage (Google Drive, OneDrive, Dropbox)
- Network drive (NAS)
- USB drive stored elsewhere

**Example Workflow:**
```
Daily: Database backup (fast, local)
Weekly: Full backup to external drive
Monthly: Full backup to cloud storage
```

## Restoring from Full Backup

### Option 1: Manual Restore (Recommended)

1. **Locate your backup folder** (e.g., `GCode_Full_Backup_2025-12-05_14-30-45`)
2. **Close the application**
3. **Copy database file:**
   - From: `backup_folder/gcode_database.db`
   - To: `File organizer/gcode_database.db` (replace existing)
4. **Copy repository files:**
   - From: `backup_folder/repository/*`
   - To: Your repository location
5. **Restart application**

### Option 2: Using Restore Button

1. Click **📂 Restore Backup**
2. Select `gcode_database.db` from backup folder
3. **Manually copy repository files** from `backup_folder/repository/`
4. Restart application

**Note:** The Restore button only restores the database. You must manually copy the .nc files from the backup.

### If Repository Location Changed

If you restore to a different computer or location:

1. Restore database and files as above
2. Use **🔧 Repair Paths** feature (Files tab)
3. Point to new repository location
4. Paths will be updated automatically

## Progress Tracking

During full backup, you'll see:
- **Current operation** - What's being backed up
- **Progress bar** - Visual progress indicator
- **File counts** - Copied, missing, total
- **Status updates** every 10 files

## Backup Info File

Each full backup includes `BACKUP_INFO.txt`:
```
GCode Database Full Backup
==================================================

Created: 2025-12-05 14:30:45
Database records: 8,214
Files copied: 8,150
Files missing: 64

Contents:
  - gcode_database.db (database file)
  - repository/ (all .nc files)

To Restore:
  1. Copy gcode_database.db to your program folder
  2. Copy repository/ contents to your repository location
  3. Update file paths in database if repository location changed
```

This tells you exactly what's in the backup.

## Missing Files

If some files are missing during backup:
- **Files copied:** Successfully backed up
- **Files missing:** Not found at time of backup (may have been deleted)

Missing files are tracked but won't cause backup to fail. The backup still saves all files that exist.

## Storage Requirements

### Database Only
- Size: ~5-50 MB
- Speed: 1-2 seconds
- Storage: Minimal

### Full Backup
- Size: Varies (depends on number of .nc files)
  - Small repository (1,000 files): ~500 MB
  - Medium repository (5,000 files): ~2 GB
  - Large repository (10,000 files): ~4 GB
- Speed: 1-5 minutes depending on size
- Storage: Plan accordingly for backup location

## Best Practices

### DO:
✅ Keep multiple full backups at different milestones
✅ Store backups in different physical locations
✅ Label backups clearly (rename folder if needed)
✅ Test restore occasionally
✅ Keep backups on external media
✅ Verify backup completed successfully

### DON'T:
❌ Store only in one location (risk of loss)
❌ Delete old backups immediately (keep a few)
❌ Ignore "files missing" warnings
❌ Modify backup files manually
❌ Store backups in repository folder (defeats purpose)

## Comparison: Full vs Database Backup

| Feature | Full Backup | Database Backup |
|---------|-------------|-----------------|
| Database | ✅ | ✅ |
| .nc Files | ✅ | ❌ |
| Choose location | ✅ | ❌ (auto) |
| Size | Large (GB) | Small (MB) |
| Speed | Slower (minutes) | Fast (seconds) |
| Portability | Complete | Needs files |
| Best for | Archiving, Transfer | Quick saves |

## Troubleshooting

### "Failed to create full backup"
- Check you have write permission to selected location
- Ensure enough disk space
- Try different backup location

### "Files missing: XX"
- Some files in database don't exist on disk
- May have been deleted or moved
- Backup still succeeds for files that exist

### Backup taking too long
- Normal for large repositories (thousands of files)
- Progress bar shows it's working
- Don't close window while backing up

### Can't find backup
- Check the location you selected
- Look for folder starting with `GCode_Full_Backup_`
- Check desktop if unsure where you saved it

## Advanced: Automated Backups

You can create automated full backups using:
- Windows Task Scheduler (script the backup process)
- Cloud sync software (auto-sync backup folder)
- Batch scripts (scheduled full backups)

## Summary

**Full Backup = Complete Copy**
- Database + All files
- Save anywhere you choose
- Perfect for archiving and transferring

**Database Backup = Quick Save**
- Database only
- Auto-saved to program folder
- Perfect for daily safety nets

Use **📦 Full Backup** when you need everything!
