# Version History Comparison Feature

## Overview

Added the ability to compare any program against its historical versions stored in the `program_versions` table. This solves the problem of needing to select 2 files before opening the file comparison tool.

---

## 🎯 What Was Added

### 1. Version History Window
- **Access:** Right-click any program → "View Version History"
- **Shows:** All saved versions of the selected program
- **Columns:** Version, Tag, Date Created, Created By, Change Summary

### 2. Compare to Current
- **Button:** "Compare to Current" in Version History window
- **Action:** Opens file comparison with color highlighting
- **Shows:** Side-by-side diff of selected version vs current file

### 3. Restore Version
- **Button:** "Restore This Version" in Version History window
- **Action:** Restores old version as current file
- **Safety:** Creates backup of current file before restoring

---

## 🔧 How It Works

### Workflow

**Step 1: Open Version History**
```
1. Right-click a program in the results table
2. Select "View Version History" from context menu
3. Version History window opens showing all versions
```

**Step 2: Compare Version**
```
1. Select a version from the list (e.g., v2)
2. Click "Compare to Current"
3. File comparison window opens with:
   - Left pane: Current file
   - Right pane: Selected version (v2)
   - Color highlighting showing differences
```

**Step 3: Restore Version (Optional)**
```
1. Select a version from the list
2. Click "Restore This Version"
3. Confirm the restoration
4. Current file is replaced with selected version
5. Backup of current file is saved as new version
```

---

## 💡 Technical Implementation

### Files Modified: `gcode_database_manager.py`

#### A. Context Menu Addition (Lines 6436-6452)

Added "View Version History" option to right-click menu:

```python
def show_context_menu(self, event):
    """Show right-click context menu"""
    # Select row under mouse
    row_id = self.tree.identify_row(event.y)
    if row_id:
        self.tree.selection_set(row_id)

        menu = tk.Menu(self.root, tearoff=0, bg=self.input_bg, fg=self.fg_color)
        menu.add_command(label="Open File", command=self.open_file)
        menu.add_command(label="Edit Entry", command=self.edit_entry)
        menu.add_command(label="View Details", command=self.view_details)
        menu.add_separator()
        menu.add_command(label="View Version History", command=self.show_version_history_window)
        menu.add_separator()
        menu.add_command(label="Delete Entry", command=self.delete_entry)

        menu.post(event.x_root, event.y_root)
```

#### B. Version History Launch Method (Lines 4709-4732)

Gets program file path and opens version history window:

```python
def show_version_history_window(self):
    """Show version history window for selected program"""
    selected = self.tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a program to view version history")
        return

    program_number = self.tree.item(selected[0])['values'][0]

    # Get file path for the program
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM programs WHERE program_number = ?", (program_number,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        messagebox.showerror("Error", "File path not found for this program.")
        return

    file_path = result[0]

    # Open version history window
    VersionHistoryWindow(self.root, self, program_number, file_path)
```

#### C. VersionHistoryWindow Class (Lines 10421-10674)

Complete window implementation with three main methods:

**1. `load_versions()` - Populate version list:**
```python
def load_versions(self):
    """Load version history into the treeview"""
    # Clear existing items
    for item in self.tree.get_children():
        self.tree.delete(item)

    # Get versions from database
    versions = self.db_manager.get_version_history(self.program_number)

    if not versions:
        self.tree.insert("", tk.END, values=("No versions found", "", "", "", ""))
        return

    # Insert versions into tree
    for version in versions:
        version_id, version_number, version_tag, date_created, created_by, change_summary = version
        # ... format and insert
```

**2. `compare_to_current()` - Compare with current file:**
```python
def compare_to_current(self):
    """Compare selected version to current file"""
    # Get version content from database
    cursor.execute("SELECT file_content FROM program_versions WHERE version_id = ?",
                  (version_id,))
    version_content = cursor.fetchone()[0]

    # Read current file
    with open(self.current_file_path, 'r') as f:
        current_content = f.read()

    # Create comparison data structure
    files_to_compare = [
        (f"{self.program_number} (Current)", current_content),
        (f"{self.program_number} ({version_number})", version_content)
    ]

    # Open file comparison window with color highlighting
    FileComparisonWindow(self.window, self.db_manager, files_to_compare)
```

**3. `restore_version()` - Restore old version:**
```python
def restore_version(self):
    """Restore selected version as current file"""
    # Confirm restoration
    confirm = messagebox.askyesno("Confirm Restore", ...)

    # Get version content from database
    cursor.execute("SELECT file_content FROM program_versions WHERE version_id = ?",
                  (version_id,))
    version_content = cursor.fetchone()[0]

    # Create backup of current file first
    self.db_manager.create_version(self.program_number,
                                  f"Backup before restoring {version_number}")

    # Write restored content to current file
    with open(self.current_file_path, 'w') as f:
        f.write(version_content)

    # Reload versions to show the new backup
    self.load_versions()
```

---

## 🎨 UI Design

### Version History Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                  Version History for O12345                     │
│                                                                 │
│    Select a version and click 'Compare to Current' to see      │
│                        differences                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Version │ Tag    │ Date Created       │ Created By │ Summary   │
├─────────────────────────────────────────────────────────────────┤
│ v5      │ PROD   │ 2025-11-26 14:30  │ JohnW      │ Final rev │
│ v4      │        │ 2025-11-25 10:15  │ JohnW      │ Fix bore  │
│ v3      │ TEST   │ 2025-11-24 16:45  │ BobS       │ Add drill │
│ v2      │        │ 2025-11-20 09:00  │ JohnW      │ Initial   │
│ v1      │        │ 2025-11-15 08:30  │ JohnW      │ Created   │
└─────────────────────────────────────────────────────────────────┘
  [Compare to Current] [Restore This Version]           [Close]
```

---

## 📊 Usage Examples

### Example 1: Compare Current File to v3

**Scenario:** You want to see what changed between v3 and the current file.

**Steps:**
1. Right-click program O12345
2. Select "View Version History"
3. Click on "v3" row
4. Click "Compare to Current"

**Result:**
- File comparison window opens
- Left pane shows current file
- Right pane shows v3
- Orange lines = changed
- Green lines = added since v3
- Red lines = deleted since v3

---

### Example 2: Restore v4 Because v5 Has Errors

**Scenario:** The latest version has a bug, need to revert to v4.

**Steps:**
1. Right-click program O12345
2. Select "View Version History"
3. Click on "v4" row
4. Click "Restore This Version"
5. Confirm restoration

**Result:**
- Current file is backed up as v6 with note "Backup before restoring v4"
- v4 content replaces current file
- Version list refreshes showing v6 at top

---

### Example 3: Review All Changes Since Original

**Scenario:** Want to see how the program evolved from v1.

**Steps:**
1. Right-click program O12345
2. Select "View Version History"
3. Click on "v1" row
4. Click "Compare to Current"

**Result:**
- Side-by-side comparison of v1 vs current
- All cumulative changes highlighted
- Can see full evolution of the program

---

## ✅ Benefits

### No More Multi-File Selection
- **Before:** Had to select 2 programs before opening comparison
- **After:** Right-click → View History → Compare to any version

### Single Program Focus
- Compare program against its own history
- No confusion about which files to select
- Clear version timeline

### Safe Restoration
- Always creates backup before restoring
- Can't lose current work
- Easy to undo if restoration was wrong

### Leverages Existing Features
- Reuses fixed FileComparisonWindow with color highlighting
- Uses existing program_versions table
- Integrates with existing version system

---

## 🔍 Integration with Existing Features

### Uses Existing Database Methods

**From `gcode_database_manager.py`:**

```python
# Get version history (line 840)
def get_version_history(self, program_number):
    """Get all versions of a program"""
    cursor.execute("""
        SELECT version_id, version_number, version_tag, date_created,
               created_by, change_summary
        FROM program_versions
        WHERE program_number = ?
        ORDER BY date_created DESC
    """, (program_number,))
    return cursor.fetchall()

# Create new version (line 752)
def create_version(self, program_number, change_summary=None):
    """Create a new version of a program"""
    # ... creates backup in program_versions table
```

### Uses Fixed File Comparison

**The comparison leverages the recently fixed color highlighting:**

```python
# FileComparisonWindow with working color highlighting
# - Orange background: Changed lines
# - Green background: Added lines
# - Red background: Deleted lines
# - Summary at top: "⚠ X difference(s): Y changed, Z added, W removed"
```

---

## 🎯 Key Features

### 1. Version List Display
- **Shows:** Version number, tag, date, creator, summary
- **Sorted:** Newest first (descending by date)
- **Visual:** Clean table format with columns

### 2. Comparison Integration
- **Fetches:** Version content from database (not file system)
- **Compares:** Against current file on disk
- **Shows:** Color-coded differences using FileComparisonWindow

### 3. Restoration with Safety
- **Backup:** Creates new version before overwriting
- **Confirmation:** Requires user confirmation with warning
- **Reload:** Updates version list after restoration

### 4. Error Handling
- **No versions:** Shows "No versions found" message
- **Missing file:** Error if current file path doesn't exist
- **Missing content:** Error if version content not in database
- **No selection:** Warning if no version selected

---

## 🐛 Edge Cases Handled

### Case 1: Program Has No Versions
- Version list shows "No versions found"
- Compare button disabled (no selection possible)

### Case 2: Current File Deleted/Moved
- Error message: "Current file not found: [path]"
- Comparison cannot proceed
- User must update file_path or restore file

### Case 3: Version Content Missing
- Error: "Version content not found in database"
- Possible if database was corrupted or manually edited
- Cannot compare or restore

### Case 4: Database Lock During Compare
- SQLite connection opens/closes quickly
- Minimal lock time
- Other operations can proceed

---

## 📋 Summary

### What Changed

| Component | Location | Purpose |
|-----------|----------|---------|
| **Context Menu** | Line 6448 | Added "View Version History" option |
| **Launch Method** | Lines 4709-4732 | `show_version_history_window()` method |
| **Version Window** | Lines 10421-10674 | Complete `VersionHistoryWindow` class |

### Files Modified

**gcode_database_manager.py:**
- Context menu: Added version history option
- Launch method: Gets program file path and opens window
- New class: VersionHistoryWindow with compare and restore features

### User Impact

✅ **Easier Workflow** - Right-click → View History → Compare
✅ **Single Program Focus** - Compare against own history, not other files
✅ **Safe Restoration** - Always creates backup before restoring
✅ **Color Highlighting** - Leverages recently fixed comparison tool
✅ **Full Version Timeline** - See all versions in one place

---

## 🎉 Complete!

You can now compare any program against its historical versions without needing to select 2 files first!

**Usage:**
1. **Right-click program** → "View Version History"
2. **Select version** from the list
3. **Click "Compare to Current"** → See color-coded differences
4. **Optional: Click "Restore This Version"** → Revert to old version (with backup)

**Key Benefits:**
- No more multi-file selection confusion
- Compare program against its own history
- Safe restoration with automatic backup
- Leverages existing color highlighting fix

---

*Feature implemented: 2025-11-26*
*Session: Version History Comparison Integration*
