"""
Improved G-Code Parser - Combines logic from:
1. FILE SEARCH combined_part_detection.py (pattern recognition)
2. FILE SEARCH comprehensive_gcode_validator.py (validation logic)
3. Hub_Spacer_Gen (header format understanding)

This parser provides high-accuracy detection of:
- Program numbers
- Spacer types (Standard, Hub-Centric, STEP, 2-Piece, Metric)
- Dimensions (OD, Thickness, CB, OB, Hub Height, Counterbore)
- Material
- P-codes and validation
"""

import os
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class GCodeParseResult:
    """Complete parsing result for a G-code file"""
    # Identifiers
    program_number: str
    filename: str
    file_path: str

    # Part Type
    spacer_type: str  # 'standard', 'hub_centric', 'step', '2pc_part1', '2pc_part2', 'metric_spacer'
    detection_method: str  # 'BOTH', 'KEYWORD', 'PATTERN', 'NONE'
    detection_confidence: str  # 'HIGH', 'MEDIUM', 'LOW', 'CONFLICT', 'NONE'

    # Dimensions
    outer_diameter: Optional[float]  # inches
    thickness: Optional[float]  # inches (always stored in inches for calculations)
    thickness_display: Optional[str]  # Original format from title: "10MM" or "0.75"
    center_bore: Optional[float]  # mm
    hub_height: Optional[float]  # inches (hub-centric only)
    hub_diameter: Optional[float]  # mm (hub-centric only, same as OB)
    counter_bore_diameter: Optional[float]  # mm (STEP only)
    counter_bore_depth: Optional[float]  # inches (STEP only)

    # Material
    material: str  # '6061-T6', 'Steel', 'Stainless'

    # Metadata
    title: str
    date_created: Optional[str]
    last_modified: Optional[str]

    # Validation Data
    pcodes_found: List[int]
    drill_depth: Optional[float]
    cb_from_gcode: Optional[float]  # mm
    ob_from_gcode: Optional[float]  # mm
    od_from_gcode: Optional[float]  # inches (diameter)

    # Issues/Warnings (categorized by severity)
    validation_issues: List[str]          # CRITICAL errors (RED)
    validation_warnings: List[str]        # General warnings (YELLOW)
    bore_warnings: List[str]              # Bore dimension warnings (ORANGE)
    dimensional_issues: List[str]         # P-code/thickness mismatches (PURPLE)
    detection_notes: List[str]


class ImprovedGCodeParser:
    """
    Enhanced G-code parser combining multiple detection strategies
    """

    def __init__(self):
        self.debug = False

    def parse_file(self, file_path: str) -> Optional[GCodeParseResult]:
        """
        Main parsing function - combines all detection methods
        """
        try:
            filename = os.path.basename(file_path)

            # Read file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Initialize result
            result = GCodeParseResult(
                program_number=None,
                filename=filename,
                file_path=file_path,
                spacer_type='standard',
                detection_method='NONE',
                detection_confidence='NONE',
                outer_diameter=None,
                thickness=None,
                thickness_display=None,
                center_bore=None,
                hub_height=None,
                hub_diameter=None,
                counter_bore_diameter=None,
                counter_bore_depth=None,
                material='6061-T6',
                title='',
                date_created=None,
                last_modified=None,
                pcodes_found=[],
                drill_depth=None,
                cb_from_gcode=None,
                ob_from_gcode=None,
                od_from_gcode=None,
                validation_issues=[],
                validation_warnings=[],
                bore_warnings=[],
                dimensional_issues=[],
                detection_notes=[]
            )

            # 1. Extract program number
            result.program_number = self._extract_program_number(filename, lines)

            # 2. Extract title
            result.title = self._extract_title(lines)

            # 3. Detect spacer type (combined keyword + pattern)
            type_detection = self._detect_spacer_type_combined(result.title, lines)
            result.spacer_type = type_detection['final_type']
            result.detection_method = type_detection['method']
            result.detection_confidence = type_detection['confidence']
            result.detection_notes = type_detection['notes']

            # 4. Extract dimensions from title
            self._extract_dimensions_from_title(result)

            # 5. Extract dimensions from G-code
            self._extract_dimensions_from_gcode(result, lines)

            # 6. Extract material
            result.material = self._extract_material(result.title, lines)

            # 7. Extract P-codes
            result.pcodes_found = self._extract_pcodes(lines)

            # 8. Extract drill depth
            result.drill_depth = self._extract_drill_depth(lines)

            # 9. Validate consistency
            self._validate_consistency(result)

            # 10. Get file timestamps
            try:
                from datetime import datetime
                stat = os.stat(file_path)
                result.date_created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                result.last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except:
                pass

            return result

        except Exception as e:
            if self.debug:
                print(f"Error parsing {file_path}: {e}")
            return None

    def _extract_program_number(self, filename: str, lines: List[str]) -> Optional[str]:
        """
        Extract program number from filename and validate against file content
        """
        # From filename
        match = re.search(r'[oO](\d{4,6})', filename)
        file_prog_num = match.group(1) if match else None

        # From file content (first 30 lines)
        internal_prog_num = None
        for line in lines[:30]:
            match = re.search(r'^[oO](\d{4,6})', line.strip())
            if match:
                internal_prog_num = match.group(1)
                break

        # Return the program number (prefer internal)
        if internal_prog_num:
            return f"o{internal_prog_num}"
        elif file_prog_num:
            return f"o{file_prog_num}"

        return None

    def _extract_title(self, lines: List[str]) -> str:
        """
        Extract title from first few lines

        Hub_Spacer_Gen format: O12345 (6.5IN DIA 77/93.1MM 1.50 HC 0.5)
        """
        for line in lines[:10]:
            if line.strip().startswith(('O', 'o')) and '(' in line:
                match = re.search(r'\(([^)]+)\)', line)
                if match:
                    return match.group(1).strip()
        return ''

    def _detect_spacer_type_combined(self, title: str, lines: List[str]) -> Dict:
        """
        Combined detection using BOTH keywords and G-code patterns
        Based on FILE SEARCH/combined_part_detection.py
        """
        result = {
            'final_type': 'standard',
            'confidence': 'NONE',
            'method': 'NONE',
            'notes': []
        }

        # Run keyword detection
        keyword_type, keyword_conf = self._detect_by_keywords(title)

        # Run pattern detection
        pattern_type, pattern_conf = self._detect_by_pattern(lines)

        # Decision logic (from combined_part_detection.py)

        # Case 1: Both agree
        if keyword_type and pattern_type and keyword_type == pattern_type:
            result['final_type'] = keyword_type
            result['confidence'] = 'HIGH'
            result['method'] = 'BOTH'
            result['notes'].append(f'Keyword and pattern agree: {keyword_type}')

        # Case 2: Conflict
        elif keyword_type and pattern_type and keyword_type != pattern_type:
            result['confidence'] = 'CONFLICT'
            result['notes'].append(f'CONFLICT: Keyword={keyword_type}, Pattern={pattern_type}')

            # Rule 0A: HC keyword with EXPLICIT hub height value
            # If title has "HC 0.50" or "1.25 HC 0.50", user is explicitly stating it's hub-centric
            # This overrides pattern detection (even if pattern sees STEP-like two-stage boring)
            # Example: "5.75 IN 70.5-60.1mm 1.25 HC 0.50 L1" - has both bore values AND hub height
            if (keyword_type in ['hub_centric', 'metric_spacer'] and
                'HC' in (title or '').upper()):
                # Check for explicit hub height value after HC
                hub_height_match = re.search(r'HC\s+(\d*\.?\d+)', title or '', re.IGNORECASE)
                if hub_height_match:
                    result['final_type'] = 'hub_centric'
                    result['method'] = 'KEYWORD'
                    result['notes'].append('Using HC keyword (Explicit hub height found - user stated hub-centric)')
                # Rule 0B: HC keyword + HUB_CENTRIC pattern vs STEP pattern
                # These are hub-centric STEP pieces - both STEP bore AND OB in OP2
                # HC keyword indicates the primary classification should be hub-centric
                elif pattern_type == 'step':
                    # Check if there's ALSO hub-centric pattern detected
                    pattern_result = self._detect_by_pattern(lines)
                    if pattern_result[0] == 'hub_centric':
                        result['final_type'] = 'hub_centric'
                        result['method'] = 'KEYWORD'
                        result['notes'].append('Using HC keyword (Hub-centric STEP: has both STEP bore and OB)')
                    # No hub-centric pattern, trust STEP pattern
                    else:
                        result['final_type'] = pattern_type
                        result['method'] = 'PATTERN'
                        result['notes'].append('Using pattern (STEP pattern is highly reliable)')

            # Rule 1: STEP pattern is highly reliable - trust it when HIGH confidence
            elif pattern_type == 'step' and pattern_conf == 'HIGH':
                result['final_type'] = pattern_type
                result['method'] = 'PATTERN'
                result['notes'].append('Using pattern (STEP pattern is highly reliable)')

            # Rule 2: HUB_CENTRIC pattern is reliable - trust it when HIGH confidence
            elif pattern_type == 'hub_centric' and pattern_conf == 'HIGH':
                result['final_type'] = pattern_type
                result['method'] = 'PATTERN'
                result['notes'].append('Using pattern (Hub-Centric pattern is reliable)')

            # Rule 3: If keyword is STEP, trust it (strong indicator)
            elif keyword_type == 'step' and keyword_conf == 'HIGH':
                result['final_type'] = keyword_type
                result['method'] = 'KEYWORD'
                result['notes'].append('Using keyword (STEP keyword is strong indicator)')

            # Rule 4: For HC conflicts, prefer pattern (more reliable than HC keyword alone)
            elif keyword_type in ['hub_centric', 'metric_spacer'] and pattern_conf in ['HIGH', 'MEDIUM']:
                result['final_type'] = pattern_type
                result['method'] = 'PATTERN'
                result['notes'].append('Using pattern (more reliable than HC keyword for type distinction)')

            # Rule 5: Default - prefer keyword if no other rules apply
            else:
                result['final_type'] = keyword_type
                result['method'] = 'KEYWORD'
                result['notes'].append('Using keyword (default in unresolved conflict)')

        # Case 3: Only keyword
        elif keyword_type and not pattern_type:
            result['final_type'] = keyword_type
            result['confidence'] = keyword_conf
            result['method'] = 'KEYWORD'
            result['notes'].append('Using keyword only')

        # Case 4: Only pattern
        elif pattern_type and not keyword_type:
            result['final_type'] = pattern_type
            result['confidence'] = pattern_conf
            result['method'] = 'PATTERN'
            result['notes'].append('Using pattern only')

        # Case 5: Nothing detected - default to standard
        else:
            result['final_type'] = 'standard'
            result['confidence'] = 'LOW'
            result['method'] = 'DEFAULT'
            result['notes'].append('No detection - defaulting to standard')

        return result

    def _detect_by_keywords(self, title: str) -> Tuple[Optional[str], str]:
        """
        Detect spacer type from title keywords
        Returns: (type, confidence)

        Hub_Spacer_Gen formats:
        - Standard: "6.5IN DIA 77MM 1.50"
        - Hub-Centric: "6.5IN DIA 77/93.1MM 1.50 HC 0.5"
        - STEP: "6.5IN DIA 106.1/74M B/C 1.50" or "STEP" or "DEEP"
        """
        if not title:
            return None, 'NONE'

        title_upper = title.upper()

        # STEP indicators (highest priority)
        if any(word in title_upper for word in ['STEP', 'DEEP', 'B/C']):
            return 'step', 'HIGH'

        # HC keyword
        if 'HC' in title_upper:
            # Check for CB/OB pattern (XX/YY format)
            if re.search(r'\d+\.?\d*\s*/\s*\d+\.?\d*', title):
                return 'hub_centric', 'HIGH'
            else:
                return 'hub_centric', 'MEDIUM'

        # Check for CB/OB slash pattern without HC keyword
        if re.search(r'\d+\.?\d*\s*/\s*\d+\.?\d*\s*MM', title, re.IGNORECASE):
            return 'hub_centric', 'MEDIUM'

        # Single CB/ID pattern
        if re.search(r'\d+\.?\d+\s*MM\s+ID', title, re.IGNORECASE):
            return 'standard', 'LOW'

        # 2-piece indicators
        if '2PC' in title_upper:
            if 'LUG' in title_upper or 'PART1' in title_upper or 'P1' in title_upper:
                return '2pc_part1', 'HIGH'
            elif 'STUD' in title_upper or 'PART2' in title_upper or 'P2' in title_upper:
                return '2pc_part2', 'HIGH'

        return None, 'NONE'

    def _detect_by_pattern(self, lines: List[str]) -> Tuple[Optional[str], str]:
        """
        Detect spacer type from G-code machining patterns
        Based on FILE SEARCH/combined_part_detection.py
        """
        try:
            # Track operations
            in_drill = False
            in_bore_op1 = False
            in_bore_op2 = False
            in_turn_op2 = False
            in_flip = False

            drill_depth = None
            bore_x_values = []
            bore_z_values = []
            current_x = None

            cb_marker_found = False
            ob_after_chamfer = False
            chamfer_found = False
            progressive_facing_count = 0

            # Scan file
            for i, line in enumerate(lines):
                line_upper = line.upper()

                # Track operation sections
                if 'T101' in line_upper or '(DRILL)' in line_upper:
                    in_drill = True
                    in_bore_op1 = in_bore_op2 = in_turn_op2 = False
                elif 'T121' in line_upper or 'T202' in line_upper or '(BORE)' in line_upper:
                    in_drill = False
                    if not in_flip:
                        in_bore_op1 = True
                    else:
                        in_bore_op2 = True
                    in_turn_op2 = False
                elif 'T303' in line_upper or ('TURN' in line_upper and 'TOOL' in line_upper):
                    in_drill = in_bore_op1 = in_bore_op2 = False
                    if in_flip:
                        in_turn_op2 = True
                elif 'FLIP' in line_upper:
                    in_flip = True
                    in_drill = in_bore_op1 = False

                # Extract drill depth
                if in_drill:
                    z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
                    if z_match:
                        depth = float(z_match.group(1))
                        if depth > 0.3:
                            drill_depth = depth

                # Track bore OP1 patterns
                if in_bore_op1:
                    x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                    if x_match:
                        current_x = float(x_match.group(1))
                        if current_x > 2.0:
                            bore_x_values.append(current_x)

                    z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
                    if z_match and current_x is not None:
                        z_val = float(z_match.group(1))
                        if z_val > 0.1:
                            bore_z_values.append((current_x, z_val))

                    if '(X IS CB)' in line_upper or 'X IS CB' in line:
                        cb_marker_found = True

                # Track OP2 patterns
                if in_turn_op2:
                    x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                    z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

                    if x_match and z_match:
                        chamfer_x = float(x_match.group(1))
                        z_val = float(z_match.group(1))
                        if chamfer_x > 4.0 and z_val < 2.0:
                            chamfer_found = True
                            # Look ahead for OB
                            for j in range(i+1, min(i+10, len(lines))):
                                x_next = re.search(r'X\s*([\d.]+)', lines[j], re.IGNORECASE)
                                if x_next:
                                    x_val = float(x_next.group(1))
                                    if x_val < chamfer_x * 0.6:
                                        ob_after_chamfer = True
                                        break

                    # Count progressive facing cycles
                    if x_match:
                        x_val = float(x_match.group(1))
                        if x_val > 5.5:
                            for k in range(max(0, i-3), i):
                                prev_x = re.search(r'X\s*([\d.]+)', lines[k], re.IGNORECASE)
                                if prev_x:
                                    prev_x_val = float(prev_x.group(1))
                                    if prev_x_val < 4.0:
                                        progressive_facing_count += 1
                                        break

            # ANALYZE PATTERNS

            # STEP pattern detection
            if drill_depth and len(bore_z_values) >= 2:
                unique_x = []
                for x in bore_x_values:
                    is_unique = True
                    for ux in unique_x:
                        if abs(x - ux) < 0.2:
                            is_unique = False
                            break
                    if is_unique:
                        unique_x.append(x)

                # Check for X changes after intermediate Z
                x_changes = False
                intermediate_z = 0
                for i, (x, z) in enumerate(bore_z_values):
                    if 0.2 < z < drill_depth - 0.2:
                        intermediate_z += 1
                        if i + 1 < len(bore_z_values):
                            next_x, next_z = bore_z_values[i + 1]
                            if abs(next_x - x) > 0.3:
                                x_changes = True

                if len(unique_x) >= 2 and intermediate_z > 0 and x_changes:
                    return 'step', 'HIGH'

            # Hub-centric pattern detection
            if cb_marker_found and ob_after_chamfer and chamfer_found:
                return 'hub_centric', 'HIGH'
            elif progressive_facing_count >= 2:
                return 'hub_centric', 'HIGH'

            # Standard pattern
            if cb_marker_found and not in_bore_op2 and not ob_after_chamfer:
                return 'standard', 'MEDIUM'

            # Metric spacer pattern
            if in_bore_op1 and not cb_marker_found:
                return 'metric_spacer', 'LOW'

            return None, 'NONE'

        except:
            return None, 'NONE'

    def _extract_dimensions_from_title(self, result: GCodeParseResult):
        """
        Extract dimensions from title

        Hub_Spacer_Gen formats:
        - "6.5IN DIA 77MM 1.50" -> OD=6.5, CB=77, Thick=1.50
        - "6.5IN DIA 77/93.1MM 1.50 HC 0.5" -> OD=6.5, CB=77, OB=93.1, Thick=1.50, Hub=0.5
        - "6.5IN DIA 106.1/74MM B/C 1.50" -> OD=6.5, Counterbore=106.1, CB=74, Thick=1.50
        """
        title = result.title

        # Outer Diameter (inches)
        od_patterns = [
            r'(\d+\.?\d*)\s*IN\$?\s+DIA',       # Match "5.75IN$ DIA" or "5.75IN DIA"
            r'(\d+\.?\d*)\s*IN\s+(?!DIA)\d',    # Match "5.75 IN 60MM" (IN followed by number, not DIA)
            r'(\d+\.?\d*)\s*IN\s+ROUND',
            r'(\d+\.?\d*)\s*"\s*(?:DIA|ROUND)',
            r'^(\d+\.?\d*)\s+\d+\.?\d*MM',      # OD at start before MM pattern (e.g., "5.75 70.3MM")
        ]
        for pattern in od_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    od_value = float(match.group(1))
                    # Validate OD is in reasonable range (3-12 inches)
                    if 3.0 <= od_value <= 12.0:
                        result.outer_diameter = od_value
                        break
                except:
                    pass

        # Thickness extraction - capture both value and original format
        # Patterns ordered by priority (most specific first)
        # Note: "15HC" means 15MM thickness + has hub (hub height = 0.50" by default)

        # Check for fractional inch values first (before decimal patterns)
        # Special case: 3/8" → display as "10MM" (3/8" = 0.375" ≈ 9.525mm ≈ 10mm)
        # Other fractions like 7/8" → keep as fraction display
        fraction_match = re.search(r'(\d+)/(\d+)(?:\s*"|\s+|$)', title)
        if fraction_match:
            numerator = int(fraction_match.group(1))
            denominator = int(fraction_match.group(2))
            thickness_inches = numerator / denominator

            # Validate reasonable thickness range
            if 0.25 <= thickness_inches <= 4.0:
                result.thickness = thickness_inches

                # Special case: 3/8" displays as "10MM"
                if numerator == 3 and denominator == 8:
                    result.thickness_display = "10MM"
                else:
                    # Keep other fractions as fractional display (e.g., "7/8")
                    result.thickness_display = f"{numerator}/{denominator}"

        thick_patterns = [
            (r'\s+(\d+)\s*HC(?:\s|$)', 'MM', True),      # "15HC" or " 15 HC" - MM thickness with hub (no "MM" in text)
            (r'(\d+\.?\d*)\s*MM\s+HC', 'MM', True),      # "15MM HC" - MM thickness with hub (explicit MM)
            (r'(\d+\.?\d*)\s*MM\s+THK', 'MM', False),    # "10MM THK" - MM thickness standard
            (r'\s+(\d+\.?\d*)\s*MM\s*$', 'MM', False),   # "10MM" at end
            (r'ID\s+(\d+\.?\d*)\s*MM\s+', 'MM', False),  # "ID 10MM SPACER"
            (r'ID\s+(\d*\.?\d+)(?:\s+|$)', 'IN', False), # "ID 1.5" - inches
            (r'(\d*\.?\d+)\s+THK', 'IN', False),         # "0.75 THK" - inches
            (r'B/C\s+(\d*\.?\d+)', 'IN', False),         # "B/C 1.50"
            (r'MM\s+(\d*\.?\d+)\s+(?:THK|HC)', 'IN', False),  # "MM 1.50 THK"
            (r'/[\d.]+MM\s+(\d*\.?\d+)', 'IN', False),   # After slash pattern
            (r'(\d*\.?\d+)\s*$', 'IN', False),           # End of line (last resort)
        ]

        for pattern, unit, is_hub_centric_mm in thick_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    thickness_val = float(match.group(1))

                    # Determine if this is MM or inches
                    is_metric = (unit == 'MM') or (thickness_val >= 10 and thickness_val <= 100)

                    if is_metric:
                        # Store display format as "##MM"
                        result.thickness_display = f"{int(thickness_val) if thickness_val == int(thickness_val) else thickness_val}MM"
                        # Convert to inches for calculations
                        result.thickness = thickness_val / 25.4
                    else:
                        # Store display format as is
                        result.thickness_display = str(thickness_val)
                        result.thickness = thickness_val

                    # Validate thickness is in reasonable range
                    if 0.25 <= result.thickness <= 4.0:
                        break  # Found valid thickness
                    else:
                        # Reset if out of range
                        result.thickness = None
                        result.thickness_display = None
                except:
                    pass

        # CB/OB pattern (XX/YY or XX-YY format) - more flexible matching
        cb_ob_patterns = [
            r'(\d+\.?\d*)\s*MM\s*/\s*(\d+\.?\d*)\s*MM',  # 70.5MM/60.1MM (both have MM, slash)
            r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*MM',  # 70.5/60.1MM (only second has MM, slash)
            r'(\d+\.?\d*)\s*MM\s*/\s*(\d+\.?\d*)',  # 70.5MM/60.1 (only first has MM, slash)
            r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*MM',  # 70.5-60.1MM (dash separator, MM at end)
            r'(\d+\.?\d*)\s*MM\s*-\s*(\d+\.?\d*)\s*MM',  # 70.5MM-60.1MM (both have MM, dash)
        ]
        cb_ob_match = None
        for pattern in cb_ob_patterns:
            cb_ob_match = re.search(pattern, title, re.IGNORECASE)
            if cb_ob_match:
                break

        if cb_ob_match:
            try:
                first_val = float(cb_ob_match.group(1))
                second_val = float(cb_ob_match.group(2))

                # Determine which is CB and which is OB/Counterbore
                if result.spacer_type == 'step':
                    # For STEP: first is counterbore (larger), second is CB (smaller)
                    result.counter_bore_diameter = first_val
                    result.center_bore = second_val
                else:
                    # For hub-centric: first is CB, second is OB (order matters, not size)
                    # Format: CB-OB or CB/OB (e.g., 70.5-60.1mm means CB=70.5, OB=60.1)
                    result.center_bore = first_val
                    result.hub_diameter = second_val  # OB = Hub OD
            except:
                pass
        else:
            # Single CB value
            cb_match = re.search(r'(\d+\.?\d*)\s*(?:MM|M)\s+(?:ID|CB|B/C)', title, re.IGNORECASE)
            if cb_match:
                try:
                    result.center_bore = float(cb_match.group(1))
                except:
                    pass

        # Hub height (for hub-centric)
        if result.spacer_type == 'hub_centric':
            # Try to extract from title (format: "HC 0.5" or "0.5 HC")
            hub_patterns = [
                r'HC\s+(\d*\.?\d+)',  # HC 0.5
                r'(\d*\.?\d+)\s+HC',  # 0.5 HC
            ]
            for pattern in hub_patterns:
                hub_match = re.search(pattern, title, re.IGNORECASE)
                if hub_match:
                    try:
                        hub_val = float(hub_match.group(1))
                        # Hub height is typically 0.25" to 0.75"
                        if 0.2 < hub_val < 1.0:
                            result.hub_height = hub_val
                            break
                    except:
                        pass

            # If not found in title, use standard 0.50" hub height
            if not result.hub_height:
                result.hub_height = 0.50

    def _extract_dimensions_from_gcode(self, result: GCodeParseResult, lines: List[str]):
        """
        Extract dimensions directly from G-code operations

        Multi-Method Strategy:
        1. CB: Smallest X value in BORE operation (OP1) with Z depth
        2. OB: Smallest X value in OP2 progressive facing (hub-centric only)
        3. Hub Height: Final Z depth in OP2 facing before OB (hub-centric)
        4. Thickness: Calculate from drill_depth - hub_height - 0.15 (hub-centric)
                      or drill_depth - 0.15 (standard/STEP)
        5. OD: Maximum X value in turning operations (lathe in diameter mode)
        """
        in_bore_op1 = False
        in_flip = False
        in_turn_op2 = False

        cb_candidates = []
        ob_candidates = []
        od_candidates = []  # Track OD from turning operations
        op2_z_depths = []  # Track Z depths in OP2 for hub height extraction
        last_z_before_ob = None  # Last Z depth before reaching OB

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Track operations
            if 'FLIP' in line_upper:
                in_flip = True
                in_bore_op1 = False
            elif 'T121' in line_upper or 'BORE' in line_upper:
                if not in_flip:
                    in_bore_op1 = True
                    in_turn_op2 = False
            elif 'T303' in line_upper or ('TURN' in line_upper and 'TOOL' in line_upper):
                in_bore_op1 = False
                if in_flip:
                    in_turn_op2 = True
            elif 'T101' in line_upper or 'DRILL' in line_upper:
                in_bore_op1 = in_turn_op2 = False

            # Extract CB from OP1 BORE
            if in_bore_op1 and not in_flip:
                # Look for X value with Z depth (indicates actual boring)
                x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

                # Check for explicit CB marker comment
                has_cb_marker = '(X IS CB)' in line_upper or 'X IS CB' in line

                if x_match:
                    x_val = float(x_match.group(1))
                    # CB is typically 2.0-4.0 inches in diameter
                    if 1.5 < x_val < 6.0:
                        # Check if there's a Z depth on same line or next few lines
                        has_depth = z_match is not None
                        if not has_depth:
                            # Look ahead a few lines
                            for j in range(i+1, min(i+3, len(lines))):
                                if re.search(r'Z\s*-\s*([\d.]+)', lines[j], re.IGNORECASE):
                                    has_depth = True
                                    break

                        if has_depth:
                            # If this line has "(X IS CB)" comment, this is THE CB value
                            # Clear any previous candidates and use only this value
                            if has_cb_marker:
                                cb_candidates = [x_val]  # Replace all candidates with this definitive value
                            else:
                                cb_candidates.append(x_val)

            # Extract OD from any X value in turning operations
            # Lathe is in diameter mode, so X value IS the diameter (no multiplication needed)
            # Look for T3xx tools (turning/facing operations)
            if re.search(r'T3\d{2}', line_upper):
                # Found a turning tool, now collect X values in next lines
                for j in range(i, min(i+50, len(lines))):  # Look ahead up to 50 lines
                    if re.search(r'T[12]\d{2}', lines[j].upper()):  # Stop at next non-turning tool
                        break
                    x_match = re.search(r'X\s*([\d.]+)', lines[j], re.IGNORECASE)
                    if x_match:
                        x_val = float(x_match.group(1))
                        # OD is typically 3.0-12.0 inches (filter out small X values which are CB/OB)
                        if 3.0 < x_val < 12.0:
                            od_candidates.append(x_val)

            # Extract OB and hub height from OP2 progressive facing (hub-centric only)
            if in_turn_op2:
                x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

                # Track Z depths for hub height calculation
                if z_match:
                    z_val = float(z_match.group(1))
                    if 0.1 < z_val < 2.0:  # Reasonable hub height range
                        op2_z_depths.append((z_val, x_match.group(1) if x_match else None))

                if x_match and result.spacer_type == 'hub_centric':
                    x_val = float(x_match.group(1))
                    # OB (Hub D) is typically 2.2-4.0 inches (filter out OD facing operations > 4.0)
                    # Progressive facing cuts down to the OB, then retracts to smaller X (CB)
                    # Exclude values too large (OD facing) and too small (CB)
                    if 2.2 < x_val < 4.0:
                        ob_candidates.append(x_val)

        # Select CB: smallest from candidates (actual bore diameter)
        if cb_candidates:
            result.cb_from_gcode = min(cb_candidates) * 25.4  # Convert to mm

        # Select OB: largest from OP2 candidates (hub diameter is the target of progressive facing)
        # Progressive facing cuts DOWN from large diameter TO the hub diameter (OB)
        # Then chamfers further down toward CB
        if ob_candidates and cb_candidates:
            cb_inches = min(cb_candidates)
            # Filter OB candidates to only those significantly larger than CB (> 0.15" margin)
            valid_ob = [x for x in ob_candidates if x > cb_inches + 0.15]
            if valid_ob:
                # Use MAXIMUM X value - progressive facing cuts down TO this diameter (hub OD)
                result.ob_from_gcode = max(valid_ob) * 25.4  # Convert to mm
        elif ob_candidates:
            result.ob_from_gcode = min(ob_candidates) * 25.4  # Convert to mm

        # Select OD: maximum from turning operations (already in diameter mode)
        if od_candidates:
            result.od_from_gcode = max(od_candidates)  # Already in inches, no conversion needed

        # Extract hub height from OP2 Z depths (hub-centric only)
        # The pattern: progressive facing goes to deeper Z values, then final Z before OB is hub height
        if result.spacer_type == 'hub_centric' and op2_z_depths:
            # Find Z depths associated with larger X values (facing cuts)
            # The last/deepest Z before we hit small X (OB) is typically the hub height
            facing_z_values = []
            for z_val, x_str in op2_z_depths:
                if x_str:
                    try:
                        x_val = float(x_str)
                        if x_val > 4.0:  # Facing cuts, not OB
                            facing_z_values.append(z_val)
                    except:
                        pass

            if facing_z_values:
                # Hub height is the deepest Z in the facing sequence
                calculated_hub_height = max(facing_z_values)
                # Validate it's reasonable (0.25" to 0.75")
                if 0.2 < calculated_hub_height < 1.0:
                    # Only override if title didn't have hub height
                    if not result.hub_height or result.hub_height == 0.50:
                        result.hub_height = round(calculated_hub_height, 2)

        # Multi-method thickness calculation (fallback if not in title)
        if not result.thickness:
            # Method 1: From P-codes (work offset indicates total height) - ALWAYS try this first
            thickness_from_pcode = self._calculate_thickness_from_pcode(result.pcodes_found, result.spacer_type)
            if thickness_from_pcode:
                result.thickness = thickness_from_pcode
                # Set display format to inches (from P-code fallback)
                if not result.thickness_display:
                    result.thickness_display = str(thickness_from_pcode)
            # Method 2: From drill depth (if P-code method didn't work)
            elif result.drill_depth:
                if result.spacer_type == 'hub_centric' and result.hub_height:
                    # thickness = drill_depth - hub_height - 0.15" clearance
                    result.thickness = round(result.drill_depth - result.hub_height - 0.15, 2)
                else:
                    # Standard/STEP: thickness = drill_depth - 0.15"
                    result.thickness = round(result.drill_depth - 0.15, 2)
                # Set display format to inches (from drill depth fallback)
                if not result.thickness_display:
                    result.thickness_display = str(result.thickness)

        # COMPREHENSIVE FALLBACK LOGIC - Use G-code extraction when title parsing fails

        # OD fallback
        if not result.outer_diameter and result.od_from_gcode:
            result.outer_diameter = result.od_from_gcode

        # CB fallback
        if not result.center_bore and result.cb_from_gcode:
            result.center_bore = result.cb_from_gcode

        # OB/Hub Diameter fallback (hub-centric only)
        if result.spacer_type == 'hub_centric' and not result.hub_diameter and result.ob_from_gcode:
            result.hub_diameter = result.ob_from_gcode

    def _calculate_thickness_from_pcode(self, pcodes: List[int], spacer_type: str) -> Optional[float]:
        """
        Calculate thickness from P-codes (work offsets)

        P-code indicates TOTAL part thickness/height for ALL part types.
        For hub-centric: thickness = total_height - hub_height

        Complete P-code mapping:
        P1/P2   → 10MM  (0.394")
        P3/P4   → 12MM  (0.472")
        P5/P6   → 15MM / 0.50"
        P7/P8   → 17MM  (0.669")
        P13/P14 → 0.75"
        P15/P16 → 1.00"
        P17/P18 → 1.25"
        P19/P20 → 1.50"
        P21/P22 → 1.75"
        P23/P24 → 2.00"
        P25/P26 → 2.25"
        P27/P28 → 2.50"
        P29/P30 → 2.75"
        P31/P32 → 3.00"
        P33/P34 → 3.25"
        P35/P36 → 3.50"
        P37/P38 → 3.75"
        P39/P40 → 4.00"
        """
        if not pcodes:
            return None

        # P-code to total height mapping (complete table)
        pcode_map = {
            1: 10/25.4,    # 10MM → 0.394"
            2: 10/25.4,
            3: 12/25.4,    # 12MM → 0.472"
            4: 12/25.4,
            5: 0.50,       # 15MM / 0.50"
            6: 0.50,
            7: 17/25.4,    # 17MM → 0.669"
            8: 17/25.4,
            13: 0.75,      # 0.75"
            14: 0.75,
            15: 1.00,      # 1.00"
            16: 1.00,
            17: 1.25,      # 1.25" (all parts, not just hub-centric!)
            18: 1.25,
            19: 1.50,      # 1.50"
            20: 1.50,
            21: 1.75,      # 1.75"
            22: 1.75,
            23: 2.00,      # 2.00"
            24: 2.00,
            25: 2.25,      # 2.25"
            26: 2.25,
            27: 2.50,      # 2.50"
            28: 2.50,
            29: 2.75,      # 2.75"
            30: 2.75,
            31: 3.00,      # 3.00"
            32: 3.00,
            33: 3.25,      # 3.25"
            34: 3.25,
            35: 3.50,      # 3.50"
            36: 3.50,
            37: 3.75,      # 3.75"
            38: 3.75,
            39: 4.00,      # 4.00"
            40: 4.00,
        }

        # Find matching P-code
        for pcode in pcodes:
            if pcode in pcode_map:
                total_height = pcode_map[pcode]

                # For hub-centric, subtract hub height to get thickness
                if spacer_type == 'hub_centric':
                    return round(total_height - 0.50, 2)  # Standard 0.50" hub
                else:
                    return total_height

        return None

    def _extract_material(self, title: str, lines: List[str]) -> str:
        """
        Extract material from title or file content
        """
        full_text = title + ' ' + ' '.join(lines[:30])
        full_lower = full_text.lower()

        if 'stainless' in full_lower or 'ss' in full_lower:
            return 'Stainless'
        elif 'steel' in full_lower and 'stainless' not in full_lower:
            return 'Steel'
        elif '6061' in full_text or 'aluminum' in full_lower or 'aluminium' in full_lower:
            return '6061-T6'

        return '6061-T6'  # Default

    def _extract_pcodes(self, lines: List[str]) -> List[int]:
        """
        Extract all P-codes from G-code
        """
        pcodes = set()
        for line in lines:
            p_matches = re.findall(r'P(\d+)', line, re.IGNORECASE)
            for p in p_matches:
                pcodes.add(int(p))
        return sorted(pcodes)

    def _extract_drill_depth(self, lines: List[str]) -> Optional[float]:
        """
        Extract drill depth from G81/G83 commands
        """
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('G81', 'G83')):
                z_match = re.search(r'Z\s*-?\s*([\d.]+)', stripped, re.IGNORECASE)
                if z_match:
                    return float(z_match.group(1))
        return None

    def _validate_consistency(self, result: GCodeParseResult):
        """
        Validate G-code against title specifications

        CRITICAL: Title is SPECIFICATION (what part should be)
                  G-code is IMPLEMENTATION (what will be cut)
                  If mismatch within tolerance -> G-CODE HAS ERROR

        Tolerances (from production requirements):
        - CB/Counterbore: +0.1mm (looser fit acceptable)
        - OB: -0.1mm (tighter fit acceptable)
        - Thickness: ±0.01" (very tight)
        """
        # Program number mismatch (filename vs internal)
        filename = result.filename
        file_prog_match = re.search(r'[oO](\d{4,6})', filename)
        if file_prog_match and result.program_number:
            file_prog_num = f"o{file_prog_match.group(1)}"
            if file_prog_num != result.program_number:
                result.validation_issues.append(
                    f'FILENAME MISMATCH: File {file_prog_num} != Internal {result.program_number}'
                )

        # CB Validation: Title is SPEC, G-code should be within tolerance
        # Acceptable range: title_cb to (title_cb + 0.1mm)
        if result.center_bore and result.cb_from_gcode:
            title_cb = result.center_bore  # SPECIFICATION
            gcode_cb = result.cb_from_gcode  # IMPLEMENTATION

            # Check if G-code is within acceptable range
            # Lower bound: title_cb - 0.2mm (warning threshold)
            # Upper bound: title_cb + 0.3mm (max acceptable, includes +0.1mm tolerance + margin)
            diff = gcode_cb - title_cb

            if diff < -0.2:
                # CRITICAL: CB way too small - RED
                result.validation_issues.append(
                    f'CB TOO SMALL: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif diff > 0.3:
                # CRITICAL: CB way too large - RED
                result.validation_issues.append(
                    f'CB TOO LARGE: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif abs(diff) > 0.1:
                # BORE WARNING: At tolerance limit - ORANGE
                result.bore_warnings.append(
                    f'CB at tolerance limit: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm)'
                )

        # OB Validation: Title is SPEC, G-code should be within tolerance
        # Acceptable range: (title_ob - 0.1mm) to title_ob
        if result.hub_diameter and result.ob_from_gcode:
            title_ob = result.hub_diameter  # SPECIFICATION
            gcode_ob = result.ob_from_gcode  # IMPLEMENTATION

            # Check if G-code is within acceptable range
            # Lower bound: title_ob - 0.3mm (max acceptable, includes -0.1mm tolerance + margin)
            # Upper bound: title_ob + 0.2mm (warning threshold)
            diff = gcode_ob - title_ob

            if diff < -0.3:
                # CRITICAL: OB way too small - RED
                result.validation_issues.append(
                    f'OB TOO SMALL: Spec={title_ob:.1f}mm, G-code={gcode_ob:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif diff > 0.2:
                # CRITICAL: OB way too large - RED
                result.validation_issues.append(
                    f'OB TOO LARGE: Spec={title_ob:.1f}mm, G-code={gcode_ob:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif abs(diff) > 0.1:
                # BORE WARNING: At tolerance limit - ORANGE
                result.bore_warnings.append(
                    f'OB at tolerance limit: Spec={title_ob:.1f}mm, G-code={gcode_ob:.1f}mm ({diff:+.2f}mm)'
                )

        # Thickness validation from drill depth
        # Title thickness is SPEC, drill depth should produce correct thickness
        if result.drill_depth and result.thickness:
            title_thickness = result.thickness  # SPECIFICATION

            # Calculate actual thickness from drill depth
            # Standard/STEP: thickness = drill_depth - 0.15"
            # Hub-Centric: thickness = drill_depth - 0.65" (includes 0.50" hub + 0.15" clearance)
            if result.spacer_type == 'hub_centric':
                calculated_thickness = result.drill_depth - 0.65
            else:
                calculated_thickness = result.drill_depth - 0.15

            # Tolerance: ±0.01"
            diff = calculated_thickness - title_thickness

            if abs(diff) > 0.02:  # Beyond ±0.01" with margin
                # CRITICAL: Thickness way off - RED
                result.validation_issues.append(
                    f'THICKNESS ERROR: Spec={title_thickness:.2f}", Calculated from drill={calculated_thickness:.2f}" ({diff:+.3f}") - CRITICAL ERROR'
                )
            elif abs(diff) > 0.01:
                # DIMENSIONAL: Thickness mismatch - PURPLE
                result.dimensional_issues.append(
                    f'Thickness mismatch: Spec={title_thickness:.2f}", Calculated={calculated_thickness:.2f}" ({diff:+.3f}")'
                )

        # OD Validation: Title is SPEC, G-code should match within tolerance
        # Tolerance: ±0.05" (OD is less critical than bore dimensions)
        if result.outer_diameter and result.od_from_gcode:
            title_od = result.outer_diameter  # SPECIFICATION
            gcode_od = result.od_from_gcode  # IMPLEMENTATION

            diff = gcode_od - title_od

            if abs(diff) > 0.1:  # More than ±0.1" is an error
                result.validation_issues.append(
                    f'OD MISMATCH: Spec={title_od:.2f}", G-code={gcode_od:.2f}" ({diff:+.3f}") - G-CODE ERROR'
                )
            elif abs(diff) > 0.05:  # Warning zone ±0.05-0.1"
                result.validation_warnings.append(
                    f'OD tolerance check: Spec={title_od:.2f}", G-code={gcode_od:.2f}" ({diff:+.3f}")'
                )

        # P-Code Consistency Validation
        if result.pcodes_found:
            # Check 1: P-codes should come in pairs (odd + even)
            # OP1 uses odd P-codes (P13, P15, P17, etc.)
            # OP2 uses even P-codes (P14, P16, P18, etc.)
            odd_pcodes = [p for p in result.pcodes_found if p % 2 == 1]
            even_pcodes = [p for p in result.pcodes_found if p % 2 == 0]

            if odd_pcodes and not even_pcodes:
                result.validation_warnings.append(
                    f'P-CODE PAIRING: Only OP1 P-codes found {odd_pcodes}, missing OP2 pair'
                )
            elif even_pcodes and not odd_pcodes:
                result.validation_warnings.append(
                    f'P-CODE PAIRING: Only OP2 P-codes found {even_pcodes}, missing OP1 pair'
                )
            elif odd_pcodes and even_pcodes:
                # Check if pairs match (P13 with P14, P15 with P16, etc.)
                for odd in odd_pcodes:
                    if odd + 1 not in even_pcodes:
                        result.validation_warnings.append(
                            f'P-CODE PAIRING: P{odd} found but P{odd+1} missing'
                        )

            # Check 2: Should only have ONE pair of P-codes
            if len(result.pcodes_found) > 2:
                result.validation_warnings.append(
                    f'MULTIPLE P-CODES: Found {result.pcodes_found} - should only have one pair (OP1+OP2)'
                )

            # Check 3: Validate P-code matches detected thickness
            # Calculate expected P-codes for the thickness
            if result.thickness:
                # For hub-centric, P-code = thickness + 0.50"
                if result.spacer_type == 'hub_centric':
                    total_height = result.thickness + 0.50
                else:
                    total_height = result.thickness

                # Find expected P-codes
                pcode_map = {
                    1: 10/25.4, 3: 12/25.4, 5: 0.50, 7: 17/25.4,
                    13: 0.75, 15: 1.00, 17: 1.25, 19: 1.50,
                    21: 1.75, 23: 2.00, 25: 2.25, 27: 2.50,
                    29: 2.75, 31: 3.00, 33: 3.25, 35: 3.50,
                    37: 3.75, 39: 4.00
                }

                expected_pcode = None
                for pcode, height in pcode_map.items():
                    if abs(height - total_height) < 0.01:  # Match within 0.01"
                        expected_pcode = pcode
                        break

                if expected_pcode:
                    # Check if any found P-code matches expected
                    if expected_pcode not in result.pcodes_found and (expected_pcode + 1) not in result.pcodes_found:
                        actual_pcodes = [p for p in result.pcodes_found if p in pcode_map or p+1 in pcode_map]
                        if actual_pcodes:
                            # DIMENSIONAL: P-code doesn't match thickness - PURPLE
                            result.dimensional_issues.append(
                                f'P-CODE MISMATCH: Thickness {result.thickness}\" expects P{expected_pcode}/P{expected_pcode+1}, but found {actual_pcodes}'
                            )


# Test the parser
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        print("Usage: python improved_gcode_parser.py <file_path>")
        sys.exit(1)

    parser = ImprovedGCodeParser()
    parser.debug = True

    result = parser.parse_file(test_file)

    if result:
        print("=" * 80)
        print("PARSE RESULT")
        print("=" * 80)
        print(f"File: {result.filename}")
        print(f"Program: {result.program_number}")
        print(f"Title: {result.title}")
        print()
        print(f"Type: {result.spacer_type} ({result.detection_confidence})")
        print(f"Detection: {result.detection_method}")
        for note in result.detection_notes:
            print(f"  - {note}")
        print()
        print(f"OD: {result.outer_diameter}\"" if result.outer_diameter else "OD: Not found")
        print(f"Thickness: {result.thickness}\"" if result.thickness else "Thickness: Not found")
        print(f"CB: {result.center_bore}mm" if result.center_bore else "CB: Not found")
        if result.hub_height:
            print(f"Hub Height: {result.hub_height}\"")
        if result.hub_diameter:
            print(f"Hub Diameter (OB): {result.hub_diameter}mm")
        if result.counter_bore_diameter:
            print(f"Counterbore: {result.counter_bore_diameter}mm")
        print(f"Material: {result.material}")
        print()
        if result.pcodes_found:
            print(f"P-codes: {result.pcodes_found}")
        if result.drill_depth:
            print(f"Drill Depth: {result.drill_depth:.2f}\"")
        print()
        if result.validation_issues:
            print("ISSUES:")
            for issue in result.validation_issues:
                print(f"  - {issue}")
        if result.validation_warnings:
            print("WARNINGS:")
            for warning in result.validation_warnings:
                print(f"  - {warning}")
    else:
        print("Failed to parse file")
