"""
Archive Cleanup Manager
Handles compression and cleanup of archived program versions.

Part of Phase 3: Version History & Archive Improvements
"""

import os
import gzip
import shutil
import sqlite3
import hashlib
import tempfile
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


class ArchiveCleanupManager:
    """Manages compression and cleanup of archive files"""

    def __init__(self, db_path: str, archive_path: str):
        """
        Initialize cleanup manager.

        Args:
            db_path: Path to SQLite database
            archive_path: Path to archive directory
        """
        self.db_path = db_path
        self.archive_path = archive_path

    def get_compression_candidates(self, days_threshold: int = 90) -> List[Tuple[int, str, int]]:
        """
        Find archives older than threshold that are eligible for compression.
        Version 1 files are always protected from compression.

        Args:
            days_threshold: Number of days old before eligible for compression

        Returns:
            List of tuples: (archive_id, file_path, version_number)
        """
        cutoff_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT archive_id, file_path, version_number
                FROM archive_metadata
                WHERE date_archived < ?
                  AND is_compressed = 0
                  AND version_number != 1
                  AND file_path IS NOT NULL
                ORDER BY date_archived ASC
            """, (cutoff_date,))

            candidates = cursor.fetchall()
            conn.close()

            # Filter out files that don't exist or are already .gz
            valid_candidates = []
            for archive_id, file_path, version_number in candidates:
                if file_path and os.path.exists(file_path) and not file_path.endswith('.gz'):
                    valid_candidates.append((archive_id, file_path, version_number))

            return valid_candidates

        except Exception as e:
            print(f"Error getting compression candidates: {e}")
            return []

    def compress_file(self, file_path: str) -> str:
        """
        Compress file using gzip and verify integrity.

        Args:
            file_path: Path to file to compress

        Returns:
            Path to compressed file

        Raises:
            Exception: If compression fails or verification fails
        """
        compressed_path = f"{file_path}.gz"

        # Read original file and calculate hash
        with open(file_path, 'rb') as f_in:
            original_data = f_in.read()
            original_hash = hashlib.sha256(original_data).hexdigest()

        # Compress file
        with gzip.open(compressed_path, 'wb', compresslevel=6) as f_out:
            f_out.write(original_data)

        # Verify compressed file
        if not self.verify_compressed(compressed_path, original_hash):
            # Clean up failed compression
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
            raise Exception("Compression verification failed")

        # Delete original file only after successful verification
        os.remove(file_path)

        return compressed_path

    def verify_compressed(self, compressed_path: str, original_hash: str) -> bool:
        """
        Verify that compressed file matches original.

        Args:
            compressed_path: Path to compressed file
            original_hash: SHA256 hash of original file

        Returns:
            True if compressed file decompresses to match original hash
        """
        try:
            with gzip.open(compressed_path, 'rb') as f:
                decompressed_data = f.read()
                decompressed_hash = hashlib.sha256(decompressed_data).hexdigest()

            return decompressed_hash == original_hash

        except Exception as e:
            print(f"Error verifying compressed file: {e}")
            return False

    def decompress_for_viewing(self, compressed_path: str) -> str:
        """
        Decompress file to temporary location for viewing.

        Args:
            compressed_path: Path to compressed (.gz) file

        Returns:
            Path to temporary decompressed file
        """
        # Create temp file with appropriate extension
        file_ext = os.path.splitext(os.path.splitext(compressed_path)[0])[1]
        if not file_ext:
            file_ext = '.nc'

        temp_fd, temp_path = tempfile.mkstemp(suffix=file_ext)
        os.close(temp_fd)

        try:
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            return temp_path

        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Failed to decompress file: {e}")

    def compress_old_archives(self, days_threshold: int = 90,
                             dry_run: bool = True) -> Tuple[int, int, List[str]]:
        """
        Compress archives older than threshold.

        Args:
            days_threshold: Number of days old before eligible
            dry_run: If True, only report what would be compressed without actually doing it

        Returns:
            Tuple of (compressed_count, error_count, error_messages)
        """
        candidates = self.get_compression_candidates(days_threshold)

        if not candidates:
            return (0, 0, [])

        compressed_count = 0
        error_count = 0
        error_messages = []

        print(f"[Compression] Found {len(candidates)} files eligible for compression")

        for archive_id, file_path, version_number in candidates:
            if dry_run:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                size_mb = file_size / (1024 * 1024)
                print(f"[Dry Run] Would compress: {os.path.basename(file_path)} ({size_mb:.2f} MB)")
                compressed_count += 1
                continue

            try:
                # Compress the file
                compressed_path = self.compress_file(file_path)

                # Update metadata in database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE archive_metadata
                    SET is_compressed = 1,
                        compressed_date = ?,
                        file_path = ?
                    WHERE archive_id = ?
                """, (datetime.now().isoformat(), compressed_path, archive_id))

                conn.commit()
                conn.close()

                # Get compression ratio
                original_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                compressed_size = os.path.getsize(compressed_path)
                if original_size > 0:
                    ratio = (1 - compressed_size / original_size) * 100
                    print(f"[Compression] {os.path.basename(file_path)} → {os.path.basename(compressed_path)} (saved {ratio:.1f}%)")
                else:
                    print(f"[Compression] {os.path.basename(file_path)} → {os.path.basename(compressed_path)}")

                compressed_count += 1

            except Exception as e:
                error_msg = f"Failed to compress {os.path.basename(file_path)}: {e}"
                print(f"[Compression Error] {error_msg}")
                error_messages.append(error_msg)
                error_count += 1

        return (compressed_count, error_count, error_messages)

    def get_compression_statistics(self) -> dict:
        """
        Get statistics about archive compression.

        Returns:
            Dictionary with compression statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total archives
            cursor.execute("SELECT COUNT(*) FROM archive_metadata")
            total_archives = cursor.fetchone()[0]

            # Compressed archives
            cursor.execute("SELECT COUNT(*) FROM archive_metadata WHERE is_compressed = 1")
            compressed_count = cursor.fetchone()[0]

            # Uncompressed archives
            cursor.execute("SELECT COUNT(*) FROM archive_metadata WHERE is_compressed = 0")
            uncompressed_count = cursor.fetchone()[0]

            # Total size of uncompressed files
            cursor.execute("SELECT SUM(file_size) FROM archive_metadata WHERE is_compressed = 0")
            result = cursor.fetchone()
            uncompressed_size = result[0] if result[0] else 0

            # Version 1 files (protected from compression)
            cursor.execute("SELECT COUNT(*) FROM archive_metadata WHERE version_number = 1")
            v1_count = cursor.fetchone()[0]

            conn.close()

            return {
                'total_archives': total_archives,
                'compressed': compressed_count,
                'uncompressed': uncompressed_count,
                'uncompressed_size_bytes': uncompressed_size,
                'uncompressed_size_mb': uncompressed_size / (1024 * 1024),
                'version_1_protected': v1_count,
                'compression_ratio': (compressed_count / total_archives * 100) if total_archives > 0 else 0
            }

        except Exception as e:
            print(f"Error getting compression statistics: {e}")
            return {
                'total_archives': 0,
                'compressed': 0,
                'uncompressed': 0,
                'uncompressed_size_bytes': 0,
                'uncompressed_size_mb': 0,
                'version_1_protected': 0,
                'compression_ratio': 0
            }
