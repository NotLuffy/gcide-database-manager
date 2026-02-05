"""
Phase 1 Test - Pre-Import File Scanner
Isolated test environment for the file scanning feature

This module tests the file scanner functionality independently
before integrating into the main application.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
from typing import Dict, List, Optional

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from improved_gcode_parser import ImprovedGCodeParser, GCodeParseResult
except ImportError as e:
    print(f"Error importing parser: {e}")
    print(f"Parent dir: {parent_dir}")
    print("Please ensure improved_gcode_parser.py is in the parent directory")
    sys.exit(1)


class FileScanner:
    """
    File scanner for G-code files - scans for issues without importing to database
    """

    def __init__(self):
        self.parser = ImprovedGCodeParser()

    def scan_file_for_issues(self, file_path: str) -> Dict:
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
            'raw_data': None,
            'spacer_type': None,
            'title': None,
            'material': None,
            'tools_used': [],
            'pcodes_found': []
        }

        try:
            # Parse file
            parse_result = self.parser.parse_file(file_path)
            results['raw_data'] = parse_result
            results['success'] = True

            # Extract program number
            results['program_number'] = parse_result.program_number

            # Extract round size (outer diameter)
            results['round_size'] = parse_result.outer_diameter

            # Extract spacer type
            results['spacer_type'] = parse_result.spacer_type

            # Extract title
            results['title'] = parse_result.title

            # Extract material
            results['material'] = parse_result.material

            # Extract tools
            results['tools_used'] = parse_result.tools_used

            # Extract P-codes
            results['pcodes_found'] = parse_result.pcodes_found

            # Extract dimensions
            results['dimensions'] = {
                'outer_diameter': parse_result.outer_diameter,
                'thickness': parse_result.thickness,
                'thickness_display': parse_result.thickness_display,
                'center_bore': parse_result.center_bore,
                'hub_diameter': parse_result.hub_diameter,
                'hub_height': parse_result.hub_height,
                'counter_bore_diameter': parse_result.counter_bore_diameter,
                'counter_bore_depth': parse_result.counter_bore_depth,
            }

            # Collect warnings from various sources

            # Tool home issues
            if parse_result.tool_home_issues:
                for issue in parse_result.tool_home_issues:
                    if issue.strip():
                        results['warnings'].append({
                            'type': 'tool_home',
                            'severity': 'warning',
                            'category': 'Tool Home Position',
                            'message': issue.strip(),
                            'line_number': None
                        })

            # Bore warnings
            if parse_result.bore_warnings:
                for warning in parse_result.bore_warnings:
                    if warning.strip():
                        results['warnings'].append({
                            'type': 'bore',
                            'severity': 'warning',
                            'category': 'Bore Dimensions',
                            'message': warning.strip(),
                            'line_number': None
                        })

            # Dimensional issues
            if parse_result.dimensional_issues:
                for issue in parse_result.dimensional_issues:
                    if issue.strip():
                        results['warnings'].append({
                            'type': 'dimensional',
                            'severity': 'warning',
                            'category': 'Dimensional',
                            'message': issue.strip(),
                            'line_number': None
                        })

            # Validation warnings
            if parse_result.validation_warnings:
                for warning in parse_result.validation_warnings:
                    if warning.strip():
                        results['warnings'].append({
                            'type': 'validation',
                            'severity': 'warning',
                            'category': 'Validation',
                            'message': warning.strip(),
                            'line_number': None
                        })

            # Validation issues (errors)
            if parse_result.validation_issues:
                for issue in parse_result.validation_issues:
                    if issue.strip():
                        results['errors'].append({
                            'type': 'validation',
                            'severity': 'error',
                            'category': 'Critical',
                            'message': issue.strip(),
                            'line_number': None
                        })

            # Check for missing critical dimensions
            if parse_result.outer_diameter is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'category': 'Missing Data',
                    'message': 'Outer diameter not detected',
                    'line_number': None
                })

            if parse_result.thickness is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'category': 'Missing Data',
                    'message': 'Thickness not detected',
                    'line_number': None
                })

            if parse_result.center_bore is None:
                results['warnings'].append({
                    'type': 'dimensional',
                    'severity': 'info',
                    'category': 'Missing Data',
                    'message': 'Center bore not detected',
                    'line_number': None
                })

        except Exception as e:
            results['errors'].append({
                'type': 'parse_error',
                'severity': 'error',
                'category': 'Parse Error',
                'message': f"Failed to parse file: {str(e)}",
                'line_number': None
            })

        return results


class FileScannerWindow:
    """Window for scanning G-code files before import"""

    def __init__(self, parent=None):
        self.scanner = FileScanner()
        self.current_file = None
        self.scan_results = None

        # Create main window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()

        self.window.title("G-Code File Scanner - Phase 1 Test")
        self.window.geometry("900x700")

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""

        # Header
        header = ttk.Frame(self.window)
        header.pack(fill='x', padx=10, pady=10)

        ttk.Label(header, text="Phase 1 Test Environment - Pre-Import File Scanner",
                 font=('TkDefaultFont', 12, 'bold')).pack()

        # File selection
        file_frame = ttk.LabelFrame(self.window, text="Select File to Scan")
        file_frame.pack(fill='x', padx=10, pady=10)

        file_inner = ttk.Frame(file_frame)
        file_inner.pack(fill='x', padx=10, pady=10)

        ttk.Label(file_inner, text="File:").pack(side='left')
        self.file_entry = ttk.Entry(file_inner, width=60)
        self.file_entry.pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(file_inner, text="Browse...",
                  command=self.browse_file).pack(side='left', padx=5)

        # Scan button
        scan_btn_frame = ttk.Frame(self.window)
        scan_btn_frame.pack(pady=5)

        ttk.Button(scan_btn_frame, text="🔍 Scan File",
                  command=self.scan_file,
                  style='Accent.TButton').pack()

        # Results area with tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab 1: Summary
        summary_tab = ttk.Frame(notebook)
        notebook.add(summary_tab, text="Summary")

        self.summary_text = scrolledtext.ScrolledText(
            summary_tab,
            wrap=tk.WORD,
            height=20,
            font=('Courier New', 10)
        )
        self.summary_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Configure text tags for colored output
        self.summary_text.tag_config('success', foreground='green', font=('Courier New', 10, 'bold'))
        self.summary_text.tag_config('warning', foreground='orange', font=('Courier New', 10, 'bold'))
        self.summary_text.tag_config('error', foreground='red', font=('Courier New', 10, 'bold'))
        self.summary_text.tag_config('info', foreground='blue')
        self.summary_text.tag_config('header', font=('Courier New', 11, 'bold'))
        self.summary_text.tag_config('subheader', font=('Courier New', 10, 'bold'), underline=True)

        # Tab 2: Detailed Issues
        issues_tab = ttk.Frame(notebook)
        notebook.add(issues_tab, text="Issues Details")

        # Issues tree
        issues_tree_frame = ttk.Frame(issues_tab)
        issues_tree_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Scrollbar for tree
        issues_scroll = ttk.Scrollbar(issues_tree_frame)
        issues_scroll.pack(side='right', fill='y')

        self.issues_tree = ttk.Treeview(
            issues_tree_frame,
            columns=('severity', 'category', 'message'),
            show='tree headings',
            yscrollcommand=issues_scroll.set
        )
        issues_scroll.config(command=self.issues_tree.yview)

        self.issues_tree.heading('severity', text='Severity')
        self.issues_tree.heading('category', text='Category')
        self.issues_tree.heading('message', text='Message')

        self.issues_tree.column('#0', width=50)
        self.issues_tree.column('severity', width=100)
        self.issues_tree.column('category', width=150)
        self.issues_tree.column('message', width=500)

        self.issues_tree.pack(fill='both', expand=True)

        # Tab 3: Raw Data
        raw_tab = ttk.Frame(notebook)
        notebook.add(raw_tab, text="Raw Parse Data")

        self.raw_text = scrolledtext.ScrolledText(
            raw_tab,
            wrap=tk.WORD,
            height=20,
            font=('Courier New', 9)
        )
        self.raw_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Action buttons
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=10)

        self.view_btn = ttk.Button(button_frame, text="📄 View File",
                                   command=self.view_file, state='disabled')
        self.view_btn.pack(side='left', padx=5)

        self.export_btn = ttk.Button(button_frame, text="💾 Export Report",
                                     command=self.export_report, state='disabled')
        self.export_btn.pack(side='left', padx=5)

        ttk.Button(button_frame, text="❌ Close",
                  command=self.window.destroy).pack(side='right', padx=5)

        # Status bar
        self.status_label = ttk.Label(self.window, text="Ready to scan", relief='sunken')
        self.status_label.pack(fill='x', side='bottom')

    def browse_file(self):
        """Browse for a file"""
        # Start in repository directory if it exists
        initial_dir = os.path.join(parent_dir, 'repository')
        if not os.path.exists(initial_dir):
            initial_dir = parent_dir

        filepath = filedialog.askopenfilename(
            title="Select G-Code File",
            initialdir=initial_dir,
            filetypes=[
                ("G-Code files", "*.nc"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        if filepath:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)

    def scan_file(self):
        """Scan the selected file"""
        filepath = self.file_entry.get().strip()

        if not filepath:
            messagebox.showerror("Error", "Please select a file to scan")
            return

        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"File not found: {filepath}")
            return

        self.current_file = filepath
        self.status_label.config(text=f"Scanning {os.path.basename(filepath)}...")
        self.window.update()

        try:
            # Scan file
            self.scan_results = self.scanner.scan_file_for_issues(filepath)

            # Display results
            self.display_summary()
            self.display_issues_tree()
            self.display_raw_data()

            # Enable action buttons
            self.view_btn.config(state='normal')
            self.export_btn.config(state='normal')

            # Update status
            if self.scan_results['success']:
                warn_count = len(self.scan_results['warnings'])
                err_count = len(self.scan_results['errors'])
                self.status_label.config(
                    text=f"Scan complete: {warn_count} warning(s), {err_count} error(s)"
                )
            else:
                self.status_label.config(text="Scan failed - see errors")

        except Exception as e:
            messagebox.showerror("Scan Error", f"Error scanning file:\n{str(e)}")
            self.status_label.config(text="Scan failed")

    def display_summary(self):
        """Display scan results summary"""
        t = self.summary_text
        t.delete(1.0, tk.END)

        results = self.scan_results

        # Header
        t.insert(tk.END, "="*80 + "\n", 'header')
        t.insert(tk.END, "G-CODE FILE SCAN RESULTS\n", 'header')
        t.insert(tk.END, "="*80 + "\n", 'header')
        t.insert(tk.END, f"\nFile: {os.path.basename(self.current_file)}\n")
        t.insert(tk.END, f"Path: {self.current_file}\n\n")

        if results['success']:
            t.insert(tk.END, "✓ ", 'success')
            t.insert(tk.END, "File parsed successfully\n\n")

            # Program information
            t.insert(tk.END, "PROGRAM INFORMATION\n", 'subheader')
            t.insert(tk.END, "-" * 80 + "\n")

            if results['program_number']:
                t.insert(tk.END, f"  Program Number:  {results['program_number']}\n")

            if results['title']:
                t.insert(tk.END, f"  Title:           {results['title']}\n")

            if results['round_size']:
                t.insert(tk.END, f"  Round Size:      {results['round_size']}\"\n")

            if results['spacer_type']:
                t.insert(tk.END, f"  Spacer Type:     {results['spacer_type']}\n")

            if results['material']:
                t.insert(tk.END, f"  Material:        {results['material']}\n")

            if results['tools_used']:
                t.insert(tk.END, f"  Tools Used:      {', '.join(results['tools_used'])}\n")

            if results['pcodes_found']:
                t.insert(tk.END, f"  P-Codes Found:   {', '.join(map(str, results['pcodes_found']))}\n")

            # Dimensions
            t.insert(tk.END, "\n\nDIMENSIONS\n", 'subheader')
            t.insert(tk.END, "-" * 80 + "\n")

            dims = results['dimensions']
            dim_labels = {
                'outer_diameter': 'Outer Diameter (OD)',
                'thickness': 'Thickness',
                'thickness_display': 'Thickness Display',
                'center_bore': 'Center Bore (CB)',
                'hub_diameter': 'Hub Diameter (OB)',
                'hub_height': 'Hub Height',
                'counter_bore_diameter': 'Counter Bore Diameter',
                'counter_bore_depth': 'Counter Bore Depth'
            }

            for key, label in dim_labels.items():
                value = dims.get(key)
                if value is not None:
                    t.insert(tk.END, f"  ✓ {label:30} {value}\n", 'success')
                else:
                    t.insert(tk.END, f"  - {label:30} Not detected\n", 'info')

            # Warnings
            t.insert(tk.END, "\n\nISSUES\n", 'subheader')
            t.insert(tk.END, "-" * 80 + "\n")

            if results['errors']:
                t.insert(tk.END, f"\n❌ ERRORS ({len(results['errors'])})\n", 'error')
                for i, error in enumerate(results['errors'], 1):
                    t.insert(tk.END, f"  {i}. [{error['category']}] {error['message']}\n", 'error')

            if results['warnings']:
                t.insert(tk.END, f"\n⚠️  WARNINGS ({len(results['warnings'])})\n", 'warning')

                # Group warnings by category
                categories = {}
                for warning in results['warnings']:
                    cat = warning['category']
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(warning['message'])

                for category, messages in categories.items():
                    t.insert(tk.END, f"\n  {category}:\n", 'warning')
                    for i, msg in enumerate(messages, 1):
                        t.insert(tk.END, f"    {i}. {msg}\n", 'warning')

            if not results['warnings'] and not results['errors']:
                t.insert(tk.END, "\n✓ No issues found - file is clean!\n", 'success')

        else:
            t.insert(tk.END, "❌ ", 'error')
            t.insert(tk.END, "Failed to parse file\n\n", 'error')

            if results['errors']:
                for error in results['errors']:
                    t.insert(tk.END, f"  • {error['message']}\n", 'error')

    def display_issues_tree(self):
        """Display issues in tree view"""
        # Clear tree
        for item in self.issues_tree.get_children():
            self.issues_tree.delete(item)

        results = self.scan_results

        if not results['success']:
            return

        # Add errors
        if results['errors']:
            error_node = self.issues_tree.insert('', 'end', text='❌',
                                                 values=('ERROR', 'Errors', f"{len(results['errors'])} error(s)"))
            for error in results['errors']:
                self.issues_tree.insert(error_node, 'end', text='',
                                       values=('ERROR', error['category'], error['message']))

        # Add warnings grouped by category
        if results['warnings']:
            warning_node = self.issues_tree.insert('', 'end', text='⚠️',
                                                   values=('WARNING', 'Warnings', f"{len(results['warnings'])} warning(s)"))

            # Group by category
            categories = {}
            for warning in results['warnings']:
                cat = warning['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(warning)

            for category, warnings in categories.items():
                cat_node = self.issues_tree.insert(warning_node, 'end', text='📁',
                                                   values=('WARNING', category, f"{len(warnings)} warning(s)"))
                for warning in warnings:
                    severity = warning['severity'].upper()
                    self.issues_tree.insert(cat_node, 'end', text='•',
                                          values=(severity, category, warning['message']))

        # Add info if no issues
        if not results['warnings'] and not results['errors']:
            self.issues_tree.insert('', 'end', text='✓',
                                   values=('INFO', 'Success', 'No issues found'))

    def display_raw_data(self):
        """Display raw parse data"""
        t = self.raw_text
        t.delete(1.0, tk.END)

        results = self.scan_results

        if not results['success'] or not results['raw_data']:
            t.insert(tk.END, "No parse data available")
            return

        raw = results['raw_data']

        # Display all attributes
        t.insert(tk.END, "RAW PARSE RESULT DATA\n")
        t.insert(tk.END, "=" * 80 + "\n\n")

        # Get all attributes from the dataclass
        for field_name in raw.__dataclass_fields__:
            value = getattr(raw, field_name)

            # Format the value
            if isinstance(value, list):
                if value:
                    t.insert(tk.END, f"{field_name}:\n")
                    for item in value:
                        t.insert(tk.END, f"  - {item}\n")
                else:
                    t.insert(tk.END, f"{field_name}: []\n")
            elif isinstance(value, dict):
                t.insert(tk.END, f"{field_name}:\n")
                for k, v in value.items():
                    t.insert(tk.END, f"  {k}: {v}\n")
            else:
                t.insert(tk.END, f"{field_name}: {value}\n")

            t.insert(tk.END, "\n")

    def view_file(self):
        """Open file in default text editor"""
        if self.current_file:
            try:
                os.startfile(self.current_file)  # Windows
            except AttributeError:
                # Linux/Mac
                import subprocess
                subprocess.run(['xdg-open', self.current_file])

    def export_report(self):
        """Export scan report to text file"""
        if not self.scan_results:
            return

        # Ask for save location
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"scan_report_{os.path.basename(self.current_file)}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'w') as f:
                    # Write summary
                    content = self.summary_text.get(1.0, tk.END)
                    f.write(content)

                    # Write raw data
                    f.write("\n\n" + "=" * 80 + "\n")
                    f.write("RAW PARSE DATA\n")
                    f.write("=" * 80 + "\n\n")
                    raw_content = self.raw_text.get(1.0, tk.END)
                    f.write(raw_content)

                messagebox.showinfo("Success", f"Report exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export report:\n{str(e)}")

    def run(self):
        """Run the application"""
        self.window.mainloop()


def main():
    """Main entry point for testing"""
    print("="*80)
    print("Phase 1 Test Environment - Pre-Import File Scanner")
    print("="*80)
    print()
    print("This is an isolated test environment for the file scanner feature.")
    print("It does NOT modify the main database or application.")
    print()

    app = FileScannerWindow()
    app.run()


if __name__ == '__main__':
    main()
