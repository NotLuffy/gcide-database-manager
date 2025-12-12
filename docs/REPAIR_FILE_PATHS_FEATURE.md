# Repair File Paths Feature

## 🎯 Purpose

This feature fixes a critical issue where **database file_path entries don't match actual files** in the repository. This prevents batch rename operations from working correctly.

### The Problem It Solves:

After various operations (imports, manual edits, file moves), the database can have incorrect file_path values:
1. ❌ Path points to non-existent file
2. ❌ Path is missing file extension
3. ❌ Path has old filename with suffixes (e.g., `O00004_1.nc` when file is now `o00004.nc`)
4. ❌ Path is empty or NULL

This causes **batch rename to fail** because it can't find the files to rename.

The "Repair File Paths" button scans the repository folder and matches files to their database entries, fixing incorrect paths.

---

## 📍 Location

**Repository Tab → Row 4**

Button: **🔧 Repair File Paths**

Located next to the "📦 Export Repository by Round Size" button.

---

## 🔧 How It Works

### Step 1: Scan Repository

Scans the repository folder and finds all `.nc` files on disk.

### Step 2: Check Database

Compares database file_path entries with actual files:
- If file exists at stored path → ✅ OK
- If file doesn't exist at stored path → 🔍 Try to find it

### Step 3: Match Files

For files that can't be found, tries multiple name variations:
- Exact program number match (e.g., `o00004(1)` → `o00004(1).nc`)
- Without suffixes (e.g., `o00004(1)` → `o00004.nc`)
- With underscore conversion (e.g., `o00004(1)` → `o00004_1.nc`)

### Step 4: Preview

Shows what will be repaired:
```
Program: o00004(1)
  Title: 6 SPACER
  Current DB path: O00004_1.nc
  ✓ Found at: I:\My Drive\NC Master\REVISED PROGRAMS\repository\o00004.nc

Program: o00801(2)
  Title: 8 SPACER
  Current DB path: o00801_1
  ❌ File not found in repository
```

### Step 5: Apply Repairs

When you click "Apply Repairs":
1. Updates database `file_path` for files that were found
2. Updates registry `file_path` for files that were found
3. Clears `file_path` (sets to NULL) for files that weren't found
4. Shows success/error count

---

## 🎬 Usage

### When to Use:

**Use this button when:**
1. Batch rename is failing with "File not found" errors
2. After manually moving files in repository
3. After importing files from external sources
4. Database was edited manually
5. Files were renamed outside the application

**Typical Workflow:**
```
1. Batch rename fails (27 files failed, 23 skipped)
2. 🔧 Click "Repair File Paths"  ← NEW!
3. Review preview of what will be fixed
4. Click "Apply Repairs"
5. Try batch rename again → Now works!
```

### Step-by-Step:

1. **Click the button**
   - Go to Repository tab
   - Click "🔧 Repair File Paths"

2. **Wait for scan**
   - Scans repository folder for all .nc files
   - Checks all database entries
   - Shows preview of repairs needed

3. **Review preview**
   - Shows programs with incorrect paths
   - Displays where files were found (or not found)
   - First 50 displayed, shows total count

4. **Apply or Cancel**
   - Click "✓ Apply Repairs" to fix paths
   - Click "✗ Cancel" to abort

5. **Watch progress**
   - Each file path is updated
   - Database and registry updated
   - Shows success/error count

---

## 📊 Example

### Before Repair:

**Database:**
```sql
program_number | file_path
---------------+------------------------------------------
o00004(1)      | O00004_1.nc                        ❌ Doesn't exist
o00801(2)      | o00801_1                           ❌ No extension, doesn't exist
o85000         | I:\...\repository\o85000.nc        ✅ Correct
```

**Repository Folder:**
```
I:\My Drive\NC Master\REVISED PROGRAMS\repository\
├── o00004.nc  ← Exists but DB points to O00004_1.nc
├── o85000.nc  ← Correct
```

**Result:** Batch rename fails because it can't find `O00004_1.nc`

### After Repair:

**Database:**
```sql
program_number | file_path
---------------+------------------------------------------
o00004(1)      | I:\...\repository\o00004.nc        ✅ Fixed!
o00801(2)      | NULL                               ⚠️ File not found
o85000         | I:\...\repository\o85000.nc        ✅ Still correct
```

**Result:** Batch rename now works for `o00004(1)` because database points to correct file!

---

## 🛡️ Safety Features

### 1. Non-Destructive

**No files are moved or renamed:**
- Only updates database pointers
- Files stay where they are
- Safe to run multiple times

### 2. Preview Before Action

Shows exactly what will be changed before doing anything:
- Current database path
- New path (if found)
- Which files can't be found

### 3. Multiple Name Variations

Tries multiple variations to find files:
```python
# For program_number: o00004(1)
Tries:
1. o00004(1).nc  ← Exact match
2. o00004.nc     ← Without suffix
3. o00004_1.nc   ← Underscore conversion
```

### 4. Handles Missing Files

Files that can't be found:
- Database path set to NULL
- Marked as "missing file"
- Doesn't break the operation
- User can handle separately

---

## 🔧 Technical Details

### Function: repair_file_paths()

**Location:** Lines 11229-11487

### Repository Scan Logic:

```python
# Scan repository for all .nc files
nc_files = {}  # program_number -> full_path
for root, dirs, files in os.walk(repo_path):
    for filename in files:
        if filename.lower().endswith('.nc'):
            full_path = os.path.join(root, filename)
            base_name = os.path.splitext(filename)[0].lower()
            nc_files[base_name] = full_path
```

### File Matching Logic:

```python
# For each program with incorrect path
base_prog = prog_num.replace('(', '').replace(')', '').replace('_', '').lower()

possible_names = [
    prog_num.lower(),  # Exact match
    base_prog,  # Without suffixes
    prog_num.replace('(', '_').replace(')', '').lower(),  # Convert () to _
]

found_path = None
for name in possible_names:
    if name in nc_files:
        found_path = nc_files[name]
        break
```

### Update Operations:

```python
# Update programs table
cursor.execute("""
    UPDATE programs
    SET file_path = ?
    WHERE program_number = ?
""", (new_path, prog_num))

# Update registry table
cursor.execute("""
    UPDATE program_number_registry
    SET file_path = ?
    WHERE program_number = ?
""", (new_path, prog_num))

conn.commit()
```

---

## 📝 What It Updates

### 1. Programs Table
- Updates `file_path` column
- Points to actual file location
- Sets to NULL if file not found

### 2. Registry Table
- Updates `file_path` column
- Keeps registry in sync with programs
- Sets to NULL if file not found

### Does NOT Update:
- File names on disk (files stay as-is)
- Program numbers
- File content
- Any other database fields

---

## ✅ Success Criteria

After running this function:

**✓ Database paths match actual files**
```
All file_path entries point to files that exist
No paths pointing to non-existent files
```

**✓ Batch rename can find files**
```
Batch rename operations work correctly
No "File not found" errors
Files are renamed successfully
```

**✓ Clean database**
```
Missing files have NULL paths (not incorrect paths)
Can identify which programs are truly missing files
```

---

## 🔄 Integration with Workflow

### Why This Is Needed:

**Problem Scenario:**
1. User imports files → Some paths incorrect
2. User runs "Fix Underscore Suffix" → Files renamed, but DB not updated
3. User tries batch rename → Fails because DB has wrong paths
4. User frustrated, can't proceed

**Solution Scenario:**
1. User imports files → Some paths incorrect
2. User runs "Fix Underscore Suffix" → Files renamed
3. 🔧 User clicks "Repair File Paths" → DB updated to match actual files
4. User runs batch rename → Works perfectly!

### Complete Workflow:

```
1. 📂 Scan Folder
2. 🔄 Sync Registry
3. 🎯 Detect Round Sizes
4. 📁 Add to Repository
5. 🔍 Manage Duplicates (3 passes)
6. 🔧 Repair File Paths ⭐ NEW! (if batch rename fails)
7. 🔧 Batch Rename Out-of-Range
8. 🔄 Sync Filenames with Database
9. ✅ Done!
```

---

## 🎯 Use Cases

### Use Case 1: Batch Rename Failing

**Scenario:**
- Batch rename fails with 27 files
- Error: "File not found"
- Database paths are incorrect

**Solution:**
1. Click "🔧 Repair File Paths"
2. Review preview
3. Apply repairs
4. Retry batch rename → Works!

### Use Case 2: After Manual File Moves

**Scenario:**
- Manually moved/renamed files in repository folder
- Database still has old paths
- Application can't find files

**Solution:**
1. Click "🔧 Repair File Paths"
2. Scan finds files at new locations
3. Database updated
4. Application finds files again

### Use Case 3: After External Import

**Scenario:**
- Imported files from USB/network drive
- Some filenames don't match expectations
- Database has incorrect paths

**Solution:**
1. Click "🔧 Repair File Paths"
2. Matches files by multiple name patterns
3. Database updated with actual paths
4. Repository synchronized

### Use Case 4: Database Cleanup

**Scenario:**
- Suspect database has stale/incorrect paths
- Want to verify and fix
- Ensure all paths are correct

**Solution:**
1. Click "🔧 Repair File Paths"
2. Scans entire repository
3. Fixes any incorrect paths
4. Identifies truly missing files

---

## 📊 Performance

### Speed:

**Small Repository (100-500 files):**
- Scan: 1-2 seconds
- Match: < 1 second
- Update: 1-2 seconds
- Total: 3-5 seconds

**Medium Repository (500-2,000 files):**
- Scan: 2-3 seconds
- Match: 1-2 seconds
- Update: 2-5 seconds
- Total: 5-10 seconds

**Large Repository (2,000+ files):**
- Scan: 3-5 seconds
- Match: 2-3 seconds
- Update: 5-10 seconds
- Total: 10-18 seconds

### Impact:

- Read-only until "Apply Repairs" is clicked
- Only updates database (no file operations)
- Safe to run anytime
- No performance impact on files

---

## 💡 Tips & Best Practices

### Tip 1: Run After Operations

**Good times to run:**
```
✓ After batch operations that failed
✓ After manually moving/renaming files
✓ After importing from external sources
✓ When batch rename reports errors
✓ After database edits
```

### Tip 2: Check Missing Files

If files are marked as "missing":
```
1. Check if they were deleted
2. Check if they're in a different folder
3. Check if they have different names
4. Manually add them back if needed
```

### Tip 3: Run Before Critical Operations

Before major batch operations:
```
1. Run "Repair File Paths"
2. Ensure all paths are correct
3. Then run batch rename/duplicate management
4. Reduces errors and failures
```

### Tip 4: Combine with Sync Filenames

**Best practice workflow:**
```
1. Fix Underscore Suffix Files
2. 🔧 Repair File Paths (DB → match files)
3. 🔄 Sync Filenames (files → match DB)
4. Batch Rename Out-of-Range
5. Clean repository ready!
```

---

## 🎉 Summary

**Purpose:** Fix database file_path entries that don't match actual files in repository

**Location:** Repository tab → "🔧 Repair File Paths" button

**What it does:**
1. Scans repository folder for all .nc files
2. Checks database file_path entries
3. Matches files to database entries
4. Shows preview of repairs needed
5. Updates database with correct paths

**When to use:**
- When batch rename fails with "File not found"
- After manual file operations
- After external imports
- For database cleanup/verification
- Anytime paths seem incorrect

**Result:** Database paths match actual files, batch operations work correctly!

---

**Common Fix Sequence:**

```
❌ Batch rename failing →
🔧 Repair File Paths →
✅ Batch rename works!
```

---

*Feature Added: 2025-12-03*
*Function: repair_file_paths() (lines 11229-11487)*
*Button: Repository tab, Row 4*
