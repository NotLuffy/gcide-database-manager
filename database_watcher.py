"""
Database File Watcher Module
Watches database file for external changes from other computers/processes

Extracted from test_phase1/database_monitor_test.py for integration into main application
Requires: watchdog library (pip install watchdog)
"""

import os
import time
import hashlib
try:
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Create dummy base class if watchdog not available
    class FileSystemEventHandler:
        pass


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
