import sqlite3
import sys
import os

# Add the current directory to path to import the parser
sys.path.insert(0, os.path.dirname(__file__))

from improved_gcode_parser import ImprovedGCodeParser

db_path = r"c:\Users\John Wayne\Desktop\Bronson Generators\File organizer\gcode_database.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get o50420 file path
cursor.execute("SELECT file_path FROM programs WHERE program_number = 'o50420'")
result = cursor.fetchone()

if result and result[0]:
    file_path = result[0]

    print("=" * 80)
    print("RE-PARSING o50420")
    print("=" * 80)
    print()

    # Parse file
    parser = ImprovedGCodeParser()
    parse_result = parser.parse_file(file_path)

    if parse_result:
        print(f"Program Number: {parse_result.program_number}")
        print(f"Title: {parse_result.title}")
        print(f"Spacer Type: {parse_result.spacer_type}")
        print()
        print(f"Thickness (from title): {parse_result.thickness}")
        print(f"Thickness Display: {parse_result.thickness_display}")
        print(f"Drill Depth (from G-code): {parse_result.drill_depth}")
        print()

        if parse_result.validation_issues:
            print("Validation Issues:")
            for issue in parse_result.validation_issues:
                print(f"  - {issue}")
        print()

        if parse_result.dimensional_issues:
            print("Dimensional Issues:")
            for issue in parse_result.dimensional_issues:
                print(f"  - {issue}")
    else:
        print("Failed to parse file")
else:
    print("o50420 not found")

conn.close()
