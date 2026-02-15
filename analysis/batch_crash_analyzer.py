"""
Comprehensive G-Code Crash Analysis Tool

Analyzes ALL G-code files in the database to identify crash patterns
and validation issues. Generates comprehensive report for complete
coverage validation of the crash prevention system.

Author: G-Code Database Manager
Date: 2026-02-08
"""

import sqlite3
import random
import os
from pathlib import Path
from collections import defaultdict, Counter
import json
from datetime import datetime
from improved_gcode_parser import ImprovedGCodeParser


class BatchCrashAnalyzer:
    """Analyzes batch of G-code files for crash patterns and validation issues"""

    def __init__(self, db_path: str, repository_path: str):
        self.db_path = db_path
        self.repository_path = repository_path
        self.parser = ImprovedGCodeParser()
        self.results = {
            'total_files': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'files_with_critical': 0,
            'files_with_warnings': 0,
            'files_with_bore_warnings': 0,
            'files_with_dimensional': 0,
            'critical_issues': [],
            'warnings': [],
            'bore_warnings': [],
            'dimensional_issues': [],
            'crash_patterns': defaultdict(int),
            'warning_patterns': defaultdict(int),
            'dimension_stats': {
                'round_sizes': [],
                'thicknesses': [],
                'hub_heights': []
            },
            'tool_usage': Counter(),
            'files_analyzed': []
        }

    def select_all_files(self):
        """Select ALL files with dimensions from database for comprehensive analysis"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        # Get ALL files with valid dimensions (no sampling, no limit)
        query = """
        SELECT program_number, file_path, outer_diameter, thickness, hub_height, tools_used
        FROM programs
        WHERE file_path IS NOT NULL
          AND outer_diameter IS NOT NULL
          AND thickness IS NOT NULL
        ORDER BY program_number
        """

        cursor.execute(query)
        files = cursor.fetchall()
        conn.close()

        print(f"Selected ALL {len(files)} files from database for comprehensive analysis")
        return files

    def analyze_file(self, program_number: str, file_path: str,
                    outer_diameter: float, thickness: float, hub_height: float, tools_used: str):
        """Analyze single G-code file for crash patterns"""

        self.results['total_files'] += 1

        # Track dimension statistics
        if outer_diameter:
            self.results['dimension_stats']['round_sizes'].append(outer_diameter)
        if thickness:
            self.results['dimension_stats']['thicknesses'].append(thickness)
        if hub_height:
            self.results['dimension_stats']['hub_heights'].append(hub_height)

        # Track tool usage
        if tools_used:
            try:
                tool_list = json.loads(tools_used) if isinstance(tools_used, str) else tools_used
                for tool in tool_list:
                    self.results['tool_usage'][tool] += 1
            except:
                pass

        # Check if file exists
        if not os.path.exists(file_path):
            self.results['failed_parses'] += 1
            return

        # Parse file
        try:
            parse_result = self.parser.parse_file(file_path)
            self.results['successful_parses'] += 1

            # Store file info
            file_info = {
                'program_number': program_number,
                'file_path': file_path,
                'outer_diameter': outer_diameter,
                'thickness': thickness,
                'hub_height': hub_height,
                'tools_used': tools_used,
                'has_critical': bool(parse_result.validation_issues),
                'has_warnings': bool(parse_result.validation_warnings),
                'has_bore_warnings': bool(parse_result.bore_warnings),
                'has_dimensional': bool(parse_result.dimensional_issues)
            }

            # Collect critical issues
            if parse_result.validation_issues:
                self.results['files_with_critical'] += 1
                for issue in parse_result.validation_issues:
                    self.results['critical_issues'].append({
                        'program': program_number,
                        'issue': issue,
                        'outer_diameter': outer_diameter,
                        'thickness': thickness,
                        'hub_height': hub_height
                    })
                    # Categorize crash pattern
                    if 'G00' in issue and 'negative Z' in issue:
                        self.results['crash_patterns']['G00_rapid_to_negative_Z'] += 1
                    elif 'G00' in issue and 'diagonal' in issue:
                        self.results['crash_patterns']['G00_diagonal_rapid_negative_Z'] += 1
                    elif 'G53' in issue and 'negative Z' in issue:
                        self.results['crash_patterns']['G53_tool_home_negative_Z'] += 1
                    elif 'jaw clearance' in issue.lower():
                        self.results['crash_patterns']['jaw_clearance_critical'] += 1
                    else:
                        self.results['crash_patterns']['other_critical'] += 1

                file_info['critical_issues'] = parse_result.validation_issues

            # Collect warnings
            if parse_result.validation_warnings:
                self.results['files_with_warnings'] += 1
                for warning in parse_result.validation_warnings:
                    self.results['warnings'].append({
                        'program': program_number,
                        'warning': warning,
                        'outer_diameter': outer_diameter,
                        'thickness': thickness
                    })
                    # Categorize warning pattern
                    if 'X0' in warning or 'Z0' in warning:
                        self.results['warning_patterns']['decimal_precision'] += 1
                    elif 'feed rate' in warning.lower():
                        self.results['warning_patterns']['feed_rate'] += 1
                    elif 'spindle speed' in warning.lower():
                        self.results['warning_patterns']['spindle_speed'] += 1
                    else:
                        self.results['warning_patterns']['other_warnings'] += 1

                file_info['warnings'] = parse_result.validation_warnings

            # Collect bore warnings
            if parse_result.bore_warnings:
                self.results['files_with_bore_warnings'] += 1
                for warning in parse_result.bore_warnings:
                    self.results['bore_warnings'].append({
                        'program': program_number,
                        'warning': warning,
                        'outer_diameter': outer_diameter,
                        'thickness': thickness
                    })

                file_info['bore_warnings'] = parse_result.bore_warnings

            # Collect dimensional issues
            if parse_result.dimensional_issues:
                self.results['files_with_dimensional'] += 1
                for issue in parse_result.dimensional_issues:
                    self.results['dimensional_issues'].append({
                        'program': program_number,
                        'issue': issue,
                        'outer_diameter': outer_diameter,
                        'thickness': thickness,
                        'hub_height': hub_height
                    })

                file_info['dimensional_issues'] = parse_result.dimensional_issues

            self.results['files_analyzed'].append(file_info)

        except Exception as e:
            self.results['failed_parses'] += 1
            print(f"Error parsing {program_number}: {str(e)}")

    def run_batch_analysis(self):
        """Run comprehensive batch analysis on ALL files in database"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE CRASH ANALYSIS - ALL FILES IN DATABASE")
        print(f"{'='*80}\n")

        files = self.select_all_files()

        for i, (program_number, file_path, round_size, thickness, hub_height, tools) in enumerate(files, 1):
            if i % 100 == 0:  # Progress every 100 files for large datasets
                print(f"Progress: {i}/{len(files)} files analyzed...")

            self.analyze_file(program_number, file_path, round_size, thickness, hub_height, tools)

        print(f"\nAnalysis complete: {self.results['successful_parses']}/{self.results['total_files']} files parsed successfully")

    def generate_report(self, output_file: str = None):
        """Generate comprehensive crash analysis report"""

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"crash_analysis_report_{timestamp}.txt"

        report_lines = []

        # Header
        report_lines.append("="*80)
        report_lines.append("COMPREHENSIVE G-CODE CRASH ANALYSIS REPORT")
        report_lines.append("COMPLETE DATABASE SCAN - 100% COVERAGE")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("="*80)
        report_lines.append("")

        # Summary Statistics
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-"*80)
        report_lines.append(f"Total Files Analyzed: {self.results['total_files']}")
        report_lines.append(f"Successfully Parsed: {self.results['successful_parses']}")
        report_lines.append(f"Failed to Parse: {self.results['failed_parses']}")
        report_lines.append(f"Files with Critical Issues: {self.results['files_with_critical']} ({self.results['files_with_critical']/max(1, self.results['total_files'])*100:.1f}%)")
        report_lines.append(f"Files with Warnings: {self.results['files_with_warnings']} ({self.results['files_with_warnings']/max(1, self.results['total_files'])*100:.1f}%)")
        report_lines.append(f"Files with Bore Warnings: {self.results['files_with_bore_warnings']} ({self.results['files_with_bore_warnings']/max(1, self.results['total_files'])*100:.1f}%)")
        report_lines.append(f"Files with Dimensional Issues: {self.results['files_with_dimensional']} ({self.results['files_with_dimensional']/max(1, self.results['total_files'])*100:.1f}%)")
        report_lines.append("")

        # Crash Pattern Analysis
        report_lines.append("CRASH PATTERN BREAKDOWN")
        report_lines.append("-"*80)
        for pattern, count in sorted(self.results['crash_patterns'].items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {pattern}: {count} occurrences")
        if not self.results['crash_patterns']:
            report_lines.append("  No crash patterns detected")
        report_lines.append("")

        # Warning Pattern Analysis
        report_lines.append("WARNING PATTERN BREAKDOWN")
        report_lines.append("-"*80)
        for pattern, count in sorted(self.results['warning_patterns'].items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {pattern}: {count} occurrences")
        if not self.results['warning_patterns']:
            report_lines.append("  No warning patterns detected")
        report_lines.append("")

        # Dimension Statistics
        report_lines.append("DIMENSION STATISTICS")
        report_lines.append("-"*80)
        if self.results['dimension_stats']['round_sizes']:
            rounds = self.results['dimension_stats']['round_sizes']
            report_lines.append(f"Outer Diameters (inches):")
            report_lines.append(f"  Min: {min(rounds):.3f}, Max: {max(rounds):.3f}, Avg: {sum(rounds)/len(rounds):.3f}")

        if self.results['dimension_stats']['thicknesses']:
            thicknesses = self.results['dimension_stats']['thicknesses']
            report_lines.append(f"Thicknesses (inches):")
            report_lines.append(f"  Min: {min(thicknesses):.3f}, Max: {max(thicknesses):.3f}, Avg: {sum(thicknesses)/len(thicknesses):.3f}")

        if self.results['dimension_stats']['hub_heights']:
            hub_heights = self.results['dimension_stats']['hub_heights']
            report_lines.append(f"Hub Heights (inches):")
            report_lines.append(f"  Min: {min(hub_heights):.3f}, Max: {max(hub_heights):.3f}, Avg: {sum(hub_heights)/len(hub_heights):.3f}")
        report_lines.append("")

        # Tool Usage Analysis
        report_lines.append("TOOL USAGE ANALYSIS")
        report_lines.append("-"*80)
        for tool, count in self.results['tool_usage'].most_common(10):
            report_lines.append(f"  {tool}: {count} programs")
        report_lines.append("")

        # Critical Issues Detail (Top 20)
        report_lines.append("CRITICAL ISSUES DETAIL (Top 20)")
        report_lines.append("-"*80)
        for i, issue_data in enumerate(self.results['critical_issues'][:20], 1):
            report_lines.append(f"{i}. Program: {issue_data['program']}")
            report_lines.append(f"   Dimensions: OD={issue_data['outer_diameter']}, Thick={issue_data['thickness']}, Hub={issue_data['hub_height']}")
            report_lines.append(f"   Issue: {issue_data['issue']}")
            report_lines.append("")

        if len(self.results['critical_issues']) > 20:
            report_lines.append(f"... and {len(self.results['critical_issues']) - 20} more critical issues")
            report_lines.append("")

        # Recommendations
        report_lines.append("RECOMMENDATIONS")
        report_lines.append("-"*80)

        # Analyze patterns for recommendations
        if self.results['crash_patterns']['G00_rapid_to_negative_Z'] > 5:
            report_lines.append("• HIGH PRIORITY: G00 rapid to negative Z pattern detected frequently")
            report_lines.append("  Consider enhancing detection for incremental depth moves")
            report_lines.append("")

        if self.results['crash_patterns']['jaw_clearance_critical'] > 3:
            report_lines.append("• MEDIUM PRIORITY: Jaw clearance violations detected")
            report_lines.append("  Review jaw clearance calculation for edge cases")
            report_lines.append("")

        if self.results['warning_patterns']['decimal_precision'] > 10:
            report_lines.append("• LOW PRIORITY: Many decimal precision warnings (X0, Z0)")
            report_lines.append("  These are suggestions, not safety issues")
            report_lines.append("")

        if self.results['files_with_bore_warnings'] > 20:
            report_lines.append("• REVIEW: High number of bore warnings")
            report_lines.append("  May indicate need for bore depth validation refinement")
            report_lines.append("")

        # Look for new crash patterns in critical issues
        report_lines.append("POTENTIAL NEW CRASH PATTERNS TO INVESTIGATE:")
        report_lines.append("")

        # Analyze unclassified critical issues
        unique_patterns = set()
        for issue_data in self.results['critical_issues']:
            issue_text = issue_data['issue']
            # Extract key phrases
            if 'G00' not in issue_text and 'G53' not in issue_text and 'jaw' not in issue_text.lower():
                unique_patterns.add(issue_text[:100])  # First 100 chars for uniqueness

        if unique_patterns:
            for i, pattern in enumerate(list(unique_patterns)[:10], 1):
                report_lines.append(f"{i}. {pattern}")
        else:
            report_lines.append("  No unclassified patterns detected - current detection appears comprehensive")

        report_lines.append("")
        report_lines.append("="*80)
        report_lines.append("END OF REPORT")
        report_lines.append("="*80)

        # Write report to file
        report_text = "\n".join(report_lines)

        with open(output_file, 'w') as f:
            f.write(report_text)

        print(f"\nReport saved to: {output_file}")

        # Also return report text for display
        return report_text

    def save_detailed_json(self, output_file: str = None):
        """Save detailed results as JSON for further analysis"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"crash_analysis_data_{timestamp}.json"

        # Prepare serializable data
        export_data = {
            'summary': {
                'total_files': self.results['total_files'],
                'successful_parses': self.results['successful_parses'],
                'failed_parses': self.results['failed_parses'],
                'files_with_critical': self.results['files_with_critical'],
                'files_with_warnings': self.results['files_with_warnings'],
                'files_with_bore_warnings': self.results['files_with_bore_warnings'],
                'files_with_dimensional': self.results['files_with_dimensional']
            },
            'crash_patterns': dict(self.results['crash_patterns']),
            'warning_patterns': dict(self.results['warning_patterns']),
            'dimension_stats': self.results['dimension_stats'],
            'tool_usage': dict(self.results['tool_usage']),
            'critical_issues': self.results['critical_issues'],
            'warnings': self.results['warnings'],
            'bore_warnings': self.results['bore_warnings'],
            'dimensional_issues': self.results['dimensional_issues'],
            'files_analyzed': self.results['files_analyzed']
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Detailed data saved to: {output_file}")


def main():
    """Main entry point for batch crash analysis"""

    # Configuration
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    repository_path = r"l:\My Drive\Home\File organizer\repository"

    # Create analyzer
    analyzer = BatchCrashAnalyzer(db_path, repository_path)

    # Run comprehensive analysis on ALL files in database
    analyzer.run_batch_analysis()

    # Generate report
    report_text = analyzer.generate_report()

    # Save detailed JSON data
    analyzer.save_detailed_json()

    # Display report to console
    print("\n" + report_text)


if __name__ == "__main__":
    main()
