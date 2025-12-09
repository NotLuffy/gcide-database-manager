import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING MM THICKNESS RANGE (5MM - 24MM)")
print("=" * 80)
print()

# Check all files with MM in thickness_display
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display
    FROM programs
    WHERE thickness_display LIKE '%MM%'
    ORDER BY CAST(REPLACE(thickness_display, 'MM', '') AS INTEGER)
""")

results = cursor.fetchall()

# Parse MM values and categorize
valid_range = []      # 5mm - 24mm (typical thickness)
below_range = []      # < 5mm (might be wrong)
above_range = []      # > 24mm (might be wrong)
non_numeric = []      # Can't parse

for prog_num, title, thickness, thickness_display in results:
    try:
        # Extract numeric value from "15MM" format
        mm_str = thickness_display.replace('MM', '').replace('mm', '').strip()
        mm_value = float(mm_str)

        if 5 <= mm_value <= 24:
            valid_range.append((prog_num, title, mm_value, thickness_display))
        elif mm_value < 5:
            below_range.append((prog_num, title, mm_value, thickness_display))
        else:  # > 24
            above_range.append((prog_num, title, mm_value, thickness_display))
    except:
        non_numeric.append((prog_num, title, thickness_display))

print("=" * 80)
print(f"VALID RANGE (5MM - 24MM): {len(valid_range)} files")
print("=" * 80)
print(f"{'Prog #':<10} {'Display':<12} {'Title':<60}")
print("-" * 85)

# Show distribution by MM value
mm_counts = {}
for prog_num, title, mm_value, thickness_display in valid_range:
    mm_counts[int(mm_value)] = mm_counts.get(int(mm_value), 0) + 1

for mm_val in sorted(mm_counts.keys()):
    count = mm_counts[mm_val]
    print(f"{mm_val}MM: {count} files")

print()
print("Sample files:")
for prog_num, title, mm_value, thickness_display in valid_range[:15]:
    title_str = title[:57] + "..." if len(title) > 60 else title
    print(f"{prog_num:<10} {thickness_display:<12} {title_str}")

if len(below_range) > 0:
    print()
    print("=" * 80)
    print(f"BELOW RANGE (< 5MM): {len(below_range)} files")
    print("=" * 80)
    print("These might be incorrect detections:")
    for prog_num, title, mm_value, thickness_display in below_range[:10]:
        print(f"{prog_num}: {thickness_display} - {title[:60]}")

if len(above_range) > 0:
    print()
    print("=" * 80)
    print(f"ABOVE RANGE (> 24MM): {len(above_range)} files")
    print("=" * 80)
    print("These might be incorrect detections:")
    for prog_num, title, mm_value, thickness_display in above_range[:10]:
        print(f"{prog_num}: {thickness_display} - {title[:60]}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total MM thickness files: {len(results)}")
print(f"  [OK] Valid range (5-24MM): {len(valid_range)}")
print(f"  [!] Below 5MM: {len(below_range)}")
print(f"  [!] Above 24MM: {len(above_range)}")

conn.close()
