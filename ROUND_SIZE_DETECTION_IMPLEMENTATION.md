# Round Size Detection - Phase 1 Implementation

## ✅ Completed

Phase 1 of the Program Number Management Plan has been implemented! This provides the foundation for all duplicate resolution and range validation features.

---

## 🗄️ Database Changes

### New Fields Added to `programs` Table

```sql
-- Round size tracking
round_size REAL                    -- Detected round size (e.g., 6.25, 10.5)
round_size_confidence TEXT          -- 'HIGH', 'MEDIUM', 'LOW', 'NONE'
round_size_source TEXT              -- 'TITLE', 'GCODE', 'DIMENSION', 'MANUAL'
in_correct_range INTEGER DEFAULT 1  -- 1 if program number matches round size range
legacy_names TEXT                   -- JSON array of previous program numbers
last_renamed_date TEXT              -- ISO timestamp of last rename
rename_reason TEXT                  -- Why it was renamed
```

### New Tables Created

**1. `program_number_registry`** - Tracks all 97,001 program numbers
```sql
CREATE TABLE program_number_registry (
    program_number TEXT PRIMARY KEY,
    round_size REAL,
    range_start INTEGER,
    range_end INTEGER,
    status TEXT DEFAULT 'AVAILABLE',  -- 'AVAILABLE', 'IN_USE', 'RESERVED'
    file_path TEXT,
    duplicate_count INTEGER DEFAULT 0,
    last_checked TEXT,
    notes TEXT
)
```

**2. `duplicate_resolutions`** - Audit log of duplicate fixes
```sql
CREATE TABLE duplicate_resolutions (
    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resolution_date TEXT,
    duplicate_type TEXT,            -- 'NAME_CONTENT_MISMATCH', etc.
    program_numbers TEXT,           -- JSON array
    action_taken TEXT,              -- 'RENAME', 'DELETE', 'MERGE', 'SKIP'
    files_affected TEXT,            -- JSON array
    old_values TEXT,                -- JSON of old state
    new_values TEXT,                -- JSON of new state
    user_override INTEGER DEFAULT 0,
    notes TEXT
)
```

---

## 🔧 Functions Implemented

### 1. Range Management

**`get_round_size_ranges()`** - Returns all defined ranges
```python
{
    10.25: (10000, 12999, "10.25 & 10.50"),
    10.50: (10000, 12999, "10.25 & 10.50"),
    13.0:  (13000, 13999, "13.0"),
    5.75:  (50000, 59999, "5.75"),
    6.0:   (60000, 62499, "6.0"),
    6.25:  (62500, 64999, "6.25"),
    6.5:   (65000, 69999, "6.5"),
    7.0:   (70000, 74999, "7.0"),
    7.5:   (75000, 79000, "7.5"),
    8.0:   (80000, 84999, "8.0"),
    8.5:   (85000, 89999, "8.5"),
    9.5:   (90000, 99999, "9.5"),
    0.0:   (1000, 9999, "Free Range 1"),
    -1.0:  (14000, 49999, "Free Range 2")
}
```

**`get_range_for_round_size(round_size)`** - Lookup range for a size
- Exact match first
- Fuzzy match with ±0.1 tolerance
- Returns `(start, end)` tuple

### 2. Detection Methods

**`detect_round_size_from_title(title)`** - Parse title for round size
- **Patterns:**
  - "6.25 OD", "10.5 rnd", "7.0 round"
  - Decimal numbers: "6.25", "10.50"
- **Validation:** 5.0 ≤ size ≤ 15.0
- **Returns:** `float` or `None`

**Example:**
```python
detect_round_size_from_title("6.25 OD Spacer CB 54mm")  # → 6.25
detect_round_size_from_title("10.5 rnd solid disc")     # → 10.5
```

**`detect_round_size_from_gcode(program_number)`** - Get from `ob_from_gcode`
- Queries database for `ob_from_gcode` field
- Validates 5.0 ≤ value ≤ 15.0
- **Returns:** `float` or `None`

**`detect_round_size_from_dimension(program_number)`** - Get from `outer_diameter`
- Queries database for `outer_diameter` field
- Validates 5.0 ≤ value ≤ 15.0
- **Returns:** `float` or `None`

### 3. Master Detection

**`detect_round_size(program_number, title=None)`** - Multi-method detection

**Priority Order:**
1. **Title** (if provided) → Confidence: HIGH
2. **G-code OB** → Confidence: HIGH
3. **Database OD** → Confidence: MEDIUM
4. **Manual** required → Confidence: NONE

**Returns:** `(round_size, confidence, source)`

**Example:**
```python
detect_round_size("o62500", "6.25 OD Spacer")
# → (6.25, 'HIGH', 'TITLE')

detect_round_size("o10234")  # Has ob_from_gcode = 10.5
# → (10.5, 'HIGH', 'GCODE')

detect_round_size("o99999")  # No detection possible
# → (None, 'NONE', 'MANUAL')
```

### 4. Validation

**`is_in_correct_range(program_number, round_size)`** - Range validation

**Example:**
```python
is_in_correct_range("o62500", 6.25)   # → True (62500 in 62500-64999)
is_in_correct_range("o12345", 6.25)   # → False (12345 NOT in 62500-64999)
is_in_correct_range("o70123", 7.0)    # → True (70123 in 70000-74999)
```

### 5. Database Updates

**`update_round_size_for_program(program_number, ...)`** - Update single program

**Parameters:**
- `program_number` - Program to update
- `round_size` - Detected or manual size (optional, auto-detects if None)
- `confidence` - 'HIGH', 'MEDIUM', 'LOW', 'NONE'
- `source` - 'TITLE', 'GCODE', 'DIMENSION', 'MANUAL'
- `manual_override` - Set to True for manual entry

**Updates:**
- `round_size`
- `round_size_confidence`
- `round_size_source`
- `in_correct_range` (calculated automatically)

**`batch_detect_round_sizes(program_numbers=None)`** - Batch processing

**Returns:**
```python
{
    'processed': 6213,      # Total programs processed
    'detected': 5847,       # Successfully detected
    'failed': 12,           # Errors
    'manual_needed': 354    # Require manual input
}
```

---

## 📍 Code Locations

**File:** [gcode_database_manager.py](gcode_database_manager.py)

- **Database Fields:** Lines 350-377
- **New Tables:** Lines 484-513
- **Round Size Functions:** Lines 948-1177
  - `get_round_size_ranges()` - Line 950
  - `get_range_for_round_size()` - Line 970
  - `detect_round_size_from_title()` - Line 987
  - `detect_round_size_from_gcode()` - Line 1019
  - `detect_round_size_from_dimension()` - Line 1040
  - `detect_round_size()` - Line 1060
  - `is_in_correct_range()` - Line 1086
  - `update_round_size_for_program()` - Line 1105
  - `batch_detect_round_sizes()` - Line 1136

---

## 🎯 How to Use

### Example 1: Detect Round Size for a Program

```python
# Auto-detect using all methods
round_size, confidence, source = app.detect_round_size("o62500", "6.25 OD Spacer")
print(f"Round Size: {round_size}")        # 6.25
print(f"Confidence: {confidence}")         # HIGH
print(f"Source: {source}")                 # TITLE

# Update database
app.update_round_size_for_program("o62500", round_size, confidence, source)
```

### Example 2: Batch Detect All Programs

```python
# Detect for all programs in database
results = app.batch_detect_round_sizes()

print(f"Processed: {results['processed']}")
print(f"Detected: {results['detected']}")
print(f"Manual needed: {results['manual_needed']}")
```

### Example 3: Check if Program is in Correct Range

```python
# Program o12345 with round size 6.25
is_correct = app.is_in_correct_range("o12345", 6.25)
print(is_correct)  # False (12345 is NOT in 62500-64999 range)

# Should be in 62500-64999 range for 6.25
correct_range = app.get_range_for_round_size(6.25)
print(correct_range)  # (62500, 64999)
```

### Example 4: Manual Round Size Entry

```python
# User manually sets round size
app.update_round_size_for_program(
    program_number="o12345",
    round_size=6.25,
    confidence="HIGH",
    source="MANUAL",
    manual_override=True
)
```

---

## 🧪 Testing

### Test 1: Title Detection
```python
# Should detect from title
test_titles = [
    ("6.25 OD Spacer", 6.25),
    ("10.5 rnd solid", 10.5),
    ("7.0 round disc", 7.0),
    ("625 OD hub", 6.25),  # Should this work? Currently no
]

for title, expected in test_titles:
    result = app.detect_round_size_from_title(title)
    print(f"{title} → {result} (expected: {expected})")
```

### Test 2: Range Validation
```python
# Test range checking
test_cases = [
    ("o62500", 6.25, True),   # Correct
    ("o12345", 6.25, False),  # Wrong range
    ("o70000", 7.0, True),    # Correct
    ("o90000", 9.5, True),    # Correct
]

for prog, size, expected in test_cases:
    result = app.is_in_correct_range(prog, size)
    status = "✓" if result == expected else "✗"
    print(f"{status} {prog} with {size} → {result}")
```

### Test 3: Priority Order
```python
# Test detection priority
# Program with title, gcode, and dimension all set

# Title takes priority
result = app.detect_round_size("o62500", title="6.25 OD")
# Should return ('6.25', 'HIGH', 'TITLE')

# No title → G-code next
result = app.detect_round_size("o62500", title=None)
# Should check ob_from_gcode

# No title, no gcode → dimension
result = app.detect_round_size("o62500", title=None)
# Should check outer_diameter
```

---

## ✅ What This Enables

### Now Available:
1. ✅ **Auto-detect round size** from title, G-code, or dimensions
2. ✅ **Validate program numbers** against round size ranges
3. ✅ **Track detection confidence** to know which need manual review
4. ✅ **Batch process all programs** to populate round size data
5. ✅ **Database foundation** for duplicate resolution (next phase)

### Ready for Next Phase:
- **Type 1 Duplicates** - Can now determine correct range for name conflicts
- **Type 2 Duplicates** - Can validate programs before merging
- **Type 3 Duplicates** - Can keep lowest number in correct range
- **Program Number Registry** - Can populate with current usage
- **Rename with Legacy Tracking** - Database fields ready

---

## 🚀 Next Steps

### Immediate Testing:
1. Run application to create new database fields
2. Run `batch_detect_round_sizes()` on existing programs
3. Check results - how many detected vs manual needed
4. Review programs with `in_correct_range = 0` (wrong range)

### Next Implementation (Phase 2):
**Program Number Registry Population**
- Generate all 97,001 program numbers in registry table
- Mark current database entries as "IN_USE"
- Track duplicates in registry
- Create "Find Next Available" function

### Command to Test:
```python
# After starting application
app = GCodeDatabaseGUI(root)

# Run batch detection
results = app.batch_detect_round_sizes()
print(f"Detection complete: {results}")

# Query programs out of range
conn = sqlite3.connect(app.db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT program_number, round_size, round_size_source, in_correct_range
    FROM programs
    WHERE in_correct_range = 0
    LIMIT 20
""")
out_of_range = cursor.fetchall()
print("Programs in wrong range:")
for prog in out_of_range:
    print(f"  {prog}")
```

---

## 📊 Summary

### Implemented:
- ✅ 7 new database fields
- ✅ 2 new tables (registry + resolutions)
- ✅ 9 new functions for detection and validation
- ✅ Multi-method detection with priority
- ✅ Range validation
- ✅ Batch processing

### Time Spent: ~2 hours

### Lines of Code: ~230 lines

### Next Phase: Registry population + Type 2 duplicate resolution (exact duplicates)

---

*Implemented: 2025-11-26*
*Status: ✅ Phase 1 Complete - Ready for Testing*
