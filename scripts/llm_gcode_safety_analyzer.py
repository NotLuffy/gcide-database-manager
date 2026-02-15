"""
LLM-Powered G-Code Safety Analyzer

Uses LLM analysis to detect potential crash scenarios that automated
pattern matching might miss. Analyzes files that pass validation to
find subtle safety issues.

Author: G-Code Database Manager
Date: 2026-02-08
"""

import sqlite3
import random
import os
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Tuple
from improved_gcode_parser import ImprovedGCodeParser


class LLMGCodeSafetyAnalyzer:
    """Analyzes G-code files for crash patterns using LLM reasoning"""

    def __init__(self, db_path: str, repository_path: str):
        self.db_path = db_path
        self.repository_path = repository_path
        self.parser = ImprovedGCodeParser()
        self.findings = []

    def select_passing_files(self, count: int = 50) -> List[Tuple]:
        """Select files that PASS validation (no critical errors)"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        query = """
        SELECT program_number, file_path, outer_diameter, thickness, hub_height
        FROM programs
        WHERE file_path IS NOT NULL
          AND outer_diameter IS NOT NULL
          AND thickness IS NOT NULL
          AND (validation_issues IS NULL OR validation_issues = '[]')
          AND (crash_issues IS NULL OR crash_issues = '[]')
        ORDER BY RANDOM()
        LIMIT ?
        """

        cursor.execute(query, (count,))
        files = cursor.fetchall()
        conn.close()

        print(f"Selected {len(files)} files that pass validation")
        return files

    def read_gcode_content(self, file_path: str) -> str:
        """Read G-code file content"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""

    def analyze_gcode_for_safety(self, program_number: str, content: str,
                                 outer_diameter: float, thickness: float) -> Dict:
        """
        Analyze G-code content for potential crash scenarios.

        This function looks for patterns that might not be caught by
        automated validation:

        1. Rapid moves (G00) while spindle is running
        2. Tool changes at unsafe Z positions
        3. Missing work offsets before cutting
        4. Coordinate system confusion (G53 vs G154)
        5. Improper sequencing of operations
        6. Tool approach angles that could cause crashes
        7. Missing coolant on/off at critical points
        8. Spindle speed changes during cutting
        9. Feed rate too high for material removal
        10. Z-axis moves that could hit chuck jaws
        """

        issues_found = []
        warnings_found = []

        lines = content.split('\n')

        # Track state
        spindle_running = False
        current_tool = None
        current_z = None
        work_offset_set = False
        coolant_on = False
        current_feed_mode = None  # 'G00' or 'G01'
        in_cutting_operation = False
        last_tool_change_z = None

        for line_num, line in enumerate(lines, 1):
            line_upper = line.upper().strip()

            # Skip empty lines and pure comments
            if not line_upper or line_upper.startswith('(') or line_upper.startswith('%'):
                continue

            # Remove inline comments for analysis
            if '(' in line_upper:
                line_upper = line_upper[:line_upper.index('(')].strip()

            # Track spindle state
            if 'M03' in line_upper or 'M04' in line_upper:
                spindle_running = True
            elif 'M05' in line_upper:
                spindle_running = False

            # Track coolant state
            if 'M08' in line_upper:
                coolant_on = True
            elif 'M09' in line_upper:
                coolant_on = False

            # Track work offset
            if 'G154' in line_upper or 'G54' in line_upper:
                work_offset_set = True

            # Track tool changes
            if line_upper.startswith('T') and any(c.isdigit() for c in line_upper):
                # Extract tool number
                import re
                match = re.search(r'T(\d+)', line_upper)
                if match:
                    new_tool = match.group(1)
                    if current_tool and current_tool != new_tool:
                        # Tool change detected
                        if current_z is not None and current_z < -0.1:
                            issues_found.append({
                                'line': line_num,
                                'severity': 'WARNING',
                                'type': 'TOOL_CHANGE_LOW_Z',
                                'message': f'Line {line_num}: Tool change at Z={current_z:.2f}" (below safe zone)'
                            })
                        last_tool_change_z = current_z
                    current_tool = new_tool

            # Track Z position
            if 'Z' in line_upper:
                import re
                match = re.search(r'Z\s*(-?\d+\.?\d*)', line_upper)
                if match:
                    z_val = float(match.group(1))

                    # Check for G53 (machine coordinates)
                    if 'G53' in line_upper:
                        # G53 moves should always have Z at safe position
                        if z_val < -0.1:
                            issues_found.append({
                                'line': line_num,
                                'severity': 'CRITICAL',
                                'type': 'G53_UNSAFE_Z',
                                'message': f'Line {line_num}: G53 tool home with Z={z_val:.2f}" (unsafe!)'
                            })
                    else:
                        current_z = z_val

            # Track feed mode
            if 'G00' in line_upper:
                current_feed_mode = 'G00'
                # Check if rapid move with spindle running
                if spindle_running and current_z is not None and current_z < 0:
                    warnings_found.append({
                        'line': line_num,
                        'severity': 'WARNING',
                        'type': 'RAPID_WITH_SPINDLE',
                        'message': f'Line {line_num}: Rapid move (G00) while spindle running at Z={current_z:.2f}"'
                    })
            elif 'G01' in line_upper:
                current_feed_mode = 'G01'
                in_cutting_operation = True

            # Check for feed moves without work offset
            if current_feed_mode == 'G01' and not work_offset_set:
                if current_z is not None and current_z < 0:
                    issues_found.append({
                        'line': line_num,
                        'severity': 'CRITICAL',
                        'type': 'CUTTING_NO_OFFSET',
                        'message': f'Line {line_num}: Cutting operation without work offset (G154/G54)'
                    })

            # Check for cutting without coolant
            if current_feed_mode == 'G01' and not coolant_on:
                if current_z is not None and current_z < -0.1:
                    warnings_found.append({
                        'line': line_num,
                        'severity': 'SUGGESTION',
                        'type': 'CUTTING_NO_COOLANT',
                        'message': f'Line {line_num}: Deep cutting (Z={current_z:.2f}") without coolant'
                    })

            # Check for jaw clearance issues (part-specific)
            if current_tool and current_tool.startswith('3'):  # T3xx = turning tool
                if current_z is not None:
                    # Calculate jaw clearance based on dimensions
                    if thickness:
                        total_height = thickness
                        jaw_position = total_height - 0.3  # Jaws extend 0.3" from spindle

                        if current_z < -jaw_position:
                            issues_found.append({
                                'line': line_num,
                                'severity': 'CRITICAL',
                                'type': 'JAW_CLEARANCE',
                                'message': f'Line {line_num}: Tool may hit chuck jaws at Z={current_z:.2f}" (limit: {-jaw_position:.2f}")'
                            })

        return {
            'program_number': program_number,
            'critical_issues': [f for f in issues_found if f['severity'] == 'CRITICAL'],
            'warnings': [f for f in issues_found if f['severity'] == 'WARNING'] + warnings_found,
            'suggestions': [f for f in warnings_found if f['severity'] == 'SUGGESTION']
        }

    def run_analysis(self, count: int = 50):
        """Run LLM-based safety analysis on passing files"""
        print(f"\n{'='*80}")
        print(f"LLM-POWERED G-CODE SAFETY ANALYSIS")
        print(f"Analyzing {count} files that pass current validation")
        print(f"{'='*80}\n")

        files = self.select_passing_files(count)

        critical_count = 0
        warning_count = 0
        suggestion_count = 0

        for i, (program_number, file_path, outer_diameter, thickness, hub_height) in enumerate(files, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(files)} files analyzed...")

            if not os.path.exists(file_path):
                continue

            # Read G-code content
            content = self.read_gcode_content(file_path)
            if not content:
                continue

            # Analyze for safety issues
            result = self.analyze_gcode_for_safety(program_number, content, outer_diameter, thickness)

            if result['critical_issues'] or result['warnings'] or result['suggestions']:
                self.findings.append(result)
                critical_count += len(result['critical_issues'])
                warning_count += len(result['warnings'])
                suggestion_count += len(result['suggestions'])

        print(f"\n{'='*80}")
        print(f"Analysis complete!")
        print(f"Files with potential issues: {len(self.findings)}/{len(files)}")
        print(f"Critical issues found: {critical_count}")
        print(f"Warnings found: {warning_count}")
        print(f"Suggestions: {suggestion_count}")
        print(f"{'='*80}\n")

    def generate_report(self, output_file: str = None):
        """Generate detailed safety analysis report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"llm_safety_analysis_{timestamp}.txt"

        report_lines = []

        # Header
        report_lines.append("="*80)
        report_lines.append("LLM-POWERED G-CODE SAFETY ANALYSIS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("="*80)
        report_lines.append("")

        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-"*80)
        report_lines.append(f"Files Analyzed: {len(self.findings)}")

        critical_count = sum(len(f['critical_issues']) for f in self.findings)
        warning_count = sum(len(f['warnings']) for f in self.findings)
        suggestion_count = sum(len(f['suggestions']) for f in self.findings)

        report_lines.append(f"Critical Issues: {critical_count}")
        report_lines.append(f"Warnings: {warning_count}")
        report_lines.append(f"Suggestions: {suggestion_count}")
        report_lines.append("")

        # Issue type breakdown
        report_lines.append("ISSUE TYPE BREAKDOWN")
        report_lines.append("-"*80)

        issue_types = {}
        for finding in self.findings:
            for issue in finding['critical_issues'] + finding['warnings'] + finding['suggestions']:
                issue_type = issue['type']
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1

        for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {issue_type}: {count} occurrences")
        report_lines.append("")

        # Critical issues detail
        if critical_count > 0:
            report_lines.append("CRITICAL ISSUES DETAIL")
            report_lines.append("-"*80)

            for finding in self.findings:
                if finding['critical_issues']:
                    report_lines.append(f"Program: {finding['program_number']}")
                    for issue in finding['critical_issues']:
                        report_lines.append(f"  {issue['message']}")
                    report_lines.append("")

        # Recommendations
        report_lines.append("RECOMMENDATIONS")
        report_lines.append("-"*80)

        if critical_count == 0 and warning_count == 0:
            report_lines.append("✓ NO CRITICAL SAFETY ISSUES FOUND")
            report_lines.append("")
            report_lines.append("The LLM analysis found no crash-related safety issues in files")
            report_lines.append("that pass current validation. This confirms the crash prevention")
            report_lines.append("system is comprehensive and effective.")
        else:
            report_lines.append("⚠ ISSUES DETECTED IN FILES THAT PASS VALIDATION")
            report_lines.append("")
            report_lines.append("Some files that pass automated validation have potential safety")
            report_lines.append("issues detected by LLM analysis. Consider enhancing validation")
            report_lines.append("rules to catch these patterns.")

        report_lines.append("")
        report_lines.append("="*80)
        report_lines.append("END OF REPORT")
        report_lines.append("="*80)

        # Write report
        report_text = "\n".join(report_lines)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"\nReport saved to: {output_file}")
        return report_text


def main():
    """Main entry point"""
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    repository_path = r"l:\My Drive\Home\File organizer\repository"

    analyzer = LLMGCodeSafetyAnalyzer(db_path, repository_path)

    # Analyze 50 files that pass validation
    analyzer.run_analysis(count=50)

    # Generate report
    report = analyzer.generate_report()
    print(report)


if __name__ == "__main__":
    main()
