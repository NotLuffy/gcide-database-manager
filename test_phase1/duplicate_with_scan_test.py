"""
Phase 1.4 Test - Duplicate with Automatic Scan
Isolated test environment for duplicating programs with automatic scanning

This module tests the duplicate-with-scan functionality that:
1. Scans the source file before duplicating
2. Shows warnings to the user
3. Optionally fixes warnings in the new file
4. Optionally opens the new file in an editor
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import re
import shutil
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the file scanner from Phase 1.1
try:
    from file_scanner_test import FileScanner
except ImportError:
    print("ERROR: Could not import FileScanner from Phase 1.1")
    print("Make sure file_scanner_test.py exists in the same directory")
    sys.exit(1)


class AutoFixer:
    """
    Automatic fixer for common G-code issues
    """

    @staticmethod
    def fix_tool_home_z(content, expected_z):
        """
        Fix tool home Z position

        Args:
            content: G-code file content
            expected_z: Expected Z value (e.g., -10.0)

        Returns:
            str: Fixed content
        """
        # Pattern: G43 H## Z-##.#
        pattern = r'(G43\s+H\d+\s+Z)(-?\d+\.?\d*)'

        def replace_z(match):
            return f"{match.group(1)}{expected_z}"

        fixed = re.sub(pattern, replace_z, content, flags=re.IGNORECASE)
        return fixed

    @staticmethod
    def fix_coolant_sequence(content):
        """
        Fix M09/M05 sequence - ensure M09 comes before M05

        Args:
            content: G-code file content

        Returns:
            str: Fixed content
        """
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Check if this line has M05 but no M09 before it
            if 'M05' in line.upper():
                # Look at previous line
                if i > 0 and 'M09' not in fixed_lines[-1].upper():
                    # Insert M09 before this line
                    fixed_lines.append('M09')

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    @staticmethod
    def apply_all_fixes(content, scan_results):
        """
        Apply all applicable fixes based on scan results

        Args:
            content: G-code file content
            scan_results: Results from FileScanner

        Returns:
            tuple: (fixed_content, list of fixes applied)
        """
        fixes_applied = []
        fixed = content

        # Check for tool home issues
        if scan_results['warnings']:
            for warning in scan_results['warnings']:
                msg = warning['message'].lower()

                # Fix tool home Z
                if 'tool home' in msg and 'z' in msg:
                    # Try to extract expected Z value from message
                    match = re.search(r'expected.*?z-?(\d+\.?\d*)', msg, re.IGNORECASE)
                    if match:
                        expected_z = f"-{match.group(1)}"
                        fixed = AutoFixer.fix_tool_home_z(fixed, expected_z)
                        fixes_applied.append(f"Fixed tool home Z to {expected_z}")

                # Fix M09/M05 sequence
                if 'm09' in msg and 'm05' in msg:
                    fixed = AutoFixer.fix_coolant_sequence(fixed)
                    fixes_applied.append("Fixed M09/M05 sequence")

        return fixed, fixes_applied


class DuplicateWithScanDialog:
    """Dialog for duplicating a file with automatic scanning"""

    def __init__(self, parent=None):
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()

        self.window.title("Duplicate with Scan - Phase 1.4 Test")
        self.window.geometry("900x750")

        # Initialize scanner
        self.scanner = FileScanner()

        # State
        self.source_file = None
        self.scan_results = None
        self.result = None

        # Options
        self.fix_warnings_var = tk.BooleanVar(value=False)
        self.edit_after_var = tk.BooleanVar(value=False)

        self.setup_ui()

    def setup_ui(self):
        """Set up user interface"""

        # Header
        header = ttk.Frame(self.window)
        header.pack(fill='x', padx=10, pady=10)

        ttk.Label(header, text="Phase 1.4 Test - Duplicate with Automatic Scan",
                 font=('TkDefaultFont', 12, 'bold')).pack()

        # Source file selection
        source_frame = ttk.LabelFrame(self.window, text="Source File")
        source_frame.pack(fill='x', padx=10, pady=10)

        source_inner = ttk.Frame(source_frame)
        source_inner.pack(fill='x', padx=10, pady=10)

        ttk.Label(source_inner, text="Source:").pack(side='left')
        self.source_entry = ttk.Entry(source_inner, width=60)
        self.source_entry.pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(source_inner, text="Browse...",
                  command=self.browse_source).pack(side='left', padx=5)

        # Scan button
        ttk.Button(source_frame, text="🔍 Scan Source File",
                  command=self.scan_source).pack(pady=5)

        # Scan results
        results_frame = ttk.LabelFrame(self.window, text="Source File Scan Results")
        results_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            height=15,
            font=('Courier New', 9)
        )
        self.results_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Configure tags
        self.results_text.tag_config('success', foreground='green')
        self.results_text.tag_config('warning', foreground='orange')
        self.results_text.tag_config('error', foreground='red')
        self.results_text.tag_config('header', font=('Courier New', 10, 'bold'))

        # Duplicate settings
        settings_frame = ttk.LabelFrame(self.window, text="Duplicate Settings")
        settings_frame.pack(fill='x', padx=10, pady=10)

        settings_inner = ttk.Frame(settings_frame)
        settings_inner.pack(padx=10, pady=10)

        # New file name
        name_row = ttk.Frame(settings_inner)
        name_row.pack(fill='x', pady=5)

        ttk.Label(name_row, text="New file name:").pack(side='left')
        self.new_name_entry = ttk.Entry(name_row, width=50)
        self.new_name_entry.pack(side='left', padx=5)

        # Options
        self.fix_warnings_cb = ttk.Checkbutton(
            settings_inner,
            text="Auto-fix warnings in new file",
            variable=self.fix_warnings_var,
            state='disabled'
        )
        self.fix_warnings_cb.pack(anchor='w', pady=2)

        ttk.Checkbutton(
            settings_inner,
            text="Open in editor after creation",
            variable=self.edit_after_var
        ).pack(anchor='w', pady=2)

        # Action buttons
        action_frame = ttk.Frame(self.window)
        action_frame.pack(fill='x', padx=10, pady=10)

        self.duplicate_btn = ttk.Button(
            action_frame,
            text="📄 Create Duplicate",
            command=self.create_duplicate,
            state='disabled'
        )
        self.duplicate_btn.pack(side='left', padx=5)

        ttk.Button(action_frame, text="❌ Close",
                  command=self.window.destroy).pack(side='right', padx=5)

        # Status bar
        self.status_label = ttk.Label(self.window, text="Select a source file to begin",
                                     relief='sunken')
        self.status_label.pack(fill='x', side='bottom')

    def browse_source(self):
        """Browse for source file"""
        initial_dir = os.path.join(parent_dir, 'repository')
        if not os.path.exists(initial_dir):
            initial_dir = parent_dir

        filepath = filedialog.askopenfilename(
            title="Select Source G-Code File",
            initialdir=initial_dir,
            filetypes=[("G-Code files", "*.nc"), ("All files", "*.*")]
        )

        if filepath:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, filepath)

            # Auto-generate new filename
            base = os.path.basename(filepath)
            name, ext = os.path.splitext(base)
            new_name = f"{name}_copy{ext}"
            self.new_name_entry.delete(0, tk.END)
            self.new_name_entry.insert(0, new_name)

    def scan_source(self):
        """Scan the source file"""
        source_path = self.source_entry.get().strip()

        if not source_path:
            messagebox.showerror("Error", "Please select a source file")
            return

        if not os.path.exists(source_path):
            messagebox.showerror("Error", f"Source file not found:\n{source_path}")
            return

        self.source_file = source_path
        self.status_label.config(text=f"Scanning {os.path.basename(source_path)}...")
        self.window.update()

        try:
            # Scan the file
            self.scan_results = self.scanner.scan_file_for_issues(source_path)

            # Display results
            self.display_scan_results()

            # Enable duplicate button
            self.duplicate_btn.config(state='normal')

            # Enable fix warnings if warnings exist
            if self.scan_results['warnings']:
                self.fix_warnings_cb.config(state='normal')

            # Update status
            warn_count = len(self.scan_results['warnings'])
            err_count = len(self.scan_results['errors'])

            if err_count > 0:
                self.status_label.config(
                    text=f"Scan complete: {warn_count} warning(s), {err_count} error(s) - Review before duplicating"
                )
            elif warn_count > 0:
                self.status_label.config(
                    text=f"Scan complete: {warn_count} warning(s) found - Consider auto-fix option"
                )
            else:
                self.status_label.config(text="Scan complete: No issues found - Safe to duplicate")

        except Exception as e:
            messagebox.showerror("Scan Error", f"Failed to scan file:\n{str(e)}")
            self.status_label.config(text="Scan failed")

    def display_scan_results(self):
        """Display scan results"""
        t = self.results_text
        t.delete(1.0, tk.END)

        results = self.scan_results

        if not results['success']:
            t.insert(tk.END, "❌ Failed to scan file\n\n", 'error')
            for error in results['errors']:
                t.insert(tk.END, f"  • {error['message']}\n", 'error')
            return

        # Summary
        t.insert(tk.END, "SOURCE FILE SCAN RESULTS\n", 'header')
        t.insert(tk.END, "=" * 60 + "\n\n")

        t.insert(tk.END, f"File: {os.path.basename(self.source_file)}\n")
        if results['program_number']:
            t.insert(tk.END, f"Program: {results['program_number']}\n")
        if results['round_size']:
            t.insert(tk.END, f"Round Size: {results['round_size']}\"\n")

        # Errors
        if results['errors']:
            t.insert(tk.END, f"\n❌ ERRORS ({len(results['errors'])})\n", 'error')
            for error in results['errors']:
                t.insert(tk.END, f"  • {error['message']}\n", 'error')

        # Warnings
        if results['warnings']:
            t.insert(tk.END, f"\n⚠️  WARNINGS ({len(results['warnings'])})\n", 'warning')

            # Group by category
            categories = {}
            for warning in results['warnings']:
                cat = warning['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(warning['message'])

            for category, messages in categories.items():
                t.insert(tk.END, f"\n  {category}:\n", 'warning')
                for msg in messages:
                    t.insert(tk.END, f"    • {msg}\n", 'warning')

        # No issues
        if not results['warnings'] and not results['errors']:
            t.insert(tk.END, "\n✓ No issues found - file is clean!\n", 'success')

    def create_duplicate(self):
        """Create the duplicate file"""
        if not self.source_file or not self.scan_results:
            messagebox.showerror("Error", "Please scan the source file first")
            return

        new_name = self.new_name_entry.get().strip()
        if not new_name:
            messagebox.showerror("Error", "Please enter a new file name")
            return

        # Confirm if warnings exist
        if self.scan_results['warnings']:
            warn_count = len(self.scan_results['warnings'])

            if not messagebox.askyesno(
                "Warnings Detected",
                f"The source file has {warn_count} warning(s).\n\n"
                "Do you want to proceed with duplication?",
                icon='warning'
            ):
                return

        # Determine destination path
        source_dir = os.path.dirname(self.source_file)
        dest_path = os.path.join(source_dir, new_name)

        # Check if destination exists
        if os.path.exists(dest_path):
            if not messagebox.askyesno(
                "File Exists",
                f"File already exists:\n{new_name}\n\nOverwrite?",
                icon='warning'
            ):
                return

        try:
            # Read source content
            with open(self.source_file, 'r') as f:
                content = f.read()

            # Apply fixes if requested
            fixes_applied = []
            if self.fix_warnings_var.get() and self.scan_results['warnings']:
                content, fixes_applied = AutoFixer.apply_all_fixes(content, self.scan_results)

            # Write to destination
            with open(dest_path, 'w') as f:
                f.write(content)

            # Success message
            msg = f"Duplicate created successfully:\n\n{dest_path}"
            if fixes_applied:
                msg += "\n\nFixes applied:\n"
                for fix in fixes_applied:
                    msg += f"  • {fix}\n"

            messagebox.showinfo("Success", msg)

            # Open in editor if requested
            if self.edit_after_var.get():
                try:
                    os.startfile(dest_path)  # Windows
                except AttributeError:
                    import subprocess
                    subprocess.run(['xdg-open', dest_path])  # Linux/Mac

            self.status_label.config(text=f"Duplicate created: {new_name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create duplicate:\n{str(e)}")

    def run(self):
        """Run the application"""
        self.window.mainloop()


def main():
    """Main entry point"""
    print("="*80)
    print("Phase 1.4 Test Environment - Duplicate with Automatic Scan")
    print("="*80)
    print()
    print("This test environment demonstrates duplicating G-code files with")
    print("automatic scanning for issues, optional auto-fix, and editor integration.")
    print()

    app = DuplicateWithScanDialog()
    app.run()


if __name__ == '__main__':
    main()
