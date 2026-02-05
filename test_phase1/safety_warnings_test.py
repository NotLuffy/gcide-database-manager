"""
Phase 1.3 Test - Safety Warnings Before Writes
Isolated test environment for database safety features

This module tests the safety warning system that prevents
data conflicts and loss before database writes.
"""

import sys
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import shutil
import json
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class DatabaseSafetyChecker:
    """
    Safety checker for database operations
    Tracks modifications, detects conflicts, creates backups
    """

    def __init__(self, db_path):
        """
        Initialize safety checker

        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
        self.metadata_file = db_path + '.metadata.json'
        self.backup_dir = os.path.join(os.path.dirname(db_path), 'safety_backups')

        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)

        # Load or initialize metadata
        self.metadata = self.load_metadata()

    def load_metadata(self):
        """Load metadata about last database access"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {
            'last_accessed_by': None,
            'last_accessed_time': None,
            'last_modified_by': None,
            'last_modified_time': None,
            'computer_name': None,
            'access_count': 0,
            'write_count': 0
        }

    def save_metadata(self):
        """Save metadata to file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Failed to save metadata: {e}")

    def record_access(self, computer_name=None):
        """Record database access"""
        if computer_name is None:
            computer_name = os.environ.get('COMPUTERNAME', 'Unknown')

        self.metadata['last_accessed_by'] = computer_name
        self.metadata['last_accessed_time'] = datetime.now().isoformat()
        self.metadata['access_count'] = self.metadata.get('access_count', 0) + 1
        self.save_metadata()

    def record_write(self, computer_name=None):
        """Record database write"""
        if computer_name is None:
            computer_name = os.environ.get('COMPUTERNAME', 'Unknown')

        self.metadata['last_modified_by'] = computer_name
        self.metadata['last_modified_time'] = datetime.now().isoformat()
        self.metadata['computer_name'] = computer_name
        self.metadata['write_count'] = self.metadata.get('write_count', 0) + 1
        self.save_metadata()

    def check_for_conflicts(self):
        """
        Check if database has been modified since last access

        Returns:
            dict with keys:
                - conflict_detected: bool
                - last_modified_by: str
                - last_modified_time: str
                - file_modified_time: str
                - warning_level: str (none, low, medium, high)
        """
        result = {
            'conflict_detected': False,
            'last_modified_by': self.metadata.get('last_modified_by'),
            'last_modified_time': self.metadata.get('last_modified_time'),
            'file_modified_time': None,
            'warning_level': 'none',
            'message': None
        }

        if not os.path.exists(self.db_path):
            result['warning_level'] = 'high'
            result['message'] = 'Database file not found'
            return result

        # Get actual file modification time
        try:
            stat = os.stat(self.db_path)
            file_mtime = datetime.fromtimestamp(stat.st_mtime)
            result['file_modified_time'] = file_mtime.isoformat()

            # Check if modified by someone else
            last_access = self.metadata.get('last_accessed_time')
            if last_access:
                last_access_dt = datetime.fromisoformat(last_access)

                # If file was modified after our last access
                if file_mtime > last_access_dt:
                    result['conflict_detected'] = True

                    # Check if it was us or someone else
                    current_computer = os.environ.get('COMPUTERNAME', 'Unknown')
                    last_modifier = self.metadata.get('last_modified_by')

                    if last_modifier and last_modifier != current_computer:
                        result['warning_level'] = 'high'
                        result['message'] = f'Database modified by {last_modifier}'
                    else:
                        result['warning_level'] = 'medium'
                        result['message'] = 'Database modified externally'

        except Exception as e:
            result['warning_level'] = 'low'
            result['message'] = f'Could not check file status: {e}'

        return result

    def create_backup(self):
        """
        Create backup of database before write operation

        Returns:
            tuple: (success: bool, backup_path: str, error: str)
        """
        if not os.path.exists(self.db_path):
            return (False, None, 'Database file not found')

        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            db_name = os.path.basename(self.db_path)
            backup_name = f"{db_name}.backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)

            # Copy database file
            shutil.copy2(self.db_path, backup_path)

            # Verify backup
            if os.path.exists(backup_path):
                return (True, backup_path, None)
            else:
                return (False, None, 'Backup file not created')

        except Exception as e:
            return (False, None, str(e))

    def cleanup_old_backups(self, keep_count=5):
        """
        Remove old backups, keeping only the most recent ones

        Args:
            keep_count: Number of backups to keep
        """
        if not os.path.exists(self.backup_dir):
            return

        try:
            # Get all backup files
            backups = []
            db_name = os.path.basename(self.db_path)

            for filename in os.listdir(self.backup_dir):
                if filename.startswith(db_name + '.backup_'):
                    filepath = os.path.join(self.backup_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    backups.append((filepath, mtime))

            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)

            # Delete old backups
            for filepath, _ in backups[keep_count:]:
                try:
                    os.remove(filepath)
                    print(f"Deleted old backup: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"Failed to delete {filepath}: {e}")

        except Exception as e:
            print(f"Failed to cleanup backups: {e}")

    def get_backup_info(self):
        """Get information about existing backups"""
        if not os.path.exists(self.backup_dir):
            return []

        backups = []
        db_name = os.path.basename(self.db_path)

        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith(db_name + '.backup_'):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)

                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)

        except Exception as e:
            print(f"Failed to get backup info: {e}")

        return backups


class SafetyWarningsTestWindow:
    """Test window for safety warnings system"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Safety Warnings - Phase 1.3 Test")
        self.window.geometry("900x700")

        # Find database
        self.db_path = self.find_database()

        # Create safety checker
        self.safety = DatabaseSafetyChecker(self.db_path)

        # Settings
        self.auto_backup_enabled = tk.BooleanVar(value=True)
        self.conflict_check_enabled = tk.BooleanVar(value=True)
        self.warn_on_write = tk.BooleanVar(value=True)

        self.setup_ui()
        self.refresh_status()

    def find_database(self):
        """Find the database file"""
        # Check parent directory
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(parent, 'gcode_database.db')

        if os.path.exists(db_path):
            return db_path

        # Check current directory
        db_path = os.path.join(os.getcwd(), 'gcode_database.db')
        if os.path.exists(db_path):
            return db_path

        # Default path (may not exist)
        return os.path.join(parent, 'gcode_database.db')

    def setup_ui(self):
        """Set up user interface"""

        # Header
        header = ttk.Frame(self.window)
        header.pack(fill='x', padx=10, pady=10)

        ttk.Label(header, text="Phase 1.3 Test Environment - Safety Warnings Before Writes",
                 font=('TkDefaultFont', 12, 'bold')).pack()

        # Database info
        db_frame = ttk.LabelFrame(self.window, text="Database Information")
        db_frame.pack(fill='x', padx=10, pady=10)

        info_grid = ttk.Frame(db_frame)
        info_grid.pack(padx=10, pady=10, fill='x')

        # Path
        ttk.Label(info_grid, text="Path:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, sticky='w', pady=2)
        self.db_path_label = ttk.Label(info_grid, text=self.db_path, foreground='blue')
        self.db_path_label.grid(row=0, column=1, sticky='w', padx=10)

        # Status
        ttk.Label(info_grid, text="Status:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=1, column=0, sticky='w', pady=2)
        self.db_status_label = ttk.Label(info_grid, text="--")
        self.db_status_label.grid(row=1, column=1, sticky='w', padx=10)

        # Last modified by
        ttk.Label(info_grid, text="Last Modified By:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=2, column=0, sticky='w', pady=2)
        self.last_modified_by_label = ttk.Label(info_grid, text="--")
        self.last_modified_by_label.grid(row=2, column=1, sticky='w', padx=10)

        # Last modified time
        ttk.Label(info_grid, text="Last Modified:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=3, column=0, sticky='w', pady=2)
        self.last_modified_time_label = ttk.Label(info_grid, text="--")
        self.last_modified_time_label.grid(row=3, column=1, sticky='w', padx=10)

        # Safety settings
        settings_frame = ttk.LabelFrame(self.window, text="Safety Settings")
        settings_frame.pack(fill='x', padx=10, pady=10)

        settings_inner = ttk.Frame(settings_frame)
        settings_inner.pack(padx=10, pady=10)

        ttk.Checkbutton(settings_inner, text="Auto-backup before writes",
                       variable=self.auto_backup_enabled).pack(anchor='w', pady=2)
        ttk.Checkbutton(settings_inner, text="Check for conflicts before writes",
                       variable=self.conflict_check_enabled).pack(anchor='w', pady=2)
        ttk.Checkbutton(settings_inner, text="Warn before write operations",
                       variable=self.warn_on_write).pack(anchor='w', pady=2)

        # Conflict check results
        conflict_frame = ttk.LabelFrame(self.window, text="Conflict Check Status")
        conflict_frame.pack(fill='x', padx=10, pady=10)

        conflict_grid = ttk.Frame(conflict_frame)
        conflict_grid.pack(padx=10, pady=10, fill='x')

        # Warning level
        ttk.Label(conflict_grid, text="Warning Level:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, sticky='w', pady=2)
        self.warning_level_label = ttk.Label(conflict_grid, text="--")
        self.warning_level_label.grid(row=0, column=1, sticky='w', padx=10)

        # Conflict detected
        ttk.Label(conflict_grid, text="Conflict Detected:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=1, column=0, sticky='w', pady=2)
        self.conflict_detected_label = ttk.Label(conflict_grid, text="--")
        self.conflict_detected_label.grid(row=1, column=1, sticky='w', padx=10)

        # Message
        ttk.Label(conflict_grid, text="Message:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=2, column=0, sticky='w', pady=2)
        self.conflict_message_label = ttk.Label(conflict_grid, text="--")
        self.conflict_message_label.grid(row=2, column=1, sticky='w', padx=10)

        # Backup info
        backup_frame = ttk.LabelFrame(self.window, text="Backup Information")
        backup_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Backup list
        backup_list_frame = ttk.Frame(backup_frame)
        backup_list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Scrollbar
        backup_scroll = ttk.Scrollbar(backup_list_frame)
        backup_scroll.pack(side='right', fill='y')

        # Treeview for backups
        self.backup_tree = ttk.Treeview(
            backup_list_frame,
            columns=('created', 'size'),
            show='tree headings',
            yscrollcommand=backup_scroll.set
        )
        backup_scroll.config(command=self.backup_tree.yview)

        self.backup_tree.heading('created', text='Created')
        self.backup_tree.heading('size', text='Size (MB)')

        self.backup_tree.column('#0', width=400)
        self.backup_tree.column('created', width=200)
        self.backup_tree.column('size', width=100)

        self.backup_tree.pack(fill='both', expand=True)

        # Action buttons
        action_frame = ttk.Frame(self.window)
        action_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(action_frame, text="🔄 Refresh Status",
                  command=self.refresh_status).pack(side='left', padx=5)

        ttk.Button(action_frame, text="🔍 Check Conflicts",
                  command=self.check_conflicts).pack(side='left', padx=5)

        ttk.Button(action_frame, text="💾 Create Backup",
                  command=self.create_backup).pack(side='left', padx=5)

        ttk.Button(action_frame, text="✍️ Simulate Write",
                  command=self.simulate_write).pack(side='left', padx=5)

        ttk.Button(action_frame, text="🗑️ Cleanup Old Backups",
                  command=self.cleanup_backups).pack(side='left', padx=5)

        ttk.Button(action_frame, text="❌ Close",
                  command=self.window.destroy).pack(side='right', padx=5)

    def refresh_status(self):
        """Refresh all status displays"""
        # Check database exists
        if os.path.exists(self.db_path):
            self.db_status_label.config(text="✓ Found", foreground='green')
        else:
            self.db_status_label.config(text="✗ Not Found", foreground='red')

        # Update metadata
        metadata = self.safety.metadata

        if metadata.get('last_modified_by'):
            self.last_modified_by_label.config(text=metadata['last_modified_by'])
        else:
            self.last_modified_by_label.config(text="Unknown")

        if metadata.get('last_modified_time'):
            try:
                dt = datetime.fromisoformat(metadata['last_modified_time'])
                self.last_modified_time_label.config(text=dt.strftime('%Y-%m-%d %H:%M:%S'))
            except:
                self.last_modified_time_label.config(text=metadata['last_modified_time'])
        else:
            self.last_modified_time_label.config(text="Never")

        # Refresh conflict check
        self.check_conflicts()

        # Refresh backup list
        self.refresh_backups()

    def check_conflicts(self):
        """Check for conflicts"""
        result = self.safety.check_for_conflicts()

        # Update warning level
        level = result['warning_level']
        level_colors = {
            'none': ('✓ None', 'green'),
            'low': ('⚠ Low', 'orange'),
            'medium': ('⚠ Medium', 'orange'),
            'high': ('⚠ High', 'red')
        }

        text, color = level_colors.get(level, ('Unknown', 'gray'))
        self.warning_level_label.config(text=text, foreground=color)

        # Update conflict detected
        if result['conflict_detected']:
            self.conflict_detected_label.config(text="✗ Yes", foreground='red')
        else:
            self.conflict_detected_label.config(text="✓ No", foreground='green')

        # Update message
        if result['message']:
            self.conflict_message_label.config(text=result['message'])
        else:
            self.conflict_message_label.config(text="No issues detected")

    def refresh_backups(self):
        """Refresh backup list"""
        # Clear tree
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)

        # Get backups
        backups = self.safety.get_backup_info()

        if not backups:
            self.backup_tree.insert('', 'end', text='No backups found', values=('', ''))
            return

        # Add backups to tree
        for backup in backups:
            self.backup_tree.insert('', 'end',
                                   text=backup['filename'],
                                   values=(backup['created'], backup['size_mb']))

    def create_backup(self):
        """Create a backup"""
        success, backup_path, error = self.safety.create_backup()

        if success:
            messagebox.showinfo("Backup Created",
                f"Backup created successfully:\n\n{os.path.basename(backup_path)}")
            self.refresh_backups()
        else:
            messagebox.showerror("Backup Failed",
                f"Failed to create backup:\n\n{error}")

    def simulate_write(self):
        """Simulate a database write operation"""
        if not os.path.exists(self.db_path):
            messagebox.showerror("Error", "Database file not found")
            return

        # Check conflicts if enabled
        if self.conflict_check_enabled.get():
            result = self.safety.check_for_conflicts()

            if result['conflict_detected'] and result['warning_level'] in ['medium', 'high']:
                if not messagebox.askyesno("Conflict Detected",
                    f"{result['message']}\n\n"
                    "The database has been modified externally.\n\n"
                    "Do you want to continue anyway?",
                    icon='warning'):
                    return

        # Create backup if enabled
        if self.auto_backup_enabled.get():
            success, backup_path, error = self.safety.create_backup()
            if not success:
                if not messagebox.askyesno("Backup Failed",
                    f"Failed to create backup:\n{error}\n\n"
                    "Continue without backup?",
                    icon='warning'):
                    return

        # Warn if enabled
        if self.warn_on_write.get():
            if not messagebox.askyesno("Confirm Write",
                "Are you sure you want to write to the database?\n\n"
                "This operation will modify the database file.",
                icon='question'):
                return

        # Simulate write by recording it
        computer_name = os.environ.get('COMPUTERNAME', 'TestComputer')
        self.safety.record_write(computer_name)

        messagebox.showinfo("Write Complete",
            "Simulated database write completed.\n\n"
            "Metadata has been updated.")

        self.refresh_status()

    def cleanup_backups(self):
        """Cleanup old backups"""
        backups = self.safety.get_backup_info()
        count = len(backups)

        if count == 0:
            messagebox.showinfo("No Backups", "No backups found to cleanup")
            return

        # Ask how many to keep
        keep = 5
        self.safety.cleanup_old_backups(keep_count=keep)

        messagebox.showinfo("Cleanup Complete",
            f"Cleaned up old backups.\nKept the {keep} most recent backups.")

        self.refresh_backups()

    def run(self):
        """Run the application"""
        self.window.mainloop()


def main():
    """Main entry point"""
    print("="*80)
    print("Phase 1.3 Test Environment - Safety Warnings Before Writes")
    print("="*80)
    print()
    print("This test environment demonstrates safety features that prevent")
    print("data conflicts and loss before database write operations.")
    print()

    app = SafetyWarningsTestWindow()
    app.run()


if __name__ == '__main__':
    main()
