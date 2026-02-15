"""
Modal G-Code Crash Pattern Detector

Detects cases where G00 (rapid) is set and next line has negative Z
without explicit G01, causing rapid move into part.

Pattern:
Line 1: G154 P24G00 X2.5 Z0.1  <- Sets G00 mode
Line 2: Z-0.09                  <- Inherits G00 (CRASH!)

Author: G-Code Database Manager
Date: 2026-02-08
"""

import sqlite3
import re
from typing import List, Dict, Optional


class ModalGCodeCrashDetector:
    """Detects modal G-code crashes where G00 is followed by negative Z"""

    def __init__(self, db_path: str, repository_path: str):
        self.db_path = db_path
        self.repository_path = repository_path
        self.results = {
            'total_files': 0,
            'files_with_modal_crashes': 0,
            'modal_crash_instances': [],
            'g154_g00_runons': 0,  # G154 and G00 with no space
        }

    def detect_modal_crash(self, lines: List[str], file_path: str, program_number: str):
        """
        Detect modal G-code crash pattern.

        Pattern to detect:
        1. Line with G00 (in work coordinates, NOT G53 machine coordinates)
        2. Next line(s) with negative Z but NO explicit G01
        3. Modal G00 causes rapid into part (CRASH)
        """
        current_g_code = None  # Track modal G-code state
        in_work_coordinates = False  # Track if we're in work coordinates

        for i, line in enumerate(lines):
            line_upper = line.strip().upper()

            # Skip comments and empty lines
            if line_upper.startswith('(') or not line_upper:
                continue

            # Detect G53 (machine coordinates - SAFE, not work coordinates)
            if 'G53' in line_upper:
                in_work_coordinates = False
                continue  # Skip G53 lines, they're machine coordinates (tool change pos)

            # Detect G154 (work coordinate system)
            if 'G154' in line_upper:
                in_work_coordinates = True

                # Check if G154 and G00 are run together (no space)
                if re.search(r'G154\s+P\d+G00', line_upper):
                    self.results['g154_g00_runons'] += 1
                    current_g_code = 'G00'

            # Detect G00 (but only count if in work coordinates)
            if 'G00' in line_upper and in_work_coordinates:
                current_g_code = 'G00'

            # Detect G01, G02, G03 (changes modal state)
            elif 'G01' in line_upper:
                current_g_code = 'G01'
            elif 'G02' in line_upper:
                current_g_code = 'G02'
            elif 'G03' in line_upper:
                current_g_code = 'G03'

            # Check if current line has negative Z move
            z_match = re.search(r'Z\s*(-\d+\.?\d*)', line_upper)
            if z_match:
                z_value = float(z_match.group(1))

                # If Z is negative, in work coordinates, and we're in G00 mode
                if z_value < 0 and current_g_code == 'G00' and in_work_coordinates:
                    # Check if this line has explicit G01
                    if 'G01' not in line_upper:
                        # CRASH DETECTED: Rapid move to negative Z in work coordinates
                        self.results['modal_crash_instances'].append({
                            'program': program_number,
                            'file_path': file_path,
                            'line_number': i + 1,
                            'line_content': line.strip(),
                            'z_value': z_value,
                            'issue': 'G00 modal state inherited, rapid into part (work coordinates)'
                        })

                        self.results['files_with_modal_crashes'] += 1
                        return True  # Found crash in this file

        return False

    def analyze_file(self, program_number: str, file_path: str):
        """Analyze single file for modal G-code crashes"""
        self.results['total_files'] += 1

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            self.detect_modal_crash(lines, file_path, program_number)

        except Exception as e:
            print(f"Error analyzing {program_number}: {e}")

    def run_analysis(self, sample_size: int = 1000):
        """Run analysis on sample of files"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        query = """
        SELECT program_number, file_path
        FROM programs
        WHERE file_path IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
        """

        cursor.execute(query, (sample_size,))
        files = cursor.fetchall()
        conn.close()

        print(f"Analyzing {len(files)} files for modal G-code crash patterns...")

        for i, (program_number, file_path) in enumerate(files, 1):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(files)}...")

            self.analyze_file(program_number, file_path)

        print(f"\nAnalysis complete!")

    def generate_report(self) -> str:
        """Generate report of modal G-code crash patterns"""
        lines = []

        lines.append("=" * 80)
        lines.append("MODAL G-CODE CRASH PATTERN DETECTION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Files Analyzed: {self.results['total_files']}")
        lines.append(f"Files with Modal Crashes: {self.results['files_with_modal_crashes']}")
        lines.append(f"Total Modal Crash Instances: {len(self.results['modal_crash_instances'])}")
        lines.append(f"G154/G00 Run-ons Found: {self.results['g154_g00_runons']}")
        lines.append("")

        # Pattern explanation
        lines.append("PATTERN DETECTED")
        lines.append("-" * 80)
        lines.append("Modal G-code crash occurs when:")
        lines.append("1. G00 (rapid) is set on a line")
        lines.append("2. Next line has negative Z movement WITHOUT explicit G01")
        lines.append("3. Modal state inherits G00, causing rapid into part (CRASH)")
        lines.append("")
        lines.append("Example:")
        lines.append("  Line 98: G154 P24G00 X2.5 Z0.1  <- Sets G00 mode")
        lines.append("  Line 99: Z-0.09 F0.008           <- Inherits G00 (CRASH!)")
        lines.append("")
        lines.append("Correct version:")
        lines.append("  Line 98: G154 P24G00 X2.5 Z0.1  <- Sets G00 mode")
        lines.append("  Line 99: G01 Z-0.09 F0.008      <- Explicit G01 (SAFE)")
        lines.append("")

        # List all crash instances
        if self.results['modal_crash_instances']:
            lines.append("MODAL CRASH INSTANCES FOUND")
            lines.append("-" * 80)

            for i, crash in enumerate(self.results['modal_crash_instances'][:50], 1):
                lines.append(f"{i}. {crash['program']} (Line {crash['line_number']})")
                lines.append(f"   Code: {crash['line_content']}")
                lines.append(f"   Z Value: {crash['z_value']}")
                lines.append(f"   Issue: {crash['issue']}")
                lines.append("")

            if len(self.results['modal_crash_instances']) > 50:
                lines.append(f"... and {len(self.results['modal_crash_instances']) - 50} more instances")
                lines.append("")

        else:
            lines.append("NO MODAL CRASHES DETECTED")
            lines.append("-" * 80)
            lines.append("All files properly use explicit G01 before negative Z moves.")
            lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        lines.append("1. Add modal G-code state tracking to crash_prevention_validator.py")
        lines.append("2. Track current G-code (G00/G01/G02/G03) across lines")
        lines.append("3. Warn if negative Z move occurs while in G00 mode")
        lines.append("4. Suggest fix: Add explicit G01 before negative Z move")
        lines.append("5. Parse G154 P##G00 patterns (handle run-on commands)")
        lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """Main entry point"""
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    repository_path = r"l:\My Drive\Home\File organizer\repository"

    detector = ModalGCodeCrashDetector(db_path, repository_path)

    # Analyze 1000 files
    detector.run_analysis(sample_size=1000)

    # Generate report
    report = detector.generate_report()

    # Save to file
    with open("modal_gcode_crash_report.txt", 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print(f"\nReport saved to: modal_gcode_crash_report.txt")


if __name__ == "__main__":
    main()
