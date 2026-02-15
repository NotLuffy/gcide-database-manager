"""
Tool Home Position Fixer
Fixes G53 Z tool home positions by changing all Z values more negative than Z-13 to Z-13.

This script will:
1. Scan for G53 Z positions where Z < -13 (e.g., Z-14, Z-15, Z-16, etc.)
2. Replace them with Z-13.
3. Create a backup of each modified file
4. Generate a report of all changes made
"""

import os
import re
import shutil
from datetime import datetime
from typing import List, Dict, Tuple


class ToolHomeFixer:
    """Fixes G53 Z tool home positions to Z-13."""

    # G-code file extensions to process
    GCODE_EXTENSIONS = {'.nc', '.txt', '.ngc', '.gcode', '.tap', '.mpf', ''}

    # Target Z value
    TARGET_Z = "-13."

    def __init__(self, scan_path: str, create_backups: bool = False):
        self.scan_path = scan_path
        self.create_backups = create_backups
        self.changes: List[Dict] = []
        self.files_modified = 0
        self.total_replacements = 0

        # Pattern to match G53 lines with Z coordinates more negative than -13
        # Captures: G53 [X...] Z-VALUE
        # We need to replace the Z value portion
        self.g53_pattern = re.compile(
            r'(G53\s*(?:X[\d.\-]*\s*)?)Z([\-\d.]+)',
            re.IGNORECASE
        )

    def is_gcode_file(self, filepath: str) -> bool:
        """Check if file is likely a G-code file"""
        ext = os.path.splitext(filepath)[1].lower()

        if ext in self.GCODE_EXTENSIONS:
            if ext in ('', '.txt'):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = f.read(500)
                        if re.search(r'[OoPp]\d{4,}|G[0-9]|M[0-9]|N\d+', first_lines):
                            return True
                        return False
                except:
                    return False
            return True
        return False

    def fix_file(self, filepath: str) -> Tuple[int, List[Dict]]:
        """
        Fix a single file's G53 Z positions.
        Returns (number_of_replacements, list_of_changes)
        """
        file_changes = []
        replacements = 0

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return 0, []

        modified = False
        new_lines = []

        for line_num, line in enumerate(lines, 1):
            original_line = line
            line_stripped = line.strip()

            # Skip pure comments
            if line_stripped.startswith('(') or line_stripped.startswith(';'):
                new_lines.append(line)
                continue

            # Check for G53 Z pattern
            match = self.g53_pattern.search(line)
            if match:
                try:
                    z_value = float(match.group(2))
                except ValueError:
                    new_lines.append(line)
                    continue

                # Only fix if Z is more negative than -13
                if z_value < -13:
                    # Replace the Z value with Z-13.
                    prefix = match.group(1)  # "G53 X0 " or "G53 "

                    # Construct new line preserving the prefix
                    new_z_part = f"Z{self.TARGET_Z}"
                    new_line = self.g53_pattern.sub(f'{prefix}{new_z_part}', line, count=1)

                    file_changes.append({
                        'line_num': line_num,
                        'old_line': line_stripped,
                        'new_line': new_line.strip(),
                        'old_z': z_value,
                        'new_z': -13.0
                    })

                    new_lines.append(new_line)
                    modified = True
                    replacements += 1
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Write changes if any were made
        if modified:
            # Create backup if requested
            if self.create_backups:
                backup_path = filepath + '.bak'
                try:
                    shutil.copy2(filepath, backup_path)
                except Exception as e:
                    print(f"Warning: Could not create backup for {filepath}: {e}")

            # Write the modified file
            try:
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    f.writelines(new_lines)
            except Exception as e:
                print(f"Error writing {filepath}: {e}")
                return 0, []

        return replacements, file_changes

    def fix_directory(self, progress_callback=None) -> Tuple[int, int]:
        """
        Fix all G-code files in directory tree.
        Returns (files_modified, total_replacements)
        """
        self.changes = []
        self.files_modified = 0
        self.total_replacements = 0

        print(f"\nFixing tool home positions in: {self.scan_path}")
        print(f"Target Z value: Z{self.TARGET_Z}")
        print("-" * 60)

        # Collect all G-code files
        all_files = []
        for root, dirs, files in os.walk(self.scan_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                if self.is_gcode_file(filepath):
                    all_files.append(filepath)

        total_files = len(all_files)
        print(f"Found {total_files} G-code files to process\n")

        for i, filepath in enumerate(all_files):
            # Progress update
            if progress_callback:
                progress_callback(i + 1, total_files, filepath)
            elif (i + 1) % 100 == 0 or (i + 1) == total_files:
                print(f"  Processed {i + 1}/{total_files} files... "
                      f"({self.files_modified} modified, {self.total_replacements} replacements)",
                      flush=True)

            replacements, file_changes = self.fix_file(filepath)

            if replacements > 0:
                self.files_modified += 1
                self.total_replacements += replacements

                # Store changes for reporting
                self.changes.append({
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'folder': os.path.dirname(filepath),
                    'replacements': replacements,
                    'details': file_changes
                })

        return self.files_modified, self.total_replacements

    def generate_report(self, output_path: str = None) -> str:
        """Generate a text report of all changes made"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                os.path.dirname(self.scan_path) if os.path.isdir(self.scan_path) else os.getcwd(),
                f"tool_home_fix_report_{timestamp}.txt"
            )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Tool Home Position Fix Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Scan Location: {self.scan_path}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Target Z Value: Z{self.TARGET_Z}\n\n")
            f.write(f"Files Modified: {self.files_modified}\n")
            f.write(f"Total Replacements: {self.total_replacements}\n")
            f.write("\n" + "=" * 60 + "\n\n")

            # Group by folder
            folders = {}
            for change in self.changes:
                folder = change['folder']
                if folder not in folders:
                    folders[folder] = []
                folders[folder].append(change)

            for folder in sorted(folders.keys()):
                f.write(f"\nFolder: {folder}\n")
                f.write("-" * 60 + "\n")

                for file_change in folders[folder]:
                    f.write(f"\n  File: {file_change['filename']}\n")
                    f.write(f"  Replacements: {file_change['replacements']}\n")

                    for detail in file_change['details']:
                        f.write(f"    Line {detail['line_num']}: Z{detail['old_z']} -> Z{self.TARGET_Z}\n")
                        f.write(f"      Before: {detail['old_line']}\n")
                        f.write(f"      After:  {detail['new_line']}\n")

        print(f"\nReport saved to: {output_path}")
        return output_path


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Fix G53 Z tool home positions to Z-13.')
    parser.add_argument('path', nargs='?', default=r"I:\My Drive\NC Master\Kevins USB Check",
                        help='Path to fix (default: I:\\My Drive\\NC Master\\Kevins USB Check)')
    parser.add_argument('--backup', '-b', action='store_true',
                        help='Create .bak backup files before modifying')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be changed without making changes')

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}")
        return 1

    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")

    # Create fixer and run
    fixer = ToolHomeFixer(args.path, create_backups=args.backup)

    if args.dry_run:
        # For dry run, we'll scan but not write
        print("Scanning for changes that would be made...\n")
        # Use the scanner instead for dry run
        from tool_home_scanner import ToolHomeScanner
        scanner = ToolHomeScanner(args.path)
        files_scanned, issues_found = scanner.scan_directory()
        print(f"\nDry Run Results:")
        print(f"  Would modify files with {issues_found} G53 Z positions")
        return 0

    files_modified, total_replacements = fixer.fix_directory()

    print(f"\n{'='*60}")
    print(f"Fix Complete!")
    print(f"  Files Modified: {files_modified}")
    print(f"  Total Replacements: {total_replacements}")

    if files_modified > 0:
        # Generate report
        report_path = fixer.generate_report()
        print(f"\nDetailed report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    exit(main())
