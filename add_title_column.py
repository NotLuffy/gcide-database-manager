"""
Add 'title' column to database to store G-code title from ()
"""
import sqlite3
from datetime import datetime

db_path = "gcode_database.db"
backup_path = f"gcode_database_backup_title_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

print(f"Creating backup: {backup_path}")
import os
os.system(f'copy "{db_path}" "{backup_path}"')

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\nChecking if 'title' column already exists...")
cursor.execute('PRAGMA table_info(programs)')
columns = [col[1] for col in cursor.fetchall()]

if 'title' in columns:
    print("'title' column already exists!")
else:
    print("Adding 'title' column after 'program_number'...")

    # SQLite doesn't support adding columns at specific positions
    # We need to create a new table with the column in the right place

    # Create new table with title column
    cursor.execute('''
        CREATE TABLE programs_new (
            program_number TEXT PRIMARY KEY,
            title TEXT,
            spacer_type TEXT NOT NULL,
            outer_diameter REAL,
            thickness REAL,
            thickness_display TEXT,
            center_bore REAL,
            hub_height REAL,
            hub_diameter REAL,
            counter_bore_diameter REAL,
            counter_bore_depth REAL,
            paired_program TEXT,
            material TEXT,
            notes TEXT,
            date_created TEXT,
            last_modified TEXT,
            file_path TEXT,
            detection_confidence TEXT,
            detection_method TEXT,
            validation_status TEXT,
            validation_issues TEXT,
            validation_warnings TEXT,
            cb_from_gcode REAL,
            ob_from_gcode REAL,
            bore_warnings TEXT,
            dimensional_issues TEXT
        )
    ''')

    # Copy data from old table
    print("Copying data from old table...")
    cursor.execute('''
        INSERT INTO programs_new
        SELECT
            program_number,
            NULL as title,
            spacer_type,
            outer_diameter,
            thickness,
            thickness_display,
            center_bore,
            hub_height,
            hub_diameter,
            counter_bore_diameter,
            counter_bore_depth,
            paired_program,
            material,
            notes,
            date_created,
            last_modified,
            file_path,
            detection_confidence,
            detection_method,
            validation_status,
            validation_issues,
            validation_warnings,
            cb_from_gcode,
            ob_from_gcode,
            bore_warnings,
            dimensional_issues
        FROM programs
    ''')

    # Drop old table and rename new one
    print("Replacing old table...")
    cursor.execute('DROP TABLE programs')
    cursor.execute('ALTER TABLE programs_new RENAME TO programs')

    conn.commit()
    print("Done! 'title' column added at index 1")

# Verify
cursor.execute('PRAGMA table_info(programs)')
columns = cursor.fetchall()
print("\nNew column order:")
for i, col in enumerate(columns[:5]):
    print(f"  {i}: {col[1]}")
print("  ...")

conn.close()

print(f"\nBackup saved to: {backup_path}")
print("Run the GUI and rescan to populate title column!")
