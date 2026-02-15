"""
Archive Management GUI
Provides interface for repository cleanup, archive browsing, and file management
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from pathlib import Path
from repository_manager import RepositoryManager


class ArchiveManagerGUI:
    """GUI for managing repository archives and cleanup"""

    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        self.repo_manager = RepositoryManager(
            db_manager.db_path,
            db_manager.repository_path
        )

        # Create main frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Build GUI
        self.build_gui()
        self.refresh_stats()

    def build_gui(self):
        """Build the archive management GUI"""

        # Title
        title_label = tk.Label(self.frame, text="📦 Repository & Archive Management",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))

        # Statistics Frame
        stats_frame = ttk.LabelFrame(self.frame, text="Repository Statistics", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.stats_text = tk.Text(stats_frame, height=6, width=80, bg="#f0f0f0",
                                 font=("Courier", 9))
        self.stats_text.pack(fill=tk.X)

        # Refresh button
        ttk.Button(stats_frame, text="🔄 Refresh Stats",
                  command=self.refresh_stats).pack(pady=(5, 0))

        # Operations Frame
        ops_frame = ttk.LabelFrame(self.frame, text="Cleanup Operations", padding=10)
        ops_frame.pack(fill=tk.X, pady=(0, 10))

        # Grid for operation buttons
        row = 0

        # Orphan Cleanup
        ttk.Label(ops_frame, text="🗑️ Orphan Files:",
                 font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(ops_frame, text="Files in repository not tracked in database").grid(
            row=row, column=1, sticky=tk.W, padx=(10, 0))

        row += 1
        ttk.Button(ops_frame, text="Detect Orphans (Dry Run)",
                  command=lambda: self.run_cleanup('orphan', 'detect')).grid(
            row=row, column=0, padx=5, pady=2, sticky=tk.EW)
        ttk.Button(ops_frame, text="Archive Orphans",
                  command=lambda: self.run_cleanup('orphan', 'archive')).grid(
            row=row, column=1, padx=5, pady=2, sticky=tk.EW)

        row += 1
        ttk.Separator(ops_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)

        # Duplicate Consolidation
        row += 1
        ttk.Label(ops_frame, text="📋 Duplicate Files:",
                 font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(ops_frame, text="Multiple files for same program number").grid(
            row=row, column=1, sticky=tk.W, padx=(10, 0))

        row += 1
        ttk.Button(ops_frame, text="Detect Duplicates (Dry Run)",
                  command=lambda: self.run_cleanup('duplicate', 'detect')).grid(
            row=row, column=0, padx=5, pady=2, sticky=tk.EW)
        ttk.Button(ops_frame, text="Consolidate Duplicates",
                  command=lambda: self.run_cleanup('duplicate', 'consolidate')).grid(
            row=row, column=1, padx=5, pady=2, sticky=tk.EW)

        row += 1
        ttk.Separator(ops_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)

        # Archive Cleanup
        row += 1
        ttk.Label(ops_frame, text="🗄️ Old Archives:",
                 font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(ops_frame, text="Delete archived files older than 180 days").grid(
            row=row, column=1, sticky=tk.W, padx=(10, 0))

        row += 1
        ttk.Button(ops_frame, text="Check Old Archives (Dry Run)",
                  command=lambda: self.run_cleanup('archive', 'detect')).grid(
            row=row, column=0, padx=5, pady=2, sticky=tk.EW)
        ttk.Button(ops_frame, text="Delete Old Archives",
                  command=lambda: self.run_cleanup('archive', 'delete')).grid(
            row=row, column=1, padx=5, pady=2, sticky=tk.EW)

        # Configure grid weights
        ops_frame.columnconfigure(0, weight=1)
        ops_frame.columnconfigure(1, weight=1)

        # Output Frame
        output_frame = ttk.LabelFrame(self.frame, text="Operation Output", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, width=80,
                                                     font=("Courier", 9))
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Archive Browser Frame
        browser_frame = ttk.LabelFrame(self.frame, text="Archive Browser", padding=10)
        browser_frame.pack(fill=tk.BOTH, expand=True)

        # Search box
        search_row = ttk.Frame(browser_frame)
        search_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_row, text="Program Number:").pack(side=tk.LEFT, padx=(0, 5))
        self.program_search_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.program_search_var, width=20).pack(
            side=tk.LEFT, padx=(0, 5))
        ttk.Button(search_row, text="🔍 Search Archives",
                  command=self.search_archives).pack(side=tk.LEFT)

        # Archive list
        self.archive_tree = ttk.Treeview(browser_frame,
                                        columns=("Version", "Date", "Size", "Path"),
                                        show="tree headings", height=8)
        self.archive_tree.heading("#0", text="Program")
        self.archive_tree.heading("Version", text="Version")
        self.archive_tree.heading("Date", text="Archive Date")
        self.archive_tree.heading("Size", text="Size")
        self.archive_tree.heading("Path", text="Path")

        self.archive_tree.column("#0", width=100)
        self.archive_tree.column("Version", width=70)
        self.archive_tree.column("Date", width=100)
        self.archive_tree.column("Size", width=80)
        self.archive_tree.column("Path", width=400)

        self.archive_tree.pack(fill=tk.BOTH, expand=True)

        # Restore button
        ttk.Button(browser_frame, text="📥 Restore Selected Archive",
                  command=self.restore_archive).pack(pady=(5, 0))

    def refresh_stats(self):
        """Refresh repository statistics"""
        self.stats_text.delete(1.0, tk.END)

        try:
            # Repository stats
            orphans = self.repo_manager.detect_orphan_files()
            duplicates = self.repo_manager.detect_duplicates()

            repo_files = sum(1 for f in Path(self.repo_manager.repository_path).iterdir()
                           if f.is_file())

            # Archive stats
            archive_stats = self.repo_manager.get_archive_stats()

            # Database stats
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM programs")
            db_count = cursor.fetchone()[0]
            conn.close()

            stats = f"""Repository:
  Files in repository:        {repo_files:,}
  Programs in database:       {db_count:,}
  Orphan files (untracked):   {len(orphans):,}
  Programs with duplicates:   {len(duplicates):,}

Archive:
  Total archived files:       {archive_stats['total_files']:,}
  Total archive size:         {archive_stats['total_size_mb']} MB
  Archive date folders:       {archive_stats['date_folders']}
"""

            self.stats_text.insert(1.0, stats)
            self.stats_text.config(state=tk.DISABLED)

        except Exception as e:
            self.stats_text.insert(1.0, f"Error loading stats: {e}")

    def run_cleanup(self, operation_type, action):
        """
        Run cleanup operation in background thread.

        operation_type: 'orphan', 'duplicate', 'archive'
        action: 'detect', 'archive', 'consolidate', 'delete'
        """
        # Confirm destructive operations
        if action in ['archive', 'consolidate', 'delete']:
            if operation_type == 'orphan':
                message = f"Archive {len(self.repo_manager.detect_orphan_files())} orphan files?"
            elif operation_type == 'duplicate':
                message = f"Consolidate {len(self.repo_manager.detect_duplicates())} programs with duplicates?"
            elif operation_type == 'archive':
                message = "Delete archived files older than 180 days?"

            if not messagebox.askyesno("Confirm Operation", message + "\n\nThis cannot be undone."):
                return

        # Clear output
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Starting {operation_type} {action}...\n\n")

        # Run in thread
        thread = threading.Thread(target=self._run_cleanup_thread,
                                 args=(operation_type, action))
        thread.daemon = True
        thread.start()

    def _run_cleanup_thread(self, operation_type, action):
        """Background thread for cleanup operations"""
        try:
            if operation_type == 'orphan':
                if action == 'detect':
                    orphans = self.repo_manager.detect_orphan_files()
                    self._append_output(f"Found {len(orphans)} orphan files:\n")
                    for filename, path in orphans[:50]:
                        self._append_output(f"  - {filename}\n")
                    if len(orphans) > 50:
                        self._append_output(f"  ... and {len(orphans) - 50} more\n")

                elif action == 'archive':
                    result = self.repo_manager.cleanup_orphans(action='archive', dry_run=False)
                    self._append_output(f"\nArchived {result['count']} orphan files\n")
                    if result.get('errors', 0) > 0:
                        self._append_output(f"Errors: {result['errors']}\n")

            elif operation_type == 'duplicate':
                if action == 'detect':
                    duplicates = self.repo_manager.detect_duplicates()
                    self._append_output(f"Found {len(duplicates)} programs with multiple files:\n")
                    for prog_num, files in list(duplicates.items())[:50]:
                        self._append_output(f"  {prog_num}: {len(files)} files\n")
                        for f in files:
                            self._append_output(f"    - {Path(f).name}\n")
                    if len(duplicates) > 50:
                        self._append_output(f"  ... and {len(duplicates) - 50} more\n")

                elif action == 'consolidate':
                    result = self.repo_manager.consolidate_duplicates(dry_run=False)
                    self._append_output(f"\nConsolidated {result['count']} programs\n")
                    if result.get('errors', 0) > 0:
                        self._append_output(f"Errors: {result['errors']}\n")

            elif operation_type == 'archive':
                if action == 'detect':
                    result = self.repo_manager.delete_old_archives(days=180, dry_run=True)
                    self._append_output(f"Would delete {result['count']} files ({result['size_mb']} MB)\n")

                elif action == 'delete':
                    result = self.repo_manager.delete_old_archives(days=180, dry_run=False)
                    self._append_output(f"\nDeleted {result['count']} archived files ({result['size_mb']} MB)\n")

            self._append_output("\n✅ Operation complete!\n")

            # Refresh stats
            self.parent.after(100, self.refresh_stats)

        except Exception as e:
            self._append_output(f"\n❌ Error: {e}\n")
            import traceback
            self._append_output(traceback.format_exc())

    def _append_output(self, text):
        """Thread-safe append to output text"""
        self.parent.after(0, lambda: self.output_text.insert(tk.END, text))
        self.parent.after(0, lambda: self.output_text.see(tk.END))

    def search_archives(self):
        """Search for archived versions of a program"""
        program_number = self.program_search_var.get().strip().lower()

        if not program_number:
            messagebox.showwarning("Input Required", "Please enter a program number")
            return

        # Clear tree
        for item in self.archive_tree.get_children():
            self.archive_tree.delete(item)

        # Search archives
        versions = self.repo_manager.list_archived_versions(program_number)

        if not versions:
            self.archive_tree.insert("", tk.END, text=f"{program_number}: No archived versions found")
            return

        # Add to tree
        for version, date, filepath, size in versions:
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.2f} MB"

            self.archive_tree.insert("", tk.END,
                                    text=program_number,
                                    values=(f"v{version}", date, size_str, filepath))

    def restore_archive(self):
        """Restore selected archive file"""
        selected = self.archive_tree.selection()

        if not selected:
            messagebox.showwarning("No Selection", "Please select an archive to restore")
            return

        item = self.archive_tree.item(selected[0])
        program_number = item['text']
        filepath = item['values'][3]

        # Confirm
        if not messagebox.askyesno("Confirm Restore",
                                   f"Restore {program_number} from archive?\n\n"
                                   f"This will archive the current version and restore:\n{filepath}\n\n"
                                   f"Continue?"):
            return

        try:
            # Restore with replacement
            result = self.repo_manager.restore_from_archive(filepath, program_number,
                                                           replace_current=True)

            if result:
                messagebox.showinfo("Success", f"Restored {program_number} successfully!\n\n{result}")
                self.refresh_stats()
            else:
                messagebox.showerror("Error", "Failed to restore archive")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore archive:\n{e}")


def add_archive_tab_to_notebook(notebook, db_manager):
    """Add archive management tab to existing notebook"""
    archive_tab = ttk.Frame(notebook)
    notebook.add(archive_tab, text="📦 Archive")

    # Create archive GUI
    ArchiveManagerGUI(archive_tab, db_manager)

    return archive_tab


if __name__ == '__main__':
    # Test GUI standalone
    root = tk.Tk()
    root.title("Archive Manager")
    root.geometry("900x800")

    # Mock db_manager for testing
    class MockDBManager:
        db_path = "gcode_database.db"
        repository_path = "repository"

    manager = MockDBManager()
    gui = ArchiveManagerGUI(root, manager)

    root.mainloop()
