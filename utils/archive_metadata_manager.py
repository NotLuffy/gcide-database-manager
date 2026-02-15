"""
Archive Metadata Manager
Manages metadata tracking for archived program versions.

Part of Phase 3: Version History & Archive Improvements
"""

import os
import sqlite3
import hashlib
import glob
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, Callable
from improved_gcode_parser import ImprovedGCodeParser


class ArchiveMetadataExtractor:
    """Utility class for extracting metadata from archive files"""

    @staticmethod
    def extract_from_filename(filename: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Parse program number and version from filename.

        Args:
            filename: Archive filename (e.g., 'o57508_5.nc')

        Returns:
            Tuple of (program_number, version_number) or (None, None)
        """
        match = re.match(r'(o\d+)_(\d+)\.', filename, re.IGNORECASE)
        if match:
            return match.group(1).lower(), int(match.group(2))
        return None, None

    @staticmethod
    def extract_dimensions(file_path: str) -> Dict[str, Optional[float]]:
        """
        Extract dimensions from G-code file.

        Args:
            file_path: Path to G-code file

        Returns:
            Dictionary with outer_diameter, thickness, center_bore
        """
        try:
            parser = ImprovedGCodeParser()
            result = parser.parse_file(file_path)
            return {
                'outer_diameter': result.outer_diameter,
                'thickness': result.thickness,
                'center_bore': result.center_bore
            }
        except Exception as e:
            print(f"Warning: Failed to extract dimensions from {file_path}: {e}")
            return {
                'outer_diameter': None,
                'thickness': None,
                'center_bore': None
            }


class ArchiveMetadataManager:
    """Manages metadata for archived program versions"""

    def __init__(self, db_path: str, archive_path: str):
        """
        Initialize manager.

        Args:
            db_path: Path to SQLite database
            archive_path: Path to archive directory
        """
        self.db_path = db_path
        self.archive_path = archive_path

    def add_metadata(self, program_number: str, version: int, file_path: str,
                    metadata: Dict) -> bool:
        """
        Insert or update metadata for an archived version.

        Args:
            program_number: Program number (e.g., 'o57508')
            version: Version number
            file_path: Path to archived file
            metadata: Dictionary containing metadata fields:
                - date_archived: ISO date string
                - archived_by: Username
                - archive_reason: Reason for archiving (optional)
                - change_summary: Summary of changes (optional)
                - file_size: File size in bytes
                - file_hash: SHA256 hash of file
                - metadata_source: 'full', 'extracted', or 'inferred'
                - metadata_confidence: Integer 0-100
                - outer_diameter: Float (optional)
                - thickness: Float (optional)
                - center_bore: Float (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO archive_metadata
                (program_number, version_number, file_path, date_archived,
                 archived_by, archive_reason, change_summary, file_size, file_hash,
                 metadata_source, metadata_confidence, outer_diameter, thickness, center_bore)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                program_number.lower(),
                version,
                file_path,
                metadata.get('date_archived'),
                metadata.get('archived_by'),
                metadata.get('archive_reason'),
                metadata.get('change_summary'),
                metadata.get('file_size'),
                metadata.get('file_hash'),
                metadata.get('metadata_source', 'extracted'),
                metadata.get('metadata_confidence', 60),
                metadata.get('outer_diameter'),
                metadata.get('thickness'),
                metadata.get('center_bore')
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error adding metadata for {program_number} v{version}: {e}")
            return False

    def bulk_scan_archives(self, progress_callback: Optional[Callable[[int], None]] = None) -> int:
        """
        Scan all archive folders and populate metadata for existing archives.

        Args:
            progress_callback: Optional callback function called with file count

        Returns:
            Total number of files processed
        """
        total_files = 0
        errors = 0

        # Find all date folders in archive directory
        date_folders = glob.glob(os.path.join(self.archive_path, '*'))

        for date_folder in date_folders:
            if not os.path.isdir(date_folder):
                continue

            # Extract date from folder name (YYYY-MM-DD format)
            folder_name = os.path.basename(date_folder)

            # Find all archive files in this date folder
            archive_files = glob.glob(os.path.join(date_folder, '*'))

            for archive_file in archive_files:
                if not os.path.isfile(archive_file):
                    continue

                # Skip already compressed files for now
                if archive_file.endswith('.gz'):
                    continue

                # Extract program number and version from filename
                filename = os.path.basename(archive_file)
                program_num, version = ArchiveMetadataExtractor.extract_from_filename(filename)

                if not program_num or version is None:
                    print(f"Warning: Could not parse filename: {filename}")
                    errors += 1
                    continue

                # Calculate file hash
                try:
                    with open(archive_file, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                except Exception as e:
                    print(f"Warning: Could not read file {archive_file}: {e}")
                    errors += 1
                    continue

                # Extract dimensions
                dims = ArchiveMetadataExtractor.extract_dimensions(archive_file)

                # Store metadata
                metadata = {
                    'date_archived': folder_name,  # Use folder name as date
                    'archived_by': None,  # Unknown for existing archives
                    'archive_reason': None,
                    'change_summary': None,
                    'file_size': os.path.getsize(archive_file),
                    'file_hash': file_hash,
                    'metadata_source': 'extracted',
                    'metadata_confidence': 60,  # Medium confidence for extracted data
                    'outer_diameter': dims.get('outer_diameter'),
                    'thickness': dims.get('thickness'),
                    'center_bore': dims.get('center_bore')
                }

                if self.add_metadata(program_num, version, archive_file, metadata):
                    total_files += 1

                    # Call progress callback every 50 files
                    if progress_callback and total_files % 50 == 0:
                        progress_callback(total_files)
                else:
                    errors += 1

        # Final progress callback
        if progress_callback:
            progress_callback(total_files)

        if errors > 0:
            print(f"Completed with {errors} errors")

        return total_files

    def get_metadata(self, program_number: str, version: int) -> Optional[Dict]:
        """
        Get metadata for a specific archived version.

        Args:
            program_number: Program number
            version: Version number

        Returns:
            Dictionary with metadata or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT archive_id, file_path, date_archived, archived_by,
                       archive_reason, change_summary, file_size, file_hash,
                       is_compressed, compressed_date, outer_diameter, thickness,
                       center_bore, metadata_source, metadata_confidence
                FROM archive_metadata
                WHERE program_number = ? AND version_number = ?
            """, (program_number.lower(), version))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'archive_id': row[0],
                    'file_path': row[1],
                    'date_archived': row[2],
                    'archived_by': row[3],
                    'archive_reason': row[4],
                    'change_summary': row[5],
                    'file_size': row[6],
                    'file_hash': row[7],
                    'is_compressed': bool(row[8]),
                    'compressed_date': row[9],
                    'outer_diameter': row[10],
                    'thickness': row[11],
                    'center_bore': row[12],
                    'metadata_source': row[13],
                    'metadata_confidence': row[14]
                }

            return None

        except Exception as e:
            print(f"Error getting metadata for {program_number} v{version}: {e}")
            return None


class ChangeDetector:
    """Utility class for detecting changes between versions"""

    @staticmethod
    def detect_dimensional_changes(file1: str, file2: str) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
        """
        Compare dimensions between two versions.

        Args:
            file1: Path to first version
            file2: Path to second version

        Returns:
            Dictionary of changed dimensions with (old_value, new_value) tuples
        """
        dims1 = ArchiveMetadataExtractor.extract_dimensions(file1)
        dims2 = ArchiveMetadataExtractor.extract_dimensions(file2)

        changes = {}
        for key in dims1.keys():
            val1 = dims1.get(key)
            val2 = dims2.get(key)

            # Compare values (handle None values)
            if val1 != val2:
                # Only report if at least one value is not None
                if val1 is not None or val2 is not None:
                    changes[key] = (val1, val2)

        return changes

    @staticmethod
    def has_dimensional_changes(file1: str, file2: str) -> bool:
        """
        Check if there are any dimensional changes between versions.

        Args:
            file1: Path to first version
            file2: Path to second version

        Returns:
            True if dimensions changed, False otherwise
        """
        changes = ChangeDetector.detect_dimensional_changes(file1, file2)
        return len(changes) > 0
