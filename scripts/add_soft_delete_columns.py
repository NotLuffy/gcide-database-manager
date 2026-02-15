"""
Add soft-delete functionality to programs table.

Adds is_deleted and deleted_date columns to support soft-delete pattern.
This allows keeping deleted records accessible for restore instead of permanent deletion.

Author: G-Code Database Manager
Date: 2026-02-08
"""

import sqlite3
import os
from datetime import datetime

def add_soft_delete_columns(db_path: str):
    """
    Add is_deleted and deleted_date columns to programs table if they don't exist.

    Args:
        db_path: Path to SQLite database
    """
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(programs)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        print(f"Current columns in programs table: {len(column_names)}")

        # Check if columns already exist
        has_is_deleted = 'is_deleted' in column_names
        has_deleted_date = 'deleted_date' in column_names

        if has_is_deleted and has_deleted_date:
            print("[OK] Soft-delete columns already exist")
            return True

        # Add is_deleted column
        if not has_is_deleted:
            print("Adding is_deleted column...")
            cursor.execute("""
                ALTER TABLE programs
                ADD COLUMN is_deleted INTEGER DEFAULT 0
            """)
            print("[OK] Added is_deleted column")
        else:
            print("[OK] is_deleted column already exists")

        # Add deleted_date column
        if not has_deleted_date:
            print("Adding deleted_date column...")
            cursor.execute("""
                ALTER TABLE programs
                ADD COLUMN deleted_date TEXT
            """)
            print("[OK] Added deleted_date column")
        else:
            print("[OK] deleted_date column already exists")

        conn.commit()
        print("\n[OK] Soft-delete columns successfully added to programs table")
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def find_stale_records(db_path: str, repository_path: str):
    """
    Find records where file_path points to non-existent file.

    Args:
        db_path: Path to SQLite database
        repository_path: Path to repository folder

    Returns:
        List of (program_number, file_path) tuples
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    try:
        # Get all records with file paths
        cursor.execute("""
            SELECT program_number, file_path
            FROM programs
            WHERE file_path IS NOT NULL
            AND (is_deleted IS NULL OR is_deleted = 0)
        """)

        all_records = cursor.fetchall()
        stale_records = []

        for program_number, file_path in all_records:
            if not os.path.exists(file_path):
                stale_records.append((program_number, file_path))

        return stale_records

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return []

    finally:
        conn.close()


def soft_delete_stale_records(db_path: str, repository_path: str):
    """
    Mark records with non-existent files as deleted.

    Args:
        db_path: Path to SQLite database
        repository_path: Path to repository folder

    Returns:
        Number of records marked as deleted
    """
    # First find stale records
    stale_records = find_stale_records(db_path, repository_path)

    if not stale_records:
        print("[OK] No stale records found - all file paths are valid")
        return 0

    print(f"\nFound {len(stale_records)} stale records (files no longer exist):")
    for program_number, file_path in stale_records[:10]:  # Show first 10
        print(f"  - {program_number}: {file_path}")

    if len(stale_records) > 10:
        print(f"  ... and {len(stale_records) - 10} more")

    # Soft-delete them
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    try:
        deleted_count = 0
        current_time = datetime.now().isoformat()

        for program_number, file_path in stale_records:
            cursor.execute("""
                UPDATE programs
                SET is_deleted = 1,
                    deleted_date = ?
                WHERE program_number = ?
            """, (current_time, program_number))
            deleted_count += 1

        conn.commit()
        print(f"\n[OK] Successfully marked {deleted_count} records as deleted")
        print(f"  These records are now hidden from normal views but can be restored")
        return deleted_count

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        conn.rollback()
        return 0

    finally:
        conn.close()


def main():
    """Main entry point"""
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    repository_path = r"l:\My Drive\Home\File organizer\repository"

    print("=" * 80)
    print("SOFT-DELETE SETUP - Add columns and mark stale records")
    print("=" * 80)
    print()

    # Step 1: Add columns
    print("STEP 1: Add soft-delete columns to database")
    print("-" * 80)
    success = add_soft_delete_columns(db_path)

    if not success:
        print("\n[ERROR] Failed to add columns - aborting")
        return

    print()

    # Step 2: Find and soft-delete stale records
    print("STEP 2: Find and mark stale records (files no longer exist)")
    print("-" * 80)
    deleted_count = soft_delete_stale_records(db_path, repository_path)

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"[OK] Soft-delete columns: Added to programs table")
    print(f"[OK] Stale records marked: {deleted_count} records")
    print()
    print("Next steps:")
    print("  1. Update queries to exclude deleted records (WHERE is_deleted=0)")
    print("  2. Create 'View Archived/Deleted Files' browser with restore function")
    print("=" * 80)


if __name__ == "__main__":
    main()
