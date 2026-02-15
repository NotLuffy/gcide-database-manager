import re
import os
from pathlib import Path

def split_cnc_file(input_file, output_folder):
    """
    Split a CNC file containing multiple programs into individual files.
    Each program starts with O##### and ends with M30.
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    current_program = []
    current_program_number = None
    programs_created = 0

    for line in lines:
        stripped_line = line.strip()

        # Check if this line starts a new program (O followed by digits)
        match = re.match(r'^O(\d+)', stripped_line, re.IGNORECASE)

        if match:
            # If we already have a program in progress, save it first
            if current_program and current_program_number:
                output_file = os.path.join(output_folder, f"o{current_program_number}.nc")
                with open(output_file, 'w', encoding='utf-8') as out:
                    out.writelines(current_program)
                programs_created += 1
                print(f"Created: {output_file}")

            # Start new program
            current_program_number = match.group(1)
            current_program = [line]
        elif current_program_number:
            # Add line to current program
            current_program.append(line)

            # Check if this is the end of the program
            if stripped_line.upper() == 'M30':
                # Save the program
                output_file = os.path.join(output_folder, f"o{current_program_number}.nc")
                with open(output_file, 'w', encoding='utf-8') as out:
                    out.writelines(current_program)
                programs_created += 1
                print(f"Created: {output_file}")

                # Reset for next program
                current_program = []
                current_program_number = None

    # Save any remaining program (in case file doesn't end with M30)
    if current_program and current_program_number:
        output_file = os.path.join(output_folder, f"o{current_program_number}.nc")
        with open(output_file, 'w', encoding='utf-8') as out:
            out.writelines(current_program)
        programs_created += 1
        print(f"Created: {output_file}")

    return programs_created

# Process both files
print("=" * 60)
print("Splitting ALL LATHE 1.nc into L1 Memory folder...")
print("=" * 60)
count1 = split_cnc_file("D:/ALL LATHE 1.nc", "D:/L1 Memory")
print(f"\nTotal programs created from ALL LATHE 1: {count1}")

print("\n" + "=" * 60)
print("Splitting ALL LATHE 2.nc into L2 Memory folder...")
print("=" * 60)
count2 = split_cnc_file("D:/ALL LATHE 2.nc", "D:/L2 Memory")
print(f"\nTotal programs created from ALL LATHE 2: {count2}")

print("\n" + "=" * 60)
print(f"COMPLETE! Total programs created: {count1 + count2}")
print("=" * 60)
