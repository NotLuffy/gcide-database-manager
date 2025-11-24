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
import shutil

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
    title: Optional[str]  # Raw title from G-code (content in parentheses)
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
    lathe: Optional[str] = None  # 'L1', 'L2', 'L3', 'L2/L3'

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
                title TEXT,
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
                ob_from_gcode REAL,
                lathe TEXT
            )
        ''')

        # Upgrade existing database if needed
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN title TEXT")
        except:
            pass
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
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN lathe TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN duplicate_type TEXT")  # 'SOLID', 'NAME_COLLISION', 'CONTENT_DUP', NULL
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN parent_file TEXT")  # Reference to parent program_number
        except:
            pass
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN duplicate_group TEXT")  # Group ID for related duplicates
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

    def backup_database(self) -> bool:
        """Create a backup of the database in a special backup folder

        Returns:
            bool: True if backup was successful, False otherwise
        """
        try:
            # Create backup folder if it doesn't exist
            backup_folder = "Database_Backups"
            if not os.path.exists(backup_folder):
                os.makedirs(backup_folder)

            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"gcode_database_backup_{timestamp}.db"
            backup_path = os.path.join(backup_folder, backup_filename)

            # Copy database file
            shutil.copy2(self.db_path, backup_path)

            # Keep only last 10 backups to prevent folder bloat
            self.cleanup_old_backups(backup_folder, keep_count=10)

            return True
        except Exception as e:
            messagebox.showerror("Backup Error", f"Failed to create database backup:\n{str(e)}")
            return False

    def cleanup_old_backups(self, backup_folder: str, keep_count: int = 10):
        """Keep only the most recent N backups

        Args:
            backup_folder: Path to backup folder
            keep_count: Number of recent backups to keep
        """
        try:
            # Get all backup files
            backup_files = [f for f in os.listdir(backup_folder)
                           if f.startswith("gcode_database_backup_") and f.endswith(".db")]

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_folder, x)), reverse=True)

            # Delete older backups
            for old_backup in backup_files[keep_count:]:
                old_path = os.path.join(backup_folder, old_backup)
                os.remove(old_path)
        except Exception as e:
            # Don't show error for cleanup failures, just log it
            print(f"Backup cleanup warning: {str(e)}")

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
        
        # Top section - Title and Ribbon Tabs
        top_frame = tk.Frame(main_container, bg=self.bg_color)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_top_section(top_frame)

        # Ribbon tabs section
        ribbon_frame = tk.Frame(main_container, bg=self.bg_color, relief=tk.RAISED, borderwidth=1)
        ribbon_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_ribbon_tabs(ribbon_frame)
        
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

    def create_ribbon_tabs(self, parent):
        """Create ribbon-style tab interface for organizing buttons"""
        # Create notebook (tabbed interface)
        style = ttk.Style()
        style.configure('Ribbon.TNotebook', background=self.bg_color, borderwidth=0)
        style.configure('Ribbon.TNotebook.Tab', padding=[20, 10], font=('Arial', 10, 'bold'))

        ribbon = ttk.Notebook(parent, style='Ribbon.TNotebook')
        ribbon.pack(fill=tk.X, padx=5, pady=5)

        # Tab 1: File Management
        tab_files = tk.Frame(ribbon, bg=self.bg_color)
        ribbon.add(tab_files, text='📂 Files')

        files_group = tk.Frame(tab_files, bg=self.bg_color)
        files_group.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(files_group, text="📁 Scan Folder", command=self.scan_folder,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(files_group, text="🆕 Scan New Only", command=self.scan_for_new_files,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(files_group, text="🔄 Rescan Database", command=self.rescan_database,
                 bg="#FF6F00", fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(files_group, text="📁 Organize by OD", command=self.organize_files_by_od,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(files_group, text="📋 Copy Filtered", command=self.copy_filtered_view,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(files_group, text="➕ Add Entry", command=self.add_entry,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        # Tab 2: Duplicates
        tab_duplicates = tk.Frame(ribbon, bg=self.bg_color)
        ribbon.add(tab_duplicates, text='🔍 Duplicates')

        dup_group = tk.Frame(tab_duplicates, bg=self.bg_color)
        dup_group.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(dup_group, text="🔍 Find Repeats", command=self.find_and_mark_repeats,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(dup_group, text="⚖️ Compare Files", command=self.compare_files,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(dup_group, text="📝 Rename Duplicates", command=self.rename_duplicate_files,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(dup_group, text="🔧 Fix Program #s", command=self.fix_program_numbers,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(dup_group, text="🗑️ Delete Duplicates", command=self.delete_duplicates,
                 bg="#D32F2F", fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        # Tab 3: Reports
        tab_reports = tk.Frame(ribbon, bg=self.bg_color)
        ribbon.add(tab_reports, text='📊 Reports')

        reports_group = tk.Frame(tab_reports, bg=self.bg_color)
        reports_group.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(reports_group, text="📤 Export CSV", command=self.export_csv,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(reports_group, text="📋 Unused #s", command=self.export_unused_numbers,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(reports_group, text="📊 Statistics", command=self.show_statistics,
                 bg="#1976D2", fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(reports_group, text="❓ Help & Workflow", command=self.show_legend,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        # Tab 4: Backup & Database
        tab_database = tk.Frame(ribbon, bg=self.bg_color)
        ribbon.add(tab_database, text='💾 Backup')

        db_group = tk.Frame(tab_database, bg=self.bg_color)
        db_group.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(db_group, text="💾 Backup Now", command=self.create_manual_backup,
                 bg="#1976D2", fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(db_group, text="📂 Restore Backup", command=self.restore_from_backup,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(db_group, text="📋 View Backups", command=self.view_backups,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(db_group, text="💾 Save Profile", command=self.save_database_profile,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(db_group, text="📂 Load Profile", command=self.load_database_profile,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(db_group, text="📋 Manage Profiles", command=self.manage_database_profiles,
                 bg=self.button_bg, fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        # Tab 5: Maintenance
        tab_maint = tk.Frame(ribbon, bg=self.bg_color)
        ribbon.add(tab_maint, text='⚙️ Maintenance')

        maint_group = tk.Frame(tab_maint, bg=self.bg_color)
        maint_group.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(maint_group, text="🗑️ Clear Database", command=self.clear_database,
                 bg="#D32F2F", fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

        tk.Button(maint_group, text="❌ Delete Filtered", command=self.delete_filtered_view,
                 bg="#D32F2F", fg=self.fg_color, font=("Arial", 9, "bold"),
                 width=14, height=2).pack(side=tk.LEFT, padx=3)

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

        # Duplicate Type
        tk.Label(row1, text="Dup Type:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        dup_type_values = ["SOLID", "NAME_COLLISION", "CONTENT_DUP", "None"]
        self.filter_dup_type = MultiSelectCombobox(row1, dup_type_values, self.bg_color, self.fg_color,
                                                   self.input_bg, self.button_bg, width=15)
        self.filter_dup_type.pack(side=tk.LEFT, padx=5)

        # Row 2 - Dimensional filters
        row2 = tk.Frame(filter_container, bg=self.bg_color)
        row2.pack(fill=tk.X, pady=5)
        
        # Outer Diameter
        # OD Range - Common standard sizes
        tk.Label(row2, text="OD Range:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        od_values = ["", "5.75", "6.0", "6.25", "6.5", "7.0", "7.5", "8.0", "8.5", "9.5", "10.25", "10.5", "13.0"]
        self.filter_od_min = ttk.Combobox(row2, values=od_values, width=8)
        self.filter_od_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_od_max = ttk.Combobox(row2, values=od_values, width=8)
        self.filter_od_max.pack(side=tk.LEFT, padx=2)

        # Thickness - Common values
        tk.Label(row2, text="Thick:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        thick_values = ["", "0.25", "0.38", "0.5", "0.62", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0"]
        self.filter_thickness_min = ttk.Combobox(row2, values=thick_values, width=8)
        self.filter_thickness_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_thickness_max = ttk.Combobox(row2, values=thick_values, width=8)
        self.filter_thickness_max.pack(side=tk.LEFT, padx=2)

        # Center Bore - Common CB sizes (mm)
        tk.Label(row2, text="CB:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        cb_values = ["", "38", "40", "50", "54", "56", "60", "63", "66", "70", "77", "78", "84", "93", "100", "106", "108", "110", "125", "130", "150", "170", "220"]
        self.filter_cb_min = ttk.Combobox(row2, values=cb_values, width=8)
        self.filter_cb_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_cb_max = ttk.Combobox(row2, values=cb_values, width=8)
        self.filter_cb_max.pack(side=tk.LEFT, padx=2)

        # Row 2.5 - Additional dimensional filters (Hub Dia, Hub H, Step)
        row2_5 = tk.Frame(filter_container, bg=self.bg_color)
        row2_5.pack(fill=tk.X, pady=5)

        # Hub Diameter - Common OB/Hub sizes (mm)
        tk.Label(row2_5, text="Hub Dia:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        hub_dia_values = ["", "54", "56", "57", "59", "60", "63", "66", "70", "73", "74", "77", "78", "84", "87", "93", "95", "100", "106", "108", "110"]
        self.filter_hub_dia_min = ttk.Combobox(row2_5, values=hub_dia_values, width=8)
        self.filter_hub_dia_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2_5, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_hub_dia_max = ttk.Combobox(row2_5, values=hub_dia_values, width=8)
        self.filter_hub_dia_max.pack(side=tk.LEFT, padx=2)

        # Hub Height - Common hub heights (inches)
        tk.Label(row2_5, text="Hub H:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        hub_h_values = ["", "0.25", "0.33", "0.38", "0.44", "0.47", "0.5", "0.55", "0.6", "0.65", "0.7", "0.75", "1.0", "1.25", "1.5"]
        self.filter_hub_h_min = ttk.Combobox(row2_5, values=hub_h_values, width=8)
        self.filter_hub_h_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2_5, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_hub_h_max = ttk.Combobox(row2_5, values=hub_h_values, width=8)
        self.filter_hub_h_max.pack(side=tk.LEFT, padx=2)

        # Step Diameter - Common step/shelf sizes (mm)
        tk.Label(row2_5, text="Step D:", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=5)
        step_d_values = ["", "64", "70", "74", "78", "82", "84", "85", "87", "90", "93", "95", "100", "106", "108", "110", "125", "130"]
        self.filter_step_d_min = ttk.Combobox(row2_5, values=step_d_values, width=8)
        self.filter_step_d_min.pack(side=tk.LEFT, padx=2)
        tk.Label(row2_5, text="to", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=2)
        self.filter_step_d_max = ttk.Combobox(row2_5, values=step_d_values, width=8)
        self.filter_step_d_max.pack(side=tk.LEFT, padx=2)

        # Row 2.6 - Error type filter
        row2_6 = tk.Frame(filter_container, bg=self.bg_color)
        row2_6.pack(fill=tk.X, pady=5)

        tk.Label(row2_6, text="Error Contains:", bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        # Combobox with common error types (editable for custom searches)
        common_errors = [
            "",  # Empty for "all"
            "CB TOO LARGE",
            "CB TOO SMALL",
            "THICKNESS ERROR",
            "OB TOO LARGE",
            "OB TOO SMALL",
            "OD MISMATCH",
            "DRILL",
            "CHAMFER",
            "STEP",
            "HUB",
            "BORE"
        ]
        self.filter_error_text = ttk.Combobox(row2_6, values=common_errors, width=47)
        self.filter_error_text.pack(side=tk.LEFT, padx=2)
        self.filter_error_text.set("")  # Default to empty

        tk.Label(row2_6, text="(Select common error or type custom search)",
                bg=self.bg_color, fg="#888888", font=("Arial", 8, "italic")).pack(side=tk.LEFT, padx=5)

        # Row 3 - Sort options
        row3 = tk.Frame(filter_container, bg=self.bg_color)
        row3.pack(fill=tk.X, pady=5)

        tk.Label(row3, text="Sort by:", bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        # Sort columns available
        sort_columns = ["", "Program #", "Dup", "Type", "Lathe", "OD", "Thick", "CB", "Hub H", "Hub D",
                       "CB Bore", "Step D", "Material", "Status"]

        # Sort 1
        self.sort1_col = ttk.Combobox(row3, values=sort_columns, state="readonly", width=10)
        self.sort1_col.pack(side=tk.LEFT, padx=2)
        self.sort1_col.set("CB")
        self.sort1_dir = ttk.Combobox(row3, values=["Low→High", "High→Low"], state="readonly", width=9)
        self.sort1_dir.pack(side=tk.LEFT, padx=2)
        self.sort1_dir.set("Low→High")

        tk.Label(row3, text="then", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=3)

        # Sort 2
        self.sort2_col = ttk.Combobox(row3, values=sort_columns, state="readonly", width=10)
        self.sort2_col.pack(side=tk.LEFT, padx=2)
        self.sort2_col.set("OD")
        self.sort2_dir = ttk.Combobox(row3, values=["Low→High", "High→Low"], state="readonly", width=9)
        self.sort2_dir.pack(side=tk.LEFT, padx=2)
        self.sort2_dir.set("Low→High")

        tk.Label(row3, text="then", bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=3)

        # Sort 3
        self.sort3_col = ttk.Combobox(row3, values=sort_columns, state="readonly", width=10)
        self.sort3_col.pack(side=tk.LEFT, padx=2)
        self.sort3_col.set("")
        self.sort3_dir = ttk.Combobox(row3, values=["Low→High", "High→Low"], state="readonly", width=9)
        self.sort3_dir.pack(side=tk.LEFT, padx=2)
        self.sort3_dir.set("Low→High")

        btn_sort = tk.Button(row3, text="↕️ Sort", command=self.apply_multi_sort,
                            bg=self.button_bg, fg=self.fg_color,
                            font=("Arial", 9, "bold"), width=8)
        btn_sort.pack(side=tk.LEFT, padx=5)

        # Row 4 - Action buttons
        row4 = tk.Frame(filter_container, bg=self.bg_color)
        row4.pack(fill=tk.X, pady=5)

        btn_search = tk.Button(row4, text="🔍 Search", command=self.refresh_results,
                              bg=self.accent_color, fg=self.fg_color,
                              font=("Arial", 10, "bold"), width=12, height=1)
        btn_search.pack(side=tk.LEFT, padx=5)

        btn_refresh = tk.Button(row4, text="🔄 Refresh", command=self.refresh_results,
                               bg="#2E7D32", fg=self.fg_color,
                               font=("Arial", 10, "bold"), width=12, height=1)
        btn_refresh.pack(side=tk.LEFT, padx=5)

        btn_clear = tk.Button(row4, text="❌ Clear Filters", command=self.clear_filters,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"), width=12, height=1)
        btn_clear.pack(side=tk.LEFT, padx=5)

        # Duplicates only checkbox
        self.filter_duplicates = tk.BooleanVar()
        dup_check = tk.Checkbutton(row4, text="Duplicates Only", variable=self.filter_duplicates,
                                   bg=self.bg_color, fg=self.fg_color, selectcolor=self.input_bg,
                                   activebackground=self.bg_color, activeforeground=self.fg_color,
                                   font=("Arial", 9))
        dup_check.pack(side=tk.LEFT, padx=10)

        # Results count label
        self.results_label = tk.Label(row4, text="", bg=self.bg_color, fg=self.fg_color,
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
        columns = ("Program #", "Dup", "Title", "Type", "Lathe", "OD", "Thick", "CB", "Hub H", "Hub D",
                  "CB Bore", "Step D", "Material", "Status", "File")

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Configure tags for color coding (severity-based)
        self.tree.tag_configure('critical', background='#4d1f1f', foreground='#ff6b6b')     # RED - Critical errors
        self.tree.tag_configure('bore_warning', background='#4d3520', foreground='#ffa500') # ORANGE - Bore warnings
        self.tree.tag_configure('dimensional', background='#3d1f4d', foreground='#da77f2')  # PURPLE - P-code/thickness
        self.tree.tag_configure('warning', background='#4d3d1f', foreground='#ffd43b')      # YELLOW - General warnings
        self.tree.tag_configure('repeat', background='#3d3d3d', foreground='#909090')       # GRAY - Repeat files
        self.tree.tag_configure('pass', background='#1f4d2e', foreground='#69db7c')         # GREEN - Pass
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        column_widths = {
            "Program #": 100,
            "Dup": 40,
            "Title": 250,
            "Type": 120,
            "Lathe": 60,
            "OD": 80,
            "Thick": 80,
            "CB": 80,
            "Hub H": 80,
            "Hub D": 80,
            "CB Bore": 80,
            "Step D": 70,
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
                title=result.title,
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
                ob_from_gcode=result.ob_from_gcode,
                lathe=result.lathe
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

    def update_gcode_program_number(self, file_path, new_program_number):
        """Update the internal O-number in a G-code file

        Args:
            file_path: Path to the G-code file
            new_program_number: New program number (e.g., "o57001" or "57001")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure program number has 'o' prefix
            if not new_program_number.lower().startswith('o'):
                new_program_number = 'o' + new_program_number

            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Find and update the program number line (usually first line starting with O)
            updated = False
            for i, line in enumerate(lines):
                stripped = line.strip().upper()
                # Match O##### at start of line
                if stripped.startswith('O') and re.match(r'^O\d{4,}', stripped):
                    # Replace the O-number
                    lines[i] = new_program_number.upper() + '\n'
                    updated = True
                    break

            if updated:
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            else:
                # No O-number found in file, add it at the beginning
                lines.insert(0, new_program_number.upper() + '\n')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True

        except Exception as e:
            print(f"Error updating G-code program number: {e}")
            return False

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
        progress_window.geometry("700x500")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Scanning folder...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 font=("Courier", 9),
                                                 width=80, height=20)
        progress_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.update()

        # Scan for gcode files (with or without extension)
        all_scanned_files = []
        file_count = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                # Match any file containing o##### pattern (4+ digits)
                # This includes: o57000, o57000.nc, o57000.gcode, etc.
                if re.search(r'[oO]\d{4,}', file):
                    all_scanned_files.append(os.path.join(root, file))
                    file_count += 1
                    # Update progress every 50 files
                    if file_count % 50 == 0:
                        progress_label.config(text=f"Scanning... found {file_count} files so far")
                        self.root.update()

        progress_label.config(text=f"Analyzing {len(all_scanned_files)} files...")
        progress_text.insert(tk.END, f"Found {len(all_scanned_files)} total files. Analyzing...\n\n")
        progress_text.see(tk.END)
        self.root.update()

        # Get existing files from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM programs WHERE file_path IS NOT NULL")
        existing_files_data = {}  # {filename_lower: [file_paths]}

        for row in cursor.fetchall():
            file_path = row[0]
            if file_path and os.path.exists(file_path):
                basename = os.path.basename(file_path).lower()
                if basename not in existing_files_data:
                    existing_files_data[basename] = []
                existing_files_data[basename].append(file_path)

        # Detect duplicates within the scan AND against database
        files_by_name = {}  # Group scanned files by filename
        for filepath in all_scanned_files:
            basename_lower = os.path.basename(filepath).lower()
            if basename_lower not in files_by_name:
                files_by_name[basename_lower] = []
            files_by_name[basename_lower].append(filepath)

        # Categorize files
        files_to_process = []
        exact_duplicates_db = []  # Same name + content as database
        exact_duplicates_scan = []  # Same name + content within scan
        name_collisions_db = []  # Same name, different content vs database
        name_collisions_scan = []  # Same name, different content within scan

        analyzed_count = 0
        total_unique_names = len(files_by_name)

        for basename_lower, filepaths in files_by_name.items():
            analyzed_count += 1
            # Update progress every 10 unique filenames
            if analyzed_count % 10 == 0 or analyzed_count == total_unique_names:
                progress_label.config(text=f"Analyzing duplicates... {analyzed_count}/{total_unique_names}")
                self.root.update()
            # Check against database first
            in_database = basename_lower in existing_files_data

            if len(filepaths) == 1:
                # Single file with this name in scan
                filepath = filepaths[0]

                if in_database:
                    # Compare content with database file(s)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            new_content = f.read()

                        is_exact_match = False
                        for db_path in existing_files_data[basename_lower]:
                            try:
                                with open(db_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    db_content = f.read()
                                if new_content == db_content:
                                    is_exact_match = True
                                    break
                            except:
                                continue

                        if is_exact_match:
                            exact_duplicates_db.append(filepath)
                        else:
                            name_collisions_db.append((filepath, existing_files_data[basename_lower][0]))
                    except:
                        name_collisions_db.append((filepath, existing_files_data[basename_lower][0]))
                else:
                    # New file, safe to add
                    files_to_process.append(filepath)

            else:
                # Multiple files with same name in scan
                # Read all contents and find unique ones
                file_contents = {}
                for filepath in filepaths:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if content not in file_contents:
                            file_contents[content] = []
                        file_contents[content].append(filepath)
                    except:
                        # If can't read, treat as unique
                        file_contents[filepath] = [filepath]

                # For each unique content, keep first file
                for content, paths in file_contents.items():
                    first_file = paths[0]
                    duplicates_in_scan = paths[1:]

                    # Check if this content matches database
                    if in_database:
                        try:
                            is_exact_match = False
                            for db_path in existing_files_data[basename_lower]:
                                try:
                                    with open(db_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        db_content = f.read()
                                    if content == db_content:
                                        is_exact_match = True
                                        break
                                except:
                                    continue

                            if is_exact_match:
                                exact_duplicates_db.append(first_file)
                            else:
                                name_collisions_db.append((first_file, existing_files_data[basename_lower][0]))
                        except:
                            name_collisions_db.append((first_file, existing_files_data[basename_lower][0]))
                    else:
                        # New unique content, add first one
                        files_to_process.append(first_file)

                    # Mark duplicates within scan
                    for dup in duplicates_in_scan:
                        exact_duplicates_scan.append((dup, first_file))

        # Display analysis results
        progress_text.insert(tk.END, f"=== SCAN ANALYSIS ===\n")
        progress_text.insert(tk.END, f"Files to process: {len(files_to_process)}\n")
        progress_text.insert(tk.END, f"Exact duplicates (vs database): {len(exact_duplicates_db)}\n")
        progress_text.insert(tk.END, f"Exact duplicates (within scan): {len(exact_duplicates_scan)}\n")
        progress_text.insert(tk.END, f"Name collisions (vs database): {len(name_collisions_db)}\n")
        progress_text.insert(tk.END, f"Name collisions (within scan): {len(name_collisions_scan)}\n\n")

        # Show details
        if exact_duplicates_db:
            progress_text.insert(tk.END, f"=== SKIPPING - Already in Database (Exact Match) ===\n")
            for dup in exact_duplicates_db[:10]:
                progress_text.insert(tk.END, f"  SKIP: {os.path.basename(dup)}\n")
            if len(exact_duplicates_db) > 10:
                progress_text.insert(tk.END, f"  ... and {len(exact_duplicates_db) - 10} more\n")
            progress_text.insert(tk.END, "\n")

        if exact_duplicates_scan:
            progress_text.insert(tk.END, f"=== SKIPPING - Duplicates Within Scan ===\n")
            for dup, kept in exact_duplicates_scan[:10]:
                progress_text.insert(tk.END, f"  SKIP: {os.path.basename(dup)} (same as {os.path.basename(kept)})\n")
            if len(exact_duplicates_scan) > 10:
                progress_text.insert(tk.END, f"  ... and {len(exact_duplicates_scan) - 10} more\n")
            progress_text.insert(tk.END, "\n")

        if name_collisions_db:
            progress_text.insert(tk.END, f"⚠️  WARNING - Name Collisions vs Database ===\n")
            progress_text.insert(tk.END, f"These files will be SKIPPED. Rename them first!\n\n")
            for new_file, db_file in name_collisions_db[:5]:
                progress_text.insert(tk.END, f"  ⚠️  {os.path.basename(new_file)}\n")
                progress_text.insert(tk.END, f"     Scan: {new_file}\n")
                progress_text.insert(tk.END, f"     Database: {db_file}\n\n")
            if len(name_collisions_db) > 5:
                progress_text.insert(tk.END, f"  ... and {len(name_collisions_db) - 5} more\n")
            progress_text.insert(tk.END, "\n")

        progress_text.insert(tk.END, f"Processing {len(files_to_process)} files...\n\n")
        progress_text.see(tk.END)
        self.root.update()

        # Process only the unique files
        added = 0
        updated = 0
        errors = 0
        duplicates_within_processing = 0  # Track duplicates found during processing

        # Track which program numbers we've seen during processing
        seen_in_scan = {}  # program_number -> filepath
        gcode_files = files_to_process  # Use filtered list
        total_to_process = len(gcode_files)

        for idx, filepath in enumerate(gcode_files, 1):
            filename = os.path.basename(filepath)
            progress_label.config(text=f"Processing {idx}/{total_to_process}: {filename}")
            progress_text.insert(tk.END, f"[{idx}/{total_to_process}] Processing: {filename}\n")
            progress_text.see(tk.END)
            self.root.update()
            
            try:
                record = self.parse_gcode_file(filepath)
            except Exception as e:
                errors += 1
                progress_text.insert(tk.END, f"  PARSE EXCEPTION: {str(e)[:100]}\n")
                progress_text.see(tk.END)
                continue

            if record:
                try:
                    # Check for duplicate in this scan and assign unique suffix
                    original_prog_num = record.program_number
                    if record.program_number in seen_in_scan:
                        # Find next available suffix
                        suffix = 1
                        while f"{original_prog_num}({suffix})" in seen_in_scan:
                            suffix += 1
                        record.program_number = f"{original_prog_num}({suffix})"
                        progress_text.insert(tk.END, f"  DUPLICATE: {original_prog_num} -> saved as {record.program_number}\n")
                        progress_text.see(tk.END)
                        duplicates_within_processing += 1

                    # Track this file with its (possibly modified) program number
                    seen_in_scan[record.program_number] = filepath

                    # Check if exists in database
                    cursor.execute("SELECT program_number FROM programs WHERE program_number = ?",
                                 (record.program_number,))
                    exists = cursor.fetchone()

                    if exists:
                        # Update existing
                        cursor.execute('''
                            UPDATE programs SET
                                title = ?, spacer_type = ?, outer_diameter = ?, thickness = ?, thickness_display = ?,
                                center_bore = ?, hub_height = ?, hub_diameter = ?,
                                counter_bore_diameter = ?, counter_bore_depth = ?,
                                material = ?, last_modified = ?, file_path = ?,
                                detection_confidence = ?, detection_method = ?,
                                validation_status = ?, validation_issues = ?,
                                validation_warnings = ?, bore_warnings = ?, dimensional_issues = ?,
                                cb_from_gcode = ?, ob_from_gcode = ?, lathe = ?
                            WHERE program_number = ?
                        ''', (record.title, record.spacer_type, record.outer_diameter, record.thickness, record.thickness_display,
                             record.center_bore, record.hub_height, record.hub_diameter,
                             record.counter_bore_diameter, record.counter_bore_depth,
                             record.material, record.last_modified, record.file_path,
                             record.detection_confidence, record.detection_method,
                             record.validation_status, record.validation_issues,
                             record.validation_warnings, record.bore_warnings, record.dimensional_issues,
                             record.cb_from_gcode, record.ob_from_gcode, record.lathe,
                             record.program_number))
                        updated += 1
                    else:
                        # Insert new
                        cursor.execute('''
                            INSERT INTO programs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (record.program_number, record.title, record.spacer_type, record.outer_diameter,
                             record.thickness, record.thickness_display, record.center_bore, record.hub_height,
                             record.hub_diameter, record.counter_bore_diameter,
                             record.counter_bore_depth, record.paired_program,
                             record.material, record.notes, record.date_created,
                             record.last_modified, record.file_path, record.detection_confidence,
                             record.detection_method, record.validation_status,
                             record.validation_issues, record.validation_warnings,
                             record.bore_warnings, record.dimensional_issues,
                             record.cb_from_gcode, record.ob_from_gcode, record.lathe,
                             None, None, None))  # duplicate_type, parent_file, duplicate_group
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
        
        # Calculate total duplicates (both exact duplicates and name collisions)
        total_duplicates = len(exact_duplicates_db) + len(exact_duplicates_scan) + len(name_collisions_db) + len(name_collisions_scan)

        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"\n{'='*50}\n")
        progress_text.insert(tk.END, f"SCAN SUMMARY\n")
        progress_text.insert(tk.END, f"{'='*50}\n")
        progress_text.insert(tk.END, f"Total files scanned: {len(all_scanned_files)}\n")
        progress_text.insert(tk.END, f"Files to process: {len(files_to_process)}\n")
        progress_text.insert(tk.END, f"Duplicates skipped: {total_duplicates}\n")
        progress_text.insert(tk.END, f"  - Exact match (DB): {len(exact_duplicates_db)}\n")
        progress_text.insert(tk.END, f"  - Exact match (scan): {len(exact_duplicates_scan)}\n")
        progress_text.insert(tk.END, f"  - Name collision (DB): {len(name_collisions_db)}\n")
        progress_text.insert(tk.END, f"  - Name collision (scan): {len(name_collisions_scan)}\n")
        progress_text.insert(tk.END, f"Added: {added}\n")
        progress_text.insert(tk.END, f"Updated: {updated}\n")
        progress_text.insert(tk.END, f"Errors: {errors}\n")
        if duplicates_within_processing > 0:
            progress_text.insert(tk.END, f"Program number conflicts (saved with suffix): {duplicates_within_processing}\n")
        progress_text.insert(tk.END, f"Unique programs: {len(seen_in_scan)}\n")
        progress_text.see(tk.END)
        
        close_btn = tk.Button(progress_window, text="Close", 
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

        # Refresh filter dropdowns with new values
        self.refresh_filter_values()
        self.refresh_results()

    def scan_for_new_files(self):
        """Scan a folder for gcode files and import only NEW files not already in database"""
        folder = filedialog.askdirectory(title="Select Folder to Scan for New Files",
                                        initialdir=self.config.get("last_folder", ""))

        if not folder:
            return

        self.config["last_folder"] = folder
        self.save_config()

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Scanning for New Files...")
        progress_window.geometry("600x400")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Scanning...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 width=70, height=15)
        progress_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.update()

        # Get all existing files from database (filename and content hash)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM programs WHERE file_path IS NOT NULL")
        existing_files_data = {}  # {filename_lower: [file_paths]}

        for row in cursor.fetchall():
            file_path = row[0]
            if file_path and os.path.exists(file_path):
                basename = os.path.basename(file_path).lower()
                if basename not in existing_files_data:
                    existing_files_data[basename] = []
                existing_files_data[basename].append(file_path)

        # Scan for gcode files (with or without extension)
        gcode_files = []
        name_collisions = []  # Files with same name but need content check

        for root, dirs, files in os.walk(folder):
            for file in files:
                # Match any file containing o##### pattern (4+ digits)
                if re.search(r'[oO]\d{4,}', file):
                    filepath = os.path.join(root, file)
                    basename_lower = file.lower()

                    # Check if filename exists in database
                    if basename_lower in existing_files_data:
                        # Need to check content to see if it's exact duplicate
                        name_collisions.append((filepath, existing_files_data[basename_lower]))
                    else:
                        # New filename, safe to add
                        gcode_files.append(filepath)

        # Check name collisions for exact duplicates vs different content
        exact_duplicates = []
        different_content = []

        for new_file, existing_paths in name_collisions:
            # Read new file content
            try:
                with open(new_file, 'r', encoding='utf-8', errors='ignore') as f:
                    new_content = f.read()

                # Compare with existing file(s)
                is_exact_match = False
                for existing_path in existing_paths:
                    try:
                        with open(existing_path, 'r', encoding='utf-8', errors='ignore') as f:
                            existing_content = f.read()

                        if new_content == existing_content:
                            is_exact_match = True
                            break
                    except:
                        continue

                if is_exact_match:
                    exact_duplicates.append(new_file)
                else:
                    different_content.append((new_file, existing_paths[0]))
            except:
                # If can't read, treat as different content (to be safe)
                different_content.append((new_file, existing_paths[0]))

        progress_label.config(text=f"Analyzing files...")
        progress_text.insert(tk.END, f"Total files scanned: {len(gcode_files) + len(name_collisions)}\n")
        progress_text.insert(tk.END, f"New files (unique names): {len(gcode_files)}\n")
        progress_text.insert(tk.END, f"Exact duplicates (ignored): {len(exact_duplicates)}\n")
        progress_text.insert(tk.END, f"Name collisions (different content): {len(different_content)}\n\n")

        # Show exact duplicates being skipped
        if exact_duplicates:
            progress_text.insert(tk.END, f"=== SKIPPING EXACT DUPLICATES ===\n")
            for dup_file in exact_duplicates[:10]:
                progress_text.insert(tk.END, f"  SKIP: {os.path.basename(dup_file)} (exact match already in database)\n")
            if len(exact_duplicates) > 10:
                progress_text.insert(tk.END, f"  ... and {len(exact_duplicates) - 10} more\n")
            progress_text.insert(tk.END, f"\n")

        # Warn about name collisions
        if different_content:
            progress_text.insert(tk.END, f"⚠️  WARNING - NAME COLLISIONS DETECTED ===\n")
            progress_text.insert(tk.END, f"The following files have the same name as files in the database\n")
            progress_text.insert(tk.END, f"but DIFFERENT CONTENT. You must rename them before adding!\n\n")
            for new_file, existing_file in different_content[:10]:
                progress_text.insert(tk.END, f"  ⚠️  {os.path.basename(new_file)}\n")
                progress_text.insert(tk.END, f"     New: {new_file}\n")
                progress_text.insert(tk.END, f"     Existing: {existing_file}\n\n")
            if len(different_content) > 10:
                progress_text.insert(tk.END, f"  ... and {len(different_content) - 10} more\n")
            progress_text.insert(tk.END, f"\nPlease rename these files and scan again.\n\n")

        progress_text.insert(tk.END, f"Processing {len(gcode_files)} new files...\n\n")
        progress_text.see(tk.END)
        self.root.update()

        if len(gcode_files) == 0:
            progress_label.config(text="No new files found!")
            close_btn = tk.Button(progress_window, text="Close",
                                 command=progress_window.destroy,
                                 bg=self.button_bg, fg=self.fg_color,
                                 font=("Arial", 10, "bold"))
            close_btn.pack(pady=10)
            conn.close()  # Close the database connection
            return

        # Process files
        added = 0
        errors = 0
        duplicates = 0

        # Track which program numbers we've seen in this scan
        seen_in_scan = {}  # program_number -> filepath

        for idx, filepath in enumerate(gcode_files, 1):
            filename = os.path.basename(filepath)

            # Check file size
            try:
                file_size = os.path.getsize(filepath)
                size_kb = file_size / 1024
            except:
                size_kb = 0

            progress_label.config(text=f"Processing {idx}/{len(gcode_files)}: {filename}")
            progress_text.insert(tk.END, f"[{idx}/{len(gcode_files)}] Processing: {filename} ({size_kb:.1f} KB)\n")
            progress_text.see(tk.END)
            self.root.update()

            try:
                progress_text.insert(tk.END, f"  Parsing file...\n")
                progress_text.see(tk.END)
                self.root.update()

                record = self.parse_gcode_file(filepath)

                progress_text.insert(tk.END, f"  Parse complete.\n")
                progress_text.see(tk.END)
                self.root.update()
            except Exception as e:
                errors += 1
                progress_text.insert(tk.END, f"  PARSE EXCEPTION: {str(e)[:100]}\n")
                progress_text.see(tk.END)
                self.root.update()
                continue

            if record:
                try:
                    # Check for duplicate in this scan and assign unique suffix
                    original_prog_num = record.program_number
                    if record.program_number in seen_in_scan:
                        # Find next available suffix
                        suffix = 1
                        while f"{original_prog_num}({suffix})" in seen_in_scan:
                            suffix += 1
                        record.program_number = f"{original_prog_num}({suffix})"
                        progress_text.insert(tk.END, f"  DUPLICATE: {original_prog_num} -> saved as {record.program_number}\n")
                        progress_text.see(tk.END)
                        duplicates_within_processing += 1

                    # Track this file with its (possibly modified) program number
                    seen_in_scan[record.program_number] = filepath

                    # Insert new record
                    cursor.execute('''
                        INSERT INTO programs (
                            program_number, title, spacer_type, outer_diameter, thickness, thickness_display,
                            center_bore, hub_height, hub_diameter,
                            counter_bore_diameter, counter_bore_depth,
                            paired_program, material, notes, date_created, last_modified, file_path,
                            detection_confidence, detection_method,
                            validation_status, validation_issues,
                            validation_warnings, bore_warnings, dimensional_issues,
                            cb_from_gcode, ob_from_gcode, lathe,
                            duplicate_type, parent_file, duplicate_group
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record.program_number,
                        record.title,
                        record.spacer_type,
                        record.outer_diameter,
                        record.thickness,
                        record.thickness_display,
                        record.center_bore,
                        record.hub_height,
                        record.hub_diameter,
                        record.counter_bore_diameter,
                        record.counter_bore_depth,
                        record.paired_program,
                        record.material,
                        record.notes,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        filepath,
                        record.detection_confidence,
                        record.detection_method,
                        record.validation_status,
                        record.validation_issues,
                        record.validation_warnings,
                        record.bore_warnings,
                        record.dimensional_issues,
                        record.cb_from_gcode,
                        record.ob_from_gcode,
                        record.lathe,
                        None,  # duplicate_type
                        None,  # parent_file
                        None   # duplicate_group
                    ))
                    added += 1
                    progress_text.insert(tk.END, f"  ADDED: {record.program_number}\n")
                    progress_text.see(tk.END)
                    self.root.update()
                except sqlite3.Error as e:
                    errors += 1
                    progress_text.insert(tk.END, f"  DATABASE ERROR: {str(e)[:100]}\n")
                    progress_text.see(tk.END)
                    self.root.update()
            else:
                errors += 1
                progress_text.insert(tk.END, f"  PARSE ERROR: Could not extract data\n")
                progress_text.see(tk.END)
                self.root.update()

        conn.commit()
        conn.close()

        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"\n{'='*50}\n")
        progress_text.insert(tk.END, f"New files found: {len(gcode_files)}\n")
        progress_text.insert(tk.END, f"Duplicates: {duplicates}\n")
        progress_text.insert(tk.END, f"Added: {added}\n")
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

    def rescan_database(self):
        """Re-parse all files already in database to refresh with latest parser improvements"""
        # Confirm with user
        response = messagebox.askyesno(
            "Rescan Database",
            "This will re-parse ALL files in the database to refresh their data.\n\n"
            "This is useful after parser improvements (like the updated hub height detection).\n\n"
            "Files will be re-analyzed but NOT moved or renamed.\n\n"
            "Continue?",
            icon='question'
        )

        if not response:
            return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Rescanning Database...")
        progress_window.geometry("700x500")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Rescanning files...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 font=("Courier", 9),
                                                 width=80, height=20)
        progress_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.update()

        # Get all files from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT program_number, file_path FROM programs WHERE file_path IS NOT NULL")
        all_files = cursor.fetchall()

        total_files = len(all_files)
        progress_text.insert(tk.END, f"Found {total_files} files in database\n")
        progress_text.insert(tk.END, f"Starting re-scan...\n\n")
        progress_text.see(tk.END)
        self.root.update()

        # Import parser
        from improved_gcode_parser import ImprovedGCodeParser
        parser = ImprovedGCodeParser()

        updated = 0
        skipped = 0
        errors = 0

        for idx, (prog_num, file_path) in enumerate(all_files, 1):
            filename = os.path.basename(file_path)

            # Update progress
            if idx % 50 == 0 or idx == total_files:
                progress_label.config(text=f"Rescanning... {idx}/{total_files} files")
                self.root.update()

            # Check if file exists
            if not os.path.exists(file_path):
                skipped += 1
                if idx <= 10 or idx % 100 == 0:  # Show first 10 and every 100th
                    progress_text.insert(tk.END, f"[{idx}/{total_files}] {filename} - SKIP (file not found)\n")
                    progress_text.see(tk.END)
                    self.root.update()
                continue

            # Parse the file
            try:
                parse_result = parser.parse_file(file_path)

                if not parse_result:
                    errors += 1
                    if idx <= 10 or idx % 100 == 0:
                        progress_text.insert(tk.END, f"[{idx}/{total_files}] {filename} - ERROR (parse failed)\n")
                        progress_text.see(tk.END)
                        self.root.update()
                    continue

                # Calculate validation status (prioritized by severity)
                validation_status = "PASS"
                if parse_result.validation_issues:
                    validation_status = "CRITICAL"  # RED - Critical errors
                elif parse_result.bore_warnings:
                    validation_status = "BORE_WARNING"  # ORANGE - Bore dimension warnings
                elif parse_result.dimensional_issues:
                    validation_status = "DIMENSIONAL"  # PURPLE - P-code/thickness mismatches
                elif parse_result.validation_warnings:
                    validation_status = "WARNING"  # YELLOW - General warnings

                # Update database with refreshed data
                # Note: paired_program not updated (not in parser result)
                cursor.execute("""
                    UPDATE programs
                    SET title = ?,
                        spacer_type = ?,
                        outer_diameter = ?,
                        thickness = ?,
                        thickness_display = ?,
                        center_bore = ?,
                        hub_height = ?,
                        hub_diameter = ?,
                        counter_bore_diameter = ?,
                        counter_bore_depth = ?,
                        material = ?,
                        detection_confidence = ?,
                        detection_method = ?,
                        validation_status = ?,
                        validation_issues = ?,
                        validation_warnings = ?,
                        cb_from_gcode = ?,
                        ob_from_gcode = ?,
                        bore_warnings = ?,
                        dimensional_issues = ?,
                        lathe = ?
                    WHERE program_number = ?
                """, (
                    parse_result.title,
                    parse_result.spacer_type,
                    parse_result.outer_diameter,
                    parse_result.thickness,
                    parse_result.thickness_display,
                    parse_result.center_bore,
                    parse_result.hub_height,
                    parse_result.hub_diameter,
                    parse_result.counter_bore_diameter,
                    parse_result.counter_bore_depth,
                    parse_result.material,
                    parse_result.detection_confidence,
                    parse_result.detection_method,
                    validation_status,
                    '|'.join(parse_result.validation_issues) if parse_result.validation_issues else None,
                    '|'.join(parse_result.validation_warnings) if parse_result.validation_warnings else None,
                    parse_result.cb_from_gcode,
                    parse_result.ob_from_gcode,
                    '|'.join(parse_result.bore_warnings) if parse_result.bore_warnings else None,
                    '|'.join(parse_result.dimensional_issues) if parse_result.dimensional_issues else None,
                    parse_result.lathe,
                    prog_num
                ))

                updated += 1

                # Show first 10, then every 100th, and last 10
                if idx <= 10 or idx % 100 == 0 or idx > total_files - 10:
                    progress_text.insert(tk.END, f"[{idx}/{total_files}] {filename} - ✓ Updated\n")
                    progress_text.see(tk.END)
                    self.root.update()

            except Exception as e:
                errors += 1
                if idx <= 10 or idx % 100 == 0:
                    progress_text.insert(tk.END, f"[{idx}/{total_files}] {filename} - ERROR: {str(e)}\n")
                    progress_text.see(tk.END)
                    self.root.update()

        # Commit all changes
        conn.commit()
        conn.close()

        # Summary
        progress_label.config(text="Rescan Complete!")
        progress_text.insert(tk.END, f"\n{'='*60}\n")
        progress_text.insert(tk.END, f"RESCAN COMPLETE\n")
        progress_text.insert(tk.END, f"{'='*60}\n")
        progress_text.insert(tk.END, f"Total files: {total_files}\n")
        progress_text.insert(tk.END, f"Updated: {updated}\n")
        progress_text.insert(tk.END, f"Skipped (not found): {skipped}\n")
        progress_text.insert(tk.END, f"Errors: {errors}\n")
        progress_text.see(tk.END)

        # Close button
        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

        # Refresh the display
        self.refresh_results()

    def fix_program_numbers(self):
        """Update internal O-numbers to match filenames - FILTERED VIEW ONLY"""
        # Get currently displayed items (respects filters)
        displayed_items = self.tree.get_children()

        if not displayed_items:
            messagebox.showwarning("No Files",
                "No files in current view.\n\n"
                "Apply filters to show the files you want to fix.")
            return

        # Get program numbers and file info from filtered view
        filtered_files = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for item in displayed_items:
            values = self.tree.item(item)['values']
            if values:
                prog_num = values[0]
                # Get file path from database
                cursor.execute("""
                    SELECT program_number, file_path
                    FROM programs
                    WHERE program_number = ?
                """, (prog_num,))
                row = cursor.fetchone()
                if row and row[1]:  # Has file_path
                    filtered_files.append(row)

        conn.close()

        if not filtered_files:
            messagebox.showwarning("No Files with Paths",
                "No files in filtered view have physical file paths.\n\n"
                "Only files with linked physical files can be fixed.")
            return

        # Confirm operation
        msg = f"Fix program numbers for {len(filtered_files)} file(s) in filtered view?\n\n"
        msg += "This will:\n"
        msg += "• Read the O-number from each filename\n"
        msg += "• Update the internal O-number in the G-code file to match\n"
        msg += "• Update database program_number to match filename\n\n"
        msg += "Use this AFTER renaming files with 'Rename Duplicates'\n"
        msg += "to synchronize internal content with filenames.\n\n"
        msg += "Database backup will be created automatically."

        result = messagebox.askyesno("Confirm Fix Program Numbers", msg)
        if not result:
            return

        # Create backup
        if not self.backup_database():
            messagebox.showerror("Backup Failed",
                "Database backup failed. Operation canceled for safety.")
            return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Fixing Program Numbers (Filtered View)")
        progress_window.geometry("700x600")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Processing filtered files...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 font=("Courier", 9),
                                                 wrap=tk.WORD)
        progress_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.root.update()

        progress_text.insert(tk.END, f"Processing {len(filtered_files)} file(s) from filtered view...\n\n")

        # Process files from filtered view
        fixed = 0
        skipped = 0
        errors = 0
        total_files = len(filtered_files)

        # Open single database connection for all updates (prevents locking issues)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for file_idx, file_info in enumerate(filtered_files, 1):
            old_prog_num, filepath = file_info
            filename = os.path.basename(filepath)

            progress_label.config(text=f"Processing {file_idx}/{total_files}: {filename}")
            progress_text.insert(tk.END, f"[{file_idx}/{total_files}] {filename}\n")
            progress_text.see(tk.END)
            self.root.update()

            try:
                # Check if file exists
                if not os.path.exists(filepath):
                    progress_text.insert(tk.END, f"  SKIP: File not found\n\n")
                    skipped += 1
                    continue

                # Extract O-number from filename (e.g., o80556.txt -> O80556)
                match = re.search(r'[oO](\d+)', filename)
                if not match:
                    progress_text.insert(tk.END, f"  SKIP: Cannot extract O-number from filename\n\n")
                    skipped += 1
                    continue

                file_onumber = int(match.group(1))
                new_prog_str = f"O{file_onumber:05d}"  # Always 5 digits with leading zeros
                new_prog_str_lower = new_prog_str.lower()

                # Check if already correct
                if old_prog_num.lower() == new_prog_str_lower:
                    progress_text.insert(tk.END, f"  ✓ Already correct: {new_prog_str_lower}\n\n")
                    skipped += 1
                    continue

                # Read file content
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # Update internal program number (first line with O#####)
                updated = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    match_line = re.match(r'^([oO]\d{4,})\s*(\(.*)?$', stripped)
                    if match_line:
                        title_part = match_line.group(2) if match_line.group(2) else ""
                        if title_part:
                            lines[i] = f"{new_prog_str} {title_part}\n"
                        else:
                            lines[i] = f"{new_prog_str}\n"
                        updated = True
                        break

                if not updated:
                    progress_text.insert(tk.END, f"  ⚠️  WARNING: No O-number line found in file to update\n")

                # Write updated content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                # Update database with new program number
                cursor.execute("""
                    UPDATE programs
                    SET program_number = ?
                    WHERE program_number = ?
                """, (new_prog_str_lower, old_prog_num))
                conn.commit()

                progress_text.insert(tk.END, f"  ✓ {old_prog_num} → {new_prog_str_lower}\n\n")
                fixed += 1
                progress_text.see(tk.END)

            except Exception as e:
                progress_text.insert(tk.END, f"  ❌ ERROR: {str(e)[:100]}\n\n")
                progress_text.see(tk.END)
                errors += 1

        # Close database connection
        conn.close()

        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"\n{'='*50}\n")
        progress_text.insert(tk.END, f"FIX PROGRAM NUMBERS - SUMMARY\n")
        progress_text.insert(tk.END, f"{'='*50}\n")
        progress_text.insert(tk.END, f"Files processed: {total_files}\n")
        progress_text.insert(tk.END, f"Successfully fixed: {fixed}\n")
        progress_text.insert(tk.END, f"Already correct/Skipped: {skipped}\n")
        progress_text.insert(tk.END, f"Errors: {errors}\n\n")
        progress_text.insert(tk.END, f"Internal O-numbers now match filenames.\n")
        progress_text.insert(tk.END, f"Database updated.\n")
        progress_text.see(tk.END)

        # Refresh the view to show new program numbers
        self.refresh_filter_values()
        self.refresh_results()

        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

    def clear_database(self):
        """Clear all records from the database"""
        # Confirm with user
        result = messagebox.askyesno(
            "Clear Database",
            "Are you sure you want to delete ALL records from the database?\n\n"
            "This action cannot be undone!",
            icon='warning'
        )

        if not result:
            return

        # Double confirm
        result2 = messagebox.askyesno(
            "Confirm Clear",
            "This will permanently delete all program records.\n\n"
            "Are you absolutely sure?",
            icon='warning'
        )

        if not result2:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get count before deletion
            cursor.execute("SELECT COUNT(*) FROM programs")
            count = cursor.fetchone()[0]

            # Delete all records
            cursor.execute("DELETE FROM programs")
            conn.commit()
            conn.close()

            # Refresh the display
            self.refresh_filter_values()
            self.refresh_results()

            messagebox.showinfo(
                "Database Cleared",
                f"Successfully deleted {count} records from the database.\n\n"
                "The database is now empty."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear database:\n{str(e)}")

    def save_database_profile(self):
        """Save current database as a named profile"""
        import shutil
        from datetime import datetime

        # Create profiles directory if it doesn't exist
        profiles_dir = os.path.join(os.path.dirname(self.db_path), "database_profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        # Prompt for profile name
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Save Database Profile")
        profile_window.geometry("450x200")
        profile_window.configure(bg=self.bg_color)
        profile_window.transient(self.root)
        profile_window.grab_set()

        tk.Label(profile_window,
                text="Save current database state as a profile",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=15)

        tk.Label(profile_window,
                text="Profile Name:",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=5)

        # Suggest default name with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_name = f"Profile_{timestamp}"

        entry = tk.Entry(profile_window, bg=self.input_bg, fg=self.fg_color,
                        font=("Arial", 11), width=40)
        entry.insert(0, default_name)
        entry.pack(pady=10)
        entry.focus()
        entry.select_range(0, tk.END)

        result = [None]

        def save():
            profile_name = entry.get().strip()
            if not profile_name:
                messagebox.showwarning("Invalid Name", "Please enter a profile name.")
                return

            # Remove any invalid filename characters
            profile_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '-', '_'))

            profile_path = os.path.join(profiles_dir, f"{profile_name}.db")

            # Check if profile already exists
            if os.path.exists(profile_path):
                overwrite = messagebox.askyesno(
                    "Profile Exists",
                    f"Profile '{profile_name}' already exists.\n\nOverwrite?"
                )
                if not overwrite:
                    return

            try:
                # Copy current database to profile
                shutil.copy2(self.db_path, profile_path)

                # Get record count
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM programs")
                count = cursor.fetchone()[0]
                conn.close()

                result[0] = profile_name
                messagebox.showinfo(
                    "Profile Saved",
                    f"Database profile '{profile_name}' saved successfully!\n\n"
                    f"Records: {count}\n"
                    f"Location: {profile_path}"
                )
                profile_window.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save profile:\n{str(e)}")

        def cancel():
            profile_window.destroy()

        btn_frame = tk.Frame(profile_window, bg=self.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="💾 Save", command=save,
                 bg=self.accent_color, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Cancel", command=cancel,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

        self.root.wait_window(profile_window)

    def load_database_profile(self):
        """Load a saved database profile"""
        import shutil

        profiles_dir = os.path.join(os.path.dirname(self.db_path), "database_profiles")

        # Check if profiles directory exists
        if not os.path.exists(profiles_dir):
            messagebox.showinfo(
                "No Profiles",
                "No saved profiles found.\n\n"
                "Use 'Save Profile' to create your first database profile."
            )
            return

        # Get list of profile files
        profile_files = [f for f in os.listdir(profiles_dir) if f.endswith('.db')]

        if not profile_files:
            messagebox.showinfo(
                "No Profiles",
                "No saved profiles found.\n\n"
                "Use 'Save Profile' to create your first database profile."
            )
            return

        # Create selection window
        select_window = tk.Toplevel(self.root)
        select_window.title("Load Database Profile")
        select_window.geometry("600x500")
        select_window.configure(bg=self.bg_color)
        select_window.transient(self.root)
        select_window.grab_set()

        tk.Label(select_window,
                text="Select a profile to load",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=15)

        # Listbox with profile info
        list_frame = tk.Frame(select_window, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, bg=self.input_bg, fg=self.fg_color,
                            font=("Courier", 10), yscrollcommand=scrollbar.set,
                            selectmode=tk.SINGLE)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # Populate listbox with profile info
        profile_data = []
        for profile_file in sorted(profile_files, reverse=True):
            profile_path = os.path.join(profiles_dir, profile_file)
            profile_name = profile_file[:-3]  # Remove .db extension

            # Get file stats
            stat = os.stat(profile_path)
            size_mb = stat.st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            # Get record count
            try:
                conn = sqlite3.connect(profile_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM programs")
                count = cursor.fetchone()[0]
                conn.close()
            except:
                count = "?"

            display = f"{profile_name:<35} | {count:>6} records | {modified} | {size_mb:.1f} MB"
            listbox.insert(tk.END, display)
            profile_data.append((profile_name, profile_path, count))

        def load_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a profile to load.")
                return

            idx = selection[0]
            profile_name, profile_path, count = profile_data[idx]

            # Confirm load
            result = messagebox.askyesno(
                "Confirm Load Profile",
                f"Load profile '{profile_name}'?\n\n"
                f"This will replace your current database with:\n"
                f"  • {count} records\n"
                f"  • From: {os.path.basename(profile_path)}\n\n"
                f"⚠️  Your current database will be backed up first.",
                icon='warning'
            )

            if not result:
                return

            try:
                # Backup current database
                backup_name = f"before_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                backup_path = os.path.join(os.path.dirname(self.db_path), "backups", backup_name)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(self.db_path, backup_path)

                # Load profile
                shutil.copy2(profile_path, self.db_path)

                # Refresh display
                self.refresh_filter_values()
                self.refresh_results()

                messagebox.showinfo(
                    "Profile Loaded",
                    f"Successfully loaded profile '{profile_name}'!\n\n"
                    f"Records loaded: {count}\n"
                    f"Previous database backed up to:\n{backup_name}"
                )

                select_window.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load profile:\n{str(e)}")

        def cancel():
            select_window.destroy()

        btn_frame = tk.Frame(select_window, bg=self.bg_color)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="📂 Load Selected", command=load_selected,
                 bg=self.accent_color, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=15).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Cancel", command=cancel,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=15).pack(side=tk.LEFT, padx=5)

    def manage_database_profiles(self):
        """Manage saved database profiles - view, delete, rename"""
        import shutil
        from datetime import datetime

        profiles_dir = os.path.join(os.path.dirname(self.db_path), "database_profiles")

        # Check if profiles directory exists
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir, exist_ok=True)

        # Create management window
        manage_window = tk.Toplevel(self.root)
        manage_window.title("Manage Database Profiles")
        manage_window.geometry("800x600")
        manage_window.configure(bg=self.bg_color)

        tk.Label(manage_window,
                text="Database Profile Manager",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 14, "bold")).pack(pady=15)

        # Treeview for profile list
        tree_frame = tk.Frame(manage_window, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ('name', 'records', 'date', 'size')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)

        tree.heading('name', text='Profile Name')
        tree.heading('records', text='Records')
        tree.heading('date', text='Date Modified')
        tree.heading('size', text='Size (MB)')

        tree.column('name', width=300)
        tree.column('records', width=100)
        tree.column('date', width=200)
        tree.column('size', width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_profile_list():
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Get profile files
            profile_files = [f for f in os.listdir(profiles_dir) if f.endswith('.db')]

            if not profile_files:
                tree.insert('', tk.END, values=("No profiles found - use 'Save Profile' to create one", "", "", ""))
                return

            for profile_file in sorted(profile_files, reverse=True):
                profile_path = os.path.join(profiles_dir, profile_file)
                profile_name = profile_file[:-3]

                # Get stats
                stat = os.stat(profile_path)
                size_mb = f"{stat.st_size / (1024 * 1024):.2f}"
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                # Get record count
                try:
                    conn = sqlite3.connect(profile_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM programs")
                    count = cursor.fetchone()[0]
                    conn.close()
                except:
                    count = "Error"

                tree.insert('', tk.END, values=(profile_name, count, modified, size_mb))

        def delete_profile():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a profile to delete.")
                return

            item = selection[0]
            profile_name = tree.item(item)['values'][0]

            if profile_name == "No profiles found - use 'Save Profile' to create one":
                return

            result = messagebox.askyesno(
                "Confirm Delete",
                f"Delete profile '{profile_name}'?\n\n"
                f"This cannot be undone!",
                icon='warning'
            )

            if result:
                try:
                    profile_path = os.path.join(profiles_dir, f"{profile_name}.db")
                    os.remove(profile_path)
                    refresh_profile_list()
                    messagebox.showinfo("Deleted", f"Profile '{profile_name}' deleted successfully.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete profile:\n{str(e)}")

        def export_profile():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a profile to export.")
                return

            item = selection[0]
            profile_name = tree.item(item)['values'][0]

            if profile_name == "No profiles found - use 'Save Profile' to create one":
                return

            # Ask where to save
            export_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                initialfile=f"{profile_name}.db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                title="Export Profile"
            )

            if export_path:
                try:
                    profile_path = os.path.join(profiles_dir, f"{profile_name}.db")
                    shutil.copy2(profile_path, export_path)
                    messagebox.showinfo("Exported", f"Profile exported to:\n{export_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export profile:\n{str(e)}")

        # Initial load
        refresh_profile_list()

        # Button frame
        btn_frame = tk.Frame(manage_window, bg=self.bg_color)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="🗑️ Delete", command=delete_profile,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="📤 Export", command=export_profile,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🔄 Refresh", command=refresh_profile_list,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Close", command=manage_window.destroy,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

    def fix_duplicates(self):
        """Fix duplicate program numbers by assigning new unique o##### values based on OD"""
        # Find duplicates in database (entries with (##) suffix)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find all programs with duplicate suffix pattern
        cursor.execute("""
            SELECT program_number, file_path, outer_diameter
            FROM programs
            WHERE program_number LIKE '%(%)'
            ORDER BY program_number
        """)
        duplicates = cursor.fetchall()

        if not duplicates:
            messagebox.showinfo("No Duplicates", "No duplicate programs found in the database.\n\n"
                              "Duplicates have a (1), (2), etc. suffix.")
            conn.close()
            return

        # Confirm with user
        result = messagebox.askyesno(
            "Fix Duplicates",
            f"Found {len(duplicates)} duplicate programs.\n\n"
            "This will:\n"
            "1. Assign new unique o##### program numbers based on OD\n"
            "2. Rename the files\n"
            "3. Update the internal program number in each file\n"
            "4. Update the database\n\n"
            "Proceed?"
        )

        if not result:
            conn.close()
            return

        # Get all existing program numbers (to avoid collisions)
        cursor.execute("SELECT program_number FROM programs")
        existing_programs = set(row[0] for row in cursor.fetchall())

        # Also check the filesystem for any o##### files
        # Get unique directories from duplicates
        directories = set()
        for _, file_path, _ in duplicates:
            if file_path:
                directories.add(os.path.dirname(file_path))

        # Scan directories for existing program numbers
        for directory in directories:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    match = re.search(r'[oO](\d{4,})', file)
                    if match:
                        existing_programs.add(f"o{match.group(1)}")

        conn.close()

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Fixing Duplicates...")
        progress_window.geometry("600x500")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Processing duplicates...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 width=70, height=20)
        progress_text.pack(padx=10, pady=10)

        self.root.update()

        # Process each duplicate
        fixed = 0
        errors = 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for old_program_number, file_path, outer_diameter in duplicates:
            progress_text.insert(tk.END, f"\nProcessing: {old_program_number}\n")
            progress_text.see(tk.END)
            self.root.update()

            # Determine OD range for new program number
            new_program_number = self._get_next_available_program_number(
                outer_diameter, existing_programs
            )

            if not new_program_number:
                progress_text.insert(tk.END, f"  ERROR: Could not find available program number\n")
                errors += 1
                continue

            # Add to existing set to prevent reuse
            existing_programs.add(new_program_number)

            progress_text.insert(tk.END, f"  New program number: {new_program_number}\n")

            # Update file if it exists
            if file_path and os.path.exists(file_path):
                try:
                    # Read file content (preserve original encoding and line endings)
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()

                    # Detect line ending style
                    if b'\r\n' in content_bytes:
                        line_ending = '\r\n'
                    elif b'\r' in content_bytes:
                        line_ending = '\r'
                    else:
                        line_ending = '\n'

                    # Decode content
                    try:
                        content = content_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        content = content_bytes.decode('latin-1')

                    # Split into lines (normalize first, then restore)
                    lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')

                    # Update internal program number
                    new_lines = []
                    internal_updated = False
                    for line in lines:
                        stripped = line.strip()
                        # Check if line is a program number (O followed by digits)
                        if re.match(r'^[oO]\d{4,}\s*$', stripped):
                            new_lines.append(f"O{new_program_number[1:]}")  # Use uppercase O
                            internal_updated = True
                        else:
                            new_lines.append(line)

                    # Write back to file with original line endings
                    with open(file_path, 'w', newline='') as f:
                        f.write(line_ending.join(new_lines))

                    if internal_updated:
                        progress_text.insert(tk.END, f"  Updated internal program number\n")

                    # Rename file
                    directory = os.path.dirname(file_path)
                    old_filename = os.path.basename(file_path)

                    # Determine new filename (preserve extension if any)
                    if '.' in old_filename:
                        ext = old_filename[old_filename.rfind('.'):]
                        new_filename = f"{new_program_number}{ext}"
                    else:
                        new_filename = new_program_number

                    new_file_path = os.path.join(directory, new_filename)

                    # Check if target file already exists
                    if os.path.exists(new_file_path):
                        progress_text.insert(tk.END, f"  WARNING: Target file already exists: {new_filename}\n")
                        errors += 1
                        continue

                    os.rename(file_path, new_file_path)
                    progress_text.insert(tk.END, f"  Renamed: {old_filename} -> {new_filename}\n")

                    # Update database
                    cursor.execute("""
                        UPDATE programs
                        SET program_number = ?, file_path = ?
                        WHERE program_number = ?
                    """, (new_program_number, new_file_path, old_program_number))

                    progress_text.insert(tk.END, f"  Database updated\n")
                    fixed += 1

                except Exception as e:
                    progress_text.insert(tk.END, f"  ERROR: {str(e)}\n")
                    errors += 1
            else:
                # File doesn't exist, just update database
                progress_text.insert(tk.END, f"  WARNING: File not found, updating database only\n")
                cursor.execute("""
                    UPDATE programs
                    SET program_number = ?
                    WHERE program_number = ?
                """, (new_program_number, old_program_number))
                fixed += 1

            progress_text.see(tk.END)
            self.root.update()

        conn.commit()
        conn.close()

        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"\n{'='*50}\n")
        progress_text.insert(tk.END, f"Fixed: {fixed}\n")
        progress_text.insert(tk.END, f"Errors: {errors}\n")
        progress_text.see(tk.END)

        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

        # Refresh display
        self.refresh_filter_values()
        self.refresh_results()

    def _get_next_available_program_number(self, outer_diameter: float, existing: set) -> str:
        """
        Get next available program number based on OD.

        OD-based ranges:
        - 7.0", 7.5", 8.0", 8.5" -> o7####
        - 6.0", 6.25", 6.5" -> o6####
        - 5.75" -> o5####
        - All others -> any available
        """
        # Determine preferred range based on OD
        if outer_diameter:
            if outer_diameter >= 7.0:
                preferred_ranges = [(70000, 79999), (80000, 89999), (60000, 69999), (50000, 59999)]
            elif outer_diameter >= 6.0:
                preferred_ranges = [(60000, 69999), (70000, 79999), (50000, 59999), (80000, 89999)]
            elif outer_diameter >= 5.5:
                preferred_ranges = [(50000, 59999), (60000, 69999), (70000, 79999), (80000, 89999)]
            else:
                preferred_ranges = [(50000, 59999), (60000, 69999), (70000, 79999), (80000, 89999)]
        else:
            # No OD info, try all ranges
            preferred_ranges = [(50000, 59999), (60000, 69999), (70000, 79999), (80000, 89999)]

        # Search for available number in preferred order
        for start, end in preferred_ranges:
            for num in range(start, end + 1):
                candidate = f"o{num}"
                if candidate not in existing and candidate.upper() not in existing:
                    return candidate

        # If all preferred ranges are full, search extended ranges
        for num in range(10000, 99999):
            candidate = f"o{num}"
            if candidate not in existing and candidate.upper() not in existing:
                return candidate

        return None

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

        # Duplicate Type filter (multi-select)
        selected_dup_types = self.filter_dup_type.get_selected()
        if selected_dup_types and len(selected_dup_types) < len(self.filter_dup_type.values):
            # Handle "None" selection (files with no duplicate_type)
            if "None" in selected_dup_types:
                other_types = [t for t in selected_dup_types if t != "None"]
                if other_types:
                    placeholders = ','.join('?' * len(other_types))
                    query += f" AND (duplicate_type IN ({placeholders}) OR duplicate_type IS NULL)"
                    params.extend(other_types)
                else:
                    query += " AND duplicate_type IS NULL"
            else:
                placeholders = ','.join('?' * len(selected_dup_types))
                query += f" AND duplicate_type IN ({placeholders})"
                params.extend(selected_dup_types)

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

        # Hub Diameter range
        if self.filter_hub_dia_min.get():
            query += " AND hub_diameter >= ?"
            params.append(float(self.filter_hub_dia_min.get()))
        if self.filter_hub_dia_max.get():
            query += " AND hub_diameter <= ?"
            params.append(float(self.filter_hub_dia_max.get()))

        # Hub Height range
        if self.filter_hub_h_min.get():
            query += " AND hub_height >= ?"
            params.append(float(self.filter_hub_h_min.get()))
        if self.filter_hub_h_max.get():
            query += " AND hub_height <= ?"
            params.append(float(self.filter_hub_h_max.get()))

        # Step Diameter range
        if self.filter_step_d_min.get():
            query += " AND counter_bore_diameter >= ?"
            params.append(float(self.filter_step_d_min.get()))
        if self.filter_step_d_max.get():
            query += " AND counter_bore_diameter <= ?"
            params.append(float(self.filter_step_d_max.get()))

        # Error text filter (searches in validation_issues, bore_warnings, dimensional_issues)
        if self.filter_error_text.get():
            error_search = f"%{self.filter_error_text.get()}%"
            query += " AND (validation_issues LIKE ? OR bore_warnings LIKE ? OR dimensional_issues LIKE ?)"
            params.extend([error_search, error_search, error_search])

        query += " ORDER BY program_number"

        # Note: Duplicates filter is applied after query in the display logic
        # since it requires checking for duplicate filenames across all results
        
        # Execute query
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        # Populate tree
        # Column indices (based on database schema):
        # 0:program_number, 1:title, 2:spacer_type, 3:outer_diameter, 4:thickness, 5:thickness_display,
        # 6:center_bore, 7:hub_height, 8:hub_diameter, 9:counter_bore_diameter, 10:counter_bore_depth,
        # 11:paired_program, 12:material, 13:notes, 14:date_created, 15:last_modified, 16:file_path,
        # 17:detection_confidence, 18:detection_method, 19:validation_status, ...

        # Build set of duplicate filenames (exact filenames that appear more than once)
        filename_counts = {}
        for row in results:
            if row[16]:  # file_path
                filename = os.path.basename(row[16]).lower()  # Case-insensitive
                filename_counts[filename] = filename_counts.get(filename, 0) + 1

        # Filenames that appear more than once are duplicates
        duplicate_filenames = {fn for fn, count in filename_counts.items() if count > 1}

        # Assign occurrence numbers to duplicates
        occurrence_tracker = {}
        filename_occurrences = {}  # Maps file_path to its occurrence number
        for row in results:
            if row[16]:  # file_path
                filename = os.path.basename(row[16]).lower()
                if filename in duplicate_filenames:
                    occurrence_tracker[filename] = occurrence_tracker.get(filename, 0) + 1
                    filename_occurrences[row[16]] = occurrence_tracker[filename]

        # Count status breakdown
        status_counts = {
            'CRITICAL': 0,
            'BORE_WARNING': 0,
            'DIMENSIONAL': 0,
            'WARNING': 0,
            'PASS': 0,
            'REPEAT': 0
        }

        for row in results:
            program_number = row[0]
            # Check if this filename is a duplicate and get its occurrence number
            is_dup = ""
            dup_num = ""
            if row[16]:  # file_path
                filename = os.path.basename(row[16]).lower()
                if filename in duplicate_filenames:
                    dup_num = filename_occurrences.get(row[16], 1)
                    is_dup = f"({dup_num})"

            # Apply duplicates filter - skip non-duplicates if filter is checked
            if self.filter_duplicates.get() and not is_dup:
                continue

            title = row[1] if row[1] else "-"  # NEW: Title from G-code
            spacer_type = row[2]  # Shifted from row[1]
            od = f"{row[3]:.3f}" if row[3] else "-"  # Shifted from row[2]

            # Use thickness_display (row[5]) if available, otherwise fall back to formatted thickness (row[4])
            thick = row[5] if row[5] else (f"{row[4]:.3f}" if row[4] else "-")  # Shifted from row[4]/row[3]

            cb = f"{row[6]:.1f}" if row[6] else "-"  # Shifted from row[5]

            # Hub Height - only applicable for hub_centric
            if spacer_type == 'hub_centric':
                hub_h = f"{row[7]:.2f}" if row[7] else "-"  # Shifted from row[6]
            else:
                hub_h = "N/A"

            # Hub Diameter (OB) - only applicable for hub_centric
            if spacer_type == 'hub_centric':
                hub_d = f"{row[8]:.1f}" if row[8] else "-"  # Shifted from row[7]
            else:
                hub_d = "N/A"

            # Counter Bore - only applicable for STEP parts
            if spacer_type == 'step':
                cb_bore = f"{row[9]:.1f}" if row[9] else "-"  # Shifted from row[8]
            else:
                cb_bore = "N/A"

            # Step Depth - only applicable for STEP parts (row[10] = counter_bore_depth)
            if spacer_type == 'step':
                step_d = f"{row[10]:.2f}" if row[10] else "-"
            else:
                step_d = "N/A"

            material = row[12] if row[12] else "-"  # Shifted from row[11]
            filename = os.path.basename(row[16]) if row[16] else "-"  # Shifted from row[15]

            # Lathe (index 26)
            lathe = row[26] if len(row) > 26 and row[26] else "-"

            # Validation status (index 19 - validation_status)
            validation_status = row[19] if len(row) > 19 and row[19] else "N/A"  # Shifted from row[18]

            # Count status
            if validation_status in status_counts:
                status_counts[validation_status] += 1
            elif validation_status == 'ERROR':  # Old status name
                status_counts['CRITICAL'] += 1

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
            elif validation_status == 'REPEAT':
                tag = 'repeat'  # GRAY - Duplicate files
            elif validation_status == 'PASS':
                tag = 'pass'  # GREEN - Pass
            # Old status names for backward compatibility
            elif validation_status == 'ERROR':
                tag = 'critical'

            self.tree.insert("", "end", values=(
                program_number, is_dup, title, spacer_type, lathe, od, thick, cb,
                hub_h, hub_d, cb_bore, step_d, material, validation_status, filename
            ), tags=(tag,))

        # Update count with status breakdown
        status_text = f"Results: {len(results)} programs  |  "
        status_parts = []
        if status_counts['CRITICAL'] > 0:
            status_parts.append(f"CRITICAL: {status_counts['CRITICAL']}")
        if status_counts['BORE_WARNING'] > 0:
            status_parts.append(f"BORE: {status_counts['BORE_WARNING']}")
        if status_counts['DIMENSIONAL'] > 0:
            status_parts.append(f"DIM: {status_counts['DIMENSIONAL']}")
        if status_counts['WARNING'] > 0:
            status_parts.append(f"WARN: {status_counts['WARNING']}")
        if status_counts['REPEAT'] > 0:
            status_parts.append(f"REPEAT: {status_counts['REPEAT']}")
        if status_counts['PASS'] > 0:
            status_parts.append(f"PASS: {status_counts['PASS']}")

        status_text += "  ".join(status_parts) if status_parts else "No status data"
        self.results_label.config(text=status_text)
        
    def clear_filters(self):
        """Clear all filter fields"""
        self.filter_program.delete(0, tk.END)
        self.filter_type.clear()
        self.filter_material.clear()
        self.filter_status.clear()
        self.filter_dup_type.clear()
        # All dimensional filters are now comboboxes - use .set("")
        self.filter_od_min.set("")
        self.filter_od_max.set("")
        self.filter_thickness_min.set("")
        self.filter_thickness_max.set("")
        self.filter_cb_min.set("")
        self.filter_cb_max.set("")
        self.filter_hub_dia_min.set("")
        self.filter_hub_dia_max.set("")
        self.filter_hub_h_min.set("")
        self.filter_hub_h_max.set("")
        self.filter_step_d_min.set("")
        self.filter_step_d_max.set("")
        self.filter_error_text.set("")
        self.filter_duplicates.set(False)
        self.refresh_results()
        
    def sort_column(self, col):
        """Sort treeview by column with toggle support"""
        # Initialize sort state if not exists
        if not hasattr(self, '_sort_state'):
            self._sort_state = {'column': None, 'reverse': False}

        # Toggle direction if same column, otherwise new sort
        if self._sort_state['column'] == col:
            self._sort_state['reverse'] = not self._sort_state['reverse']
        else:
            self._sort_state['column'] = col
            self._sort_state['reverse'] = False

        # Get all data
        children = self.tree.get_children('')

        def get_sort_value(child):
            """Get sortable value from column"""
            val = self.tree.set(child, col)
            # Handle empty/N/A values - put at end
            if val in ('-', 'N/A', ''):
                return (1, 0)  # (is_empty, value) - empty values sort last
            try:
                return (0, float(val))
            except:
                return (0, val.lower() if isinstance(val, str) else val)

        # Sort data
        data = sorted(
            children,
            key=get_sort_value,
            reverse=self._sort_state['reverse']
        )

        # Rearrange
        for index, child in enumerate(data):
            self.tree.move(child, '', index)

        # Update column header to show sort direction
        direction = "▼" if self._sort_state['reverse'] else "▲"
        for column in self.tree['columns']:
            # Reset all headers
            base_name = column.replace(" ▲", "").replace(" ▼", "")
            if column == col or column.replace(" ▲", "").replace(" ▼", "") == col:
                self.tree.heading(column, text=f"{base_name} {direction}",
                                 command=lambda c=base_name: self.sort_column(c))
            else:
                self.tree.heading(column, text=base_name,
                                 command=lambda c=base_name: self.sort_column(c))

    def apply_multi_sort(self):
        """Apply multi-column sorting based on dropdown selections"""
        # Get sort configurations
        sort_configs = []

        for col_combo, dir_combo in [(self.sort1_col, self.sort1_dir),
                                     (self.sort2_col, self.sort2_dir),
                                     (self.sort3_col, self.sort3_dir)]:
            col = col_combo.get()
            if col:  # Only add if column is selected
                reverse = dir_combo.get() == "High→Low"
                sort_configs.append((col, reverse))

        if not sort_configs:
            return

        # Get all children
        children = list(self.tree.get_children(''))

        def get_sort_value(child, column):
            """Get sortable value from column"""
            val = self.tree.set(child, column)
            # Handle empty/N/A values - put at end
            if val in ('-', 'N/A', ''):
                return (1, 0)  # (is_empty, value) - empty values sort last
            try:
                return (0, float(val))
            except:
                return (0, val.lower() if isinstance(val, str) else val)

        # Sort using stable sort - apply in reverse order of priority
        # (last sort first, then earlier sorts override while preserving order)
        sorted_children = children

        # Apply sorts in reverse order (last sort first, then override with earlier sorts)
        for col, reverse in reversed(sort_configs):
            sorted_children = sorted(
                sorted_children,
                key=lambda child: get_sort_value(child, col),
                reverse=reverse
            )

        # Rearrange
        for index, child in enumerate(sorted_children):
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
        import csv

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filepath:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get column names from database
            cursor.execute("PRAGMA table_info(programs)")
            columns = [col[1] for col in cursor.fetchall()]

            # Get all data
            cursor.execute("SELECT * FROM programs ORDER BY program_number")
            results = cursor.fetchall()

            # Write CSV with proper escaping
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(columns)

                # Data
                for row in results:
                    # Convert None to empty string
                    cleaned_row = [str(x) if x is not None else "" for x in row]
                    writer.writerow(cleaned_row)

            conn.close()
            messagebox.showinfo("Export Complete", f"Exported {len(results)} records to:\n{filepath}")

    def export_unused_numbers(self):
        """Export a CSV of unused program numbers within standard ranges"""
        import csv

        # Define ranges - full range from 00001 to 99999
        ranges = [
            ("o00001-o09999", 1, 9999),
            ("o10000-o19999", 10000, 19999),
            ("o20000-o29999", 20000, 29999),
            ("o30000-o39999", 30000, 39999),
            ("o40000-o49999", 40000, 49999),
            ("o50000-o59999", 50000, 59999),
            ("o60000-o69999", 60000, 69999),
            ("o70000-o79999", 70000, 79999),
            ("o80000-o89999", 80000, 89999),
            ("o90000-o99999", 90000, 99999),
        ]

        # Get all existing program numbers from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT program_number FROM programs")
        existing = set()
        for row in cursor.fetchall():
            prog = row[0]
            # Extract numeric part (handle duplicates like o70000(1))
            match = re.search(r'[oO]?(\d+)', str(prog))
            if match:
                existing.add(int(match.group(1)))
        conn.close()

        # Ask user for save location
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Unused Program Numbers"
        )

        if not filepath:
            return

        # Generate unused numbers for each range
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Range", "Program Number", "Available"])

            total_unused = 0
            for range_name, start, end in ranges:
                unused_in_range = []
                for num in range(start, end + 1):
                    if num not in existing:
                        unused_in_range.append(num)

                # Write unused numbers for this range
                for num in unused_in_range:
                    writer.writerow([range_name, f"o{num}", "Yes"])
                    total_unused += 1

        messagebox.showinfo(
            "Export Complete",
            f"Exported {total_unused} unused program numbers to:\n{filepath}\n\n"
            f"These are available numbers within standard OD ranges."
        )

    def find_and_mark_repeats(self):
        """Enhanced duplicate detection with parent/child relationships and classification"""
        import uuid
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Finding & Classifying Duplicates...")
        progress_window.geometry("700x500")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Analyzing database...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 width=80, height=20)
        progress_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.update()

        # Get all files from database with full info
        cursor.execute('''
            SELECT program_number, title, spacer_type, outer_diameter, thickness,
                   center_bore, hub_height, hub_diameter, counter_bore_diameter,
                   counter_bore_depth, last_modified, file_path, detection_confidence,
                   validation_status, date_created
            FROM programs
        ''')
        all_files = cursor.fetchall()

        progress_text.insert(tk.END, f"Found {len(all_files)} total files in database.\n")
        progress_text.insert(tk.END, f"Classifying duplicates...\n\n")
        progress_text.see(tk.END)
        self.root.update()

        # Build filename and content maps
        filename_map = {}  # filename -> list of files
        content_map = {}   # (title+dims) -> list of files

        for file_data in all_files:
            prog_num, title, stype, od, thick, cb, hub_h, hub_d, cb_d, cb_dep, modified, fpath, confidence, val_status, created = file_data

            filename = os.path.basename(fpath).lower() if fpath else ""

            # Add to filename map
            if filename:
                if filename not in filename_map:
                    filename_map[filename] = []
                filename_map[filename].append(file_data)

            # Create content key
            content_key = (
                title.strip().upper() if title else "",
                stype,
                round(od, 3) if od else None,
                round(thick, 3) if thick else None,
                round(cb, 3) if cb else None,
                round(hub_h, 3) if hub_h else None,
                round(hub_d, 3) if hub_d else None,
                round(cb_d, 3) if cb_d else None,
                round(cb_dep, 3) if cb_dep else None
            )

            if content_key not in content_map:
                content_map[content_key] = []
            content_map[content_key].append(file_data)

        # Classify duplicates
        solid_dups = 0
        name_collisions = 0
        content_dups = 0

        # Process SOLID DUPLICATES (same filename AND same content)
        for filename, files in filename_map.items():
            if len(files) > 1:
                # Check if they also have same content
                first_content = (files[0][1], files[0][2], files[0][3], files[0][4], files[0][5])
                all_same_content = all(
                    (f[1], f[2], f[3], f[4], f[5]) == first_content for f in files
                )

                if all_same_content:
                    # SOLID DUPLICATE - same filename, same content
                    group_id = str(uuid.uuid4())[:8]

                    # Choose parent: oldest file with best validation
                    def sort_key(f):
                        # Priority: 1) Validation status, 2) Confidence, 3) Oldest date
                        val_priority = {'PASS': 0, 'WARNING': 1, 'DIMENSIONAL': 2, 'BORE_WARNING': 3, 'CRITICAL': 4, 'REPEAT': 5}
                        conf_priority = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
                        date = f[14] if f[14] else f[10] if f[10] else '9999-12-31'  # created or modified
                        return (val_priority.get(f[13], 9), conf_priority.get(f[12], 9), date)

                    sorted_files = sorted(files, key=sort_key)
                    parent = sorted_files[0]
                    children = sorted_files[1:]

                    progress_text.insert(tk.END, f"SOLID DUP: {filename}\n")
                    progress_text.insert(tk.END, f"  ✓ Parent: {parent[0]} (oldest with best validation)\n")

                    # Mark children as REPEAT
                    for child in children:
                        cursor.execute('''
                            UPDATE programs
                            SET validation_status = 'REPEAT',
                                duplicate_type = 'SOLID',
                                parent_file = ?,
                                duplicate_group = ?
                            WHERE program_number = ?
                        ''', (parent[0], group_id, child[0]))
                        progress_text.insert(tk.END, f"  ✗ Child: {child[0]}\n")
                        solid_dups += 1

                    progress_text.insert(tk.END, "\n")
                    progress_text.see(tk.END)
                    self.root.update()
                else:
                    # NAME COLLISION - same filename, different content
                    group_id = str(uuid.uuid4())[:8]
                    progress_text.insert(tk.END, f"NAME COLLISION: {filename}\n")
                    for f in files:
                        cursor.execute('''
                            UPDATE programs
                            SET duplicate_type = 'NAME_COLLISION',
                                duplicate_group = ?
                            WHERE program_number = ?
                        ''', (group_id, f[0]))
                        progress_text.insert(tk.END, f"  ! {f[0]} - Different content, needs rename\n")
                        name_collisions += 1
                    progress_text.insert(tk.END, "\n")
                    progress_text.see(tk.END)
                    self.root.update()

        # Process CONTENT DUPLICATES (same content, different filenames)
        for content_key, files in content_map.items():
            if len(files) > 1:
                # Get unique filenames in this group
                filenames = set(os.path.basename(f[11]).lower() if f[11] else "" for f in files)

                if len(filenames) > 1:  # Different filenames but same content
                    group_id = str(uuid.uuid4())[:8]

                    # Choose parent: oldest file with best validation
                    def sort_key(f):
                        val_priority = {'PASS': 0, 'WARNING': 1, 'DIMENSIONAL': 2, 'BORE_WARNING': 3, 'CRITICAL': 4, 'REPEAT': 5}
                        conf_priority = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
                        date = f[14] if f[14] else f[10] if f[10] else '9999-12-31'
                        return (val_priority.get(f[13], 9), conf_priority.get(f[12], 9), date)

                    sorted_files = sorted(files, key=sort_key)
                    parent = sorted_files[0]
                    children = sorted_files[1:]

                    progress_text.insert(tk.END, f"CONTENT DUP: {content_key[0][:50]}\n")
                    progress_text.insert(tk.END, f"  ✓ Parent: {parent[0]} (oldest with best validation)\n")

                    for child in children:
                        cursor.execute('''
                            UPDATE programs
                            SET validation_status = 'REPEAT',
                                duplicate_type = 'CONTENT_DUP',
                                parent_file = ?,
                                duplicate_group = ?
                            WHERE program_number = ?
                        ''', (parent[0], group_id, child[0]))
                        progress_text.insert(tk.END, f"  ✗ Child: {child[0]}\n")
                        content_dups += 1

                    progress_text.insert(tk.END, "\n")
                    progress_text.see(tk.END)
                    self.root.update()

        conn.commit()
        conn.close()

        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"{'='*70}\n")
        progress_text.insert(tk.END, f"SOLID Duplicates (same file+content): {solid_dups}\n")
        progress_text.insert(tk.END, f"NAME Collisions (same name, diff content): {name_collisions}\n")
        progress_text.insert(tk.END, f"CONTENT Duplicates (diff name, same content): {content_dups}\n")
        progress_text.insert(tk.END, f"\nTotal duplicates found: {solid_dups + name_collisions + content_dups}\n")
        progress_text.see(tk.END)

        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

    def delete_duplicates(self):
        """Delete all duplicate files (REPEAT status) keeping only parent files"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count duplicates to be deleted
        cursor.execute("""
            SELECT COUNT(*) FROM programs
            WHERE validation_status = 'REPEAT'
        """)
        dup_count = cursor.fetchone()[0]

        if dup_count == 0:
            conn.close()
            messagebox.showinfo("No Duplicates",
                "No duplicate files found.\n\n"
                "Use 'Find Repeats' first to identify duplicates.")
            return

        # Get details about what will be deleted
        cursor.execute("""
            SELECT program_number, duplicate_type, parent_file
            FROM programs
            WHERE validation_status = 'REPEAT'
            ORDER BY duplicate_type, parent_file
        """)
        duplicates = cursor.fetchall()
        conn.close()

        # Confirmation dialog
        result = messagebox.askyesno(
            "Delete All Duplicates",
            f"This will DELETE {dup_count} duplicate record(s) from the DATABASE.\n\n"
            f"✓ Parent files (best versions) will be KEPT\n"
            f"✗ Child files (duplicates) will be DELETED\n\n"
            f"⚠️  The actual files on disk will NOT be deleted.\n"
            f"⚠️  Only database records will be removed.\n\n"
            f"Do you want to continue?",
            icon='warning'
        )

        if not result:
            return

        # Second confirmation - type "DELETE DUPLICATES"
        confirm_window = tk.Toplevel(self.root)
        confirm_window.title("Final Confirmation")
        confirm_window.geometry("500x250")
        confirm_window.configure(bg=self.bg_color)
        confirm_window.transient(self.root)
        confirm_window.grab_set()

        tk.Label(confirm_window,
                text=f"⚠️  You are about to delete {dup_count} duplicate records",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(confirm_window,
                text='Type "DELETE DUPLICATES" to confirm:',
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=10)

        confirm_entry = tk.Entry(confirm_window, bg=self.input_bg, fg=self.fg_color,
                                font=("Arial", 12), width=25)
        confirm_entry.pack(pady=10)
        confirm_entry.focus()

        confirmed = [False]

        def check_confirmation():
            if confirm_entry.get() == "DELETE DUPLICATES":
                confirmed[0] = True
                confirm_window.destroy()
            else:
                messagebox.showerror("Invalid", 'You must type "DELETE DUPLICATES" exactly to confirm.')

        def cancel_delete():
            confirm_window.destroy()

        btn_frame = tk.Frame(confirm_window, bg=self.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Confirm", command=check_confirmation,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=10).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Cancel", command=cancel_delete,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=10).pack(side=tk.LEFT, padx=5)

        # Bind Enter key to confirm
        confirm_entry.bind('<Return>', lambda e: check_confirmation())

        # Wait for window to close
        self.root.wait_window(confirm_window)

        if not confirmed[0]:
            return

        # Create database backup before deleting
        if not self.backup_database():
            messagebox.showerror("Backup Failed",
                "Database backup failed. Delete operation canceled for safety.\n\n"
                "Please check the error and try again.")
            return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Deleting Duplicates")
        progress_window.geometry("700x500")
        progress_window.configure(bg=self.bg_color)

        tk.Label(progress_window,
                text="Deleting duplicate records...",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=10)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                  bg=self.input_bg, fg=self.fg_color,
                                                  font=("Courier", 9),
                                                  wrap=tk.WORD)
        progress_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Group duplicates by type for reporting
        by_type = {}
        for prog_num, dup_type, parent in duplicates:
            if dup_type not in by_type:
                by_type[dup_type] = []
            by_type[dup_type].append((prog_num, parent))

        # Show what's being deleted
        progress_text.insert(tk.END, f"Deleting {dup_count} duplicate records:\n\n")

        for dup_type, items in by_type.items():
            progress_text.insert(tk.END, f"--- {dup_type or 'Unknown Type'} ({len(items)} records) ---\n")
            for prog_num, parent in items[:10]:  # Show first 10
                progress_text.insert(tk.END, f"  DELETE: {prog_num} (parent: {parent or 'N/A'})\n")
            if len(items) > 10:
                progress_text.insert(tk.END, f"  ... and {len(items) - 10} more\n")
            progress_text.insert(tk.END, "\n")
            self.root.update()

        # Delete from database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM programs
                WHERE validation_status = 'REPEAT'
            """)

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            progress_text.insert(tk.END, f"{'='*60}\n")
            progress_text.insert(tk.END, f"✓ Successfully deleted {deleted_count} duplicate record(s)\n")
            progress_text.insert(tk.END, f"✓ Parent files have been preserved\n")
            progress_text.insert(tk.END, f"⚠️  Files on disk were NOT deleted\n")

            # Refresh the display
            self.refresh_filter_values()
            self.refresh_results()

        except Exception as e:
            progress_text.insert(tk.END, f"\n\n❌ ERROR: {str(e)}\n")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

        # Add close button
        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

        # Refresh the display
        self.refresh_results()

    def compare_files(self):
        """Compare selected files side-by-side with difference highlighting"""
        # Get selected items from treeview
        selected_items = self.tree.selection()

        if len(selected_items) < 2:
            messagebox.showwarning("Selection Required",
                "Please select 2 or more files to compare.\n\n"
                "Hold Ctrl and click to select multiple files.")
            return

        if len(selected_items) > 4:
            result = messagebox.askyesno("Many Files Selected",
                f"You selected {len(selected_items)} files.\n\n"
                f"Comparing many files may be difficult to view.\n\n"
                f"Continue anyway?")
            if not result:
                return

        # Extract program numbers
        program_numbers = []
        for item in selected_items:
            values = self.tree.item(item)['values']
            if values:
                program_numbers.append(values[0])

        # Get file details from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(program_numbers))
        cursor.execute(f'''
            SELECT program_number, title, file_path, spacer_type, outer_diameter, thickness,
                   center_bore, hub_height, hub_diameter, counter_bore_diameter,
                   counter_bore_depth, validation_status, detection_confidence,
                   duplicate_type, parent_file, last_modified, date_created
            FROM programs
            WHERE program_number IN ({placeholders})
        ''', program_numbers)

        files_data = cursor.fetchall()
        conn.close()

        if len(files_data) < 2:
            messagebox.showerror("Error", "Could not retrieve file information from database.")
            return

        # Open comparison window
        FileComparisonWindow(self.root, files_data, self.bg_color, self.fg_color,
                           self.input_bg, self.button_bg, self.refresh_results, self)

    def rename_duplicate_files(self):
        """Rename physical files with duplicate filenames and update database - FILTERED VIEW ONLY"""
        # Get currently displayed items (respects filters)
        displayed_items = self.tree.get_children()

        if not displayed_items:
            messagebox.showwarning("No Files",
                "No files in current view.\n\n"
                "Apply filters to show the files you want to rename.")
            return

        # Get program numbers from filtered view
        filtered_program_numbers = []
        for item in displayed_items:
            values = self.tree.item(item)['values']
            if values:
                filtered_program_numbers.append(values[0])

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find files with duplicate filenames - ONLY IN FILTERED VIEW
        placeholders = ','.join('?' * len(filtered_program_numbers))
        cursor.execute(f"""
            SELECT program_number, file_path, duplicate_type, parent_file, duplicate_group,
                   validation_status
            FROM programs
            WHERE file_path IS NOT NULL
              AND program_number IN ({placeholders})
            ORDER BY file_path
        """, filtered_program_numbers)
        all_files = cursor.fetchall()

        # Group files by filename (case-insensitive)
        filename_groups = {}
        for prog_num, file_path, dup_type, parent, dup_group, val_status in all_files:
            if not file_path or not os.path.exists(file_path):
                continue

            basename = os.path.basename(file_path).lower()
            if basename not in filename_groups:
                filename_groups[basename] = []
            filename_groups[basename].append((prog_num, file_path, dup_type, parent, dup_group, val_status))

        # Find files that need renaming (duplicates)
        duplicates_to_rename = []
        for basename, files in filename_groups.items():
            if len(files) > 1:
                # Sort to determine parent (keep oldest with best validation)
                def sort_key(f):
                    val_priority = {'PASS': 0, 'WARNING': 1, 'DIMENSIONAL': 2, 'BORE_WARNING': 3, 'CRITICAL': 4, 'REPEAT': 5}
                    return val_priority.get(f[5], 9)

                sorted_files = sorted(files, key=sort_key)
                parent_file = sorted_files[0]
                child_files = sorted_files[1:]

                for child in child_files:
                    duplicates_to_rename.append({
                        'prog_num': child[0],
                        'old_path': child[1],
                        'parent_prog': parent_file[0],
                        'basename': basename
                    })

        conn.close()

        if not duplicates_to_rename:
            messagebox.showinfo("No Duplicates",
                "No duplicate filenames found.\n\n"
                "All files have unique names.")
            return

        # Show mode selection: Preview or Execute
        mode_choice = [None]

        mode_window = tk.Toplevel(self.root)
        mode_window.title("Rename Duplicate Files")
        mode_window.geometry("500x200")
        mode_window.configure(bg=self.bg_color)
        mode_window.transient(self.root)
        mode_window.grab_set()

        tk.Label(mode_window,
                text=f"Found {len(duplicates_to_rename)} file(s) with duplicate names",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=15)

        tk.Label(mode_window,
                text="This will assign new O-numbers (o59000+) to duplicate files.",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=5)

        tk.Label(mode_window,
                text="Updates: physical file, internal O-number, and database.",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=5)

        tk.Label(mode_window,
                text="Choose mode:",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=5)

        def preview_mode():
            mode_choice[0] = "preview"
            mode_window.destroy()

        def execute_mode():
            mode_choice[0] = "execute"
            mode_window.destroy()

        def cancel_mode():
            mode_window.destroy()

        btn_frame = tk.Frame(mode_window, bg=self.bg_color)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="🔍 Preview (Dry Run)",
                 command=preview_mode,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="▶️ Execute (Rename Files)",
                 command=execute_mode,
                 bg=self.accent_color, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Cancel",
                 command=cancel_mode,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=5)

        self.root.wait_window(mode_window)

        if mode_choice[0] is None:
            return

        dry_run = (mode_choice[0] == "preview")

        # Create backup if executing
        if not dry_run:
            if not self.backup_database():
                messagebox.showerror("Backup Failed",
                    "Database backup failed. Rename operation canceled for safety.")
                return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        if dry_run:
            progress_window.title("Rename Preview (Dry Run)")
        else:
            progress_window.title("Assigning New O-Numbers to Duplicates")
        progress_window.geometry("900x600")
        progress_window.configure(bg=self.bg_color)

        tk.Label(progress_window,
                text="Preview - Files that WOULD be assigned new O-numbers:" if dry_run else "Assigning new O-numbers...",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=10)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                  bg=self.input_bg, fg=self.fg_color,
                                                  font=("Courier", 9),
                                                  wrap=tk.WORD)
        progress_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if dry_run:
            progress_text.insert(tk.END, f"=== DRY RUN MODE - NO CHANGES WILL BE MADE ===\n\n")

        progress_text.insert(tk.END, f"Found {len(duplicates_to_rename)} duplicate file(s) in filtered view.\n")
        progress_text.insert(tk.END, f"Assigning available O-numbers (avoiding reserved 00000-01000)...\n\n")

        renamed_count = 0
        errors = 0

        # Get all existing program numbers to find available O-numbers
        conn_temp = sqlite3.connect(self.db_path)
        cursor_temp = conn_temp.cursor()
        cursor_temp.execute("SELECT program_number FROM programs")
        existing_program_numbers = set()
        for row in cursor_temp.fetchall():
            prog = row[0]
            # Extract numeric part
            match = re.search(r'o?(\d+)', prog, re.IGNORECASE)
            if match:
                existing_program_numbers.add(int(match.group(1)))
        conn_temp.close()

        # Reserved ranges (DO NOT USE for production files)
        reserved_ranges = [
            (0, 1000)  # Machine needed files (00000-01000)
        ]

        # Helper function to check if number is in reserved range
        def is_reserved(num):
            for reserved_start, reserved_end in reserved_ranges:
                if reserved_start <= num <= reserved_end:
                    return True
            return False

        # Find available O-numbers starting from 1001 (avoiding reserved 0-1000)
        def find_next_available_onumber(start=1001):
            """Find the next available O-number, skipping reserved ranges"""
            current = start
            while current < 100000:
                if current not in existing_program_numbers and not is_reserved(current):
                    existing_program_numbers.add(current)  # Reserve it
                    return current
                current += 1
            return None  # No available numbers found

        # Track used names to avoid collisions
        used_names = set()

        for idx, dup_info in enumerate(duplicates_to_rename, 1):
            prog_num = dup_info['prog_num']
            old_path = dup_info['old_path']
            parent_prog = dup_info['parent_prog']

            # Get available O-number
            new_onumber = find_next_available_onumber()

            # Check if we ran out of numbers
            if new_onumber is None:
                progress_text.insert(tk.END, f"[{idx}] ❌ ERROR: No available O-numbers in entire range (00000-99999)!\n\n")
                errors += 1
                continue

            # Format with leading zeros (always 5 digits: o01057, not o1057)
            new_prog_num = f"o{new_onumber:05d}"

            # Generate new filename
            old_dir = os.path.dirname(old_path)
            old_basename = os.path.basename(old_path)
            name_without_ext, ext = os.path.splitext(old_basename)

            # New filename with proper O-number (5 digits with leading zeros)
            new_basename = f"o{new_onumber:05d}{ext}"
            new_path = os.path.join(old_dir, new_basename)

            # Safety check - ensure new path doesn't exist
            if os.path.exists(new_path):
                progress_text.insert(tk.END, f"[{idx}] ⚠️  SKIP: {new_basename} already exists\n\n")
                continue

            used_names.add(new_basename.lower())

            try:
                if dry_run:
                    progress_text.insert(tk.END, f"[{idx}] WOULD RENAME:\n")
                    progress_text.insert(tk.END, f"    Old File: {old_basename}\n")
                    progress_text.insert(tk.END, f"    New File: {new_basename}\n")
                    progress_text.insert(tk.END, f"    Old Program: {prog_num} (parent: {parent_prog})\n")
                    progress_text.insert(tk.END, f"    New Program: {new_prog_num}\n\n")
                    renamed_count += 1
                else:
                    # Actually rename the physical file
                    os.rename(old_path, new_path)

                    # Update internal G-code program number
                    if not self.update_gcode_program_number(new_path, new_prog_num):
                        progress_text.insert(tk.END, f"    ⚠️  Warning: Could not update internal O-number\n")

                    # Update database with new path AND new program number
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE programs
                        SET file_path = ?,
                            program_number = ?
                        WHERE program_number = ?
                    """, (new_path, new_prog_num, prog_num))
                    conn.commit()
                    conn.close()

                    progress_text.insert(tk.END, f"[{idx}] ✓ RENAMED:\n")
                    progress_text.insert(tk.END, f"    Old File: {old_basename}\n")
                    progress_text.insert(tk.END, f"    New File: {new_basename}\n")
                    progress_text.insert(tk.END, f"    Old Program: {prog_num}\n")
                    progress_text.insert(tk.END, f"    New Program: {new_prog_num}\n\n")
                    renamed_count += 1

                progress_text.see(tk.END)
                self.root.update()

            except Exception as e:
                progress_text.insert(tk.END, f"[{idx}] ❌ ERROR: {prog_num}\n")
                progress_text.insert(tk.END, f"    {str(e)}\n\n")
                errors += 1
                progress_text.see(tk.END)
                self.root.update()

        # Summary
        progress_text.insert(tk.END, f"\n{'='*70}\n")
        if dry_run:
            progress_text.insert(tk.END, f"PREVIEW COMPLETE - No actual changes were made.\n")
            progress_text.insert(tk.END, f"Would assign new O-numbers to: {renamed_count} file(s)\n")
            progress_text.insert(tk.END, f"\nClick 'Execute' to apply these changes.\n")
        else:
            progress_text.insert(tk.END, f"OPERATION COMPLETE!\n")
            progress_text.insert(tk.END, f"Successfully assigned new O-numbers to: {renamed_count} file(s)\n")
            progress_text.insert(tk.END, f"Errors: {errors}\n")
            progress_text.insert(tk.END, f"\nAll files now have unique O-numbers (o59000+)\n")
            progress_text.insert(tk.END, f"Physical files renamed, internal O-numbers updated, database updated.\n")

            # Refresh display
            self.refresh_filter_values()
            self.refresh_results()

        progress_text.see(tk.END)

        # Close button
        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

    def organize_files_by_od(self):
        """Copy all database files to organized folder structure by OD"""
        import shutil

        # Ask user for destination folder
        dest_folder = filedialog.askdirectory(title="Select Destination Folder for Organized Files")

        if not dest_folder:
            return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Organizing Files by OD...")
        progress_window.geometry("600x400")
        progress_window.configure(bg=self.bg_color)

        progress_label = tk.Label(progress_window, text="Organizing files...",
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 width=70, height=15)
        progress_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.update()

        # Get all files from database with OD info
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT program_number, file_path, outer_diameter
            FROM programs
            WHERE file_path IS NOT NULL
        ''')
        all_files = cursor.fetchall()
        conn.close()

        progress_text.insert(tk.END, f"Found {len(all_files)} files in database.\n")
        progress_text.insert(tk.END, f"Destination: {dest_folder}\n\n")
        progress_text.see(tk.END)
        self.root.update()

        # OD folder mapping (round to standard sizes)
        od_folders = {
            5.75: "5.75 Round",
            6.00: "6.00 Round",
            6.25: "6.25 Round",
            6.50: "6.50 Round",
            7.00: "7.00 Round",
            7.50: "7.50 Round",
            8.00: "8.00 Round",
            8.50: "8.50 Round",
            9.50: "9.50 Round",
            10.25: "10.25 Round",
            10.50: "10.50 Round",
            13.00: "13.00 Round"
        }

        copied = 0
        skipped = 0
        errors = 0

        for idx, (prog_num, file_path, od) in enumerate(all_files, 1):
            progress_label.config(text=f"Processing {idx}/{len(all_files)}: {prog_num}")
            self.root.update()

            # Check if file exists
            if not os.path.exists(file_path):
                progress_text.insert(tk.END, f"SKIP: {prog_num} - file not found: {file_path}\n")
                progress_text.see(tk.END)
                skipped += 1
                continue

            # Determine OD folder
            if od is None:
                folder_name = "Unknown OD"
            else:
                # Find closest standard OD
                closest_od = min(od_folders.keys(), key=lambda x: abs(x - od))
                if abs(closest_od - od) <= 0.1:  # Within tolerance
                    folder_name = od_folders[closest_od]
                else:
                    folder_name = f"Other ({od:.2f})"

            # Create destination folder if needed
            od_folder_path = os.path.join(dest_folder, folder_name)
            os.makedirs(od_folder_path, exist_ok=True)

            # Copy file
            filename = os.path.basename(file_path)
            dest_path = os.path.join(od_folder_path, filename)

            try:
                shutil.copy2(file_path, dest_path)
                progress_text.insert(tk.END, f"COPY: {prog_num} -> {folder_name}/{filename}\n")
                progress_text.see(tk.END)
                copied += 1
            except Exception as e:
                progress_text.insert(tk.END, f"ERROR: {prog_num} - {str(e)[:100]}\n")
                progress_text.see(tk.END)
                errors += 1

        # Show results
        progress_label.config(text="Complete!")
        progress_text.insert(tk.END, f"\n{'='*60}\n")
        progress_text.insert(tk.END, f"Total files: {len(all_files)}\n")
        progress_text.insert(tk.END, f"Copied: {copied}\n")
        progress_text.insert(tk.END, f"Skipped: {skipped}\n")
        progress_text.insert(tk.END, f"Errors: {errors}\n")
        progress_text.see(tk.END)

        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

    def copy_filtered_view(self):
        """Copy currently filtered/displayed files to folder with OD subfolders and auto-rename"""
        import shutil

        # Get currently displayed items from treeview
        displayed_items = self.tree.get_children()
        if not displayed_items:
            messagebox.showwarning("No Results", "No files in current view to copy.\n\nPlease search/filter first.")
            return

        # Ask user: Preview or Execute?
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Copy Mode")
        preview_window.geometry("400x180")
        preview_window.configure(bg=self.bg_color)

        tk.Label(preview_window,
                text=f"Ready to copy {len(displayed_items)} files",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=15)

        tk.Label(preview_window,
                text="Choose operation mode:",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=5)

        mode_choice = [None]  # Use list to modify in nested function

        def preview_mode():
            mode_choice[0] = "preview"
            preview_window.destroy()

        def execute_mode():
            mode_choice[0] = "execute"
            preview_window.destroy()

        btn_frame = tk.Frame(preview_window, bg=self.bg_color)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="🔍 Preview (Dry Run)", command=preview_mode,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=18, height=2).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="▶️ Execute (Copy Files)", command=execute_mode,
                 bg=self.accent_color, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=18, height=2).pack(side=tk.LEFT, padx=5)

        # Wait for user choice
        self.root.wait_window(preview_window)

        if not mode_choice[0]:
            return  # User closed window

        dry_run = (mode_choice[0] == "preview")

        # Create database backup before executing (not for preview)
        if not dry_run:
            if not self.backup_database():
                messagebox.showerror("Backup Failed",
                    "Database backup failed. Operation canceled for safety.\n\n"
                    "Please check the error and try again.")
                return

        # Ask user for destination folder
        dest_folder = filedialog.askdirectory(title="Select Destination Folder for Filtered Files")
        if not dest_folder:
            return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        title_text = "Preview: Copy Filtered View" if dry_run else "Copying Filtered View..."
        progress_window.title(title_text)
        progress_window.geometry("700x500")
        progress_window.configure(bg=self.bg_color)

        label_text = "Preview Mode (No files will be copied)" if dry_run else "Copying files..."
        progress_label = tk.Label(progress_window, text=label_text,
                                 bg=self.bg_color, fg=self.fg_color,
                                 font=("Arial", 12))
        progress_label.pack(pady=20)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                 bg=self.input_bg, fg=self.fg_color,
                                                 width=80, height=20)
        progress_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.update()

        # Get file info from database for displayed items
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Extract program numbers from treeview
        program_numbers = []
        for item in displayed_items:
            values = self.tree.item(item)['values']
            if values:
                program_numbers.append(values[0])  # First column is Program #

        progress_text.insert(tk.END, f"Found {len(program_numbers)} files in current view.\n")
        progress_text.insert(tk.END, f"Destination: {dest_folder}\n\n")
        progress_text.see(tk.END)
        self.root.update()

        # Get file details from database
        placeholders = ','.join('?' * len(program_numbers))
        cursor.execute(f'''
            SELECT program_number, file_path, outer_diameter
            FROM programs
            WHERE program_number IN ({placeholders})
        ''', program_numbers)
        files_to_copy = cursor.fetchall()
        conn.close()

        # OD folder mapping
        od_folders = {
            5.75: "5.75 Round",
            6.00: "6.00 Round",
            6.25: "6.25 Round",
            6.50: "6.50 Round",
            7.00: "7.00 Round",
            7.50: "7.50 Round",
            8.00: "8.00 Round",
            8.50: "8.50 Round",
            9.50: "9.50 Round",
            10.25: "10.25 Round",
            10.50: "10.50 Round",
            13.00: "13.00 Round"
        }

        copied = 0
        skipped = 0
        errors = 0
        renamed = 0

        # Track filenames to handle collisions with auto-rename
        filename_tracker = {}  # {(folder, basename): occurrence_count}

        for idx, (prog_num, file_path, od) in enumerate(files_to_copy, 1):
            progress_label.config(text=f"Processing {idx}/{len(files_to_copy)}: {prog_num}")
            self.root.update()

            # Check if file exists
            if not file_path:
                progress_text.insert(tk.END, f"⚠️  SKIP: {prog_num} - no file path in database\n")
                progress_text.see(tk.END)
                skipped += 1
                continue

            if not os.path.exists(file_path):
                progress_text.insert(tk.END, f"⚠️  SKIP: {prog_num} - file not found at: {file_path}\n")
                progress_text.see(tk.END)
                skipped += 1
                continue

            # Determine OD folder
            if od is None:
                folder_name = "Unknown OD"
            else:
                closest_od = min(od_folders.keys(), key=lambda x: abs(x - od))
                if abs(closest_od - od) <= 0.1:
                    folder_name = od_folders[closest_od]
                else:
                    folder_name = f"Other ({od:.2f})"

            # Create destination folder
            od_folder_path = os.path.join(dest_folder, folder_name)
            os.makedirs(od_folder_path, exist_ok=True)

            # Get filename and handle collisions
            base_filename = os.path.basename(file_path)
            name_without_ext, ext = os.path.splitext(base_filename)

            # Check for collision and auto-rename with (1), (2), etc.
            folder_file_key = (od_folder_path, base_filename)
            if folder_file_key in filename_tracker:
                # Collision detected - add suffix
                filename_tracker[folder_file_key] += 1
                occurrence = filename_tracker[folder_file_key]
                new_filename = f"{name_without_ext}({occurrence}){ext}"
                progress_text.insert(tk.END, f"COLLISION: {base_filename} -> {new_filename}\n")
                renamed += 1
            else:
                # First occurrence
                filename_tracker[folder_file_key] = 1
                new_filename = base_filename

            dest_path = os.path.join(od_folder_path, new_filename)

            try:
                if dry_run:
                    # Preview mode - just show what would happen
                    progress_text.insert(tk.END, f"WOULD COPY: {prog_num} -> {folder_name}/{new_filename}\n")
                    progress_text.see(tk.END)
                    copied += 1
                else:
                    # Actually copy the file
                    shutil.copy2(file_path, dest_path)
                    progress_text.insert(tk.END, f"COPIED: {prog_num} -> {folder_name}/{new_filename}\n")
                    progress_text.see(tk.END)
                    copied += 1
            except Exception as e:
                progress_text.insert(tk.END, f"ERROR: {prog_num} - {str(e)[:100]}\n")
                progress_text.see(tk.END)
                errors += 1

        # Show results
        if dry_run:
            progress_label.config(text="Preview Complete (No files copied)")
            progress_text.insert(tk.END, f"\n{'='*70}\n")
            progress_text.insert(tk.END, f"PREVIEW MODE - No files were actually copied\n")
            progress_text.insert(tk.END, f"Total files: {len(files_to_copy)}\n")
            progress_text.insert(tk.END, f"Would copy: {copied}\n")
            progress_text.insert(tk.END, f"Would auto-rename (collisions): {renamed}\n")
            progress_text.insert(tk.END, f"Would skip: {skipped}\n")
            progress_text.insert(tk.END, f"Potential errors: {errors}\n")
        else:
            progress_label.config(text="Complete!")
            progress_text.insert(tk.END, f"\n{'='*70}\n")
            progress_text.insert(tk.END, f"Total files: {len(files_to_copy)}\n")
            progress_text.insert(tk.END, f"Copied: {copied}\n")
            progress_text.insert(tk.END, f"Auto-renamed (collisions): {renamed}\n")
            progress_text.insert(tk.END, f"Skipped: {skipped}\n")
            progress_text.insert(tk.END, f"Errors: {errors}\n")

        if skipped > 0:
            progress_text.insert(tk.END, f"\n⚠️  NOTE: {skipped} file(s) were skipped because the file paths in the database\n")
            progress_text.insert(tk.END, f"    are invalid or the files no longer exist at those locations.\n")
            progress_text.insert(tk.END, f"    You may need to use 'Scan Folder' to update the database with current file locations.\n")

        progress_text.see(tk.END)

        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

    def delete_filtered_view(self):
        """Delete currently filtered/displayed files from database (NOT from filesystem)"""
        # Get currently displayed items from treeview
        displayed_items = self.tree.get_children()
        if not displayed_items:
            messagebox.showwarning("No Results", "No files in current view to delete.\n\nPlease search/filter first.")
            return

        # Extract program numbers and details
        program_numbers = []
        program_details = []  # For preview
        for item in displayed_items:
            values = self.tree.item(item)['values']
            if values:
                program_numbers.append(values[0])  # First column is Program #
                # Store prog_num, filename, OD for preview
                prog_num = values[0]
                filename = os.path.basename(values[1]) if len(values) > 1 and values[1] else "Unknown"
                od = values[6] if len(values) > 6 else "N/A"
                program_details.append((prog_num, filename, od))

        count = len(program_numbers)

        # Ask user: Preview or Execute?
        mode_choice = [None]  # Use list to modify in nested function

        mode_window = tk.Toplevel(self.root)
        mode_window.title("Delete Mode Selection")
        mode_window.geometry("450x180")
        mode_window.configure(bg=self.bg_color)
        mode_window.transient(self.root)
        mode_window.grab_set()

        tk.Label(mode_window,
                text=f"Delete {count} record(s) from database",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=15)

        tk.Label(mode_window,
                text="Choose mode:",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 10)).pack(pady=5)

        def preview_mode():
            mode_choice[0] = "preview"
            mode_window.destroy()

        def execute_mode():
            mode_choice[0] = "execute"
            mode_window.destroy()

        def cancel_mode():
            mode_window.destroy()

        btn_frame = tk.Frame(mode_window, bg=self.bg_color)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="🔍 Preview (Dry Run)",
                 command=preview_mode,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="▶️ Execute (Delete Records)",
                 command=execute_mode,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Cancel",
                 command=cancel_mode,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=5)

        # Wait for user choice
        self.root.wait_window(mode_window)

        if mode_choice[0] is None:
            return  # User canceled

        dry_run = (mode_choice[0] == "preview")

        # If executing (not preview), require "DELETE" confirmation
        if not dry_run:
            confirm_window = tk.Toplevel(self.root)
            confirm_window.title("Final Confirmation")
            confirm_window.geometry("400x200")
            confirm_window.configure(bg=self.bg_color)
            confirm_window.transient(self.root)
            confirm_window.grab_set()

            tk.Label(confirm_window,
                    text=f"You are about to delete {count} records",
                    bg=self.bg_color, fg=self.fg_color,
                    font=("Arial", 12, "bold")).pack(pady=10)

            tk.Label(confirm_window,
                    text='Type "DELETE" to confirm:',
                    bg=self.bg_color, fg=self.fg_color,
                    font=("Arial", 10)).pack(pady=10)

            confirm_entry = tk.Entry(confirm_window, bg=self.input_bg, fg=self.fg_color,
                                    font=("Arial", 12), width=20)
            confirm_entry.pack(pady=10)
            confirm_entry.focus()

            confirmed = [False]  # Use list to modify in nested function

            def check_confirmation():
                if confirm_entry.get() == "DELETE":
                    confirmed[0] = True
                    confirm_window.destroy()
                else:
                    messagebox.showerror("Invalid", 'You must type "DELETE" exactly to confirm.')

            def cancel_delete():
                confirm_window.destroy()

            btn_frame = tk.Frame(confirm_window, bg=self.bg_color)
            btn_frame.pack(pady=10)

            tk.Button(btn_frame, text="Confirm", command=check_confirmation,
                     bg=self.button_bg, fg=self.fg_color,
                     font=("Arial", 10, "bold"), width=10).pack(side=tk.LEFT, padx=5)

            tk.Button(btn_frame, text="Cancel", command=cancel_delete,
                     bg=self.button_bg, fg=self.fg_color,
                     font=("Arial", 10, "bold"), width=10).pack(side=tk.LEFT, padx=5)

            # Bind Enter key to confirm
            confirm_entry.bind('<Return>', lambda e: check_confirmation())

            # Wait for window to close
            self.root.wait_window(confirm_window)

            if not confirmed[0]:
                return

            # Create database backup before executing delete
            if not self.backup_database():
                messagebox.showerror("Backup Failed",
                    "Database backup failed. Delete operation canceled for safety.\n\n"
                    "Please check the error and try again.")
                return

        # Show progress window
        progress_window = tk.Toplevel(self.root)
        if dry_run:
            progress_window.title("Delete Preview (Dry Run)")
        else:
            progress_window.title("Deleting Records")
        progress_window.geometry("700x500")
        progress_window.configure(bg=self.bg_color)

        tk.Label(progress_window,
                text="Preview - Records that WOULD be deleted:" if dry_run else "Deleting database records...",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 12, "bold")).pack(pady=10)

        progress_text = scrolledtext.ScrolledText(progress_window,
                                                  bg=self.input_bg, fg=self.fg_color,
                                                  font=("Courier", 9),
                                                  wrap=tk.WORD)
        progress_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Process deletions
        deleted_count = 0
        try:
            if dry_run:
                # Preview mode - just show what would be deleted
                progress_text.insert(tk.END, f"=== DRY RUN MODE - NO CHANGES WILL BE MADE ===\n\n")
                progress_text.insert(tk.END, f"The following {count} record(s) WOULD be deleted from the database:\n\n")

                for prog_num, filename, od in program_details:
                    progress_text.insert(tk.END, f"WOULD DELETE: {prog_num} - {filename} (OD: {od})\n")
                    self.root.update()

                deleted_count = count  # For summary message
                progress_text.insert(tk.END, f"\n{'='*60}\n")
                progress_text.insert(tk.END, f"Preview complete. {count} record(s) WOULD be deleted.\n")
                progress_text.insert(tk.END, f"No actual changes were made to the database.\n")
            else:
                # Execute mode - actually delete from database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                placeholders = ','.join('?' * len(program_numbers))
                cursor.execute(f'''
                    DELETE FROM programs
                    WHERE program_number IN ({placeholders})
                ''', program_numbers)

                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()

                # Show deleted records
                for prog_num, filename, od in program_details:
                    progress_text.insert(tk.END, f"DELETED: {prog_num} - {filename} (OD: {od})\n")
                    self.root.update()

                progress_text.insert(tk.END, f"\n{'='*60}\n")
                progress_text.insert(tk.END, f"Successfully deleted {deleted_count} record(s) from the database.\n")
                progress_text.insert(tk.END, f"⚠️  The files on disk were NOT deleted.\n")

                # Refresh the display
                self.refresh_filter_values()
                self.refresh_results()

        except Exception as e:
            progress_text.insert(tk.END, f"\n\n❌ ERROR: {str(e)}\n")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

        # Add close button
        close_btn = tk.Button(progress_window, text="Close",
                             command=progress_window.destroy,
                             bg=self.button_bg, fg=self.fg_color,
                             font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

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

    def show_statistics(self):
        """Show comprehensive database statistics with filtering support"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Database Statistics")
        stats_window.geometry("1200x800")
        stats_window.configure(bg=self.bg_color)

        # Create notebook for different stat views
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Get current filters to show filtered vs total stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build filter query
        filter_query = "SELECT COUNT(*) FROM programs WHERE 1=1"
        filter_params = []

        # Apply current filters
        if hasattr(self, 'filter_od_min') and self.filter_od_min.get():
            filter_query += " AND outer_diameter >= ?"
            filter_params.append(float(self.filter_od_min.get()))
        if hasattr(self, 'filter_od_max') and self.filter_od_max.get():
            filter_query += " AND outer_diameter <= ?"
            filter_params.append(float(self.filter_od_max.get()))
        if hasattr(self, 'filter_thickness_min') and self.filter_thickness_min.get():
            filter_query += " AND thickness >= ?"
            filter_params.append(float(self.filter_thickness_min.get()))
        if hasattr(self, 'filter_thickness_max') and self.filter_thickness_max.get():
            filter_query += " AND thickness <= ?"
            filter_params.append(float(self.filter_thickness_max.get()))
        if hasattr(self, 'filter_cb_min') and self.filter_cb_min.get():
            filter_query += " AND center_bore >= ?"
            filter_params.append(float(self.filter_cb_min.get()))
        if hasattr(self, 'filter_cb_max') and self.filter_cb_max.get():
            filter_query += " AND center_bore <= ?"
            filter_params.append(float(self.filter_cb_max.get()))

        # Check if any filters are active
        filters_active = len(filter_params) > 0

        # TAB 1: Overall Statistics
        tab_overall = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(tab_overall, text='📊 Overall')

        overall_text = scrolledtext.ScrolledText(tab_overall, bg=self.input_bg, fg=self.fg_color,
                                                 font=("Courier", 10), wrap=tk.NONE, padx=10, pady=10)
        overall_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM programs")
        total_count = cursor.fetchone()[0]

        # Get filtered count
        cursor.execute(filter_query, filter_params)
        filtered_count = cursor.fetchone()[0]

        overall_text.insert(tk.END, "="*100 + "\n")
        overall_text.insert(tk.END, "DATABASE STATISTICS - OVERALL SUMMARY\n")
        overall_text.insert(tk.END, "="*100 + "\n\n")

        if filters_active:
            overall_text.insert(tk.END, f"Total Programs in Database: {total_count:,}\n")
            overall_text.insert(tk.END, f"Filtered View: {filtered_count:,} ({filtered_count/total_count*100:.1f}%)\n\n")
            overall_text.insert(tk.END, "NOTE: Statistics below show FILTERED data only\n")
            overall_text.insert(tk.END, "="*100 + "\n\n")
        else:
            overall_text.insert(tk.END, f"Total Programs: {total_count:,}\n")
            overall_text.insert(tk.END, "="*100 + "\n\n")

        # Validation Status Breakdown
        if filter_params:
            status_query = filter_query.replace("SELECT COUNT(*)", "SELECT validation_status, COUNT(*)") + " GROUP BY validation_status ORDER BY validation_status"
        else:
            status_query = "SELECT validation_status, COUNT(*) FROM programs GROUP BY validation_status ORDER BY validation_status"

        cursor.execute(status_query, filter_params)
        status_results = cursor.fetchall()

        overall_text.insert(tk.END, "VALIDATION STATUS BREAKDOWN:\n")
        overall_text.insert(tk.END, "-"*100 + "\n")
        overall_text.insert(tk.END, f"{'Status':<20} {'Count':>10} {'Percentage':>12}\n")
        overall_text.insert(tk.END, "-"*100 + "\n")

        status_total = sum(r[1] for r in status_results)
        for status, count in status_results:
            percentage = (count / status_total * 100) if status_total > 0 else 0
            overall_text.insert(tk.END, f"{status or 'NULL':<20} {count:>10,} {percentage:>11.1f}%\n")

        overall_text.insert(tk.END, "-"*100 + "\n")
        overall_text.insert(tk.END, f"{'TOTAL':<20} {status_total:>10,} {100.0:>11.1f}%\n\n\n")

        # Spacer Type Breakdown
        if filter_params:
            type_query = filter_query.replace("SELECT COUNT(*)", "SELECT spacer_type, COUNT(*)") + " GROUP BY spacer_type ORDER BY COUNT(*) DESC"
        else:
            type_query = "SELECT spacer_type, COUNT(*) FROM programs GROUP BY spacer_type ORDER BY COUNT(*) DESC"

        cursor.execute(type_query, filter_params)
        type_results = cursor.fetchall()

        overall_text.insert(tk.END, "SPACER TYPE BREAKDOWN:\n")
        overall_text.insert(tk.END, "-"*100 + "\n")
        overall_text.insert(tk.END, f"{'Type':<25} {'Count':>10} {'Percentage':>12}\n")
        overall_text.insert(tk.END, "-"*100 + "\n")

        type_total = sum(r[1] for r in type_results)
        for stype, count in type_results:
            percentage = (count / type_total * 100) if type_total > 0 else 0
            overall_text.insert(tk.END, f"{stype or 'NULL':<25} {count:>10,} {percentage:>11.1f}%\n")

        overall_text.insert(tk.END, "-"*100 + "\n")
        overall_text.insert(tk.END, f"{'TOTAL':<25} {type_total:>10,} {100.0:>11.1f}%\n\n\n")

        # Material Breakdown
        if filter_params:
            material_query = filter_query.replace("SELECT COUNT(*)", "SELECT material, COUNT(*)") + " GROUP BY material ORDER BY COUNT(*) DESC"
        else:
            material_query = "SELECT material, COUNT(*) FROM programs GROUP BY material ORDER BY COUNT(*) DESC"

        cursor.execute(material_query, filter_params)
        material_results = cursor.fetchall()

        overall_text.insert(tk.END, "MATERIAL BREAKDOWN:\n")
        overall_text.insert(tk.END, "-"*100 + "\n")
        overall_text.insert(tk.END, f"{'Material':<25} {'Count':>10} {'Percentage':>12}\n")
        overall_text.insert(tk.END, "-"*100 + "\n")

        material_total = sum(r[1] for r in material_results)
        for material, count in material_results:
            percentage = (count / material_total * 100) if material_total > 0 else 0
            overall_text.insert(tk.END, f"{material or 'NULL':<25} {count:>10,} {percentage:>11.1f}%\n")

        overall_text.insert(tk.END, "-"*100 + "\n")
        overall_text.insert(tk.END, f"{'TOTAL':<25} {material_total:>10,} {100.0:>11.1f}%\n")

        overall_text.config(state=tk.DISABLED)

        # TAB 2: By OD Size
        tab_od = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(tab_od, text='📏 By OD Size')

        od_text = scrolledtext.ScrolledText(tab_od, bg=self.input_bg, fg=self.fg_color,
                                           font=("Courier", 9), wrap=tk.NONE, padx=10, pady=10)
        od_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Define OD ranges
        od_ranges = [
            (5.50, 6.00, '5.75"'),
            (6.00, 6.25, '6.00"'),
            (6.25, 6.50, '6.25"'),
            (6.50, 7.00, '6.50"'),
            (7.00, 7.50, '7.00"'),
            (7.50, 8.00, '7.50"'),
            (8.00, 8.50, '8.00"'),
            (8.50, 9.00, '8.50"'),
            (9.00, 10.00, '9.50"'),
            (10.00, 10.50, '10.25"'),
            (10.50, 11.00, '10.50"'),
            (11.00, 12.00, '11.00"'),
            (12.00, 13.50, '13.00"'),
        ]

        od_text.insert(tk.END, "="*140 + "\n")
        od_text.insert(tk.END, "STATISTICS BY OD SIZE\n")
        od_text.insert(tk.END, "="*140 + "\n\n")

        if filters_active:
            od_text.insert(tk.END, "NOTE: Showing FILTERED data only\n\n")

        od_text.insert(tk.END, f"{'OD Size':<10} {'Total':>8} {'PASS':>8} {'CRITICAL':>10} {'DIMENSIONAL':>13} {'WARNING':>9} {'BORE_WARN':>11} {'% PASS':>9}\n")
        od_text.insert(tk.END, "-"*140 + "\n")

        grand_total = 0
        grand_pass = 0
        grand_critical = 0
        grand_dimensional = 0
        grand_warning = 0
        grand_bore = 0

        for min_od, max_od, label in od_ranges:
            # Build query with OD range and optional filters
            od_filter_query = filter_query + " AND outer_diameter >= ? AND outer_diameter < ?"
            od_params = filter_params + [min_od, max_od]

            cursor.execute(od_filter_query, od_params)
            range_total = cursor.fetchone()[0]

            if range_total == 0:
                continue

            # Get status breakdown for this range
            status_query = od_filter_query.replace("SELECT COUNT(*)", "SELECT validation_status, COUNT(*)") + " GROUP BY validation_status"
            cursor.execute(status_query, od_params)
            status_breakdown = dict(cursor.fetchall())

            pass_count = status_breakdown.get('PASS', 0)
            critical_count = status_breakdown.get('CRITICAL', 0)
            dimensional_count = status_breakdown.get('DIMENSIONAL', 0)
            warning_count = status_breakdown.get('WARNING', 0)
            bore_count = status_breakdown.get('BORE_WARNING', 0)
            pass_pct = (pass_count / range_total * 100) if range_total > 0 else 0

            od_text.insert(tk.END, f"{label:<10} {range_total:>8,} {pass_count:>8,} {critical_count:>10,} {dimensional_count:>13,} {warning_count:>9,} {bore_count:>11,} {pass_pct:>8.1f}%\n")

            grand_total += range_total
            grand_pass += pass_count
            grand_critical += critical_count
            grand_dimensional += dimensional_count
            grand_warning += warning_count
            grand_bore += bore_count

        od_text.insert(tk.END, "-"*140 + "\n")
        grand_pass_pct = (grand_pass / grand_total * 100) if grand_total > 0 else 0
        od_text.insert(tk.END, f"{'TOTAL':<10} {grand_total:>8,} {grand_pass:>8,} {grand_critical:>10,} {grand_dimensional:>13,} {grand_warning:>9,} {grand_bore:>11,} {grand_pass_pct:>8.1f}%\n")

        od_text.config(state=tk.DISABLED)

        # TAB 3: Status by OD (matrix view)
        tab_matrix = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(tab_matrix, text='🔢 Status Matrix')

        matrix_text = scrolledtext.ScrolledText(tab_matrix, bg=self.input_bg, fg=self.fg_color,
                                               font=("Courier", 9), wrap=tk.NONE, padx=10, pady=10)
        matrix_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        matrix_text.insert(tk.END, "="*140 + "\n")
        matrix_text.insert(tk.END, "VALIDATION STATUS BY OD SIZE - DETAILED MATRIX\n")
        matrix_text.insert(tk.END, "="*140 + "\n\n")

        if filters_active:
            matrix_text.insert(tk.END, "NOTE: Showing FILTERED data only\n\n")

        # Get all validation statuses
        status_list = ['PASS', 'CRITICAL', 'DIMENSIONAL', 'WARNING', 'BORE_WARNING']

        # Create matrix
        for status in status_list:
            matrix_text.insert(tk.END, f"\n{'='*140}\n")
            matrix_text.insert(tk.END, f"{status} BY OD SIZE:\n")
            matrix_text.insert(tk.END, f"{'='*140}\n")
            matrix_text.insert(tk.END, f"{'OD Size':<12} {'Count':>10} {'% of Size':>12} {'% of Status':>14}\n")
            matrix_text.insert(tk.END, "-"*140 + "\n")

            # Get total for this status
            status_filter_query = filter_query + " AND validation_status = ?"
            cursor.execute(status_filter_query, filter_params + [status])
            status_total = cursor.fetchone()[0]

            if status_total == 0:
                matrix_text.insert(tk.END, f"No programs with {status} status\n")
                continue

            status_subtotal = 0
            for min_od, max_od, label in od_ranges:
                od_status_query = filter_query + " AND outer_diameter >= ? AND outer_diameter < ? AND validation_status = ?"
                cursor.execute(od_status_query, filter_params + [min_od, max_od, status])
                count = cursor.fetchone()[0]

                if count == 0:
                    continue

                # Get total for this OD size
                od_total_query = filter_query + " AND outer_diameter >= ? AND outer_diameter < ?"
                cursor.execute(od_total_query, filter_params + [min_od, max_od])
                od_total = cursor.fetchone()[0]

                pct_of_size = (count / od_total * 100) if od_total > 0 else 0
                pct_of_status = (count / status_total * 100) if status_total > 0 else 0

                matrix_text.insert(tk.END, f"{label:<12} {count:>10,} {pct_of_size:>11.1f}% {pct_of_status:>13.1f}%\n")
                status_subtotal += count

            matrix_text.insert(tk.END, "-"*140 + "\n")
            matrix_text.insert(tk.END, f"{'TOTAL':<12} {status_subtotal:>10,} {'':>11} {100.0:>13.1f}%\n")

        matrix_text.config(state=tk.DISABLED)

        # TAB 4: Top Error Types
        tab_errors = tk.Frame(notebook, bg=self.bg_color)
        notebook.add(tab_errors, text='⚠️ Error Types')

        error_text = scrolledtext.ScrolledText(tab_errors, bg=self.input_bg, fg=self.fg_color,
                                              font=("Courier", 9), wrap=tk.NONE, padx=10, pady=10)
        error_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        error_text.insert(tk.END, "="*100 + "\n")
        error_text.insert(tk.END, "TOP ERROR TYPES\n")
        error_text.insert(tk.END, "="*100 + "\n\n")

        if filters_active:
            error_text.insert(tk.END, "NOTE: Showing FILTERED data only\n\n")

        # Count different error types from validation_issues
        issues_query = filter_query.replace("SELECT COUNT(*)", "SELECT validation_issues") + " AND validation_issues IS NOT NULL"
        cursor.execute(issues_query, filter_params)
        all_issues = cursor.fetchall()

        # Parse and count error types
        error_counts = {}
        for (issues_str,) in all_issues:
            if not issues_str:
                continue
            # Split by pipe delimiter
            issues = [i.strip() for i in issues_str.split('|') if i.strip()]
            for issue in issues:
                # Extract error type (first part before colon)
                error_type = issue.split(':')[0].strip() if ':' in issue else issue.strip()
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # Sort by count
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

        error_text.insert(tk.END, f"{'Error Type':<60} {'Count':>10} {'Percentage':>12}\n")
        error_text.insert(tk.END, "-"*100 + "\n")

        total_errors = sum(error_counts.values())
        for error_type, count in sorted_errors[:20]:  # Top 20 errors
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            error_text.insert(tk.END, f"{error_type:<60} {count:>10,} {percentage:>11.1f}%\n")

        error_text.insert(tk.END, "-"*100 + "\n")
        error_text.insert(tk.END, f"{'TOTAL ERRORS':<60} {total_errors:>10,} {100.0:>11.1f}%\n\n")

        error_text.insert(tk.END, f"\nTotal programs with errors: {len(all_issues):,}\n")

        error_text.config(state=tk.DISABLED)

        conn.close()

        # Add close button
        close_btn = tk.Button(stats_window, text="Close", command=stats_window.destroy,
                             bg=self.button_bg, fg=self.fg_color, font=("Arial", 10, "bold"))
        close_btn.pack(pady=10)

    def show_legend(self):
        """Show validation status legend and help"""
        legend_window = tk.Toplevel(self.root)
        legend_window.title("G-Code Database Manager - Help & Workflow Guide")
        legend_window.geometry("900x900")
        legend_window.configure(bg=self.bg_color)

        # Create scrolled text widget
        text = scrolledtext.ScrolledText(legend_window, bg=self.input_bg, fg=self.fg_color,
                                        font=("Courier", 10), wrap=tk.WORD, padx=15, pady=15)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Legend content
        legend_content = """
═══════════════════════════════════════════════════════════════════════════════
                      G-CODE DATABASE MANAGER - HELP GUIDE
═══════════════════════════════════════════════════════════════════════════════

TABLE OF CONTENTS:
  1. Production-Ready Workflow (Recommended Steps)
  2. Function Descriptions (What Each Button Does)
  3. Duplicate Handling Strategies
  4. Validation Status Legend
  5. Filtering Tips

═══════════════════════════════════════════════════════════════════════════════
                    1. PRODUCTION-READY WORKFLOW (START HERE!)
═══════════════════════════════════════════════════════════════════════════════

GOAL: Clean catalog with NO duplicate names, NO _dup suffixes, all unique files

STEP 1: INITIAL SCAN
───────────────────────────────────────────────────────────────────────────────
📂 Scan Folder
  • Click "📂 Scan Folder" button (Data tab)
  • Select your main G-code directory
  • This scans ALL files recursively and adds them to database
  • Automatically detects and SKIPS exact duplicates
  • Warns about name collisions (same name, different content)

What Happens:
  ✓ Exact duplicates (same name + content) → Automatically skipped
  ✓ New unique files → Added to database
  ✓ Existing files → Updated if changed
  ⚠️  Name collisions → Warned (you must rename manually before scan)

STEP 2: DETECT DUPLICATES
───────────────────────────────────────────────────────────────────────────────
🔍 Find Repeats
  • Click "🔍 Find Repeats" button (Tools tab)
  • Analyzes ALL files in database for duplicates
  • Classifies duplicates into categories

What Happens:
  • SOLID duplicates: Exact same content, different names
  • NAME_COLLISION: Same name, different content
  • CONTENT_DUP: Same content as parent file
  • Parent/child relationships established

STEP 3: REVIEW DUPLICATES
───────────────────────────────────────────────────────────────────────────────
⚖️ Compare Files
  • Hold Ctrl and click multiple files in the list
  • Click "⚖️ Compare Files" button (Tools tab)
  • View files side-by-side with metadata and G-code preview
  • Decide which to keep, rename, or delete

Decision Process:
  1. If EXACT SAME content but different names:
     → Keep the one with better name (more descriptive)
     → Delete the others from database (file stays on disk)

  2. If SAME NAME but DIFFERENT content:
     → Keep both files BUT rename one
     → Use the rename function to give it a unique name

  3. If similar but slightly different:
     → Compare the G-code to see actual differences
     → Keep the correct/latest version
     → Delete or rename the outdated version

STEP 4: AUTO-ASSIGN NEW O-NUMBERS TO DUPLICATES
───────────────────────────────────────────────────────────────────────────────
📝 Rename Duplicates
  • Filter view first (e.g., Duplicate Type = NAME_COLLISION)
  • Click "📝 Rename Duplicates" button (Tools tab)
  • Finds files with duplicate filenames IN FILTERED VIEW ONLY
  • Assigns new available O-numbers (o59000+)
  • NO _dup suffix - assigns proper clean O-numbers
  • Creates backup before making changes
  • Updates: physical file, internal O-number, database

⚠️  IMPORTANT: Works on FILTERED VIEW ONLY!
  • Filter for the duplicates you want to rename
  • Parent file keeps original name
  • Child files get new O-numbers (o59000, o59001, etc.)
  • All changes are automatic - no manual renaming needed

Preview Mode:
  • Shows exactly what O-numbers will be assigned
  • Review the plan before executing
  • Click Execute to apply changes

STEP 5: DELETE UNWANTED DUPLICATES
───────────────────────────────────────────────────────────────────────────────
🗑️ Delete Filtered View
  • Use filters to show only duplicates
  • Apply filters: Duplicate Type = SOLID, CONTENT_DUP, etc.
  • Click "🗑️ Delete Filtered View" (Tools tab)
  • Deletes from DATABASE ONLY (files stay on disk for safety)

Safety Features:
  • Preview mode shows what will be deleted
  • Database backup created automatically
  • Physical files are NOT deleted (safer)

STEP 6: VERIFY PRODUCTION-READY STATE
───────────────────────────────────────────────────────────────────────────────
✅ Final Checks:
  1. Run Find Repeats again
     → Should find ZERO duplicates

  2. Filter by Validation Status = PASS
     → These are production-ready files

  3. Check total file count
     → All files should have unique O-numbers

  4. Export to CSV for documentation
     → Click "📊 Export CSV" (Reports tab)

═══════════════════════════════════════════════════════════════════════════════
                    2. FUNCTION DESCRIPTIONS (WHAT EACH BUTTON DOES)
═══════════════════════════════════════════════════════════════════════════════

DATA TAB - File Import/Management
───────────────────────────────────────────────────────────────────────────────
📂 Scan Folder
  • Recursively scans a directory for G-code files
  • Parses dimensions, P-codes, and metadata
  • Adds new files, updates existing files
  • Auto-detects exact duplicates (skips them)
  • Warns about name collisions (same name, different content)
  • Shows live progress with file counts

🆕 Scan New Only
  • Scans directory but ONLY adds NEW files
  • Skips files already in database
  • Faster for adding new batches
  • Still detects duplicates and name collisions
  • Use after initial full scan

➕ Add Entry
  • Manually add a single program
  • Fill in all fields manually
  • Use when you need precise control
  • Links to physical file on disk

✏️ Edit Entry
  • Double-click any row OR click this button
  • Modify any field in database
  • Changes save to database
  • Does NOT modify physical file

TOOLS TAB - Duplicate Management
───────────────────────────────────────────────────────────────────────────────
🔍 Find Repeats
  • Analyzes ALL files for duplicates
  • Compares file content (not just names)
  • Creates parent/child relationships
  • Classifies duplicates: SOLID, NAME_COLLISION, CONTENT_DUP
  • Populates duplicate_type column
  • Required before using duplicate filters

⚖️ Compare Files
  • Select 2+ files (Ctrl+Click)
  • Shows side-by-side comparison
  • Displays metadata and G-code content
  • Highlights differences
  • Actions: Keep, Rename, Delete
  • Updates internal O-number when renaming

📝 Rename Duplicates
  • Works on FILTERED VIEW ONLY (not all files)
  • Finds files with same filename in current view
  • Assigns proper available O-numbers (o59000+)
  • NO _dup suffix - assigns clean O-numbers
  • Renames physical files
  • Updates internal O-number in G-code file
  • Updates database program_number
  • Preview mode: See changes before applying
  • Execute mode: Actually renames files
  • Creates automatic backup

📋 Copy Filtered View
  • Copies currently filtered files to new folder
  • Preserves directory structure
  • Only copies files matching active filters
  • Use to extract specific file groups
  • Physical file copy operation

🗑️ Delete Filtered View
  • Deletes currently filtered files from DATABASE
  • Does NOT delete physical files (safer)
  • Preview mode available
  • Creates backup before deletion
  • Use to clean up duplicate entries

REPORTS TAB - Export/Analysis
───────────────────────────────────────────────────────────────────────────────
📊 Export CSV
  • Exports current filtered view to CSV
  • Includes all columns
  • Use for Excel analysis, documentation
  • Respects active filters

📄 Export Unused Numbers
  • Finds gaps in program number sequence
  • Exports available O-numbers
  • Helps when creating new programs
  • Useful for number assignment

🗂️ Organize by OD
  • Groups files by Outer Diameter
  • Creates folders for each OD size
  • Copies files to organized structure
  • Preview mode available

❓ Help/Legend
  • Opens this help guide
  • Workflow documentation
  • Function descriptions
  • Color-coded validation system

═══════════════════════════════════════════════════════════════════════════════
                    3. DUPLICATE HANDLING STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

SCENARIO A: Same Name, Same Content (Exact Duplicates)
───────────────────────────────────────────────────────────────────────────────
Example: O57001.nc in two different folders, identical content

What to do:
  1. Scan Folder → Auto-skips exact duplicates
  2. Find Repeats → Marks as SOLID duplicate
  3. Compare Files → Verify they're identical
  4. Delete one from database (keep the one in primary location)

Result: Only ONE file in database, no confusion

SCENARIO B: Same Name, Different Content (Name Collision)
───────────────────────────────────────────────────────────────────────────────
Example: O57001.nc exists twice but programs are different

THIS IS THE CRITICAL SCENARIO - REQUIRES MANUAL DECISION!

What to do:
  1. Find Repeats → Marks as NAME_COLLISION
  2. Compare Files → View both side-by-side
  3. Decide which is correct:

     Option A - Keep BOTH (they're both valid):
       • Select one file in Compare window
       • Click Rename action
       • Give it a new unique O-number (e.g., O57001A or O59999)
       • System updates filename AND internal O-number
       • Now you have O57001.nc and O59999.nc (both unique)

     Option B - Keep ONE (one is wrong/outdated):
       • Select the wrong one
       • Click Delete action
       • Removes from database (file stays on disk for safety)
       • Correct file remains as O57001.nc

⚠️  NEVER let two different programs share the same O-number!

SCENARIO C: Different Names, Same Content (SOLID Duplicate)
───────────────────────────────────────────────────────────────────────────────
Example: O57001.nc and O57001_backup.nc are identical

What to do:
  1. Find Repeats → Marks as SOLID duplicate
  2. Compare Files → Confirm they're identical
  3. Delete the backup from database
  4. Keep the one with the cleaner name

Result: Single entry with best filename

SCENARIO D: Using Rename Duplicates for Automatic Assignment
───────────────────────────────────────────────────────────────────────────────
Example: You have multiple files named O57001.nc in different folders

Automatic workflow:
  1. Filter: Duplicate Type = NAME_COLLISION
  2. Click "📝 Rename Duplicates" (Tools tab)
  3. Preview mode shows the new O-numbers to be assigned
  4. Execute: Child files automatically renamed to o59000, o59001, etc.
  5. System updates:
     • Physical filename (O57001.nc → o59000.nc)
     • Internal O-number (O57001 → O59000)
     • Database program_number

Result: All files have unique O-numbers (NO _dup suffix!)
  • Parent keeps original: O57001.nc
  • Child 1: o59000.nc
  • Child 2: o59001.nc
  • All are production-ready with proper O-numbers

═══════════════════════════════════════════════════════════════════════════════
                    4. VALIDATION STATUS LEGEND
═══════════════════════════════════════════════════════════════════════════════

The database uses a 5-color validation system to categorize issues by severity.

═══════════════════════════════════════════════════════════════════════════════

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

Color    Status         Severity    Production Impact    Action
------   ------------   ---------   ------------------   ---------
🔴 RED    CRITICAL       CRITICAL    Part failure/crash   IMMEDIATE
🟠 ORANGE BORE_WARNING   HIGH        Possible fit issues  Before 1st
🟣 PURPLE DIMENSIONAL    MEDIUM      Setup errors         Before run
🟡 YELLOW WARNING        LOW         Minor issues         When ready
🟢 GREEN  PASS           NONE        None                 N/A

TOLERANCE REFERENCE
───────────────────────────────────────────────────────────────────────────────
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

═══════════════════════════════════════════════════════════════════════════════
                    5. FILTERING TIPS
═══════════════════════════════════════════════════════════════════════════════

Multi-Select Filters
───────────────────────────────────────────────────────────────────────────────
  • Click Type/Material/Status/Duplicate Type dropdowns
  • Check multiple boxes to filter
  • Shows "3 selected" when multiple items chosen
  • Click "Apply Filters" button to filter results
  • Click "Reset Filters" to clear all filters

Common Filter Combinations
───────────────────────────────────────────────────────────────────────────────
Focus on Issues Only:
  • Status: Select CRITICAL + BORE_WARNING + DIMENSIONAL
  • Result: See only files needing attention

Production-Ready Files:
  • Status: Select only PASS
  • Duplicate Type: Leave empty or uncheck all
  • Result: Clean, validated files ready to run

View All Duplicates:
  • Duplicate Type: Select SOLID + NAME_COLLISION + CONTENT_DUP
  • Result: See all duplicate files for cleanup

View Only SOLID Duplicates (same content, different names):
  • Duplicate Type: Select only SOLID
  • Result: Files you can safely delete (keep one copy)

View Name Collisions (CRITICAL - different content, same name):
  • Duplicate Type: Select only NAME_COLLISION
  • Result: Files that MUST be manually reviewed and renamed

View by Material:
  • Material: Select specific materials (e.g., 1018, 4140)
  • Result: See files for specific material types

View by Outer Diameter:
  • OD Range: Enter min/max values
  • Result: See files within specific size range

═══════════════════════════════════════════════════════════════════════════════
                    QUICK REFERENCE - RECOMMENDED WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

INITIAL SETUP (First Time):
  1. Scan Folder → Load all files
  2. Find Repeats → Detect duplicates
  3. Review & Compare → Use Compare Files
  4. Clean Up → Rename or Delete duplicates
  5. Verify → Check for _dup files and duplicates

DAILY PRODUCTION USE:
  1. Scan New Only → Add new files
  2. Filter by Status → Focus on PASS files
  3. Export CSV → Document production files
  4. Organize by OD → Group files for easy access

TROUBLESHOOTING:
  • If Copy Filtered not working → Run Find Repeats first
  • If duplicates showing → Use Rename Duplicates or Compare Files
  • If Rename Duplicates does nothing → Check that view is filtered
  • If validation errors → Fix G-code and re-scan

═══════════════════════════════════════════════════════════════════════════════

For more documentation, see project README files in the application directory.

═══════════════════════════════════════════════════════════════════════════════
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

    def create_manual_backup(self):
        """Create a manual backup with timestamp"""
        import shutil
        from datetime import datetime

        backups_dir = os.path.join(os.path.dirname(self.db_path), "database_backups")
        os.makedirs(backups_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"gcode_db_backup_{timestamp}.db"
        backup_path = os.path.join(backups_dir, backup_filename)

        try:
            shutil.copy2(self.db_path, backup_path)
            messagebox.showinfo("Backup Created",
                f"Database backed up successfully!\n\n"
                f"Backup saved to:\n{backup_filename}\n\n"
                f"Location: {backups_dir}")
        except Exception as e:
            messagebox.showerror("Backup Failed",
                f"Failed to create backup:\n{str(e)}")

    def restore_from_backup(self):
        """Restore database from a backup file"""
        import shutil
        from datetime import datetime

        backups_dir = os.path.join(os.path.dirname(self.db_path), "database_backups")

        # Let user select backup file
        backup_file = filedialog.askopenfilename(
            title="Select Backup to Restore",
            initialdir=backups_dir if os.path.exists(backups_dir) else os.path.dirname(self.db_path),
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )

        if not backup_file:
            return

        # Confirm restoration
        result = messagebox.askyesno(
            "Confirm Restore",
            f"Restore database from:\n{os.path.basename(backup_file)}\n\n"
            f"⚠️ WARNING ⚠️\n"
            f"This will replace your current database!\n"
            f"All current data will be lost!\n\n"
            f"A backup of the current database will be created first.\n\n"
            f"Continue?",
            icon='warning'
        )

        if not result:
            return

        try:
            # Create backup of current database first
            current_backup_dir = os.path.join(os.path.dirname(self.db_path), "database_backups")
            os.makedirs(current_backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            current_backup = os.path.join(current_backup_dir, f"before_restore_{timestamp}.db")
            shutil.copy2(self.db_path, current_backup)

            # Restore from selected backup
            shutil.copy2(backup_file, self.db_path)

            messagebox.showinfo("Restore Complete",
                f"Database restored successfully!\n\n"
                f"Restored from: {os.path.basename(backup_file)}\n\n"
                f"Previous database saved as:\n{os.path.basename(current_backup)}\n\n"
                f"Please restart the application to load the restored database.")

        except Exception as e:
            messagebox.showerror("Restore Failed",
                f"Failed to restore database:\n{str(e)}")

    def view_backups(self):
        """View and manage database backups"""
        import shutil
        from datetime import datetime

        backups_dir = os.path.join(os.path.dirname(self.db_path), "database_backups")
        os.makedirs(backups_dir, exist_ok=True)

        # Create window
        backup_window = tk.Toplevel(self.root)
        backup_window.title("Database Backups")
        backup_window.geometry("900x600")
        backup_window.configure(bg=self.bg_color)

        tk.Label(backup_window,
                text="Database Backup Manager",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 14, "bold")).pack(pady=15)

        # Treeview for backup list
        tree_frame = tk.Frame(backup_window, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ('filename', 'records', 'date', 'size')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)

        tree.heading('filename', text='Backup File')
        tree.heading('records', text='Records')
        tree.heading('date', text='Date Created')
        tree.heading('size', text='Size (MB)')

        tree.column('filename', width=350)
        tree.column('records', width=100)
        tree.column('date', width=200)
        tree.column('size', width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_backup_list():
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)

            # Get backup files
            if not os.path.exists(backups_dir):
                tree.insert('', tk.END, values=("No backups found", "", "", ""))
                return

            backup_files = [f for f in os.listdir(backups_dir) if f.endswith('.db')]

            if not backup_files:
                tree.insert('', tk.END, values=("No backups found - use 'Backup Now' to create one", "", "", ""))
                return

            for backup_file in sorted(backup_files, reverse=True):
                backup_path = os.path.join(backups_dir, backup_file)

                # Get stats
                stat = os.stat(backup_path)
                size_mb = f"{stat.st_size / (1024 * 1024):.2f}"
                created = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                # Get record count
                try:
                    conn = sqlite3.connect(backup_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM programs")
                    count = cursor.fetchone()[0]
                    conn.close()
                except:
                    count = "Error"

                tree.insert('', tk.END, values=(backup_file, count, created, size_mb))

        def delete_backup():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup to delete.")
                return

            item = selection[0]
            filename = tree.item(item)['values'][0]

            if "No backups found" in filename:
                return

            result = messagebox.askyesno(
                "Confirm Delete",
                f"Delete backup '{filename}'?\n\n"
                f"This cannot be undone!",
                icon='warning'
            )

            if result:
                try:
                    backup_path = os.path.join(backups_dir, filename)
                    os.remove(backup_path)
                    refresh_backup_list()
                    messagebox.showinfo("Deleted", f"Backup '{filename}' deleted successfully.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete backup:\n{str(e)}")

        def restore_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup to restore.")
                return

            item = selection[0]
            filename = tree.item(item)['values'][0]

            if "No backups found" in filename:
                return

            backup_path = os.path.join(backups_dir, filename)

            result = messagebox.askyesno(
                "Confirm Restore",
                f"Restore database from:\n{filename}\n\n"
                f"⚠️ WARNING ⚠️\n"
                f"This will replace your current database!\n\n"
                f"A backup of current database will be created first.\n\n"
                f"Continue?",
                icon='warning'
            )

            if result:
                try:
                    # Backup current database
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    current_backup = os.path.join(backups_dir, f"before_restore_{timestamp}.db")
                    shutil.copy2(self.db_path, current_backup)

                    # Restore
                    shutil.copy2(backup_path, self.db_path)

                    messagebox.showinfo("Restore Complete",
                        f"Database restored from {filename}!\n\n"
                        f"Current database backed up as:\n{os.path.basename(current_backup)}\n\n"
                        f"Please restart the application.")
                    backup_window.destroy()

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to restore:\n{str(e)}")

        # Initial load
        refresh_backup_list()

        # Info label
        info_text = f"Backup location: {backups_dir}"
        tk.Label(backup_window, text=info_text,
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 9)).pack(pady=5)

        # Button frame
        btn_frame = tk.Frame(backup_window, bg=self.bg_color)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="💾 Backup Now", command=lambda: [self.create_manual_backup(), refresh_backup_list()],
                 bg="#1976D2", fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=14).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="📂 Restore", command=restore_selected,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=14).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🗑️ Delete", command=delete_backup,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=14).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🔄 Refresh", command=refresh_backup_list,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=14).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="❌ Close", command=backup_window.destroy,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10, "bold"), width=14).pack(side=tk.LEFT, padx=5)


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
                    INSERT INTO programs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (program_number, None,  # title
                     spacer_type, outer_diameter, thickness, None,  # thickness_display
                     center_bore, hub_height, hub_diameter, cb_diameter, cb_depth,
                     paired_program, material, notes, datetime.now().isoformat(),
                     datetime.now().isoformat(), file_path,
                     None, None, None, None, None,  # detection_confidence, detection_method, validation_status, validation_issues, validation_warnings
                     None, None,  # bore_warnings, dimensional_issues
                     None, None, None,  # cb_from_gcode, ob_from_gcode, lathe
                     None, None, None))  # duplicate_type, parent_file, duplicate_group
            
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
            ("Title", 1),
            ("Spacer Type", 2),
            ("Outer Diameter", 3),
            ("Thickness", 4),
            ("Thickness Display", 5),
            ("Center Bore", 6),
            ("Hub Height", 7),
            ("Hub Diameter", 8),
            ("Counter Bore Diameter", 9),
            ("Counter Bore Depth", 10),
            ("Paired Program", 11),
            ("Material", 12),
            ("Notes", 13),
            ("Date Created", 14),
            ("Last Modified", 15),
            ("File Path", 16),
        ]

        text.insert(tk.END, "="*50 + "\n")
        text.insert(tk.END, f"  PROGRAM DETAILS - {self.record[0]}\n")
        text.insert(tk.END, "="*50 + "\n\n")

        for label, idx in fields:
            value = self.record[idx] if self.record[idx] else "-"
            text.insert(tk.END, f"{label}:\n  {value}\n\n")

        # Add validation information if available
        if len(self.record) > 18:
            text.insert(tk.END, "="*50 + "\n")
            text.insert(tk.END, "  VALIDATION RESULTS\n")
            text.insert(tk.END, "="*50 + "\n\n")

            # Detection info
            if self.record[17]:  # detection_confidence
                text.insert(tk.END, f"Detection Confidence: {self.record[17]}\n")
            if self.record[18]:  # detection_method
                text.insert(tk.END, f"Detection Method: {self.record[18]}\n")

            # Lathe assignment
            if len(self.record) > 26 and self.record[26]:  # lathe
                text.insert(tk.END, f"Lathe: {self.record[26]}\n")

            # Validation status
            status = self.record[19] if self.record[19] else "N/A"
            text.insert(tk.END, f"\nValidation Status: {status}\n\n")

            # G-code dimensions
            if len(self.record) > 22 and self.record[22]:  # cb_from_gcode (index 22)
                text.insert(tk.END, f"CB from G-code: {self.record[22]:.1f}mm\n")
            if len(self.record) > 23 and self.record[23]:  # ob_from_gcode (index 23)
                text.insert(tk.END, f"OB from G-code: {self.record[23]:.1f}mm\n")

            # Validation issues (CRITICAL - RED)
            if self.record[20]:  # validation_issues
                try:
                    # Try JSON format first (backward compatibility)
                    issues = json.loads(self.record[20])
                except:
                    # Fall back to pipe-delimited format
                    issues = [i.strip() for i in self.record[20].split('|') if i.strip()]

                if issues:
                    text.insert(tk.END, "\nCRITICAL ISSUES:\n")
                    for issue in issues:
                        text.insert(tk.END, f"  - {issue}\n")

            # Bore warnings (ORANGE)
            if len(self.record) > 24 and self.record[24]:  # bore_warnings (index 24)
                try:
                    # Try JSON format first (backward compatibility)
                    bore_warns = json.loads(self.record[24])
                except:
                    # Fall back to pipe-delimited format
                    bore_warns = [i.strip() for i in self.record[24].split('|') if i.strip()]

                if bore_warns:
                    text.insert(tk.END, "\nBORE WARNINGS:\n")
                    for warning in bore_warns:
                        text.insert(tk.END, f"  - {warning}\n")

            # Dimensional issues (PURPLE)
            if len(self.record) > 25 and self.record[25]:  # dimensional_issues (index 25)
                try:
                    # Try JSON format first (backward compatibility)
                    dim_issues = json.loads(self.record[25])
                except:
                    # Fall back to pipe-delimited format
                    dim_issues = [i.strip() for i in self.record[25].split('|') if i.strip()]

                if dim_issues:
                    text.insert(tk.END, "\nDIMENSIONAL ISSUES:\n")
                    for issue in dim_issues:
                        text.insert(tk.END, f"  - {issue}\n")

            # Validation warnings (YELLOW)
            if self.record[21]:  # validation_warnings
                try:
                    # Try JSON format first (backward compatibility)
                    warnings = json.loads(self.record[21])
                except:
                    # Fall back to pipe-delimited format
                    warnings = [i.strip() for i in self.record[21].split('|') if i.strip()]

                if warnings:
                    text.insert(tk.END, "\nWARNINGS:\n")
                    for warning in warnings:
                        text.insert(tk.END, f"  - {warning}\n")

        text.config(state=tk.DISABLED)
        
        # Close button
        btn_close = tk.Button(self.window, text="Close", command=self.window.destroy,
                             bg=self.parent.button_bg, fg=self.parent.fg_color,
                             font=("Arial", 10, "bold"), width=15)
        btn_close.pack(pady=10)


class FileComparisonWindow:
    """Window to compare multiple files side-by-side"""
    def __init__(self, parent, files_data, bg_color, fg_color, input_bg, button_bg, refresh_callback, manager=None):
        self.parent = parent
        self.files_data = files_data
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.input_bg = input_bg
        self.button_bg = button_bg
        self.refresh_callback = refresh_callback
        self.manager = manager  # Reference to GCodeDatabaseManager instance

        # Create lookup dictionary: {program_number: (all file data)}
        self.files_lookup = {file_info[0]: file_info for file_info in files_data}

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Compare {len(files_data)} Files")
        self.window.geometry("1400x900")
        self.window.configure(bg=bg_color)

        # Track actions for each file
        self.file_actions = {}  # {program_number: 'keep'/'delete'/'rename'}

        self.setup_ui()

    def setup_ui(self):
        """Setup the comparison UI"""
        # Title
        title_label = tk.Label(self.window,
                              text=f"File Comparison - {len(self.files_data)} Files Selected",
                              bg=self.bg_color, fg=self.fg_color,
                              font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # Main comparison area with scrollbar
        main_frame = tk.Frame(self.window, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Canvas with scrollbar for horizontal scrolling
        canvas = tk.Canvas(main_frame, bg=self.bg_color)
        h_scrollbar = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        v_scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)

        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        # Pack scrollbars and canvas
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create side-by-side panels for each file
        panels_frame = tk.Frame(scrollable_frame, bg=self.bg_color)
        panels_frame.pack(fill=tk.BOTH, expand=True)

        # Load file contents
        file_contents = {}
        for file_info in self.files_data:
            prog_num = file_info[0]
            file_path = file_info[2]

            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_contents[prog_num] = f.read()
                except:
                    file_contents[prog_num] = "[Error reading file]"
            else:
                file_contents[prog_num] = "[File not found]"

        # Create a panel for each file
        for idx, file_info in enumerate(self.files_data):
            self.create_file_panel(panels_frame, file_info, file_contents, idx)

        # Bottom action buttons
        bottom_frame = tk.Frame(self.window, bg=self.bg_color)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(bottom_frame, text="Apply Actions & Close",
                 command=self.apply_actions,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 11, "bold"), width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(bottom_frame, text="Cancel",
                 command=self.window.destroy,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 11), width=15).pack(side=tk.LEFT, padx=5)

        # Summary label
        self.summary_label = tk.Label(bottom_frame,
                                     text="Select actions for each file",
                                     bg=self.bg_color, fg=self.fg_color,
                                     font=("Arial", 10))
        self.summary_label.pack(side=tk.RIGHT, padx=10)

    def create_file_panel(self, parent, file_info, file_contents, index):
        """Create a panel for one file"""
        prog_num, title, file_path, spacer_type, od, thickness = file_info[:6]
        cb, hub_h, hub_d, cb_d, cb_dep, val_status, confidence = file_info[6:13]
        dup_type, parent_file, modified, created = file_info[13:17]

        # Panel container
        panel = tk.Frame(parent, bg=self.input_bg, relief=tk.RAISED, borderwidth=2)
        panel.grid(row=0, column=index, padx=5, pady=5, sticky="nsew")

        # Make columns expand equally
        parent.grid_columnconfigure(index, weight=1, uniform="col")

        # Header with file number and status
        header_bg = self.get_status_color(val_status)
        header = tk.Frame(panel, bg=header_bg)
        header.pack(fill=tk.X, pady=(0, 5))

        tk.Label(header, text=f"File {index + 1}: {prog_num}",
                bg=header_bg, fg="white",
                font=("Arial", 12, "bold")).pack(pady=5)

        if val_status:
            tk.Label(header, text=f"Status: {val_status}",
                    bg=header_bg, fg="white",
                    font=("Arial", 9)).pack()

        # Metadata section
        meta_frame = tk.Frame(panel, bg=self.input_bg)
        meta_frame.pack(fill=tk.X, padx=5, pady=5)

        metadata = [
            ("Title", title or "N/A"),
            ("Type", spacer_type or "N/A"),
            ("OD", f"{od:.3f}\"" if od else "N/A"),
            ("Thickness", f"{thickness:.3f}\"" if thickness else "N/A"),
            ("Center Bore", f"{cb:.3f}\"" if cb else "N/A"),
            ("Confidence", confidence or "N/A"),
        ]

        if dup_type:
            metadata.append(("Dup Type", dup_type))
        if parent_file:
            metadata.append(("Parent", parent_file))

        for label, value in metadata:
            row = tk.Frame(meta_frame, bg=self.input_bg)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{label}:", bg=self.input_bg, fg=self.fg_color,
                    font=("Arial", 9, "bold"), width=12, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=self.input_bg, fg=self.fg_color,
                    font=("Arial", 9), anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File content preview with syntax highlighting
        tk.Label(panel, text="G-Code Preview:", bg=self.input_bg, fg=self.fg_color,
                font=("Arial", 10, "bold")).pack(pady=(10, 5))

        content_frame = tk.Frame(panel, bg=self.input_bg)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        content_text = scrolledtext.ScrolledText(content_frame,
                                                bg="#1e1e1e", fg="#d4d4d4",
                                                font=("Courier New", 8),
                                                height=20, wrap=tk.NONE)
        content_text.pack(fill=tk.BOTH, expand=True)

        # Insert content with basic syntax highlighting
        content = file_contents.get(prog_num, "[No content]")
        self.insert_with_highlighting(content_text, content)
        content_text.config(state=tk.DISABLED)

        # Highlight differences if multiple files
        if len(self.files_data) > 1 and index > 0:
            self.highlight_differences(content_text, content, file_contents[self.files_data[0][0]])

        # Action buttons
        action_frame = tk.Frame(panel, bg=self.input_bg)
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        tk.Label(action_frame, text="Action:", bg=self.input_bg, fg=self.fg_color,
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        action_var = tk.StringVar(value="keep")
        self.file_actions[prog_num] = action_var

        tk.Radiobutton(action_frame, text="✓ Keep", variable=action_var, value="keep",
                      bg=self.input_bg, fg=self.fg_color, selectcolor=self.button_bg,
                      font=("Arial", 9), command=self.update_summary).pack(side=tk.LEFT, padx=3)

        tk.Radiobutton(action_frame, text="✏️ Rename", variable=action_var, value="rename",
                      bg=self.input_bg, fg=self.fg_color, selectcolor=self.button_bg,
                      font=("Arial", 9), command=self.update_summary).pack(side=tk.LEFT, padx=3)

        tk.Radiobutton(action_frame, text="🗑️ Delete", variable=action_var, value="delete",
                      bg=self.input_bg, fg=self.fg_color, selectcolor=self.button_bg,
                      font=("Arial", 9), command=self.update_summary).pack(side=tk.LEFT, padx=3)

    def get_status_color(self, status):
        """Get color based on validation status"""
        colors = {
            'CRITICAL': '#d32f2f',
            'DIMENSIONAL': '#7b1fa2',
            'BORE_WARNING': '#f57c00',
            'WARNING': '#fbc02d',
            'PASS': '#388e3c',
            'REPEAT': '#757575'
        }
        return colors.get(status, '#455a64')

    def insert_with_highlighting(self, text_widget, content):
        """Insert content with basic G-code syntax highlighting"""
        text_widget.tag_configure("gcode", foreground="#569cd6")  # Blue for G/M codes
        text_widget.tag_configure("comment", foreground="#6a9955")  # Green for comments
        text_widget.tag_configure("number", foreground="#b5cea8")  # Light green for numbers

        lines = content.split('\n')
        for line in lines:
            if '(' in line:
                # Line has comments
                before_comment = line.split('(')[0]
                comment_part = '(' + '('.join(line.split('(')[1:])
                text_widget.insert(tk.END, before_comment)
                text_widget.insert(tk.END, comment_part, "comment")
                text_widget.insert(tk.END, "\n")
            elif line.strip().startswith('G') or line.strip().startswith('M'):
                text_widget.insert(tk.END, line, "gcode")
                text_widget.insert(tk.END, "\n")
            else:
                text_widget.insert(tk.END, line + "\n")

    def highlight_differences(self, text_widget, content1, content2):
        """Highlight differences between two file contents"""
        text_widget.tag_configure("diff", background="#4d2600")  # Brown background for differences

        lines1 = content1.split('\n')
        lines2 = content2.split('\n')

        import difflib
        diff = difflib.unified_diff(lines2, lines1, lineterm='')
        diff_lines = set()

        for line in diff:
            if line.startswith('@@'):
                # Parse line numbers from unified diff format
                import re
                match = re.search(r'\+(\d+)', line)
                if match:
                    diff_lines.add(int(match.group(1)) - 1)

        # Highlight different lines (basic implementation)
        # For now, just mark if files are different
        if content1 != content2:
            text_widget.tag_configure("diff_marker", foreground="#ff9800")
            text_widget.insert("1.0", "⚠ Differences detected\n", "diff_marker")

    def update_summary(self):
        """Update the summary label with current action counts"""
        keep_count = sum(1 for var in self.file_actions.values() if var.get() == "keep")
        rename_count = sum(1 for var in self.file_actions.values() if var.get() == "rename")
        delete_count = sum(1 for var in self.file_actions.values() if var.get() == "delete")

        summary = f"Keep: {keep_count} | Rename: {rename_count} | Delete: {delete_count}"
        self.summary_label.config(text=summary)

    def apply_actions(self):
        """Apply the selected actions to files"""
        actions_to_apply = {prog: var.get() for prog, var in self.file_actions.items()}

        # Validate at least one file is kept
        if not any(action == "keep" for action in actions_to_apply.values()):
            messagebox.showerror("Invalid Action",
                "You must keep at least one file.\n\n"
                "Please select 'Keep' for at least one file.")
            return

        # Confirm actions
        delete_count = sum(1 for action in actions_to_apply.values() if action == "delete")
        rename_count = sum(1 for action in actions_to_apply.values() if action == "rename")

        msg = f"Apply the following actions?\n\n"
        msg += f"Delete: {delete_count} file(s)\n"
        msg += f"Rename: {rename_count} file(s)\n\n"
        msg += f"⚠️  Files will be deleted from DATABASE only (not disk)"

        result = messagebox.askyesno("Confirm Actions", msg)
        if not result:
            return

        # Apply actions
        conn = sqlite3.connect("gcode_database.db")
        cursor = conn.cursor()

        deleted = 0
        renamed = 0

        for prog_num, action in actions_to_apply.items():
            if action == "delete":
                cursor.execute("DELETE FROM programs WHERE program_number = ?", (prog_num,))
                deleted += 1
            elif action == "rename":
                # Prompt for new name
                new_name = self.prompt_rename(prog_num)
                if new_name and new_name != prog_num:
                    # Get file_path for this program
                    file_info = self.files_lookup.get(prog_num)
                    if file_info and len(file_info) > 2:
                        file_path = file_info[2]  # file_path is at index 2

                        # Update internal G-code program number if we have manager access
                        if self.manager and file_path and os.path.exists(file_path):
                            if not self.manager.update_gcode_program_number(file_path, new_name):
                                print(f"Warning: Could not update internal O-number in {file_path}")

                    # Update database
                    cursor.execute("""
                        UPDATE programs
                        SET program_number = ?
                        WHERE program_number = ?
                    """, (new_name, prog_num))
                    renamed += 1

        conn.commit()
        conn.close()

        # Show results
        messagebox.showinfo("Actions Applied",
            f"Successfully applied actions:\n\n"
            f"Deleted: {deleted} file(s)\n"
            f"Renamed: {renamed} file(s)")

        # Refresh parent and close
        if self.refresh_callback:
            self.refresh_callback()
        self.window.destroy()

    def prompt_rename(self, old_name):
        """Prompt user for new filename"""
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Rename {old_name}")
        dialog.geometry("400x150")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.window)
        dialog.grab_set()

        tk.Label(dialog, text=f"Rename {old_name} to:",
                bg=self.bg_color, fg=self.fg_color,
                font=("Arial", 11)).pack(pady=15)

        entry = tk.Entry(dialog, bg=self.input_bg, fg=self.fg_color,
                        font=("Arial", 11), width=30)
        entry.insert(0, old_name)
        entry.pack(pady=10)
        entry.focus()
        entry.select_range(0, tk.END)

        result = [old_name]

        def confirm():
            new_name = entry.get().strip()
            if new_name:
                result[0] = new_name
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="OK", command=confirm,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Cancel", command=cancel,
                 bg=self.button_bg, fg=self.fg_color,
                 font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=5)

        entry.bind('<Return>', lambda e: confirm())
        entry.bind('<Escape>', lambda e: cancel())

        self.window.wait_window(dialog)
        return result[0]


def main():
    root = tk.Tk()
    app = GCodeDatabaseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
