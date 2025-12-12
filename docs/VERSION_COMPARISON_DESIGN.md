# Version History Comparison Feature - Design Document

## 📋 Overview

Add the ability to compare the current version of a file against its older versions stored in the `program_versions` table. This leverages the existing file comparison tool (with color highlighting) to show changes over time.

---

## 🎯 Goals

1. **View Version History** - See all versions of a program
2. **Compare Versions** - Compare any two versions side-by-side
3. **Compare to Current** - Quickly compare any old version to current
4. **Version Timeline** - Visual timeline of changes
5. **Dimension Changes** - Track how dimensions changed over time
6. **Revert Capability** - Ability to restore an old version

---

## 🗄️ Database Schema (Already Exists!)

### **program_versions** table (Lines 376-389):
```sql
CREATE TABLE IF NOT EXISTS program_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_number TEXT NOT NULL,
    version_number TEXT NOT NULL,        -- "1", "2", "3" or "v1.0", "v2.0"
    version_tag TEXT,                     -- "Production", "Testing", "Archived"
    file_content TEXT,                    -- Full G-code content
    file_hash TEXT,                       -- SHA256 hash for integrity
    file_path TEXT,                       -- Path when version created
    date_created TEXT,                    -- ISO timestamp
    created_by TEXT,                      -- Username who created version
    change_summary TEXT,                  -- What was changed
    dimensions_snapshot TEXT,             -- JSON of dimensions at this version
    FOREIGN KEY (program_number) REFERENCES programs(program_number)
)
```

### **programs** table additions:
- `current_version INTEGER DEFAULT 1` - Current version number (already exists, line 339)
- `modified_by TEXT` - Last user who modified (already exists, line 343)

---

## 🎨 UI Design

### **1. Version History Button**

**Location:** Detail view dialog / Context menu

Add a "📜 Version History" button that opens the Version History window.

```python
# In detail view or context menu
tk.Button(frame, text="📜 Version History",
         command=lambda: self.show_version_history(program_number),
         bg=self.button_bg, fg=self.fg_color,
         font=("Arial", 10, "bold"), width=18).pack(...)
```

---

### **2. Version History Window**

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  📜 Version History: o12345                            [X]  │
├─────────────────────────────────────────────────────────────┤
│  Current Program: o12345 - "5.75 Solid Spacer"             │
│  Current Version: v5 (Modified: 2025-11-25 by admin)       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Version List                                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ ☑ v5 (Current) - 2025-11-25 14:30 by admin         │  │
│  │   "Fixed CB dimension from 54 to 60mm"             │  │
│  │   OD: 5.75", Thick: 1.25", CB: 60mm                │  │
│  │   [Compare to Current] [View] [Restore]            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ □ v4 - 2025-11-20 10:15 by john                    │  │
│  │   "Updated material to 6061"                       │  │
│  │   OD: 5.75", Thick: 1.25", CB: 54mm                │  │
│  │   [Compare to Current] [View] [Restore]            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ □ v3 - 2025-11-15 16:45 by admin                   │  │
│  │   "Changed thickness from 1.0 to 1.25"             │  │
│  │   OD: 5.75", Thick: 1.0", CB: 54mm                 │  │
│  │   [Compare to Current] [View] [Restore]            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ □ v2 - 2025-11-10 09:20 by admin                   │  │
│  │   "Initial production version"                     │  │
│  │   OD: 5.75", Thick: 1.0", CB: 54mm                 │  │
│  │   [Compare to Current] [View] [Restore]            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ □ v1 - 2025-11-05 14:00 by admin                   │  │
│  │   "Original program"                               │  │
│  │   OD: 5.75", Thick: 1.0", CB: 54mm                 │  │
│  │   [Compare to Current] [View] [Restore]            │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Actions:                                                   │
│  [📊 Compare Selected] [📋 View Timeline] [Close]         │
└─────────────────────────────────────────────────────────────┘
```

---

### **3. Version Comparison Window**

Use the **existing FileComparisonWindow** class, but populate with version data instead of different files.

**Example:**
```
┌─────────────────────────────────────────────────────────────┐
│  Compare Versions: o12345                             [X]  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┬──────────────────┬──────────────────┐ │
│  │ Version v3       │ Version v4       │ Version v5       │ │
│  │ 2025-11-15       │ 2025-11-20       │ 2025-11-25       │ │
│  │ Status: PASS     │ Status: PASS     │ Status: PASS     │ │
│  ├──────────────────┼──────────────────┼──────────────────┤ │
│  │ OD: 5.75"        │ OD: 5.75"        │ OD: 5.75"        │ │
│  │ Thick: 1.0"      │ Thick: 1.25"     │ Thick: 1.25"     │ │
│  │ CB: 54mm         │ CB: 54mm         │ CB: 60mm         │ │
│  │ Material: 6061   │ Material: 6061   │ Material: 6061   │ │
│  ├──────────────────┼──────────────────┼──────────────────┤ │
│  │ G-Code:          │ G-Code:          │ G-Code:          │ │
│  │ O1234            │ O1234            │ O1234            │ │
│  │ G54              │ G54              │ G54              │ │
│  │ G00 X0 Y0        │ G00 X0 Y0        │ G00 X0 Y0        │ │
│  │ M03 S1000        │ M03 S1000        │ M03 S1200        │ │ ← Orange (changed)
│  │ G01 Z-1.0 F10    │ G01 Z-1.25 F10   │ G01 Z-1.25 F10   │ │ ← Orange (changed)
│  │ M05              │ M05              │ G02 X10 I5       │ │ ← Green (added)
│  │ M30              │ M30              │ M05              │ │
│  │                  │                  │ M30              │ │
│  └──────────────────┴──────────────────┴──────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [Export Comparison] [Print] [Close]                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Plan

### **Phase 1: Basic Version History View**

#### **1. Add "Version History" Button**

**Location:** Add to detail view and results table context menu

```python
def show_version_history(self, program_number):
    """Show version history for a program"""
    VersionHistoryWindow(self.root, program_number, self.db_path,
                        self.bg_color, self.fg_color, self.input_bg,
                        self.button_bg, self.current_username)
```

#### **2. Create VersionHistoryWindow Class**

```python
class VersionHistoryWindow:
    def __init__(self, parent, program_number, db_path, bg_color, fg_color,
                input_bg, button_bg, username):
        self.parent = parent
        self.program_number = program_number
        self.db_path = db_path
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.input_bg = input_bg
        self.button_bg = button_bg
        self.username = username

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Version History: {program_number}")
        self.window.geometry("900x700")
        self.window.configure(bg=bg_color)

        self.load_versions()
        self.setup_ui()

    def load_versions(self):
        """Load all versions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current program info
        cursor.execute("""
            SELECT title, current_version, last_modified, modified_by,
                   file_path, outer_diameter, thickness, center_bore
            FROM programs WHERE program_number = ?
        """, (self.program_number,))
        self.current_program = cursor.fetchone()

        # Get all versions
        cursor.execute("""
            SELECT version_id, version_number, version_tag, date_created,
                   created_by, change_summary, dimensions_snapshot, file_hash
            FROM program_versions
            WHERE program_number = ?
            ORDER BY version_number DESC
        """, (self.program_number,))
        self.versions = cursor.fetchall()

        conn.close()

    def setup_ui(self):
        """Setup the UI"""
        # Header with current program info
        header = tk.Frame(self.window, bg=self.bg_color)
        header.pack(fill=tk.X, padx=10, pady=10)

        title_text = f"📜 Version History: {self.program_number}"
        if self.current_program and self.current_program[0]:
            title_text += f' - "{self.current_program[0]}"'

        tk.Label(header, text=title_text,
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 14, "bold")).pack(anchor='w')

        if self.current_program:
            current_ver = self.current_program[1] or 1
            modified = self.current_program[2] or "Unknown"
            modified_by = self.current_program[3] or "Unknown"

            info_text = f"Current Version: v{current_ver} (Modified: {modified[:16]} by {modified_by})"
            tk.Label(header, text=info_text,
                    bg=self.bg_color, fg=self.fg_color,
                    font=("Arial", 10)).pack(anchor='w', pady=(5, 0))

        # Version list (scrollable)
        list_frame = tk.Frame(self.window, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(list_frame, bg=self.bg_color)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)

        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add current version at top
        self.add_current_version_panel(scrollable_frame)

        # Add historical versions
        for version_data in self.versions:
            self.add_version_panel(scrollable_frame, version_data)

        # Bottom actions
        actions = tk.Frame(self.window, bg=self.bg_color)
        actions.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(actions, text="📊 Compare Selected Versions",
                 command=self.compare_selected,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=25).pack(side=tk.LEFT, padx=5)

        tk.Button(actions, text="📋 View Timeline",
                 command=self.show_timeline,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=18).pack(side=tk.LEFT, padx=5)

        tk.Button(actions, text="Close",
                 command=self.window.destroy,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10), width=12).pack(side=tk.RIGHT, padx=5)

    def add_current_version_panel(self, parent):
        """Add panel for current version"""
        if not self.current_program:
            return

        panel = tk.Frame(parent, bg="#1b5e20", relief=tk.RAISED, borderwidth=2)
        panel.pack(fill=tk.X, pady=5)

        # Header
        header = tk.Frame(panel, bg="#2e7d32")
        header.pack(fill=tk.X, pady=5, padx=5)

        tk.Label(header, text=f"☑ Current Version (v{self.current_program[1] or 1})",
                bg="#2e7d32", fg="white",
                font=("Arial", 11, "bold")).pack(side=tk.LEFT)

        # Info
        info_frame = tk.Frame(panel, bg="#1b5e20")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        modified = self.current_program[2] or "Unknown"
        modified_by = self.current_program[3] or "Unknown"

        tk.Label(info_frame, text=f"Modified: {modified[:16]} by {modified_by}",
                bg="#1b5e20", fg="white",
                font=("Arial", 9)).pack(anchor='w')

        # Dimensions
        od, thick, cb = self.current_program[5:8]
        dims_text = f"OD: {od:.3f}\"" if od else "OD: N/A"
        dims_text += f" | Thick: {thick:.3f}\"" if thick else " | Thick: N/A"
        dims_text += f" | CB: {cb:.1f}mm" if cb else " | CB: N/A"

        tk.Label(info_frame, text=dims_text,
                bg="#1b5e20", fg="white",
                font=("Arial", 9)).pack(anchor='w')

    def add_version_panel(self, parent, version_data):
        """Add panel for a historical version"""
        vid, vnum, vtag, created, created_by, summary, dims_json, fhash = version_data

        panel = tk.Frame(parent, bg=self.input_bg, relief=tk.RAISED, borderwidth=1)
        panel.pack(fill=tk.X, pady=3)

        # Header
        header = tk.Frame(panel, bg="#455a64")
        header.pack(fill=tk.X, pady=3, padx=3)

        version_text = f"□ Version {vnum}"
        if vtag:
            version_text += f" ({vtag})"

        tk.Label(header, text=version_text,
                bg="#455a64", fg="white",
                font=("Arial", 10, "bold")).pack(side=tk.LEFT)

        # Info
        info_frame = tk.Frame(panel, bg=self.input_bg)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(info_frame, text=f"Created: {created[:16]} by {created_by or 'Unknown'}",
                bg=self.input_bg, fg=self.fg_color,
                font=("Arial", 9)).pack(anchor='w')

        if summary:
            tk.Label(info_frame, text=f'"{summary}"',
                    bg=self.input_bg, fg=self.fg_color,
                    font=("Arial", 9, "italic")).pack(anchor='w')

        # Dimensions
        if dims_json:
            import json
            try:
                dims = json.loads(dims_json)
                dims_text = f"OD: {dims.get('outer_diameter', 'N/A')}"
                dims_text += f" | Thick: {dims.get('thickness', 'N/A')}"
                dims_text += f" | CB: {dims.get('center_bore', 'N/A')}"

                tk.Label(info_frame, text=dims_text,
                        bg=self.input_bg, fg=self.fg_color,
                        font=("Arial", 9)).pack(anchor='w')
            except:
                pass

        # Actions
        actions = tk.Frame(panel, bg=self.input_bg)
        actions.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(actions, text="Compare to Current",
                 command=lambda: self.compare_to_current(vid),
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 8), width=18).pack(side=tk.LEFT, padx=2)

        tk.Button(actions, text="View",
                 command=lambda: self.view_version(vid),
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 8), width=10).pack(side=tk.LEFT, padx=2)

        tk.Button(actions, text="Restore",
                 command=lambda: self.restore_version(vid),
                 bg="#ff6b00", fg=self.fg_color,
                 font=("Arial", 8), width=10).pack(side=tk.LEFT, padx=2)

    def compare_to_current(self, version_id):
        """Compare selected version to current version"""
        # Get version content
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT version_number, file_content, dimensions_snapshot,
                   date_created, created_by
            FROM program_versions WHERE version_id = ?
        """, (version_id,))
        old_version = cursor.fetchone()

        # Get current content
        cursor.execute("""
            SELECT file_path, title, outer_diameter, thickness, center_bore,
                   validation_status
            FROM programs WHERE program_number = ?
        """, (self.program_number,))
        current = cursor.fetchone()

        conn.close()

        if not old_version or not current or not current[0]:
            messagebox.showerror("Error", "Could not load version data")
            return

        # Read current file
        try:
            with open(current[0], 'r', encoding='utf-8', errors='ignore') as f:
                current_content = f.read()
        except:
            messagebox.showerror("Error", "Could not read current file")
            return

        # Create comparison data structures
        # Format: (prog_num, title, file_path, spacer_type, od, thickness, cb, ...)

        # Old version data (fake file_path for comparison)
        old_data = (
            f"{self.program_number}_v{old_version[0]}",  # prog_num
            f"Version {old_version[0]}",  # title
            None,  # file_path (will use content directly)
            None, None, None, None, None, None, None, None,  # dims
            "ARCHIVED",  # status
            None, None, None,  # dup info
            old_version[3],  # modified date
            old_version[3]   # created date
        )

        # Current version data
        current_data = (
            self.program_number,
            current[1],  # title
            current[0],  # file_path
            None, current[2], current[3], current[4],  # dims
            None, None, None, None,  # more dims
            current[5],  # status
            None, None, None, None, None  # dup/dates
        )

        # Create temporary FileComparisonWindow with version content
        # This would require modifying FileComparisonWindow to accept
        # content directly instead of only file paths

        messagebox.showinfo("Compare Versions",
            f"Comparing version {old_version[0]} to current version.\n\n"
            "This will open the file comparison window.")

        # TODO: Open FileComparisonWindow with version data

    def view_version(self, version_id):
        """View the content of a specific version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT version_number, file_content, change_summary,
                   date_created, created_by
            FROM program_versions WHERE version_id = ?
        """, (version_id,))
        version = cursor.fetchone()
        conn.close()

        if not version:
            messagebox.showerror("Error", "Version not found")
            return

        # Create viewer window
        viewer = tk.Toplevel(self.window)
        viewer.title(f"View Version {version[0]}: {self.program_number}")
        viewer.geometry("800x600")
        viewer.configure(bg=self.bg_color)

        # Header
        header = tk.Frame(viewer, bg=self.bg_color)
        header.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(header, text=f"Version {version[0]}",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 14, "bold")).pack(anchor='w')

        tk.Label(header, text=f"Created: {version[3]} by {version[4] or 'Unknown'}",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(anchor='w')

        if version[2]:
            tk.Label(header, text=f'"{version[2]}"',
                    bg=self.bg_color, fg=self.fg_color,
                    font=("Arial", 10, "italic")).pack(anchor='w', pady=(5, 0))

        # Content
        content_frame = tk.Frame(viewer, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text = scrolledtext.ScrolledText(content_frame,
                                        bg="#1e1e1e", fg="#d4d4d4",
                                        font=("Courier New", 9),
                                        wrap=tk.NONE)
        text.pack(fill=tk.BOTH, expand=True)

        text.insert("1.0", version[1] or "[No content]")
        text.config(state=tk.DISABLED)

        # Close button
        tk.Button(viewer, text="Close", command=viewer.destroy,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10), width=12).pack(pady=10)

    def restore_version(self, version_id):
        """Restore a previous version as current"""
        response = messagebox.askyesno(
            "Restore Version",
            "This will restore the selected version as the current version.\n\n"
            "The current version will be saved to version history.\n\n"
            "Continue?"
        )

        if not response:
            return

        # TODO: Implement restore logic
        # 1. Create version of current state
        # 2. Load old version content
        # 3. Write to current file
        # 4. Update database
        # 5. Increment current_version

        messagebox.showinfo("Restore Version", "Version restore not yet implemented")

    def compare_selected(self):
        """Compare multiple selected versions"""
        messagebox.showinfo("Compare Selected", "Multi-version comparison not yet implemented")

    def show_timeline(self):
        """Show timeline view of changes"""
        messagebox.showinfo("Timeline View", "Timeline view not yet implemented")
```

---

### **Phase 2: Integration with FileComparisonWindow**

Modify `FileComparisonWindow` to accept content directly:

```python
def __init__(self, parent, files_data, bg_color, fg_color, input_bg,
            button_bg, refresh_callback, manager=None, content_dict=None):
    # ...existing code...

    # NEW: Optional content dictionary
    # {program_number: file_content_string}
    self.content_dict = content_dict or {}
```

Then in `create_file_panel`, check if content exists in dict:

```python
# Load file contents
if prog_num in self.content_dict:
    file_contents[prog_num] = self.content_dict[prog_num]
elif file_path and os.path.exists(file_path):
    # ...existing file reading code...
```

---

### **Phase 3: Auto-Versioning on Changes**

Add automatic version creation when files are modified:

```python
def auto_create_version_if_changed(self, program_number):
    """Auto-create version if file content has changed"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()

    # Get current file hash
    cursor.execute("SELECT file_path FROM programs WHERE program_number = ?",
                  (program_number,))
    result = cursor.fetchone()

    if not result or not result[0] or not os.path.exists(result[0]):
        conn.close()
        return

    file_path = result[0]

    # Calculate current hash
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    import hashlib
    current_hash = hashlib.sha256(content.encode()).hexdigest()

    # Get last version hash
    cursor.execute("""
        SELECT file_hash FROM program_versions
        WHERE program_number = ?
        ORDER BY date_created DESC LIMIT 1
    """, (program_number,))
    last_version = cursor.fetchone()

    conn.close()

    # If hash is different, create new version
    if not last_version or last_version[0] != current_hash:
        self.create_version(program_number, "Auto-save: Content changed")
```

---

## 📋 Feature Checklist

### **Core Features:**
- [ ] Version history button in detail view
- [ ] Version history button in context menu
- [ ] VersionHistoryWindow class
- [ ] List all versions with metadata
- [ ] Show current version at top
- [ ] Compare version to current button
- [ ] View version content button
- [ ] Restore version button
- [ ] Compare multiple versions
- [ ] Timeline view

### **Integration:**
- [ ] Modify FileComparisonWindow to accept content dict
- [ ] Color highlighting for version diffs (already works!)
- [ ] Dimension comparison in versions
- [ ] Auto-versioning on file changes

### **Advanced:**
- [ ] Version tags (Production, Testing, Archived)
- [ ] Version annotations/comments
- [ ] Diff statistics per version
- [ ] Export version history report
- [ ] Rollback multiple versions
- [ ] Branch/merge versions (future)

---

## 🎯 Usage Scenarios

### **Scenario 1: Check What Changed**
1. User notices program o12345 is different
2. Right-click → "Version History"
3. See list of all versions
4. Click "Compare to Current" on v3
5. See exactly what lines changed (color highlighted!)

### **Scenario 2: Rollback Bad Change**
1. Program o12345 causing issues
2. Open version history
3. Find last good version (v4)
4. Click "Restore"
5. Current file reverted to v4 content

### **Scenario 3: Track Dimension Changes**
1. Customer asks "When did CB change from 54 to 60?"
2. Open version history
3. See dimensions in each version
4. v4: CB=54mm, v5: CB=60mm
5. Answer: Changed on 2025-11-25

---

## 🔧 Implementation Effort

### **Time Estimates:**
- **Phase 1 (Basic History View):** 4-6 hours
- **Phase 2 (Comparison Integration):** 2-3 hours
- **Phase 3 (Auto-Versioning):** 2-3 hours
- **Testing & Refinement:** 2-3 hours

**Total:** 10-15 hours of development

---

## ✅ Benefits

1. **Change Tracking** - See exactly what changed and when
2. **Accountability** - Know who made changes
3. **Safety** - Can rollback bad changes
4. **Debugging** - Find when issues were introduced
5. **Audit Trail** - Complete history for quality/compliance
6. **Collaboration** - Multiple users can track changes

---

## 🚀 Next Steps

1. **Implement VersionHistoryWindow** class
2. **Add button to detail view** and context menu
3. **Test with existing program_versions** table
4. **Integrate with FileComparisonWindow**
5. **Add auto-versioning** on file saves
6. **Document** usage for users

---

*Design Date: 2025-11-26*
*Status: Ready for Implementation*
*Estimated Effort: 10-15 hours*
