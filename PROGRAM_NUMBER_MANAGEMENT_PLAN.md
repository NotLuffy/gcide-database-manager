# Program Number Management Plan

## 🎯 Overview

This document outlines a comprehensive system for managing program numbers based on round size ranges, detecting/resolving duplicates, and maintaining an Excel tracking file for number availability.

---

## 📐 Round Size to Program Number Ranges

### Defined Ranges

| Round Size | Program Number Range | Total Capacity |
|------------|---------------------|----------------|
| **10.25 & 10.50** | O10000 - O12999 | 3,000 numbers |
| **13.0** | O13000 - O13999 | 1,000 numbers |
| **5.75** | O50000 - O59999 | 10,000 numbers |
| **6.0** | O60000 - O62499 | 2,500 numbers |
| **6.25** | O62500 - O64999 | 2,500 numbers |
| **6.5** | O65000 - O69999 | 5,000 numbers |
| **7.0** | O70000 - O74999 | 5,000 numbers |
| **7.5** | O75000 - O79000 | 4,001 numbers |
| **8.0** | O80000 - O84999 | 5,000 numbers |
| **8.5** | O85000 - O89999 | 5,000 numbers |
| **9.5** | O90000 - O99999 | 10,000 numbers |
| **Free Range 1** | O01000 - O09999 | 9,000 numbers |
| **Free Range 2** | O14000 - O49999 | 36,000 numbers |

**Total Capacity:** 97,001 program numbers

---

## 🔧 System Requirements

### 1. Excel Tracking File

**File:** `program_number_registry.xlsx`

**Structure:**

| Column A | Column B | Column C | Column D | Column E | Column F |
|----------|----------|----------|----------|----------|----------|
| Program # | Status | File Path 1 | Dup Type 1 | File Path 2 | Dup Type 2 |
| O10000 | Available | - | - | - | - |
| O10001 | In Use | repository/o10001.nc | - | - | - |
| O10002 | In Use | repository/o10002.nc | Name Match | E:/USB/o10002.nc | Content Mismatch |
| O10003 | In Use | repository/o10003.nc | Name + Content | repository/o10003(1).nc | Exact Duplicate |

**Benefits:**
- ✅ Fast lookup without database query
- ✅ Visual availability at a glance
- ✅ Duplicate tracking in one place
- ✅ Can be shared/exported for review

### 2. Automatic Round Size Detection

**Methods (in priority order):**

1. **From Title** - Parse title for round size mention
   ```
   "6.25 OD Spacer CB 54mm" → Round size: 6.25
   "7.0 solid disc" → Round size: 7.0
   ```

2. **From Geometry (OD in G-code)** - Use `ob_from_gcode` field
   ```sql
   SELECT ob_from_gcode FROM programs WHERE program_number = 'o12345'
   -- If ob_from_gcode = 6.25, assign to 6.25 range
   ```

3. **From Database Dimensions** - Use `outer_diameter` field
   ```sql
   SELECT outer_diameter FROM programs WHERE program_number = 'o12345'
   -- Match to closest defined range
   ```

4. **Manual Assignment** - User selects from dropdown if auto-detection fails

### 3. Program Number Assignment Logic

**Algorithm:**

```
FOR each file needing a number:
  1. Detect round size (title → gcode → dimensions → manual)
  2. Look up range for that round size
  3. Query Excel file for first "Available" number in range
  4. IF no available numbers in range:
       Use Free Range (01000-09999, then 14000-49999)
  5. Assign new number to file
  6. Update Excel: Mark as "In Use", add file path
  7. Update internal O-number in file content
  8. Add legacy name comment to file
  9. Rename physical file on disk
  10. Update database record
```

---

## 🔍 Duplicate Detection & Resolution

### Type 1: Same Name, Different Content

**Detection:**
```sql
SELECT program_number, COUNT(*) as count,
       GROUP_CONCAT(file_path) as paths,
       GROUP_CONCAT(content_hash) as hashes
FROM programs
GROUP BY program_number
HAVING count > 1
  AND COUNT(DISTINCT content_hash) > 1
```

**Resolution Strategy:**

**Option A: Keep Lowest Number in Correct Range**
```
Files:
  o12345 (content: ABC, OD: 6.25) - Falls in 6.25 range (62500-64999) - WRONG RANGE
  o12345 (content: XYZ, OD: 10.5) - Falls in 10.25/10.50 range (10000-12999) - CORRECT RANGE

Decision:
  - Keep o12345 for the 10.5 file (correct range)
  - Rename o12345 (6.25) → o62500 (first available in 6.25 range)
```

**Option B: Keep Newest/Repository File**
```
Files:
  o12345 (date: 2023-01-01, location: external)
  o12345 (date: 2025-01-01, location: repository)

Decision:
  - Keep o12345 (repository, newest)
  - Rename o12345 (external) → next available in its range
```

**Implementation:**
- Present user with side-by-side comparison
- Show: Content preview, round size, date, location
- Recommend which to keep based on rules
- Allow user override

### Type 2: Same Name, Same Content

**Detection:**
```sql
SELECT program_number, content_hash, COUNT(*) as count,
       GROUP_CONCAT(file_path) as paths
FROM programs
GROUP BY program_number, content_hash
HAVING count > 1
```

**Resolution Strategy:**

**Simple - Keep Best Copy:**
```
Files:
  o12345 (hash: abc123, date: 2023-01-01, location: external)
  o12345 (hash: abc123, date: 2025-01-01, location: repository)

Decision:
  - Keep repository copy (date: 2025-01-01)
  - Delete external reference (or move external file to deleted/)
```

**Priority Order:**
1. Repository over External (`is_managed = 1`)
2. Newest over Oldest (`date_created DESC`)
3. Lowest file path length (fewer nested folders)

**Implementation:**
- Automatic with preview
- Show which will be kept/deleted
- Batch operation available

### Type 3: Different Name, Same Content

**Detection:**
```sql
SELECT content_hash, COUNT(*) as count,
       GROUP_CONCAT(program_number) as numbers,
       GROUP_CONCAT(file_path) as paths,
       GROUP_CONCAT(outer_diameter) as ods
FROM programs
GROUP BY content_hash
HAVING count > 1
  AND COUNT(DISTINCT program_number) > 1
```

**Resolution Strategy:**

**Keep Lowest Number in Correct Range:**
```
Files:
  o62500 (hash: abc123, OD: 6.25) - In correct range (62500-64999)
  o62750 (hash: abc123, OD: 6.25) - In correct range (62500-64999)
  o12345 (hash: abc123, OD: 6.25) - WRONG range (should be 62500-64999)

Decision:
  - Keep o62500 (lowest number in correct range)
  - Delete o62750 (duplicate, higher number)
  - Rename o12345 → o62501 (wrong range, move to correct range)
    OR delete if it's exact duplicate of o62500
```

**Similarity Threshold:**
- 100% match (exact) → Automatic resolution
- 95-99% match (near-duplicate) → User review
- <95% match → Separate programs, no action

**Implementation:**
- Side-by-side comparison with % similarity
- Highlight differences
- Show round size and range correctness
- Recommend action

---

## 📝 Legacy Name Tracking

### Comment Format

When renaming a file, add comment to top of G-code:

```gcode
(====================================)
(LEGACY NAME: o12345)
(RENAMED TO: o62500)
(DATE: 2025-11-26)
(REASON: Round size range correction - 6.25 OD should be in 62500-64999 range)
(PREVIOUS PATH: I:/My Drive/NC Master/REVISED PROGRAMS/o12345.nc)
(====================================)
O62500
G54
...
```

**Benefits:**
- ✅ Audit trail of name changes
- ✅ Can search for files by old name
- ✅ Understand why file was renamed
- ✅ File path preserved for reference (machine ignores comments)

**Database Field:**
- Add `legacy_names` TEXT field to programs table
- Store JSON array: `["o12345", "o12346"]`
- Allows searching by previous names

---

## 🚀 Implementation Phases

### Phase 1: Excel Registry Setup (Week 1)

**Tasks:**
1. Generate initial Excel file with all program number ranges
2. Mark current database entries as "In Use"
3. Mark gaps as "Available"
4. Add duplicate tracking columns
5. Export to `program_number_registry.xlsx`

**Deliverables:**
- Excel file with 97,001 rows
- Initial status populated from database
- Formulas for availability calculation

**Code Required:**
- `generate_program_registry()` - Create Excel file
- `update_registry_status()` - Sync with database
- `find_next_available()` - Lookup first available number in range

### Phase 2: Round Size Detection (Week 2)

**Tasks:**
1. Add `round_size` field to programs table
2. Implement auto-detection from title
3. Implement auto-detection from `ob_from_gcode`
4. Implement auto-detection from `outer_diameter`
5. Create manual assignment UI
6. Add range validation

**Deliverables:**
- Auto-detection algorithm with confidence scoring
- Manual override UI
- Range lookup table
- Validation warnings for out-of-range numbers

**Code Required:**
- `detect_round_size()` - Multi-method detection
- `get_range_for_round_size()` - Range lookup
- `validate_number_in_range()` - Check if number matches round size

### Phase 3: Duplicate Type 1 - Name/Content Mismatch (Week 3)

**Tasks:**
1. Scan for same name, different content
2. Build comparison UI
3. Implement "Keep in Correct Range" logic
4. Implement rename with legacy tracking
5. Add batch processing

**Deliverables:**
- Detection query
- Side-by-side comparison window
- Automatic recommendation engine
- Batch rename tool

**Code Required:**
- `find_name_content_mismatch()` - Detection
- `recommend_keeper()` - Decision logic
- `rename_with_legacy()` - Rename + comment
- `NameMismatchResolutionWindow()` - UI class

### Phase 4: Duplicate Type 2 - Name/Content Match (Week 4)

**Tasks:**
1. Scan for exact duplicates
2. Build automatic resolution logic
3. Implement preview before deletion
4. Add batch processing
5. Track deletions

**Deliverables:**
- Detection query
- Priority ranking algorithm
- Confirmation dialog with preview
- Deletion log

**Code Required:**
- `find_exact_duplicates()` - Detection
- `rank_duplicates()` - Priority algorithm
- `delete_duplicates_batch()` - Batch deletion

### Phase 5: Duplicate Type 3 - Different Name, Same Content (Week 5)

**Tasks:**
1. Scan for content matches with different names
2. Implement similarity percentage calculation
3. Build comparison UI with highlighting
4. Implement "Keep Lowest in Range" logic
5. Add fuzzy matching threshold

**Deliverables:**
- Content hash grouping query
- Similarity % calculator
- Comparison window with diff highlighting
- Range-aware decision engine

**Code Required:**
- `find_content_duplicates_diff_names()` - Detection
- `calculate_similarity()` - % match calculator
- `get_correct_range()` - Validate number vs round size
- `ContentMatchResolutionWindow()` - UI class

### Phase 6: Integration & Testing (Week 6)

**Tasks:**
1. Integrate all 3 duplicate types into workflow
2. Create master "Resolve All Duplicates" wizard
3. Add progress tracking
4. Add undo capability
5. Comprehensive testing

**Deliverables:**
- Unified resolution wizard
- Progress bar with step indicators
- Undo log
- Test suite

**Code Required:**
- `DuplicateResolutionWizard()` - Master UI class
- `DuplicateResolutionEngine()` - Orchestrator
- `ResolutionHistory()` - Undo tracking

---

## 🎨 UI Mockups

### 1. Duplicate Resolution Wizard

```
┌─────────────────────────────────────────────────────────────────┐
│              🔧 Duplicate Resolution Wizard                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1/3: Name Mismatch Resolution                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                 │
│  Found 47 files with same name but different content           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Program: O12345                                         │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ File 1: repository/o12345.nc                            │  │
│  │  - Round Size: 6.25 (WRONG RANGE - should be 62500+)   │  │
│  │  - Date: 2023-01-15                                     │  │
│  │  - Content Preview: G54 G00 X0 Y0...                    │  │
│  │                                                          │  │
│  │ File 2: external/USB/o12345.nc                          │  │
│  │  - Round Size: 10.5 (CORRECT RANGE - 10000-12999)      │  │
│  │  - Date: 2025-05-10                                     │  │
│  │  - Content Preview: G55 G01 X1 Y1...                    │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ ✅ Recommendation:                                      │  │
│  │    - Keep o12345 for File 2 (10.5, correct range)      │  │
│  │    - Rename File 1 → o62500 (first available in 6.25)  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [ ✓ Accept ] [ Compare Side-by-Side ] [ Manual Override ]    │
│  [ Skip ] [ Skip All Similar ]                                 │
│                                                                 │
│  Progress: 1/47   [ Previous ] [ Next ] [ Batch Process ]     │
├─────────────────────────────────────────────────────────────────┤
│  [ Cancel ]              [ Apply Changes ]           [ Finish ] │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Program Number Registry Viewer

```
┌─────────────────────────────────────────────────────────────────┐
│              📊 Program Number Registry                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Round Size: [6.25 ▼]     Status: [All ▼]                     │
│                                                                 │
│  Range: O62500 - O64999    Available: 1,847 / 2,500 (73.9%)   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                 │
│  Program #  Status      File Path              Duplicates      │
│  ────────────────────────────────────────────────────────────  │
│  O62500     Available   -                      -               │
│  O62501     In Use      repository/o62501.nc   -               │
│  O62502     In Use      repository/o62502.nc   Name Match (2)  │
│  O62503     Available   -                      -               │
│  O62504     In Use      repository/o62504.nc   Content (1)     │
│  ...                                                            │
│                                                                 │
│  [ Refresh ] [ Export to Excel ] [ Find Next Available ]       │
├─────────────────────────────────────────────────────────────────┤
│  Next Available: O62500, O62503, O62505...                     │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Rename with Legacy Tracking

```
┌─────────────────────────────────────────────────────────────────┐
│              ✏️ Rename Program with Legacy Tracking            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Current Name:  O12345                                         │
│  Round Size:    6.25 (detected from OD)                        │
│  Correct Range: O62500 - O64999                                │
│                                                                 │
│  ⚠️ WARNING: Current number is outside correct range!         │
│                                                                 │
│  New Name:      [O62500] (auto-suggested)                      │
│                 [ Find Next Available ]                         │
│                                                                 │
│  ☑ Update internal O-number in file content                    │
│  ☑ Add legacy name comment to file                             │
│  ☑ Update Excel registry                                       │
│  ☑ Track in database (legacy_names field)                      │
│                                                                 │
│  Legacy Comment Preview:                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ (====================================)                  │  │
│  │ (LEGACY NAME: O12345)                                   │  │
│  │ (RENAMED TO: O62500)                                    │  │
│  │ (DATE: 2025-11-26)                                      │  │
│  │ (REASON: Range correction - 6.25 OD → 62500-64999)     │  │
│  │ (====================================)                  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [ Cancel ]                              [ Rename Program ]    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Database Schema Updates

### New Fields for Programs Table

```sql
ALTER TABLE programs ADD COLUMN round_size REAL;
ALTER TABLE programs ADD COLUMN round_size_confidence TEXT;  -- 'HIGH', 'MEDIUM', 'LOW'
ALTER TABLE programs ADD COLUMN round_size_source TEXT;      -- 'TITLE', 'GCODE', 'DIMENSION', 'MANUAL'
ALTER TABLE programs ADD COLUMN legacy_names TEXT;           -- JSON array: ["o12345", "o12346"]
ALTER TABLE programs ADD COLUMN last_renamed_date TEXT;      -- ISO timestamp
ALTER TABLE programs ADD COLUMN rename_reason TEXT;          -- Why it was renamed
ALTER TABLE programs ADD COLUMN in_correct_range INTEGER;    -- 1 if number matches round size range, 0 if not
```

### New Table: program_number_registry

```sql
CREATE TABLE program_number_registry (
    program_number TEXT PRIMARY KEY,
    round_size REAL,
    range_start INTEGER,
    range_end INTEGER,
    status TEXT,                    -- 'AVAILABLE', 'IN_USE', 'RESERVED'
    file_path TEXT,                 -- If in use, which file
    duplicate_count INTEGER,        -- How many files use this number
    last_checked TEXT,              -- Last registry update timestamp
    notes TEXT
);
```

### New Table: duplicate_resolutions

```sql
CREATE TABLE duplicate_resolutions (
    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resolution_date TEXT,
    duplicate_type TEXT,            -- 'NAME_CONTENT_MISMATCH', 'EXACT_DUPLICATE', 'CONTENT_MATCH_NAME_DIFF'
    program_numbers TEXT,           -- JSON array of involved programs
    action_taken TEXT,              -- 'RENAME', 'DELETE', 'MERGE', 'SKIP'
    files_affected TEXT,            -- JSON array of file paths
    old_values TEXT,                -- JSON of old state
    new_values TEXT,                -- JSON of new state
    user_override INTEGER,          -- 1 if user overrode recommendation
    notes TEXT
);
```

---

## 🔧 Key Functions to Implement

### 1. Round Size Detection

```python
def detect_round_size(program_number):
    """
    Detect round size using multiple methods.
    Returns: (round_size, confidence, source)
    """
    # Method 1: Parse title
    title_match = parse_round_size_from_title(title)
    if title_match:
        return (title_match, 'HIGH', 'TITLE')

    # Method 2: Get from G-code OB
    ob_from_gcode = get_ob_from_gcode(program_number)
    if ob_from_gcode:
        return (ob_from_gcode, 'HIGH', 'GCODE')

    # Method 3: Get from database dimension
    outer_diameter = get_outer_diameter(program_number)
    if outer_diameter:
        return (outer_diameter, 'MEDIUM', 'DIMENSION')

    # Method 4: Manual required
    return (None, 'NONE', 'MANUAL')
```

### 2. Range Validation

```python
def get_range_for_round_size(round_size):
    """Get program number range for a round size"""
    ranges = {
        10.25: (10000, 12999),
        10.50: (10000, 12999),
        13.0:  (13000, 13999),
        5.75:  (50000, 59999),
        6.0:   (60000, 62499),
        6.25:  (62500, 64999),
        # ... etc
    }
    return ranges.get(round_size, None)

def is_in_correct_range(program_number, round_size):
    """Check if program number is in correct range for its round size"""
    prog_num = int(program_number.replace('o', '').replace('O', ''))
    range_start, range_end = get_range_for_round_size(round_size)
    return range_start <= prog_num <= range_end
```

### 3. Excel Registry Management

```python
def generate_program_registry():
    """Generate initial Excel file with all ranges"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active

    # Headers
    ws['A1'] = 'Program Number'
    ws['B1'] = 'Status'
    ws['C1'] = 'File Path 1'
    ws['D1'] = 'Dup Type 1'
    # ... etc

    # Generate all numbers
    row = 2
    for round_size, (start, end) in ranges.items():
        for num in range(start, end + 1):
            ws[f'A{row}'] = f'O{num:05d}'
            ws[f'B{row}'] = 'Available'
            row += 1

    wb.save('program_number_registry.xlsx')

def update_registry_from_database():
    """Sync Excel file with database current state"""
    # Load Excel
    # Query database for all used program numbers
    # Update Status column to "In Use"
    # Add file paths
    # Detect and add duplicates
    # Save Excel
```

### 4. Duplicate Detection Queries

```python
def find_name_content_mismatch():
    """Find same name, different content"""
    query = """
    SELECT program_number,
           GROUP_CONCAT(file_path) as paths,
           COUNT(DISTINCT content_hash) as unique_contents
    FROM (
        SELECT program_number, file_path,
               sha256_hash_of_content as content_hash
        FROM programs
    )
    GROUP BY program_number
    HAVING COUNT(*) > 1
      AND unique_contents > 1
    """
    return execute_query(query)

def find_exact_duplicates():
    """Find same name AND same content"""
    query = """
    SELECT program_number, content_hash,
           COUNT(*) as count,
           GROUP_CONCAT(file_path) as paths
    FROM (
        SELECT program_number, file_path,
               sha256_hash_of_content as content_hash
        FROM programs
    )
    GROUP BY program_number, content_hash
    HAVING count > 1
    """
    return execute_query(query)

def find_content_match_name_diff():
    """Find different name, same content"""
    query = """
    SELECT content_hash,
           COUNT(DISTINCT program_number) as name_count,
           GROUP_CONCAT(DISTINCT program_number) as numbers,
           GROUP_CONCAT(file_path) as paths
    FROM (
        SELECT program_number, file_path,
               sha256_hash_of_content as content_hash
        FROM programs
    )
    GROUP BY content_hash
    HAVING name_count > 1
    """
    return execute_query(query)
```

### 5. Legacy Name Tracking

```python
def rename_with_legacy_tracking(old_number, new_number, reason):
    """Rename program and add legacy tracking"""
    # 1. Read file content
    content = read_file(file_path)

    # 2. Add legacy comment
    legacy_comment = f"""(====================================)
(LEGACY NAME: {old_number})
(RENAMED TO: {new_number})
(DATE: {datetime.now().isoformat()})
(REASON: {reason})
(PREVIOUS PATH: {file_path})
(====================================)
"""
    new_content = legacy_comment + content.replace(old_number, new_number)

    # 3. Write new file
    write_file(new_path, new_content)

    # 4. Update database
    update_database(old_number, new_number, reason)

    # 5. Update Excel registry
    update_excel_registry(old_number, new_number)
```

---

## 🎯 Success Criteria

### After Implementation:

1. ✅ **All programs in correct ranges** - 100% of programs have numbers matching their round size
2. ✅ **Zero name duplicates** - No two files with same program number but different content
3. ✅ **Excel registry accurate** - Registry reflects database state in real-time
4. ✅ **Legacy tracking complete** - All renamed files have legacy comments
5. ✅ **Minimal content duplicates** - Exact duplicates merged/deleted
6. ✅ **Free range usage tracked** - Know when ranges are full and free ranges are used

---

## 📈 Estimated Effort

**Total Time:** 6 weeks (assuming 20-30 hours/week)

**Phase 1:** 5-8 hours
**Phase 2:** 8-12 hours
**Phase 3:** 12-15 hours
**Phase 4:** 8-10 hours
**Phase 5:** 15-20 hours
**Phase 6:** 10-15 hours

**Total:** 58-80 hours

---

## 🚨 Risks & Mitigations

### Risk 1: Renaming breaks machine compatibility
**Mitigation:**
- Test on sample files first
- Keep legacy name in comments
- Maintain undo log
- Backup before batch operations

### Risk 2: Excel file becomes too large
**Mitigation:**
- Use binary Excel format (.xlsx)
- Only load active ranges into memory
- Consider SQLite fallback for lookups

### Risk 3: Round size detection inaccurate
**Mitigation:**
- Multi-method detection with confidence scoring
- Manual override always available
- Preview before committing changes

### Risk 4: Free ranges run out
**Mitigation:**
- Track usage percentage
- Alert when range >90% full
- Suggest range expansion
- Archive old/unused programs

---

## 🎉 Next Steps

### Immediate Actions (This Week):

1. **Review and approve this plan**
2. **Prioritize which duplicate type to tackle first**
3. **Decide on Excel vs database for registry** (Excel for visual, SQLite for performance)
4. **Create test dataset** with known duplicates for testing

### Recommendations:

**Start with:** Phase 2 (Round Size Detection)
- **Why:** Foundation for everything else
- **Effort:** Medium
- **Risk:** Low
- **Value:** High - enables all other features

**Then:** Phase 4 (Exact Duplicates - Type 2)
- **Why:** Easiest to automate, clear rules
- **Effort:** Low-Medium
- **Risk:** Low
- **Value:** High - immediate storage savings

**Then:** Phase 3 (Name/Content Mismatch - Type 1)
- **Why:** Prevents confusion
- **Effort:** Medium-High
- **Risk:** Medium
- **Value:** High - data integrity

**Finally:** Phase 5 (Different Name, Same Content - Type 3)
- **Why:** Most complex, requires similarity detection
- **Effort:** High
- **Risk:** Medium-High
- **Value:** Medium-High - cleanup + optimization

---

*Document Created: 2025-11-26*
*Status: PROPOSED - Awaiting Approval*
