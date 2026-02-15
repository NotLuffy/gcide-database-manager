"""
Split a Haas ALL.nc file into individual program files.
Each program starts with O##### (program number with title) and ends with M30.
"""

import os
import re

def split_all_file(input_file, output_folder):
    """
    Split ALL.nc into individual files named after program numbers.

    Args:
        input_file: Path to the ALL.nc file
        output_folder: Folder to save individual program files
    """

    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    # Read the entire file
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Pattern to match program start: O followed by digits, then optional title in ()
    # Example: O06069 (9.5IN DIA 154.2MM 1.75 STEEL S-1 )
    program_pattern = re.compile(r'^(O\d{4,5})\s*(\([^)]*\))?', re.MULTILINE)

    # Find all program starts
    matches = list(program_pattern.finditer(content))

    if not matches:
        print("No programs found in file!")
        return

    print(f"Found {len(matches)} programs in the file")

    programs_saved = 0
    programs_skipped = 0

    for i, match in enumerate(matches):
        program_num = match.group(1)  # e.g., "O06069"
        title = match.group(2) or ""   # e.g., "(9.5IN DIA 154.2MM 1.75 STEEL S-1 )"

        start_pos = match.start()

        # Find the end of this program (next M30 or next program start)
        # Look for M30 that ends this program
        end_pos = None

        # Search for M30 between this program start and the next program start
        if i < len(matches) - 1:
            next_start = matches[i + 1].start()
            # Find M30 before next program
            m30_search = content[start_pos:next_start]
            m30_match = re.search(r'\nM30\s*\n', m30_search)
            if m30_match:
                end_pos = start_pos + m30_match.end()
            else:
                # No M30 found, use position just before next program
                end_pos = next_start
        else:
            # Last program - find M30 or end of file
            m30_match = re.search(r'\nM30\s*\n', content[start_pos:])
            if m30_match:
                end_pos = start_pos + m30_match.end()
            else:
                # Check for % at end
                end_match = re.search(r'\n%\s*$', content[start_pos:])
                if end_match:
                    end_pos = start_pos + end_match.end()
                else:
                    end_pos = len(content)

        # Extract program content
        program_content = content[start_pos:end_pos].strip()

        # Create filename from program number (lowercase)
        filename = program_num.lower() + ".nc"
        filepath = os.path.join(output_folder, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            print(f"  Skipping {filename} - already exists")
            programs_skipped += 1
            continue

        # Write the program file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(program_content)
            if not program_content.endswith('\n'):
                f.write('\n')

        programs_saved += 1
        title_display = title[:50] if title else "(no title)"
        print(f"  Saved: {filename} - {title_display}")

    print(f"\n=== Summary ===")
    print(f"Programs found: {len(matches)}")
    print(f"Programs saved: {programs_saved}")
    print(f"Programs skipped (already exist): {programs_skipped}")
    print(f"Output folder: {output_folder}")


def main():
    input_file = r"C:\Users\design2\My Drive\L4 PROGRAMS\ALL.nc"
    output_folder = r"C:\Users\design2\My Drive\L4 PROGRAMS\split"

    print(f"Splitting: {input_file}")
    print(f"Output to: {output_folder}")
    print()

    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return

    split_all_file(input_file, output_folder)


if __name__ == '__main__':
    main()
