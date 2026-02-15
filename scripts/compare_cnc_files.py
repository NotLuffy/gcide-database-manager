import os
import re
from pathlib import Path

def extract_program_title(file_path):
    """
    Extract the title from parentheses after the O##### program number.
    Returns the program number and title.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for O##### followed by optional text in parentheses
                match = re.search(r'^O(\d+)\s*(\([^)]*\))?', line.strip(), re.IGNORECASE)
                if match:
                    program_num = match.group(1)
                    title = match.group(2) if match.group(2) else "(NO TITLE)"
                    return program_num, title.strip()
    except Exception as e:
        return None, f"(ERROR: {e})"
    return None, "(NO PROGRAM NUMBER FOUND)"

def compare_folders(folder1, folder2):
    """
    Compare files between two folders and find duplicates with matching titles.
    """
    # Get all .nc files from both folders
    files1 = set(f for f in os.listdir(folder1) if f.endswith('.nc'))
    files2 = set(f for f in os.listdir(folder2) if f.endswith('.nc'))

    # Find common filenames
    common_files = sorted(files1.intersection(files2))

    print(f"Found {len(common_files)} files with matching names between folders")
    print("=" * 80)

    if not common_files:
        print("No duplicate filenames found.")
        return

    # Check which ones have matching titles
    matching_titles = []
    different_titles = []

    for filename in common_files:
        path1 = os.path.join(folder1, filename)
        path2 = os.path.join(folder2, filename)

        prog_num1, title1 = extract_program_title(path1)
        prog_num2, title2 = extract_program_title(path2)

        if title1 == title2:
            matching_titles.append((filename, title1))
        else:
            different_titles.append((filename, title1, title2))

    # Report results
    if matching_titles:
        print(f"\n[MATCH] FILES WITH SAME NAME AND SAME TITLE: {len(matching_titles)}")
        print("=" * 80)
        for filename, title in matching_titles:
            print(f"  {filename:<20} {title}")

    if different_titles:
        print(f"\n[DIFFERENT] FILES WITH SAME NAME BUT DIFFERENT TITLES: {len(different_titles)}")
        print("=" * 80)
        for filename, title1, title2 in different_titles:
            print(f"\n  {filename}")
            print(f"    L1: {title1}")
            print(f"    L2: {title2}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Total files in L1 Memory: {len(files1)}")
    print(f"  Total files in L2 Memory: {len(files2)}")
    print(f"  Files with matching names: {len(common_files)}")
    print(f"  Same name + same title: {len(matching_titles)}")
    print(f"  Same name + different title: {len(different_titles)}")
    print("=" * 80)

# Run the comparison
compare_folders("D:/L1 Memory", "D:/L2 Memory")
