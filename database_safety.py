"""
Database Safety Checker Module
Tracks modifications, detects conflicts, creates backups before writes

Extracted from test_phase1/safety_warnings_test.py for integration into main application
"""

import os
import json
import shutil
from datetime import datetime


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
                    # Check if it was us or someone else
                    current_computer = os.environ.get('COMPUTERNAME', 'Unknown')
                    last_modifier = self.metadata.get('last_modified_by')

                    # Calculate time since last access (in seconds)
                    time_since_access = (file_mtime - last_access_dt).total_seconds()

                    # If modified by another computer -> HIGH warning
                    if last_modifier and last_modifier != current_computer:
                        result['conflict_detected'] = True
                        result['warning_level'] = 'high'
                        result['message'] = f'Database modified by {last_modifier}'
                    # If modified by us but it's been a while (>30 seconds) -> MEDIUM warning
                    elif time_since_access > 30:
                        result['conflict_detected'] = True
                        result['warning_level'] = 'medium'
                        result['message'] = 'Database modified externally (long time since last access)'
                    # If modified by us recently (<=30 seconds) -> NO warning (normal operation)
                    else:
                        # This is expected - we just wrote to the DB
                        result['conflict_detected'] = False
                        result['warning_level'] = 'none'
                        result['message'] = None

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
                    print(f"Failed to delete backup: {e}")

        except Exception as e:
            print(f"Failed to cleanup backups: {e}")

    def update_metadata(self, updates):
        """
        Update specific metadata fields

        Args:
            updates: dict of fields to update
        """
        self.metadata.update(updates)
        self.save_metadata()
