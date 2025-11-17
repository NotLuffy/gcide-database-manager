"""
Fix database schema - Move thickness_display to correct position (index 4)
"""
import sqlite3
import os
from datetime import datetime

db_path = "gcode_database.db"
backup_path = f"gcode_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

print(f"Creating backup: {backup_path}")
os.system(f'copy "{db_path}" "{backup_path}"')

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\nCreating new table with correct column order...")

# Create new table with correct schema
cursor.execute('''
    CREATE TABLE IF NOT EXISTS programs_new (
        program_number TEXT PRIMARY KEY,
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

print("Copying data from old table to new table...")

# Copy data with correct column mapping
cursor.execute('''
    INSERT INTO programs_new
    SELECT
        program_number,
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

print("Dropping old table...")
cursor.execute('DROP TABLE programs')

print("Renaming new table to 'programs'...")
cursor.execute('ALTER TABLE programs_new RENAME TO programs')

conn.commit()
conn.close()

print("\n✅ Database schema fixed!")
print(f"Backup saved to: {backup_path}")
print("\nVerifying new schema...")

# Verify
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(programs)')
columns = cursor.fetchall()
print("\nNew column order:")
for i, col in enumerate(columns):
    print(f"  {i}: {col[1]} ({col[2]})")
conn.close()

print("\n✅ Done! You can now run the GUI.")
