import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check o50240
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, hub_height, spacer_type
    FROM programs
    WHERE program_number = 'o50240'
""")

result = cursor.fetchone()

if result:
    prog_num, title, thickness, thickness_display, hub_height, spacer_type = result
    print("=" * 80)
    print("CHECKING o50240")
    print("=" * 80)
    print(f"Program Number: {prog_num}")
    print(f"Title: {title}")
    print(f"Spacer Type: {spacer_type}")
    print(f"Thickness (stored): {thickness}")
    print(f"Thickness Display: {thickness_display}")
    print(f"Hub Height: {hub_height}")
    print()
    print("ANALYSIS:")
    print(f"Title: '{title}'")
    print(f"Expected thickness: 1.0 (before --HC)")
    print(f"Detected thickness: {thickness}")
    print(f"Hub height (after HC): 0.50")
    print(f"Detected hub height: {hub_height}")
    print()
    print("ISSUE: Parser detected 0.50 (hub height) instead of 1.0 (thickness)")
else:
    print("o50240 not found in database")

conn.close()

print()
print("=" * 80)
print("PATTERN ANALYSIS")
print("=" * 80)
print("Correct pattern: ##.## --HC ##.##")
print("                 ^^^^^      ^^^^^")
print("                 thickness  hub_height")
print()
print("The value BEFORE --HC or HC is the thickness")
print("The value AFTER HC (if present) is the hub height")
