import sqlite3
import json

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("VERIFICATION: FILENAME MISMATCH WARNINGS")
print("=" * 80)
print()

# Count files with filename mismatch warnings
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE is_managed = 1
      AND validation_status = 'CRITICAL'
      AND validation_issues LIKE '%FILENAME MISMATCH%'
""")

count = cursor.fetchone()[0]

print(f"Files with FILENAME MISMATCH warnings: {count}")
print()

if count > 0:
    # Show the files
    cursor.execute("""
        SELECT program_number, title, file_path, validation_issues
        FROM programs
        WHERE is_managed = 1
          AND validation_status = 'CRITICAL'
          AND validation_issues LIKE '%FILENAME MISMATCH%'
        ORDER BY program_number
    """)

    results = cursor.fetchall()

    print("=" * 80)
    print("REMAINING FILENAME MISMATCH WARNINGS (True Mismatches)")
    print("=" * 80)
    print()

    for prog_num, title, file_path, validation_issues_str in results:
        try:
            issues = json.loads(validation_issues_str)
            for issue in issues:
                if 'FILENAME MISMATCH' in issue:
                    print(f"{prog_num}:")
                    print(f"  Title: {title[:60]}")
                    print(f"  Warning: {issue}")
                    print()
        except:
            print(f"{prog_num}: {validation_issues_str}")
            print()
else:
    print("[OK] No filename mismatch warnings remaining!")

# Count validation statuses
print()
print("=" * 80)
print("VALIDATION STATUS BREAKDOWN")
print("=" * 80)

cursor.execute("""
    SELECT validation_status, COUNT(*)
    FROM programs
    WHERE is_managed = 1
    GROUP BY validation_status
    ORDER BY
        CASE validation_status
            WHEN 'CRITICAL' THEN 1
            WHEN 'BORE_WARNING' THEN 2
            WHEN 'DIMENSIONAL' THEN 3
            WHEN 'WARNING' THEN 4
            WHEN 'PASS' THEN 5
            WHEN 'REPEAT' THEN 6
            ELSE 7
        END
""")

status_results = cursor.fetchall()

for status, count in status_results:
    status_display = status if status else "NULL"
    print(f"  {status_display:<20} {count:>6} files")

conn.close()

print()
print("=" * 80)
print("COMPLETE")
print("=" * 80)
