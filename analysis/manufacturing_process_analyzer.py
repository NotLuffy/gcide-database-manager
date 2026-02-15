"""
Manufacturing Process Pattern Analyzer

Analyzes G-code files to discover manufacturing patterns, processes,
and best practices for different part types, dimensions, and operations.

Focus areas:
1. Process sequences by part type
2. Thickness ranges and their impact on operations
3. Hub height variations and their manufacturing approach
4. Steel ring manufacturing patterns
5. Common operation sequences and patterns
6. Correlations between dimensions and tooling/feeds/speeds

Author: G-Code Database Manager
Date: 2026-02-08
"""

import sqlite3
import os
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime


class ManufacturingProcessAnalyzer:
    """Analyzes G-code files to discover manufacturing patterns"""

    def __init__(self, db_path: str, repository_path: str):
        self.db_path = db_path
        self.repository_path = repository_path
        self.patterns = {
            'thickness_categories': defaultdict(list),  # Group by thickness ranges
            'hub_height_categories': defaultdict(list),  # Group by hub heights
            'od_categories': defaultdict(list),  # Group by outer diameter
            'operation_sequences': defaultdict(int),  # Common operation orders
            'tool_sequences': defaultdict(int),  # Common tool change sequences
            'feed_speed_by_dimension': defaultdict(list),  # Feeds/speeds by part size
            'side1_vs_side2_patterns': defaultdict(int),  # Side 1 vs Side 2 differences
            'bore_patterns': defaultdict(list),  # Bore-specific patterns
            'threading_patterns': defaultdict(list),  # Threading patterns
            'facing_patterns': defaultdict(list),  # Facing operation patterns
            'special_features': defaultdict(int),  # Special features detected
            'feed_speeds_by_op': defaultdict(list),  # Feed/speed by operation type
            'ring_parts': [],  # Parts that are likely rings (large bore/OD ratio)
            'depth_of_cut_patterns': defaultdict(list),  # Depth of cut by operation
            'coolant_patterns': defaultdict(int),  # Coolant usage patterns
            'spindle_speeds_by_tool': defaultdict(list),  # Spindle speeds by tool
        }

    def categorize_by_dimensions(self, od: float, thickness: float, hub_height: Optional[float]) -> Tuple[str, str, str]:
        """Categorize part by dimensional ranges"""
        # OD categories
        if od <= 6.0:
            od_cat = "Small (≤6\")"
        elif od <= 8.0:
            od_cat = "Medium (6-8\")"
        elif od <= 10.0:
            od_cat = "Large (8-10\")"
        else:
            od_cat = "Extra Large (>10\")"

        # Thickness categories
        if thickness <= 0.5:
            thick_cat = "Thin (≤0.5\")"
        elif thickness <= 1.5:
            thick_cat = "Standard (0.5-1.5\")"
        elif thickness <= 3.0:
            thick_cat = "Thick (1.5-3.0\")"
        else:
            thick_cat = "Extra Thick (>3.0\")"

        # Hub height categories
        if hub_height is None or hub_height < 0.3:
            hub_cat = "No Hub (<0.3\")"
        elif hub_height <= 0.5:
            hub_cat = "Small Hub (0.3-0.5\")"
        elif hub_height <= 1.0:
            hub_cat = "Medium Hub (0.5-1.0\")"
        else:
            hub_cat = "Large Hub (>1.0\")"

        return od_cat, thick_cat, hub_cat

    def extract_operation_sequence(self, gcode_content: str) -> List[str]:
        """Extract operation sequence from G-code comments"""
        operations = []
        lines = gcode_content.split('\n')

        for line in lines:
            line_upper = line.upper().strip()

            # Extract operation from comments
            if '(FACE' in line_upper or '( FACE' in line_upper:
                operations.append('FACE')
            elif '(BORE' in line_upper or '( BORE' in line_upper:
                operations.append('BORE')
            elif '(DRILL' in line_upper or '( DRILL' in line_upper:
                operations.append('DRILL')
            elif '(THREAD' in line_upper or '( THREAD' in line_upper:
                operations.append('THREAD')
            elif '(TURN' in line_upper or '( TURN' in line_upper:
                operations.append('TURN')
            elif '(CHAMFER' in line_upper or '( CHAMFER' in line_upper:
                operations.append('CHAMFER')
            elif 'SIDE 1' in line_upper or 'SIDE1' in line_upper:
                operations.append('--- SIDE 1 ---')
            elif 'SIDE 2' in line_upper or 'SIDE2' in line_upper:
                operations.append('--- SIDE 2 ---')

        return operations

    def extract_tool_sequence(self, gcode_content: str) -> List[str]:
        """Extract tool change sequence"""
        tools = []
        lines = gcode_content.split('\n')

        current_tool = None
        for line in lines:
            line_upper = line.upper().strip()

            # Tool change
            if line_upper.startswith('T') and any(c.isdigit() for c in line_upper):
                match = re.search(r'T(\d+)', line_upper)
                if match:
                    tool = 'T' + match.group(1)
                    if tool != current_tool:
                        tools.append(tool)
                        current_tool = tool

        return tools

    def detect_special_features(self, gcode_content: str) -> List[str]:
        """Detect special features in G-code"""
        features = []
        content_upper = gcode_content.upper()

        # Threading
        if 'G32' in content_upper or 'G33' in content_upper or 'G76' in content_upper:
            features.append('Threading')

        # Grooving
        if 'GROOVE' in content_upper or 'GROOVING' in content_upper:
            features.append('Grooving')

        # Multiple diameters (stepped part)
        if 'STEP' in content_upper or 'DIAMETER' in content_upper:
            features.append('Stepped')

        # Tapping
        if 'TAP' in content_upper or 'G84' in content_upper:
            features.append('Tapping')

        # Chamfer
        if 'CHAMFER' in content_upper:
            features.append('Chamfer')

        # Counterbore
        if 'COUNTERBORE' in content_upper or 'CBORE' in content_upper:
            features.append('Counterbore')

        return features

    def extract_feed_speed_data(self, gcode_content: str) -> List[Dict]:
        """Extract feed rates and spindle speeds from G-code"""
        feed_speed_data = []
        lines = gcode_content.split('\n')

        current_operation = None
        current_tool = None

        for line in lines:
            line_upper = line.upper().strip()

            # Track current operation
            if '(DRILL' in line_upper:
                current_operation = 'DRILL'
            elif '(BORE' in line_upper:
                current_operation = 'BORE'
            elif '(FACE' in line_upper:
                current_operation = 'FACE'
            elif '(TURN' in line_upper:
                current_operation = 'TURN'
            elif '(THREAD' in line_upper:
                current_operation = 'THREAD'

            # Track tool
            if line_upper.startswith('T') and any(c.isdigit() for c in line_upper):
                match = re.search(r'T(\d+)', line_upper)
                if match:
                    current_tool = 'T' + match.group(1)

            # Extract feed rate (F)
            if 'F' in line_upper and 'G01' in line_upper:
                match = re.search(r'F\s*(\d+\.?\d*)', line_upper)
                if match:
                    feed_rate = float(match.group(1))

                    # Extract spindle speed if present
                    spindle_speed = None
                    if 'S' in line_upper:
                        s_match = re.search(r'S\s*(\d+)', line_upper)
                        if s_match:
                            spindle_speed = int(s_match.group(1))

                    if current_operation:
                        feed_speed_data.append({
                            'operation': current_operation,
                            'tool': current_tool,
                            'feed_rate': feed_rate,
                            'spindle_speed': spindle_speed
                        })

        return feed_speed_data

    def detect_ring_part(self, gcode_content: str, od: float) -> Optional[Dict]:
        """Detect if part is a ring (large center bore relative to OD)"""
        # Extract center bore diameter from G-code
        center_bore = None
        lines = gcode_content.split('\n')

        for line in lines:
            # Look for bore diameter in comments
            if 'CENTER BORE' in line.upper() or 'CB' in line.upper():
                # Try to extract diameter
                match = re.search(r'(\d+\.?\d*)\s*MM', line.upper())
                if match:
                    cb_mm = float(match.group(1))
                    center_bore = cb_mm / 25.4  # Convert to inches
                    break

        if center_bore:
            ratio = center_bore / od
            if ratio > 0.5:  # If CB is more than 50% of OD, likely a ring
                return {
                    'od': od,
                    'center_bore': center_bore,
                    'ratio': ratio,
                    'type': 'Ring' if ratio > 0.7 else 'Thick-walled ring'
                }

        return None

    def analyze_side_patterns(self, gcode_content: str) -> Dict:
        """Analyze differences between Side 1 and Side 2 operations"""
        lines = gcode_content.split('\n')

        side1_ops = []
        side2_ops = []
        current_side = None

        for line in lines:
            line_upper = line.upper().strip()

            if 'SIDE 1' in line_upper or 'SIDE1' in line_upper:
                current_side = 1
            elif 'SIDE 2' in line_upper or 'SIDE2' in line_upper:
                current_side = 2

            # Track operations
            if current_side == 1:
                if '(DRILL' in line_upper:
                    side1_ops.append('DRILL')
                elif '(BORE' in line_upper:
                    side1_ops.append('BORE')
                elif '(FACE' in line_upper:
                    side1_ops.append('FACE')
                elif '(THREAD' in line_upper:
                    side1_ops.append('THREAD')
            elif current_side == 2:
                if '(DRILL' in line_upper:
                    side2_ops.append('DRILL')
                elif '(BORE' in line_upper:
                    side2_ops.append('BORE')
                elif '(FACE' in line_upper:
                    side2_ops.append('FACE')
                elif '(THREAD' in line_upper:
                    side2_ops.append('THREAD')

        return {
            'side1_ops': side1_ops,
            'side2_ops': side2_ops,
            'has_side1': len(side1_ops) > 0,
            'has_side2': len(side2_ops) > 0,
            'operations_match': Counter(side1_ops) == Counter(side2_ops)
        }

    def analyze_files(self, sample_size: int = 500):
        """Analyze sample of files for patterns"""
        print(f"\n{'='*80}")
        print(f"MANUFACTURING PROCESS PATTERN ANALYSIS")
        print(f"Analyzing {sample_size} random files from database")
        print(f"{'='*80}\n")

        # Get random sample of files
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        query = """
        SELECT program_number, file_path, outer_diameter, thickness, hub_height
        FROM programs
        WHERE file_path IS NOT NULL
          AND outer_diameter IS NOT NULL
          AND thickness IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
        """

        cursor.execute(query, (sample_size,))
        files = cursor.fetchall()
        conn.close()

        print(f"Selected {len(files)} files for analysis\n")

        # Analyze each file
        for i, (program_number, file_path, od, thickness, hub_height) in enumerate(files, 1):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(files)} files analyzed...")

            if not os.path.exists(file_path):
                continue

            try:
                # Read G-code
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    gcode_content = f.read()

                # Categorize by dimensions
                od_cat, thick_cat, hub_cat = self.categorize_by_dimensions(od, thickness, hub_height)

                # Store in categories
                part_info = {
                    'program': program_number,
                    'od': od,
                    'thickness': thickness,
                    'hub_height': hub_height
                }

                self.patterns['od_categories'][od_cat].append(part_info)
                self.patterns['thickness_categories'][thick_cat].append(part_info)
                self.patterns['hub_height_categories'][hub_cat].append(part_info)

                # Extract operation sequence
                operations = self.extract_operation_sequence(gcode_content)
                if operations:
                    op_sequence = ' → '.join(operations)
                    self.patterns['operation_sequences'][op_sequence] += 1

                # Extract tool sequence
                tools = self.extract_tool_sequence(gcode_content)
                if tools:
                    tool_sequence = ' → '.join(tools)
                    self.patterns['tool_sequences'][tool_sequence] += 1

                # Detect special features
                features = self.detect_special_features(gcode_content)
                for feature in features:
                    self.patterns['special_features'][feature] += 1

                # Analyze side patterns
                side_analysis = self.analyze_side_patterns(gcode_content)
                if side_analysis['has_side1'] and side_analysis['has_side2']:
                    if side_analysis['operations_match']:
                        self.patterns['side1_vs_side2_patterns']['Operations Match'] += 1
                    else:
                        self.patterns['side1_vs_side2_patterns']['Operations Differ'] += 1

                    # Track specific patterns
                    side1_str = ', '.join(side_analysis['side1_ops'])
                    side2_str = ', '.join(side_analysis['side2_ops'])
                    pattern = f"S1:[{side1_str}] vs S2:[{side2_str}]"
                    self.patterns['side1_vs_side2_patterns'][pattern] += 1

                # Extract feed/speed data
                feed_speed_data = self.extract_feed_speed_data(gcode_content)
                for data in feed_speed_data:
                    self.patterns['feed_speeds_by_op'][data['operation']].append(data)
                    if data['spindle_speed'] and data['tool']:
                        self.patterns['spindle_speeds_by_tool'][data['tool']].append(data['spindle_speed'])

                # Detect ring parts
                ring_info = self.detect_ring_part(gcode_content, od)
                if ring_info:
                    ring_info['program'] = program_number
                    ring_info['thickness'] = thickness
                    self.patterns['ring_parts'].append(ring_info)

            except Exception as e:
                print(f"Error analyzing {program_number}: {e}")

        print(f"\nAnalysis complete!\n")

    def generate_report(self, output_file: str = None):
        """Generate comprehensive manufacturing pattern report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"manufacturing_patterns_{timestamp}.txt"

        report_lines = []

        # Header
        report_lines.append("="*80)
        report_lines.append("MANUFACTURING PROCESS PATTERN ANALYSIS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("="*80)
        report_lines.append("")

        # Part Size Distribution
        report_lines.append("PART SIZE DISTRIBUTION")
        report_lines.append("-"*80)

        report_lines.append("\nOuter Diameter Categories:")
        for od_cat, parts in sorted(self.patterns['od_categories'].items()):
            avg_thickness = sum(p['thickness'] for p in parts) / len(parts)
            avg_hub = sum(p.get('hub_height', 0) or 0 for p in parts) / len(parts)
            report_lines.append(f"  {od_cat}: {len(parts)} parts")
            report_lines.append(f"    Avg Thickness: {avg_thickness:.3f}\"")
            report_lines.append(f"    Avg Hub Height: {avg_hub:.3f}\"")

        report_lines.append("\nThickness Categories:")
        for thick_cat, parts in sorted(self.patterns['thickness_categories'].items()):
            avg_od = sum(p['od'] for p in parts) / len(parts)
            report_lines.append(f"  {thick_cat}: {len(parts)} parts (Avg OD: {avg_od:.3f}\")")

        report_lines.append("\nHub Height Categories:")
        for hub_cat, parts in sorted(self.patterns['hub_height_categories'].items()):
            avg_od = sum(p['od'] for p in parts) / len(parts)
            avg_thickness = sum(p['thickness'] for p in parts) / len(parts)
            report_lines.append(f"  {hub_cat}: {len(parts)} parts")
            report_lines.append(f"    Avg OD: {avg_od:.3f}\", Avg Thickness: {avg_thickness:.3f}\"")

        report_lines.append("")

        # Most Common Operation Sequences
        report_lines.append("MOST COMMON OPERATION SEQUENCES (Top 20)")
        report_lines.append("-"*80)
        for i, (sequence, count) in enumerate(sorted(self.patterns['operation_sequences'].items(),
                                                     key=lambda x: x[1], reverse=True)[:20], 1):
            report_lines.append(f"{i}. ({count} programs) {sequence}")
        report_lines.append("")

        # Most Common Tool Sequences
        report_lines.append("MOST COMMON TOOL SEQUENCES (Top 20)")
        report_lines.append("-"*80)
        for i, (sequence, count) in enumerate(sorted(self.patterns['tool_sequences'].items(),
                                                     key=lambda x: x[1], reverse=True)[:20], 1):
            report_lines.append(f"{i}. ({count} programs) {sequence}")
        report_lines.append("")

        # Special Features
        report_lines.append("SPECIAL FEATURES DETECTED")
        report_lines.append("-"*80)
        for feature, count in sorted(self.patterns['special_features'].items(),
                                     key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {feature}: {count} programs")
        report_lines.append("")

        # Side 1 vs Side 2 Patterns
        report_lines.append("SIDE 1 vs SIDE 2 OPERATION PATTERNS")
        report_lines.append("-"*80)
        for pattern, count in sorted(self.patterns['side1_vs_side2_patterns'].items(),
                                     key=lambda x: x[1], reverse=True)[:15]:
            report_lines.append(f"  ({count}x) {pattern}")
        report_lines.append("")

        # Feed and Speed Patterns by Operation
        report_lines.append("FEED & SPEED PATTERNS BY OPERATION")
        report_lines.append("-"*80)
        for operation, data_list in sorted(self.patterns['feed_speeds_by_op'].items()):
            if data_list:
                feed_rates = [d['feed_rate'] for d in data_list]
                spindle_speeds = [d['spindle_speed'] for d in data_list if d['spindle_speed']]

                report_lines.append(f"\n{operation}:")
                report_lines.append(f"  Feed Rates: Min={min(feed_rates):.3f}, Max={max(feed_rates):.3f}, Avg={sum(feed_rates)/len(feed_rates):.3f} IPR")
                if spindle_speeds:
                    report_lines.append(f"  Spindle Speeds: Min={min(spindle_speeds)}, Max={max(spindle_speeds)}, Avg={int(sum(spindle_speeds)/len(spindle_speeds))} RPM")
                report_lines.append(f"  Samples: {len(data_list)}")
        report_lines.append("")

        # Ring Parts Analysis
        if self.patterns['ring_parts']:
            report_lines.append("RING PARTS DETECTED (Large Bore/OD Ratio)")
            report_lines.append("-"*80)
            report_lines.append(f"Total Ring Parts: {len(self.patterns['ring_parts'])}")
            report_lines.append("")
            report_lines.append("Examples:")
            for i, ring in enumerate(self.patterns['ring_parts'][:10], 1):
                report_lines.append(f"{i}. {ring['program']}: OD={ring['od']:.3f}\", CB={ring['center_bore']:.3f}\", Ratio={ring['ratio']:.2%} - {ring['type']}")
            if len(self.patterns['ring_parts']) > 10:
                report_lines.append(f"... and {len(self.patterns['ring_parts']) - 10} more ring parts")
            report_lines.append("")

        # Spindle Speeds by Tool
        report_lines.append("AVERAGE SPINDLE SPEEDS BY TOOL")
        report_lines.append("-"*80)
        for tool, speeds in sorted(self.patterns['spindle_speeds_by_tool'].items()):
            if speeds:
                avg_speed = int(sum(speeds) / len(speeds))
                min_speed = min(speeds)
                max_speed = max(speeds)
                report_lines.append(f"  {tool}: Avg={avg_speed} RPM, Range={min_speed}-{max_speed} RPM ({len(speeds)} samples)")
        report_lines.append("")

        # Key Insights
        report_lines.append("KEY MANUFACTURING INSIGHTS")
        report_lines.append("-"*80)

        # Most common tool sequence
        if self.patterns['tool_sequences']:
            most_common_tools = max(self.patterns['tool_sequences'].items(), key=lambda x: x[1])
            report_lines.append(f"• Most Common Tool Sequence: {most_common_tools[0]}")
            report_lines.append(f"  Used in {most_common_tools[1]} programs")
            report_lines.append("")

        # Most common operation sequence
        if self.patterns['operation_sequences']:
            most_common_ops = max(self.patterns['operation_sequences'].items(), key=lambda x: x[1])
            report_lines.append(f"• Most Common Operation Sequence: {most_common_ops[0]}")
            report_lines.append(f"  Used in {most_common_ops[1]} programs")
            report_lines.append("")

        # Feature prevalence
        if self.patterns['special_features']:
            report_lines.append("• Special Feature Prevalence:")
            total_programs = sum(len(parts) for parts in self.patterns['od_categories'].values())
            for feature, count in sorted(self.patterns['special_features'].items(),
                                        key=lambda x: x[1], reverse=True)[:5]:
                percentage = (count / total_programs) * 100
                report_lines.append(f"  - {feature}: {percentage:.1f}% of programs")

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

    analyzer = ManufacturingProcessAnalyzer(db_path, repository_path)

    # Analyze 1000 random files for comprehensive insights
    analyzer.analyze_files(sample_size=1000)

    # Generate report
    report = analyzer.generate_report()
    print(report)


if __name__ == "__main__":
    main()
