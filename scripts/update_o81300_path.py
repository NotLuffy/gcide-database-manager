"""
Update o81300 path in database (run when database manager is closed).
"""

import sqlite3

db_path = "L:/My Drive/Home/File organizer/gcode_database.db"

print("Updating o81300 path in database...")
print()

try:
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    # Use forward slashes like other records (standard format)
    correct_path = "L:/My Drive/Home/File organizer/repository/o81300.nc"

    cursor.execute("""
        UPDATE programs
        SET file_path = ?
        WHERE program_number = 'o81300'
    """, (correct_path,))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    if updated > 0:
        print(f"[OK] Database updated successfully")
        print(f"     Path: {correct_path}")
        print()
        print("You can now open o81300 from the database manager!")
    else:
        print("[INFO] No record found to update (o81300 may not be in database)")

except sqlite3.OperationalError as e:
    if "locked" in str(e).lower():
        print("[ERROR] Database is locked - please close the database manager first!")
        print("        Then run this script again.")
    else:
        print(f"[ERROR] {e}")
except Exception as e:
    print(f"[ERROR] {e}")
