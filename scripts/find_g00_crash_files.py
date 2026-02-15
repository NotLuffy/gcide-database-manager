"""
Find all files with G00 rapid into negative Z crash issues
"""

import sqlite3
import json

db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"

try:
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    # Get all programs with crash issues
    cursor.execute('''
        SELECT program_number, crash_issues, file_path
        FROM programs
        WHERE crash_issues IS NOT NULL AND crash_issues != "null"
    ''')
    results = cursor.fetchall()

    g00_rapid_files = []
    diagonal_rapid_files = []
    other_crash_files = []

    for prog_num, crash_issues_str, file_path in results:
        try:
            crash_issues = json.loads(crash_issues_str) if crash_issues_str else []

            has_g00_rapid = False
            has_diagonal = False

            for issue in crash_issues:
                if 'G00 rapid to Z' in issue:
                    has_g00_rapid = True
                    g00_rapid_files.append((prog_num, issue, file_path))
                elif 'diagonal' in issue.lower() and 'G00' in issue:
                    has_diagonal = True
                    diagonal_rapid_files.append((prog_num, issue, file_path))

            if not has_g00_rapid and not has_diagonal:
                other_crash_files.append((prog_num, crash_issues[0] if crash_issues else '', file_path))

        except Exception as e:
            print(f"Error parsing {prog_num}: {e}")

    print("="*70)
    print("G-CODE CRASH ANALYSIS")
    print("="*70)
    print()
    print(f"Total programs with crash issues: {len(results)}")
    print(f"  G00 rapid into negative Z: {len(g00_rapid_files)}")
    print(f"  Diagonal rapids with negative Z: {len(diagonal_rapid_files)}")
    print(f"  Other crash types: {len(other_crash_files)}")
    print()

    if g00_rapid_files:
        print("="*70)
        print(f"FILES WITH G00 RAPID INTO NEGATIVE Z ({len(g00_rapid_files)} total)")
        print("="*70)
        for prog_num, issue, file_path in g00_rapid_files[:20]:
            print(f"\n{prog_num}:")
            print(f"  {issue[:150]}")
            if file_path:
                print(f"  Path: {file_path}")

        if len(g00_rapid_files) > 20:
            print(f"\n... and {len(g00_rapid_files) - 20} more files")

    if diagonal_rapid_files:
        print()
        print("="*70)
        print(f"FILES WITH DIAGONAL RAPIDS ({len(diagonal_rapid_files)} total)")
        print("="*70)
        for prog_num, issue, file_path in diagonal_rapid_files[:10]:
            print(f"\n{prog_num}:")
            print(f"  {issue[:150]}")

        if len(diagonal_rapid_files) > 10:
            print(f"\n... and {len(diagonal_rapid_files) - 10} more files")

    conn.close()

    # Save results to file for reference
    with open('g00_crash_files_list.txt', 'w') as f:
        f.write("G00 RAPID INTO NEGATIVE Z - FILES LIST\n")
        f.write("="*70 + "\n\n")
        for prog_num, issue, file_path in g00_rapid_files:
            f.write(f"{prog_num}\n")
            f.write(f"  {issue}\n")
            f.write(f"  {file_path}\n\n")

    print()
    print("="*70)
    print(f"Results saved to: g00_crash_files_list.txt")
    print("="*70)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
