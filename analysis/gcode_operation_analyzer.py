"""
G-Code Operation Pattern Analyzer

Analyzes HOW G-code removes material, not just WHAT operations are present.
Distinguishes between:
- Incremental roughing vs final dimension passes
- Centerbore (full depth) vs Counterbore (shallow pocket)
- Hub profiles from stepped turning operations
- Steel ring assemblies (aluminum ring + steel hub press-fit)

Author: G-Code Database Manager
Date: 2026-02-08
"""

import sqlite3
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BoreFeature:
    """Represents a bore feature extracted from G-code"""
    diameter: float
    depth: float
    is_counterbore: bool  # True if shallow pocket, False if through-bore
    has_chamfer: bool
    side: int  # 1 or 2
    line_number: int
    z_start: float = 0.0

    @property
    def feature_type(self) -> str:
        if self.is_counterbore:
            return "COUNTERBORE"
        else:
            return "CENTERBORE"


@dataclass
class HubFeature:
    """Represents a hub profile from stepped turning"""
    outer_diameter: float  # Large OD
    hub_diameter: float    # Smaller stepped diameter (OB = outer bore)
    hub_height: float      # Depth of the step
    side: int
    line_number: int


@dataclass
class OperationPass:
    """Represents a single material removal pass"""
    operation_type: str  # BORE, TURN, DRILL
    x_value: float
    z_start: float
    z_end: float
    feed_rate: float
    is_roughing: bool  # True if part of incremental sequence
    is_finish: bool    # True if final dimension pass
    line_number: int


class GCodeOperationAnalyzer:
    """Analyzes G-code operations to understand material removal patterns"""

    def __init__(self, db_path: str, repository_path: str):
        self.db_path = db_path
        self.repository_path = repository_path

        self.results = {
            'total_files': 0,
            'files_with_centerbore': 0,
            'files_with_counterbore': 0,
            'files_with_hub': 0,
            'steel_ring_assemblies': 0,
            'stepped_parts': 0,
            'roughing_patterns': defaultdict(int),
            'centerbore_features': [],
            'counterbore_features': [],
            'hub_features': [],
            'dimension_corrections': []  # Cases where parser got wrong dimension
        }

    def analyze_bore_operation(self, lines: List[str], start_idx: int,
                               part_thickness: float) -> Tuple[List[BoreFeature], List[OperationPass]]:
        """
        Analyze bore operation to distinguish roughing, finish, centerbore, and counterbore.

        Key patterns:
        1. Incremental X values (X2.3, X2.6, X2.9...) = roughing passes
        2. X value with chamfer (Z-0.15) = final dimension
        3. Depth ≈ thickness = centerbore (through-hole)
        4. Depth < 50% thickness = counterbore (shallow pocket)
        """
        bore_features = []
        operation_passes = []

        x_values_seen = []
        current_side = 1  # Default to side 1

        # Detect which side we're on
        for i in range(max(0, start_idx - 20), start_idx):
            if 'FLIP PART' in lines[i].upper() or 'OP2' in lines[i].upper():
                current_side = 2
                break

        # Scan forward through bore operation
        i = start_idx
        while i < len(lines) and i < start_idx + 100:  # Look ahead max 100 lines
            line = lines[i].strip()
            line_upper = line.upper()

            # Stop if we hit next tool change or end
            if line_upper.startswith('T') and any(c.isdigit() for c in line_upper):
                if i > start_idx + 5:  # Not the current tool
                    break

            # Extract X value (diameter as radius)
            x_match = re.search(r'X\s*(\d+\.?\d*)', line_upper)
            z_match = re.search(r'Z\s*(-?\d+\.?\d*)', line_upper)
            f_match = re.search(r'F\s*(\d+\.?\d*)', line_upper)

            if x_match:
                x_val = float(x_match.group(1))
                z_val = float(z_match.group(1)) if z_match else 0.0
                feed = float(f_match.group(1)) if f_match else 0.0

                x_values_seen.append((x_val, z_val, i, line))

                # Detect final dimension with chamfer
                # Pattern: X value followed by Z-0.1 to Z-0.15 (chamfer angle)
                if -0.2 < z_val < -0.05 and '(X IS CB)' in line.upper():
                    # This is the final centerbore/counterbore diameter
                    diameter = x_val

                    # Look for depth on next line
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip().upper()
                        depth_match = re.search(r'Z\s*(-?\d+\.?\d*)', next_line)
                        if depth_match:
                            depth = abs(float(depth_match.group(1)))

                            # Determine if counterbore or centerbore
                            is_counterbore = depth < (part_thickness * 0.5)

                            bore_feature = BoreFeature(
                                diameter=diameter,
                                depth=depth,
                                is_counterbore=is_counterbore,
                                has_chamfer=True,
                                side=current_side,
                                line_number=i + 1,
                                z_start=z_val
                            )
                            bore_features.append(bore_feature)

            i += 1

        # Detect roughing patterns
        if len(x_values_seen) >= 3:
            # Check if X values increment consistently (roughing)
            x_only = [x[0] for x in x_values_seen[:-1]]  # Exclude last (finish pass)

            if len(x_only) >= 3:
                # Calculate increments
                increments = [x_only[i+1] - x_only[i] for i in range(len(x_only)-1)]
                avg_increment = sum(increments) / len(increments) if increments else 0

                # If consistent increments (0.2 to 0.4), it's roughing
                if 0.15 < avg_increment < 0.5:
                    self.results['roughing_patterns']['Incremental X roughing'] += 1

                    # Mark all but last as roughing passes
                    for idx, (x, z, line_no, line_text) in enumerate(x_values_seen[:-1]):
                        op = OperationPass(
                            operation_type='BORE',
                            x_value=x,
                            z_start=0.0,
                            z_end=z,
                            feed_rate=0.0,
                            is_roughing=True,
                            is_finish=False,
                            line_number=line_no
                        )
                        operation_passes.append(op)

        return bore_features, operation_passes

    def analyze_stepped_turning(self, lines: List[str], start_idx: int) -> Optional[HubFeature]:
        """
        Analyze stepped turning to detect hub profiles.

        Pattern: Repeated Z-depth passes with same X travel
        Example:
          G01 Z-0.2 F0.013
          X6.7
          G00 X10.17
          G01 Z-0.4 F0.013  <- Incrementing Z depth
          X6.7              <- Same X endpoint (hub diameter)
        """
        z_depths = []
        x_endpoint = None
        x_startpoint = None
        current_side = 2  # Hubs typically on side 2

        # Scan for repeated pattern
        i = start_idx
        while i < len(lines) and i < start_idx + 50:
            line = lines[i].strip().upper()

            # Look for Z depth followed by X value
            z_match = re.search(r'G01\s+Z\s*(-\d+\.?\d*)', line)
            if z_match:
                z_depth = abs(float(z_match.group(1)))

                # Look for X value on next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip().upper()
                    x_match = re.search(r'^X\s*(\d+\.?\d*)', next_line)
                    if x_match:
                        x_val = float(x_match.group(1))
                        z_depths.append(z_depth)

                        if x_endpoint is None:
                            x_endpoint = x_val

                        # Check for comment indicating hub diameter
                        if '(X IS OB)' in next_line:
                            x_endpoint = x_val  # This is the hub diameter

            # Look for starting X value (OD)
            if 'G00 X' in line and x_startpoint is None:
                x_match = re.search(r'X\s*(\d+\.?\d*)', line)
                if x_match:
                    x_startpoint = float(x_match.group(1))

            i += 1

        # If we found repeated Z-depth passes (3+), it's a stepped/hub feature
        if len(z_depths) >= 3 and x_endpoint and x_startpoint:
            # Check if Z depths increment (stepped turning pattern)
            is_incremental = all(z_depths[i] < z_depths[i+1] for i in range(len(z_depths)-1))

            if is_incremental:
                hub_height = max(z_depths)

                hub_feature = HubFeature(
                    outer_diameter=x_startpoint,
                    hub_diameter=x_endpoint,
                    hub_height=hub_height,
                    side=current_side,
                    line_number=start_idx
                )

                return hub_feature

        return None

    def analyze_file(self, program_number: str, file_path: str,
                    thickness: float, hub_height: Optional[float]):
        """Analyze single G-code file for operation patterns"""

        self.results['total_files'] += 1

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            # Check for steel ring assembly pattern
            first_line = lines[0].upper() if lines else ""
            is_steel_ring = 'MM ID' in first_line or 'MM CB' in first_line or 'RING' in first_line
            if is_steel_ring:
                self.results['steel_ring_assemblies'] += 1

            # Analyze bore operations
            all_bore_features = []
            all_operation_passes = []

            for i, line in enumerate(lines):
                line_upper = line.upper().strip()

                # Detect bore operation start
                if 'T121' in line_upper and 'BORE' in line_upper:
                    bore_features, op_passes = self.analyze_bore_operation(lines, i, thickness)
                    all_bore_features.extend(bore_features)
                    all_operation_passes.extend(op_passes)

                # Detect turn operation for hub profiles
                if 'T303' in line_upper and 'TURN' in line_upper:
                    hub_feature = self.analyze_stepped_turning(lines, i)
                    if hub_feature:
                        self.results['hub_features'].append({
                            'program': program_number,
                            'outer_diameter': hub_feature.outer_diameter,
                            'hub_diameter': hub_feature.hub_diameter,
                            'hub_height': hub_feature.hub_height,
                            'side': hub_feature.side
                        })
                        self.results['files_with_hub'] += 1

            # Store centerbore and counterbore features
            for bf in all_bore_features:
                feature_data = {
                    'program': program_number,
                    'diameter': bf.diameter,
                    'depth': bf.depth,
                    'side': bf.side,
                    'has_chamfer': bf.has_chamfer,
                    'is_steel_ring': is_steel_ring
                }

                if bf.is_counterbore:
                    self.results['counterbore_features'].append(feature_data)
                    self.results['files_with_counterbore'] += 1
                else:
                    self.results['centerbore_features'].append(feature_data)
                    self.results['files_with_centerbore'] += 1

            # Detect stepped parts (has both centerbore and counterbore)
            has_centerbore = any(not bf.is_counterbore for bf in all_bore_features)
            has_counterbore = any(bf.is_counterbore for bf in all_bore_features)
            if has_centerbore and has_counterbore:
                self.results['stepped_parts'] += 1

        except Exception as e:
            print(f"Error analyzing {program_number}: {e}")

    def run_analysis(self, sample_size: int = 500):
        """Run analysis on sample of files"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()

        query = """
        SELECT program_number, file_path, thickness, hub_height
        FROM programs
        WHERE file_path IS NOT NULL
          AND thickness IS NOT NULL
        ORDER BY RANDOM()
        LIMIT ?
        """

        cursor.execute(query, (sample_size,))
        files = cursor.fetchall()
        conn.close()

        print(f"Analyzing {len(files)} files for operation patterns...")

        for i, (program_number, file_path, thickness, hub_height) in enumerate(files, 1):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(files)}...")

            self.analyze_file(program_number, file_path, thickness, hub_height)

        print(f"\nAnalysis complete!")

    def generate_report(self) -> str:
        """Generate comprehensive operation analysis report"""
        lines = []

        lines.append("=" * 80)
        lines.append("G-CODE OPERATION PATTERN ANALYSIS")
        lines.append("How Material is Removed - Detailed Process Analysis")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Files Analyzed: {self.results['total_files']}")
        lines.append(f"Files with CENTERBORE (through-hole): {self.results['files_with_centerbore']}")
        lines.append(f"Files with COUNTERBORE (shallow pocket): {self.results['files_with_counterbore']}")
        lines.append(f"Files with HUB profile: {self.results['files_with_hub']}")
        lines.append(f"Stepped parts (centerbore + counterbore): {self.results['stepped_parts']}")
        lines.append(f"Steel ring assemblies: {self.results['steel_ring_assemblies']}")
        lines.append("")

        # Roughing patterns
        lines.append("ROUGHING PATTERNS DETECTED")
        lines.append("-" * 80)
        for pattern, count in sorted(self.results['roughing_patterns'].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {pattern}: {count} files")
        lines.append("")

        # Centerbore analysis
        if self.results['centerbore_features']:
            lines.append("CENTERBORE FEATURES (Through-Holes)")
            lines.append("-" * 80)
            lines.append(f"Total: {len(self.results['centerbore_features'])}")

            diameters = [f['diameter'] for f in self.results['centerbore_features']]
            depths = [f['depth'] for f in self.results['centerbore_features']]

            lines.append(f"Diameter Range: {min(diameters):.3f}\" - {max(diameters):.3f}\"")
            lines.append(f"Depth Range: {min(depths):.3f}\" - {max(depths):.3f}\"")
            lines.append("")

            lines.append("Examples:")
            for i, feature in enumerate(self.results['centerbore_features'][:10], 1):
                ring_marker = " [STEEL RING]" if feature.get('is_steel_ring') else ""
                lines.append(f"  {i}. {feature['program']}: Ø{feature['diameter']:.3f}\" × {feature['depth']:.3f}\" deep (Side {feature['side']}){ring_marker}")
            lines.append("")

        # Counterbore analysis
        if self.results['counterbore_features']:
            lines.append("COUNTERBORE FEATURES (Shallow Pockets)")
            lines.append("-" * 80)
            lines.append(f"Total: {len(self.results['counterbore_features'])}")

            diameters = [f['diameter'] for f in self.results['counterbore_features']]
            depths = [f['depth'] for f in self.results['counterbore_features']]

            lines.append(f"Diameter Range: {min(diameters):.3f}\" - {max(diameters):.3f}\"")
            lines.append(f"Depth Range: {min(depths):.3f}\" - {max(depths):.3f}\"")
            lines.append(f"Average Depth: {sum(depths)/len(depths):.3f}\"")
            lines.append("")

            lines.append("Examples:")
            for i, feature in enumerate(self.results['counterbore_features'][:10], 1):
                lines.append(f"  {i}. {feature['program']}: Ø{feature['diameter']:.3f}\" × {feature['depth']:.3f}\" deep (Side {feature['side']})")
            lines.append("")

        # Hub analysis
        if self.results['hub_features']:
            lines.append("HUB PROFILES (Stepped Turning)")
            lines.append("-" * 80)
            lines.append(f"Total: {len(self.results['hub_features'])}")
            lines.append("")

            lines.append("Examples:")
            for i, hub in enumerate(self.results['hub_features'][:10], 1):
                lines.append(f"  {i}. {hub['program']}: OD {hub['outer_diameter']:.3f}\" -> Hub {hub['hub_diameter']:.3f}\" x {hub['hub_height']:.3f}\" deep")
            lines.append("")

        # Key insights
        lines.append("KEY MANUFACTURING INSIGHTS")
        lines.append("-" * 80)
        lines.append("• Incremental roughing is standard practice (X values increment 0.2-0.4\")")
        lines.append("• Final dimensions marked with chamfer move (Z-0.1 to Z-0.15)")
        lines.append("• Centerbore = full-depth bore (≥50% of thickness)")
        lines.append("• Counterbore = shallow pocket (<50% of thickness)")
        lines.append("• Stepped parts have BOTH centerbore and counterbore")
        lines.append("• Hub profiles created via repeated Z-depth turning passes")
        lines.append("• Steel ring assemblies use counterbore for press-fit hub")
        lines.append("")

        # Recommended parser improvements
        lines.append("RECOMMENDED PARSER IMPROVEMENTS")
        lines.append("-" * 80)
        lines.append("1. Ignore incremental X values (roughing passes) when extracting dimensions")
        lines.append("2. Extract final dimension from line with chamfer comment '(X IS CB)'")
        lines.append("3. Distinguish centerbore vs counterbore based on depth ratio")
        lines.append("4. Detect hub profiles from stepped turning (comment 'X IS OB')")
        lines.append("5. Tag steel ring assemblies from 'MM ID' or 'MM CB' in program title")
        lines.append("6. Track Side 1 vs Side 2 operations separately")
        lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """Main entry point"""
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    repository_path = r"l:\My Drive\Home\File organizer\repository"

    analyzer = GCodeOperationAnalyzer(db_path, repository_path)

    # Analyze 500 random files
    analyzer.run_analysis(sample_size=500)

    # Generate and save report
    report = analyzer.generate_report()

    # Save to file first
    with open("operation_analysis_report.txt", 'w', encoding='utf-8') as f:
        f.write(report)

    print("\nReport saved to: operation_analysis_report.txt")
    print("\nSummary:")
    print(f"  Files analyzed: {analyzer.results['total_files']}")
    print(f"  Centerbores: {analyzer.results['files_with_centerbore']}")
    print(f"  Counterbores: {analyzer.results['files_with_counterbore']}")
    print(f"  Hub profiles: {analyzer.results['files_with_hub']}")
    print(f"  Stepped parts: {analyzer.results['stepped_parts']}")
    print(f"  Steel ring assemblies: {analyzer.results['steel_ring_assemblies']}")


if __name__ == "__main__":
    main()
