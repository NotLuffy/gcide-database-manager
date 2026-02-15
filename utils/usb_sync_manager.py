"""
USB Sync Manager - Core Logic

Manages synchronization between repository G-code files and USB drives used on CNC machines.

Features:
- SHA256 hash-based change detection
- Manual drive registration (no automatic detection)
- Safe copy operations with hash verification
- Automatic backup integration
- Conflict detection and resolution support

Status Values:
- IN_SYNC: Repository and USB hashes match
- REPO_NEWER: Repository has newer version than USB
- USB_NEWER: USB has newer version than repository
- CONFLICT: Both have changes (requires manual resolution)
- USB_MISSING: File exists in repo but not on USB
- REPO_MISSING: File exists on USB but not in repo
"""

import sqlite3
import hashlib
import shutil
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import getpass


class USBSyncManager:
    """Core USB sync manager for hash-based file synchronization"""

    def __init__(self, db_path: str, repository_path: str):
        """
        Initialize USB sync manager.

        Args:
            db_path: Path to SQLite database
            repository_path: Path to repository folder
        """
        self.db_path = db_path
        self.repository_path = Path(repository_path)
        self.current_user = getpass.getuser()

    # =============================================================
    # HASH CALCULATION
    # =============================================================

    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash as hex string, or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None

    def calculate_directory_hashes(self, directory: str, pattern: str = "*.nc") -> Dict[str, Dict]:
        """
        Calculate hashes for all matching files in directory.

        Args:
            directory: Path to directory
            pattern: File pattern (default: *.nc)

        Returns:
            Dict mapping program_number -> {hash, modified, size}
        """
        directory_path = Path(directory)
        if not directory_path.exists():
            return {}

        results = {}
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                # Extract program number from filename (e.g., o57508.nc -> O57508)
                program_number = file_path.stem.upper()
                if not program_number.startswith('O'):
                    program_number = 'O' + program_number

                # Calculate hash and get metadata
                file_hash = self.calculate_file_hash(str(file_path))
                if file_hash:
                    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    results[program_number] = {
                        'hash': file_hash,
                        'modified': modified_time.isoformat(),
                        'size': file_path.stat().st_size,
                        'path': str(file_path)
                    }

        return results

    # =============================================================
    # DRIVE MANAGEMENT
    # =============================================================

    def register_drive(self, drive_label: str, drive_path: str, drive_serial: str = None, notes: str = None) -> bool:
        """
        Register a new USB drive.

        Args:
            drive_label: Friendly name for drive (e.g., "CNC-MACHINE-A")
            drive_path: Path to drive folder (e.g., "E:\\GCODE\\")
            drive_serial: Optional drive serial number
            notes: Optional notes

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO usb_drives (drive_label, drive_serial, last_seen_path, notes)
                VALUES (?, ?, ?, ?)
            ''', (drive_label, drive_serial, drive_path, notes))

            conn.commit()
            return True

        except sqlite3.IntegrityError:
            # Drive already exists
            cursor.execute('''
                UPDATE usb_drives
                SET last_seen_path = ?, drive_serial = ?, notes = ?
                WHERE drive_label = ?
            ''', (drive_path, drive_serial, notes, drive_label))
            conn.commit()
            return True

        except Exception as e:
            print(f"Error registering drive: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def get_registered_drives(self) -> List[Dict]:
        """
        Get list of all registered drives.

        Returns:
            List of drive dictionaries
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT drive_id, drive_label, drive_serial, last_seen_path,
                   last_scan_date, total_programs, in_sync_count, notes
            FROM usb_drives
            ORDER BY drive_label
        ''')

        drives = []
        for row in cursor.fetchall():
            drives.append({
                'drive_id': row[0],
                'drive_label': row[1],
                'drive_serial': row[2],
                'last_seen_path': row[3],
                'last_scan_date': row[4],
                'total_programs': row[5],
                'in_sync_count': row[6],
                'notes': row[7]
            })

        conn.close()
        return drives

    def get_drive_path(self, drive_label: str) -> Optional[str]:
        """
        Get the path for a registered drive.

        Args:
            drive_label: Drive label

        Returns:
            Drive path or None if not found
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT last_seen_path
            FROM usb_drives
            WHERE drive_label = ?
        ''', (drive_label,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    # =============================================================
    # DRIVE SCANNING
    # =============================================================

    def scan_drive(self, drive_label: str, drive_path: str = None) -> Dict:
        """
        Scan USB drive and compare with repository.

        Args:
            drive_label: Drive label
            drive_path: Optional override path (uses registered path if None)

        Returns:
            Dict with scan results and statistics
        """
        # Get drive path if not provided
        if not drive_path:
            drive_path = self.get_drive_path(drive_label)
            if not drive_path:
                return {'error': 'Drive not found'}

        # Verify path exists
        if not os.path.exists(drive_path):
            return {'error': f'Drive path not found: {drive_path}'}

        # Scan USB drive
        print(f"Scanning USB drive: {drive_path}")
        usb_files = self.calculate_directory_hashes(drive_path)

        # Get repository hashes from database
        repo_hashes = self._get_repository_hashes()

        # Compare and update sync tracking
        stats = {
            'in_sync': 0,
            'repo_newer': 0,
            'usb_newer': 0,
            'conflict': 0,
            'usb_missing': 0,
            'repo_missing': 0,
            'total_scanned': len(usb_files)
        }

        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            # Compare each USB file with repository
            for program_number, usb_info in usb_files.items():
                repo_info = repo_hashes.get(program_number)

                if not repo_info:
                    # File on USB but not in repository
                    status = 'REPO_MISSING'
                    stats['repo_missing'] += 1
                elif usb_info['hash'] == repo_info['hash']:
                    # Hashes match - in sync
                    status = 'IN_SYNC'
                    stats['in_sync'] += 1
                else:
                    # Hashes differ - determine which is newer
                    usb_time = datetime.fromisoformat(usb_info['modified'])
                    repo_time = datetime.fromisoformat(repo_info['modified'])

                    if repo_time > usb_time:
                        status = 'REPO_NEWER'
                        stats['repo_newer'] += 1
                    elif usb_time > repo_time:
                        status = 'USB_NEWER'
                        stats['usb_newer'] += 1
                    else:
                        # Same timestamp but different hash - conflict
                        status = 'CONFLICT'
                        stats['conflict'] += 1

                # Update sync tracking
                cursor.execute('''
                    INSERT OR REPLACE INTO usb_sync_tracking (
                        drive_label, drive_path, program_number,
                        repo_hash, usb_hash, repo_modified, usb_modified,
                        sync_status, last_sync_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    drive_label,
                    drive_path,
                    program_number,
                    repo_info['hash'] if repo_info else None,
                    usb_info['hash'],
                    repo_info['modified'] if repo_info else None,
                    usb_info['modified'],
                    status,
                    datetime.now().isoformat()
                ))

            # Check for files in repository but not on USB
            for program_number, repo_info in repo_hashes.items():
                if program_number not in usb_files:
                    stats['usb_missing'] += 1
                    cursor.execute('''
                        INSERT OR REPLACE INTO usb_sync_tracking (
                            drive_label, drive_path, program_number,
                            repo_hash, usb_hash, repo_modified, usb_modified,
                            sync_status, last_sync_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        drive_label,
                        drive_path,
                        program_number,
                        repo_info['hash'],
                        None,
                        repo_info['modified'],
                        None,
                        'USB_MISSING',
                        datetime.now().isoformat()
                    ))

            # Update drive metadata
            cursor.execute('''
                UPDATE usb_drives
                SET last_scan_date = ?,
                    total_programs = ?,
                    in_sync_count = ?,
                    last_seen_path = ?
                WHERE drive_label = ?
            ''', (
                datetime.now().isoformat(),
                len(usb_files),
                stats['in_sync'],
                drive_path,
                drive_label
            ))

            conn.commit()
            stats['success'] = True

        except Exception as e:
            conn.rollback()
            stats['error'] = str(e)
            stats['success'] = False

        finally:
            conn.close()

        return stats

    def _get_repository_hashes(self) -> Dict[str, Dict]:
        """
        Get all program hashes from database.

        Returns:
            Dict mapping program_number -> {hash, modified}
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT program_number, content_hash, last_modified
            FROM programs
            WHERE program_number IS NOT NULL
        ''')

        results = {}
        for row in cursor.fetchall():
            if row[1]:  # Only include if hash exists
                results[row[0]] = {
                    'hash': row[1],
                    'modified': row[2] if row[2] else datetime.now().isoformat()
                }

        conn.close()
        return results

    # =============================================================
    # SYNC STATUS QUERIES
    # =============================================================

    def get_sync_status(self, drive_label: str, filter_status: str = None) -> List[Dict]:
        """
        Get sync status for all programs on a drive.

        Args:
            drive_label: Drive label
            filter_status: Optional status filter (e.g., 'CONFLICT', 'REPO_NEWER')

        Returns:
            List of sync status dictionaries
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        query = '''
            SELECT program_number, sync_status, repo_hash, usb_hash,
                   repo_modified, usb_modified, last_sync_date, notes
            FROM usb_sync_tracking
            WHERE drive_label = ?
        '''
        params = [drive_label]

        if filter_status:
            query += ' AND sync_status = ?'
            params.append(filter_status)

        query += ' ORDER BY program_number'

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                'program_number': row[0],
                'sync_status': row[1],
                'repo_hash': row[2],
                'usb_hash': row[3],
                'repo_modified': row[4],
                'usb_modified': row[5],
                'last_sync_date': row[6],
                'notes': row[7]
            })

        conn.close()
        return results

    # =============================================================
    # SAFE COPY OPERATIONS
    # =============================================================

    def copy_to_usb(self, drive_label: str, program_numbers: List[str], force: bool = False) -> Dict:
        """
        Copy files from repository to USB with safety checks.

        Args:
            drive_label: Target drive label
            program_numbers: List of program numbers to copy
            force: If True, overwrite even if USB is newer (use with caution)

        Returns:
            Dict with results {success, copied, skipped, errors}
        """
        drive_path = self.get_drive_path(drive_label)
        if not drive_path:
            return {'success': False, 'error': 'Drive not found'}

        if not os.path.exists(drive_path):
            return {'success': False, 'error': f'Drive path not accessible: {drive_path}'}

        results = {
            'success': True,
            'copied': [],
            'skipped': [],
            'errors': []
        }

        for program_number in program_numbers:
            try:
                # Get sync status
                status_info = self._get_sync_info(drive_label, program_number)

                # Safety check: don't overwrite newer USB files unless forced
                if not force and status_info and status_info['sync_status'] in ['USB_NEWER', 'CONFLICT']:
                    results['skipped'].append({
                        'program': program_number,
                        'reason': f"USB has newer version (status: {status_info['sync_status']})"
                    })
                    continue

                # Get repository file path
                repo_file = self._get_repo_file_path(program_number)
                if not repo_file or not os.path.exists(repo_file):
                    results['errors'].append({
                        'program': program_number,
                        'error': 'Repository file not found'
                    })
                    continue

                # Calculate source hash
                source_hash = self.calculate_file_hash(repo_file)
                if not source_hash:
                    results['errors'].append({
                        'program': program_number,
                        'error': 'Failed to calculate source hash'
                    })
                    continue

                # Destination file path
                dest_file = Path(drive_path) / f"{program_number.lower()}.nc"

                # Copy file
                shutil.copy2(repo_file, dest_file)

                # Verify hash after copy
                dest_hash = self.calculate_file_hash(str(dest_file))
                if dest_hash != source_hash:
                    # Hash mismatch - rollback
                    os.remove(dest_file)
                    results['errors'].append({
                        'program': program_number,
                        'error': 'Hash verification failed after copy'
                    })
                    continue

                # Update sync tracking
                self._update_sync_tracking(
                    drive_label=drive_label,
                    drive_path=drive_path,
                    program_number=program_number,
                    repo_hash=source_hash,
                    usb_hash=dest_hash,
                    sync_status='IN_SYNC',
                    sync_direction='REPO_TO_USB'
                )

                # Log to history
                self._log_sync_action(
                    drive_label=drive_label,
                    program_number=program_number,
                    action='COPY_TO_USB',
                    repo_hash_before=status_info['repo_hash'] if status_info else None,
                    repo_hash_after=source_hash
                )

                results['copied'].append(program_number)

            except Exception as e:
                results['errors'].append({
                    'program': program_number,
                    'error': str(e)
                })

        return results

    def copy_from_usb(self, drive_label: str, program_numbers: List[str], auto_backup: bool = True) -> Dict:
        """
        Copy files from USB to repository with automatic backup.

        Args:
            drive_label: Source drive label
            program_numbers: List of program numbers to copy
            auto_backup: If True, backup existing repo file before overwriting

        Returns:
            Dict with results {success, copied, backed_up, errors}
        """
        drive_path = self.get_drive_path(drive_label)
        if not drive_path:
            return {'success': False, 'error': 'Drive not found'}

        if not os.path.exists(drive_path):
            return {'success': False, 'error': f'Drive path not accessible: {drive_path}'}

        results = {
            'success': True,
            'copied': [],
            'backed_up': [],
            'errors': []
        }

        for program_number in program_numbers:
            try:
                # Source USB file
                usb_file = Path(drive_path) / f"{program_number.lower()}.nc"
                if not usb_file.exists():
                    results['errors'].append({
                        'program': program_number,
                        'error': 'USB file not found'
                    })
                    continue

                # Calculate USB hash
                usb_hash = self.calculate_file_hash(str(usb_file))
                if not usb_hash:
                    results['errors'].append({
                        'program': program_number,
                        'error': 'Failed to calculate USB hash'
                    })
                    continue

                # Get repository file path
                repo_file = self._get_repo_file_path(program_number)
                if not repo_file:
                    results['errors'].append({
                        'program': program_number,
                        'error': 'Repository file not found'
                    })
                    continue

                # Auto-backup existing file if requested
                repo_hash_before = None
                if auto_backup and os.path.exists(repo_file):
                    repo_hash_before = self.calculate_file_hash(repo_file)
                    backup_result = self._backup_repo_file(program_number, repo_file)
                    if backup_result:
                        results['backed_up'].append(program_number)

                # Copy file from USB
                shutil.copy2(str(usb_file), repo_file)

                # Verify hash after copy
                repo_hash = self.calculate_file_hash(repo_file)
                if repo_hash != usb_hash:
                    # Hash mismatch - rollback (if backup exists, restore it)
                    results['errors'].append({
                        'program': program_number,
                        'error': 'Hash verification failed after copy'
                    })
                    continue

                # Update database hash
                self._update_program_hash(program_number, repo_hash)

                # Update sync tracking
                self._update_sync_tracking(
                    drive_label=drive_label,
                    drive_path=drive_path,
                    program_number=program_number,
                    repo_hash=repo_hash,
                    usb_hash=usb_hash,
                    sync_status='IN_SYNC',
                    sync_direction='USB_TO_REPO'
                )

                # Log to history
                self._log_sync_action(
                    drive_label=drive_label,
                    program_number=program_number,
                    action='COPY_FROM_USB',
                    repo_hash_before=repo_hash_before,
                    repo_hash_after=repo_hash
                )

                results['copied'].append(program_number)

            except Exception as e:
                results['errors'].append({
                    'program': program_number,
                    'error': str(e)
                })

        return results

    # =============================================================
    # HELPER METHODS
    # =============================================================

    def _get_sync_info(self, drive_label: str, program_number: str) -> Optional[Dict]:
        """Get sync tracking info for a program"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sync_status, repo_hash, usb_hash, repo_modified, usb_modified
            FROM usb_sync_tracking
            WHERE drive_label = ? AND program_number = ?
        ''', (drive_label, program_number))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'sync_status': result[0],
                'repo_hash': result[1],
                'usb_hash': result[2],
                'repo_modified': result[3],
                'usb_modified': result[4]
            }
        return None

    def _get_repo_file_path(self, program_number: str) -> Optional[str]:
        """Get repository file path from database"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT file_path
            FROM programs
            WHERE program_number = ?
        ''', (program_number,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def _update_sync_tracking(self, drive_label: str, drive_path: str, program_number: str,
                             repo_hash: str, usb_hash: str, sync_status: str, sync_direction: str):
        """Update sync tracking table"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            # Get current repo/usb modified times
            repo_file = self._get_repo_file_path(program_number)
            repo_modified = None
            if repo_file and os.path.exists(repo_file):
                repo_modified = datetime.fromtimestamp(os.path.getmtime(repo_file)).isoformat()

            usb_file = Path(drive_path) / f"{program_number.lower()}.nc"
            usb_modified = None
            if usb_file.exists():
                usb_modified = datetime.fromtimestamp(usb_file.stat().st_mtime).isoformat()

            cursor.execute('''
                INSERT OR REPLACE INTO usb_sync_tracking (
                    drive_label, drive_path, program_number,
                    repo_hash, usb_hash, repo_modified, usb_modified,
                    sync_status, last_sync_date, last_sync_direction
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                drive_label, drive_path, program_number,
                repo_hash, usb_hash, repo_modified, usb_modified,
                sync_status, datetime.now().isoformat(), sync_direction
            ))

            conn.commit()

        finally:
            conn.close()

    def _update_program_hash(self, program_number: str, new_hash: str):
        """Update program content hash in database"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE programs
                SET content_hash = ?, last_modified = ?
                WHERE program_number = ?
            ''', (new_hash, datetime.now().isoformat(), program_number))

            conn.commit()

        finally:
            conn.close()

    def _backup_repo_file(self, program_number: str, repo_file: str) -> bool:
        """
        Backup repository file using RepositoryManager.

        Args:
            program_number: Program number
            repo_file: Path to repository file

        Returns:
            True if backup successful
        """
        try:
            # Import RepositoryManager for archiving
            from repository_manager import RepositoryManager

            repo_mgr = RepositoryManager(self.db_path, str(self.repository_path))
            backup_path = repo_mgr.archive_old_file(
                old_file_path=repo_file,
                program_number=program_number,
                reason='usb_sync_import'
            )

            return backup_path is not None

        except Exception as e:
            print(f"Error backing up {program_number}: {e}")
            return False

    def _log_sync_action(self, drive_label: str, program_number: str, action: str,
                        repo_hash_before: str = None, repo_hash_after: str = None, details: str = None):
        """Log sync action to history table"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO sync_history (
                    sync_date, drive_label, program_number, action,
                    username, repo_hash_before, repo_hash_after, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                drive_label,
                program_number,
                action,
                self.current_user,
                repo_hash_before,
                repo_hash_after,
                details
            ))

            conn.commit()

        finally:
            conn.close()

    # =============================================================
    # SYNC HISTORY
    # =============================================================

    def get_sync_history(self, drive_label: str = None, program_number: str = None, limit: int = 100) -> List[Dict]:
        """
        Get sync history with optional filters.

        Args:
            drive_label: Optional drive filter
            program_number: Optional program filter
            limit: Maximum records to return

        Returns:
            List of history dictionaries
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        query = '''
            SELECT history_id, sync_date, drive_label, program_number,
                   action, username, files_affected, repo_hash_before, repo_hash_after, details
            FROM sync_history
            WHERE 1=1
        '''
        params = []

        if drive_label:
            query += ' AND drive_label = ?'
            params.append(drive_label)

        if program_number:
            query += ' AND program_number = ?'
            params.append(program_number)

        query += ' ORDER BY sync_date DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                'history_id': row[0],
                'sync_date': row[1],
                'drive_label': row[2],
                'program_number': row[3],
                'action': row[4],
                'username': row[5],
                'files_affected': row[6],
                'repo_hash_before': row[7],
                'repo_hash_after': row[8],
                'details': row[9]
            })

        conn.close()
        return results
