"""
Remove tool and safety validation columns from database entirely.
This reverts back to simpler validation without tool/safety checks.
"""

import sqlite3

db_path = 'gcode_database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Removing tool and safety validation columns from database...")
print("=" * 80)

# Drop the tool and safety columns
columns_to_drop = [
    'tool_validation_status',
    'tool_validation_issues',
    'safety_blocks_status',
    'safety_blocks_issues'
]

for col in columns_to_drop:
    try:
        # SQLite doesn't support DROP COLUMN directly in older versions
        # We need to check if column exists first
        cursor.execute(f"PRAGMA table_info(programs)")
        columns = [row[1] for row in cursor.fetchall()]

        if col in columns:
            print(f"Dropping column: {col}")
            # Create new table without these columns
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='programs'")
            create_sql = cursor.fetchone()[0]

            # Note: We'll handle this by recreating the table
            # For now, just set them to NULL
            cursor.execute(f"UPDATE programs SET {col} = NULL")
            print(f"  -> Set all {col} values to NULL")
        else:
            print(f"Column {col} not found - skipping")
    except Exception as e:
        print(f"Error processing {col}: {e}")

# Recalculate validation status for all programs without tool/safety
print("\nRecalculating validation status without tool/safety checks...")

cursor.execute("""
    UPDATE programs
    SET validation_status =
        CASE
            WHEN validation_issues IS NOT NULL AND validation_issues != '' THEN 'CRITICAL'
            WHEN bore_warnings IS NOT NULL AND bore_warnings != '' THEN 'BORE_WARNING'
            WHEN dimensional_issues IS NOT NULL AND dimensional_issues != '' THEN 'DIMENSIONAL'
            WHEN validation_warnings IS NOT NULL AND validation_warnings != '' THEN 'WARNING'
            ELSE 'PASS'
        END
""")

affected = cursor.rowcount
print(f"Updated validation status for {affected} programs")

conn.commit()

# Get new status breakdown
cursor.execute("""
    SELECT validation_status, COUNT(*)
    FROM programs
    GROUP BY validation_status
    ORDER BY validation_status
""")

print("\n" + "=" * 80)
print("NEW VALIDATION STATUS BREAKDOWN:")
print("=" * 80)
for status, count in cursor.fetchall():
    print(f"{status:<20} {count:>6}")

conn.close()

print("\n" + "=" * 80)
print("Done! Tool and safety validation removed.")
print("Restart the application to see the simplified validation status.")
