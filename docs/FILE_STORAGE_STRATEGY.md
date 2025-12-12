# File Storage Strategy - Analysis & Recommendation

## Current State

Your system currently uses **external file references**:
- Database stores `file_path` pointing to original location
- When dragging & dropping: files are copied to `target_folder`
- When scanning folder: files stay in original location

## The Problem

**Relying on external file paths is risky:**

❌ **Cons of Current Approach:**
1. Files can be moved/deleted externally
2. Broken references if folder renamed
3. Network path issues
4. Hard to backup (files scattered)
5. Version history breaks if file moved
6. Can't track file changes reliably
7. Not portable (can't move database to another computer)

## 🎯 Recommended Solution: Managed Repository

Create a **managed file repository** inside your program folder:

```
Bronson Generators/
└── File organizer/
    ├── gcode_database.db
    ├── repository/              # ← NEW: Managed storage
    │   ├── o57000.nc
    │   ├── o57001.nc
    │   ├── o62500.gcode
    │   └── ...
    ├── versions/                # ← NEW: Version storage
    │   ├── o57000/
    │   │   ├── v1.0.nc
    │   │   ├── v2.0.nc
    │   │   └── v3.0.nc
    │   └── o62500/
    │       ├── v1.0.gcode
    │       └── v2.0.gcode
    └── backups/                 # ← NEW: Database backups
        ├── gcode_database_2025-11-25.db
        └── gcode_database_2025-11-24.db
```

## Benefits of Managed Repository

✅ **Reliability**
- Files never disappear
- Always in known location
- No broken references

✅ **Version History Works**
- Can store versions as separate files
- Or keep full content in database
- Hybrid approach possible

✅ **Portability**
- Copy entire folder = full backup
- Move to another computer easily
- Share with team members

✅ **Performance**
- Faster access (local files)
- Can optimize file organization
- Easy to index/search

✅ **Backup & Recovery**
- One folder to backup
- Everything in one place
- Easy disaster recovery

✅ **Change Detection**
- Can detect external edits
- Track file modification times
- Trigger auto-versioning

## Implementation Options

### Option 1: Repository + Version Files (Recommended)

**Structure:**
```
repository/       # Current working files
  o57000.nc      # Latest version
  o62500.gcode   # Latest version

versions/         # Historical versions
  o57000/
    v1.0.nc     # Old versions as files
    v2.0.nc
  o62500/
    v1.0.gcode
```

**Pros:**
- Easy to access any version (just open file)
- Can edit old versions directly
- Simple backup (copy folder)
- File system is the backup

**Cons:**
- More disk space (duplicate files)
- Many files to manage

**Best for:** Your use case (manufacturing, need file access)

---

### Option 2: Repository + Database BLOB Storage

**Structure:**
```
repository/       # Current working files only
  o57000.nc
  o62500.gcode

Database:
  program_versions.file_content (BLOB)  # Versions in DB
```

**Pros:**
- Less disk space
- Versions in database (atomic)
- Easier to query

**Cons:**
- Can't directly edit old versions
- Need to extract to use
- Database file gets large

**Best for:** Web applications, cloud storage

---

### Option 3: Hybrid (Best of Both Worlds)

**Structure:**
```
repository/       # Current files
  o57000.nc

versions/         # Recent versions as files (last 5)
  o57000/
    v2.0.nc
    v3.0.nc

Database:
  program_versions.file_content (BLOB)  # All versions
```

**Pros:**
- Recent versions easily accessible
- Old versions compressed in database
- Balance space vs accessibility

**Cons:**
- More complex to implement
- Need retention policy

---

## 🏆 My Recommendation: Option 1

For your manufacturing use case, I recommend **Option 1**:

### Why Option 1?

1. **Manufacturing needs file access**
   - CNC machines need actual files
   - Operators need to open files directly
   - Easy to send to machine

2. **Disk space is cheap**
   - G-code files are small (5-50KB)
   - 1000 programs × 10 versions × 20KB = 200MB
   - Negligible storage cost

3. **Simplicity**
   - Easy to understand
   - Easy to backup
   - Easy to recover

4. **Version integrity**
   - Each version is a real file
   - Can diff with external tools
   - Can open in any editor

## Implementation Plan

### Step 1: Create Repository Structure

```python
def init_repository(self):
    """Initialize managed file repository"""
    base_path = os.path.dirname(os.path.abspath(__file__))

    self.repository_path = os.path.join(base_path, 'repository')
    self.versions_path = os.path.join(base_path, 'versions')
    self.backups_path = os.path.join(base_path, 'backups')

    # Create directories
    os.makedirs(self.repository_path, exist_ok=True)
    os.makedirs(self.versions_path, exist_ok=True)
    os.makedirs(self.backups_path, exist_ok=True)
```

### Step 2: Import Files to Repository

```python
def import_to_repository(self, source_file):
    """Import a file into the managed repository"""
    filename = os.path.basename(source_file)
    dest_path = os.path.join(self.repository_path, filename)

    # Copy file
    shutil.copy2(source_file, dest_path)

    # Return new path
    return dest_path
```

### Step 3: Store Versions as Files

```python
def create_version_file(self, program_number, version_number):
    """Save version as a physical file"""
    # Create version folder
    version_folder = os.path.join(self.versions_path, program_number)
    os.makedirs(version_folder, exist_ok=True)

    # Get current file
    current_path = self.get_program_file_path(program_number)

    # Copy to version folder
    version_filename = f"{version_number}.nc"
    version_path = os.path.join(version_folder, version_filename)

    shutil.copy2(current_path, version_path)

    return version_path
```

### Step 4: Migration Strategy

For existing databases:

```python
def migrate_to_repository(self):
    """Migrate existing files to managed repository"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT program_number, file_path FROM programs WHERE file_path IS NOT NULL")

    migrated = 0
    errors = 0

    for prog_num, old_path in cursor.fetchall():
        if os.path.exists(old_path):
            try:
                # Copy to repository
                new_path = self.import_to_repository(old_path)

                # Update database
                cursor.execute("UPDATE programs SET file_path = ? WHERE program_number = ?",
                             (new_path, prog_num))

                migrated += 1
            except Exception as e:
                print(f"Error migrating {prog_num}: {e}")
                errors += 1

    conn.commit()
    conn.close()

    return migrated, errors
```

## Database Schema Changes

Add to `program_versions` table:

```sql
ALTER TABLE program_versions ADD COLUMN version_file_path TEXT;
```

This stores the path to the version file:
- `repository/o57000.nc` (current)
- `versions/o57000/v2.0.nc` (old version)

## Configuration

Add to config.json:

```json
{
  "repository_path": "repository",
  "versions_path": "versions",
  "backups_path": "backups",
  "version_retention_count": 10,  // Keep last 10 versions as files
  "auto_backup_enabled": true,
  "backup_frequency_days": 7
}
```

## File Organization Strategies

### Strategy A: Flat Structure (Simple)
```
repository/
  o57000.nc
  o57001.nc
  o62500.gcode
  ... (all 871 files)
```

**Pros:** Simple, fast
**Cons:** Many files in one folder

---

### Strategy B: Categorized by Type (Organized)
```
repository/
  hub_centric/
    o57000.nc
    o58000.nc
  standard/
    o62500.gcode
  steel_ring/
    o75000.nc
```

**Pros:** Organized, easy to browse
**Cons:** Need to track category changes

---

### Strategy C: Hash-based (Scalable)
```
repository/
  o5/
    o57000.nc
    o58000.nc
  o6/
    o62500.gcode
  o7/
    o75000.nc
```

**Pros:** Scales to millions of files
**Cons:** Less human-readable

---

**Recommendation:** Start with **Strategy A** (flat), migrate to **Strategy B** (categorized) later if needed.

## Backup Strategy

### Automatic Backups

```python
def auto_backup(self):
    """Create automatic backup of database and repository"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # Backup database
    db_backup = os.path.join(self.backups_path, f"database_{timestamp}.db")
    shutil.copy2(self.db_path, db_backup)

    # Backup repository (zip it)
    repo_backup = os.path.join(self.backups_path, f"repository_{timestamp}.zip")
    shutil.make_archive(repo_backup.replace('.zip', ''), 'zip', self.repository_path)

    # Cleanup old backups (keep last 10)
    self.cleanup_old_backups(keep=10)
```

## Change Detection

With managed repository, you can detect external changes:

```python
def detect_file_changes(self):
    """Detect if repository files were modified externally"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT program_number, file_path, last_modified FROM programs")

    changes = []
    for prog_num, file_path, db_modified in cursor.fetchall():
        if os.path.exists(file_path):
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

            if file_modified > db_modified:
                changes.append({
                    'program': prog_num,
                    'db_time': db_modified,
                    'file_time': file_modified
                })

    conn.close()
    return changes
```

## Summary

### ✅ Recommended Approach

1. **Use managed repository** (`repository/` folder)
2. **Store versions as files** (`versions/program_number/v1.0.nc`)
3. **Keep database lean** (metadata only, not file content)
4. **Flat structure initially** (all files in `repository/`)
5. **Automatic backups** (weekly zip of everything)

### 📋 Implementation Checklist

- [ ] Create `repository/` folder structure
- [ ] Create `versions/` folder structure
- [ ] Create `backups/` folder structure
- [ ] Add `version_file_path` column to `program_versions`
- [ ] Implement `import_to_repository()`
- [ ] Implement `create_version_file()`
- [ ] Implement `migrate_to_repository()`
- [ ] Update drag-drop to use repository
- [ ] Update scan folder to copy to repository
- [ ] Implement auto-backup
- [ ] Implement change detection

### 🚀 Migration Path

**For existing users:**
1. Run migration tool to copy all files to repository
2. Update all `file_path` references
3. Keep original files as backup (don't delete)
4. Verify all programs still accessible
5. Remove old file references after verification

**For new users:**
- Everything automatically goes to repository
- No migration needed

---

**Ready to implement this?** I can start building the repository system right now!
