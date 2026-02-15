"""
2PC Part Matcher - Finds matching STUD and LUG pairs

2PC (two-piece) wheel spacers consist of two parts that lock together:
- STUD: Has a hub (typically 0.25") that protrudes and fits INTO the LUG
- LUG: Has a shelf/counterbore (typically 0.30-0.32" deep) that RECEIVES the STUD's hub

Matching Criteria:
1. Same round size (e.g., both 7.5IN)
2. STUD's hub OB diameter fits within LUG's shelf CB diameter (0-0.05" clearance, ~0-1.27mm)
3. One part is STUD type, other is LUG type

The hub OB (from STUD) should be slightly smaller than shelf CB (from LUG) so they slot together.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from collections import defaultdict


@dataclass
class TwoPCPart:
    """Represents a 2PC part with its key dimensions for matching"""
    program_number: str
    file_path: str
    title: str
    round_size: Optional[float]  # inches (e.g., 7.5)
    part_type: str  # 'STUD', 'LUG', 'UNKNOWN'

    # Key dimensions for matching (all in mm for consistency)
    hub_ob: Optional[float]  # Hub outer bore diameter (STUD parts) - the protruding part
    shelf_cb: Optional[float]  # Shelf/counterbore diameter (LUG parts) - the receiving pocket
    hub_depth: Optional[float]  # Hub height in inches (STUD)
    shelf_depth: Optional[float]  # Shelf depth in inches (LUG)

    # Additional info
    center_bore: Optional[float]  # mm
    thickness: Optional[float]  # inches

    # Detection info
    detection_notes: List[str] = None

    def __post_init__(self):
        if self.detection_notes is None:
            self.detection_notes = []


class TwoPCMatcher:
    """
    Analyzes 2PC G-code files and finds matching STUD/LUG pairs.
    """

    # Standard round sizes in inches
    ROUND_SIZES = [5.75, 6.00, 6.25, 6.50, 7.00, 7.50, 8.00, 8.50, 9.50, 10.25, 10.50, 13.00]

    def __init__(self, repository_path: str):
        self.repository_path = repository_path
        self.parts: List[TwoPCPart] = []
        self.matches: List[Tuple[TwoPCPart, TwoPCPart, float]] = []  # (stud, lug, clearance)

    def scan_repository(self) -> int:
        """Scan repository for 2PC files and extract dimensions."""
        count = 0
        for filename in os.listdir(self.repository_path):
            if not filename.lower().endswith(('.nc', '.txt')):
                continue

            file_path = os.path.join(self.repository_path, filename)
            part = self._analyze_file(file_path)

            if part and part.part_type != 'UNKNOWN':
                self.parts.append(part)
                count += 1

        print(f"Found {count} 2PC parts ({len([p for p in self.parts if p.part_type == 'STUD'])} STUD, "
              f"{len([p for p in self.parts if p.part_type == 'LUG'])} LUG)")
        return count

    def _analyze_file(self, file_path: str) -> Optional[TwoPCPart]:
        """Analyze a single file to extract 2PC dimensions."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            return None

        # Check if this is a 2PC file
        content_upper = content.upper()
        if '2PC' not in content_upper and 'LUG' not in content_upper and 'STUD' not in content_upper:
            return None

        # Extract program number and title
        program_number = self._extract_program_number(os.path.basename(file_path), lines)
        title = self._extract_title(lines)

        if not title:
            return None

        # Determine part type (STUD or LUG)
        part_type = self._determine_part_type(title, lines)

        # Extract round size
        round_size = self._extract_round_size(title)

        # Extract dimensions from G-code
        dimensions = self._extract_2pc_dimensions(lines, part_type)

        # Extract basic dimensions
        center_bore = self._extract_center_bore(title)
        thickness = self._extract_thickness(title)

        part = TwoPCPart(
            program_number=program_number,
            file_path=file_path,
            title=title,
            round_size=round_size,
            part_type=part_type,
            hub_ob=dimensions.get('hub_ob'),
            shelf_cb=dimensions.get('shelf_cb'),
            hub_depth=dimensions.get('hub_depth'),
            shelf_depth=dimensions.get('shelf_depth'),
            center_bore=center_bore,
            thickness=thickness,
            detection_notes=dimensions.get('notes', [])
        )

        return part

    def _extract_program_number(self, filename: str, lines: List[str]) -> str:
        """Extract program number from filename or O-line."""
        # Try filename first
        match = re.search(r'[oO](\d+)', filename)
        if match:
            return f"O{match.group(1)}"

        # Try O-line in file
        for line in lines[:10]:
            match = re.search(r'^[oO](\d+)', line.strip())
            if match:
                return f"O{match.group(1)}"

        return filename

    def _extract_title(self, lines: List[str]) -> Optional[str]:
        """Extract title from G-code (content in parentheses on O-line)."""
        for line in lines[:10]:
            # Look for O-number line with title in parentheses
            match = re.search(r'^[oO]\d+\s*\(([^)]+)\)', line.strip())
            if match:
                return match.group(1).strip()
        return None

    def _determine_part_type(self, title: str, lines: List[str]) -> str:
        """Determine if this is a STUD or LUG part."""
        title_upper = title.upper()

        # Check title first
        if 'LUG' in title_upper:
            return 'LUG'
        if 'STUD' in title_upper:
            return 'STUD'

        # Check comments in first 20 lines
        for line in lines[:20]:
            line_upper = line.upper()
            if 'LUG PLATE' in line_upper or '(LUG)' in line_upper:
                return 'LUG'
            if 'STUD PLATE' in line_upper or '(STUD)' in line_upper:
                return 'STUD'

        # If has 2PC but no LUG/STUD indicator, try to determine from G-code patterns
        # STUD typically has shallower shelf (~0.31") and creates hub in OP2
        # LUG typically has deeper shelf (~1.0"+) to receive STUD

        return 'UNKNOWN'

    def _extract_round_size(self, title: str) -> Optional[float]:
        """Extract round size from title."""
        title_upper = title.upper()

        # Pattern: "7.5IN" or "7.5 IN" or "7.50IN"
        match = re.search(r'(\d+\.?\d*)\s*IN', title_upper)
        if match:
            size = float(match.group(1))
            # Round to nearest standard size
            for std_size in self.ROUND_SIZES:
                if abs(size - std_size) < 0.1:
                    return std_size
            return size

        # Pattern: "13.0" at start (for 13" parts)
        match = re.search(r'^(\d+\.?\d*)\s', title)
        if match:
            size = float(match.group(1))
            if size > 4:  # Likely a round size
                for std_size in self.ROUND_SIZES:
                    if abs(size - std_size) < 0.1:
                        return std_size

        return None

    def _extract_center_bore(self, title: str) -> Optional[float]:
        """Extract center bore from title (in mm)."""
        # Pattern: "95.1MM" or "95MM" or "DIA 95.1MM"
        match = re.search(r'(\d+\.?\d*)\s*MM', title.upper())
        if match:
            return float(match.group(1))
        return None

    def _extract_thickness(self, title: str) -> Optional[float]:
        """Extract thickness from title (in inches)."""
        # Pattern: ".75" or "1.25" or "0.75"
        # Usually appears after MM value or before 2PC/HC
        match = re.search(r'[\s]\.?(\d*\.?\d+)\s*(?:2PC|HC|LUG|STUD|THK|$)', title.upper())
        if match:
            val = match.group(1)
            if val.startswith('.'):
                return float('0' + val)
            return float(val)
        return None

    def _extract_2pc_dimensions(self, lines: List[str], part_type: str) -> Dict:
        """
        Extract 2PC-specific dimensions from G-code.

        For STUD parts:
        - hub_ob: The hub's outer diameter (from OP2 facing - where facing ends before CB chamfer)
        - hub_depth: The hub height (deepest Z in OP2 facing, typically 0.25")
        - shelf_cb: The shelf/step diameter in OP1 (for the receiving portion)
        - shelf_depth: The shelf depth in OP1 (typically 0.30-0.32")

        For LUG parts:
        - shelf_cb: The shelf/counterbore diameter (from OP1 boring)
        - shelf_depth: The shelf depth (typically 1.0"+ to receive STUD)
        - hub_ob: May also have a hub in OP2 for special parts

        Key insight for hub_ob detection:
        - In OP2, the turn tool faces from OD inward to create the hub
        - The hub OB is where the facing ENDS before transitioning to CB chamfer
        - Pattern: progressive facing at increasing Z depths, ending at hub OB diameter
        - The smallest X value at significant hub depth (not OD) is the hub OB
        """
        result = {
            'hub_ob': None,
            'shelf_cb': None,
            'hub_depth': None,
            'shelf_depth': None,
            'notes': []
        }

        in_op2 = False
        in_bore_op1 = False
        in_turn_op2 = False

        # Track operations
        op1_bore_moves = []  # (x_diameter, z_depth) tuples from OP1 boring
        op2_turn_moves = []  # (x_diameter, z_depth, line_num) tuples from OP2 turning

        current_x = None
        current_tool = None

        for i, line in enumerate(lines):
            line_upper = line.upper().strip()

            # Detect OP2 boundary
            if any(marker in line_upper for marker in ['OP2', 'OP 2', 'FLIP PART', 'FLIP', 'SIDE 2']):
                in_op2 = True
                in_bore_op1 = False

            # Track tool changes
            if 'T121' in line_upper or ('BORE' in line_upper and 'T' in line_upper):
                current_tool = 'T121'
                if not in_op2:
                    in_bore_op1 = True
                    in_turn_op2 = False
                else:
                    in_turn_op2 = False  # T121 in OP2 is chamfer, not turn
            elif 'T303' in line_upper or ('TURN' in line_upper and 'T' in line_upper):
                current_tool = 'T303'
                in_bore_op1 = False
                if in_op2:
                    in_turn_op2 = True
            elif re.match(r'T\d{3}', line_upper):
                current_tool = line_upper[:4]
                in_bore_op1 = False
                in_turn_op2 = False

            # Extract X and Z values from G01 moves (cutting moves)
            if line_upper.startswith('G01') or (not line_upper.startswith('G00') and 'X' in line_upper):
                x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

                if x_match:
                    current_x = float(x_match.group(1))

                # Collect OP1 bore moves (for shelf detection)
                if in_bore_op1 and not in_op2 and current_x and z_match:
                    z_val = float(z_match.group(1))
                    if 0.1 <= z_val <= 2.0:  # Reasonable bore depth range
                        op1_bore_moves.append((current_x, z_val, i))

                # Collect OP2 turn moves (for hub detection)
                # Only collect moves where X is NOT near OD (< 5" typically)
                if in_op2 and in_turn_op2 and current_x:
                    if current_x < 5.0:  # Filter out OD moves
                        if z_match:
                            z_val = float(z_match.group(1))
                        else:
                            z_val = None
                        op2_turn_moves.append((current_x, z_val, i))

            # Also track X-only moves in OP2 (facing moves often have X without Z)
            elif in_op2 and in_turn_op2 and 'X' in line_upper and 'G00' not in line_upper:
                x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                if x_match:
                    x_val = float(x_match.group(1))
                    if x_val < 5.0:  # Filter out OD moves
                        op2_turn_moves.append((x_val, None, i))

        # Analyze OP1 bore moves for shelf
        if op1_bore_moves:
            # Group by Z depth to find shelf pattern
            depth_groups = defaultdict(list)
            for x, z, line_num in op1_bore_moves:
                # Round to 0.01" for grouping
                z_rounded = round(z, 2)
                depth_groups[z_rounded].append(x)

            # Find shelf: look for chamfer pattern (X IS CB comment or diagonal move)
            # The shelf CB is typically marked with "(X IS CB)" or is the largest X at shelf depth
            for line_num, (x, z, ln) in enumerate(op1_bore_moves):
                if ln < len(lines):
                    if '(X IS CB)' in lines[ln].upper() or 'X IS CB' in lines[ln].upper():
                        # Found explicit CB marker
                        result['shelf_cb'] = round(x * 25.4, 2)
                        result['shelf_depth'] = z
                        result['notes'].append(f'OP1 shelf (marked): {x * 25.4:.1f}mm at Z-{z}"')
                        break

            # If no explicit marker, find shelf from depth pattern
            if not result['shelf_cb']:
                sorted_depths = sorted(depth_groups.keys())
                if len(sorted_depths) >= 2:
                    # Look for transition point - shelf is typically 0.28-1.5" deep
                    for depth in sorted_depths:
                        x_vals = depth_groups[depth]
                        if 0.28 <= depth <= 1.5 and len(x_vals) >= 1:
                            max_x = max(x_vals)
                            shelf_cb_mm = max_x * 25.4
                            if 50 <= shelf_cb_mm <= 150:  # Reasonable shelf range (not OD)
                                result['shelf_cb'] = round(shelf_cb_mm, 2)
                                result['shelf_depth'] = depth
                                result['notes'].append(f'OP1 shelf: {shelf_cb_mm:.1f}mm at Z-{depth}"')
                                break

        # Analyze OP2 turn moves for hub OB
        if op2_turn_moves:
            # Filter to reasonable hub diameters (not OD, not CB)
            # Hub OB is typically 70-130mm (2.75" - 5.1")
            hub_candidates = []

            for x, z, line_num in op2_turn_moves:
                x_mm = x * 25.4
                # Hub OB range: larger than typical CB (60mm) but smaller than OD (150mm+)
                if 70 <= x_mm <= 140:
                    hub_candidates.append((x, z, line_num))

            if hub_candidates:
                # The hub OB is the X value where facing ends before going to CB
                # Look for the smallest X in the hub range that appears multiple times
                # or has significant Z depth
                x_values = [x for x, z, ln in hub_candidates]

                # Find most common X values (facing passes)
                from collections import Counter
                x_counts = Counter([round(x, 3) for x in x_values])

                if x_counts:
                    # Get the smallest frequently-used X (this is likely the hub OB)
                    frequent_x = [x for x, count in x_counts.items() if count >= 1]
                    if frequent_x:
                        hub_ob_x = min(frequent_x)
                        hub_ob_mm = hub_ob_x * 25.4

                        # Find the Z depth for this X
                        z_at_hub = [z for x, z, ln in hub_candidates
                                   if abs(x - hub_ob_x) < 0.01 and z is not None]

                        if z_at_hub:
                            result['hub_depth'] = max(z_at_hub)
                        else:
                            # Estimate from other moves
                            all_z = [z for x, z, ln in op2_turn_moves if z is not None and z > 0.1]
                            if all_z:
                                result['hub_depth'] = max(all_z)

                        result['hub_ob'] = round(hub_ob_mm, 2)
                        result['notes'].append(f'OP2 hub: {hub_ob_mm:.1f}mm OB' +
                                              (f' at Z-{result["hub_depth"]}" depth' if result['hub_depth'] else ''))

        return result

    def find_matches(self, clearance_min: float = 0.0, clearance_max: float = 1.5) -> List[Tuple[TwoPCPart, TwoPCPart, float]]:
        """
        Find matching STUD/LUG pairs.

        The matching logic:
        - STUD parts have a shelf_cb (pocket) that receives the LUG's hub
        - LUG parts have a hub_ob (protruding hub) that fits into the STUD's shelf
        - Match when: LUG's hub_ob fits into STUD's shelf_cb with small clearance

        This is counter-intuitive but based on actual G-code analysis:
        - STUD creates a receiving pocket (shelf_cb) at ~0.31" depth
        - LUG creates a protruding hub (hub_ob) at ~0.25" depth
        - The LUG's hub inserts into the STUD's shelf

        Args:
            clearance_min: Minimum clearance in mm (default 0.0)
            clearance_max: Maximum clearance in mm (default 1.5mm = ~0.06")

        Returns:
            List of (stud, lug, clearance_mm) tuples
        """
        self.matches = []

        # Group parts by round size
        by_round_size = defaultdict(lambda: {'STUD': [], 'LUG': []})

        for part in self.parts:
            if part.round_size and part.part_type in ('STUD', 'LUG'):
                by_round_size[part.round_size][part.part_type].append(part)

        # Find matches within each round size group
        for round_size, groups in by_round_size.items():
            studs = groups['STUD']
            lugs = groups['LUG']

            for stud in studs:
                if not stud.shelf_cb:  # STUD needs a shelf to receive LUG's hub
                    continue

                for lug in lugs:
                    if not lug.hub_ob:  # LUG needs a hub to insert into STUD's shelf
                        continue

                    # Check if LUG's hub fits into STUD's shelf
                    # STUD shelf should be slightly larger than LUG hub
                    clearance = stud.shelf_cb - lug.hub_ob

                    if clearance_min <= clearance <= clearance_max:
                        self.matches.append((stud, lug, clearance))

        # Sort by clearance (best fit first)
        self.matches.sort(key=lambda x: x[2])

        return self.matches

    def print_parts(self):
        """Print all detected 2PC parts."""
        print("\n" + "="*80)
        print("2PC PARTS DETECTED")
        print("="*80)

        # Group by round size
        by_round_size = defaultdict(list)
        for part in self.parts:
            by_round_size[part.round_size or 0].append(part)

        for round_size in sorted(by_round_size.keys()):
            parts = by_round_size[round_size]
            print(f"\n--- {round_size}\" Round Size ---" if round_size else "\n--- Unknown Round Size ---")

            for part in sorted(parts, key=lambda p: p.program_number):
                print(f"\n  {part.program_number} ({part.part_type})")
                print(f"    Title: {part.title}")
                if part.hub_ob:
                    print(f"    Hub OB: {part.hub_ob:.1f}mm (depth: {part.hub_depth or '?'}\")")
                if part.shelf_cb:
                    print(f"    Shelf CB: {part.shelf_cb:.1f}mm (depth: {part.shelf_depth or '?'}\")")
                if part.detection_notes:
                    for note in part.detection_notes:
                        print(f"    Note: {note}")

    def print_matches(self):
        """Print all found matches."""
        print("\n" + "="*80)
        print("2PC MATCHING PAIRS")
        print("="*80)

        if not self.matches:
            print("\nNo matches found.")
            return

        # Group by round size
        by_round_size = defaultdict(list)
        for stud, lug, clearance in self.matches:
            by_round_size[stud.round_size or 0].append((stud, lug, clearance))

        for round_size in sorted(by_round_size.keys()):
            matches = by_round_size[round_size]
            print(f"\n--- {round_size}\" Round Size ({len(matches)} matches) ---")

            for stud, lug, clearance in matches:
                print(f"\n  STUD: {stud.program_number}")
                print(f"    Title: {stud.title}")
                print(f"    Hub OB: {stud.hub_ob:.1f}mm")
                print(f"  LUG:  {lug.program_number}")
                print(f"    Title: {lug.title}")
                print(f"    Shelf CB: {lug.shelf_cb:.1f}mm")
                print(f"  CLEARANCE: {clearance:.2f}mm ({clearance/25.4:.4f}\")")

                # Fit assessment
                if clearance < 0.5:
                    fit = "TIGHT FIT"
                elif clearance < 1.0:
                    fit = "GOOD FIT"
                else:
                    fit = "LOOSE FIT"
                print(f"  FIT: {fit}")


def main():
    """Test the 2PC matcher."""
    import sys

    # Default repository path
    repo_path = r"k:\My Drive\Home\File organizer\repository"

    if len(sys.argv) > 1:
        repo_path = sys.argv[1]

    print(f"Scanning repository: {repo_path}")
    print("-" * 80)

    matcher = TwoPCMatcher(repo_path)

    # Scan for 2PC parts
    count = matcher.scan_repository()

    if count == 0:
        print("No 2PC parts found.")
        return

    # Print all detected parts
    matcher.print_parts()

    # Find matches
    print("\n" + "="*80)
    print("FINDING MATCHES...")
    print("="*80)

    matches = matcher.find_matches(clearance_min=0.0, clearance_max=2.0)
    print(f"\nFound {len(matches)} potential matches")

    # Print matches
    matcher.print_matches()

    # Test specific pair
    print("\n" + "="*80)
    print("TESTING KNOWN PAIR: O76023 + O75717")
    print("="*80)

    o76023 = None
    o75717 = None
    for part in matcher.parts:
        if part.program_number == 'O76023':
            o76023 = part
        elif part.program_number == 'O75717':
            o75717 = part

    if o76023 and o75717:
        print(f"\nO76023:")
        print(f"  Type: {o76023.part_type}")
        print(f"  Hub OB: {o76023.hub_ob}mm")
        print(f"  Shelf CB: {o76023.shelf_cb}mm")

        print(f"\nO75717:")
        print(f"  Type: {o75717.part_type}")
        print(f"  Hub OB: {o75717.hub_ob}mm")
        print(f"  Shelf CB: {o75717.shelf_cb}mm")

        # Check if they match
        if o76023.hub_ob and o75717.shelf_cb:
            clearance = o75717.shelf_cb - o76023.hub_ob
            print(f"\nClearance (O75717 shelf - O76023 hub): {clearance:.2f}mm")
    else:
        print(f"\nCould not find both files:")
        print(f"  O76023: {'Found' if o76023 else 'Not found'}")
        print(f"  O75717: {'Found' if o75717 else 'Not found'}")


if __name__ == '__main__':
    main()
