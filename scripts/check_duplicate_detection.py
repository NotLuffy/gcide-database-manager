"""
Diagnostic: Check why files aren't being imported
Helps identify if files are being detected as duplicates or missing
"""

import sqlite3
import os
import hashlib
import sys

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        return f"ERROR: {e}"

def check_files_in_folder(folder_path, db_path):
    """Check which files are already in database and why"""

    # Connect to database
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    # Get all files from database
    cursor.execute("""
        SELECT program_number, file_path, content_hash
        FROM programs
        WHERE file_path IS NOT NULL
    """)
    db_files = cursor.fetchall()

    # Create lookup dictionaries
    by_filename = {}  # filename_lower -> [(prog_num, file_path, hash)]
    by_hash = {}      # hash -> [(prog_num, file_path)]

    for prog_num, file_path, content_hash in db_files:
        if file_path:
            filename = os.path.basename(file_path).lower()
            if filename not in by_filename:
                by_filename[filename] = []
            by_filename[filename].append((prog_num, file_path, content_hash))

        if content_hash:
            if content_hash not in by_hash:
                by_hash[content_hash] = []
            by_hash[content_hash].append((prog_num, file_path))

    # Scan folder for G-code files
    import re
    files_to_check = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if re.search(r'[oO]\d{4,}', file):
                files_to_check.append(os.path.join(root, file))

    print("="*70)
    print(f"DUPLICATE DETECTION ANALYSIS")
    print("="*70)
    print(f"\nFolder: {folder_path}")
    print(f"Files found: {len(files_to_check)}")
    print(f"Database programs: {len(db_files)}")
    print()

    # Analyze each file
    new_files = []
    exact_duplicates = []
    name_collisions = []

    for filepath in files_to_check:
        filename = os.path.basename(filepath)
        filename_lower = filename.lower()

        print("-"*70)
        print(f"File: {filename}")
        print(f"Path: {filepath}")

        # Check by filename
        if filename_lower in by_filename:
            print(f"  OK Filename exists in database")

            # Calculate hash for this file
            file_hash = calculate_file_hash(filepath)
            print(f"  Hash: {file_hash[:16]}...")

            # Check if exact match
            db_entries = by_filename[filename_lower]
            exact_match = False

            for prog_num, db_path, db_hash in db_entries:
                print(f"    DB Entry: {prog_num} -> {db_path}")
                if db_hash:
                    print(f"      DB Hash: {db_hash[:16]}...")
                    if db_hash == file_hash:
                        exact_match = True
                        print(f"      WARNING  EXACT DUPLICATE (same hash)")
                        exact_duplicates.append((filepath, prog_num, db_path))
                        break
                else:
                    print(f"      DB Hash: (none in database)")

            if not exact_match:
                print(f"    WARNING  NAME COLLISION (different content)")
                name_collisions.append((filepath, db_entries[0][1]))
        else:
            print(f"  OK New filename (not in database)")

            # Still check hash in case file was renamed
            file_hash = calculate_file_hash(filepath)
            print(f"  Hash: {file_hash[:16]}...")

            if file_hash in by_hash:
                print(f"    WARNING  HASH MATCH - file exists under different name!")
                for prog_num, db_path in by_hash[file_hash]:
                    print(f"      DB Entry: {prog_num} -> {db_path}")
                exact_duplicates.append((filepath, prog_num, db_path))
            else:
                print(f"    OK NEW FILE (can be imported)")
                new_files.append(filepath)

    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"New files (can be imported): {len(new_files)}")
    print(f"Exact duplicates (will be skipped): {len(exact_duplicates)}")
    print(f"Name collisions (need renaming): {len(name_collisions)}")
    print()

    if new_files:
        print("NEW FILES:")
        for f in new_files:
            print(f"  OK {os.path.basename(f)}")
        print()

    if exact_duplicates:
        print("EXACT DUPLICATES (already in database):")
        for new_path, prog_num, db_path in exact_duplicates:
            print(f"  WARNING  {os.path.basename(new_path)}")
            print(f"     Program: {prog_num}")
            print(f"     DB Path: {db_path}")
        print()

    if name_collisions:
        print("NAME COLLISIONS (same name, different content - need renaming):")
        for new_path, db_path in name_collisions:
            print(f"  WARNING  {os.path.basename(new_path)}")
            print(f"     New: {new_path}")
            print(f"     Existing: {db_path}")
        print()

    conn.close()

    return {
        'new': len(new_files),
        'duplicates': len(exact_duplicates),
        'collisions': len(name_collisions)
    }

if __name__ == "__main__":
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = input("Enter folder path to check (e.g., F:\\): ").strip()

    if not os.path.exists(folder_path):
        print(f"ERROR: Folder does not exist: {folder_path}")
        sys.exit(1)

    results = check_files_in_folder(folder_path, db_path)

    print()
    print("="*70)
    if results['new'] == 0:
        print("WARNING: NO NEW FILES TO IMPORT")
        print()
        if results['duplicates'] > 0:
            print("All files are already in the database (exact duplicates).")
            print("This is normal if you've already imported these files before.")
        if results['collisions'] > 0:
            print("Some files have name collisions and need to be renamed before importing.")
    else:
        print(f"OK: {results['new']} files ready to import")
    print("="*70)
