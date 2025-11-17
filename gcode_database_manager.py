import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import sqlite3
import os
import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Tuple, Set
import json
import sys

# Import the improved parser
from improved_gcode_parser import ImprovedGCodeParser, GCodeParseResult


class MultiSelectCombobox(ttk.Frame):
    """Custom multi-select combobox widget"""
    def __init__(self, parent, values, bg_color, fg_color, input_bg, button_bg, width=15):
        super().__init__(parent, style='Dark.TFrame')
        self.values = values
        self.selected = set()
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.input_bg = input_bg
        self.button_bg = button_bg

        # Display label showing selected count
        self.display_label = tk.Label(self, text="All", bg=input_bg, fg=fg_color,
                                     width=width, anchor='w', relief='sunken', cursor='hand2')
        self.display_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.display_label.bind('<Button-1>', self.show_popup)

        self.popup = None

    def show_popup(self, event=None):
        """Show multi-select popup"""
        if self.popup:
            self.popup.destroy()
            self.popup = None
            return

        # Create popup window
        self.popup = tk.Toplevel(self.master)
        self.popup.title("Select Items")
        self.popup.geometry("320x400")
        self.popup.configure(bg=self.bg_color)

        # Position below the button
        x = self.display_label.winfo_rootx()
        y = self.display_label.winfo_rooty() + self.display_label.winfo_height()
        self.popup.geometry(f"+{x}+{y}")

        # Make it a transient window
        self.popup.transient(self.master)
        self.popup.grab_set()

        # Frame for checkboxes
        frame = tk.Frame(self.popup, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add scrollbar
        canvas = tk.Canvas(frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Checkboxes for each value
        self.check_vars = {}
        for value in self.values:
            var = tk.BooleanVar(value=value in self.selected)
            self.check_vars[value] = var

            cb = tk.Checkbutton(scrollable_frame, text=value, variable=var,
                              bg=self.bg_color, fg=self.fg_color,
                              selectcolor=self.input_bg, activebackground=self.bg_color,
                              activeforeground=self.fg_color,
                              font=('Arial', 10), pady=5, padx=5,
                              cursor='hand2')
            cb.pack(anchor='w', pady=3, padx=5, fill=tk.X)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        button_frame = tk.Frame(self.popup, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        btn_all = tk.Button(button_frame, text="Select All", command=self.select_all,
                          bg=self.button_bg, fg=self.fg_color,
                          font=('Arial', 10, 'bold'), width=12, height=2)
        btn_all.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)

        btn_none = tk.Button(button_frame, text="Clear All", command=self.select_none,
                           bg=self.button_bg, fg=self.fg_color,
                           font=('Arial', 10, 'bold'), width=12, height=2)
        btn_none.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)

        btn_apply = tk.Button(button_frame, text="✓ Apply", command=self.apply_selection,
                            bg='#4a90e2', fg=self.fg_color,
                            font=('Arial', 11, 'bold'), width=12, height=2)
        btn_apply.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)

        # Close on click outside (bind to popup destroy)
        self.popup.bind('<FocusOut>', lambda e: self.close_popup())

    def select_all(self):
        """Select all items"""
        for var in self.check_vars.values():
            var.set(True)

    def select_none(self):
        """Clear all selections"""
        for var in self.check_vars.values():
            var.set(False)

    def apply_selection(self):
        """Apply the selection and close popup"""
        self.selected = {value for value, var in self.check_vars.items() if var.get()}
        self.update_display()
        self.close_popup()

    def close_popup(self):
        """Close the popup"""
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def update_display(self):
        """Update the display label"""
        if not self.selected or len(self.selected) == len(self.values):
            self.display_label.config(text="All")
        elif len(self.selected) == 1:
            self.display_label.config(text=list(self.selected)[0])
        else:
            self.display_label.config(text=f"{len(self.selected)} selected")

    def get_selected(self) -> Set[str]:
        """Get selected values"""
        return self.selected if self.selected else set(self.values)

    def clear(self):
        """Clear all selections"""
        self.selected = set()
        self.update_display()


@dataclass
class ProgramRecord:
    """Represents a gcode program record"""
    program_number: str
    spacer_type: str
    outer_diameter: Optional[float]
    thickness: Optional[float]
    thickness_display: Optional[str]  # Display format: "10MM" or "0.75"
    center_bore: Optional[float]
    hub_height: Optional[float]
    hub_diameter: Optional[float]
    counter_bore_diameter: Optional[float]
    counter_bore_depth: Optional[float]
    paired_program: Optional[str]
    material: Optional[str]
    notes: Optional[str]
    date_created: Optional[str]
    last_modified: Optional[str]
    file_path: str
    # Validation fields
    detection_confidence: Optional[str] = None
    detection_method: Optional[str] = None
    validation_status: Optional[str] = None  # 'CRITICAL', 'DIMENSIONAL', 'BORE_WARNING', 'WARNING', 'PASS'
    validation_issues: Optional[str] = None  # JSON list - CRITICAL errors (RED)
    validation_warnings: Optional[str] = None  # JSON list - General warnings (YELLOW)
    bore_warnings: Optional[str] = None  # JSON list - Bore warnings (ORANGE)
    dimensional_issues: Optional[str] = None  # JSON list - P-code/thickness issues (PURPLE)
    cb_from_gcode: Optional[float] = None
    ob_from_gcode: Optional[float] = None

class GCodeDatabaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("G-Code Database Manager - Wheel Spacer Programs")
        self.root.geometry("1600x900")
        
        # Dark mode colors
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.input_bg = "#3c3c3c"
        self.button_bg = "#4a4a4a"
        self.accent_color = "#4a90e2"
        
        self.root.configure(bg=self.bg_color)
        
        # Database setup
        self.db_path = "gcode_database.db"
        self.init_database()

        # Configuration
        self.config_file = "gcode_manager_config.json"
        self.load_config()

        # Initialize improved parser
        self.parser = ImprovedGCodeParser()

        # Configure ttk dark theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame', background=self.bg_color)

        # Get available values from database for filters
        self.available_types = self.get_available_values("spacer_type")
        self.available_materials = self.get_available_values("material")
        self.available_statuses = self.get_available_values("validation_status")

        # Build GUI
        self.setup_gui()
        self.refresh_results()
        
    def init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                program_number TEXT PRIMARY KEY,
                spacer_type TEXT NOT NULL,
                outer_diameter REAL,
                thickness REAL,
                thickness_display TEXT,
                center_bore REAL,
                hub_height REAL,
                hub_diameter REAL,
                counter_bore_diameter REAL,
                counter_bore_depth REAL,
                paired_program TEXT,
                material TEXT,
                notes TEXT,
                date_created TEXT,
                last_modified TEXT,
                file_path TEXT,
                detection_confidence TEXT,
                detection_method TEXT,
                validation_status TEXT,
                validation_issues TEXT,
                validation_warnings TEXT,
                bore_warnings TEXT,
                dimensional_issues TEXT,
                cb_from_gcode REAL,
                ob_from_gcode REAL
            )
        ''')

        # Upgrade existing database if needed
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN detection_confidence TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN detection_method TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN validation_status TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN validation_issues TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN validation_warnings TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN cb_from_gcode REAL")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN ob_from_gcode REAL")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN bore_warnings TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN dimensional_issues TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN thickness_display TEXT")
        except:
            pass

        conn.commit()
        conn.close()
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "last_folder": "",
            "material_list": ["6061-T6", "Steel", "Stainless", "Other"],
            "spacer_types": ["standard", "hub_centric", "steel_ring", "2pc_part1", "2pc_part2"]
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = default_config
        else:
            self.config = default_config
            
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_available_values(self, column: str) -> List[str]:
        """Get distinct values from database column for filter dropdowns"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT {column} FROM programs WHERE {column} IS NOT NULL ORDER BY {column}")
            values = [row[0] for row in cursor.fetchall()]
            conn.close()
            return values
        except:
            return []
            
    def setup_gui(self):
        """Setup the main GUI"""
        # Create main container
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section - Actions and Import
        top_frame = tk.Frame(main_container, bg=self.bg_color)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_top_section(top_frame)
        
        # Middle section - Filters
        filter_frame = tk.LabelFrame(main_container, text="Search & Filter", 
                                     bg=self.bg_color, fg=self.fg_color,
                                     font=("Arial", 10, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_filter_section(filter_frame)
        
        # Bottom section - Results
        results_frame = tk.LabelFrame(main_container, text="Results", 
                                      bg=self.bg_color, fg=self.fg_color,
                                      font=("Arial", 10, "bold"))
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.create_results_section(results_frame)
        
    def create_top_section(self, parent):
        """Create top action buttons"""
        # Title
        title = tk.Label(parent, text="G-Code Database Manager", 
                        font=("Arial", 16, "bold"), 
                        bg=self.bg_color, fg=self.fg_color)
        title.pack(side=tk.LEFT, padx=10)
        
        # Buttons on the right
        button_frame = tk.Frame(parent, bg=self.bg_color)
        button_frame.pack(side=tk.RIGHT)
        
        btn_scan = tk.Button(button_frame, text="📁 Scan Folder", 
                            command=self.scan_folder,
                            bg=self.button_bg, fg=self.fg_color,
                            font=("Arial", 10, "bold"), width=15, height=2)
        btn_scan.pack(side=tk.LEFT, padx=5)
        
        btn_add = tk.Button(button_frame, text="➕ Add Entry", 
                           command=self.add_entry,
                           bg=self.button_bg, fg=self.fg_color,
                           font=("Arial", 10, "bold"), width=15, height=2)
        btn_add.pack(side=tk.LEFT, padx=5)
        
        btn_export = tk.Button(button_frame, text="📤 Export CSV",
                              command=self.export_csv,
                              bg=self.button_bg, fg=self.fg_color,
                              font=("Arial", 10, "bold"), width=15, height=2)
        btn_export.pack(side=tk.LEFT, padx=5)

        btn_help = tk.Button(button_frame, text="❓ Help/Legend",
                            command=self.show_legend,
                            bg=self.button_bg, fg=self.fg_color,
                            font=("Arial", 10, "bold"), width=15, height=2)
        btn_help.pack(side=tk.LEFT, padx=5)
        
    def create_filter_section(self, parent):
        """Create filter controls"""
        filter_container = tk.Frame(parent, bg=self.bg_color)
        filter_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Row 1
        row1 = tk.Frame(filter_container, bg=self.bg_color)
        row1.pack(fill=tk.X, pady=5)
        
        # Program Number
        tk.Label(row1, text="Program #:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        self.filter_program = tk.Entry(row1, bg=self.input_bg, fg=self.fg_color, width=15)
        self.filter_program.pack(side=tk.LEFT, padx=5)
        
        # Spacer Type
        tk.Label(row1, text="Type:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        type_values = self.available_types if self.available_types else self.config["spacer_types"]
        self.filter_type = MultiSelectCombobox(row1, type_values, self.bg_color, self.fg_color,
                                              self.input_bg, self.button_bg, width=15)
        self.filter_type.pack(side=tk.LEFT, padx=5)

        # Material
        tk.Label(row1, text="Material:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        material_values = self.available_materials if self.available_materials else self.config["material_list"]
        self.filter_material = MultiSelectCombobox(row1, material_values, self.bg_color, self.fg_color,
                                                  self.input_bg, self.button_bg, width=15)
        self.filter_material.pack(side=tk.LEFT, padx=5)

        # Validation Status
        tk.Label(row1, text="Status:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        status_values = self.available_statuses if self.available_statuses else ["CRITICAL", "BORE_WARNING", "DIMENSIONAL", "WARNING", "PASS"]
        self.filter_status = MultiSelectCombobox(row1, status_values, self.bg_color, self.fg_color,
                                                self.input_bg, self.button_bg, width=15)
        self.filter_status.pack(side=tk.LEFT, padx=5)
        
        # Row 2 - Dimensional filters
        row2 = tk.Frame(filter_container, bg=self.bg_color)
        row2.pack(fill=tk.X, pady=5)
        
        # Outer Diameter
        tk.Label(row2, text="OD Range:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        self.filter_od_min = tk.Entry(row2, bg=self.input_bg, fg=self.fg_color, width=10)
        self.filter_od_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_od_max = tk.Entry(row2, bg=self.input_bg, fg=self.fg_color, width=10)
        self.filter_od_max.pack(side=tk.LEFT, padx=2)
        
        # Thickness
        tk.Label(row2, text="Thick:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        self.filter_thickness_min = tk.Entry(row2, bg=self.input_bg, fg=self.fg_color, width=10)
        self.filter_thickness_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_thickness_max = tk.Entry(row2, bg=self.input_bg, fg=self.fg_color, width=10)
        self.filter_thickness_max.pack(side=tk.LEFT, padx=2)
        
        # Center Bore
        tk.Label(row2, text="CB:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        self.filter_cb_min = tk.Entry(row2, bg=self.input_bg, fg=self.fg_color, width=10)
        self.filter_cb_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_cb_max = tk.Entry(row2, bg=self.input_bg, fg=self.fg_color, width=10)
        self.filter_cb_max.pack(side=tk.LEFT, padx=2)
        
        # Row 3 - Action buttons
        row3 = tk.Frame(filter_container, bg=self.bg_color)
        row3.pack(fill=tk.X, pady=5)
        
        btn_search = tk.Button(row3, text="🔍 Search", command=self.refresh_results,
                              bg=self.accent_color, fg=self.fg_color,
                              font=("Arial", 10, "bold"), width=12, height=1)
        btn_search.pack(side=tk.LEFT, padx=5)
        
        btn_clear = tk.Button(row3, text="🔄 Clear Filters", command=self.clear_filters,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"), width=12, height=1)
        btn_clear.pack(side=tk.LEFT, padx=5)
        
        # Results count label
        self.results_label = tk.Label(row3, text="", bg=self.bg_color, fg=self.fg_color,
                                     font=("Arial", 10))
        self.results_label.pack(side=tk.RIGHT, padx=10)
        
    def create_results_section(self, parent):
        """Create results table"""
        # Create treeview with scrollbars
        tree_frame = tk.Frame(parent, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        columns = ("Program #", "Type", "OD", "Thick", "CB", "Hub H", "Hub D",
                  "CB Bore", "Material", "Status", "File")

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Configure tags for color coding (severity-based)
        self.tree.tag_configure('critical', background='#4d1f1f', foreground='#ff6b6b')     # RED - Critical errors
        self.tree.tag_configure('bore_warning', background='#4d3520', foreground='#ffa500') # ORANGE - Bore warnings
        self.tree.tag_configure('dimensional', background='#3d1f4d', foreground='#da77f2')  # PURPLE - P-code/thickness
        self.tree.tag_configure('warning', background='#4d3d1f', foreground='#ffd43b')      # YELLOW - General warnings
        self.tree.tag_configure('pass', background='#1f4d2e', foreground='#69db7c')         # GREEN - Pass
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        column_widths = {
            "Program #": 100,
            "Type": 120,
            "OD": 80,
            "Thick": 80,
            "CB": 80,
            "Hub H": 80,
            "Hub D": 80,
            "CB Bore": 80,
            "Material": 100,
            "Status": 90,
            "File": 200
        }
        
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=column_widths[col], anchor="center")
        
        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.open_file)
        
        # Bottom action buttons
        action_frame = tk.Frame(parent, bg=self.bg_color)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        btn_open = tk.Button(action_frame, text="📄 Open File", command=self.open_file,
                            bg=self.button_bg, fg=self.fg_color,
                            font=("Arial", 9), width=12)
        btn_open.pack(side=tk.LEFT, padx=5)
        
        btn_edit = tk.Button(action_frame, text="✏️ Edit Entry", command=self.edit_entry,
                            bg=self.button_bg, fg=self.fg_color,
                            font=("Arial", 9), width=12)
        btn_edit.pack(side=tk.LEFT, padx=5)
        
        btn_delete = tk.Button(action_frame, text="🗑️ Delete Entry", command=self.delete_entry,
                              bg=self.button_bg, fg=self.fg_color,
                              font=("Arial", 9), width=12)
        btn_delete.pack(side=tk.LEFT, padx=5)
        
        btn_view = tk.Button(action_frame, text="👁️ View Details", command=self.view_details,
                            bg=self.button_bg, fg=self.fg_color,
                            font=("Arial", 9), width=12)
        btn_view.pack(side=tk.LEFT, padx=5)
        
    def parse_gcode_file(self, filepath: str) -> Optional[ProgramRecord]:
        """Parse a gcode file using the improved parser"""
        try:
            # Use improved parser
            result = self.parser.parse_file(filepath)
            if not result:
                return None

            # Determine validation status (prioritized by severity)
            validation_status = "PASS"
            if result.validation_issues:
                validation_status = "CRITICAL"  # RED - Critical errors
            elif result.bore_warnings:
                validation_status = "BORE_WARNING"  # ORANGE - Bore dimension warnings
            elif result.dimensional_issues:
                validation_status = "DIMENSIONAL"  # PURPLE - P-code/thickness mismatches
            elif result.validation_warnings:
                validation_status = "WARNING"  # YELLOW - General warnings

            # Convert to ProgramRecord
            return ProgramRecord(
                program_number=result.program_number,
                spacer_type=result.spacer_type,
                outer_diameter=result.outer_diameter,
                thickness=result.thickness,
                thickness_display=result.thickness_display,
                center_bore=result.center_bore,
                hub_height=result.hub_height,
                hub_diameter=result.hub_diameter,
                counter_bore_diameter=result.counter_bore_diameter,
                counter_bore_depth=result.counter_bore_depth,
                paired_program=None,
                material=result.material,
                notes=None,
                date_created=result.date_created,
                last_modified=result.last_modified,
                file_path=result.file_path,
                detection_confidence=result.detection_confidence,
                detection_method=result.detection_method,
                validation_status=validation_status,
                validation_issues=json.dumps(result.validation_issues) if result.validation_issues else None,
                validation_warnings=json.dumps(result.validation_warnings) if result.validation_warnings else None,
                bore_warnings=json.dumps(result.bore_warnings) if result.bore_warnings else None,
                dimensional_issues=json.dumps(result.dimensional_issues) if result.dimensional_issues else None,
                cb_from_gcode=result.cb_from_gcode,
                ob_from_gcode=result.ob_from_gcode
            )

        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def extract_dimension(self, text: str, patterns: List[str]) -> Optional[float]:
        """Extract dimension using multiple regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        return None
        
    def scan_folder(self):
        """Scan a folder for gcode files and import them"""
        folder = filedialog.askdirectory(title="Select Folder with G-Code Files",
                                        initialdir=self.config.get("last_folder", ""))
        
        if not folder:
            return
            
        self.config["last_folder"] = folder
        self.save_config()
        
        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Scanning Files...")
        progress_window.geometry("400x200")
        progress_window.configure(bg=self.bg_color)
        
        progress_label = tk.Label(progress_window, text="Scanning...", 
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)
        
        progress_text = scrolledtext.ScrolledText(progress_window, 
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 width=50, height=8)
        progress_text.pack(padx=10, pady=10)
        
        self.root.update()
        
        # Scan for gcode files (with or without extension)
        gcode_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                # Match files with extensions OR files matching o##### pattern
                if (file.lower().endswith(('.nc', '.gcode', '.cnc')) and re.search(r'[oO]\d{4,6}', file)) or \
                   (re.match(r'^[oO]\d{4,6}$', file)):
                    gcode_files.append(os.path.join(root, file))
        
        progress_label.config(text=f"Found {len(gcode_files)} files. Processing...")
        self.root.update()
        
        # Process files
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        added = 0
        updated = 0
        errors = 0
        
        for filepath in gcode_files:
            filename = os.path.basename(filepath)
            progress_text.insert(tk.END, f"Processing: {filename}\n")
            progress_text.see(tk.END)
            self.root.update()
            
            record = self.parse_gcode_file(filepath)
            
            if record:
                try:
                    # Check if exists
                    cursor.execute("SELECT program_number FROM programs WHERE program_number = ?", 
                                 (record.program_number,))
                    exists = cursor.fetchone()
                    
                    if exists:
                        # Update existing
                        cursor.execute('''
                            UPDATE programs SET
                                spacer_type = ?, outer_diameter = ?, thickness = ?, thickness_display = ?,
                                center_bore = ?, hub_height = ?, hub_diameter = ?,
                                counter_bore_diameter = ?, counter_bore_depth = ?,
                                material = ?, last_modified = ?, file_path = ?,
                                detection_confidence = ?, detection_method = ?,
                                validation_status = ?, validation_issues = ?,
                                validation_warnings = ?, bore_warnings = ?, dimensional_issues = ?,
                                cb_from_gcode = ?, ob_from_gcode = ?
                            WHERE program_number = ?
                        ''', (record.spacer_type, record.outer_diameter, record.thickness, record.thickness_display,
                             record.center_bore, record.hub_height, record.hub_diameter,
                             record.counter_bore_diameter, record.counter_bore_depth,
                             record.material, record.last_modified, record.file_path,
                             record.detection_confidence, record.detection_method,
                             record.validation_status, record.validation_issues,
                             record.validation_warnings, record.bore_warnings, record.dimensional_issues,
                             record.cb_from_gcode, record.ob_from_gcode,
                             record.program_number))
                        updated += 1
                    else:
                        # Insert new
                        cursor.execute('''
                            INSERT INTO programs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (record.program_number, record.spacer_type, record.outer_diameter,
                             record.thickness, record.thickness_display, record.center_bore, record.hub_height,
                             record.hub_diameter, record.counter_bore_diameter,
                             record.counter_bore_depth, record.paired_program,
                             record.material, record.notes, record.date_created,
                             record.last_modified, record.file_path, record.detection_confidence,
                             record.detection_method, record.validation_status,
                             record.validation_issues, record.validation_warnings,
                             record.bore_warnings, record.dimensional_issues,
                             record.cb_from_gcode, record.ob_from_gcode))
                        added += 1
                        
                except Exception as e:
                    errors += 1
                    progress_text.insert(tk.END, f"  DATABASE ERROR: {str(e)[:100]}\n")
                    progress_text.see(tk.END)
            else:
                errors += 1
                progress_text.insert(tk.END, f"  PARSE ERROR: Could not extract data\n")
                progress_text.see(tk.END)
        
        conn.commit()
        conn.close()
        
        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"\n{'='*50}\n")
        progress_text.insert(tk.END, f"Added: {added}\n")
        progress_text.insert(tk.END, f"Updated: {updated}\n")
        progress_text.insert(tk.END, f"Errors: {errors}\n")
        progress_text.see(tk.END)
        
        close_btn = tk.Button(progress_window, text="Close", 
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

        # Refresh filter dropdowns with new values
        self.refresh_filter_values()
        self.refresh_results()
        
    def refresh_filter_values(self):
        """Refresh available filter values from database"""
        # Update available values from database
        new_types = self.get_available_values("spacer_type")
        new_materials = self.get_available_values("material")
        new_statuses = self.get_available_values("validation_status")

        # Update filter widgets if values changed
        if new_types != self.available_types:
            self.available_types = new_types
            self.filter_type.values = new_types
            self.filter_type.clear()

        if new_materials != self.available_materials:
            self.available_materials = new_materials
            self.filter_material.values = new_materials
            self.filter_material.clear()

        if new_statuses != self.available_statuses:
            self.available_statuses = new_statuses
            self.filter_status.values = new_statuses
            self.filter_status.clear()

    def refresh_results(self):
        """Refresh the results table based on current filters"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Build query
        query = "SELECT * FROM programs WHERE 1=1"
        params = []
        
        # Program number filter
        if self.filter_program.get():
            query += " AND program_number LIKE ?"
            params.append(f"%{self.filter_program.get()}%")
        
        # Type filter (multi-select)
        selected_types = self.filter_type.get_selected()
        if selected_types and len(selected_types) < len(self.filter_type.values):
            placeholders = ','.join('?' * len(selected_types))
            query += f" AND spacer_type IN ({placeholders})"
            params.extend(selected_types)

        # Material filter (multi-select)
        selected_materials = self.filter_material.get_selected()
        if selected_materials and len(selected_materials) < len(self.filter_material.values):
            placeholders = ','.join('?' * len(selected_materials))
            query += f" AND material IN ({placeholders})"
            params.extend(selected_materials)

        # Validation Status filter (multi-select)
        selected_statuses = self.filter_status.get_selected()
        if selected_statuses and len(selected_statuses) < len(self.filter_status.values):
            placeholders = ','.join('?' * len(selected_statuses))
            query += f" AND validation_status IN ({placeholders})"
            params.extend(selected_statuses)

        # OD range
        if self.filter_od_min.get():
            query += " AND outer_diameter >= ?"
            params.append(float(self.filter_od_min.get()))
        if self.filter_od_max.get():
            query += " AND outer_diameter <= ?"
            params.append(float(self.filter_od_max.get()))
        
        # Thickness range
        if self.filter_thickness_min.get():
            query += " AND thickness >= ?"
            params.append(float(self.filter_thickness_min.get()))
        if self.filter_thickness_max.get():
            query += " AND thickness <= ?"
            params.append(float(self.filter_thickness_max.get()))
        
        # CB range
        if self.filter_cb_min.get():
            query += " AND center_bore >= ?"
            params.append(float(self.filter_cb_min.get()))
        if self.filter_cb_max.get():
            query += " AND center_bore <= ?"
            params.append(float(self.filter_cb_max.get()))
        
        query += " ORDER BY program_number"
        
        # Execute query
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        # Populate tree
        # Column indices (based on database schema):
        # 0:program_number, 1:spacer_type, 2:outer_diameter, 3:thickness, 4:thickness_display,
        # 5:center_bore, 6:hub_height, 7:hub_diameter, 8:counter_bore_diameter, 9:counter_bore_depth,
        # 10:paired_program, 11:material, 12:notes, 13:date_created, 14:last_modified, 15:file_path,
        # 16:detection_confidence, 17:detection_method, 18:validation_status, ...

        for row in results:
            program_number = row[0]
            spacer_type = row[1]
            od = f"{row[2]:.3f}" if row[2] else "-"

            # Use thickness_display (row[4]) if available, otherwise fall back to formatted thickness (row[3])
            thick = row[4] if row[4] else (f"{row[3]:.3f}" if row[3] else "-")

            cb = f"{row[5]:.1f}" if row[5] else "-"

            # Hub Height - only applicable for hub_centric
            if spacer_type == 'hub_centric':
                hub_h = f"{row[6]:.2f}" if row[6] else "-"
            else:
                hub_h = "N/A"

            # Hub Diameter (OB) - only applicable for hub_centric
            if spacer_type == 'hub_centric':
                hub_d = f"{row[7]:.1f}" if row[7] else "-"
            else:
                hub_d = "N/A"

            # Counter Bore - only applicable for STEP parts
            if spacer_type == 'step':
                cb_bore = f"{row[8]:.1f}" if row[8] else "-"
            else:
                cb_bore = "N/A"

            material = row[11] if row[11] else "-"
            filename = os.path.basename(row[15]) if row[15] else "-"

            # Validation status (index 18 - validation_status)
            validation_status = row[18] if len(row) > 18 and row[18] else "N/A"

            # Determine color tag (prioritized by severity)
            tag = ''
            if validation_status == 'CRITICAL':
                tag = 'critical'  # RED - Critical errors (CB/OB way off)
            elif validation_status == 'BORE_WARNING':
                tag = 'bore_warning'  # ORANGE - Bore dimensions at tolerance limit
            elif validation_status == 'DIMENSIONAL':
                tag = 'dimensional'  # PURPLE - P-code/thickness mismatches
            elif validation_status == 'WARNING':
                tag = 'warning'  # YELLOW - General warnings
            elif validation_status == 'PASS':
                tag = 'pass'  # GREEN - Pass
            # Old status names for backward compatibility
            elif validation_status == 'ERROR':
                tag = 'critical'

            self.tree.insert("", "end", values=(
                program_number, spacer_type, od, thick, cb,
                hub_h, hub_d, cb_bore, material, validation_status, filename
            ), tags=(tag,))
        
        # Update count
        self.results_label.config(text=f"Results: {len(results)} programs")
        
    def clear_filters(self):
        """Clear all filter fields"""
        self.filter_program.delete(0, tk.END)
        self.filter_type.clear()
        self.filter_material.clear()
        self.filter_status.clear()
        self.filter_od_min.delete(0, tk.END)
        self.filter_od_max.delete(0, tk.END)
        self.filter_thickness_min.delete(0, tk.END)
        self.filter_thickness_max.delete(0, tk.END)
        self.filter_cb_min.delete(0, tk.END)
        self.filter_cb_max.delete(0, tk.END)
        self.refresh_results()
        
    def sort_column(self, col):
        """Sort treeview by column"""
        # Get data
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        
        # Sort
        try:
            # Try numeric sort
            data.sort(key=lambda t: float(t[0].replace("-", "0")))
        except:
            # Fall back to string sort
            data.sort()
        
        # Rearrange
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
            
    def open_file(self, event=None):
        """Open selected gcode file"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a program to open")
            return
        
        program_number = self.tree.item(selected[0])['values'][0]
        
        # Get file path from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM programs WHERE program_number = ?", (program_number,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            filepath = result[0]
            if os.path.exists(filepath):
                # Open with default application
                if os.name == 'nt':  # Windows
                    os.startfile(filepath)
                elif os.name == 'posix':  # Mac/Linux
                    os.system(f'open "{filepath}"' if sys.platform == 'darwin' else f'xdg-open "{filepath}"')
            else:
                messagebox.showerror("File Not Found", f"File not found:\n{filepath}")
        else:
            messagebox.showerror("Error", "No file path in database")
            
    def add_entry(self):
        """Add a new entry manually"""
        EditEntryWindow(self, None, self.refresh_results)
        
    def edit_entry(self):
        """Edit selected entry"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a program to edit")
            return
        
        program_number = self.tree.item(selected[0])['values'][0]
        EditEntryWindow(self, program_number, self.refresh_results)
        
    def delete_entry(self):
        """Delete selected entry"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a program to delete")
            return
        
        program_number = self.tree.item(selected[0])['values'][0]
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Delete program {program_number}?\n\nThis will only remove the database entry, not the file."):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM programs WHERE program_number = ?", (program_number,))
            conn.commit()
            conn.close()
            
            self.refresh_results()
            messagebox.showinfo("Deleted", "Entry deleted successfully")
            
    def view_details(self):
        """View full details of selected entry"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a program to view")
            return
        
        program_number = self.tree.item(selected[0])['values'][0]
        
        # Get full record
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM programs WHERE program_number = ?", (program_number,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            DetailsWindow(self, result)
            
    def export_csv(self):
        """Export database to CSV"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filepath:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM programs ORDER BY program_number")
            results = cursor.fetchall()
            
            with open(filepath, 'w') as f:
                # Header
                f.write("Program,Type,OD,Thickness,CB,Hub Height,Hub Diameter,CB Bore,CB Depth,Paired,Material,Notes,Created,Modified,File Path\n")
                
                # Data
                for row in results:
                    f.write(",".join([str(x) if x else "" for x in row]) + "\n")
            
            conn.close()
            messagebox.showinfo("Export Complete", f"Exported {len(results)} records to:\n{filepath}")
            
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
            menu.add_command(label="Delete Entry", command=self.delete_entry)

            menu.post(event.x_root, event.y_root)

    def show_legend(self):
        """Show validation status legend and help"""
        legend_window = tk.Toplevel(self.root)
        legend_window.title("Validation Status Legend - Help")
        legend_window.geometry("700x800")
        legend_window.configure(bg=self.bg_color)

        # Create scrolled text widget
        text = scrolledtext.ScrolledText(legend_window, bg=self.input_bg, fg=self.fg_color,
                                        font=("Courier", 10), wrap=tk.WORD, padx=15, pady=15)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Legend content
        legend_content = """
═══════════════════════════════════════════════════════════════════
                    VALIDATION STATUS LEGEND
═══════════════════════════════════════════════════════════════════

The G-Code Database Manager uses a 5-color validation system to
categorize issues by severity. This helps you prioritize which
programs need attention first.

═══════════════════════════════════════════════════════════════════

🔴 RED - CRITICAL (Highest Priority)
═══════════════════════════════════════════════════════════════════
Status: CRITICAL

What It Means:
  • Critical dimensional errors that will produce WRONG parts
  • CB or OB dimensions way outside tolerance (>±0.2-0.3mm)
  • Thickness errors beyond ±0.02"
  • Part CANNOT be used without G-code correction

Examples:
  • CB TOO SMALL: Spec=71.0mm, G-code=66.0mm (-4.96mm)
  • OB TOO LARGE: Spec=64.1mm, G-code=66.5mm (+2.40mm)
  • THICKNESS ERROR: Spec=0.75", Calculated=0.80" (+0.05")

Action Required: ⚠️ IMMEDIATE FIX NEEDED
  • Stop production
  • Fix G-code before running
  • These errors will cause part failures or machine crashes

───────────────────────────────────────────────────────────────────

🟠 ORANGE - BORE WARNING (High Priority)
═══════════════════════════════════════════════════════════════════
Status: BORE_WARNING

What It Means:
  • Bore dimensions at tolerance limits (CB/OB within ±0.1-0.2mm)
  • Part is still within spec but close to the edge
  • May cause fit issues in assembly

Examples:
  • CB at tolerance limit: Spec=38.1mm, G-code=38.2mm (+0.10mm)
  • OB at tolerance limit: Spec=64.1mm, G-code=64.0mm (-0.10mm)

Action Required: 🔍 VERIFY CAREFULLY
  • Check dimensions carefully during setup
  • Verify first article measurement
  • Part is technically acceptable but borderline
  • Consider adjusting G-code for better margin

───────────────────────────────────────────────────────────────────

🟣 PURPLE - DIMENSIONAL (Medium Priority)
═══════════════════════════════════════════════════════════════════
Status: DIMENSIONAL

What It Means:
  • P-code and thickness mismatches (setup dimension issues)
  • Wrong work offset for part thickness
  • Drill depth calculations slightly off (±0.01-0.02")
  • Work offsets don't match part thickness

Examples:
  • P-CODE MISMATCH: Thickness 1.00" expects P15/P16, but found [17,18]
  • Thickness mismatch: Spec=0.75", Calculated=0.76" (+0.01")

Action Required: 🔧 REVIEW SETUP
  • Check work offset (P-code) settings
  • Verify drill depth matches part thickness
  • Part may run but could have setup issues
  • Update P-codes or drill depth to match

───────────────────────────────────────────────────────────────────

🟡 YELLOW - WARNING (Low Priority)
═══════════════════════════════════════════════════════════════════
Status: WARNING

What It Means:
  • General warnings that don't affect critical dimensions
  • P-code pairing issues (missing OP1 or OP2)
  • Multiple P-codes found (possible copy/paste error)
  • OD slightly off (non-critical)

Examples:
  • P-CODE PAIRING: P15 found but P16 missing
  • MULTIPLE P-CODES: Found [15,16,17,18] - should only have one pair
  • OD tolerance check: Spec=5.75", G-code=5.71" (-0.04")

Action Required: 📋 REVIEW WHEN CONVENIENT
  • Check for copy/paste errors
  • Verify P-code pairing
  • Not urgent but should be fixed eventually

───────────────────────────────────────────────────────────────────

🟢 GREEN - PASS (No Issues)
═══════════════════════════════════════════════════════════════════
Status: PASS

What It Means:
  • All validations passed ✓
  • Dimensions within spec ✓
  • P-codes match thickness ✓
  • Ready to run ✓

Action Required: ✅ None - Good to go!

═══════════════════════════════════════════════════════════════════
                        PRIORITY MATRIX
═══════════════════════════════════════════════════════════════════

Color    Status         Severity    Production Impact    Action
------   ------------   ---------   ------------------   ---------
🔴 RED    CRITICAL       CRITICAL    Part failure/crash   IMMEDIATE
🟠 ORANGE BORE_WARNING   HIGH        Possible fit issues  Before 1st
🟣 PURPLE DIMENSIONAL    MEDIUM      Setup errors         Before run
🟡 YELLOW WARNING        LOW         Minor issues         When ready
🟢 GREEN  PASS           NONE        None                 N/A

═══════════════════════════════════════════════════════════════════
                     TOLERANCE REFERENCE
═══════════════════════════════════════════════════════════════════

CB (Center Bore):
  • Acceptable:  title_cb to (title_cb + 0.1mm)
  • Orange:      ±0.1 to ±0.2mm or ±0.3mm
  • Red:         < -0.2mm or > +0.3mm

OB (Outer Bore / Hub Diameter):
  • Acceptable:  (title_ob - 0.1mm) to title_ob
  • Orange:      ±0.1 to ±0.2mm or ±0.3mm
  • Red:         < -0.3mm or > +0.2mm

Thickness:
  • Acceptable:  ±0.01"
  • Purple:      ±0.01 to ±0.02"
  • Red:         > ±0.02"

OD (Outer Diameter):
  • Acceptable:  ±0.05"
  • Yellow:      ±0.05 to ±0.1"
  • Red:         > ±0.1"

═══════════════════════════════════════════════════════════════════
                    DAILY WORKFLOW EXAMPLE
═══════════════════════════════════════════════════════════════════

1. Morning Scan:
   • Scan Folder → Select production directory
   • Database updates with validation results

2. Prioritize by Color:
   • 🔴 RED files:    Fix immediately, don't run
   • 🟠 ORANGE files: Check carefully during setup
   • 🟣 PURPLE files: Verify P-codes before running
   • 🟡 YELLOW files: Note for later review
   • 🟢 GREEN files:  Run normally

3. Fix Process:
   • Double-click file → View Details
   • See exact error (e.g., "CB TOO SMALL -4.96mm")
   • Open G-code in editor
   • Fix dimension
   • Save file
   • Re-scan folder (status updates automatically)

═══════════════════════════════════════════════════════════════════
                      FILTERING TIPS
═══════════════════════════════════════════════════════════════════

Multi-Select Filters:
  • Click Type/Material/Status dropdowns
  • Check multiple boxes to filter
  • Shows "3 selected" when multiple items chosen
  • Click "Apply" to filter results

Focus on Issues:
  • Status filter: Select CRITICAL + BORE_WARNING + DIMENSIONAL
  • Leave WARNING and PASS unchecked
  • See only files needing attention

Production-Ready Files:
  • Status filter: Select only PASS
  • Shows files ready to run

═══════════════════════════════════════════════════════════════════

For more information, see:
  • COLOR_CODED_VALIDATION_SYSTEM.md
  • MULTI_SELECT_FILTERS.md

═══════════════════════════════════════════════════════════════════
"""

        text.insert("1.0", legend_content)

        # Configure text tags for colored examples
        text.tag_configure('red', foreground='#ff6b6b')
        text.tag_configure('orange', foreground='#ffa500')
        text.tag_configure('purple', foreground='#da77f2')
        text.tag_configure('yellow', foreground='#ffd43b')
        text.tag_configure('green', foreground='#69db7c')

        text.config(state=tk.DISABLED)

        # Close button
        btn_close = tk.Button(legend_window, text="Close", command=legend_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 11, "bold"), width=20, height=2)
        btn_close.pack(pady=10)


class EditEntryWindow:
    """Window for adding/editing entries"""
    def __init__(self, parent, program_number, callback):
        self.parent = parent
        self.program_number = program_number
        self.callback = callback
        
        self.window = tk.Toplevel(parent.root)
        self.window.title("Edit Entry" if program_number else "Add Entry")
        self.window.geometry("600x700")
        self.window.configure(bg=parent.bg_color)
        
        # Load existing data if editing
        self.record = None
        if program_number:
            conn = sqlite3.connect(parent.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM programs WHERE program_number = ?", (program_number,))
            self.record = cursor.fetchone()
            conn.close()
        
        self.create_form()
        
    def create_form(self):
        """Create entry form"""
        # Container
        container = tk.Frame(self.window, bg=self.parent.bg_color)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        row = 0
        
        # Program Number
        tk.Label(container, text="Program Number:", bg=self.parent.bg_color, 
                fg=self.parent.fg_color).grid(row=row, column=0, sticky="w", pady=5)
        self.entry_program = tk.Entry(container, bg=self.parent.input_bg, 
                                     fg=self.parent.fg_color, width=30)
        self.entry_program.grid(row=row, column=1, sticky="ew", pady=5)
        if self.record:
            self.entry_program.insert(0, self.record[0])
            self.entry_program.config(state="readonly")  # Can't change primary key
        row += 1
        
        # Spacer Type
        tk.Label(container, text="Spacer Type:", bg=self.parent.bg_color, 
                fg=self.parent.fg_color).grid(row=row, column=0, sticky="w", pady=5)
        self.entry_type = ttk.Combobox(container, values=self.parent.config["spacer_types"], 
                                      state="readonly", width=28)
        self.entry_type.grid(row=row, column=1, sticky="ew", pady=5)
        if self.record and self.record[1]:
            self.entry_type.set(self.record[1])
        row += 1
        
        # Dimensions
        dims = [
            ("Outer Diameter:", 2, "outer_diameter"),
            ("Thickness:", 3, "thickness"),
            ("Center Bore:", 4, "center_bore"),
            ("Hub Height:", 5, "hub_height"),
            ("Hub Diameter:", 6, "hub_diameter"),
            ("Counter Bore Diameter:", 7, "cb_diameter"),
            ("Counter Bore Depth:", 8, "cb_depth"),
        ]
        
        self.entries = {}
        for label, idx, key in dims:
            tk.Label(container, text=label, bg=self.parent.bg_color, 
                    fg=self.parent.fg_color).grid(row=row, column=0, sticky="w", pady=5)
            entry = tk.Entry(container, bg=self.parent.input_bg, 
                           fg=self.parent.fg_color, width=30)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            if self.record and self.record[idx]:
                entry.insert(0, str(self.record[idx]))
            self.entries[key] = entry
            row += 1
        
        # Paired Program
        tk.Label(container, text="Paired Program:", bg=self.parent.bg_color, 
                fg=self.parent.fg_color).grid(row=row, column=0, sticky="w", pady=5)
        self.entry_paired = tk.Entry(container, bg=self.parent.input_bg, 
                                     fg=self.parent.fg_color, width=30)
        self.entry_paired.grid(row=row, column=1, sticky="ew", pady=5)
        if self.record and self.record[9]:
            self.entry_paired.insert(0, self.record[9])
        row += 1
        
        # Material
        tk.Label(container, text="Material:", bg=self.parent.bg_color, 
                fg=self.parent.fg_color).grid(row=row, column=0, sticky="w", pady=5)
        self.entry_material = ttk.Combobox(container, 
                                          values=self.parent.config["material_list"], 
                                          state="readonly", width=28)
        self.entry_material.grid(row=row, column=1, sticky="ew", pady=5)
        if self.record and self.record[10]:
            self.entry_material.set(self.record[10])
        row += 1
        
        # Notes
        tk.Label(container, text="Notes:", bg=self.parent.bg_color, 
                fg=self.parent.fg_color).grid(row=row, column=0, sticky="nw", pady=5)
        self.entry_notes = tk.Text(container, bg=self.parent.input_bg, 
                                  fg=self.parent.fg_color, width=30, height=4)
        self.entry_notes.grid(row=row, column=1, sticky="ew", pady=5)
        if self.record and self.record[11]:
            self.entry_notes.insert("1.0", self.record[11])
        row += 1
        
        # File Path
        tk.Label(container, text="File Path:", bg=self.parent.bg_color, 
                fg=self.parent.fg_color).grid(row=row, column=0, sticky="w", pady=5)
        path_frame = tk.Frame(container, bg=self.parent.bg_color)
        path_frame.grid(row=row, column=1, sticky="ew", pady=5)
        
        self.entry_filepath = tk.Entry(path_frame, bg=self.parent.input_bg, 
                                      fg=self.parent.fg_color)
        self.entry_filepath.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if self.record and self.record[14]:
            self.entry_filepath.insert(0, self.record[14])
        
        btn_browse = tk.Button(path_frame, text="Browse", command=self.browse_file,
                              bg=self.parent.button_bg, fg=self.parent.fg_color)
        btn_browse.pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Buttons
        button_frame = tk.Frame(container, bg=self.parent.bg_color)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        btn_save = tk.Button(button_frame, text="💾 Save", command=self.save_entry,
                            bg=self.parent.accent_color, fg=self.parent.fg_color,
                            font=("Arial", 10, "bold"), width=15)
        btn_save.pack(side=tk.LEFT, padx=5)
        
        btn_cancel = tk.Button(button_frame, text="❌ Cancel", command=self.window.destroy,
                              bg=self.parent.button_bg, fg=self.parent.fg_color,
                              font=("Arial", 10, "bold"), width=15)
        btn_cancel.pack(side=tk.LEFT, padx=5)
        
        container.columnconfigure(1, weight=1)
        
    def browse_file(self):
        """Browse for file"""
        filepath = filedialog.askopenfilename(
            title="Select G-Code File",
            filetypes=[("G-Code files", "*.nc *.gcode *.cnc"), ("All files", "*.*")]
        )
        if filepath:
            self.entry_filepath.delete(0, tk.END)
            self.entry_filepath.insert(0, filepath)
            
    def save_entry(self):
        """Save entry to database"""
        # Validate
        program_number = self.entry_program.get().strip()
        if not program_number:
            messagebox.showerror("Error", "Program number is required")
            return
        
        spacer_type = self.entry_type.get()
        if not spacer_type:
            messagebox.showerror("Error", "Spacer type is required")
            return
        
        # Get values
        def get_float(entry):
            try:
                val = entry.get().strip()
                return float(val) if val else None
            except:
                return None
        
        outer_diameter = get_float(self.entries["outer_diameter"])
        thickness = get_float(self.entries["thickness"])
        center_bore = get_float(self.entries["center_bore"])
        hub_height = get_float(self.entries["hub_height"])
        hub_diameter = get_float(self.entries["hub_diameter"])
        cb_diameter = get_float(self.entries["cb_diameter"])
        cb_depth = get_float(self.entries["cb_depth"])
        
        paired_program = self.entry_paired.get().strip() or None
        material = self.entry_material.get() or None
        notes = self.entry_notes.get("1.0", tk.END).strip() or None
        file_path = self.entry_filepath.get().strip() or None
        
        # Save to database
        conn = sqlite3.connect(self.parent.db_path)
        cursor = conn.cursor()
        
        try:
            if self.program_number:  # Update
                cursor.execute('''
                    UPDATE programs SET
                        spacer_type = ?, outer_diameter = ?, thickness = ?,
                        center_bore = ?, hub_height = ?, hub_diameter = ?,
                        counter_bore_diameter = ?, counter_bore_depth = ?,
                        paired_program = ?, material = ?, notes = ?,
                        last_modified = ?, file_path = ?
                    WHERE program_number = ?
                ''', (spacer_type, outer_diameter, thickness, center_bore,
                     hub_height, hub_diameter, cb_diameter, cb_depth,
                     paired_program, material, notes, 
                     datetime.now().isoformat(), file_path, program_number))
            else:  # Insert
                cursor.execute('''
                    INSERT INTO programs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (program_number, spacer_type, outer_diameter, thickness,
                     center_bore, hub_height, hub_diameter, cb_diameter, cb_depth,
                     paired_program, material, notes, datetime.now().isoformat(),
                     datetime.now().isoformat(), file_path, None, None, None, None, None, None, None))
            
            conn.commit()
            messagebox.showinfo("Success", "Entry saved successfully")
            self.window.destroy()
            self.callback()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Program number already exists")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
        finally:
            conn.close()


class DetailsWindow:
    """Window to view full details of an entry"""
    def __init__(self, parent, record):
        self.parent = parent
        self.record = record
        
        self.window = tk.Toplevel(parent.root)
        self.window.title(f"Details - {record[0]}")
        self.window.geometry("500x600")
        self.window.configure(bg=parent.bg_color)
        
        self.create_view()
        
    def create_view(self):
        """Create details view"""
        # Scrolled text
        text = scrolledtext.ScrolledText(self.window, bg=self.parent.input_bg, 
                                        fg=self.parent.fg_color,
                                        font=("Courier", 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Format details
        fields = [
            ("Program Number", 0),
            ("Spacer Type", 1),
            ("Outer Diameter", 2),
            ("Thickness", 3),
            ("Thickness Display", 4),
            ("Center Bore", 5),
            ("Hub Height", 6),
            ("Hub Diameter", 7),
            ("Counter Bore Diameter", 8),
            ("Counter Bore Depth", 9),
            ("Paired Program", 10),
            ("Material", 11),
            ("Notes", 12),
            ("Date Created", 13),
            ("Last Modified", 14),
            ("File Path", 15),
        ]

        text.insert(tk.END, "="*50 + "\n")
        text.insert(tk.END, f"  PROGRAM DETAILS - {self.record[0]}\n")
        text.insert(tk.END, "="*50 + "\n\n")

        for label, idx in fields:
            value = self.record[idx] if self.record[idx] else "-"
            text.insert(tk.END, f"{label}:\n  {value}\n\n")

        # Add validation information if available
        if len(self.record) > 17:
            text.insert(tk.END, "="*50 + "\n")
            text.insert(tk.END, "  VALIDATION RESULTS\n")
            text.insert(tk.END, "="*50 + "\n\n")

            # Detection info
            if self.record[15]:  # detection_confidence
                text.insert(tk.END, f"Detection Confidence: {self.record[15]}\n")
            if self.record[16]:  # detection_method
                text.insert(tk.END, f"Detection Method: {self.record[16]}\n")

            # Validation status
            status = self.record[17] if self.record[17] else "N/A"
            text.insert(tk.END, f"\nValidation Status: {status}\n\n")

            # G-code dimensions
            if self.record[20]:  # cb_from_gcode
                text.insert(tk.END, f"CB from G-code: {self.record[20]:.1f}mm\n")
            if self.record[21]:  # ob_from_gcode
                text.insert(tk.END, f"OB from G-code: {self.record[21]:.1f}mm\n")

            # Validation issues
            if self.record[18]:  # validation_issues
                try:
                    issues = json.loads(self.record[18])
                    if issues:
                        text.insert(tk.END, "\n❌ ISSUES:\n")
                        for issue in issues:
                            text.insert(tk.END, f"  • {issue}\n")
                except:
                    pass

            # Validation warnings
            if self.record[19]:  # validation_warnings
                try:
                    warnings = json.loads(self.record[19])
                    if warnings:
                        text.insert(tk.END, "\n⚠️  WARNINGS:\n")
                        for warning in warnings:
                            text.insert(tk.END, f"  • {warning}\n")
                except:
                    pass

        text.config(state=tk.DISABLED)
        
        # Close button
        btn_close = tk.Button(self.window, text="Close", command=self.window.destroy,
                             bg=self.parent.button_bg, fg=self.parent.fg_color,
                             font=("Arial", 10, "bold"), width=15)
        btn_close.pack(pady=10)


def main():
    root = tk.Tk()
    app = GCodeDatabaseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
