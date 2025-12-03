# Program Number Registry - When Is It Updated?

## ⚠️ Current Status: NOT ALWAYS UPDATED

The registry is **only updated in specific operations**, not all file changes. Here's the complete breakdown:

---

## ✅ Operations That DO Update Registry

### 1. **populate_program_registry()** - Initial Population
**When:** Manually run via `populate_registry.py` script
**What it does:**
- Generates all 98,001 program numbers
- Marks existing programs as IN_USE
- Marks available numbers as AVAILABLE

**Code:** [gcode_database_manager.py:1179-1271](gcode_database_manager.py#L1179-L1271)

```python
cursor.execute("""
    INSERT INTO program_number_registry
    (program_number, round_size, range_start, range_end, status, file_path, last_checked)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (...))
```

### 2. **rename_to_correct_range()** - Phase 3 Rename
**When:** User executes batch rename of out-of-range programs
**What it does:**
- Marks OLD number as AVAILABLE
- Marks NEW number as IN_USE

**Code:** [gcode_database_manager.py:1600-1614](gcode_database_manager.py#L1600-L1614)

```python
# Mark old number as available
UPDATE program_number_registry
SET status = 'AVAILABLE', file_path = NULL
WHERE program_number = 'o62000'

# Mark new number as in use
UPDATE program_number_registry
SET status = 'IN_USE', file_path = '/path/to/file.nc'
WHERE program_number = 'o62500'
```

---

## ❌ Operations That DO NOT Update Registry

### 1. **scan_folder()** - Scanning External Files
**When:** User scans a folder to import files
**Current behavior:**
- Adds programs to database
- Does NOT update registry

**Impact:**
- Registry shows numbers as AVAILABLE even though they're now IN_USE
- Not critical because registry mainly used by rename system

**Code:** [gcode_database_manager.py:3022-3500](gcode_database_manager.py#L3022-L3500)

```python
# Inserts into programs table but NOT registry
cursor.execute('''
    INSERT INTO programs VALUES (?, ?, ?, ...)
''', (...))
# ← No registry update here!
```

### 2. **import_to_repository()** - Moving Files to Repository
**When:** User imports external file to repository
**Current behavior:**
- Copies file to repository folder
- Updates database (is_managed = 1)
- Does NOT update registry

**Code:** [gcode_database_manager.py:548-600](gcode_database_manager.py#L548-L600)

```python
# Copies file but doesn't update registry
shutil.copy2(source_file, dest_path)
# ← No registry update!
```

### 3. **delete_from_repository()** - Deleting Programs
**When:** User deletes a program from repository
**Current behavior:**
- Deletes file from disk
- Removes from database OR marks is_managed = 0
- Does NOT update registry

**Code:** [gcode_database_manager.py:8747-8830](gcode_database_manager.py#L8747-L8830)

```python
# Deletes file and database entry
os.remove(file_path)
cursor.execute("DELETE FROM programs WHERE program_number = ?", (...))
# ← No registry update! Number still shows as IN_USE
```

### 4. **Manual Program Number Edits**
**When:** User manually changes program number in database
**Current behavior:**
- Updates programs table
- Does NOT update registry

### 5. **Duplicate Deletion/Cleanup**
**When:** User deletes content duplicates
**Current behavior:**
- Deletes duplicate files
- Removes from database
- Does NOT update registry

---

## 📊 Impact Analysis

### Current State After Typical Workflow

```
1. Initial state: Registry populated
   - 11,443 IN_USE
   - 86,558 AVAILABLE

2. User scans 100 new files
   - programs table: +100 entries
   - registry: NO CHANGE (still shows those numbers as AVAILABLE)

3. User deletes 50 programs
   - programs table: -50 entries
   - registry: NO CHANGE (still shows those numbers as IN_USE)

4. User renames 20 programs (Phase 3)
   - programs table: program numbers updated
   - registry: UPDATED (old marked AVAILABLE, new marked IN_USE)

Result: Registry is OUT OF SYNC
```

### How Out of Sync Can It Get?

**Worst Case Scenario:**
- Scan 1,000 new files → Registry doesn't know
- Delete 500 old files → Registry doesn't know
- Registry accuracy: Could be 15-20% off

**Actual Impact:**
- **Low risk** for normal operations
- Registry mainly used by `find_next_available_number()`
- That function still works (checks if number exists in database)
- Just might suggest a number that's actually in use

---

## 🔧 Solutions

### Option 1: Re-sync Periodically (Current)

**How:**
```bash
python populate_registry.py
```

**When to run:**
- After major scan batches
- After bulk deletions
- Before running batch rename
- Once a week if actively scanning

**Pros:**
- Simple
- No code changes needed
- Can be scheduled

**Cons:**
- Manual process
- Registry out of sync between runs

### Option 2: Auto-Update During All Operations (Recommended)

**Add registry updates to:**

**A) scan_folder() - After INSERT/UPDATE**
```python
# After adding program to database
cursor.execute("""
    INSERT OR REPLACE INTO program_number_registry
    (program_number, round_size, range_start, range_end, status, file_path, last_checked)
    VALUES (?, ?, ?, ?, 'IN_USE', ?, ?)
""", (record.program_number, round_size, range_start, range_end, file_path, datetime.now().isoformat()))
```

**B) delete_from_repository() - After DELETE**
```python
# After deleting from database
cursor.execute("""
    UPDATE program_number_registry
    SET status = 'AVAILABLE',
        file_path = NULL,
        last_checked = ?
    WHERE program_number = ?
""", (datetime.now().isoformat(), program_number))
```

**C) import_to_repository() - After import**
```python
# After copying file
cursor.execute("""
    UPDATE program_number_registry
    SET status = 'IN_USE',
        file_path = ?,
        last_checked = ?
    WHERE program_number = ?
""", (dest_path, datetime.now().isoformat(), program_number))
```

**Pros:**
- Always accurate
- No manual re-sync needed
- Better data integrity

**Cons:**
- Slight performance overhead
- Need to modify multiple functions

### Option 3: Lazy Update (Smart Compromise)

**Only update registry when accessed:**

```python
def find_next_available_number(round_size, preferred_number=None):
    # Before querying registry, quick sync check
    self._sync_registry_if_needed()

    # Then find available number
    ...

def _sync_registry_if_needed(self):
    # Check if registry is stale (last update > 24 hours)
    # Or if significant database changes detected
    # Then re-sync only affected ranges
```

**Pros:**
- Automatic but not constant overhead
- Good balance of accuracy vs performance

**Cons:**
- More complex logic
- Still brief periods of inaccuracy

---

## 💡 Recommendation

### Immediate (No Code Changes)

**Use Option 1: Manual Re-sync**

Add to your workflow:
```
1. After scanning large batches: run populate_registry.py
2. Before batch rename: run populate_registry.py
3. Weekly maintenance: run populate_registry.py
```

Create a batch file for convenience:
```batch
@echo off
echo Syncing Program Number Registry...
python populate_registry.py
pause
```

### Future Enhancement (Option 2)

Modify these functions to auto-update registry:
1. `scan_folder()` - lines 3370-3384 (after INSERT)
2. `delete_from_repository()` - lines 8800-8804 (after DELETE)
3. `import_to_repository()` - line 590 (after copy)
4. Any other file operations

**Estimated effort:** 30-60 minutes
**Benefit:** Always accurate registry

---

## 🎯 Current Best Practice

### Workflow with Manual Sync

```bash
# 1. Scan all your folders
python gcode_database_manager.py
# → Scan folders in UI

# 2. Re-sync registry
python populate_registry.py
# → Takes 0.4 seconds

# 3. Run round size detection (if needed)
python run_batch_detection.py

# 4. Preview renames
# → Use UI: Resolve Out-of-Range (Batch Rename)
# → Generate Preview

# 5. Execute renames
# → Registry automatically updated during rename

# 6. After more scanning, repeat step 2
```

### When Registry Accuracy Matters Most

**Critical:** Before using `find_next_available_number()`
- Re-sync registry first to ensure accurate availability

**Less Critical:** For statistics viewing
- Slightly out-of-date stats are acceptable

**Not Critical:** For rename operations
- Rename function updates registry automatically

---

## 📋 Summary Table

| Operation | Updates Registry? | When to Re-sync |
|-----------|-------------------|-----------------|
| Initial populate | ✅ Yes | N/A |
| Batch rename (Phase 3) | ✅ Yes | N/A |
| Scan folder | ❌ No | After scanning |
| Import to repository | ❌ No | After importing |
| Delete from repository | ❌ No | After deleting |
| Manual DB edits | ❌ No | After edits |
| Duplicate cleanup | ❌ No | After cleanup |

### Quick Answer to Your Question:

**"Do we update our SQLite list of numbers anytime we make a change to a file?"**

**Answer: NO** - Currently only during:
1. Initial registry population
2. Batch rename operations (Phase 3)

**Everything else requires manual re-sync** by running `populate_registry.py`

---

## 🔍 How to Check Registry Accuracy

Run this SQL query:
```sql
-- Programs in DB but registry shows AVAILABLE
SELECT p.program_number, r.status
FROM programs p
LEFT JOIN program_number_registry r ON p.program_number = r.program_number
WHERE r.status = 'AVAILABLE' OR r.program_number IS NULL;

-- Programs deleted but registry shows IN_USE
SELECT r.program_number, r.status
FROM program_number_registry r
LEFT JOIN programs p ON r.program_number = p.program_number
WHERE r.status = 'IN_USE' AND p.program_number IS NULL;
```

If these queries return results, registry is out of sync.

---

*Analysis completed: 2025-12-02*
*Status: Registry requires manual sync for most operations*
*Recommendation: Run populate_registry.py after scan batches*
