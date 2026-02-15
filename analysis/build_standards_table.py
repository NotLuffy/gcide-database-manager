"""
Build Standards Table from Feed/Speed Analysis
Creates recommended feed/speed standards organized by operation type,
round size, and thickness.

Conservative Approach:
- When values are close, use the more conservative (lower) value
- Focus on most common patterns from production data
"""

import json
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StandardRecommendation:
    """Recommended feed/speed for specific conditions"""
    operation_type: str
    round_size_min: Optional[float]
    round_size_max: Optional[float]
    thickness_min: Optional[float]
    thickness_max: Optional[float]

    # Recommendations
    feed_rate: float
    spindle_speed: int

    # Supporting data
    sample_count: int
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'


class StandardsTableBuilder:
    """Build standards table from collected feed/speed data"""

    def __init__(self, analysis_file: str):
        """
        Initialize builder.

        Args:
            analysis_file: Path to feed_speed_analysis.json
        """
        print("Loading feed/speed analysis data...")
        with open(analysis_file, 'r') as f:
            self.data = json.load(f)

        self.records = self.data['records']
        self.statistics = self.data['statistics']

        print(f"Loaded {len(self.records)} records")
        print(f"Total records: {self.statistics['total_records']}")

    def build_standards_by_operation(self) -> Dict[str, Dict]:
        """
        Build standards table organized by operation type.

        Returns:
            Dictionary with operation-specific standards
        """
        standards = {}

        for operation, op_stats in self.statistics['by_operation'].items():
            # Get feed rate recommendation
            feed_mode = op_stats['feed_rate']['mode']
            feed_median = op_stats['feed_rate']['median']
            feed_common = op_stats['feed_rate']['common_values']

            # Use mode if it has high confidence, otherwise use median
            # Conservative approach: if mode and median are close, use lower value
            if feed_mode and feed_median:
                if abs(feed_mode - feed_median) < 0.002:
                    # Very close - use lower (more conservative)
                    feed_recommendation = min(feed_mode, feed_median)
                else:
                    # Use mode (most common)
                    feed_recommendation = feed_mode
            else:
                feed_recommendation = feed_mode or feed_median

            # Get spindle speed recommendation
            speed_mode = op_stats['spindle_speed']['mode']
            speed_median = op_stats['spindle_speed']['median']

            # Conservative approach for spindle speed: lower is safer
            if speed_mode and speed_median:
                if abs(speed_mode - speed_median) < 100:
                    speed_recommendation = min(speed_mode, speed_median)
                else:
                    speed_recommendation = speed_mode
            else:
                speed_recommendation = speed_mode or speed_median

            standards[operation] = {
                'feed_rate': {
                    'recommended': feed_recommendation,
                    'mode': feed_mode,
                    'median': feed_median,
                    'min': op_stats['feed_rate']['min'],
                    'max': op_stats['feed_rate']['max'],
                    'common_values': feed_common[:3]  # Top 3
                },
                'spindle_speed': {
                    'recommended': int(speed_recommendation) if speed_recommendation else None,
                    'mode': speed_mode,
                    'median': speed_median,
                    'min': op_stats['spindle_speed']['min'],
                    'max': op_stats['spindle_speed']['max'],
                    'common_values': op_stats['spindle_speed']['common_values'][:3]
                },
                'sample_count': op_stats['feed_rate']['count']
            }

        return standards

    def build_standards_by_round_size(self) -> Dict[str, Dict]:
        """
        Build standards table organized by round size.

        Returns:
            Dictionary with round-size-specific standards
        """
        # Group round sizes into ranges
        round_size_ranges = [
            (5.5, 6.5, "5.75-6.5\" (L1)"),
            (7.0, 8.5, "7.0-8.5\" (L2/L3)"),
            (9.0, 11.0, "9.5-10.5\" (L2)"),
            (12.0, 14.0, "13.0\" (L2)")
        ]

        standards = {}

        for min_size, max_size, label in round_size_ranges:
            # Filter records for this range
            range_records = [
                r for r in self.records
                if r['round_size'] is not None
                and min_size <= r['round_size'] <= max_size
            ]

            if not range_records:
                continue

            # Group by operation type
            by_operation = defaultdict(lambda: {'feeds': [], 'speeds': []})
            for r in range_records:
                if r['feed_rate']:
                    by_operation[r['operation_type']]['feeds'].append(r['feed_rate'])
                if r['spindle_speed']:
                    by_operation[r['operation_type']]['speeds'].append(r['spindle_speed'])

            # Calculate recommendations
            operation_standards = {}
            for op_type, data in by_operation.items():
                if data['feeds'] and data['speeds']:
                    feed_mode = self._mode(data['feeds'])
                    feed_median = self._median(data['feeds'])
                    speed_mode = self._mode(data['speeds'])
                    speed_median = self._median(data['speeds'])

                    # Conservative approach
                    feed_rec = min(feed_mode, feed_median) if feed_mode and feed_median else (feed_mode or feed_median)
                    speed_rec = min(speed_mode, speed_median) if speed_mode and speed_median else (speed_mode or speed_median)

                    operation_standards[op_type] = {
                        'feed': feed_rec,
                        'speed': int(speed_rec) if speed_rec else None,
                        'samples': len(data['feeds'])
                    }

            standards[label] = operation_standards

        return standards

    def build_standards_by_thickness(self) -> Dict[str, Dict]:
        """
        Build standards table organized by thickness range.

        Returns:
            Dictionary with thickness-specific standards
        """
        # Thickness ranges (matching existing P-code table ranges)
        thickness_ranges = [
            (0.3, 0.5, "0.394-0.5\""),
            (0.5, 1.0, "0.5-1.0\""),
            (1.0, 1.5, "1.0-1.5\""),
            (1.5, 2.0, "1.5-2.0\""),
            (2.0, 2.5, "2.0-2.5\""),
            (2.5, 3.0, "2.5-3.0\""),
            (3.0, 3.75, "3.0-3.75\""),
            (3.75, 4.5, "3.75-4.0\"")
        ]

        standards = {}

        for min_thick, max_thick, label in thickness_ranges:
            # Filter records for this range
            range_records = [
                r for r in self.records
                if r['thickness'] is not None
                and min_thick <= r['thickness'] <= max_thick
            ]

            if not range_records:
                continue

            # Group by operation type
            by_operation = defaultdict(lambda: {'feeds': [], 'speeds': []})
            for r in range_records:
                if r['feed_rate']:
                    by_operation[r['operation_type']]['feeds'].append(r['feed_rate'])
                if r['spindle_speed']:
                    by_operation[r['operation_type']]['speeds'].append(r['spindle_speed'])

            # Calculate recommendations
            operation_standards = {}
            for op_type, data in by_operation.items():
                if data['feeds'] and data['speeds']:
                    feed_mode = self._mode(data['feeds'])
                    feed_median = self._median(data['feeds'])
                    speed_mode = self._mode(data['speeds'])
                    speed_median = self._median(data['speeds'])

                    # Conservative approach
                    feed_rec = min(feed_mode, feed_median) if feed_mode and feed_median else (feed_mode or feed_median)
                    speed_rec = min(speed_mode, speed_median) if speed_mode and speed_median else (speed_mode or speed_median)

                    operation_standards[op_type] = {
                        'feed': feed_rec,
                        'speed': int(speed_rec) if speed_rec else None,
                        'samples': len(data['feeds'])
                    }

            standards[label] = operation_standards

        return standards

    def _median(self, values: List) -> Optional[float]:
        """Calculate median"""
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
        """Calculate mode (most common value)"""
        if not values:
            return None
        from collections import Counter
        counts = Counter(values)
        return counts.most_common(1)[0][0]

    def export_standards_table(self, output_file: str):
        """Export standards table to JSON"""
        standards = {
            'by_operation': self.build_standards_by_operation(),
            'by_round_size': self.build_standards_by_round_size(),
            'by_thickness': self.build_standards_by_thickness(),
            'metadata': {
                'total_samples': len(self.records),
                'conservative_approach': 'When values are close, lower (safer) value is recommended',
                'confidence_levels': {
                    'HIGH': '1000+ samples',
                    'MEDIUM': '100-999 samples',
                    'LOW': '<100 samples'
                }
            }
        }

        with open(output_file, 'w') as f:
            json.dump(standards, f, indent=2)

        print(f"[OK] Standards table exported to: {output_file}")

        return standards

    def print_standards_summary(self, standards: Dict):
        """Print human-readable standards summary"""
        print("\n" + "="*70)
        print("  RECOMMENDED FEED & SPEED STANDARDS")
        print("  (Based on 365,130 samples from production programs)")
        print("="*70)

        print("\n--- BY OPERATION TYPE ---")
        print("-" * 70)
        for operation, data in standards['by_operation'].items():
            print(f"\n{operation}:")
            print(f"  Feed Rate:      {data['feed_rate']['recommended']:.3f} IPR")
            print(f"    (Mode: {data['feed_rate']['mode']:.3f}, Median: {data['feed_rate']['median']:.3f})")
            print(f"    Range: {data['feed_rate']['min']:.3f} - {data['feed_rate']['max']:.3f}")
            print(f"  Spindle Speed:  {data['spindle_speed']['recommended']} RPM")
            print(f"    (Mode: {data['spindle_speed']['mode']}, Median: {data['spindle_speed']['median']:.0f})")
            print(f"  Sample Count:   {data['sample_count']:,}")

        print("\n--- BY ROUND SIZE ---")
        print("-" * 70)
        for size_range, operations in standards['by_round_size'].items():
            print(f"\n{size_range}:")
            for op_type, data in operations.items():
                print(f"  {op_type:12} Feed={data['feed']:.3f}  Speed={data['speed']} RPM  ({data['samples']:,} samples)")

        print("\n--- BY THICKNESS RANGE ---")
        print("-" * 70)
        for thick_range, operations in standards['by_thickness'].items():
            print(f"\n{thick_range}:")
            for op_type, data in operations.items():
                print(f"  {op_type:12} Feed={data['feed']:.3f}  Speed={data['speed']} RPM  ({data['samples']:,} samples)")

        print("\n" + "="*70)
        print("Note: Conservative approach used - when values are close,")
        print("      the lower (safer) value is recommended.")
        print("="*70 + "\n")


def main():
    """Main entry point"""
    analysis_file = r"l:\My Drive\Home\File organizer\feed_speed_analysis.json"
    output_file = r"l:\My Drive\Home\File organizer\feed_speed_standards.json"

    # Build standards table
    builder = StandardsTableBuilder(analysis_file)
    standards = builder.export_standards_table(output_file)

    # Print summary
    builder.print_standards_summary(standards)


if __name__ == "__main__":
    main()
