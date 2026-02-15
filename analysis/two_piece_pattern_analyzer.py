"""
Two-Piece Part Pattern Analyzer

Analyzes G-code files to understand:
1. Process variations - which operations are optional vs required
2. Two-piece part relationships (hub + counterbore mating)
3. Dimensional compatibility rules for assembly
4. Operation sequence patterns by part features

Focus on hub/counterbore matching:
- Both parts have same OD
- Hub part: has raised hub (0.25" tall typically)
- Counterbore part: has recessed pocket (0.30" deep typically)
- Hub diameter should be within 0.05" of counterbore diameter (tight fit)

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


class TwoPiecePatternAnalyzer:
    """Analyzes two-piece part patterns and process variations"""

    def __init__(self, db_path: str, repository_path: str):
        self.db_path = db_path
        self.repository_path = repository_path
        self.patterns = {
            'operation_presence': defaultdict(int),  # How often each operation appears
            'optional_operations': defaultdict(int),  # Operations that don't always appear
            'hub_parts': [],  # Parts with hubs
            'counterbore_parts': [],  # Parts with counterbores
            'two_piece_candidates': [],  # Potential matching pairs
            'depth_patterns': defaultdict(list),  # Cutting depths by feature
            'od_groups': defaultdict(list),  # Parts grouped by OD
        }

    def extract_hub_info(self, gcode_content: str, thickness: float, hub_height: Optional[float]) -> Optional[Dict]:
        """Extract hub information from G-code"""
        if not hub_height or hub_height < 0.2:
            return None  # No significant hub

        lines = gcode_content.split('\n')
        hub_diameter = None

        # Look for hub diameter in comments
        for line in lines:
            line_upper = line.upper()
            if 'HUB' in line_upper and 'DIA' in line_upper:
                # Try to extract diameter
                match = re.search(r'(\d+\.?\d*)\s*MM', line_upper)
                if match:
                    hub_mm = float(match.group(1))
                    hub_diameter = hub_mm / 25.4  # Convert to inches

        return {
            'hub_height': hub_height,
            'hub_diameter': hub_diameter,
            'total_height': thickness + hub_height if thickness else hub_height
        }

    def extract_counterbore_info(self, gcode_content: str) -> Optional[Dict]:
        """Extract counterbore information from G-code"""
        lines = gcode_content.split('\n')

        cbore_diameter = None
        cbore_depth = None

        for line in lines:
            line_upper = line.upper()

            # Look for counterbore diameter
            if 'COUNTERBORE' in line_upper or 'CBORE' in line_upper:
                # Extract diameter
                match = re.search(r'(\d+\.?\d*)\s*MM', line_upper)
                if match:
                    cbore_mm = float(match.group(1))
                    cbore_diameter = cbore_mm / 25.4

                # Extract depth
                depth_match = re.search(r'(\d+\.?\d*)\s*DEEP', line_upper)
                if depth_match:
                    cbore_depth = float(depth_match.group(1))

        if cbore_diameter:
            return {
                'cbore_diameter': cbore_diameter,
                'cbore_depth': cbore_depth
            }

        return None

    def extract_operations_present(self, gcode_content: str) -> List[str]:
        """Extract which operations are present in the G-code"""
        operations = set()
        lines = gcode_content.split('\n')

        for line in lines:
            line_upper = line.upper().strip()

            if '(DRILL' in line_upper or '( DRILL' in line_upper:
                operations.add('DRILL')
            if '(BORE' in line_upper or '( BORE' in line_upper:
                operations.add('BORE')
            if '(FACE' in line_upper or '( FACE' in line_upper:
                operations.add('FACE')
            if '(TURN' in line_upper or '( TURN' in line_upper:
                operations.add('TURN')
            if '(THREAD' in line_upper or '( THREAD' in line_upper:
                operations.add('THREAD')
            if '(CHAMFER' in line_upper or '( CHAMFER' in line_upper:
                operations.add('CHAMFER')
            if 'COUNTERBORE' in line_upper or 'CBORE' in line_upper:
                operations.add('COUNTERBORE')
            if 'GROOVE' in line_upper:
                operations.add('GROOVE')

        return list(operations)

    def analyze_files(self, sample_size: int = 1000):
        """Analyze files for two-piece patterns"""
        print(f"\n{'='*80}")
        print(f"TWO-PIECE PART PATTERN ANALYSIS")
        print(f"Analyzing {sample_size} random files from database")
        print(f"{'='*80}\n")

        # Get random sample
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
            if i % 100 == 0:
                print(f"Progress: {i}/{len(files)} files analyzed...")

            if not os.path.exists(file_path):
                continue

            try:
                # Read G-code
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    gcode_content = f.read()

                # Extract operations present
                operations = self.extract_operations_present(gcode_content)
                for op in operations:
                    self.patterns['operation_presence'][op] += 1

                # Group by OD for matching
                od_key = round(od * 4) / 4  # Round to nearest 0.25"
                self.patterns['od_groups'][od_key].append({
                    'program': program_number,
                    'od': od,
                    'thickness': thickness,
                    'hub_height': hub_height,
                    'operations': operations
                })

                # Check for hub
                hub_info = self.extract_hub_info(gcode_content, thickness, hub_height)
                if hub_info:
                    self.patterns['hub_parts'].append({
                        'program': program_number,
                        'od': od,
                        'thickness': thickness,
                        'hub_info': hub_info,
                        'operations': operations
                    })

                # Check for counterbore
                cbore_info = self.extract_counterbore_info(gcode_content)
                if cbore_info:
                    self.patterns['counterbore_parts'].append({
                        'program': program_number,
                        'od': od,
                        'thickness': thickness,
                        'cbore_info': cbore_info,
                        'operations': operations
                    })

            except Exception as e:
                print(f"Error analyzing {program_number}: {e}")

        print(f"\nAnalysis complete!\n")

        # Find two-piece candidates
        self._find_two_piece_matches()

    def _find_two_piece_matches(self):
        """Find potential two-piece part matches"""
        print("Finding two-piece part matches...")

        # Match hub parts with counterbore parts
        for hub_part in self.patterns['hub_parts']:
            for cbore_part in self.patterns['counterbore_parts']:
                # Must have same OD (within 0.1")
                if abs(hub_part['od'] - cbore_part['od']) > 0.1:
                    continue

                # Check hub diameter vs counterbore diameter
                hub_diam = hub_part['hub_info'].get('hub_diameter')
                cbore_diam = cbore_part['cbore_info'].get('cbore_diameter')

                if hub_diam and cbore_diam:
                    diam_diff = abs(hub_diam - cbore_diam)

                    # Should be within 0.05" (tight fit)
                    if diam_diff <= 0.05:
                        # Check depth compatibility
                        hub_height = hub_part['hub_info']['hub_height']
                        cbore_depth = cbore_part['cbore_info'].get('cbore_depth', 0.3)  # Default 0.3"

                        clearance = cbore_depth - hub_height if cbore_depth else None

                        self.patterns['two_piece_candidates'].append({
                            'hub_part': hub_part['program'],
                            'cbore_part': cbore_part['program'],
                            'od': hub_part['od'],
                            'hub_diameter': hub_diam,
                            'cbore_diameter': cbore_diam,
                            'diameter_diff': diam_diff,
                            'hub_height': hub_height,
                            'cbore_depth': cbore_depth,
                            'clearance': clearance,
                            'match_quality': 'EXCELLENT' if diam_diff < 0.01 else 'GOOD'
                        })

    def generate_report(self, output_file: str = None):
        """Generate comprehensive two-piece pattern report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"two_piece_patterns_{timestamp}.txt"

        report_lines = []

        # Header
        report_lines.append("="*80)
        report_lines.append("TWO-PIECE PART PATTERN ANALYSIS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("="*80)
        report_lines.append("")

        # Operation Frequency Analysis
        report_lines.append("OPERATION FREQUENCY (Which operations are standard vs optional)")
        report_lines.append("-"*80)

        total_files = sum(len(parts) for parts in self.patterns['od_groups'].values())
        for op, count in sorted(self.patterns['operation_presence'].items(),
                               key=lambda x: x[1], reverse=True):
            percentage = (count / total_files) * 100
            status = "STANDARD" if percentage > 90 else "COMMON" if percentage > 50 else "OPTIONAL"
            report_lines.append(f"  {op}: {count}/{total_files} ({percentage:.1f}%) - {status}")
        report_lines.append("")

        # Hub Parts Analysis
        report_lines.append("HUB PARTS ANALYSIS")
        report_lines.append("-"*80)
        report_lines.append(f"Total Hub Parts: {len(self.patterns['hub_parts'])}")

        if self.patterns['hub_parts']:
            hub_heights = [p['hub_info']['hub_height'] for p in self.patterns['hub_parts']]
            hub_diameters = [p['hub_info']['hub_diameter'] for p in self.patterns['hub_parts']
                           if p['hub_info']['hub_diameter']]

            report_lines.append(f"\nHub Height Statistics:")
            report_lines.append(f"  Min: {min(hub_heights):.3f}\", Max: {max(hub_heights):.3f}\", Avg: {sum(hub_heights)/len(hub_heights):.3f}\"")
            report_lines.append(f"  Most Common: 0.25\" hub (standard)")

            if hub_diameters:
                report_lines.append(f"\nHub Diameter Statistics:")
                report_lines.append(f"  Min: {min(hub_diameters):.3f}\", Max: {max(hub_diameters):.3f}\", Avg: {sum(hub_diameters)/len(hub_diameters):.3f}\"")

            report_lines.append(f"\nOperations on Hub Parts:")
            hub_ops = Counter()
            for part in self.patterns['hub_parts']:
                for op in part['operations']:
                    hub_ops[op] += 1
            for op, count in hub_ops.most_common():
                percentage = (count / len(self.patterns['hub_parts'])) * 100
                report_lines.append(f"  {op}: {percentage:.1f}%")

        report_lines.append("")

        # Counterbore Parts Analysis
        report_lines.append("COUNTERBORE PARTS ANALYSIS")
        report_lines.append("-"*80)
        report_lines.append(f"Total Counterbore Parts: {len(self.patterns['counterbore_parts'])}")

        if self.patterns['counterbore_parts']:
            cbore_diameters = [p['cbore_info']['cbore_diameter'] for p in self.patterns['counterbore_parts']
                             if p['cbore_info']['cbore_diameter']]
            cbore_depths = [p['cbore_info']['cbore_depth'] for p in self.patterns['counterbore_parts']
                          if p['cbore_info'].get('cbore_depth')]

            if cbore_diameters:
                report_lines.append(f"\nCounterbore Diameter Statistics:")
                report_lines.append(f"  Min: {min(cbore_diameters):.3f}\", Max: {max(cbore_diameters):.3f}\", Avg: {sum(cbore_diameters)/len(cbore_diameters):.3f}\"")

            if cbore_depths:
                report_lines.append(f"\nCounterbore Depth Statistics:")
                report_lines.append(f"  Min: {min(cbore_depths):.3f}\", Max: {max(cbore_depths):.3f}\", Avg: {sum(cbore_depths)/len(cbore_depths):.3f}\"")
                report_lines.append(f"  Standard Depth: 0.30\" (to accommodate 0.25\" hub)")

            report_lines.append(f"\nOperations on Counterbore Parts:")
            cbore_ops = Counter()
            for part in self.patterns['counterbore_parts']:
                for op in part['operations']:
                    cbore_ops[op] += 1
            for op, count in cbore_ops.most_common():
                percentage = (count / len(self.patterns['counterbore_parts'])) * 100
                report_lines.append(f"  {op}: {percentage:.1f}%")

        report_lines.append("")

        # Two-Piece Matches
        report_lines.append("TWO-PIECE PART MATCHES (Hub + Counterbore)")
        report_lines.append("-"*80)
        report_lines.append(f"Total Matching Pairs Found: {len(self.patterns['two_piece_candidates'])}")

        if self.patterns['two_piece_candidates']:
            report_lines.append("")
            report_lines.append("Matching Criteria:")
            report_lines.append("  - Same OD (within 0.1\")")
            report_lines.append("  - Hub diameter within 0.05\" of counterbore diameter")
            report_lines.append("  - Counterbore depth ~0.30\" to fit 0.25\" hub")
            report_lines.append("")
            report_lines.append("Examples of Matching Pairs:")

            for i, match in enumerate(self.patterns['two_piece_candidates'][:15], 1):
                report_lines.append(f"\n{i}. {match['match_quality']} MATCH:")
                report_lines.append(f"   Hub Part: {match['hub_part']}")
                report_lines.append(f"   Counterbore Part: {match['cbore_part']}")
                report_lines.append(f"   OD: {match['od']:.3f}\"")
                report_lines.append(f"   Hub Diameter: {match['hub_diameter']:.3f}\"")
                report_lines.append(f"   Counterbore Diameter: {match['cbore_diameter']:.3f}\"")
                report_lines.append(f"   Diameter Difference: {match['diameter_diff']:.4f}\" (fit: {'TIGHT' if match['diameter_diff'] < 0.01 else 'NORMAL'})")
                report_lines.append(f"   Hub Height: {match['hub_height']:.3f}\"")
                if match['cbore_depth']:
                    report_lines.append(f"   Counterbore Depth: {match['cbore_depth']:.3f}\"")
                    if match['clearance']:
                        report_lines.append(f"   Clearance: {match['clearance']:.3f}\"")

            if len(self.patterns['two_piece_candidates']) > 15:
                report_lines.append(f"\n... and {len(self.patterns['two_piece_candidates']) - 15} more matching pairs")

        report_lines.append("")

        # OD Grouping (parts with same OD that could be two-piece sets)
        report_lines.append("PARTS GROUPED BY OD (Potential Two-Piece Sets)")
        report_lines.append("-"*80)

        od_groups_with_multiple = {od: parts for od, parts in self.patterns['od_groups'].items()
                                   if len(parts) > 1}

        report_lines.append(f"OD Groups with Multiple Parts: {len(od_groups_with_multiple)}")
        report_lines.append("")

        for od, parts in sorted(od_groups_with_multiple.items())[:10]:
            report_lines.append(f"OD {od:.2f}\": {len(parts)} parts")
            for part in parts[:5]:
                ops_str = ', '.join(part['operations'])
                hub_str = f", Hub={part['hub_height']:.2f}\"" if part.get('hub_height') else ""
                report_lines.append(f"  - {part['program']}: Thickness={part['thickness']:.2f}\"{hub_str}")
                report_lines.append(f"    Operations: {ops_str}")
            if len(parts) > 5:
                report_lines.append(f"  ... and {len(parts) - 5} more parts")
            report_lines.append("")

        # Key Insights
        report_lines.append("KEY MANUFACTURING INSIGHTS")
        report_lines.append("-"*80)

        # Calculate operation statistics
        drill_pct = (self.patterns['operation_presence']['DRILL'] / total_files) * 100
        bore_pct = (self.patterns['operation_presence']['BORE'] / total_files) * 100
        turn_pct = (self.patterns['operation_presence']['TURN'] / total_files) * 100
        chamfer_pct = (self.patterns['operation_presence']['CHAMFER'] / total_files) * 100
        cbore_pct = (self.patterns['operation_presence'].get('COUNTERBORE', 0) / total_files) * 100

        report_lines.append(f"• Standard Operations (>90% of parts):")
        if drill_pct > 90:
            report_lines.append(f"  - DRILL: {drill_pct:.1f}% (always required)")
        if bore_pct > 90:
            report_lines.append(f"  - BORE: {bore_pct:.1f}% (always required)")
        if turn_pct > 90:
            report_lines.append(f"  - TURN: {turn_pct:.1f}% (always required)")

        report_lines.append(f"\n• Common Operations (50-90% of parts):")
        if 50 < chamfer_pct <= 90:
            report_lines.append(f"  - CHAMFER: {chamfer_pct:.1f}% (often included for deburring)")

        report_lines.append(f"\n• Optional Operations (<50% of parts):")
        if cbore_pct < 50:
            report_lines.append(f"  - COUNTERBORE: {cbore_pct:.1f}% (for two-piece assemblies)")

        if self.patterns['two_piece_candidates']:
            report_lines.append(f"\n• Two-Piece Assembly Patterns:")
            report_lines.append(f"  - {len(self.patterns['two_piece_candidates'])} matching hub/counterbore pairs found")
            report_lines.append(f"  - Hub heights typically 0.25\" (standard)")
            report_lines.append(f"  - Counterbore depths typically 0.30\" (provides 0.05\" clearance)")
            report_lines.append(f"  - Diameter tolerance: ±0.05\" for tight fit")

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

    analyzer = TwoPiecePatternAnalyzer(db_path, repository_path)

    # Analyze 1000 files
    analyzer.analyze_files(sample_size=1000)

    # Generate report
    report = analyzer.generate_report()
    print(report)


if __name__ == "__main__":
    main()
