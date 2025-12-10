"""
Repository and Archive Management System
Handles file versioning, archiving, cleanup, and consolidation
"""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re


class RepositoryManager:
    """Manages repository files, archiving, and cleanup operations"""

    def __init__(self, db_path, repository_path):
        self.db_path = db_path
        self.repository_path = Path(repository_path)
        self.archive_path = self.repository_path.parent / 'archive'

        # Initialize archive structure
        self.init_archive()

    def init_archive(self):
        """Create archive folder structure"""
        self.archive_path.mkdir(exist_ok=True)
        print(f"[Archive] Initialized at: {self.archive_path}")

    def get_next_version_number(self, program_number):
        """
        Get next version number for a program by checking archive folder.

        Args:
            program_number: Program number (e.g., 'o10535')

        Returns:
            int: Next version number (1, 2, 3, etc.)
        """
        if not self.archive_path.exists():
            return 1

        # Find all archived versions of this program
        pattern = re.compile(rf'^{re.escape(program_number)}_(\d+)', re.IGNORECASE)
        max_version = 0

        for date_folder in self.archive_path.iterdir():
            if not date_folder.is_dir():
                continue

            for archived_file in date_folder.iterdir():
                match = pattern.match(archived_file.stem)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)

        return max_version + 1

    def archive_old_file(self, old_file_path, program_number, reason='update'):
        """
        Archive old file version before importing new one.
        Old file is renamed with version suffix and moved to archive.

        Args:
            old_file_path: Path to current file in repository
            program_number: Program number
            reason: Reason for archiving ('update', 'consolidate', 'orphan', 'manual')

        Returns:
            str: Path to archived file
        """
        old_file_path = Path(old_file_path)

        if not old_file_path.exists():
            print(f"[Archive] File not found: {old_file_path}")
            return None

        # Get next version number
        version = self.get_next_version_number(program_number)

        # Create dated archive folder
        date_folder = self.archive_path / datetime.now().strftime('%Y-%m-%d')
        date_folder.mkdir(exist_ok=True)

        # Build archive filename with version suffix
        file_ext = old_file_path.suffix if old_file_path.suffix else '.nc'
        archive_filename = f"{program_number}_{version}{file_ext}"
        archive_file_path = date_folder / archive_filename

        # Handle collision (shouldn't happen but be safe)
        counter = 1
        while archive_file_path.exists():
            archive_filename = f"{program_number}_{version}_{counter}{file_ext}"
            archive_file_path = date_folder / archive_filename
            counter += 1

        try:
            # Move file to archive
            shutil.move(str(old_file_path), str(archive_file_path))

            # Log to database
            self._log_archive(program_number, str(old_file_path), str(archive_file_path), reason)

            print(f"[Archive] {old_file_path.name} → {archive_file_path.relative_to(self.archive_path)}")
            return str(archive_file_path)

        except Exception as e:
            print(f"[Archive] Error archiving file: {e}")
            return None

    def _log_archive(self, program_number, old_path, archive_path, reason):
        """Log archive operation to database activity_log"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO activity_log (timestamp, username, action_type, program_number, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                'system',
                'archive_file',
                program_number,
                f"Reason: {reason}, Old: {old_path}, Archive: {archive_path}"
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Archive] Warning: Could not log to database: {e}")

    def import_with_archive(self, source_file, program_number):
        """
        Import new file version, archiving old version if exists.
        New file keeps the standard name (no suffix).
        Old file gets version suffix and moves to archive.

        Args:
            source_file: Path to new file
            program_number: Program number

        Returns:
            str: Path to new file in repository
        """
        source_file = Path(source_file)

        if not source_file.exists():
            print(f"[Import] Source file not found: {source_file}")
            return None

        # Determine standard filename (normalize to .nc extension)
        file_ext = source_file.suffix if source_file.suffix else '.nc'
        standard_filename = f"{program_number}{file_ext}"
        dest_path = self.repository_path / standard_filename

        # If file already exists in repository, archive it first
        if dest_path.exists():
            # Check if content is identical
            if self._files_identical(source_file, dest_path):
                print(f"[Import] File already exists (identical content): {standard_filename}")
                return str(dest_path)

            # Archive old version (gets version suffix)
            print(f"[Import] New version detected, archiving old version...")
            self.archive_old_file(dest_path, program_number, reason='update')

        try:
            # Copy new file to repository with standard name (no suffix)
            shutil.copy2(str(source_file), str(dest_path))
            print(f"[Import] Imported: {standard_filename}")

            return str(dest_path)

        except Exception as e:
            print(f"[Import] Error importing file: {e}")
            return None

    def _files_identical(self, file1, file2):
        """Check if two files have identical content"""
        try:
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                return f1.read() == f2.read()
        except:
            return False

    def detect_orphan_files(self):
        """
        Find files in repository not tracked in database.

        Returns:
            list: List of (filename, full_path) tuples for orphan files
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all tracked file paths from database
        cursor.execute('SELECT file_path FROM programs')
        tracked_files = set(Path(row[0]).name.lower() for row in cursor.fetchall())

        conn.close()

        # Find orphans
        orphans = []
        for item in self.repository_path.iterdir():
            if item.is_file():
                if item.name.lower() not in tracked_files:
                    orphans.append((item.name, str(item)))

        return orphans

    def cleanup_orphans(self, action='archive', dry_run=False):
        """
        Handle orphan files (files not in database).

        Args:
            action: 'archive' or 'delete'
            dry_run: If True, only report what would be done

        Returns:
            dict: Statistics about cleanup
        """
        orphans = self.detect_orphan_files()

        if not orphans:
            print("[Cleanup] No orphan files found")
            return {'count': 0, 'action': action}

        print(f"[Cleanup] Found {len(orphans)} orphan files")

        if dry_run:
            print("[Cleanup] DRY RUN - would process:")
            for filename, path in orphans[:10]:
                print(f"  - {filename}")
            if len(orphans) > 10:
                print(f"  ... and {len(orphans) - 10} more")
            return {'count': len(orphans), 'action': action, 'dry_run': True}

        processed = 0
        errors = 0

        for filename, path in orphans:
            try:
                # Extract program number from filename
                prog_num = Path(path).stem.lower()

                if action == 'archive':
                    self.archive_old_file(path, prog_num, reason='orphan')
                    processed += 1
                elif action == 'delete':
                    os.remove(path)
                    print(f"[Cleanup] Deleted: {filename}")
                    processed += 1

            except Exception as e:
                print(f"[Cleanup] Error processing {filename}: {e}")
                errors += 1

        print(f"[Cleanup] Processed: {processed}, Errors: {errors}")
        return {'count': processed, 'errors': errors, 'action': action}

    def detect_duplicates(self):
        """
        Find program numbers with multiple files (different extensions/case).

        Returns:
            dict: {program_number: [list of file paths]}
        """
        file_groups = defaultdict(list)

        for item in self.repository_path.iterdir():
            if item.is_file():
                # Normalize to program number (remove extension, lowercase)
                prog_num = item.stem.lower()
                file_groups[prog_num].append(str(item))

        # Filter to only duplicates
        duplicates = {k: v for k, v in file_groups.items() if len(v) > 1}

        return duplicates

    def consolidate_duplicates(self, dry_run=False):
        """
        Consolidate duplicate files for same program number.
        Keeps the best file (priority: .nc extension, newest), archives others.

        Args:
            dry_run: If True, only report what would be done

        Returns:
            dict: Statistics about consolidation
        """
        duplicates = self.detect_duplicates()

        if not duplicates:
            print("[Consolidate] No duplicate files found")
            return {'count': 0}

        print(f"[Consolidate] Found {len(duplicates)} programs with multiple files")

        if dry_run:
            print("[Consolidate] DRY RUN - would process:")
            for prog_num, files in list(duplicates.items())[:10]:
                print(f"  {prog_num}: {len(files)} files")
                for f in files:
                    print(f"    - {Path(f).name}")
            return {'count': len(duplicates), 'dry_run': True}

        processed = 0
        errors = 0

        for prog_num, files in duplicates.items():
            try:
                # Choose best file to keep
                best_file = self._choose_best_file(files)

                print(f"[Consolidate] {prog_num}: Keeping {Path(best_file).name}")

                # Archive other files
                for file_path in files:
                    if file_path != best_file:
                        self.archive_old_file(file_path, prog_num, reason='consolidate')

                processed += 1

            except Exception as e:
                print(f"[Consolidate] Error processing {prog_num}: {e}")
                errors += 1

        print(f"[Consolidate] Processed: {processed}, Errors: {errors}")
        return {'count': processed, 'errors': errors}

    def _choose_best_file(self, files):
        """
        Choose the best file from a list of duplicates.

        Priority:
        1. .nc extension (standard)
        2. Newest modification time
        3. Largest file size

        Args:
            files: List of file paths

        Returns:
            str: Path to best file
        """
        files = [Path(f) for f in files]

        # Priority 1: Prefer .nc extension
        nc_files = [f for f in files if f.suffix.lower() == '.nc']
        if nc_files:
            files = nc_files

        # Priority 2: Newest file
        files_sorted = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)

        return str(files_sorted[0])

    def get_archive_stats(self):
        """
        Get statistics about archived files.

        Returns:
            dict: Archive statistics
        """
        if not self.archive_path.exists():
            return {'total_files': 0, 'total_size': 0, 'date_folders': 0}

        total_files = 0
        total_size = 0
        date_folders = []

        for date_folder in self.archive_path.iterdir():
            if date_folder.is_dir():
                date_folders.append(date_folder.name)

                for archived_file in date_folder.iterdir():
                    if archived_file.is_file():
                        total_files += 1
                        total_size += archived_file.stat().st_size

        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'date_folders': len(date_folders),
            'dates': sorted(date_folders, reverse=True)
        }

    def list_archived_versions(self, program_number):
        """
        List all archived versions of a program.

        Args:
            program_number: Program number

        Returns:
            list: List of (version, date, filepath, size) tuples
        """
        if not self.archive_path.exists():
            return []

        pattern = re.compile(rf'^{re.escape(program_number)}_(\d+)', re.IGNORECASE)
        versions = []

        for date_folder in self.archive_path.iterdir():
            if not date_folder.is_dir():
                continue

            for archived_file in date_folder.iterdir():
                match = pattern.match(archived_file.stem)
                if match:
                    version = int(match.group(1))
                    size = archived_file.stat().st_size
                    versions.append((version, date_folder.name, str(archived_file), size))

        # Sort by version descending (newest first)
        versions.sort(key=lambda x: x[0], reverse=True)
        return versions

    def restore_from_archive(self, archive_path, program_number, replace_current=False):
        """
        Restore a file from archive to repository.

        Args:
            archive_path: Path to archived file
            program_number: Program number
            replace_current: If True, replace current file (archive it first)

        Returns:
            str: Path to restored file in repository
        """
        archive_path = Path(archive_path)

        if not archive_path.exists():
            print(f"[Restore] Archive file not found: {archive_path}")
            return None

        # Destination in repository
        file_ext = archive_path.suffix if archive_path.suffix else '.nc'
        dest_path = self.repository_path / f"{program_number}{file_ext}"

        if dest_path.exists() and not replace_current:
            print(f"[Restore] File already exists in repository: {dest_path.name}")
            print(f"[Restore] Use replace_current=True to replace it")
            return None

        try:
            # If replacing, archive current version first
            if dest_path.exists() and replace_current:
                print(f"[Restore] Archiving current version before restore...")
                self.archive_old_file(dest_path, program_number, reason='restore_replace')

            # Copy from archive to repository
            shutil.copy2(str(archive_path), str(dest_path))
            print(f"[Restore] Restored: {archive_path.name} → {dest_path.name}")

            return str(dest_path)

        except Exception as e:
            print(f"[Restore] Error restoring file: {e}")
            return None

    def delete_old_archives(self, days=180, dry_run=False):
        """
        Delete archived files older than specified days.

        Args:
            days: Delete archives older than this many days
            dry_run: If True, only report what would be deleted

        Returns:
            dict: Statistics about deletion
        """
        if not self.archive_path.exists():
            return {'count': 0, 'size_mb': 0}

        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)

        deleted_count = 0
        deleted_size = 0

        for date_folder in self.archive_path.iterdir():
            if not date_folder.is_dir():
                continue

            # Check if folder is old enough
            if date_folder.stat().st_mtime < cutoff_date:
                folder_size = sum(f.stat().st_size for f in date_folder.iterdir() if f.is_file())
                file_count = sum(1 for f in date_folder.iterdir() if f.is_file())

                if dry_run:
                    print(f"[Delete] Would delete: {date_folder.name} ({file_count} files, {folder_size / 1024 / 1024:.2f} MB)")
                else:
                    shutil.rmtree(date_folder)
                    print(f"[Delete] Deleted: {date_folder.name} ({file_count} files, {folder_size / 1024 / 1024:.2f} MB)")

                deleted_count += file_count
                deleted_size += folder_size

        return {
            'count': deleted_count,
            'size_mb': round(deleted_size / 1024 / 1024, 2),
            'dry_run': dry_run
        }


if __name__ == '__main__':
    # Example usage
    manager = RepositoryManager(
        'gcode_database.db',
        'repository'
    )

    print("=== Repository Manager ===")
    print()

    # Get statistics
    stats = manager.get_archive_stats()
    print(f"Archive Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    print(f"  Date folders: {stats['date_folders']}")
    print()

    # Detect orphans (dry run)
    print("Detecting orphan files...")
    orphans = manager.detect_orphan_files()
    print(f"Found {len(orphans)} orphan files")
    print()

    # Detect duplicates (dry run)
    print("Detecting duplicate files...")
    duplicates = manager.detect_duplicates()
    print(f"Found {len(duplicates)} programs with multiple files")
