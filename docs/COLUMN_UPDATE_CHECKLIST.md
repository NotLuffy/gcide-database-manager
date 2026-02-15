# Database Column Addition - Quick Checklist

**Use this checklist when adding a new column to the `programs` table**

---

## Pre-Flight Check
- [ ] Current column count: **56**
- [ ] New column count will be: **_____**
- [ ] Column name: **_____________________**
- [ ] Column type: **_____________________**
- [ ] Default value: **_____________________**

---

## Required Updates

### 1. Database Schema
- [ ] **Line ~1491**: Add to CREATE TABLE statement
- [ ] **Line ~1595**: Add ALTER TABLE migration
- [ ] **Line ~1445**: Update column count in comment (56 → XX)
- [ ] **Line ~1463**: Add to column order list

### 2. Data Model
- [ ] **Line ~340**: Add field to ProgramRecord dataclass

### 3. INSERT Statements (6 locations)

#### Full VALUES Inserts (add ?, value):
- [ ] **Line ~8676**: scan_folder() VALUES insert
  ```python
  INSERT INTO programs VALUES (?, ?, ..., ?)  ← Add one more ?
  ''', (..., None, None, NEW_VALUE))          ← Add value here
  ```

- [ ] **Line ~24480**: ManualEntryDialog VALUES insert
  ```python
  INSERT INTO programs VALUES (?, ?, ..., ?)  ← Add one more ?
  ''', (..., None, None, NEW_VALUE))          ← Add value here
  ```

#### Named Column Inserts (add column name, ?, value):
- [ ] **Line ~5195**: process_new_file()
  - Check if new column needed for file processing
  - If yes: Add to column list, placeholder, and value
  - If no: Skip (will be NULL)

- [ ] **Line ~7944**: import_files_batch()
  ```python
  INSERT OR REPLACE INTO programs (
      ..., crash_warnings, NEW_COLUMN  ← Add column name
  ) VALUES (..., ?, ?)                 ← Add placeholder
  ''', (..., None, NEW_VALUE))         ← Add value
  ```

- [ ] **Line ~8025**: _import_single_file()
  ```python
  INSERT OR REPLACE INTO programs (
      ..., crash_warnings, NEW_COLUMN  ← Add column name
  ) VALUES (..., ?, ?)                 ← Add placeholder
  ''', (..., None, NEW_VALUE))         ← Add value
  ```

- [ ] **Line ~9458**: scan_new_files()
  ```python
  INSERT INTO programs (
      ..., crash_warnings, NEW_COLUMN  ← Add column name
  ) VALUES (..., ?, ?)                 ← Add placeholder
  ''', (..., None, NEW_VALUE))         ← Add value
  ```

---

## Testing (REQUIRED)

- [ ] **Test 1**: Run `python test_column_count.py`
  - Expected: `[PASS] INSERT with 57 values: SUCCESS`

- [ ] **Test 2**: Run `python test_scan_fix.py`
  - Expected: All [PASS]

- [ ] **Test 3**: Scan for new files
  - Tools → Scan for New Files
  - Should complete without errors

- [ ] **Test 4**: Import a file
  - File → Import to Repository
  - Should complete without errors

- [ ] **Test 5**: Manual entry
  - File → Add Manual Entry
  - Should save without errors

---

## Common Errors

❌ **"table has 57 columns but got 56 values"**
- Forgot to update a VALUES INSERT
- Check lines ~8676 and ~24480

❌ **"table programs has no column named X"**
- Forgot to add to CREATE TABLE or ALTER TABLE
- Check lines ~1491 and ~1595

❌ **"X supplied X bound variables"**
- Column count doesn't match placeholder count
- Count: column names = placeholders = values

---

## After Completion

- [ ] Update docs/DATABASE_SCHEMA_MAINTENANCE.md with:
  - New column count
  - Column added to list
  - Entry in History section
  - Current line numbers (if they shifted)

- [ ] Commit changes with message:
  ```
  Add [column_name] column to programs table

  - Added CREATE TABLE and ALTER TABLE
  - Updated ProgramRecord dataclass
  - Updated all 6 INSERT statement locations
  - Tests passing: column_count, scan_fix
  ```

---

## Need Help?

📖 **Full Reference**: See `docs/DATABASE_SCHEMA_MAINTENANCE.md`

🔧 **Emergency Fix**: If you see column count errors:
1. Check error traceback for line number
2. Find INSERT statement in DATABASE_SCHEMA_MAINTENANCE.md
3. Add missing column/placeholder/value
4. Run tests
5. Document fix

---

**Checklist Version**: 1.0
**Last Updated**: 2026-02-07
**Current Schema**: 56 columns

---

*Print this checklist and keep it handy when modifying the database schema!*
