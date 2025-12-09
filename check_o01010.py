import sqlite3

conn = sqlite3.connect(r'c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT program_number, file_path, round_size, in_correct_range
    FROM programs
    WHERE file_path LIKE '%o01010.nc'
    ORDER BY program_number
""")

results = cursor.fetchall()
print('Programs pointing to o01010.nc:')
for row in results:
    print(f'  {row[0]:15} - round_size:{row[2]} - in_correct_range:{row[3]}')

# Check the actual file content
print('\nActual file content (first 5 lines):')
with open(r'c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\repository\o01010.nc', 'r') as f:
    for i in range(5):
        print(f'  {f.readline().rstrip()}')

conn.close()
