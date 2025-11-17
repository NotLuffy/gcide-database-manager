# G-Code Database Manager - Architecture & Logic Documentation

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [Parsing Logic](#parsing-logic)
5. [GUI Architecture](#gui-architecture)
6. [Data Flow](#data-flow)
7. [Key Functions Reference](#key-functions-reference)
8. [Development Roadmap](#development-roadmap)

---

## Overview

### Purpose
Organize and track thousands of CNC lathe gcode files (o00001 - o99999) for wheel spacer manufacturing. Enable quick filtering and searching by part characteristics to find the right program for any customer order.

### Key Requirements
- ✅ Never modify gcode files (read-only)
- ✅ Auto-parse dimensions from file comments
- ✅ Support multiple spacer types
- ✅ Fast filtering by dimensions and characteristics
- ✅ Dark-themed GUI matching existing tools (Breach Tester style)
- ✅ SQLite database for persistence
- ✅ Export capabilities (CSV, reports)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface (Tkinter)              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │   Filters   │  │ Action Buttons│  │ Results Table  │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Application Logic Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ File Scanner │  │ Gcode Parser │  │ DB Manager   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Data Persistence Layer                  │
│  ┌──────────────┐              ┌──────────────────────┐ │
│  │   SQLite DB  │              │  Config JSON Files   │ │
│  │  (programs)  │              │  (settings, prefs)   │ │
│  └──────────────┘              └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Gcode Files (Read-Only)                     │
│         o00001.nc ... o99999.nc                          │
└─────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Main Table: `programs`

```sql
CREATE TABLE programs (
    -- Primary Key
    program_number TEXT PRIMARY KEY,        -- 'o00001' to 'o99999'
    
    -- Type Classification
    spacer_type TEXT NOT NULL,              -- See spacer types below
    
    -- Basic Dimensions (all spacers)
    outer_diameter REAL,                    -- inches
    thickness REAL,                         -- inches
    center_bore REAL,                       -- mm
    
    -- Hub-Centric Specific
    hub_height REAL,                        -- inches (typically 0.50")
    hub_diameter REAL,                      -- mm (hub outer diameter)
    
    -- Steel Ring Specific
    counter_bore_diameter REAL,             -- mm
    counter_bore_depth REAL,                -- inches
    
    -- 2-Piece Specific
    paired_program TEXT,                    -- Reference to other half (e.g., 'o00002')
    
    -- Metadata
    material TEXT,                          -- '6061-T6', 'Steel', 'Stainless'
    notes TEXT,                             -- User notes
    date_created TEXT,                      -- ISO format datetime
    last_modified TEXT,                     -- ISO format datetime
    file_path TEXT                          -- Absolute path to file
);

-- Indexes for fast filtering
CREATE INDEX idx_spacer_type ON programs(spacer_type);
CREATE INDEX idx_outer_diameter ON programs(outer_diameter);
CREATE INDEX idx_thickness ON programs(thickness);
CREATE INDEX idx_center_bore ON programs(center_bore);
CREATE INDEX idx_material ON programs(material);
```

### Spacer Types

```python
SPACER_TYPES = {
    'standard': {
        'description': 'Basic wheel spacer, no protruding hub',
        'required_fields': ['outer_diameter', 'thickness', 'center_bore'],
        'optional_fields': []
    },
    'hub_centric': {
        'description': 'Spacer with protruding hub (typically 0.50" height)',
        'required_fields': ['outer_diameter', 'thickness', 'center_bore', 'hub_height', 'hub_diameter'],
        'optional_fields': []
    },
    'steel_ring': {
        'description': 'Spacer with counter bore for press-fit steel ring',
        'required_fields': ['outer_diameter', 'thickness', 'center_bore', 'counter_bore_diameter', 'counter_bore_depth'],
        'optional_fields': []
    },
    '2pc_part1': {
        'description': '2-piece spacer, first part with counter bore',
        'required_fields': ['outer_diameter', 'thickness', 'center_bore', 'counter_bore_diameter'],
        'optional_fields': ['paired_program']
    },
    '2pc_part2': {
        'description': '2-piece spacer, second part with hub that interlocks',
        'required_fields': ['outer_diameter', 'thickness', 'center_bore', 'hub_diameter'],
        'optional_fields': ['paired_program']
    }
}
```

---

## Parsing Logic

### File Structure Analysis

Based on your gcode generators (standard spacer v6 and hub-centric), the typical file structure is:

```gcode
(PROGRAM HEADER WITH DIMENSIONS)
(PROGRAM NUMBER AND TYPE INFO)
; Material: 6061-T6
; Date: YYYY-MM-DD
; Comments and specs
...
G154 P28              ; Work offset for OP1
T101 (DRILL)          ; Tool callout
...
G154 P29              ; Work offset for OP2
T303 (TURN TOOL)      ; Tool callout
...
M30                   ; Program end
```

### Parsing Strategy

**Phase 1: Extract Header Information (Lines 1-20)**

```python
def parse_gcode_file(filepath):
    """
    Multi-phase parsing strategy
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Phase 1: Extract program number from filename
    program_number = extract_program_number(filename)
    
    # Phase 2: Parse header (first 20 lines)
    header_text = ' '.join(lines[:20])
    
    # Phase 3: Detect spacer type
    spacer_type = detect_spacer_type(header_text, lines)
    
    # Phase 4: Extract dimensions based on type
    dimensions = extract_dimensions(header_text, spacer_type)
    
    # Phase 5: Extract metadata
    metadata = extract_metadata(header_text, lines)
    
    return ProgramRecord(...)
```

### Program Number Extraction

```python
def extract_program_number(filename: str) -> Optional[str]:
    """
    Extract program number from filename
    
    Valid formats:
    - o00001.nc
    - O00001.nc
    - 00001.nc
    - spacer_o00001.nc
    """
    patterns = [
        r'[oO](\d{5})',     # o00001 or O00001
        r'^(\d{5})',        # 00001 at start
        r'_(\d{5})',        # _00001
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return f"o{match.group(1)}"
    
    return None
```

### Spacer Type Detection

```python
def detect_spacer_type(header_text: str, lines: List[str]) -> str:
    """
    Detect spacer type from header and gcode structure
    
    Detection logic:
    1. Look for explicit type keywords in header
    2. Check for hub-specific operations (OP2 facing)
    3. Check for steel ring counter bore operations
    4. Check for paired program references
    5. Default to 'standard'
    """
    header_lower = header_text.lower()
    
    # Explicit markers
    if 'hub centric' in header_lower or 'hc' in header_lower:
        return 'hub_centric'
    
    if 'steel ring' in header_lower or 'sr' in header_lower:
        return 'steel_ring'
    
    if '2pc' in header_lower or '2 pc' in header_lower:
        if 'part1' in header_lower or 'p1' in header_lower:
            return '2pc_part1'
        if 'part2' in header_lower or 'p2' in header_lower:
            return '2pc_part2'
    
    # Structural detection
    full_text = ' '.join(lines)
    
    # Hub-centric: Look for OP2 facing operations
    if has_op2_facing(lines):
        return 'hub_centric'
    
    # Steel ring: Look for counter bore
    if has_counter_bore_operation(lines):
        return 'steel_ring'
    
    return 'standard'

def has_op2_facing(lines: List[str]) -> bool:
    """Check for OP2 facing operations indicating hub machining"""
    in_op2 = False
    for line in lines:
        if 'G154 P29' in line or 'OP2' in line:
            in_op2 = True
        if in_op2 and 'T303' in line:  # Turn tool in OP2
            return True
    return False
```

### Dimension Extraction

```python
def extract_dimensions(header_text: str, spacer_type: str) -> dict:
    """
    Extract dimensions from header comments
    
    Common patterns from your generators:
    - (6.0" x 1.5" CB:56.1mm)
    - (ROUND: 6.0 THICK: 1.5 CB: 56.1)
    - 6.0" Round, 1.5" Thick, 56.1mm CB
    - Hub Height: 0.50", Hub OD: 70mm (for hub_centric)
    """
    dims = {}
    
    # Outer Diameter (inches)
    od_patterns = [
        r'(\d+\.?\d*)\s*(?:"|inch|in)\s*(?:x|round|od|outer)',  # 6.0" x or 6.0" Round
        r'(?:round|od|outer)[:\s]*(\d+\.?\d*)\s*(?:"|in)?',     # Round: 6.0
        r'^\s*\(?\s*(\d+\.?\d*)\s*"',                           # (6.0"
    ]
    dims['outer_diameter'] = extract_first_match(header_text, od_patterns)
    
    # Thickness (inches)
    thick_patterns = [
        r'x\s*(\d+\.?\d*)\s*(?:"|inch|in)',                    # x 1.5"
        r'(?:thick|thickness)[:\s]*(\d+\.?\d*)\s*(?:"|in)?',   # Thick: 1.5
        r'(\d+\.?\d*)\s*(?:"|in)\s+(?:thick|thickness)',       # 1.5" Thick
    ]
    dims['thickness'] = extract_first_match(header_text, thick_patterns)
    
    # Center Bore (mm)
    cb_patterns = [
        r'(?:cb|center bore|bore)[:\s]*(\d+\.?\d*)\s*mm',      # CB: 56.1mm
        r'(\d+\.?\d*)\s*mm\s*(?:cb|bore)',                     # 56.1mm CB
    ]
    dims['center_bore'] = extract_first_match(header_text, cb_patterns)
    
    # Hub dimensions (if hub_centric)
    if spacer_type == 'hub_centric':
        hub_height_patterns = [
            r'(?:hub height|hh)[:\s]*(\d+\.?\d*)\s*(?:"|in)?',
            r'(\d+\.?\d*)\s*(?:"|in)\s*hub',
        ]
        dims['hub_height'] = extract_first_match(header_text, hub_height_patterns)
        
        hub_diameter_patterns = [
            r'(?:hub od|hub dia|hub diameter)[:\s]*(\d+\.?\d*)\s*mm',
            r'hub[:\s]*(\d+\.?\d*)\s*mm',
        ]
        dims['hub_diameter'] = extract_first_match(header_text, hub_diameter_patterns)
    
    # Counter bore (if steel_ring or 2pc_part1)
    if spacer_type in ['steel_ring', '2pc_part1']:
        cb_bore_patterns = [
            r'(?:cb bore|counter bore|counterbore)[:\s]*(\d+\.?\d*)\s*mm',
        ]
        dims['counter_bore_diameter'] = extract_first_match(header_text, cb_bore_patterns)
        
        cb_depth_patterns = [
            r'(?:cb depth|counter bore depth)[:\s]*(\d+\.?\d*)\s*(?:"|in)?',
        ]
        dims['counter_bore_depth'] = extract_first_match(header_text, cb_depth_patterns)
    
    return dims

def extract_first_match(text: str, patterns: List[str]) -> Optional[float]:
    """Try multiple regex patterns and return first match"""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                continue
    return None
```

### Material Detection

```python
def extract_material(header_text: str, lines: List[str]) -> str:
    """
    Extract material type from comments
    
    Look for:
    - ; Material: 6061-T6
    - (6061-T6)
    - Steel
    - Stainless
    """
    full_text = header_text + ' ' + ' '.join(lines[:30])
    full_lower = full_text.lower()
    
    # Check for explicit material callouts
    material_patterns = [
        (r'6061[-\s]?t6', '6061-T6'),
        (r'aluminum|aluminium|alum', '6061-T6'),  # Default aluminum
        (r'stainless\s+steel|stainless|ss', 'Stainless'),
        (r'(?<!stainless\s)steel', 'Steel'),
    ]
    
    for pattern, material in material_patterns:
        if re.search(pattern, full_lower):
            return material
    
    return '6061-T6'  # Default
```

### Paired Program Detection

```python
def detect_paired_program(program_number: str, header_text: str, lines: List[str]) -> Optional[str]:
    """
    For 2-piece spacers, detect the paired program
    
    Look for:
    - (PAIR: o00002)
    - Part 1 of 2 (See o00002)
    - References in comments
    """
    full_text = header_text + ' ' + ' '.join(lines[:30])
    
    # Look for explicit pair reference
    pair_patterns = [
        r'(?:pair|paired)[:\s]*[oO](\d{5})',
        r'see\s+[oO](\d{5})',
        r'part\s+[12]\s+(?:of|/)\s+[12][:\s]*[oO](\d{5})',
    ]
    
    for pattern in pair_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            return f"o{match.group(1)}"
    
    # Infer from program number (convention: consecutive numbers)
    # If this is o00001 (part1), pair is o00002 (part2) and vice versa
    prog_num = int(program_number[1:])  # Remove 'o' prefix
    
    # Check if it's odd (part1) or even (part2)
    if prog_num % 2 == 1:
        return f"o{prog_num + 1:05d}"
    else:
        return f"o{prog_num - 1:05d}"
```

---

## GUI Architecture

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  G-Code Database Manager                   [📁] [➕] [📤]       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─ Search & Filter ─────────────────────────────────────────┐ │
│  │ Program #: [______]  Type: [▼]  Material: [▼]            │ │
│  │ OD: [___] to [___]   Thick: [___] to [___]               │ │
│  │ CB: [___] to [___]                                        │ │
│  │ [🔍 Search]  [🔄 Clear]               Results: 147       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Results ────────────────────────────────────────────────┐  │
│  │ ┌──────┬────────┬─────┬──────┬─────┬──────┬──────────┐  │  │
│  │ │ Prog │  Type  │ OD  │Thick │ CB  │ Mat  │   File   │  │  │
│  │ ├──────┼────────┼─────┼──────┼─────┼──────┼──────────┤  │  │
│  │ │o00001│standard│6.000│0.750 │56.1 │6061-T│spacer.nc │  │  │
│  │ │o00002│hub_cent│6.500│1.000 │66.0 │Steel │hub_sp.nc │  │  │
│  │ │      │        │     │      │     │      │          │  │  │
│  │ └──────┴────────┴─────┴──────┴─────┴──────┴──────────┘  │  │
│  │                                                           │  │
│  │ [📄 Open] [✏️ Edit] [🗑️ Delete] [👁️ View Details]       │  │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```python
class GCodeDatabaseGUI:
    """Main application window"""
    
    def __init__(self, root):
        # Main container
        self.root = root
        
        # Components
        self.top_section = TopActionBar(self)
        self.filter_section = FilterPanel(self)
        self.results_section = ResultsTable(self)
        
        # Database connection
        self.db = DatabaseManager(self.db_path)
        
        # Parser
        self.parser = GCodeParser()

class TopActionBar:
    """Action buttons at top"""
    def __init__(self, parent):
        self.scan_button = Button("📁 Scan Folder")
        self.add_button = Button("➕ Add Entry")
        self.export_button = Button("📤 Export CSV")

class FilterPanel:
    """Search and filter controls"""
    def __init__(self, parent):
        # Filter inputs
        self.program_filter = Entry()
        self.type_filter = Combobox()
        self.material_filter = Combobox()
        
        # Range filters
        self.od_range = RangeFilter("OD")
        self.thickness_range = RangeFilter("Thickness")
        self.cb_range = RangeFilter("CB")
        
        # Actions
        self.search_button = Button("🔍 Search")
        self.clear_button = Button("🔄 Clear")

class ResultsTable:
    """Results display with sortable columns"""
    def __init__(self, parent):
        self.tree = Treeview(columns=COLUMNS)
        self.vsb = Scrollbar(orient="vertical")
        self.hsb = Scrollbar(orient="horizontal")
        
        # Action buttons
        self.open_button = Button("📄 Open")
        self.edit_button = Button("✏️ Edit")
        self.delete_button = Button("🗑️ Delete")
        self.view_button = Button("👁️ View")
```

---

## Data Flow

### 1. Folder Scan Flow

```
User clicks "Scan Folder"
    │
    ▼
Select folder via dialog
    │
    ▼
Walk directory tree, find all .nc/.gcode files
    │
    ▼
For each file:
    │
    ├─ Extract program number from filename
    │
    ├─ Read first 30 lines
    │
    ├─ Detect spacer type
    │
    ├─ Parse dimensions based on type
    │
    ├─ Extract material & metadata
    │
    └─ Create ProgramRecord
    │
    ▼
Check if program_number exists in database
    │
    ├─ If exists: UPDATE record
    │
    └─ If new: INSERT record
    │
    ▼
Display progress (added/updated/errors)
    │
    ▼
Refresh results table
```

### 2. Search/Filter Flow

```
User modifies filter fields
    │
    ▼
User clicks "Search"
    │
    ▼
Build SQL query with WHERE clauses:
    │
    ├─ Program number (LIKE)
    │
    ├─ Type (=)
    │
    ├─ Material (=)
    │
    ├─ OD range (BETWEEN)
    │
    ├─ Thickness range (BETWEEN)
    │
    └─ CB range (BETWEEN)
    │
    ▼
Execute query
    │
    ▼
Populate results table
    │
    ▼
Update result count label
```

### 3. File Open Flow

```
User double-clicks or clicks "Open"
    │
    ▼
Get program_number from selected row
    │
    ▼
Query database for file_path
    │
    ▼
Check if file exists
    │
    ├─ If exists: Open with system default app
    │
    └─ If not found: Show error dialog
```

---

## Key Functions Reference

### Database Operations

```python
class DatabaseManager:
    """Handle all database operations"""
    
    def __init__(self, db_path: str):
        """Initialize database connection"""
        
    def insert_program(self, record: ProgramRecord) -> bool:
        """Insert new program record"""
        
    def update_program(self, record: ProgramRecord) -> bool:
        """Update existing program record"""
        
    def delete_program(self, program_number: str) -> bool:
        """Delete program by number"""
        
    def get_program(self, program_number: str) -> Optional[ProgramRecord]:
        """Get single program by number"""
        
    def search_programs(self, filters: dict) -> List[ProgramRecord]:
        """Search programs with filters"""
        
    def get_all_programs(self) -> List[ProgramRecord]:
        """Get all programs"""
        
    def export_to_csv(self, filepath: str) -> bool:
        """Export all records to CSV"""
```

### Parsing Operations

```python
class GCodeParser:
    """Parse gcode files to extract information"""
    
    def parse_file(self, filepath: str) -> Optional[ProgramRecord]:
        """Main parsing function"""
        
    def extract_program_number(self, filename: str) -> Optional[str]:
        """Extract program number from filename"""
        
    def detect_spacer_type(self, header: str, lines: List[str]) -> str:
        """Detect spacer type from content"""
        
    def extract_dimensions(self, header: str, spacer_type: str) -> dict:
        """Extract dimensions based on type"""
        
    def extract_material(self, content: str) -> str:
        """Extract material type"""
        
    def extract_metadata(self, filepath: str) -> dict:
        """Extract file timestamps and other metadata"""
```

### GUI Operations

```python
class GCodeDatabaseGUI:
    """Main GUI class"""
    
    def scan_folder(self):
        """Scan folder and import files"""
        
    def refresh_results(self):
        """Refresh results table based on filters"""
        
    def clear_filters(self):
        """Clear all filter fields"""
        
    def add_entry(self):
        """Manually add new entry"""
        
    def edit_entry(self):
        """Edit selected entry"""
        
    def delete_entry(self):
        """Delete selected entry"""
        
    def open_file(self):
        """Open selected gcode file"""
        
    def view_details(self):
        """View full details of entry"""
        
    def export_csv(self):
        """Export database to CSV"""
        
    def sort_column(self, col: str):
        """Sort table by column"""
```

---

## Development Roadmap

### Phase 1: Core Functionality (Current)
- ✅ Basic GUI layout
- ✅ Database schema
- ✅ File scanning
- ✅ Basic parsing logic
- ✅ Search/filter
- ✅ CRUD operations

### Phase 2: Enhanced Parsing
- 🔄 Learn from actual gcode generator output format
- 🔄 Improve dimension extraction accuracy
- 🔄 Add support for all spacer type variants
- 🔄 Handle edge cases and malformed files
- 🔄 Add parsing validation

### Phase 3: Advanced Features
- ⏳ Batch operations (bulk edit, delete)
- ⏳ Advanced search (wildcards, regex)
- ⏳ Recent files / favorites
- ⏳ Program history / revisions
- ⏳ Customer/job tracking

### Phase 4: Integration
- ⏳ Link to gcode validator
- ⏳ Link to breach tester
- ⏳ Auto-generate summary sheets
- ⏳ Integration with shop management

### Phase 5: Reporting & Analytics
- ⏳ Generate PDF catalogs
- ⏳ Usage statistics
- ⏳ Dimensional analysis
- ⏳ Material usage reports

---

## Configuration Files

### gcode_manager_config.json

```json
{
  "last_folder": "/path/to/gcode/files",
  "window_geometry": "1600x900",
  "material_list": [
    "6061-T6",
    "Steel",
    "Stainless",
    "Other"
  ],
  "spacer_types": [
    "standard",
    "hub_centric",
    "steel_ring",
    "2pc_part1",
    "2pc_part2"
  ],
  "theme": {
    "bg_color": "#2b2b2b",
    "fg_color": "#ffffff",
    "input_bg": "#3c3c3c",
    "button_bg": "#4a4a4a",
    "accent_color": "#4a90e2"
  },
  "parsing_rules": {
    "tolerance_inches": 0.001,
    "tolerance_mm": 0.05,
    "default_material": "6061-T6",
    "max_header_lines": 30
  }
}
```

---

## Error Handling Strategy

### File Reading Errors

```python
try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    # Try with latin-1 encoding
    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
    except Exception as e:
        log_error(f"Failed to read {filepath}: {e}")
        return None
except FileNotFoundError:
    log_error(f"File not found: {filepath}")
    return None
except PermissionError:
    log_error(f"Permission denied: {filepath}")
    return None
```

### Parsing Errors

```python
def safe_parse(filepath: str) -> Optional[ProgramRecord]:
    """Safely parse file with comprehensive error handling"""
    try:
        record = parse_file(filepath)
        if record is None:
            log_warning(f"Could not extract data from {filepath}")
        return record
    except Exception as e:
        log_error(f"Parsing error in {filepath}: {e}")
        return None
```

### Database Errors

```python
def safe_db_operation(operation: Callable) -> bool:
    """Safely execute database operation"""
    try:
        operation()
        return True
    except sqlite3.IntegrityError as e:
        log_error(f"Database integrity error: {e}")
        return False
    except sqlite3.OperationalError as e:
        log_error(f"Database operation error: {e}")
        return False
    except Exception as e:
        log_error(f"Unexpected database error: {e}")
        return False
```

---

## Testing Strategy

### Unit Tests

```python
# test_parser.py
def test_extract_program_number():
    assert extract_program_number("o00001.nc") == "o00001"
    assert extract_program_number("spacer_o12345.nc") == "o12345"
    assert extract_program_number("invalid.nc") is None

def test_detect_spacer_type():
    header = "(6.0\" x 1.5\" CB:56.1mm HC 0.50\")"
    assert detect_spacer_type(header, []) == "hub_centric"

def test_extract_dimensions():
    header = "(6.0\" x 1.5\" CB:56.1mm)"
    dims = extract_dimensions(header, "standard")
    assert dims['outer_diameter'] == 6.0
    assert dims['thickness'] == 1.5
    assert dims['center_bore'] == 56.1
```

### Integration Tests

```python
# test_database.py
def test_insert_and_retrieve():
    db = DatabaseManager(":memory:")
    record = create_test_record()
    db.insert_program(record)
    retrieved = db.get_program(record.program_number)
    assert retrieved.outer_diameter == record.outer_diameter

def test_search_filters():
    db = DatabaseManager(":memory:")
    # Insert test records
    results = db.search_programs({
        'outer_diameter_min': 5.5,
        'outer_diameter_max': 6.5
    })
    assert len(results) > 0
```

---

## Performance Considerations

### Database Indexing

```sql
-- Create indexes on frequently queried columns
CREATE INDEX idx_spacer_type ON programs(spacer_type);
CREATE INDEX idx_outer_diameter ON programs(outer_diameter);
CREATE INDEX idx_thickness ON programs(thickness);
CREATE INDEX idx_center_bore ON programs(center_bore);
CREATE INDEX idx_material ON programs(material);

-- Composite index for range queries
CREATE INDEX idx_dims_composite ON programs(outer_diameter, thickness, center_bore);
```

### Parsing Optimization

```python
# Only read necessary lines
def fast_parse(filepath: str) -> ProgramRecord:
    """Optimized parsing - only read first 30 lines"""
    with open(filepath, 'r') as f:
        header_lines = [next(f) for _ in range(30)]
    
    # Parse only header, don't process full file
    return parse_header(header_lines)
```

### GUI Performance

```python
# Batch insert for large scans
def batch_scan_folder(folder: str):
    """Scan folder with batch database operations"""
    records = []
    for filepath in find_gcode_files(folder):
        record = parse_file(filepath)
        if record:
            records.append(record)
        
        # Batch insert every 100 records
        if len(records) >= 100:
            db.batch_insert(records)
            records.clear()
    
    # Insert remaining
    if records:
        db.batch_insert(records)
```

---

## Security Considerations

### File System Safety

```python
# Validate file paths
def is_safe_path(filepath: str, base_dir: str) -> bool:
    """Prevent directory traversal attacks"""
    abs_path = os.path.abspath(filepath)
    abs_base = os.path.abspath(base_dir)
    return abs_path.startswith(abs_base)

# Read-only operations
def safe_file_read(filepath: str) -> str:
    """Only read files, never write"""
    if not os.path.exists(filepath):
        raise FileNotFoundError
    
    # Open in read-only mode
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()
```

### SQL Injection Prevention

```python
# Always use parameterized queries
def search_programs(filters: dict) -> List[ProgramRecord]:
    """Safe database queries with parameters"""
    query = "SELECT * FROM programs WHERE 1=1"
    params = []
    
    if 'program_number' in filters:
        query += " AND program_number LIKE ?"
        params.append(f"%{filters['program_number']}%")
    
    # Never use string formatting for queries
    cursor.execute(query, params)
```

---

## Next Steps for VS Code Development

1. **Review this architecture document**
2. **Get sample gcode output** from your generators
3. **Refine parsing logic** based on actual format
4. **Implement unit tests** for parser
5. **Add error handling** for edge cases
6. **Create modular structure**:
   ```
   gcode_database/
   ├── main.py
   ├── gui/
   │   ├── main_window.py
   │   ├── filter_panel.py
   │   └── results_table.py
   ├── database/
   │   ├── manager.py
   │   └── schema.sql
   ├── parser/
   │   ├── gcode_parser.py
   │   ├── patterns.py
   │   └── validators.py
   ├── models/
   │   └── program_record.py
   ├── utils/
   │   ├── logger.py
   │   └── config.py
   └── tests/
       ├── test_parser.py
       └── test_database.py
   ```

---

**Ready to continue development in VS Code!** 🚀
