import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check files in free ranges with their round sizes
print("=" * 80)
print("FILES IN FREE RANGE 1 (o1000-o9999)")
print("=" * 80)

cursor.execute("""
    SELECT program_number, round_size, ob_from_gcode, outer_diameter, title
    FROM programs
    WHERE is_managed = 1
      AND CAST(REPLACE(REPLACE(program_number, 'o', ''), 'O', '') AS INTEGER) BETWEEN 1000 AND 9999
    ORDER BY program_number
    LIMIT 50
""")

free_range_1 = cursor.fetchall()
print(f"Found {len(free_range_1)} files in Free Range 1")
print()

for prog_num, round_size, ob, od, title in free_range_1[:20]:
    print(f"{prog_num}: round_size={round_size}, ob={ob}, od={od}, title={title[:50] if title else 'N/A'}")

print()
print("=" * 80)
print("FILES IN FREE RANGE 2 (o14000-o49999)")
print("=" * 80)

cursor.execute("""
    SELECT program_number, round_size, ob_from_gcode, outer_diameter, title
    FROM programs
    WHERE is_managed = 1
      AND CAST(REPLACE(REPLACE(program_number, 'o', ''), 'O', '') AS INTEGER) BETWEEN 14000 AND 49999
    ORDER BY program_number
    LIMIT 50
""")

free_range_2 = cursor.fetchall()
print(f"Found {len(free_range_2)} files in Free Range 2")
print()

for prog_num, round_size, ob, od, title in free_range_2[:20]:
    print(f"{prog_num}: round_size={round_size}, ob={ob}, od={od}, title={title[:50] if title else 'N/A'}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

# Count by round_size in free ranges
cursor.execute("""
    SELECT round_size, COUNT(*) as count
    FROM programs
    WHERE is_managed = 1
      AND (
        (CAST(REPLACE(REPLACE(program_number, 'o', ''), 'O', '') AS INTEGER) BETWEEN 1000 AND 9999)
        OR
        (CAST(REPLACE(REPLACE(program_number, 'o', ''), 'O', '') AS INTEGER) BETWEEN 14000 AND 49999)
      )
    GROUP BY round_size
    ORDER BY round_size
""")

summary = cursor.fetchall()
print("Files in free ranges by round_size:")
for rs, count in summary:
    print(f"  Round size {rs}: {count} files")

print()
print("Files with NULL round_size in free ranges:")
cursor.execute("""
    SELECT COUNT(*)
    FROM programs
    WHERE is_managed = 1
      AND round_size IS NULL
      AND (
        (CAST(REPLACE(REPLACE(program_number, 'o', ''), 'O', '') AS INTEGER) BETWEEN 1000 AND 9999)
        OR
        (CAST(REPLACE(REPLACE(program_number, 'o', ''), 'O', '') AS INTEGER) BETWEEN 14000 AND 49999)
      )
""")
null_count = cursor.fetchone()[0]
print(f"  {null_count} files")

conn.close()
