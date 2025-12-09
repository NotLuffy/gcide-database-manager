import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"  {table[0]}")

# Check what the actual table is called
if tables:
    table_name = tables[0][0]
    print(f"\nChecking first table: {table_name}")

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    print(f"\nColumns in {table_name}:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

conn.close()
