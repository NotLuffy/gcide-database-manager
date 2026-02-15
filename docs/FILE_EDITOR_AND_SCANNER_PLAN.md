# File Editor & Scanner - Implementation Plan

## Overview

Add capabilities to scan G-code files for warnings/issues either:
1. **Before import** - Scan external files before adding to database
2. **During editing** - Built-in text editor with real-time warning detection
3. **When duplicating** - Scan and show warnings when creating new program from existing

---

## Current Warning Detection System

### What We Already Have

The application currently detects these issues during import/validation:

1. **Tool Home Issues** (detected in `improved_gcode_parser.py`)
   - Z home position problems
   - Missing tool home commands
   - Incorrect tool home sequences

2. **Bore Warnings** (detected in `gcode_database_manager.py`)
   - Center bore vs program number mismatch
   - CB/OB dimensional conflicts
   - Hub diameter issues

3. **Dimensional Issues**
   - Missing dimensions
   - Inconsistent measurements
   - Invalid values

4. **Validation Issues**
   - G-code syntax errors
   - Missing required commands
   - Sequence problems

### Where Detection Happens

```python
# In improved_gcode_parser.py (lines 800-900)
def validate_tool_homes(self, ...):
    # Detects tool home issues
    # Returns: tool_home_issues string

# In gcode_database_manager.py (lines 8500-8600)
def validate_program_data(self, ...):
    # Comprehensive validation
    # Returns: bore_warnings, dimensional_issues, validation_issues

# In gcode_database_manager.py (lines 9200-9400)
def import_file(self, ...):
    # Calls all validation during import
    # Stores warnings in database
```

---

## Feature 1: Pre-Import File Scanner

### User Story
"I want to scan a G-code file BEFORE importing it to see if there are any warnings or issues, so I can fix them first or decide if I want to import it."

### UI Design

#### Option A: Scan Button in File Dialog
```
┌────────────────────────────────────────────────┐
│ Import G-Code File                              │
├────────────────────────────────────────────────┤
│ Selected: o13002.nc                             │
│                                                 │
│ [Scan for Issues]  [Import]  [Cancel]          │
└────────────────────────────────────────────────┘
```

#### Option B: Right-Click Menu on External Files
```
File Explorer → Right-click on .nc file →
  "Open with G-Code Database Manager"
    → Shows scan results before import dialog
```

#### Option C: Dedicated Scan Window (Recommended)
```
Menu: File → Scan G-Code File...

┌────────────────────────────────────────────────┐
│ G-Code File Scanner                             │
├────────────────────────────────────────────────┤
│ File: [Browse...]                               │
│                                                 │
│ [Scan File]                                     │
│                                                 │
│ Results:                                        │
│ ┌──────────────────────────────────────────┐   │
│ │ ✓ File parsed successfully                │   │
│ │ ✓ Program number: o13002                  │   │
│ │ ✓ Round size detected: 13.0"              │   │
│ │                                            │   │
│ │ ⚠️ WARNINGS (2):                           │   │
│ │   • Tool home Z position: -13.0           │   │
│ │     (Should be -10.0 for 13.0" round)     │   │
│ │   • Missing M09 before M05 at line 245    │   │
│ │                                            │   │
│ │ ✓ Dimensions:                              │   │
│ │   - OD: 13.0                               │   │
│ │   - Thickness: 2.0                         │   │
│ │   - CB: 142mm                              │   │
│ │   - OB: 220mm                              │   │
│ │   - Hub Height: 0.5                        │   │
│ └──────────────────────────────────────────┘   │
│                                                 │
│ [View File]  [Import Anyway]  [Close]          │
└────────────────────────────────────────────────┘
```

### Implementation

#### New Method: `scan_file_for_issues()`

```python
def scan_file_for_issues(self, file_path: str) -> dict:
    """
    Scan a G-code file for issues without importing

    Args:
        file_path: Path to G-code file

    Returns:
        dict with keys:
            - success: bool
            - program_number: str
            - round_size: float
            - dimensions: dict
            - warnings: list of dict
            - errors: list of dict
            - raw_data: ParseResult object
    """
    results = {
        'success': False,
        'program_number': None,
        'round_size': None,
        'dimensions': {},
        'warnings': [],
        'errors': [],
        'raw_data': None
    }

    try:
        # Parse file
        parser = ImprovedGCodeParser()
        parse_result = parser.parse_file(file_path)
        results['raw_data'] = parse_result
        results['success'] = True

        # Extract program number
        prog_match = re.search(r'[oO](\d+)', os.path.basename(file_path))
        if prog_match:
            results['program_number'] = f"o{prog_match.group(1)}"

        # Detect round size
        round_size = self.detect_round_size(
            results['program_number'],
            parse_result
        )
        results['round_size'] = round_size

        # Extract dimensions
        results['dimensions'] = {
            'outer_diameter': parse_result.outer_diameter,
            'thickness': parse_result.thickness,
            'center_bore': parse_result.center_bore,
            'hub_diameter': parse_result.hub_diameter,
            'hub_height': parse_result.hub_height,
        }

        # Check tool home issues
        tool_home_issues = parse_result.tool_home_issues
        if tool_home_issues:
            for issue in tool_home_issues.split(';'):
                if issue.strip():
                    results['warnings'].append({
                        'type': 'tool_home',
                        'severity': 'warning',
                        'message': issue.strip(),
                        'line_number': None  # Could extract from issue text
                    })

        # Check bore warnings
        bore_warnings = self.check_bore_warnings(
            results['program_number'],
            results['dimensions']['center_bore'],
            results['dimensions']['hub_diameter']
        )
        if bore_warnings:
            for warning in bore_warnings.split(';'):
                if warning.strip():
                    results['warnings'].append({
                        'type': 'bore',
                        'severity': 'warning',
                        'message': warning.strip(),
                        'line_number': None
                    })

        # Check for missing dimensions
        for dim_name, dim_value in results['dimensions'].items():
            if dim_value is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'message': f"Missing {dim_name.replace('_', ' ')}",
                    'line_number': None
                })

        # Check G-code syntax
        syntax_errors = self.validate_gcode_syntax(parse_result)
        if syntax_errors:
            results['errors'].extend(syntax_errors)

    except Exception as e:
        results['errors'].append({
            'type': 'parse_error',
            'severity': 'error',
            'message': f"Failed to parse file: {str(e)}",
            'line_number': None
        })

    return results
```

#### New Window: `FileScannerWindow`

```python
class FileScannerWindow:
    """Window for scanning G-code files before import"""

    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        self.window = tk.Toplevel(parent)
        self.window.title("G-Code File Scanner")
        self.window.geometry("700x600")

        self.setup_ui()

    def setup_ui(self):
        # File selection
        file_frame = ttk.Frame(self.window)
        file_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(file_frame, text="File:").pack(side='left')
        self.file_entry = ttk.Entry(file_frame, width=50)
        self.file_entry.pack(side='left', padx=5)
        ttk.Button(file_frame, text="Browse...",
                  command=self.browse_file).pack(side='left')

        # Scan button
        ttk.Button(self.window, text="Scan File",
                  command=self.scan_file).pack(pady=10)

        # Results area
        results_frame = ttk.LabelFrame(self.window, text="Scan Results")
        results_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Scrolled text for results
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            height=20
        )
        self.results_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Configure text tags for colored output
        self.results_text.tag_config('success', foreground='green')
        self.results_text.tag_config('warning', foreground='orange')
        self.results_text.tag_config('error', foreground='red')
        self.results_text.tag_config('info', foreground='blue')
        self.results_text.tag_config('header', font=('TkDefaultFont', 10, 'bold'))

        # Action buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=10)

        self.view_btn = ttk.Button(button_frame, text="View File",
                                   command=self.view_file, state='disabled')
        self.view_btn.pack(side='left', padx=5)

        self.import_btn = ttk.Button(button_frame, text="Import Anyway",
                                     command=self.import_file, state='disabled')
        self.import_btn.pack(side='left', padx=5)

        ttk.Button(button_frame, text="Close",
                  command=self.window.destroy).pack(side='right', padx=5)

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Select G-Code File",
            filetypes=[("G-Code files", "*.nc"), ("All files", "*.*")]
        )
        if filepath:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)

    def scan_file(self):
        filepath = self.file_entry.get()
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("Error", "Please select a valid file")
            return

        # Clear previous results
        self.results_text.delete(1.0, tk.END)

        # Scan file
        results = self.db_manager.scan_file_for_issues(filepath)

        # Display results
        self.display_results(results)

        # Enable action buttons
        if results['success']:
            self.view_btn.config(state='normal')
            self.import_btn.config(state='normal')

    def display_results(self, results):
        """Display scan results with color coding"""
        t = self.results_text

        if results['success']:
            t.insert(tk.END, "✓ ", 'success')
            t.insert(tk.END, "File parsed successfully\n\n")

            # Program info
            t.insert(tk.END, "Program Information:\n", 'header')
            if results['program_number']:
                t.insert(tk.END, f"  Program Number: {results['program_number']}\n")
            if results['round_size']:
                t.insert(tk.END, f"  Round Size: {results['round_size']}\"\n")

            # Dimensions
            t.insert(tk.END, "\nDimensions:\n", 'header')
            dims = results['dimensions']
            for key, value in dims.items():
                display_name = key.replace('_', ' ').title()
                if value is not None:
                    t.insert(tk.END, f"  ✓ {display_name}: {value}\n", 'success')
                else:
                    t.insert(tk.END, f"  ⚠ {display_name}: Not detected\n", 'warning')

            # Warnings
            if results['warnings']:
                t.insert(tk.END, f"\n⚠️ WARNINGS ({len(results['warnings'])}):\n", 'warning')
                for warning in results['warnings']:
                    t.insert(tk.END, f"  • {warning['message']}\n", 'warning')
            else:
                t.insert(tk.END, "\n✓ No warnings found\n", 'success')

            # Errors
            if results['errors']:
                t.insert(tk.END, f"\n❌ ERRORS ({len(results['errors'])}):\n", 'error')
                for error in results['errors']:
                    t.insert(tk.END, f"  • {error['message']}\n", 'error')
        else:
            t.insert(tk.END, "❌ ", 'error')
            t.insert(tk.END, "Failed to parse file\n\n", 'error')
            for error in results['errors']:
                t.insert(tk.END, f"  • {error['message']}\n", 'error')

    def view_file(self):
        """Open file in default text editor or built-in viewer"""
        filepath = self.file_entry.get()
        # TODO: Open in built-in editor (Feature 2)
        os.startfile(filepath)  # Windows
        # Alternative: subprocess.run(['xdg-open', filepath])  # Linux

    def import_file(self):
        """Import file despite warnings"""
        filepath = self.file_entry.get()
        # Call existing import dialog
        self.db_manager.import_single_file(filepath)
        self.window.destroy()
```

#### Menu Integration

```python
# In create_menu_bar() method
file_menu.add_separator()
file_menu.add_command(
    label="🔍 Scan G-Code File...",
    command=self.show_file_scanner,
    accelerator="Ctrl+Shift+S"
)

def show_file_scanner(self):
    """Show file scanner window"""
    scanner = FileScannerWindow(self.root, self)
```

---

## Feature 2: Built-In G-Code Editor with Real-Time Warnings

### User Story
"I want to edit G-code files directly in the application with real-time warning detection, so I can see issues as I type and fix them immediately."

### UI Design

```
Menu: Tools → Edit G-Code File...
or
Right-click program → "Edit G-Code"

┌─────────────────────────────────────────────────────────────┐
│ G-Code Editor - o13002.nc                              [×]   │
├─────────────────────────────────────────────────────────────┤
│ File: [o13002.nc ▼]  [Save] [Save As] [Revert] [Validate]  │
├─────────────────────────────────────────────────────────────┤
│ Line │ Code                                    │ Issues      │
├──────┼─────────────────────────────────────────┼─────────────┤
│   1  │ %                                       │             │
│   2  │ O13002                                  │             │
│   3  │ (13.0 142/220MM 2.0 HC .5)              │             │
│   4  │ G00 G20 G40 G49 G80 G90                 │             │
│   5  │ G54 G91 G28 Z0                          │             │
│   6  │ T1 M06                                  │             │
│   7  │ G00 G90 G54 X0 Y0 S2000 M03             │             │
│   8  │ G43 H01 Z-13.0 M08                      │ ⚠ Z home   │
│   .  │ ...                                     │             │
│ 245  │ M05                                     │ ⚠ M09?     │
│ 246  │ M09                                     │             │
│ 247  │ G91 G28 Z0 M05                          │             │
│ 248  │ M30                                     │             │
│ 249  │ %                                       │             │
├─────────────────────────────────────────────────────────────┤
│ Status: Modified  |  Line: 8  Col: 15  |  2 Warnings       │
├─────────────────────────────────────────────────────────────┤
│ 📋 Issues (2):                                              │
│   ⚠ Line 8: Tool home Z-13.0 (expected Z-10.0 for 13" OD)  │
│   ⚠ Line 245: M09 should come before M05                   │
│                                                             │
│ [Show Details] [Auto-Fix] [Ignore]                         │
└─────────────────────────────────────────────────────────────┘
```

### Features

#### Core Editor Features
- ✅ Syntax highlighting for G-code
- ✅ Line numbers
- ✅ Real-time validation
- ✅ Warning indicators in margin
- ✅ Issues panel at bottom
- ✅ Auto-save option
- ✅ Undo/redo
- ✅ Search and replace
- ✅ Jump to line

#### Real-Time Validation
- Parse on every change (with debouncing)
- Highlight problematic lines
- Show tooltips on hover
- Update issues panel instantly

#### Auto-Fix Suggestions
- Fix tool home Z values
- Fix M09/M05 sequence
- Add missing commands
- One-click fixes

### Implementation

#### Option A: Using tkinter.Text with Extensions

```python
class GCodeEditor:
    """Built-in G-code editor with real-time validation"""

    def __init__(self, parent, db_manager, program_number=None, file_path=None):
        self.parent = parent
        self.db_manager = db_manager
        self.program_number = program_number
        self.file_path = file_path
        self.modified = False

        self.window = tk.Toplevel(parent)
        self.window.title("G-Code Editor")
        self.window.geometry("900x700")

        self.setup_ui()
        self.load_file()

        # Start validation timer
        self.validation_timer = None
        self.text_widget.bind('<<Modified>>', self.on_text_modified)

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill='x', padx=5, pady=5)

        ttk.Label(toolbar, text="File:").pack(side='left')
        self.file_label = ttk.Label(toolbar, text="", font=('TkDefaultFont', 9, 'bold'))
        self.file_label.pack(side='left', padx=5)

        ttk.Button(toolbar, text="💾 Save", command=self.save_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_as).pack(side='left', padx=2)
        ttk.Button(toolbar, text="↺ Revert", command=self.revert_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="✓ Validate", command=self.validate_now).pack(side='left', padx=2)

        # Editor area with line numbers
        editor_frame = ttk.Frame(self.window)
        editor_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Line numbers
        self.line_numbers = tk.Text(
            editor_frame,
            width=6,
            padx=3,
            takefocus=0,
            border=0,
            background='#f0f0f0',
            state='disabled',
            wrap='none'
        )
        self.line_numbers.pack(side='left', fill='y')

        # Warning indicators column
        self.warning_indicators = tk.Text(
            editor_frame,
            width=3,
            padx=3,
            takefocus=0,
            border=0,
            background='#ffffff',
            state='disabled',
            wrap='none'
        )
        self.warning_indicators.pack(side='left', fill='y')

        # Main text editor
        self.text_widget = scrolledtext.ScrolledText(
            editor_frame,
            wrap='none',
            font=('Courier New', 10),
            undo=True,
            maxundo=-1
        )
        self.text_widget.pack(side='left', fill='both', expand=True)

        # Configure syntax highlighting tags
        self.setup_syntax_highlighting()

        # Status bar
        status_frame = ttk.Frame(self.window)
        status_frame.pack(fill='x', padx=5, pady=2)

        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side='left')

        self.position_label = ttk.Label(status_frame, text="Line: 1  Col: 1")
        self.position_label.pack(side='right', padx=10)

        # Issues panel
        issues_frame = ttk.LabelFrame(self.window, text="Issues")
        issues_frame.pack(fill='x', padx=5, pady=5)

        self.issues_text = tk.Text(
            issues_frame,
            height=6,
            wrap=tk.WORD,
            background='#fffef0'
        )
        self.issues_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Configure issue tags
        self.issues_text.tag_config('warning', foreground='orange')
        self.issues_text.tag_config('error', foreground='red')

        # Bind events
        self.text_widget.bind('<KeyRelease>', self.update_line_numbers)
        self.text_widget.bind('<ButtonRelease-1>', self.update_cursor_position)
        self.text_widget.bind('<MouseWheel>', lambda e: self.line_numbers.yview_scroll(int(-1*(e.delta/120)), "units"))

    def setup_syntax_highlighting(self):
        """Configure syntax highlighting tags"""
        # G-codes
        self.text_widget.tag_config('gcode', foreground='blue', font=('Courier New', 10, 'bold'))
        # M-codes
        self.text_widget.tag_config('mcode', foreground='green', font=('Courier New', 10, 'bold'))
        # Coordinates
        self.text_widget.tag_config('coord', foreground='purple')
        # Comments
        self.text_widget.tag_config('comment', foreground='gray', font=('Courier New', 10, 'italic'))
        # Program numbers
        self.text_widget.tag_config('program', foreground='red', font=('Courier New', 10, 'bold'))
        # Warnings
        self.text_widget.tag_config('warning_line', background='#fff3cd')
        # Errors
        self.text_widget.tag_config('error_line', background='#f8d7da')

    def apply_syntax_highlighting(self):
        """Apply syntax highlighting to current text"""
        # Remove old tags
        for tag in ['gcode', 'mcode', 'coord', 'comment', 'program']:
            self.text_widget.tag_remove(tag, '1.0', tk.END)

        content = self.text_widget.get('1.0', tk.END)

        # Highlight G-codes (G00, G01, etc.)
        for match in re.finditer(r'\bG\d+', content, re.IGNORECASE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('gcode', start, end)

        # Highlight M-codes
        for match in re.finditer(r'\bM\d+', content, re.IGNORECASE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('mcode', start, end)

        # Highlight coordinates (X, Y, Z, etc.)
        for match in re.finditer(r'\b[XYZIJKRF]-?\d+\.?\d*', content, re.IGNORECASE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('coord', start, end)

        # Highlight comments
        for match in re.finditer(r'\([^)]*\)', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('comment', start, end)

        # Highlight program numbers
        for match in re.finditer(r'\bO\d+', content, re.IGNORECASE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_widget.tag_add('program', start, end)

    def update_line_numbers(self, event=None):
        """Update line numbers display"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)

        # Get number of lines
        num_lines = int(self.text_widget.index('end-1c').split('.')[0])

        # Add line numbers
        line_numbers_str = '\n'.join(str(i) for i in range(1, num_lines + 1))
        self.line_numbers.insert('1.0', line_numbers_str)

        self.line_numbers.config(state='disabled')

        # Apply syntax highlighting
        self.apply_syntax_highlighting()

    def update_cursor_position(self, event=None):
        """Update cursor position in status bar"""
        cursor_pos = self.text_widget.index(tk.INSERT)
        line, col = cursor_pos.split('.')
        self.position_label.config(text=f"Line: {line}  Col: {int(col)+1}")

    def on_text_modified(self, event=None):
        """Called when text is modified"""
        if self.text_widget.edit_modified():
            self.modified = True
            self.update_title()

            # Schedule validation (debounce)
            if self.validation_timer:
                self.window.after_cancel(self.validation_timer)
            self.validation_timer = self.window.after(1000, self.validate_realtime)

            self.text_widget.edit_modified(False)

    def validate_realtime(self):
        """Perform real-time validation"""
        # Save to temp file
        temp_path = os.path.join(tempfile.gettempdir(), 'gcode_edit_temp.nc')
        content = self.text_widget.get('1.0', 'end-1c')

        with open(temp_path, 'w') as f:
            f.write(content)

        # Scan for issues
        results = self.db_manager.scan_file_for_issues(temp_path)

        # Update UI with issues
        self.display_issues(results)

        # Cleanup
        try:
            os.remove(temp_path)
        except:
            pass

    def display_issues(self, results):
        """Display validation issues"""
        # Clear old indicators
        self.warning_indicators.config(state='normal')
        self.warning_indicators.delete('1.0', tk.END)

        # Clear old highlighting
        self.text_widget.tag_remove('warning_line', '1.0', tk.END)
        self.text_widget.tag_remove('error_line', '1.0', tk.END)

        # Update issues panel
        self.issues_text.delete('1.0', tk.END)

        if not results['warnings'] and not results['errors']:
            self.issues_text.insert('1.0', "✓ No issues found")
            self.status_label.config(text="Ready - No issues")
            self.warning_indicators.config(state='disabled')
            return

        # Show warnings
        num_lines = int(self.text_widget.index('end-1c').split('.')[0])
        indicators = [' '] * num_lines

        for warning in results['warnings']:
            msg = warning['message']
            line_num = warning.get('line_number')

            self.issues_text.insert(tk.END, f"⚠ {msg}\n", 'warning')

            if line_num:
                indicators[line_num - 1] = '⚠'
                # Highlight line
                self.text_widget.tag_add('warning_line',
                                        f"{line_num}.0",
                                        f"{line_num}.end")

        # Show errors
        for error in results['errors']:
            msg = error['message']
            line_num = error.get('line_number')

            self.issues_text.insert(tk.END, f"❌ {msg}\n", 'error')

            if line_num:
                indicators[line_num - 1] = '❌'
                self.text_widget.tag_add('error_line',
                                        f"{line_num}.0",
                                        f"{line_num}.end")

        # Update warning indicators
        self.warning_indicators.insert('1.0', '\n'.join(indicators))
        self.warning_indicators.config(state='disabled')

        # Update status
        warn_count = len(results['warnings'])
        err_count = len(results['errors'])
        self.status_label.config(text=f"{warn_count} warning(s), {err_count} error(s)")

    def validate_now(self):
        """Force immediate validation"""
        if self.validation_timer:
            self.window.after_cancel(self.validation_timer)
        self.validate_realtime()

    def load_file(self):
        """Load file content"""
        if self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                content = f.read()
            self.text_widget.insert('1.0', content)
            self.file_label.config(text=os.path.basename(self.file_path))
            self.update_line_numbers()
            self.validate_now()

    def save_file(self):
        """Save current content"""
        if not self.file_path:
            self.save_as()
            return

        content = self.text_widget.get('1.0', 'end-1c')
        with open(self.file_path, 'w') as f:
            f.write(content)

        self.modified = False
        self.update_title()
        messagebox.showinfo("Saved", f"File saved: {os.path.basename(self.file_path)}")

    def save_as(self):
        """Save with new filename"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".nc",
            filetypes=[("G-Code files", "*.nc"), ("All files", "*.*")]
        )
        if filepath:
            self.file_path = filepath
            self.save_file()

    def update_title(self):
        """Update window title"""
        filename = os.path.basename(self.file_path) if self.file_path else "Untitled"
        modified_marker = "*" if self.modified else ""
        self.window.title(f"G-Code Editor - {filename}{modified_marker}")
```

#### Option B: Using External Editor Library

For more advanced features, consider using:
- **tkinterweb** - Web-based editor in tkinter
- **Scintilla** (via **pyScintilla**) - Professional text editor component
- **PyQt5 QScintilla** - If willing to switch to PyQt

---

## Feature 3: Scan When Duplicating Program

### User Story
"When I duplicate an existing program to create a new one, I want to automatically see any warnings in the source file, so I know if I'm starting from a clean base."

### UI Enhancement

#### Current Duplicate Dialog
```
Right-click program → Duplicate...

┌────────────────────────────────────────────┐
│ Duplicate Program                           │
├────────────────────────────────────────────┤
│ Source: o13002                              │
│ New program number: [o13003___]             │
│                                             │
│ [OK] [Cancel]                               │
└────────────────────────────────────────────┘
```

#### Enhanced Duplicate Dialog
```
Right-click program → Duplicate...

┌────────────────────────────────────────────┐
│ Duplicate Program                           │
├────────────────────────────────────────────┤
│ Source: o13002                              │
│ New program number: [o13003___]             │
│                                             │
│ ⚠️ Source file has warnings:                │
│   • Tool home Z-13.0 (should be Z-10.0)    │
│   • M09 should come before M05             │
│                                             │
│ [ ] Fix warnings in new file               │
│ [ ] Edit new file after creation           │
│                                             │
│ [Scan Source] [OK] [Cancel]                │
└────────────────────────────────────────────┘
```

### Implementation

```python
def duplicate_program_with_scan(self, source_program_number, new_program_number):
    """Duplicate program with warning scan"""

    # Get source file path
    source_file = self.get_program_file_path(source_program_number)

    if not source_file or not os.path.exists(source_file):
        messagebox.showerror("Error", "Source file not found")
        return False

    # Scan source file
    scan_results = self.scan_file_for_issues(source_file)

    # Show results in dialog
    if scan_results['warnings'] or scan_results['errors']:
        dialog = DuplicateWithWarningsDialog(
            self.root,
            source_program_number,
            new_program_number,
            scan_results
        )

        if not dialog.result:
            return False  # User cancelled

        # Get user choices
        fix_warnings = dialog.fix_warnings
        edit_after = dialog.edit_after
    else:
        fix_warnings = False
        edit_after = False

    # Perform duplication
    new_file = self.duplicate_file(source_file, new_program_number)

    # Apply auto-fixes if requested
    if fix_warnings:
        self.auto_fix_warnings(new_file, scan_results)

    # Open in editor if requested
    if edit_after:
        self.open_in_editor(new_file)

    return True


class DuplicateWithWarningsDialog:
    """Dialog for duplicating with warning display"""

    def __init__(self, parent, source_prog, new_prog, scan_results):
        self.result = None
        self.fix_warnings = False
        self.edit_after = False

        self.window = tk.Toplevel(parent)
        self.window.title("Duplicate Program")
        self.window.geometry("500x400")

        # ... (similar to previous dialogs)

        # Warning display
        if scan_results['warnings']:
            warn_frame = ttk.LabelFrame(self.window, text="⚠️ Source File Warnings")
            warn_frame.pack(fill='both', expand=True, padx=10, pady=10)

            warn_text = scrolledtext.ScrolledText(warn_frame, height=6)
            warn_text.pack(fill='both', expand=True, padx=5, pady=5)

            for warning in scan_results['warnings']:
                warn_text.insert(tk.END, f"• {warning['message']}\n")

            warn_text.config(state='disabled')

        # Options
        self.fix_var = tk.BooleanVar(value=False)
        self.edit_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(self.window, text="Fix warnings in new file",
                       variable=self.fix_var).pack(anchor='w', padx=10)
        ttk.Checkbutton(self.window, text="Edit new file after creation",
                       variable=self.edit_var).pack(anchor='w', padx=10)
```

---

## Implementation Priority

### Phase 1: Pre-Import Scanner (Highest Priority)
**Time estimate:** 8-12 hours
**Dependencies:** None
**Value:** High - prevents importing problematic files

**Tasks:**
1. Create `scan_file_for_issues()` method (4 hours)
2. Create `FileScannerWindow` class (4 hours)
3. Add menu integration (1 hour)
4. Testing (2 hours)

### Phase 2: Duplicate with Scan (Medium Priority)
**Time estimate:** 4-6 hours
**Dependencies:** Phase 1
**Value:** Medium - improves workflow

**Tasks:**
1. Enhance duplicate dialog (2 hours)
2. Add auto-fix capability (2 hours)
3. Testing (1 hour)

### Phase 3: Built-In Editor (Lower Priority, High Effort)
**Time estimate:** 20-40 hours
**Dependencies:** Phase 1
**Value:** High but complex

**Tasks:**
1. Create basic editor UI (8 hours)
2. Add syntax highlighting (4 hours)
3. Implement real-time validation (6 hours)
4. Add auto-fix features (4 hours)
5. Add search/replace (2 hours)
6. Testing (4 hours)

---

## Auto-Fix Capabilities

### What Can Be Auto-Fixed?

#### 1. Tool Home Z Position
```python
def fix_tool_home_z(file_path, expected_z):
    """Fix tool home Z position"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Find tool home line
    pattern = r'(G43\s+H\d+\s+Z)(-?\d+\.?\d*)'

    def replace_z(match):
        return f"{match.group(1)}{expected_z}"

    content = re.sub(pattern, replace_z, content)

    with open(file_path, 'w') as f:
        f.write(content)
```

#### 2. M09/M05 Sequence
```python
def fix_coolant_sequence(file_path):
    """Ensure M09 comes before M05"""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    fixed_lines = []
    for i, line in enumerate(lines):
        # If M05 found without M09 before it
        if 'M05' in line and i > 0:
            if 'M09' not in lines[i-1]:
                # Insert M09 before M05
                fixed_lines.append('M09\n')
        fixed_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(fixed_lines)
```

#### 3. Missing Commands
- Add missing G54
- Add missing G91 G28 Z0
- Add missing M30

---

## File Type Support

### Currently Supported
- `.nc` files (G-code)

### Future Support?
- `.txt` files containing G-code
- `.tap` files
- `.cnc` files
- Any text file with G-code content

---

## Configuration Options

### Settings Dialog Addition
```
┌────────────────────────────────────────────┐
│ Editor Settings                             │
├────────────────────────────────────────────┤
│ [✓] Enable real-time validation             │
│ [✓] Auto-scan on duplicate                  │
│ [✓] Syntax highlighting                     │
│ [ ] Auto-fix warnings on save               │
│                                             │
│ Validation delay: [1000] ms                 │
│ Font: [Courier New ▼] Size: [10 ▼]         │
│                                             │
│ [Save] [Cancel]                             │
└────────────────────────────────────────────┘
```

---

## Testing Plan

### Test Cases

#### Pre-Import Scanner
1. Scan file with no issues → Should show all green
2. Scan file with warnings → Should show warnings
3. Scan file with errors → Should show errors
4. Scan non-existent file → Should show error
5. Scan invalid G-code → Should parse what it can

#### Built-In Editor
1. Open file → Should load correctly
2. Edit file → Should mark as modified
3. Save file → Should save changes
4. Type G-code → Should highlight syntax
5. Introduce error → Should show warning in real-time
6. Fix error → Warning should disappear
7. Undo/redo → Should work correctly

#### Duplicate with Scan
1. Duplicate clean file → No warnings shown
2. Duplicate file with warnings → Warnings displayed
3. Choose "Fix warnings" → New file should have fixes
4. Choose "Edit after" → Should open editor

---

## Documentation Needed

### User Documentation
1. "How to Scan Files Before Import" guide
2. "Using the Built-In Editor" guide
3. "Understanding G-Code Warnings" reference
4. "Auto-Fix Features" guide

### Developer Documentation
1. Warning detection system overview
2. Adding new warning types
3. Creating new auto-fix routines
4. Editor extension guide

---

## Summary

### Feature Overview

| Feature | Priority | Effort | Value | Dependencies |
|---------|----------|--------|-------|--------------|
| Pre-Import Scanner | High | 12h | High | None |
| Duplicate with Scan | Medium | 6h | Medium | Scanner |
| Built-In Editor | Medium | 40h | High | Scanner |
| Auto-Fix System | Low | 8h | Medium | Editor |

### Recommended Implementation Order

1. **Week 1-2:** Pre-Import Scanner
   - Most value for least effort
   - Standalone feature
   - Immediate benefit

2. **Week 3:** Duplicate with Scan
   - Builds on scanner
   - Quick to implement
   - Improves workflow

3. **Month 2:** Built-In Editor (if desired)
   - Significant effort
   - High value when complete
   - Consider user demand first

### Total Time Estimate
- **Minimum** (Scanner + Duplicate): 18 hours
- **Full** (All features): 66 hours

---

**Next Steps:**
1. Review this plan
2. Decide which features to implement
3. Confirm priority order
4. Start with Phase 1 (Pre-Import Scanner)?
