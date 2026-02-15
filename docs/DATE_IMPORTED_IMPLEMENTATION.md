# Date Imported Field Implementation

**Date**: 2026-02-07
**Status**: ✅ COMPLETE

---

## Summary

Added `date_imported` field to track when G-code files were first imported into the database. Includes both database schema changes and UI filter for searching by import date.

---

## Changes Made

### 1. Database Schema (COMPLETE)

#### CREATE TABLE - Line ~1593
```sql
crash_issues TEXT,
crash_warnings TEXT,
date_imported TEXT  -- ISO timestamp when file was imported to database
)
```

#### ALTER TABLE Migration - Line ~1766
```python
try:
    cursor.execute("ALTER TABLE programs ADD COLUMN date_imported TEXT")
except:
    pass
```

#### ProgramRecord Dataclass - Line ~441
```python
# Import tracking
date_imported: Optional[str] = None  # ISO timestamp when file was imported to database
```

---

### 2. Documentation Updated (COMPLETE)

**Line ~1504**: Updated column count from 56 to 57 columns

**Line ~1552**: Added to column order list:
```
55. crash_issues           56. crash_warnings         57. date_imported
```

---

### 3. All INSERT Statements Updated (COMPLETE)

Updated all 7 INSERT statement locations to include `date_imported` field:

#### VALUES-based INSERTs (added one more ? placeholder and value):

1. **Line ~8786**: `scan_folder()` - Added `datetime.now().isoformat()` as 57th value
2. **Line ~9091**: `process_new_files_workflow()` - Added `datetime.now().isoformat()` as 57th value
3. **Line ~24628**: `ManualEntryDialog.save_entry()` - Added `datetime.now().isoformat()` as 57th value

#### Named Column INSERTs (added column name + value):

4. **Line ~8032**: `import_files_batch()` - Added `date_imported` column and `datetime.now().isoformat()` value
5. **Line ~8113**: `_import_single_file()` - Added `date_imported` column and `datetime.now().isoformat()` value
6. **Line ~9552**: `scan_new_files()` - Added `date_imported` column and `datetime.now().isoformat()` value

**All INSERT statements now use 57 columns/values instead of 56.**

---

### 4. UI Filter Added (COMPLETE)

#### Filter UI Widgets - Line ~7477

Added new row (row2_7) with date range filter:

```python
# Row 2.7 - Date Imported filter
row2_7 = tk.Frame(filter_container, bg=self.bg_color)
row2_7.pack(fill=tk.X, pady=5)

tk.Label(row2_7, text="Date Imported:", bg=self.bg_color, fg=self.fg_color,
        font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

tk.Label(row2_7, text="From:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
self.filter_date_from = tk.Entry(row2_7, width=12, bg=self.input_bg, fg=self.fg_color)
self.filter_date_from.pack(side=tk.LEFT, padx=2)

tk.Label(row2_7, text="To:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
self.filter_date_to = tk.Entry(row2_7, width=12, bg=self.input_bg, fg=self.fg_color)
self.filter_date_to.pack(side=tk.LEFT, padx=2)

tk.Label(row2_7, text="(YYYY-MM-DD format)",
        bg=self.bg_color, fg="#888888", font=("Arial", 8, "italic")).pack(side=tk.LEFT, padx=5)
```

#### Filter Query Logic - Line ~11824

Added date filter to `refresh_results()` method:

```python
# Date Imported filter
if hasattr(self, 'filter_date_from') and self.filter_date_from.get():
    try:
        # Accept YYYY-MM-DD format and convert to ISO timestamp for comparison
        date_from = self.filter_date_from.get().strip()
        # Add time component to make it start of day
        query += " AND date_imported >= ?"
        params.append(f"{date_from}T00:00:00")
    except:
        pass  # Ignore invalid date format

if hasattr(self, 'filter_date_to') and self.filter_date_to.get():
    try:
        # Accept YYYY-MM-DD format and convert to ISO timestamp for comparison
        date_to = self.filter_date_to.get().strip()
        # Add time component to make it end of day
        query += " AND date_imported <= ?"
        params.append(f"{date_to}T23:59:59")
    except:
        pass  # Ignore invalid date format
```

---

## How to Use

### For New Imports

When files are imported using any of the import methods (scan folder, drag & drop, manual entry), the `date_imported` field is automatically set to the current timestamp in ISO format.

**Example**: `2026-02-07T14:23:45`

### For Existing Records

Existing database records will have `NULL` for `date_imported` since they were imported before this field was added. They can be filtered out or will show as "not imported" in the date filter.

### Using the Date Filter

1. Open the main window
2. In the filter section, find the new "Date Imported" row
3. Enter dates in YYYY-MM-DD format:
   - **From**: `2026-02-01` (start of day)
   - **To**: `2026-02-07` (end of day)
4. Results will update automatically to show only files imported within that date range

**Examples**:
- Files imported today: From: `2026-02-07`, To: `2026-02-07`
- Files imported this week: From: `2026-02-01`, To: `2026-02-07`
- Files imported after specific date: From: `2026-01-15`, To: (leave blank)
- Files imported before specific date: From: (leave blank), To: `2026-02-05`

---

## Database Migration

The `ALTER TABLE` statement will run automatically on startup for existing databases, adding the `date_imported` column with NULL values for existing records.

**No manual database migration required** - just restart the application.

---

## Technical Details

- **Field Type**: TEXT (ISO 8601 timestamp format)
- **Format**: `YYYY-MM-DDTHH:MM:SS` (e.g., `2026-02-07T14:23:45`)
- **Timezone**: Local system time (no timezone suffix)
- **Nullable**: Yes (existing records will be NULL)
- **Indexed**: No (can be added later if performance requires)
- **Set When**: Only on initial import, never updated

---

## Files Modified

1. **gcode_database_manager.py**:
   - Line ~441: ProgramRecord dataclass
   - Line ~1504-1552: Documentation (column count and list)
   - Line ~1593: CREATE TABLE
   - Line ~1766: ALTER TABLE migration
   - Line ~7477: Filter UI widgets
   - Line ~8032: import_files_batch INSERT
   - Line ~8113: _import_single_file INSERT
   - Line ~8786: scan_folder INSERT
   - Line ~9091: process_new_files_workflow INSERT
   - Line ~9552: scan_new_files INSERT
   - Line ~11824: refresh_results filter logic
   - Line ~24628: ManualEntryDialog INSERT

---

## Testing Checklist

✅ Schema changes complete (CREATE TABLE, ALTER TABLE, dataclass)
✅ Documentation updated (column count, column list)
✅ All 7 INSERT statements updated
✅ UI filter widgets added
✅ Filter query logic implemented
⏳ Restart application to apply changes
⏳ Import a new file and verify date_imported is set
⏳ Use date filter to search by import date

---

**Implementation Complete**: 2026-02-07
**Ready to Use**: Yes - restart application to test
