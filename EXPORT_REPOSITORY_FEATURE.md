# Export Repository by Round Size Feature

## 🎯 Purpose

Export a complete copy of your managed repository, automatically organized into folders by round size. Perfect for:
- Sharing with CNC operators
- Distributing to remote facilities
- Creating backups organized by size
- Sending to customers
- USB drive deployment

---

## 📍 Location

**Repository Tab → Row 4**

Button: **📦 Export Repository by Round Size**

Large green button at the bottom of the repository management section.

---

## 🔧 How It Works

### Step 1: Select Destination

When you click the button, you'll be prompted to select a destination folder where the export will be created.

### Step 2: Automatic Organization

The system:
1. Scans all managed files in your repository
2. Groups them by round size
3. Maps unusual sizes to nearest standard folder
4. Creates organized folder structure
5. Copies all files to appropriate folders

### Step 3: Progress Display

Shows real-time progress:
- Folders being created
- Files being copied
- Count per folder
- Total progress

### Step 4: Completion Summary

Displays:
- Export location
- Number of folders created
- Number of files exported
- Any errors encountered

---

## 📁 Folder Structure

### Standard Folders Created:

```
Export_Folder/
├── 5.75/         (5.75" round size files)
├── 6.0/          (6.0" round size files)
├── 6.25/         (6.25" round size files)
├── 6.5/          (6.5" round size files)
├── 7.0/          (7.0" round size files)
├── 7.5/          (7.5" round size files)
├── 8.0/          (8.0" round size files)
├── 8.5/          (8.5" round size files)
├── 9.5/          (9.5" round size files)
├── 10.25/        (10.25" round size files)
├── 10.5/         (10.5" round size files)
├── 13.0/         (13.0" round size files)
└── NO_ROUND_SIZE/ (files without detected round size)
```

### Example Export:

```
C:\NC_Programs_Export\
├── 5.75/
│   ├── o50000.nc
│   ├── o50001.nc
│   └── o50234.nc  (127 files)
├── 6.25/
│   ├── o62500.nc
│   ├── o62501.nc
│   └── o64999.nc  (852 files)
├── 8.5/
│   ├── o85000.nc
│   ├── o85001.nc
│   └── o89856.nc  (1,243 files)
...
```

---

## 🎯 Special Size Handling

### Standard Sizes (Exact Match)

If a file has one of these exact round sizes, it goes into its own folder:
- 5.75, 6.0, 6.25, 6.5, 7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0

### Unusual Sizes (Nearest Match)

If a file has an unusual round size (e.g., 8.3", 6.1", 10.3"), it's automatically placed in the **nearest** standard folder:

**Examples:**
```
Round Size → Folder
-----------   --------
8.3"       → 8.5/     (nearest to 8.3 is 8.5)
6.1"       → 6.0/     (nearest to 6.1 is 6.0)
10.3"      → 10.25/   (nearest to 10.3 is 10.25)
7.2"       → 7.0/     (nearest to 7.2 is 7.0)
9.7"       → 9.5/     (nearest to 9.7 is 9.5)
```

**Why this approach:**
- No proliferation of special folders
- Easy for operators to find files
- Standard folder structure every time
- Slight size variation is acceptable for grouping

### No Round Size

Files without a detected round size go into:
```
NO_ROUND_SIZE/
```

This folder contains files where the system couldn't determine the round size from the title or G-code.

---

## 🎬 Usage

### Step-by-Step:

1. **Click the Button**
   ```
   Repository tab → Click "📦 Export Repository by Round Size"
   ```

2. **Select Destination**
   ```
   Browse to where you want the export
   Example: C:\NC_Export
   Or: D:\USB_Drive\Programs
   Or: \\NetworkShare\CNC_Programs
   ```

3. **Watch Progress**
   ```
   Progress window shows:
   - Folders being created
   - Files being copied
   - Real-time count
   ```

4. **Review Summary**
   ```
   When complete, shows:
   - Export location
   - Folders created
   - Files exported
   - Any errors
   ```

5. **Done!**
   ```
   Your organized export is ready to use
   ```

---

## 📊 Example Output

### Console Output:

```
Export Destination: C:\NC_Export
================================================================================

Found 3,456 files to export

Organizing files by round size...
================================================================================

EXPORT ORGANIZATION:
================================================================================

📁 5.75/ (127 files)
📁 6.0/ (234 files)
📁 6.25/ (852 files)
📁 6.5/ (156 files)
📁 7.0/ (298 files)
📁 7.5/ (89 files)
📁 8.0/ (445 files)
📁 8.5/ (1243 files)
📁 9.5/ (12 files)
📁 NO_ROUND_SIZE/ (0 files)

================================================================================
Total: 3,456 files in 9 folders

================================================================================
STARTING EXPORT...
================================================================================

📁 Created folder: 5.75/

Exporting to 5.75/:
  ✓ o50000 - o50000.nc
  ✓ o50001 - o50001.nc
  ✓ o50002 - o50002.nc
  ...

📁 Created folder: 6.25/

Exporting to 6.25/:
  ✓ o62500 - o62500.nc
  ✓ o62501 - o62501.nc
  ...

================================================================================
EXPORT COMPLETE
================================================================================

Export Location: C:\NC_Export

Folders Created: 9
Files Exported: 3,456
Errors: 0

Total Size: 9 folders, 3,456 files
```

---

## 🛡️ Safety Features

### 1. Non-Destructive

**Original files are NOT modified or moved:**
- Copies files, doesn't move them
- Your repository stays intact
- Safe to run multiple times
- Export is independent copy

### 2. Handles Missing Files

If a file in the database doesn't exist on disk:
```
⚠️ SKIP: o85000 - File not found
```
Continues with other files, logs the error.

### 3. Error Reporting

Shows errors without stopping:
- File not found
- Permission denied
- Disk full
- Invalid path

Each error is logged, operation continues.

### 4. Preserves Metadata

Uses `shutil.copy2()` which preserves:
- File modification time
- File creation time
- File permissions

---

## 📝 Technical Details

### Function: export_repository_by_round_size()

**Location:** Lines 10999-11219

### Round Size Mapping Logic:

```python
def get_folder_for_round_size(round_size):
    if not round_size:
        return "NO_ROUND_SIZE"

    # Check for exact match
    if round_size in standard_folders:
        return standard_folders[round_size]

    # Find nearest standard size
    nearest = min(standard_folders.keys(), key=lambda x: abs(x - round_size))
    return standard_folders[nearest]
```

**Example:**
```python
get_folder_for_round_size(8.3)
# Returns: "8.5" (nearest to 8.3)

get_folder_for_round_size(6.25)
# Returns: "6.25" (exact match)

get_folder_for_round_size(None)
# Returns: "NO_ROUND_SIZE"
```

### File Copy Operation:

```python
import shutil
shutil.copy2(source_path, dest_path)
# copy2 preserves metadata (timestamps, permissions)
```

### Database Query:

```python
cursor.execute("""
    SELECT program_number, file_path, round_size, title
    FROM programs
    WHERE is_managed = 1
    ORDER BY round_size, program_number
""")
```

Only exports **managed** files (files in the repository), not external scanned files.

---

## 🎯 Use Cases

### Use Case 1: CNC Shop Floor

**Scenario:**
- Need to load programs onto CNC machine control
- USB stick organized by size
- Operator can find programs easily

**Steps:**
1. Export to USB drive
2. Plug into CNC control
3. Navigate to size folder
4. Load program

**Benefit:** Organized by size, easy to navigate

### Use Case 2: Remote Facility

**Scenario:**
- Send programs to remote manufacturing site
- Need complete set organized by size
- Upload to network share

**Steps:**
1. Export to network location
2. Remote facility accesses share
3. Downloads needed sizes
4. Runs programs

**Benefit:** Self-contained, organized export

### Use Case 3: Customer Delivery

**Scenario:**
- Customer ordered spacers in multiple sizes
- Need to provide G-code files
- Email or file transfer

**Steps:**
1. Export to temporary folder
2. Zip the export folder
3. Send to customer
4. Customer has organized programs

**Benefit:** Professional, organized delivery

### Use Case 4: Backup

**Scenario:**
- Create organized backup
- Store on external drive
- Easy to restore specific sizes

**Steps:**
1. Export to backup location
2. Date the export folder
3. Store safely
4. Restore as needed

**Benefit:** Organized backup, easy to browse

---

## 📊 Performance

### Speed:

**Small Repository (100-500 files):**
- Organization: < 1 second
- Copy: 5-10 seconds
- Total: 10-15 seconds

**Medium Repository (500-2,000 files):**
- Organization: 1-2 seconds
- Copy: 15-30 seconds
- Total: 20-40 seconds

**Large Repository (2,000+ files):**
- Organization: 2-5 seconds
- Copy: 30-60 seconds
- Total: 40-80 seconds

### Disk Space:

**Export creates a complete copy:**
- If repository is 500 MB → Export is 500 MB
- No compression
- Exact file copies

**Plan accordingly for:**
- USB drive capacity
- Network transfer time
- Disk space at destination

---

## 💡 Tips & Best Practices

### Tip 1: Export Location

**Good locations:**
```
✓ USB drive: D:\NC_Programs
✓ Network share: \\server\CNC_Programs
✓ Backup drive: E:\Backups\NC_Export_2025-12-03
✓ Temp folder: C:\Temp\Export
```

**Avoid:**
```
✗ Inside repository folder (creates circular reference)
✗ System folders (C:\Windows, C:\Program Files)
```

### Tip 2: Naming Exports

Create dated folders for tracking:
```
C:\Backups\
├── NC_Export_2025-12-03/
├── NC_Export_2025-11-15/
└── NC_Export_2025-10-20/
```

### Tip 3: Verify Before Sending

After export:
1. Browse the folders
2. Check file counts match
3. Spot-check a few files
4. Then send/distribute

### Tip 4: Clean Repository First

**Before exporting:**
1. Run duplicate management
2. Fix out-of-range programs
3. Sync filenames
4. **Then export**

Result: Clean, organized export with correct names.

---

## 🔄 Integration with Workflow

### Complete Workflow:

```
1. Scan Folder
2. Sync Registry
3. Detect Round Sizes
4. Add to Repository
5. Manage Duplicates (3 passes)
6. Batch Rename Out-of-Range
7. Sync Filenames with Database
8. 📦 Export Repository by Round Size ⭐ NEW!
   → Share organized copy with others
9. Done!
```

---

## 📋 Folder Mapping Reference

| Round Size | Folder | Example Files |
|-----------|--------|---------------|
| 5.75" | 5.75/ | o50000-o59999 |
| 6.0" | 6.0/ | o60000-o62499 |
| 6.25" | 6.25/ | o62500-o64999 |
| 6.5" | 6.5/ | o65000-o69999 |
| 7.0" | 7.0/ | o70000-o74999 |
| 7.5" | 7.5/ | o75000-o79000 |
| 8.0" | 8.0/ | o80000-o84999 |
| 8.5" | 8.5/ | o85000-o89999 |
| 9.5" | 9.5/ | o90000-o99999 |
| 10.25" | 10.25/ | o10000-o12999 |
| 10.5" | 10.5/ | o10000-o12999 |
| 13.0" | 13.0/ | o13000-o13999 |
| None | NO_ROUND_SIZE/ | Any without size |

**Note:** Unusual sizes are mapped to nearest folder automatically.

---

## ✅ Success Criteria

After export:

**✓ Organized Structure**
```
All files organized by round size
No scattered files
Clear folder hierarchy
```

**✓ Complete Copy**
```
All managed files exported
File counts match database
No missing files (unless file not found)
```

**✓ Correct Grouping**
```
Each file in appropriate size folder
Unusual sizes mapped to nearest
NO_ROUND_SIZE contains files without size
```

**✓ Ready to Use**
```
Operators can navigate by size
Programs load correctly
Metadata preserved
```

---

## 🎉 Summary

**Purpose:** Export organized copy of repository by round size

**Location:** Repository tab → "📦 Export Repository by Round Size" button

**What it does:**
1. Prompts for destination folder
2. Groups files by round size
3. Creates organized folder structure
4. Copies files to appropriate folders
5. Shows progress and summary

**Folder Structure:**
- Standard folders: 5.75, 6.0, 6.25, 6.5, 7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0
- Special handling: Unusual sizes → nearest folder
- No round size: NO_ROUND_SIZE folder

**When to use:**
- Sharing with CNC operators
- Distributing to facilities
- Customer delivery
- Creating organized backups
- USB drive deployment

**Result:** Clean, organized copy of your repository ready to distribute!

---

*Feature Added: 2025-12-03*
*Function: export_repository_by_round_size() (lines 10999-11219)*
*Button: Repository tab, Row 4*
