"""
USB Sync Manager - GUI

User interface for managing USB drive synchronization with repository.

Features:
- Manual drive registration and scanning
- TreeView table with sync status display
- Color-coded status indicators
- Manual selective copy operations
- Conflict resolution dialog (uses GCodeDiffEngine)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from usb_sync_manager import USBSyncManager
from gcode_diff_engine import GCodeDiffEngine


class USBSyncGUI:
    """Main USB Sync Manager GUI window"""

    def __init__(self, parent, db_path: str, repository_path: str):
        """
        Initialize USB Sync GUI.

        Args:
            parent: Parent window
            db_path: Path to database
            repository_path: Path to repository
        """
        self.parent = parent
        self.db_path = db_path
        self.repository_path = repository_path
        self.manager = USBSyncManager(db_path, repository_path)

        # Current state
        self.current_drive = None
        self.current_filter = "All"

        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("USB Sync Manager")
        self.window.geometry("1200x700")

        # Build UI
        self._build_ui()

        # Load initial data
        self._load_registered_drives()

    def _build_ui(self):
        """Build the user interface"""

        # =============================================================
        # TOP CONTROLS
        # =============================================================
        top_frame = tk.Frame(self.window, bg='#f0f0f0', padx=10, pady=10)
        top_frame.pack(fill=tk.X)

        # Drive selection
        tk.Label(top_frame, text="Drive:", bg='#f0f0f0', font=('Segoe UI', 10)).grid(row=0, column=0, padx=5, sticky=tk.W)

        self.drive_combo = ttk.Combobox(top_frame, width=25, state='readonly')
        self.drive_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        self.drive_combo.bind('<<ComboboxSelected>>', self._on_drive_selected)

        # Scan button
        self.scan_button = tk.Button(
            top_frame,
            text="Scan",
            command=self._scan_drive,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=15,
            width=8
        )
        self.scan_button.grid(row=0, column=2, padx=5)

        # Register button
        register_button = tk.Button(
            top_frame,
            text="Register",
            command=self._register_drive,
            bg='#2196F3',
            fg='white',
            font=('Segoe UI', 10),
            padx=15,
            width=10
        )
        register_button.grid(row=0, column=3, padx=5)

        # Last scan label
        self.last_scan_label = tk.Label(
            top_frame,
            text="Last scan: Never",
            bg='#f0f0f0',
            font=('Segoe UI', 9),
            fg='#666'
        )
        self.last_scan_label.grid(row=0, column=4, padx=15, sticky=tk.W)

        # =============================================================
        # FILTER CONTROLS
        # =============================================================
        filter_frame = tk.Frame(self.window, bg='#f0f0f0', padx=10, pady=5)
        filter_frame.pack(fill=tk.X)

        tk.Label(filter_frame, text="Filter:", bg='#f0f0f0', font=('Segoe UI', 10)).grid(row=0, column=0, padx=5, sticky=tk.W)

        self.filter_combo = ttk.Combobox(
            filter_frame,
            width=20,
            state='readonly',
            values=["All", "Conflicts", "Out of Sync", "In Sync", "USB Newer", "Repo Newer", "Missing"]
        )
        self.filter_combo.current(0)
        self.filter_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        self.filter_combo.bind('<<ComboboxSelected>>', self._apply_filter)

        # Quick filter buttons
        tk.Button(
            filter_frame,
            text="Conflicts",
            command=lambda: self._quick_filter("CONFLICT"),
            bg='#FF5722',
            fg='white',
            font=('Segoe UI', 9),
            padx=10
        ).grid(row=0, column=2, padx=5)

        tk.Button(
            filter_frame,
            text="Out of Sync",
            command=lambda: self._quick_filter("OUT_OF_SYNC"),
            bg='#FF9800',
            fg='white',
            font=('Segoe UI', 9),
            padx=10
        ).grid(row=0, column=3, padx=5)

        # Refresh button
        tk.Button(
            filter_frame,
            text="Refresh",
            command=self._refresh_display,
            bg='#9E9E9E',
            fg='white',
            font=('Segoe UI', 9),
            padx=10
        ).grid(row=0, column=4, padx=5)

        # =============================================================
        # TREEVIEW TABLE
        # =============================================================
        table_frame = tk.Frame(self.window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbars
        y_scroll = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        x_scroll = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # TreeView
        columns = ("Program", "Repo Version", "USB Version", "Status", "Repo Hash", "USB Hash")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='tree headings',
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
            selectmode='extended'
        )

        # Configure scrollbars
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        # Column headings
        self.tree.heading('#0', text='☑', anchor=tk.W)
        self.tree.column('#0', width=30, stretch=False)

        self.tree.heading('Program', text='Program', anchor=tk.W)
        self.tree.column('Program', width=120, stretch=False)

        self.tree.heading('Repo Version', text='Repo Version', anchor=tk.W)
        self.tree.column('Repo Version', width=150, stretch=False)

        self.tree.heading('USB Version', text='USB Version', anchor=tk.W)
        self.tree.column('USB Version', width=150, stretch=False)

        self.tree.heading('Status', text='Status', anchor=tk.W)
        self.tree.column('Status', width=120, stretch=False)

        self.tree.heading('Repo Hash', text='Repo Hash', anchor=tk.W)
        self.tree.column('Repo Hash', width=200, stretch=True)

        self.tree.heading('USB Hash', text='USB Hash', anchor=tk.W)
        self.tree.column('USB Hash', width=200, stretch=True)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Configure row tags for color coding
        self.tree.tag_configure('in_sync', background='#C8E6C9')  # Green
        self.tree.tag_configure('repo_newer', background='#FFF9C4')  # Yellow
        self.tree.tag_configure('usb_newer', background='#FFE0B2')  # Orange
        self.tree.tag_configure('conflict', background='#FFCDD2')  # Red
        self.tree.tag_configure('missing', background='#E0E0E0')  # Gray

        # Double-click to view diff
        self.tree.bind('<Double-Button-1>', self._view_diff)

        # Right-click menu
        self.tree_menu = tk.Menu(self.tree, tearoff=0)
        self.tree_menu.add_command(label="View Diff", command=self._view_diff)
        self.tree_menu.add_command(label="Resolve Conflict", command=self._resolve_conflict)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Copy to USB", command=self._copy_selected_to_usb)
        self.tree_menu.add_command(label="Copy from USB", command=self._copy_selected_from_usb)

        self.tree.bind('<Button-3>', self._show_context_menu)

        # =============================================================
        # BOTTOM CONTROLS
        # =============================================================
        bottom_frame = tk.Frame(self.window, bg='#f0f0f0', padx=10, pady=10)
        bottom_frame.pack(fill=tk.X)

        # Selection count
        self.selection_label = tk.Label(
            bottom_frame,
            text="Selected: 0",
            bg='#f0f0f0',
            font=('Segoe UI', 10, 'bold')
        )
        self.selection_label.pack(side=tk.LEFT, padx=10)

        # Copy buttons
        tk.Button(
            bottom_frame,
            text="Copy to USB →",
            command=self._copy_selected_to_usb,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            bottom_frame,
            text="← Copy from USB",
            command=self._copy_selected_from_usb,
            bg='#2196F3',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        # Statistics (right side)
        self.stats_label = tk.Label(
            bottom_frame,
            text="",
            bg='#f0f0f0',
            font=('Segoe UI', 9),
            fg='#666'
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self._update_selection_count)

    # =============================================================
    # DRIVE MANAGEMENT
    # =============================================================

    def _load_registered_drives(self):
        """Load registered drives into combo box"""
        drives = self.manager.get_registered_drives()
        drive_labels = [d['drive_label'] for d in drives]

        self.drive_combo['values'] = drive_labels
        if len(drive_labels) > 0:
            self.drive_combo.current(0)
            self._on_drive_selected(None)

    def _register_drive(self):
        """Show drive registration dialog"""
        dialog = DriveRegistrationDialog(self.window, self.manager)
        if dialog.result:
            self._load_registered_drives()
            messagebox.showinfo("Success", f"Drive '{dialog.result['drive_label']}' registered successfully!")

    def _on_drive_selected(self, event):
        """Handle drive selection"""
        selected = self.drive_combo.get()
        if selected:
            self.current_drive = selected
            self._refresh_display()

    # =============================================================
    # SCANNING
    # =============================================================

    def _scan_drive(self):
        """Scan current drive"""
        if not self.current_drive:
            messagebox.showwarning("No Drive", "Please select a drive first.")
            return

        # Get drive path
        drive_path = self.manager.get_drive_path(self.current_drive)
        if not drive_path or not os.path.exists(drive_path):
            messagebox.showerror("Drive Not Found", f"Drive path not accessible:\n{drive_path}\n\nPlease update the drive path.")
            return

        # Show progress
        self.scan_button.config(state='disabled', text="Scanning...")
        self.window.update()

        try:
            # Run scan
            result = self.manager.scan_drive(self.current_drive, drive_path)

            if result.get('success'):
                # Update display
                self._refresh_display()

                # Show results
                stats_msg = (
                    f"Scan complete!\n\n"
                    f"Total scanned: {result['total_scanned']}\n"
                    f"In sync: {result['in_sync']}\n"
                    f"Repo newer: {result['repo_newer']}\n"
                    f"USB newer: {result['usb_newer']}\n"
                    f"Conflicts: {result['conflict']}\n"
                    f"USB missing: {result['usb_missing']}\n"
                    f"Repo missing: {result['repo_missing']}"
                )
                messagebox.showinfo("Scan Complete", stats_msg)
            else:
                messagebox.showerror("Scan Failed", f"Error: {result.get('error', 'Unknown error')}")

        finally:
            self.scan_button.config(state='normal', text="Scan")

    # =============================================================
    # DISPLAY
    # =============================================================

    def _refresh_display(self):
        """Refresh the display with current sync status"""
        if not self.current_drive:
            return

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get sync status
        status_list = self.manager.get_sync_status(self.current_drive)

        # Apply filter
        if self.current_filter == "Conflicts":
            status_list = [s for s in status_list if s['sync_status'] == 'CONFLICT']
        elif self.current_filter == "Out of Sync":
            status_list = [s for s in status_list if s['sync_status'] in ['REPO_NEWER', 'USB_NEWER', 'CONFLICT']]
        elif self.current_filter == "In Sync":
            status_list = [s for s in status_list if s['sync_status'] == 'IN_SYNC']
        elif self.current_filter == "USB Newer":
            status_list = [s for s in status_list if s['sync_status'] == 'USB_NEWER']
        elif self.current_filter == "Repo Newer":
            status_list = [s for s in status_list if s['sync_status'] == 'REPO_NEWER']
        elif self.current_filter == "Missing":
            status_list = [s for s in status_list if s['sync_status'] in ['USB_MISSING', 'REPO_MISSING']]

        # Populate tree
        for status in status_list:
            # Format dates
            repo_ver = self._format_datetime(status['repo_modified']) if status['repo_modified'] else "—"
            usb_ver = self._format_datetime(status['usb_modified']) if status['usb_modified'] else "—"

            # Format hashes
            repo_hash = status['repo_hash'][:16] + "..." if status['repo_hash'] else "—"
            usb_hash = status['usb_hash'][:16] + "..." if status['usb_hash'] else "—"

            # Determine tag for color coding
            sync_status = status['sync_status']
            if sync_status == 'IN_SYNC':
                tag = 'in_sync'
                status_text = "✓ In Sync"
            elif sync_status == 'REPO_NEWER':
                tag = 'repo_newer'
                status_text = "↑ Repo Newer"
            elif sync_status == 'USB_NEWER':
                tag = 'usb_newer'
                status_text = "↓ USB Newer"
            elif sync_status == 'CONFLICT':
                tag = 'conflict'
                status_text = "⚠ Conflict"
            elif sync_status in ['USB_MISSING', 'REPO_MISSING']:
                tag = 'missing'
                status_text = f"✗ {sync_status.replace('_', ' ').title()}"
            else:
                tag = ''
                status_text = sync_status

            # Insert row
            self.tree.insert(
                '',
                tk.END,
                text='☐',
                values=(
                    status['program_number'],
                    repo_ver,
                    usb_ver,
                    status_text,
                    repo_hash,
                    usb_hash
                ),
                tags=(tag,)
            )

        # Update statistics
        self._update_statistics(status_list)

        # Update last scan label
        drives = self.manager.get_registered_drives()
        current_drive_info = next((d for d in drives if d['drive_label'] == self.current_drive), None)
        if current_drive_info and current_drive_info['last_scan_date']:
            scan_time = self._format_datetime(current_drive_info['last_scan_date'])
            self.last_scan_label.config(text=f"Last scan: {scan_time}")
        else:
            self.last_scan_label.config(text="Last scan: Never")

    def _apply_filter(self, event):
        """Apply selected filter"""
        self.current_filter = self.filter_combo.get()
        self._refresh_display()

    def _quick_filter(self, filter_type: str):
        """Apply quick filter"""
        if filter_type == "CONFLICT":
            self.filter_combo.set("Conflicts")
            self.current_filter = "Conflicts"
        elif filter_type == "OUT_OF_SYNC":
            self.filter_combo.set("Out of Sync")
            self.current_filter = "Out of Sync"

        self._refresh_display()

    def _update_statistics(self, status_list: List[Dict]):
        """Update statistics label"""
        total = len(status_list)
        in_sync = len([s for s in status_list if s['sync_status'] == 'IN_SYNC'])
        conflicts = len([s for s in status_list if s['sync_status'] == 'CONFLICT'])
        out_of_sync = len([s for s in status_list if s['sync_status'] in ['REPO_NEWER', 'USB_NEWER']])

        stats_text = f"Total: {total} | In Sync: {in_sync} | Out of Sync: {out_of_sync} | Conflicts: {conflicts}"
        self.stats_label.config(text=stats_text)

    def _update_selection_count(self, event):
        """Update selection count label"""
        selected = len(self.tree.selection())
        self.selection_label.config(text=f"Selected: {selected}")

    @staticmethod
    def _format_datetime(dt_str: str) -> str:
        """Format ISO datetime string for display"""
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%m/%d %H:%M")
        except:
            return dt_str

    # =============================================================
    # COPY OPERATIONS
    # =============================================================

    def _copy_selected_to_usb(self):
        """Copy selected files from repo to USB"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select files to copy.")
            return

        if not self.current_drive:
            messagebox.showwarning("No Drive", "Please select a drive first.")
            return

        # Get program numbers
        program_numbers = []
        for item in selected_items:
            values = self.tree.item(item, 'values')
            program_numbers.append(values[0])  # Program number is first column

        # Confirm
        confirm = messagebox.askyesno(
            "Confirm Copy",
            f"Copy {len(program_numbers)} file(s) from repository to USB?\n\n"
            f"Drive: {self.current_drive}"
        )

        if not confirm:
            return

        # Execute copy
        result = self.manager.copy_to_usb(self.current_drive, program_numbers)

        # Show results
        if result['success']:
            msg = (
                f"Copy complete!\n\n"
                f"Copied: {len(result['copied'])}\n"
                f"Skipped: {len(result['skipped'])}\n"
                f"Errors: {len(result['errors'])}"
            )

            if result['errors']:
                msg += "\n\nErrors:\n" + "\n".join([f"- {e['program']}: {e['error']}" for e in result['errors'][:5]])

            messagebox.showinfo("Copy Complete", msg)

            # Refresh display
            self._refresh_display()
        else:
            messagebox.showerror("Copy Failed", f"Error: {result.get('error', 'Unknown error')}")

    def _copy_selected_from_usb(self):
        """Copy selected files from USB to repo"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select files to copy.")
            return

        if not self.current_drive:
            messagebox.showwarning("No Drive", "Please select a drive first.")
            return

        # Get program numbers
        program_numbers = []
        for item in selected_items:
            values = self.tree.item(item, 'values')
            program_numbers.append(values[0])

        # Confirm with backup warning
        confirm = messagebox.askyesno(
            "Confirm Import",
            f"Import {len(program_numbers)} file(s) from USB to repository?\n\n"
            f"Drive: {self.current_drive}\n\n"
            f"Existing repository files will be automatically backed up."
        )

        if not confirm:
            return

        # Execute copy
        result = self.manager.copy_from_usb(self.current_drive, program_numbers, auto_backup=True)

        # Show results
        if result['success']:
            msg = (
                f"Import complete!\n\n"
                f"Copied: {len(result['copied'])}\n"
                f"Backed up: {len(result['backed_up'])}\n"
                f"Errors: {len(result['errors'])}"
            )

            if result['errors']:
                msg += "\n\nErrors:\n" + "\n".join([f"- {e['program']}: {e['error']}" for e in result['errors'][:5]])

            messagebox.showinfo("Import Complete", msg)

            # Refresh display
            self._refresh_display()
        else:
            messagebox.showerror("Import Failed", f"Error: {result.get('error', 'Unknown error')}")

    # =============================================================
    # DIFF AND CONFLICT RESOLUTION
    # =============================================================

    def _view_diff(self, event=None):
        """View diff for selected file"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to view.")
            return

        # Get program number from first selected item
        values = self.tree.item(selected[0], 'values')
        program_number = values[0]

        # TODO: Implement diff viewer using GCodeDiffEngine
        messagebox.showinfo("View Diff", f"Diff viewer for {program_number}\n\n(To be implemented in Phase 4)")

    def _resolve_conflict(self):
        """Resolve conflict for selected file"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to resolve.")
            return

        # Get program number and sync status
        values = self.tree.item(selected[0], 'values')
        program_number = values[0]
        sync_status = values[1]

        # Verify it's actually a conflict or needs resolution
        if sync_status not in ['CONFLICT', 'USB_NEWER', 'REPO_NEWER']:
            messagebox.showinfo("No Conflict", f"{program_number} is already in sync.")
            return

        # Get current drive
        drive_label = self.drive_var.get()
        if not drive_label or drive_label == "Select Drive...":
            messagebox.showwarning("No Drive", "Please select a drive first.")
            return

        # Open conflict resolution dialog
        dialog = ConflictResolutionDialog(
            parent=self.window,
            manager=self.manager,
            drive_label=drive_label,
            program_number=program_number,
            sync_status=sync_status
        )

        # If resolution was successful, refresh the display
        if dialog.result:
            self.refresh_display()

    def _show_context_menu(self, event):
        """Show right-click context menu"""
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)


class DriveRegistrationDialog:
    """Dialog for registering a new USB drive"""

    def __init__(self, parent, manager: USBSyncManager):
        self.manager = manager
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Register USB Drive")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Drive label
        tk.Label(self.dialog, text="Drive Label:", font=('Segoe UI', 10)).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.label_entry = tk.Entry(self.dialog, width=30, font=('Segoe UI', 10))
        self.label_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        self.label_entry.insert(0, "CNC-MACHINE-A")

        # Drive path
        tk.Label(self.dialog, text="Drive Path:", font=('Segoe UI', 10)).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)

        path_frame = tk.Frame(self.dialog)
        path_frame.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        self.path_entry = tk.Entry(path_frame, width=30, font=('Segoe UI', 10))
        self.path_entry.pack(side=tk.LEFT)

        tk.Button(
            path_frame,
            text="Browse...",
            command=self._browse_path,
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT, padx=5)

        # Notes
        tk.Label(self.dialog, text="Notes:", font=('Segoe UI', 10)).grid(row=2, column=0, padx=10, pady=10, sticky=tk.NW)
        self.notes_text = tk.Text(self.dialog, width=30, height=4, font=('Segoe UI', 10))
        self.notes_text.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)

        tk.Button(
            button_frame,
            text="Register & Scan",
            command=self._register_and_scan,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Register Only",
            command=self._register_only,
            bg='#2196F3',
            fg='white',
            font=('Segoe UI', 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            font=('Segoe UI', 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        # Focus on label entry
        self.label_entry.focus()

    def _browse_path(self):
        """Browse for drive path"""
        path = filedialog.askdirectory(title="Select USB Drive Folder")
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def _register_and_scan(self):
        """Register drive and run scan"""
        if self._register():
            # TODO: Trigger scan after registration
            self.dialog.destroy()

    def _register_only(self):
        """Register drive without scanning"""
        if self._register():
            self.dialog.destroy()

    def _register(self) -> bool:
        """Register the drive"""
        drive_label = self.label_entry.get().strip()
        drive_path = self.path_entry.get().strip()
        notes = self.notes_text.get('1.0', tk.END).strip()

        # Validate
        if not drive_label:
            messagebox.showerror("Validation Error", "Please enter a drive label.")
            return False

        if not drive_path:
            messagebox.showerror("Validation Error", "Please enter a drive path.")
            return False

        if not os.path.exists(drive_path):
            confirm = messagebox.askyesno(
                "Path Not Found",
                f"The path does not exist:\n{drive_path}\n\nRegister anyway?"
            )
            if not confirm:
                return False

        # Register
        success = self.manager.register_drive(
            drive_label=drive_label,
            drive_path=drive_path,
            notes=notes
        )

        if success:
            self.result = {
                'drive_label': drive_label,
                'drive_path': drive_path,
                'notes': notes
            }
            return True
        else:
            messagebox.showerror("Registration Failed", "Failed to register drive.")
            return False


class ConflictResolutionDialog:
    """Dialog for resolving conflicts between repository and USB versions"""

    def __init__(self, parent, manager: USBSyncManager, drive_label: str, program_number: str, sync_status: str):
        """
        Initialize conflict resolution dialog.

        Args:
            parent: Parent window
            manager: USBSyncManager instance
            drive_label: Drive label
            program_number: Program number
            sync_status: Current sync status
        """
        self.manager = manager
        self.drive_label = drive_label
        self.program_number = program_number
        self.sync_status = sync_status
        self.result = None

        # Get file paths
        self.repo_file = self._get_repo_file_path()
        self.usb_file = self._get_usb_file_path()

        # Load file contents
        self.repo_content = self._load_file(self.repo_file) if self.repo_file else ""
        self.usb_content = self._load_file(self.usb_file) if self.usb_file else ""

        # Calculate hashes
        self.repo_hash = self.manager.calculate_file_hash(self.repo_file) if self.repo_file else None
        self.usb_hash = self.manager.calculate_file_hash(self.usb_file) if self.usb_file else None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Resolve Conflict: {program_number}")
        self.dialog.geometry("1400x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_ui()

    def _get_repo_file_path(self) -> Optional[str]:
        """Get repository file path"""
        import sqlite3
        conn = sqlite3.connect(self.manager.db_path, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM programs WHERE program_number = ?", (self.program_number,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result and os.path.exists(result[0]) else None

    def _get_usb_file_path(self) -> Optional[str]:
        """Get USB file path"""
        drive_path = self.manager.get_drive_path(self.drive_label)
        if not drive_path:
            return None
        usb_file = Path(drive_path) / f"{self.program_number.lower()}.nc"
        return str(usb_file) if usb_file.exists() else None

    def _load_file(self, file_path: str) -> str:
        """Load file content"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"ERROR: Failed to load file\n{str(e)}"

    def _create_ui(self):
        """Create the UI"""
        # Top info section
        info_frame = tk.Frame(self.dialog, bg='#2d2d30', pady=10)
        info_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(
            info_frame,
            text=f"Program: {self.program_number}  |  Status: {self.sync_status}",
            bg='#2d2d30',
            fg='#ffffff',
            font=('Segoe UI', 12, 'bold')
        ).pack()

        # Comparison frame
        compare_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        compare_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left side - Repository version
        left_frame = tk.Frame(compare_frame, bg='#1e1e1e')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Repository header
        repo_header = tk.Frame(left_frame, bg='#0e639c', pady=5)
        repo_header.pack(fill=tk.X)

        tk.Label(
            repo_header,
            text="📁 Repository Version",
            bg='#0e639c',
            fg='#ffffff',
            font=('Segoe UI', 10, 'bold')
        ).pack(side=tk.LEFT, padx=10)

        if self.repo_file:
            repo_mtime = datetime.fromtimestamp(os.path.getmtime(self.repo_file))
            tk.Label(
                repo_header,
                text=f"Modified: {repo_mtime.strftime('%Y-%m-%d %H:%M:%S')}",
                bg='#0e639c',
                fg='#ffffff',
                font=('Segoe UI', 9)
            ).pack(side=tk.LEFT, padx=10)

            if self.repo_hash:
                tk.Label(
                    repo_header,
                    text=f"Hash: {self.repo_hash[:12]}...",
                    bg='#0e639c',
                    fg='#cccccc',
                    font=('Consolas', 8)
                ).pack(side=tk.LEFT, padx=10)

        # Repository text widget
        self.repo_text = tk.Text(
            left_frame,
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='#ffffff',
            font=('Consolas', 9),
            wrap=tk.NONE
        )
        self.repo_text.pack(fill=tk.BOTH, expand=True)

        # Repository scrollbars
        repo_vscroll = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.repo_text.yview)
        repo_hscroll = tk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.repo_text.xview)
        self.repo_text.config(yscrollcommand=repo_vscroll.set, xscrollcommand=repo_hscroll.set)
        repo_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        repo_hscroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Right side - USB version
        right_frame = tk.Frame(compare_frame, bg='#1e1e1e')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # USB header
        usb_header = tk.Frame(right_frame, bg='#9c640e', pady=5)
        usb_header.pack(fill=tk.X)

        tk.Label(
            usb_header,
            text="💾 USB Version",
            bg='#9c640e',
            fg='#ffffff',
            font=('Segoe UI', 10, 'bold')
        ).pack(side=tk.LEFT, padx=10)

        if self.usb_file:
            usb_mtime = datetime.fromtimestamp(os.path.getmtime(self.usb_file))
            tk.Label(
                usb_header,
                text=f"Modified: {usb_mtime.strftime('%Y-%m-%d %H:%M:%S')}",
                bg='#9c640e',
                fg='#ffffff',
                font=('Segoe UI', 9)
            ).pack(side=tk.LEFT, padx=10)

            if self.usb_hash:
                tk.Label(
                    usb_header,
                    text=f"Hash: {self.usb_hash[:12]}...",
                    bg='#9c640e',
                    fg='#cccccc',
                    font=('Consolas', 8)
                ).pack(side=tk.LEFT, padx=10)

        # USB text widget
        self.usb_text = tk.Text(
            right_frame,
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='#ffffff',
            font=('Consolas', 9),
            wrap=tk.NONE
        )
        self.usb_text.pack(fill=tk.BOTH, expand=True)

        # USB scrollbars
        usb_vscroll = tk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.usb_text.yview)
        usb_hscroll = tk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.usb_text.xview)
        self.usb_text.config(yscrollcommand=usb_vscroll.set, xscrollcommand=usb_hscroll.set)
        usb_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        usb_hscroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Populate and highlight differences
        self._populate_diff()

        # Statistics frame
        stats_frame = tk.Frame(self.dialog, bg='#2d2d30', pady=5)
        stats_frame.pack(fill=tk.X, padx=10)

        stats = GCodeDiffEngine.get_diff_stats(self.repo_content, self.usb_content)
        stats_text = f"Changes: {stats['modified']} modified, {stats['added']} added, {stats['deleted']} deleted"

        tk.Label(
            stats_frame,
            text=stats_text,
            bg='#2d2d30',
            fg='#ffffff',
            font=('Segoe UI', 9)
        ).pack()

        # Decision frame
        decision_frame = tk.Frame(self.dialog, bg='#2d2d30', pady=10)
        decision_frame.pack(fill=tk.X, padx=10)

        tk.Label(
            decision_frame,
            text="Decision:",
            bg='#2d2d30',
            fg='#ffffff',
            font=('Segoe UI', 10, 'bold')
        ).pack(anchor=tk.W, padx=10)

        # Radio buttons for decision
        self.decision_var = tk.StringVar(value="keep_usb" if self.sync_status == "USB_NEWER" else "keep_repo")

        radio_frame = tk.Frame(decision_frame, bg='#2d2d30')
        radio_frame.pack(fill=tk.X, padx=20, pady=5)

        tk.Radiobutton(
            radio_frame,
            text="Keep Repository (archive USB version)",
            variable=self.decision_var,
            value="keep_repo",
            bg='#2d2d30',
            fg='#ffffff',
            selectcolor='#3e3e42',
            activebackground='#2d2d30',
            activeforeground='#ffffff',
            font=('Segoe UI', 9)
        ).pack(anchor=tk.W, pady=2)

        tk.Radiobutton(
            radio_frame,
            text="Keep USB (archive repository version)",
            variable=self.decision_var,
            value="keep_usb",
            bg='#2d2d30',
            fg='#ffffff',
            selectcolor='#3e3e42',
            activebackground='#2d2d30',
            activeforeground='#ffffff',
            font=('Segoe UI', 9)
        ).pack(anchor=tk.W, pady=2)

        # Archive checkbox
        self.archive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            decision_frame,
            text="Archive other version (recommended)",
            variable=self.archive_var,
            bg='#2d2d30',
            fg='#ffffff',
            selectcolor='#3e3e42',
            activebackground='#2d2d30',
            activeforeground='#ffffff',
            font=('Segoe UI', 9)
        ).pack(anchor=tk.W, padx=20, pady=5)

        # Notes
        tk.Label(
            decision_frame,
            text="Notes (optional):",
            bg='#2d2d30',
            fg='#ffffff',
            font=('Segoe UI', 9)
        ).pack(anchor=tk.W, padx=10, pady=(5, 2))

        self.notes_text = tk.Text(
            decision_frame,
            height=3,
            bg='#3e3e42',
            fg='#ffffff',
            insertbackground='#ffffff',
            font=('Segoe UI', 9)
        )
        self.notes_text.pack(fill=tk.X, padx=20, pady=2)

        # Buttons
        button_frame = tk.Frame(self.dialog, bg='#2d2d30', pady=10)
        button_frame.pack(fill=tk.X, padx=10)

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            bg='#3e3e42',
            fg='#ffffff',
            font=('Segoe UI', 10),
            width=12
        ).pack(side=tk.RIGHT, padx=5)

        tk.Button(
            button_frame,
            text="Resolve",
            command=self._execute_resolution,
            bg='#0e639c',
            fg='#ffffff',
            font=('Segoe UI', 10, 'bold'),
            width=12
        ).pack(side=tk.RIGHT, padx=5)

    def _populate_diff(self):
        """Populate text widgets with content and highlight differences"""
        # Insert content
        self.repo_text.insert('1.0', self.repo_content)
        self.usb_text.insert('1.0', self.usb_content)

        # Apply syntax highlighting
        try:
            GCodeDiffEngine.highlight_changes(
                self.repo_text,
                self.usb_text,
                self.repo_content,
                self.usb_content
            )
        except Exception as e:
            print(f"Error highlighting differences: {e}")

        # Make text widgets read-only
        self.repo_text.config(state=tk.DISABLED)
        self.usb_text.config(state=tk.DISABLED)

    def _execute_resolution(self):
        """Execute the resolution decision"""
        decision = self.decision_var.get()
        archive = self.archive_var.get()
        notes = self.notes_text.get('1.0', tk.END).strip()

        # Confirm action
        if decision == "keep_repo":
            action_text = "copy repository version to USB"
            if archive:
                action_text += " (USB version will be archived)"
        else:
            action_text = "copy USB version to repository"
            if archive:
                action_text += " (repository version will be archived)"

        confirm = messagebox.askyesno(
            "Confirm Resolution",
            f"Program: {self.program_number}\n\n"
            f"This will {action_text}.\n\n"
            f"Continue?"
        )

        if not confirm:
            return

        # Execute resolution
        try:
            if decision == "keep_repo":
                # Copy repository to USB (overwrite)
                result = self.manager.copy_to_usb(
                    drive_label=self.drive_label,
                    program_numbers=[self.program_number],
                    force=True  # Force overwrite
                )

                if result['errors']:
                    messagebox.showerror(
                        "Error",
                        f"Failed to copy to USB:\n{result['errors'][0]['error']}"
                    )
                    return
            else:
                # Copy USB to repository (with auto-backup)
                result = self.manager.copy_from_usb(
                    drive_label=self.drive_label,
                    program_numbers=[self.program_number],
                    auto_backup=archive
                )

                if result['errors']:
                    messagebox.showerror(
                        "Error",
                        f"Failed to copy from USB:\n{result['errors'][0]['error']}"
                    )
                    return

            # Success
            self.result = {
                'decision': decision,
                'archive': archive,
                'notes': notes
            }

            messagebox.showinfo(
                "Success",
                f"Conflict resolved for {self.program_number}\n\n"
                f"Action: {action_text}\n"
                f"Status: Files are now in sync"
            )

            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to resolve conflict:\n{str(e)}"
            )
