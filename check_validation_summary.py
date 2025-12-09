"""
Quick check of validation status breakdown after CB fix rescan.
"""

import sqlite3

conn = sqlite3.connect('gcode_database.db')
cursor = conn.cursor()

# Get overall status breakdown
cursor.execute("""
    SELECT validation_status, COUNT(*)
    FROM programs
    GROUP BY validation_status
    ORDER BY validation_status
""")

print("VALIDATION STATUS BREAKDOWN:")
print("=" * 60)
for status, count in cursor.fetchall():
    print(f"{status:<20} {count:>6}")

# Get CB TOO SMALL count
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE validation_status = 'CRITICAL'
    AND validation_issues LIKE '%CB TOO SMALL%'
""")
cb_too_small = cursor.fetchone()[0]
print(f"\n{'CB TOO SMALL errors':<20} {cb_too_small:>6}")

# Get CB TOO LARGE count
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE validation_status = 'CRITICAL'
    AND validation_issues LIKE '%CB TOO LARGE%'
""")
cb_too_large = cursor.fetchone()[0]
print(f"{'CB TOO LARGE errors':<20} {cb_too_large:>6}")

conn.close()
