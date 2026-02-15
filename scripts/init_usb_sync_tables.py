"""
Initialize USB Sync Manager database tables

This script creates the three USB sync tables:
- usb_sync_tracking
- usb_drives
- sync_history

And their associated indexes.
"""

import sqlite3
import os

# Database path
db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

print("="*70)
print("  USB SYNC MANAGER - Database Initialization")
print("="*70)

# Connect to database
conn = sqlite3.connect(db_path, timeout=30.0)
cursor = conn.cursor()

# Enable WAL mode for better concurrent access
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA busy_timeout=30000")

print("\nCreating USB Sync tables...")

# USB Sync Tracking - sync status for each program on each drive
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usb_sync_tracking (
        sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_label TEXT NOT NULL,
        drive_path TEXT NOT NULL,
        program_number TEXT NOT NULL,
        last_sync_date TEXT,
        last_sync_direction TEXT,
        repo_hash TEXT,
        usb_hash TEXT,
        repo_modified TEXT,
        usb_modified TEXT,
        sync_status TEXT,
        notes TEXT,
        UNIQUE(drive_label, program_number)
    )
''')
print("  [+] usb_sync_tracking")

# USB Drives - registered drives and their metadata
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usb_drives (
        drive_id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_label TEXT UNIQUE NOT NULL,
        drive_serial TEXT,
        last_seen_path TEXT,
        last_scan_date TEXT,
        total_programs INTEGER DEFAULT 0,
        in_sync_count INTEGER DEFAULT 0,
        notes TEXT
    )
''')
print("  [+] usb_drives")

# Sync History - audit trail of all sync operations
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sync_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_date TEXT NOT NULL,
        drive_label TEXT NOT NULL,
        program_number TEXT NOT NULL,
        action TEXT NOT NULL,
        username TEXT,
        files_affected INTEGER DEFAULT 1,
        repo_hash_before TEXT,
        repo_hash_after TEXT,
        details TEXT
    )
''')
print("  [+] sync_history")

print("\nCreating indexes...")

# USB Sync indexes for performance
cursor.execute('CREATE INDEX IF NOT EXISTS idx_usb_sync_drive ON usb_sync_tracking(drive_label)')
print("  [+] idx_usb_sync_drive")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_usb_sync_program ON usb_sync_tracking(program_number)')
print("  [+] idx_usb_sync_program")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_usb_sync_status ON usb_sync_tracking(sync_status)')
print("  [+] idx_usb_sync_status")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_usb_sync_composite ON usb_sync_tracking(drive_label, sync_status)')
print("  [+] idx_usb_sync_composite")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_history_drive ON sync_history(drive_label, sync_date DESC)')
print("  [+] idx_sync_history_drive")

cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_history_program ON sync_history(program_number, sync_date DESC)')
print("  [+] idx_sync_history_program")

# Commit changes
conn.commit()

# Verify tables created
cursor.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table'
    AND (name LIKE 'usb_%' OR name LIKE 'sync_%')
    ORDER BY name
""")

tables = cursor.fetchall()
print("\n" + "="*70)
print("Verification:")
print("="*70)
print(f"\nTables created: {len(tables)}")
for table in tables:
    print(f"  * {table[0]}")

# Check indexes
cursor.execute("""
    SELECT name FROM sqlite_master
    WHERE type='index'
    AND (name LIKE 'idx_usb_%' OR name LIKE 'idx_sync_%')
    ORDER BY name
""")

indexes = cursor.fetchall()
print(f"\nIndexes created: {len(indexes)}")
for index in indexes:
    print(f"  * {index[0]}")

conn.close()

print("\n" + "="*70)
print("USB Sync Manager database initialization complete!")
print("="*70)
print("\nYou can now proceed to Phase 2: Core Module (usb_sync_manager.py)")
