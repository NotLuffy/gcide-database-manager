# G-Code Database Manager - Development Setup

## 📦 Files Included

1. **gcode_database_manager.py** - Main application code
2. **GCODE_DATABASE_ARCHITECTURE.md** - Complete architecture and logic documentation
3. **README.md** - This file

## 🚀 Quick Start

### 1. Setup VS Code Project

```bash
# Create project directory
mkdir gcode_database
cd gcode_database

# Copy the Python file
# (Place gcode_database_manager.py here)

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install tkinter  # Usually comes with Python
```

### 2. Run the Application

```bash
python gcode_database_manager.py
```

### 3. First Time Use

1. Click **"📁 Scan Folder"**
2. Navigate to your gcode files directory
3. Wait for parsing to complete
4. Start searching and filtering!

## 📁 Recommended Project Structure

```
gcode_database/
├── gcode_database_manager.py          # Main application (current file)
├── GCODE_DATABASE_ARCHITECTURE.md     # Documentation
├── README.md                          # This file
├── requirements.txt                   # Dependencies
├── gcode_database.db                  # SQLite database (auto-created)
├── gcode_manager_config.json          # Config (auto-created)
└── tests/                             # Unit tests (to be created)
    ├── test_parser.py
    └── test_database.py
```

## 🔧 Next Development Steps

### Step 1: Improve Parsing Logic
Currently, the parser uses generic patterns. You need to:

1. **Share your gcode generator output** - Paste a sample header from a generated file
2. **Update parsing patterns** - Match exact format from your generators
3. **Test with real files** - Run scanner on your actual gcode directory

**Example**: If your generator creates:
```gcode
(WHEEL SPACER - 6.0" x 1.5" CB:56.1mm)
(O06561 - 6061-T6)
; Generated: 2024-10-15
```

Update the `parse_gcode_file()` function to match this exact format.

### Step 2: Test with Real Data

```bash
# In Python
from gcode_database_manager import GCodeParser

parser = GCodeParser()
record = parser.parse_file("/path/to/o00001.nc")

print(f"Program: {record.program_number}")
print(f"Type: {record.spacer_type}")
print(f"OD: {record.outer_diameter}")
print(f"Thickness: {record.thickness}")
print(f"CB: {record.center_bore}")
```

### Step 3: Modularize (Optional)

For better organization, split into modules:

```python
# gui/main_window.py
class GCodeDatabaseGUI:
    # Main window code

# parser/gcode_parser.py  
class GCodeParser:
    # Parsing logic

# database/manager.py
class DatabaseManager:
    # Database operations

# models/program_record.py
@dataclass
class ProgramRecord:
    # Data model
```

### Step 4: Add Unit Tests

```python
# tests/test_parser.py
import unittest
from gcode_database_manager import GCodeParser

class TestParser(unittest.TestCase):
    def test_extract_program_number(self):
        parser = GCodeParser()
        result = parser.extract_program_number("o00001.nc")
        self.assertEqual(result, "o00001")
    
    def test_detect_hub_centric(self):
        header = "(6.0\" x 1.5\" CB:56.1mm HC 0.50\")"
        parser = GCodeParser()
        spacer_type = parser.detect_spacer_type(header, [])
        self.assertEqual(spacer_type, "hub_centric")

if __name__ == '__main__':
    unittest.main()
```

## 🐛 Known Issues & Improvements Needed

### High Priority
- [ ] **Parser accuracy** - Need actual gcode format from your generators
- [ ] **Type detection** - May need refinement based on your file structure
- [ ] **Error handling** - Add more robust error messages

### Medium Priority
- [ ] **Batch operations** - Edit/delete multiple entries
- [ ] **Export formats** - Add PDF catalog generation
- [ ] **Search history** - Remember recent searches

### Low Priority
- [ ] **Dark theme refinement** - Match Breach Tester exactly
- [ ] **Keyboard shortcuts** - Add hotkeys for common actions
- [ ] **Auto-refresh** - Watch folder for new files

## 📝 Key Functions to Understand

### Main Entry Points
```python
# Scan folder and import files
def scan_folder(self):
    # Walk directory, parse each file, insert to database

# Search with filters
def refresh_results(self):
    # Build SQL query, execute, populate table

# Parse individual file
def parse_gcode_file(self, filepath):
    # Extract program number, type, dimensions, metadata
```

### Parser Functions (Need refinement!)
```python
def extract_program_number(self, filename):
    # Currently: regex pattern matching
    # TODO: Match your filename convention

def detect_spacer_type(self, header, lines):
    # Currently: keyword detection
    # TODO: Match your file structure indicators

def extract_dimensions(self, text, patterns):
    # Currently: generic patterns
    # TODO: Match your exact comment format
```

## 🎯 Critical: Share Your Gcode Format!

To make the parser work perfectly, I need a sample of what your generators create:

**Please provide:**
1. First 20 lines of a **standard spacer** file
2. First 20 lines of a **hub-centric spacer** file
3. First 20 lines of a **steel ring** file
4. First 20 lines of a **2-piece** file

**Example format needed:**
```gcode
; ← What does line 1 look like?
; ← What does line 2 look like?
; ← How are dimensions formatted?
; ← How is the program number shown?
...
```

Once I see the actual format, I can update the parser to be 100% accurate!

## 🔍 Debugging Tips

### Enable Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In parse_gcode_file():
logging.debug(f"Parsing: {filepath}")
logging.debug(f"Detected type: {spacer_type}")
logging.debug(f"Found dimensions: {dimensions}")
```

### Test Individual Functions
```python
# Test parsing without GUI
if __name__ == "__main__":
    parser = GCodeParser()
    
    test_file = "/path/to/test_file.nc"
    result = parser.parse_file(test_file)
    
    if result:
        print("✅ Parsed successfully!")
        print(f"  Program: {result.program_number}")
        print(f"  Type: {result.spacer_type}")
        print(f"  Dims: {result.outer_diameter} x {result.thickness}")
    else:
        print("❌ Parsing failed")
```

### Database Inspection
```bash
# View database contents
sqlite3 gcode_database.db

# SQL commands:
.tables                           # Show tables
.schema programs                  # Show structure
SELECT * FROM programs LIMIT 5;   # View sample data
SELECT COUNT(*) FROM programs;    # Count records
```

## 📚 Additional Resources

- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Tkinter Tutorial**: https://docs.python.org/3/library/tkinter.html
- **Regex Testing**: https://regex101.com/

## 🆘 Need Help?

Common issues:

1. **"No module named 'tkinter'"**
   - Windows: Install Python with tcl/tk option
   - Linux: `sudo apt-get install python3-tk`
   - Mac: Should be included

2. **"Database is locked"**
   - Close any other programs accessing the database
   - Check for stale lock files

3. **"Parsing returns None"**
   - File format doesn't match patterns
   - Need to see actual gcode format to fix

4. **"GUI looks different"**
   - Tkinter theming varies by OS
   - Can use ttk.Style for consistency

## ✅ Ready to Develop!

You now have:
- ✅ Working application code
- ✅ Complete architecture documentation
- ✅ Development setup guide
- ✅ Testing strategy
- ✅ Next steps outlined

**Start by running the app, then share your gcode format so we can perfect the parser!**

---

**Questions? Issues? Let me know and we'll refine it together!** 🚀
