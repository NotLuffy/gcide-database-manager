"""
Archived & Deleted Files Browser

Modal dialog for viewing and restoring:
1. Soft-deleted programs (is_deleted=1 in database)
2. Archived file versions (from archive/ folder)

Features:
- Tabbed interface (Soft-Deleted vs Archives)
- Preview pane with syntax highlighting
- One-click restore with automatic backup
- Permanent delete with double confirmation
- Search/filter capability
- Dark theme matching main application

Author: Database Manager
Date: 2026-02-12
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
import re


class ArchivedFilesBrowser:
    """
    Browser for viewing and restoring archived and soft-deleted G-code programs.

    Provides dual-tab interface:
    - Tab 1: Soft-deleted programs (is_deleted=1 in database)
    - Tab 2: Archive files (versioned files in archive/ folder)

    Features:
    - Preview G-code content with syntax highlighting
    - Restore to repository with automatic backup
    - Permanent delete with confirmations
    - Search and filter
    """

    def __init__(self, parent, db_path, repository_path, on_restore_callback=None):
        """
        Initialize Archived Files Browser.

        Args:
            parent: Parent tkinter window
            db_path: Path to database file
            repository_path: Path to repository folder
            on_restore_callback: Function to call after restore (refreshes main window)
        """
        self.parent = parent
        self.db_path = db_path
        self.repository_path = repository_path
        self.on_restore_callback = on_restore_callback

        # Colors (dark theme)
        self.bg_color = '#1e1e1e'
        self.fg_color = '#d4d4d4'
        self.header_bg = '#2d2d30'
        self.input_bg = '#3c3c3c'

        # Create modal dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🗑 Archived & Deleted Files Browser")
        self.dialog.geometry("1400x900")
        self.dialog.configure(bg=self.bg_color)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Initialize UI components
        self.notebook = None
        self.deleted_tree = None
        self.archive_tree = None
        self.preview_text = None
        self.preview_header = None

        # Create UI
        self.create_ui()

        # Load data
        self.load_soft_deleted_programs()
        self.load_archive_files()

    def create_ui(self):
        """Create the main UI layout."""
        # Header
        header = tk.Frame(self.dialog, bg=self.header_bg, pady=10)
        header.pack(fill=tk.X)

        tk.Label(header,
                text="🗑 Archived & Deleted Files Browser",
                bg=self.header_bg, fg=self.fg_color,
                font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT, padx=20)

        tk.Label(header,
                text="View and restore soft-deleted programs and archived versions",
                bg=self.header_bg, fg='#888888',
                font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=10)

        # Create tabbed interface
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Soft-Deleted Programs
        deleted_tab = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(deleted_tab, text="  🗑 Soft-Deleted Programs  ")
        self.create_soft_deleted_tab(deleted_tab)

        # Tab 2: Archive Files
        archive_tab = tk.Frame(self.notebook, bg=self.bg_color)
        self.notebook.add(archive_tab, text="  📦 Archive Files  ")
        self.create_archive_tab(archive_tab)

        # Preview pane
        self.create_preview_pane()

        # Toolbar
        self.create_toolbar()

        # Bind selection events
        self.deleted_tree.bind('<<TreeviewSelect>>', lambda e: self.preview_selected())
        self.archive_tree.bind('<<TreeviewSelect>>', lambda e: self.preview_selected())

    def create_soft_deleted_tab(self, parent):
        """Create the Soft-Deleted Programs tab."""
        # Search frame
        search_frame = tk.Frame(parent, bg=self.bg_color)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Search:",
                bg=self.bg_color, fg=self.fg_color,
                font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)

        self.deleted_search = tk.Entry(search_frame, bg=self.input_bg, fg=self.fg_color,
                                       insertbackground='#ffffff', font=('Segoe UI', 9))
        self.deleted_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.deleted_search.bind('<KeyRelease>', lambda e: self.filter_soft_deleted())

        tk.Button(search_frame, text="Clear", command=lambda: self.clear_filter('deleted'),
                 bg='#6c757d', fg='#ffffff', font=('Segoe UI', 9),
                 padx=10, pady=2).pack(side=tk.LEFT, padx=5)

        # Treeview frame
        tree_frame = tk.Frame(parent, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        v_scroll = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview
        columns = ("Program", "Title", "Deleted Date", "File Path")
        self.deleted_tree = ttk.Treeview(tree_frame,
            columns=columns,
            show='headings',
            selectmode='browse',
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            height=12)

        self.deleted_tree.heading('Program', text='Program Number')
        self.deleted_tree.heading('Title', text='Title')
        self.deleted_tree.heading('Deleted Date', text='Deleted Date')
        self.deleted_tree.heading('File Path', text='File Path')

        self.deleted_tree.column('Program', width=120)
        self.deleted_tree.column('Title', width=300)
        self.deleted_tree.column('Deleted Date', width=180)
        self.deleted_tree.column('File Path', width=500)

        self.deleted_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scroll.config(command=self.deleted_tree.yview)
        h_scroll.config(command=self.deleted_tree.xview)

        # Color coding
        self.deleted_tree.tag_configure('recent', background='#FFF9C4')  # Yellow - <7 days
        self.deleted_tree.tag_configure('old', background='#424242')     # Gray - >30 days

    def create_archive_tab(self, parent):
        """Create the Archive Files tab."""
        # Search frame
        search_frame = tk.Frame(parent, bg=self.bg_color)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Search:",
                bg=self.bg_color, fg=self.fg_color,
                font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)

        self.archive_search = tk.Entry(search_frame, bg=self.input_bg, fg=self.fg_color,
                                       insertbackground='#ffffff', font=('Segoe UI', 9))
        self.archive_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.archive_search.bind('<KeyRelease>', lambda e: self.filter_archives())

        tk.Button(search_frame, text="Clear", command=lambda: self.clear_filter('archive'),
                 bg='#6c757d', fg='#ffffff', font=('Segoe UI', 9),
                 padx=10, pady=2).pack(side=tk.LEFT, padx=5)

        # Treeview frame
        tree_frame = tk.Frame(parent, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        v_scroll = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview
        columns = ("Version", "Date", "Size", "Path")
        self.archive_tree = ttk.Treeview(tree_frame,
            columns=columns,
            show='tree headings',
            selectmode='browse',
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            height=12)

        self.archive_tree.heading('#0', text='Program')
        self.archive_tree.heading('Version', text='Ver')
        self.archive_tree.heading('Date', text='Archive Date')
        self.archive_tree.heading('Size', text='Size')
        self.archive_tree.heading('Path', text='File Path')

        self.archive_tree.column('#0', width=120)
        self.archive_tree.column('Version', width=60)
        self.archive_tree.column('Date', width=180)
        self.archive_tree.column('Size', width=100)
        self.archive_tree.column('Path', width=500)

        self.archive_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scroll.config(command=self.archive_tree.yview)
        h_scroll.config(command=self.archive_tree.xview)

        # Color coding
        self.archive_tree.tag_configure('compressed', foreground='#4EC9B0')  # Teal
        self.archive_tree.tag_configure('v1', background='#2d4a2d')          # Dark green

    def create_preview_pane(self):
        """Create the preview pane for G-code content."""
        preview_container = tk.Frame(self.dialog, bg=self.bg_color)
        preview_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Header
        header = tk.Frame(preview_container, bg=self.header_bg, pady=5)
        header.pack(fill=tk.X)

        self.preview_header = tk.Label(header,
            text="Select a file to preview",
            bg=self.header_bg, fg=self.fg_color,
            font=('Segoe UI', 10))
        self.preview_header.pack(side=tk.LEFT, padx=10)

        # Text frame
        text_frame = tk.Frame(preview_container, bg=self.bg_color)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        v_scroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Text widget
        self.preview_text = tk.Text(text_frame,
            bg=self.bg_color, fg=self.fg_color,
            font=('Consolas', 9),
            wrap=tk.NONE,
            height=10,
            state=tk.DISABLED,
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set)

        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scroll.config(command=self.preview_text.yview)
        h_scroll.config(command=self.preview_text.xview)

        # Syntax highlighting tags
        self.preview_text.tag_config('gcode', foreground='#4FC1FF')      # Blue
        self.preview_text.tag_config('mcode', foreground='#C586C0')      # Purple
        self.preview_text.tag_config('comment', foreground='#6A9955')    # Green
        self.preview_text.tag_config('program', foreground='#CE9178')    # Orange

    def create_toolbar(self):
        """Create the button toolbar."""
        toolbar = tk.Frame(self.dialog, bg=self.header_bg, pady=10)
        toolbar.pack(fill=tk.X, padx=10)

        # Left side - action buttons
        tk.Button(toolbar, text="↩ Restore Selected",
            command=self.restore_selected,
            bg='#28a745', fg='#ffffff',
            font=('Segoe UI', 10, 'bold'),
            padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="🗑 Permanent Delete",
            command=self.permanent_delete,
            bg='#dc3545', fg='#ffffff',
            font=('Segoe UI', 10),
            padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="🔄 Refresh",
            command=self.refresh_all,
            bg='#4a90e2', fg='#ffffff',
            font=('Segoe UI', 10),
            padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        # Right side - close
        tk.Button(toolbar, text="Close",
            command=self.dialog.destroy,
            bg='#6c757d', fg='#ffffff',
            font=('Segoe UI', 10),
            padx=15, pady=5).pack(side=tk.RIGHT, padx=5)

    def load_soft_deleted_programs(self):
        """Load soft-deleted programs from database."""
        # Clear existing items
        for item in self.deleted_tree.get_children():
            self.deleted_tree.delete(item)

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT program_number, title, deleted_date, file_path,
                       outer_diameter, thickness, center_bore
                FROM programs
                WHERE is_deleted = 1
                ORDER BY deleted_date DESC
            """)

            results = cursor.fetchall()
            conn.close()

            if not results:
                # Show "no data" message
                self.deleted_tree.insert('', tk.END,
                    values=("No soft-deleted programs found", "", "", ""),
                    tags=('empty',))
                self.deleted_tree.tag_configure('empty', foreground='#888888')
                return

            # Add results to tree
            now = datetime.now()
            for row in results:
                program_num, title, deleted_date, file_path, od, thick, cb = row

                # Determine age tag
                tag = ''
                if deleted_date:
                    try:
                        deleted_dt = datetime.fromisoformat(deleted_date)
                        age_days = (now - deleted_dt).days
                        if age_days < 7:
                            tag = 'recent'
                        elif age_days > 30:
                            tag = 'old'
                    except:
                        pass

                # Format deleted date
                display_date = deleted_date[:19] if deleted_date else "Unknown"

                self.deleted_tree.insert('', tk.END,
                    values=(program_num, title or "No title", display_date, file_path or "No path"),
                    tags=(tag,) if tag else ())

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load soft-deleted programs:\n{str(e)}")

    def load_archive_files(self):
        """Load archive files from archive_metadata table."""
        # Clear existing items
        for item in self.archive_tree.get_children():
            self.archive_tree.delete(item)

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT program_number, version_number, date_archived,
                       file_size, file_path, file_hash, is_compressed,
                       outer_diameter, thickness, center_bore
                FROM archive_metadata
                ORDER BY program_number, version_number DESC
            """)

            results = cursor.fetchall()
            conn.close()

            if not results:
                # Show "no data" message
                self.archive_tree.insert('', tk.END, text="No archive files found",
                    values=("", "", "", ""),
                    tags=('empty',))
                self.archive_tree.tag_configure('empty', foreground='#888888')
                return

            # Group by program number
            programs = {}
            for row in results:
                prog_num, version, date_arch, size, path, hash_val, compressed, od, thick, cb = row
                if prog_num not in programs:
                    programs[prog_num] = []
                programs[prog_num].append(row)

            # Add to tree (program as parent, versions as children)
            for prog_num in sorted(programs.keys()):
                versions = programs[prog_num]

                # Parent node (program number)
                parent_id = self.archive_tree.insert('', tk.END,
                    text=prog_num,
                    values=("", f"{len(versions)} versions", "", ""),
                    open=False)

                # Child nodes (each version)
                for row in versions:
                    prog_num, version, date_arch, size, path, hash_val, compressed, od, thick, cb = row

                    # Format size
                    if size:
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = "Unknown"

                    # Format date
                    display_date = date_arch[:19] if date_arch else "Unknown"

                    # Determine tags
                    tags = []
                    if compressed:
                        tags.append('compressed')
                    if version == 1:
                        tags.append('v1')

                    self.archive_tree.insert(parent_id, tk.END,
                        text="",
                        values=(f"v{version}", display_date, size_str, path or "Unknown"),
                        tags=tuple(tags) if tags else ())

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load archive files:\n{str(e)}")

    def preview_selected(self):
        """Preview the selected file's G-code content."""
        active_tab = self.notebook.index(self.notebook.select())

        try:
            if active_tab == 0:  # Soft-Deleted tab
                selected = self.deleted_tree.selection()
                if not selected:
                    return

                item = self.deleted_tree.item(selected[0])
                values = item['values']

                if len(values) < 4 or values[0] == "No soft-deleted programs found":
                    return

                program_num = values[0]
                title = values[1]
                file_path = values[3]

                if not file_path or file_path == "No path":
                    self.preview_header.config(text=f"{program_num}: No file path")
                    self.clear_preview()
                    return

                if not os.path.exists(file_path):
                    self.preview_header.config(text=f"{program_num}: File not found")
                    self.clear_preview()
                    return

                # Read and display file
                self.preview_header.config(text=f"{program_num} - {title}")
                self.display_file_content(file_path)

            elif active_tab == 1:  # Archive tab
                selected = self.archive_tree.selection()
                if not selected:
                    return

                item = self.archive_tree.item(selected[0])

                # Check if parent or child selected
                if not item['values'] or item['values'][0] == "":
                    # Parent selected, get first child
                    children = self.archive_tree.get_children(selected[0])
                    if not children:
                        return
                    selected_item = self.archive_tree.item(children[0])
                    program_num = item['text']
                else:
                    # Child selected
                    parent = self.archive_tree.parent(selected[0])
                    program_num = self.archive_tree.item(parent)['text'] if parent else item['text']
                    selected_item = item

                values = selected_item['values']
                if len(values) < 4:
                    return

                version = values[0]
                file_path = values[3]

                if not file_path or file_path == "Unknown":
                    self.preview_header.config(text=f"{program_num} {version}: No file path")
                    self.clear_preview()
                    return

                # Handle compressed files
                if file_path.endswith('.gz'):
                    self.preview_compressed_file(program_num, version, file_path)
                else:
                    self.preview_header.config(text=f"{program_num} {version}")
                    self.display_file_content(file_path)

        except Exception as e:
            messagebox.showerror("Preview Error", f"Failed to preview file:\n{str(e)}")

    def display_file_content(self, file_path, max_lines=500):
        """Display file content with syntax highlighting."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[:max_lines]

            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete('1.0', tk.END)

            for line in lines:
                start_idx = self.preview_text.index(tk.INSERT)
                self.preview_text.insert(tk.END, line)

                # Apply syntax highlighting
                if re.match(r'^\s*\(', line):
                    # Comment
                    self.preview_text.tag_add('comment', start_idx, self.preview_text.index(tk.INSERT))
                elif re.search(r'\bO\d+', line, re.IGNORECASE):
                    # Program number
                    self.preview_text.tag_add('program', start_idx, self.preview_text.index(tk.INSERT))
                elif re.search(r'\bG\d+', line, re.IGNORECASE):
                    # G-code
                    self.preview_text.tag_add('gcode', start_idx, self.preview_text.index(tk.INSERT))
                elif re.search(r'\bM\d+', line, re.IGNORECASE):
                    # M-code
                    self.preview_text.tag_add('mcode', start_idx, self.preview_text.index(tk.INSERT))

            if len(lines) == max_lines:
                self.preview_text.insert(tk.END, f"\n... (showing first {max_lines} lines)")

            self.preview_text.config(state=tk.DISABLED)

        except Exception as e:
            self.preview_header.config(text=f"Error reading file: {str(e)}")
            self.clear_preview()

    def preview_compressed_file(self, program_num, version, file_path):
        """Preview a compressed (.gz) archive file."""
        try:
            from archive_cleanup_manager import ArchiveCleanupManager

            cleanup_mgr = ArchiveCleanupManager(self.db_path, os.path.dirname(self.repository_path))
            temp_path = cleanup_mgr.decompress_for_viewing(file_path)

            self.preview_header.config(text=f"{program_num} {version} (compressed)")
            self.display_file_content(temp_path)

            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

        except Exception as e:
            self.preview_header.config(text=f"Error decompressing: {str(e)}")
            self.clear_preview()

    def clear_preview(self):
        """Clear the preview pane."""
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.config(state=tk.DISABLED)

    def restore_selected(self):
        """Restore the selected program."""
        active_tab = self.notebook.index(self.notebook.select())

        if active_tab == 0:
            self._restore_soft_deleted()
        elif active_tab == 1:
            self._restore_from_archive()

    def _restore_soft_deleted(self):
        """Restore a soft-deleted program."""
        selected = self.deleted_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a soft-deleted program to restore")
            return

        item = self.deleted_tree.item(selected[0])
        values = item['values']

        if len(values) < 4 or values[0] == "No soft-deleted programs found":
            return

        program_num = values[0]
        file_path = values[3]

        # Confirm restoration
        if not messagebox.askyesno("Confirm Restore",
            f"Restore {program_num} to active programs?\n\n"
            f"This will mark it as active (is_deleted=0)."):
            return

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            # Update database
            cursor.execute("""
                UPDATE programs
                SET is_deleted = 0, deleted_date = NULL
                WHERE program_number = ?
            """, (program_num,))

            conn.commit()
            conn.close()

            messagebox.showinfo("Success",
                f"Restored {program_num} successfully!\n"
                f"Program is now active in main window.")

            # Refresh views
            if self.on_restore_callback:
                self.on_restore_callback()
            self.refresh_all()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore program:\n{str(e)}")

    def _restore_from_archive(self):
        """Restore from an archive version."""
        selected = self.archive_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an archive version to restore")
            return

        item = self.archive_tree.item(selected[0])

        # Get program number and archive path
        if not item['values'] or item['values'][0] == "":
            # Parent selected
            messagebox.showinfo("Selection", "Please select a specific version to restore, not the program folder")
            return

        parent = self.archive_tree.parent(selected[0])
        program_num = self.archive_tree.item(parent)['text'] if parent else item['text']

        values = item['values']
        version = values[0]
        archive_path = values[3]

        if not archive_path or archive_path == "Unknown":
            messagebox.showerror("Error", "Archive file path not found")
            return

        # Confirm
        if not messagebox.askyesno("Confirm Restore",
            f"Restore {program_num} {version}?\n\n"
            f"Current version will be archived first.\n"
            f"Archive: {archive_path}"):
            return

        try:
            from repository_manager import RepositoryManager
            repo_mgr = RepositoryManager(self.db_path, self.repository_path)

            # Restore (auto-archives current version)
            result = repo_mgr.restore_from_archive(archive_path, program_num, replace_current=True)

            if result:
                messagebox.showinfo("Success",
                    f"Restored {program_num} {version} successfully!\n"
                    f"Previous version archived as backup.")

                # Refresh views
                if self.on_restore_callback:
                    self.on_restore_callback()
                self.refresh_all()
            else:
                messagebox.showerror("Error", "Failed to restore archive")

        except Exception as e:
            messagebox.showerror("Error", f"Restore failed:\n{str(e)}")

    def permanent_delete(self):
        """Permanently delete a soft-deleted program."""
        active_tab = self.notebook.index(self.notebook.select())

        if active_tab != 0:
            messagebox.showinfo("Info", "Permanent delete is only available for soft-deleted programs")
            return

        selected = self.deleted_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a program to permanently delete")
            return

        item = self.deleted_tree.item(selected[0])
        values = item['values']

        if len(values) < 4 or values[0] == "No soft-deleted programs found":
            return

        program_num = values[0]
        file_path = values[3]

        # First confirmation: Archive first?
        archive_first = messagebox.askyesnocancel("Archive First?",
            f"Permanently delete {program_num}?\n\n"
            f"This will remove the program from the database completely.\n"
            f"Do you want to archive the file first?")

        if archive_first is None:  # Cancel
            return

        # Second confirmation
        if not messagebox.askyesno("Confirm Permanent Delete",
            f"Are you ABSOLUTELY SURE?\n\n"
            f"This will permanently delete {program_num} from the database.\n"
            f"This action CANNOT be undone!"):
            return

        try:
            # Archive if requested and file exists
            if archive_first and file_path and file_path != "No path" and os.path.exists(file_path):
                from repository_manager import RepositoryManager
                repo_mgr = RepositoryManager(self.db_path, self.repository_path)
                repo_mgr.archive_old_file(file_path, program_num, reason='permanent_delete')

            # Delete from database
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM programs WHERE program_number = ?", (program_num,))

            conn.commit()
            conn.close()

            messagebox.showinfo("Deleted",
                f"Permanently deleted {program_num} from database.\n"
                + ("File was archived before deletion." if archive_first else ""))

            # Refresh
            self.refresh_all()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete program:\n{str(e)}")

    def filter_soft_deleted(self):
        """Filter soft-deleted programs based on search text."""
        search_text = self.deleted_search.get().lower()

        for item in self.deleted_tree.get_children():
            values = self.deleted_tree.item(item)['values']
            if len(values) < 4:
                continue

            # Search in program number, title, and date
            if (search_text in str(values[0]).lower() or
                search_text in str(values[1]).lower() or
                search_text in str(values[2]).lower()):
                self.deleted_tree.reattach(item, '', tk.END)
            else:
                self.deleted_tree.detach(item)

    def filter_archives(self):
        """Filter archive files based on search text."""
        search_text = self.archive_search.get().lower()

        for parent in self.archive_tree.get_children():
            parent_text = self.archive_tree.item(parent)['text'].lower()
            match_found = search_text in parent_text

            # Check children
            for child in self.archive_tree.get_children(parent):
                values = self.archive_tree.item(child)['values']
                if (search_text in str(values[0]).lower() or
                    search_text in str(values[1]).lower() or
                    search_text in str(values[3]).lower()):
                    match_found = True

            if match_found:
                self.archive_tree.reattach(parent, '', tk.END)
            else:
                self.archive_tree.detach(parent)

    def clear_filter(self, tab_type):
        """Clear search filter."""
        if tab_type == 'deleted':
            self.deleted_search.delete(0, tk.END)
            # Reattach all items
            for item in self.deleted_tree.get_children():
                self.deleted_tree.reattach(item, '', tk.END)
        elif tab_type == 'archive':
            self.archive_search.delete(0, tk.END)
            # Reattach all items
            for item in self.archive_tree.get_children():
                self.archive_tree.reattach(item, '', tk.END)

    def refresh_all(self):
        """Refresh both tabs."""
        self.load_soft_deleted_programs()
        self.load_archive_files()
        self.clear_preview()
        self.preview_header.config(text="Select a file to preview")
