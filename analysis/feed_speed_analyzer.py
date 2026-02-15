"""
Feed & Speed Analyzer
Scans all G-code files in repository to collect feed rates and spindle speeds.
Builds statistical table of common values correlated with part dimensions.

Analyzes:
- Feed rates (F values)
- Spindle speeds (S values)
- Tool numbers (T values)
- Depth of cut (Z movements)

Correlates with:
- Round size (outer diameter)
- Thickness
- Hub thickness
- Material type
"""

import os
import re
import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class FeedSpeedRecord:
    """Single feed/speed observation"""
    program_number: str
    line_number: int
    tool_number: Optional[str]
    feed_rate: Optional[float]      # F value (inches/min)
    spindle_speed: Optional[int]    # S value (RPM)
    z_depth: Optional[float]        # Z position when F/S used
    operation_type: str             # 'FACE', 'BORE', 'TURN', 'THREAD', 'UNKNOWN'

    # Part dimensions (for correlation)
    round_size: Optional[float]
    thickness: Optional[float]
    hub_height: Optional[float]
    material: Optional[str]


class FeedSpeedAnalyzer:
    """Analyzes feed rates and spindle speeds across all G-code files"""

    def __init__(self, repository_path: str, db_path: str):
        """
        Initialize analyzer.

        Args:
            repository_path: Path to repository folder with G-code files
            db_path: Path to database (to get part dimensions)
        """
        self.repository_path = Path(repository_path)
        self.db_path = db_path
        self.records = []

        # Statistics tracking
        self.feed_rates = defaultdict(list)     # {operation: [feed_rates]}
        self.spindle_speeds = defaultdict(list) # {operation: [speeds]}
        self.by_round_size = defaultdict(list)  # {round_size: [records]}
        self.by_thickness_range = defaultdict(list)   # {thickness_range: [records]}

    def scan_all_files(self, limit: Optional[int] = None) -> int:
        """
        Scan all G-code files in repository.

        Args:
            limit: Optional limit on number of files to scan (for testing)

        Returns:
            Number of files scanned
        """
        # Get all G-code files (any extension)
        all_files = []
        for ext in ['*.nc', '*.NC', '*.txt', '*']:
            all_files.extend(self.repository_path.glob(ext))

        # Filter to only files that look like G-code (start with 'o' or 'O')
        gcode_files = [f for f in all_files if f.stem.lower().startswith('o')]

        # Apply limit if specified
        if limit:
            gcode_files = gcode_files[:limit]

        print(f"Found {len(gcode_files)} G-code files to analyze...")

        # Load part dimensions from database
        dimensions_map = self._load_dimensions_from_db()

        # Scan each file
        files_scanned = 0
        for i, file_path in enumerate(gcode_files, 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(gcode_files)} files...")

            try:
                program_number = file_path.stem.upper()
                dimensions = dimensions_map.get(program_number, {})

                self._scan_file(file_path, program_number, dimensions)
                files_scanned += 1

            except Exception as e:
                print(f"  Error scanning {file_path.name}: {e}")
                continue

        print(f"[OK] Scanned {files_scanned} files")
        print(f"[OK] Collected {len(self.records)} feed/speed records")

        return files_scanned

    def _load_dimensions_from_db(self) -> Dict:
        """
        Load part dimensions from database for correlation.

        Returns:
            Dictionary mapping program_number to dimensions
        """
        dimensions_map = {}

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT program_number, outer_diameter, thickness, hub_height, material
                FROM programs
            """)

            for row in cursor.fetchall():
                prog_num, od, thick, hub_h, material = row
                dimensions_map[prog_num] = {
                    'round_size': od,
                    'thickness': thick,
                    'hub_height': hub_h,
                    'material': material
                }

            conn.close()
            print(f"Loaded dimensions for {len(dimensions_map)} programs from database")

        except Exception as e:
            print(f"Warning: Could not load dimensions from database: {e}")

        return dimensions_map

    def _scan_file(self, file_path: Path, program_number: str, dimensions: Dict):
        """
        Scan single G-code file for feed/speed data.

        Args:
            file_path: Path to G-code file
            program_number: Program number (e.g., 'O70500')
            dimensions: Dictionary with part dimensions
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except:
            return

        # Track current context
        current_tool = None
        current_spindle_speed = None
        last_z = None

        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            if not line.strip() or line.strip().startswith('(') or line.strip().startswith('%'):
                continue

            # Remove inline comments
            code_part = line.split('(')[0] if '(' in line else line
            code_part = code_part.upper()

            # Extract tool number (T)
            tool_match = re.search(r'T(\d+)', code_part)
            if tool_match:
                current_tool = f"T{tool_match.group(1)}"

            # Extract spindle speed (S)
            spindle_match = re.search(r'S(\d+)', code_part)
            if spindle_match:
                current_spindle_speed = int(spindle_match.group(1))

            # Extract Z position
            z_match = re.search(r'Z(-?\d+\.?\d*)', code_part)
            if z_match:
                last_z = float(z_match.group(1))

            # Extract feed rate (F)
            feed_match = re.search(r'F(\d+\.?\d*)', code_part)
            if feed_match:
                feed_rate = float(feed_match.group(1))

                # Determine operation type from tool comment or code
                operation_type = self._determine_operation_type(line, current_tool)

                # Create record
                record = FeedSpeedRecord(
                    program_number=program_number,
                    line_number=line_num,
                    tool_number=current_tool,
                    feed_rate=feed_rate,
                    spindle_speed=current_spindle_speed,
                    z_depth=last_z,
                    operation_type=operation_type,
                    round_size=dimensions.get('round_size'),
                    thickness=dimensions.get('thickness'),
                    hub_height=dimensions.get('hub_height'),
                    material=dimensions.get('material')
                )

                self.records.append(record)

                # Track in statistics
                self.feed_rates[operation_type].append(feed_rate)
                if current_spindle_speed:
                    self.spindle_speeds[operation_type].append(current_spindle_speed)

                if dimensions.get('round_size'):
                    self.by_round_size[dimensions['round_size']].append(record)

                if dimensions.get('thickness'):
                    # Group by thickness range (0.5" increments)
                    thickness_range = self._get_thickness_range(dimensions['thickness'])
                    self.by_thickness_range[thickness_range].append(record)

    def _determine_operation_type(self, line: str, tool_number: Optional[str]) -> str:
        """
        Determine operation type from line content or tool number.

        Args:
            line: G-code line (with comments)
            tool_number: Current tool number

        Returns:
            Operation type: 'FACE', 'BORE', 'TURN', 'THREAD', 'UNKNOWN'
        """
        line_upper = line.upper()

        # Check comments for operation type
        if 'FACE' in line_upper:
            return 'FACE'
        elif 'BORE' in line_upper or 'BORING' in line_upper:
            return 'BORE'
        elif 'TURN' in line_upper:
            return 'TURN'
        elif 'THREAD' in line_upper or 'TAP' in line_upper:
            return 'THREAD'
        elif 'DRILL' in line_upper:
            return 'DRILL'

        # Infer from tool number (common patterns)
        if tool_number:
            tool_num = int(tool_number[1:])  # Remove 'T' prefix

            if tool_num in [101, 102, 103]:  # Common face/bore tools
                return 'FACE/BORE'
            elif tool_num in [121, 122]:  # Common boring tools
                return 'BORE'
            elif tool_num >= 200:  # Threading tools typically 200+
                return 'THREAD'

        return 'UNKNOWN'

    def _get_thickness_range(self, thickness: float) -> str:
        """
        Get thickness range bucket for grouping.

        Args:
            thickness: Thickness in inches

        Returns:
            Range string like "0.5-1.0", "1.0-1.5", etc.
        """
        # Round to nearest 0.5"
        lower = int(thickness * 2) / 2
        upper = lower + 0.5
        return f"{lower:.1f}-{upper:.1f}"

    def generate_statistics(self) -> Dict:
        """
        Generate statistical summary of feed/speed data.

        Returns:
            Dictionary with statistical summaries
        """
        stats = {
            'total_records': len(self.records),
            'by_operation': {},
            'by_round_size': {},
            'by_thickness_range': {}
        }

        # Statistics by operation type
        for operation, feed_rates in self.feed_rates.items():
            spindle_speeds = self.spindle_speeds.get(operation, [])

            stats['by_operation'][operation] = {
                'feed_rate': {
                    'count': len(feed_rates),
                    'min': min(feed_rates) if feed_rates else None,
                    'max': max(feed_rates) if feed_rates else None,
                    'median': self._median(feed_rates),
                    'mode': self._mode(feed_rates),
                    'common_values': self._get_common_values(feed_rates, top_n=5)
                },
                'spindle_speed': {
                    'count': len(spindle_speeds),
                    'min': min(spindle_speeds) if spindle_speeds else None,
                    'max': max(spindle_speeds) if spindle_speeds else None,
                    'median': self._median(spindle_speeds),
                    'mode': self._mode(spindle_speeds),
                    'common_values': self._get_common_values(spindle_speeds, top_n=5)
                }
            }

        # Statistics by round size
        for round_size, records in self.by_round_size.items():
            feed_rates = [r.feed_rate for r in records if r.feed_rate]
            spindle_speeds = [r.spindle_speed for r in records if r.spindle_speed]

            stats['by_round_size'][f"{round_size:.2f}\""] = {
                'count': len(records),
                'feed_rate_mode': self._mode(feed_rates),
                'spindle_speed_mode': self._mode(spindle_speeds)
            }

        # Statistics by thickness range
        for thickness_range, records in self.by_thickness_range.items():
            feed_rates = [r.feed_rate for r in records if r.feed_rate]
            spindle_speeds = [r.spindle_speed for r in records if r.spindle_speed]

            stats['by_thickness_range'][thickness_range] = {
                'count': len(records),
                'feed_rate_mode': self._mode(feed_rates),
                'spindle_speed_mode': self._mode(spindle_speeds)
            }

        return stats

    def _median(self, values: List) -> Optional[float]:
        """Calculate median of values"""
        if not values:
            return None
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vals[mid-1] + sorted_vals[mid]) / 2
        else:
            return sorted_vals[mid]

    def _mode(self, values: List) -> Optional[float]:
        """Calculate mode (most common value) of values"""
        if not values:
            return None
        from collections import Counter
        counts = Counter(values)
        return counts.most_common(1)[0][0]

    def _get_common_values(self, values: List, top_n: int = 5) -> List[Tuple]:
        """
        Get most common values with their frequencies.

        Returns:
            List of (value, count) tuples
        """
        if not values:
            return []
        from collections import Counter
        return Counter(values).most_common(top_n)

    def export_to_json(self, output_path: str):
        """Export collected data to JSON file"""
        data = {
            'records': [asdict(r) for r in self.records],
            'statistics': self.generate_statistics()
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[OK] Exported data to: {output_path}")

    def print_summary(self):
        """Print human-readable summary of findings"""
        stats = self.generate_statistics()

        print("\n" + "="*60)
        print("  FEED & SPEED ANALYSIS SUMMARY")
        print("="*60)
        print(f"\nTotal Records: {stats['total_records']}")

        print("\n--- BY OPERATION TYPE ---")
        for operation, data in stats['by_operation'].items():
            print(f"\n{operation}:")
            print(f"  Feed Rate:")
            print(f"    Most Common: {data['feed_rate']['mode']}")
            print(f"    Median: {data['feed_rate']['median']}")
            print(f"    Range: {data['feed_rate']['min']} - {data['feed_rate']['max']}")
            print(f"    Top 5 Values: {data['feed_rate']['common_values']}")

            if data['spindle_speed']['count'] > 0:
                print(f"  Spindle Speed:")
                print(f"    Most Common: {data['spindle_speed']['mode']} RPM")
                print(f"    Median: {data['spindle_speed']['median']} RPM")
                print(f"    Top 5 Values: {data['spindle_speed']['common_values']}")

        print("\n--- BY ROUND SIZE ---")
        for round_size, data in sorted(stats['by_round_size'].items()):
            print(f"{round_size}: Feed={data['feed_rate_mode']}, Speed={data['spindle_speed_mode']} RPM ({data['count']} samples)")

        print("\n--- BY THICKNESS RANGE ---")
        for thickness_range, data in sorted(stats['by_thickness_range'].items()):
            print(f"{thickness_range}\": Feed={data['feed_rate_mode']}, Speed={data['spindle_speed_mode']} RPM ({data['count']} samples)")


def main():
    """Main entry point for feed/speed analysis"""
    import sys

    # Paths
    repository_path = r"l:\My Drive\Home\File organizer\repository"
    db_path = r"l:\My Drive\Home\File organizer\gcode_database.db"
    output_path = r"l:\My Drive\Home\File organizer\feed_speed_analysis.json"

    # Create analyzer
    analyzer = FeedSpeedAnalyzer(repository_path, db_path)

    # Scan files (use limit for testing, remove for full scan)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    analyzer.scan_all_files(limit=limit)

    # Print summary
    analyzer.print_summary()

    # Export to JSON
    analyzer.export_to_json(output_path)


if __name__ == "__main__":
    main()
