"""
Phase 1.2 Test - Database File Monitor
Isolated test environment for database file monitoring

This module tests the database file monitoring functionality independently
before integrating into the main application.
"""

import sys
import os
import time
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from threading import Thread
import hashlib

# Try to import watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("WARNING: watchdog library not installed")
    print("Install with: pip install watchdog")

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class DatabaseWatcher(FileSystemEventHandler):
    """
    Watches database file for external changes
    Detects when another computer/process modifies the database
    """

    def __init__(self, db_path, callback):
        """
        Initialize database watcher

        Args:
            db_path: Path to database file to monitor
            callback: Function to call when database changes detected
        """
        self.db_path = os.path.abspath(db_path)
        self.callback = callback
        self.last_modified = None
        self.last_size = None
        self.last_checksum = None
        self.monitoring = False

        # Initialize with current state
        if os.path.exists(self.db_path):
            self._update_state()

    def _update_state(self):
        """Update tracked state of database file"""
        try:
            stat = os.stat(self.db_path)
            self.last_modified = stat.st_mtime
            self.last_size = stat.st_size
            # Optional: Calculate checksum for very accurate detection
            # (disabled by default for performance)
            # self.last_checksum = self._calculate_checksum()
        except (OSError, IOError):
            pass

    def _calculate_checksum(self):
        """Calculate MD5 checksum of database file (optional, for accuracy)"""
        try:
            md5 = hashlib.md5()
            with open(self.db_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except (OSError, IOError):
            return None

    def on_modified(self, event):
        """Called when file is modified"""
        if not event.is_directory and os.path.abspath(event.src_path) == self.db_path:
            # Wait a bit for file to finish writing
            time.sleep(0.5)

            # Check if actually changed
            try:
                stat = os.stat(self.db_path)
                current_modified = stat.st_mtime
                current_size = stat.st_size

                # Only trigger if modified time or size changed
                if (self.last_modified is None or
                    current_modified != self.last_modified or
                    current_size != self.last_size):

                    self.last_modified = current_modified
                    self.last_size = current_size

                    # Notify callback
                    if self.callback:
                        self.callback()

            except (OSError, IOError):
                pass

    def start_monitoring(self):
        """Start monitoring the database file"""
        self.monitoring = True

    def stop_monitoring(self):
        """Stop monitoring the database file"""
        self.monitoring = False


class DatabaseMonitor:
    """
    High-level database monitoring manager
    Coordinates file watching and provides user notifications
    """

    def __init__(self, db_path, on_change_callback=None):
        """
        Initialize database monitor

        Args:
            db_path: Path to database file
            on_change_callback: Optional callback when changes detected
        """
        self.db_path = db_path
        self.on_change_callback = on_change_callback
        self.observer = None
        self.watcher = None
        self.monitoring = False
        self.auto_refresh = False
        self.change_count = 0
        self.last_change_time = None

    def start(self, auto_refresh=False):
        """
        Start monitoring database

        Args:
            auto_refresh: If True, automatically refresh on change
        """
        if not WATCHDOG_AVAILABLE:
            print("Cannot start monitoring - watchdog not installed")
            return False

        if not os.path.exists(self.db_path):
            print(f"Database file not found: {self.db_path}")
            return False

        self.auto_refresh = auto_refresh

        try:
            # Create watcher
            self.watcher = DatabaseWatcher(self.db_path, self._on_change_detected)

            # Create observer
            self.observer = Observer()
            watch_dir = os.path.dirname(self.db_path)
            self.observer.schedule(self.watcher, path=watch_dir, recursive=False)
            self.observer.start()

            self.monitoring = True
            print(f"Started monitoring: {self.db_path}")
            return True

        except Exception as e:
            print(f"Error starting monitor: {e}")
            return False

    def stop(self):
        """Stop monitoring database"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        self.monitoring = False
        print("Stopped monitoring")

    def _on_change_detected(self):
        """Internal callback when change detected"""
        self.change_count += 1
        self.last_change_time = datetime.now()

        print(f"Database change detected at {self.last_change_time.strftime('%H:%M:%S')}")

        if self.on_change_callback:
            self.on_change_callback()

    def get_status(self):
        """Get monitoring status"""
        return {
            'monitoring': self.monitoring,
            'auto_refresh': self.auto_refresh,
            'change_count': self.change_count,
            'last_change': self.last_change_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_change_time else None
        }

    def get_database_info(self):
        """Get information about the database file"""
        if not os.path.exists(self.db_path):
            return None

        try:
            stat = os.stat(self.db_path)
            size_mb = stat.st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(stat.st_mtime)

            # Try to get record count
            record_count = None
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM programs")
                record_count = cursor.fetchone()[0]
                conn.close()
            except:
                pass

            return {
                'path': self.db_path,
                'size_mb': round(size_mb, 2),
                'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
                'record_count': record_count
            }

        except Exception as e:
            print(f"Error getting database info: {e}")
            return None


class DatabaseMonitorTestWindow:
    """Test window for database monitoring"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Database File Monitor - Phase 1.2 Test")
        self.window.geometry("800x600")

        # Find database
        self.db_path = self.find_database()

        # Create monitor
        self.monitor = DatabaseMonitor(
            self.db_path,
            on_change_callback=self.on_database_changed
        )

        self.setup_ui()
        self.update_status()

        # Auto-start monitoring if watchdog available
        if WATCHDOG_AVAILABLE and os.path.exists(self.db_path):
            self.start_monitoring()

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

        ttk.Label(header, text="Phase 1.2 Test Environment - Database File Monitor",
                 font=('TkDefaultFont', 12, 'bold')).pack()

        # Watchdog status
        if not WATCHDOG_AVAILABLE:
            warning = ttk.Frame(self.window)
            warning.pack(fill='x', padx=10, pady=5)
            ttk.Label(warning, text="⚠️ WARNING: watchdog library not installed",
                     foreground='red', font=('TkDefaultFont', 10, 'bold')).pack()
            ttk.Label(warning, text="Install with: pip install watchdog",
                     foreground='red').pack()

        # Database info
        db_frame = ttk.LabelFrame(self.window, text="Database Information")
        db_frame.pack(fill='x', padx=10, pady=10)

        info_grid = ttk.Frame(db_frame)
        info_grid.pack(padx=10, pady=10)

        # Path
        ttk.Label(info_grid, text="Path:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, sticky='w', pady=2)
        self.db_path_label = ttk.Label(info_grid, text=self.db_path, foreground='blue')
        self.db_path_label.grid(row=0, column=1, sticky='w', padx=10)

        # Size
        ttk.Label(info_grid, text="Size:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=1, column=0, sticky='w', pady=2)
        self.db_size_label = ttk.Label(info_grid, text="--")
        self.db_size_label.grid(row=1, column=1, sticky='w', padx=10)

        # Modified
        ttk.Label(info_grid, text="Last Modified:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=2, column=0, sticky='w', pady=2)
        self.db_modified_label = ttk.Label(info_grid, text="--")
        self.db_modified_label.grid(row=2, column=1, sticky='w', padx=10)

        # Records
        ttk.Label(info_grid, text="Records:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=3, column=0, sticky='w', pady=2)
        self.db_records_label = ttk.Label(info_grid, text="--")
        self.db_records_label.grid(row=3, column=1, sticky='w', padx=10)

        # Monitoring controls
        monitor_frame = ttk.LabelFrame(self.window, text="Monitoring Controls")
        monitor_frame.pack(fill='x', padx=10, pady=10)

        control_grid = ttk.Frame(monitor_frame)
        control_grid.pack(padx=10, pady=10)

        # Start/Stop buttons
        btn_row = ttk.Frame(control_grid)
        btn_row.pack(fill='x', pady=5)

        self.start_btn = ttk.Button(btn_row, text="▶️ Start Monitoring",
                                    command=self.start_monitoring)
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = ttk.Button(btn_row, text="⏹️ Stop Monitoring",
                                   command=self.stop_monitoring, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_grid, text="Auto-refresh on change",
                       variable=self.auto_refresh_var,
                       command=self.toggle_auto_refresh).pack(anchor='w', pady=5)

        # Monitoring status
        status_frame = ttk.LabelFrame(self.window, text="Monitoring Status")
        status_frame.pack(fill='x', padx=10, pady=10)

        status_grid = ttk.Frame(status_frame)
        status_grid.pack(padx=10, pady=10)

        # Status
        ttk.Label(status_grid, text="Status:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=0, column=0, sticky='w', pady=2)
        self.status_label = ttk.Label(status_grid, text="Not monitoring", foreground='gray')
        self.status_label.grid(row=0, column=1, sticky='w', padx=10)

        # Changes detected
        ttk.Label(status_grid, text="Changes Detected:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=1, column=0, sticky='w', pady=2)
        self.changes_label = ttk.Label(status_grid, text="0")
        self.changes_label.grid(row=1, column=1, sticky='w', padx=10)

        # Last change
        ttk.Label(status_grid, text="Last Change:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=2, column=0, sticky='w', pady=2)
        self.last_change_label = ttk.Label(status_grid, text="Never")
        self.last_change_label.grid(row=2, column=1, sticky='w', padx=10)

        # Event log
        log_frame = ttk.LabelFrame(self.window, text="Event Log")
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Log text
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side='right', fill='y')

        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD,
                               yscrollcommand=log_scroll.set)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        log_scroll.config(command=self.log_text.yview)

        # Action buttons
        action_frame = ttk.Frame(self.window)
        action_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(action_frame, text="🔄 Refresh Info",
                  command=self.refresh_db_info).pack(side='left', padx=5)

        ttk.Button(action_frame, text="📝 Simulate Change",
                  command=self.simulate_change).pack(side='left', padx=5)

        ttk.Button(action_frame, text="🗑️ Clear Log",
                  command=self.clear_log).pack(side='left', padx=5)

        ttk.Button(action_frame, text="❌ Close",
                  command=self.close_window).pack(side='right', padx=5)

        # Initial log message
        self.log("Database Monitor Test Environment Started")
        if not WATCHDOG_AVAILABLE:
            self.log("⚠️ WARNING: watchdog library not installed", 'warning')
            self.log("Install with: pip install watchdog", 'info')
        if not os.path.exists(self.db_path):
            self.log(f"⚠️ WARNING: Database not found at {self.db_path}", 'warning')

    def start_monitoring(self):
        """Start monitoring"""
        if not WATCHDOG_AVAILABLE:
            messagebox.showerror("Error",
                "watchdog library not installed.\n\n"
                "Install with:\npip install watchdog")
            return

        if not os.path.exists(self.db_path):
            messagebox.showerror("Error",
                f"Database file not found:\n{self.db_path}")
            return

        auto_refresh = self.auto_refresh_var.get()
        if self.monitor.start(auto_refresh=auto_refresh):
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.log(f"Started monitoring: {os.path.basename(self.db_path)}")
            if auto_refresh:
                self.log("Auto-refresh enabled")
            self.update_status()

    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitor.stop()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log("Stopped monitoring")
        self.update_status()

    def toggle_auto_refresh(self):
        """Toggle auto-refresh setting"""
        if self.monitor.monitoring:
            self.monitor.auto_refresh = self.auto_refresh_var.get()
            status = "enabled" if self.monitor.auto_refresh else "disabled"
            self.log(f"Auto-refresh {status}")

    def on_database_changed(self):
        """Called when database change detected"""
        self.log("🔔 Database change detected!", 'alert')

        if self.monitor.auto_refresh:
            self.log("Auto-refreshing database info...")
            self.refresh_db_info()
        else:
            # Show notification
            self.window.after(0, lambda: messagebox.showinfo(
                "Database Changed",
                "The database file was modified by an external process.\n\n"
                "Click 'Refresh Info' to see updated information."
            ))

        self.update_status()

    def refresh_db_info(self):
        """Refresh database information"""
        self.log("Refreshing database information...")
        info = self.monitor.get_database_info()

        if info:
            self.db_size_label.config(text=f"{info['size_mb']} MB")
            self.db_modified_label.config(text=info['modified'])
            if info['record_count'] is not None:
                self.db_records_label.config(text=f"{info['record_count']:,}")
            else:
                self.db_records_label.config(text="Unable to read")
            self.log("Database info refreshed")
        else:
            self.log("⚠️ Failed to read database info", 'warning')

    def simulate_change(self):
        """Simulate a database change for testing"""
        if not os.path.exists(self.db_path):
            messagebox.showerror("Error", "Database file not found")
            return

        try:
            # Touch the file to update modification time
            os.utime(self.db_path, None)
            self.log("Simulated database change (updated modification time)")
            messagebox.showinfo("Simulated Change",
                "Database file modification time updated.\n\n"
                "If monitoring is active, you should see a change notification.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to simulate change:\n{str(e)}")

    def update_status(self):
        """Update status display"""
        status = self.monitor.get_status()

        if status['monitoring']:
            self.status_label.config(text="Monitoring active ✓", foreground='green')
        else:
            self.status_label.config(text="Not monitoring", foreground='gray')

        self.changes_label.config(text=str(status['change_count']))

        if status['last_change']:
            self.last_change_label.config(text=status['last_change'])
        else:
            self.last_change_label.config(text="Never")

    def log(self, message, level='info'):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_message = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)

        # Color coding
        if level == 'warning':
            # Make last line orange
            pass
        elif level == 'alert':
            # Make last line bold
            pass

    def clear_log(self):
        """Clear event log"""
        self.log_text.delete(1.0, tk.END)
        self.log("Log cleared")

    def close_window(self):
        """Close window"""
        if self.monitor.monitoring:
            self.monitor.stop()
        self.window.destroy()

    def run(self):
        """Run the application"""
        # Update info on startup
        if os.path.exists(self.db_path):
            self.refresh_db_info()

        self.window.mainloop()


def main():
    """Main entry point"""
    print("="*80)
    print("Phase 1.2 Test Environment - Database File Monitor")
    print("="*80)
    print()
    print("This test environment monitors the database file for external changes.")
    print("It does NOT modify the database - it only watches for changes.")
    print()

    if not WATCHDOG_AVAILABLE:
        print("⚠️ WARNING: watchdog library not installed")
        print("Install with: pip install watchdog")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return

    app = DatabaseMonitorTestWindow()
    app.run()


if __name__ == '__main__':
    main()
