import sqlite3

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING o50408 THICKNESS DETECTION")
print("=" * 80)
print()

# Get o50408 details
cursor.execute("""
    SELECT program_number, title, thickness, thickness_display, spacer_type
    FROM programs
    WHERE program_number = 'o50408'
""")

result = cursor.fetchone()

if result:
    prog_num, title, thickness, thickness_display, spacer_type = result

    print(f"Program Number: {prog_num}")
    print(f"Title: {title}")
    print(f"Spacer Type: {spacer_type}")
    print(f"Thickness (stored): {thickness}")
    print(f"Thickness Display: {thickness_display}")
    print()
    print("ANALYSIS:")
    print("-" * 80)
    print(f"Title: '{title}'")
    print()
    print("Pattern: '.75MM HC'")
    print("  Expected: .75MM = 0.75 inches (no conversion, already inches)")
    print("  OR: .75MM should be interpreted as decimal inches, not millimeters")
    print()
    print(f"Current detection: {thickness_display}")

    if thickness_display == "75MM":
        print("  [ERROR] Incorrectly detected as 75MM")
        print("  Should be: 0.75 (inches) or .75 (decimal inches)")
    elif thickness:
        print(f"  Thickness in inches: {thickness:.3f}")
        if abs(thickness - 0.75) < 0.01:
            print("  [OK] Correctly detected as 0.75 inches")
        elif abs(thickness - (75/25.4)) < 0.01:
            print("  [ERROR] Incorrectly converted from 75MM to inches")
            print(f"         75MM / 25.4 = {75/25.4:.3f} inches")
else:
    print("o50408 not found in database")

conn.close()

print()
print("=" * 80)
print("PATTERN ANALYSIS")
print("=" * 80)
print()
print("The pattern '.75MM HC' should be interpreted as:")
print("  Option 1: .75 = 0.75 inches (decimal without leading zero)")
print("  Option 2: Typo - should be '0.75IN HC' not '.75MM HC'")
print()
print("The parser is likely matching '75' and ignoring the '.' because")
print("the regex pattern doesn't account for decimals without leading zeros")
print("in MM context (e.g., '.75MM' vs '75MM').")
