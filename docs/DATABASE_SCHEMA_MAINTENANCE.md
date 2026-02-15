# Database Schema Maintenance Guide

**CRITICAL REFERENCE FOR ADDING NEW COLUMNS TO `programs` TABLE**

This document tracks all INSERT statement locations that must be updated when adding new columns to the `programs` table to prevent "table has X columns but only got Y values" errors.

---

## Current Table Schema

**Table**: `programs`
**Total Columns**: 56 (as of 2026-02-07)

### Column Order (1-56):
```
 1. program_number           2. title                    3. spacer_type
 4. outer_diameter           5. thickness                6. thickness_display
 7. center_bore              8. hub_height               9. hub_diameter
10. counter_bore_diameter   11. counter_bore_depth      12. paired_program
13. material                14. notes                   15. date_created
16. last_modified           17. file_path               18. detection_confidence
19. detection_method        20. validation_status       21. validation_issues
22. validation_warnings     23. cb_from_gcode           24. ob_from_gcode
25. bore_warnings           26. dimensional_issues      27. lathe
28. duplicate_type          29. parent_file             30. duplicate_group
31. current_version         32. modified_by             33. is_managed
34. round_size              35. round_size_confidence   36. round_size_source
37. in_correct_range        38. legacy_names            39. last_renamed_date
40. rename_reason           41. tools_used              42. tool_sequence
43. tool_validation_status  44. tool_validation_issues  45. safety_blocks_status
46. safety_blocks_issues    47. content_hash            48. tool_home_status
49. tool_home_issues        50. hub_height_display      51. counter_bore_depth_display
52. feasibility_status      53. feasibility_issues      54. feasibility_warnings
55. crash_issues            56. crash_warnings
```

---

## Adding a New Column - Required Updates

When adding a new column, you **MUST** update the following locations in **gcode_database_manager.py**:

### Step 1: Update Table Schema
**Location**: `init_database()` method (~line 1491)

```python
# Add to CREATE TABLE statement
CREATE TABLE IF NOT EXISTS programs (
    ...
    crash_warnings TEXT,
    your_new_column TEXT  -- Add your new column here
)
```

### Step 2: Add Migration for Existing Databases
**Location**: `init_database()` method (~line 1595)

```python
# Add ALTER TABLE statement
try:
    cursor.execute("ALTER TABLE programs ADD COLUMN your_new_column TEXT")
except:
    pass
```

### Step 3: Update ProgramRecord Dataclass
**Location**: `ProgramRecord` class definition (~line 340)

```python
@dataclass
class ProgramRecord:
    ...
    crash_warnings: Optional[List[str]] = None
    your_new_column: Optional[str] = None  -- Add your field here
```

### Step 4: Update Documentation Comment
**Location**: `init_database()` method header (~line 1441-1483)

Update the column count and column order list:
```python
"""
PROGRAMS TABLE COLUMN REFERENCE (57 columns total)  <-- Increment count
...
Column order (for VALUES inserts):
...
56. crash_warnings
57. your_new_column  <-- Add new column here
"""
```

### Step 5: Update ALL INSERT Statements

⚠️ **CRITICAL**: The following INSERT statements MUST be updated:

---

## INSERT Statement Registry

### Category A: Full VALUES Inserts (Must have ALL 56+ columns)

These INSERT statements use `VALUES (?, ?, ?, ...)` with positional placeholders for **every column**. When adding a new column, you MUST add a placeholder and value to each.

#### 1. Scan Folder Thread - Line ~8676
**File**: `gcode_database_manager.py`
**Method**: `scan_folder()` → `scan_thread()`
**Pattern**: `INSERT INTO programs VALUES (...)`
**Current Columns**: 56

```python
cursor.execute('''
    INSERT INTO programs VALUES (?, ?, ?, ..., ?, ?)  -- Must have 56 ?'s
''', (
    record.program_number,
    ...
    None, None  # crash_issues, crash_warnings
    # ADD NEW COLUMN VALUE HERE
))
```

**Action Required**: Add one more `?` in VALUES and one more value in the tuple.

---

#### 2. Manual Entry Dialog - Line ~24480
**File**: `gcode_database_manager.py`
**Method**: `ManualEntryDialog.save_entry()`
**Pattern**: `INSERT INTO programs VALUES (...)`
**Current Columns**: 56

```python
cursor.execute('''
    INSERT INTO programs VALUES (?, ?, ?, ..., ?, ?)  -- Must have 56 ?'s
''', (
    program_number,
    ...
    None, None  # crash_issues, crash_warnings
    # ADD NEW COLUMN VALUE HERE
))
```

**Action Required**: Add one more `?` in VALUES and one more value in the tuple.

---

### Category B: Named Column Inserts (Subset of columns)

These INSERT statements explicitly list column names, so they only need updating if the new column should be included. The unlisted columns will be NULL.

#### 3. Process New File - Line ~5195
**File**: `gcode_database_manager.py`
**Method**: `process_new_file()`
**Pattern**: `INSERT INTO programs (col1, col2, ...) VALUES (...)`
**Current Columns**: 35 (subset)

```python
cursor.execute("""
    INSERT INTO programs (
        program_number, title, ...,
        crash_issues, crash_warnings
        -- Add your_new_column here if needed
    ) VALUES (?, ?, ..., ?, ?)
""", (...))
```

**Action Required**:
- If new column should be set during file processing: Add to column list and VALUES
- If NULL is fine: No change needed

---

#### 4. Import Files Batch - Line ~7944
**File**: `gcode_database_manager.py`
**Method**: `import_files_to_repository_batch()`
**Pattern**: `INSERT OR REPLACE INTO programs (...) VALUES (...)`
**Current Columns**: 56 (all columns)

```python
cursor.execute('''
    INSERT OR REPLACE INTO programs (
        program_number, title, ...,
        crash_issues, crash_warnings
        -- ADD NEW COLUMN NAME HERE
    ) VALUES (?, ?, ..., ?, ?)  -- ADD PLACEHOLDER HERE
''', (
    record.program_number,
    ...
    None, None  # crash_issues, crash_warnings
    # ADD VALUE HERE
))
```

**Action Required**: Add column name, placeholder, and value.

---

#### 5. Import Single File - Line ~8025
**File**: `gcode_database_manager.py`
**Method**: `_import_single_file()`
**Pattern**: `INSERT OR REPLACE INTO programs (...) VALUES (...)`
**Current Columns**: 56 (all columns)

```python
cursor.execute("""
    INSERT OR REPLACE INTO programs (
        program_number, title, ...,
        crash_issues, crash_warnings
        -- ADD NEW COLUMN NAME HERE
    ) VALUES (?, ?, ..., ?, ?)  -- ADD PLACEHOLDER HERE
""", (
    record.program_number,
    ...
    None, None  # crash_issues, crash_warnings
    # ADD VALUE HERE
))
```

**Action Required**: Add column name, placeholder, and value.

---

#### 6. Scan New Files Processing - Line ~9458
**File**: `gcode_database_manager.py`
**Method**: `scan_for_new_files()` → processing thread
**Pattern**: `INSERT INTO programs (...) VALUES (...)`
**Current Columns**: 56 (all columns)

```python
cursor.execute('''
    INSERT INTO programs (
        program_number, title, ...,
        crash_issues, crash_warnings
        -- ADD NEW COLUMN NAME HERE
    ) VALUES (?, ?, ..., ?, ?)  -- ADD PLACEHOLDER HERE
''', (
    record.program_number,
    ...
    None, None  # crash_issues, crash_warnings
    # ADD VALUE HERE
))
```

**Action Required**: Add column name, placeholder, and value.

---

#### 7. Process New Files Workflow - Line ~9026
**File**: `gcode_database_manager.py`
**Method**: `process_new_files_workflow()` → import thread
**Pattern**: `INSERT OR REPLACE INTO programs VALUES (...)`
**Current Columns**: 56 (all columns)

```python
cursor.execute('''
    INSERT OR REPLACE INTO programs VALUES (?, ?, ..., ?, ?)  -- Must have 56 ?'s
''', (
    record.program_number,
    ...
    None, None  # crash_issues, crash_warnings
    # ADD NEW COLUMN VALUE HERE
))
```

**Action Required**: Add one more `?` in VALUES and one more value in the tuple.

---

## Quick Reference Checklist

When adding a new column to `programs` table:

- [ ] **Step 1**: Add to CREATE TABLE in `init_database()` (~line 1491)
- [ ] **Step 2**: Add ALTER TABLE migration (~line 1595)
- [ ] **Step 3**: Add field to `ProgramRecord` dataclass (~line 340)
- [ ] **Step 4**: Update column count and list in documentation comment (~line 1441)
- [ ] **Step 5**: Update INSERT statements:
  - [ ] Line ~8676: scan_folder() - VALUES insert (add ?, value)
  - [ ] Line ~24480: ManualEntryDialog - VALUES insert (add ?, value)
  - [ ] Line ~5195: process_new_file() - Check if column needed
  - [ ] Line ~7944: import_files_batch() - Add column name, ?, value
  - [ ] Line ~8025: _import_single_file() - Add column name, ?, value
  - [ ] Line ~9458: scan_new_files() - Add column name, ?, value
- [ ] **Step 6**: Run test: `python test_column_count.py`
- [ ] **Step 7**: Run test: `python test_scan_fix.py`
- [ ] **Step 8**: Test actual scan/import functionality

---

## Testing After Changes

### Test 1: Column Count Verification
```bash
python test_column_count.py
```

Expected output:
```
[PASS] INSERT with 57 values: SUCCESS  # Updated count
The schema mismatch is FIXED!
```

### Test 2: All INSERT Patterns
```bash
python test_scan_fix.py
```

Expected output:
```
[PASS] 57-column VALUES INSERT works
[PASS] 35-column named INSERT works
[PASS] 57-column named INSERT works
```

### Test 3: Actual Functionality
- Run database scan: Tools → Scan for New Files
- Import a file: File → Import to Repository
- Add manual entry: File → Add Manual Entry

All should work without "table has X columns but got Y values" errors.

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Forgetting VALUES Inserts
**Problem**: Only updating named column INSERTs, forgetting positional VALUES
**Result**: "table has 57 columns but got 56 values" error during scan

**Solution**: Always check Category A (Full VALUES Inserts) first!

### ❌ Mistake 2: Wrong Placeholder Count
**Problem**: Adding column name but forgetting placeholder `?`
**Result**: "column count mismatch" error

**Solution**: Count: Column names must equal placeholders must equal values

### ❌ Mistake 3: Not Testing After Changes
**Problem**: Assuming it works, deploying without testing
**Result**: Runtime errors during production use

**Solution**: Always run test_column_count.py and test_scan_fix.py

### ❌ Mistake 4: Inconsistent NULL Values
**Problem**: Some INSERTs use None, others use 0 or ""
**Result**: Inconsistent data, hard to query

**Solution**: Use None for new columns unless there's a specific default

---

## History of Column Additions

### 2026-02-07: Crash Prevention & Feasibility (51 → 56 columns)
**Added**:
- feasibility_status (52)
- feasibility_issues (53)
- feasibility_warnings (54)
- crash_issues (55)
- crash_warnings (56)

**Issue**: INSERT statements at lines 7944, 8025, and 9458 not updated
**Result**: "table has 56 columns but got 51/27/30 values" errors
**Fix**: Updated all 6 INSERT statement locations

**Lesson Learned**: Need comprehensive documentation to track all INSERT locations

### Previous: (Columns 1-51)
Original schema through various feature additions including:
- Tool validation
- Round size detection
- Duplicate management
- Version control
- Safety blocks
- Tool home validation

---

## Emergency Fix Procedure

If you see "table has X columns but got Y values" error:

1. **Identify the INSERT statement** from the error traceback
2. **Count actual columns** in table:
   ```python
   cursor.execute('PRAGMA table_info(programs)')
   print(f"Actual columns: {len(cursor.fetchall())}")
   ```
3. **Find the problematic INSERT** in this document's registry
4. **Update the INSERT** to match current column count
5. **Test** with test_column_count.py
6. **Document** the fix in this file's History section

---

## Maintenance Notes

- This document must be updated whenever columns are added/removed
- Keep INSERT statement line numbers current (they shift as code changes)
- Update test scripts when schema changes
- Review quarterly to ensure accuracy

---

**Document Version**: 1.0
**Last Updated**: 2026-02-07
**Next Review**: 2026-05-07
**Maintainer**: Development Team

---

*Keep this document in sync with actual code. When in doubt, run the tests!*
