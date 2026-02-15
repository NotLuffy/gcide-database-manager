# Backup System - Complete Guide

## Overview

Your G-code Database Manager now includes **complete backup protection** for all your files, including originals, edits, and version history.

---

## Folder Structure

### Main Folders

```
File organizer/
├── repository/              ← Current active files
├── revised_repository/      ← Edited/revised files
├── versions/                ← Version history (originals)
│   ├── o13002/
│   │   ├── v1.0.nc         ← Original version
│   │   ├── v2.0.nc         ← After first edit
│   │   └── v3.0.nc         ← After second edit
│   ├── o61045/
│   │   └── v1.0.nc
│   └── ...
├── backups/                 ← Database backups
├── deleted/                 ← Deleted files archive
└── gcode_database.db        ← Main database
```

---

## How Version History Works

### When You Edit a File

1. **Before editing** → Original is saved to `versions/o13002/v1.0.nc`
2. **You edit** → File is modified in place
3. **Save new version** → Copy saved to `versions/o13002/v2.0.nc`
4. **Repository file** → Always contains current/latest version

### Example Timeline

| Action | Repository | Versions Folder | Revised Repository |
|--------|-----------|----------------|-------------------|
| Initial import | `o13002.nc` (v1) | - | - |
| First edit | `o13002.nc` (v2) | `v1.0.nc` | - |
| Second edit | `o13002.nc` (v3) | `v1.0.nc`, `v2.0.nc` | - |
| Major revision | `o13002.nc` (v3) | `v1.0.nc`, `v2.0.nc` | `o13002.nc` (copy) |

### Why This Matters

✅ **You never lose originals** - First version is always in `versions/`
✅ **Complete history** - Every edit is tracked
✅ **Easy rollback** - Can restore any previous version
✅ **Safe to edit** - Original is backed up automatically

---

## Backup Operations

### 1. Full Backup (Recommended)

**What it backs up:**
- ✅ Database (all records and metadata)
- ✅ Repository folder (current files)
- ✅ **Versions folder (ALL version history)** ← NEW!
- ✅ **Revised repository (edited files)** ← NEW!

**How to use:**
1. File → Backup/Restore → Create Full Backup
2. Choose destination folder
3. Wait for backup to complete

**Result:**
```
GCode_Full_Backup_2026-02-03_14-30-00/
├── gcode_database.db
├── repository/
│   ├── o13002.nc
│   ├── o61045.nc
│   └── ...
├── versions/                    ← Complete history!
│   ├── o13002/
│   │   ├── v1.0.nc
│   │   └── v2.0.nc
│   └── ...
├── revised_repository/          ← All edits!
│   ├── o13002.nc
│   └── ...
└── BACKUP_INFO.txt
```

---

### 2. Organize by OD (Export)

**What it exports:**
- ✅ All programs organized by outer diameter
- ✅ **Versions folder (complete history)** ← NEW!
- ✅ **Revised repository (edited files)** ← NEW!

**How to use:**
1. File → Export → Organize Files by OD
2. Choose destination folder
3. Wait for export to complete

**Result:**
```
Organized_Export/
├── 5.75 Round/
│   ├── o50000.nc
│   ├── o50001.nc
│   └── ...
├── 6.00 Round/
│   ├── o61045.nc
│   └── ...
├── 13.00 Round/
│   ├── o13002.nc
│   └── ...
├── versions/                    ← Complete history!
│   ├── o13002/
│   │   └── v1.0.nc
│   └── ...
└── revised_repository/          ← All edits!
    ├── o13002.nc
    └── ...
```

---

## What's New (February 2026)

### ✅ Changes Made

#### Full Backup Now Includes:
1. **Version History** - All old versions are backed up
   - Previously: ❌ Not included
   - Now: ✅ Complete `versions/` folder backed up

2. **Revised Repository** - All edited files are backed up
   - Previously: ❌ Not included
   - Now: ✅ Complete `revised_repository/` folder backed up

3. **Better Info File** - Shows exactly what was backed up
   - File counts for all folders
   - Clear restore instructions
   - Total files backed up

#### Organize by OD Now Includes:
1. **Version History** - All old versions are exported
   - Previously: ❌ Only current files
   - Now: ✅ Includes `versions/` folder

2. **Revised Repository** - All edited files are exported
   - Previously: ❌ Not included
   - Now: ✅ Includes `revised_repository/` folder

3. **Better Progress Display** - Shows what's being copied
   - Current repository files
   - Version history count
   - Revised repository count
   - Total files exported

---

## Why This Is Important

### Before (Old System)
```
Full Backup:
├── Database ✓
└── Current files ✓

Missing:
├── Version history ✗ (originals lost!)
└── Revised files ✗ (edits lost!)
```

**Problem:** If you restored a backup, you'd lose:
- ❌ All original versions
- ❌ All edit history
- ❌ All revised files

### After (New System)
```
Full Backup:
├── Database ✓
├── Current files ✓
├── Version history ✓ (all originals!)
└── Revised files ✓ (all edits!)
```

**Solution:** When you restore, you get:
- ✅ Everything
- ✅ Complete history
- ✅ No data loss

---

## Usage Examples

### Example 1: Complete Backup Before Major Changes

**Scenario:** You're about to make major edits to 50 programs.

**Steps:**
1. File → Backup/Restore → Create Full Backup
2. Choose backup location (e.g., external drive)
3. Make your edits
4. If something goes wrong, restore from backup

**What you get:**
- Full database state
- All current files
- **All original versions** (can compare before/after)
- **All previous edits** (complete history)

---

### Example 2: Export for External Use

**Scenario:** Customer needs all files organized by size, including history.

**Steps:**
1. File → Export → Organize Files by OD
2. Choose destination folder
3. Send to customer

**What customer gets:**
- Files organized by OD (easy to find)
- **Version history** (can see evolution of programs)
- **Revised files** (can see all edits made)
- Complete package with context

---

### Example 3: Restore After System Failure

**Scenario:** Computer crashed, need to restore everything.

**Steps:**
1. Install fresh copy of G-code Database Manager
2. Copy backup folder contents:
   - `gcode_database.db` → Program folder
   - `repository/` → Program folder
   - `versions/` → Program folder ✨
   - `revised_repository/` → Program folder ✨
3. Launch application
4. Everything restored with complete history!

---

## Backup Best Practices

### 1. Regular Backups
- **Daily:** If actively editing files
- **Weekly:** During normal operation
- **Before major changes:** Always!

### 2. Backup Locations
- ✅ External drive (USB, external HDD)
- ✅ Network drive
- ✅ Cloud storage (Google Drive, Dropbox)
- ❌ Same drive as program (not safe)

### 3. What to Back Up

**Minimum (Quick):**
- Database only → File → Backup/Restore → Database Backup

**Recommended (Complete):**
- Everything → File → Backup/Restore → Create Full Backup

**Best Practice:**
1. Weekly full backup to external drive
2. Daily database backup to network drive
3. Monthly full backup to cloud storage

---

## Verification

### After Backup, Check:

1. **Backup folder exists** and has timestamp
2. **BACKUP_INFO.txt** shows correct counts
3. **File sizes** look reasonable:
   - Database: ~50-200 MB
   - Repository: Varies by file count
   - Versions: Can be large (multiple copies)
   - Revised: Small (only edited files)

### Expected File Counts

Example for 500 programs:
```
Repository files: 500 (current versions)
Version history: 800 files (500 originals + 300 edits)
Revised repository: 50 files (programs that were edited)
Total: 1,350 files
```

---

## Restore Instructions

### From Full Backup

1. **Locate backup folder:**
   ```
   GCode_Full_Backup_2026-02-03_14-30-00/
   ```

2. **Close application** if running

3. **Copy files:**
   ```
   Copy gcode_database.db → l:\My Drive\Home\File organizer\
   Copy repository\* → l:\My Drive\Home\File organizer\repository\
   Copy versions\* → l:\My Drive\Home\File organizer\versions\
   Copy revised_repository\* → l:\My Drive\Home\File organizer\revised_repository\
   ```

4. **Launch application** - Everything restored!

---

## Troubleshooting

### Q: Backup takes a long time
**A:** Normal if you have many versions. The versions folder can be large.

### Q: Can I delete old version files?
**A:** Yes, but consider:
- Keep v1.0 (original) always
- Keep recent versions (last 3-5)
- Archive old versions to external drive

### Q: How much space do I need?
**A:** Rough estimate:
- Current files: X MB
- Versions: 2-3× current files (if edited multiple times)
- Backups: 3-4× current files
- **Total: 6-10× your current repository size**

### Q: Backup says "files missing"
**A:** Some database records point to deleted files. Normal. Check:
- Most files copied successfully?
- Critical programs are there?
- If yes, you're fine!

---

## Summary

### ✅ What You Now Have

1. **Complete Protection**
   - Every file backed up
   - Every version saved
   - Every edit preserved

2. **Easy Recovery**
   - One backup has everything
   - Simple restore process
   - No data loss

3. **Better Exports**
   - Organize by OD includes history
   - Customers get complete context
   - Can trace evolution of programs

### 🎯 Bottom Line

**Your backup system is now bulletproof!**

When you do a full backup or organize by OD export, you get:
- ✅ Current files
- ✅ **ALL originals (versions/)**
- ✅ **ALL edits (revised_repository/)**
- ✅ Complete database
- ✅ Peace of mind

---

**Next Steps:**
1. Create a full backup now to test the new system
2. Verify the backup includes versions/ and revised_repository/
3. Set up a regular backup schedule
4. Store backups in multiple locations

---

**Questions?** Check the BACKUP_INFO.txt file in any backup for details about what was included.
