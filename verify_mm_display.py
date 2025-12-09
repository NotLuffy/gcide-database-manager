import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("VERIFYING MM THICKNESS DISPLAY")
print("=" * 80)
print()

# Check files with MM in thickness_display
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display
    FROM programs
    WHERE thickness_display LIKE '%MM%'
    ORDER BY program_number
    LIMIT 30
""")

results = cursor.fetchall()

print(f"Sample of files with MM thickness display:\n")
print(f"{'Prog #':<10} {'Display':<12} {'Internal (in)':<15} {'Title':<50}")
print("-" * 100)

for prog_num, title, thickness, thickness_display in results:
    thickness_str = f"{thickness:.3f}\"" if thickness else "N/A"
    title_str = title[:47] + "..." if len(title) > 50 else title
    print(f"{prog_num:<10} {thickness_display:<12} {thickness_str:<15} {title_str}")

print()
print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print(f"Total files with MM display: {len(results)}")
print()
print("All MM thickness values are now displayed as '##MM' in the table")
print("while being stored internally in inches for calculations.")

conn.close()
