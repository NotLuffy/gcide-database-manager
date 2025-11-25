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
    title: Optional[str]  # Raw title from G-code (content in parentheses)
    filename: str
    file_path: str

    # Part Type
    spacer_type: str  # 'standard', 'hub_centric', 'step', 'steel_ring', '2PC LUG', '2PC STUD', '2PC UNSURE', 'metric_spacer'
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

    # Lathe Assignment
    lathe: Optional[str]  # 'L1', 'L2', 'L3', 'L2/L3' (for overlapping sizes)

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

    # P-code tables as class constants (computed once)
    PCODE_TABLE_L1 = {
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
        17: 1.25,      # 1.25"
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

    # L2/L3 P-code table (computed once)
    PCODE_TABLE_L2_L3 = {}
    _thickness = 1.00
    _pcode = 5
    while _thickness <= 4.00:
        PCODE_TABLE_L2_L3[_pcode] = _thickness
        PCODE_TABLE_L2_L3[_pcode + 1] = _thickness
        _thickness += 0.25
        _pcode += 2

    # Standard OD sizes (inches) - actual machined sizes are slightly under
    STANDARD_OD_SIZES = [5.75, 6.00, 6.25, 6.50, 7.00, 7.50, 8.00, 8.50, 9.50, 10.25, 10.50, 13.00]

    def __init__(self):
        self.debug = False

    @staticmethod
    def _round_to_standard_od(od_value: float) -> float:
        """
        Round OD value to nearest standard size.
        Machined parts are typically 0.02-0.04" under nominal size.
        """
        if od_value is None:
            return None

        # Find the nearest standard OD size
        closest = None
        min_diff = float('inf')

        for std_od in ImprovedGCodeParser.STANDARD_OD_SIZES:
            diff = abs(od_value - std_od)
            # Allow up to 0.1" tolerance for rounding to standard
            if diff < min_diff and diff <= 0.1:
                min_diff = diff
                closest = std_od

        return closest if closest else od_value

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
                lathe=None,
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

            # 7. Assign lathe based on OD
            result.lathe = self._assign_lathe(result.outer_diameter)

            # 8. Extract P-codes
            result.pcodes_found = self._extract_pcodes(lines)

            # 8. Extract drill depth
            result.drill_depth = self._extract_drill_depth(lines)

            # 8a. Detect hub-centric from G-code if not detected from title
            # If title has CB/OB (CB < OB) but no "HC" keyword, check if hub is machined in OP2
            self._detect_hub_from_gcode(result, lines)

            # 8b. Calculate hub height from drill depth if needed
            # For ANY part type where drill depth suggests a hub exists
            if result.drill_depth and result.thickness:
                # Calculate potential hub from drill depth
                potential_hub = result.drill_depth - result.thickness - 0.15

                # If potential hub is reasonable (0.3" to 3.5"), this might be hub-centric
                if 0.3 <= potential_hub <= 3.5:
                    # If not already hub_centric, check if we should reclassify
                    if result.spacer_type != 'hub_centric':
                        # Reclassify as hub_centric if drill suggests significant hub
                        result.spacer_type = 'hub_centric'
                        result.detection_method = 'DRILL_DEPTH'
                        result.detection_confidence = 'MEDIUM'
                        result.hub_height = round(potential_hub, 2)
                    # If already hub_centric but hub_height is default 0.50, update it
                    elif not result.hub_height or result.hub_height == 0.50:
                        result.hub_height = round(potential_hub, 2)

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
        # From filename (4+ digits)
        match = re.search(r'[oO](\d{4,})', filename)
        file_prog_num = match.group(1) if match else None

        # From file content (first 30 lines)
        internal_prog_num = None
        for line in lines[:30]:
            match = re.search(r'^[oO](\d{4,})', line.strip())
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

        # Run keyword detection (scan title AND all comments in file)
        keyword_type, keyword_conf = self._detect_by_keywords(title, lines)

        # Run pattern detection
        pattern_type, pattern_conf = self._detect_by_pattern(lines, title)

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
                    pattern_result = self._detect_by_pattern(lines, title)
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

    def _detect_by_keywords(self, title: str, lines: List[str] = None) -> Tuple[Optional[str], str]:
        """
        Detect spacer type from title keywords AND comments throughout the file
        Returns: (type, confidence)

        Hub_Spacer_Gen formats:
        - Standard: "6.5IN DIA 77MM 1.50"
        - Hub-Centric: "6.5IN DIA 77/93.1MM 1.50 HC 0.5"
        - STEP: "6.5IN DIA 106.1/74M B/C 1.50" or "STEP" or "DEEP"
        - 2PC: "2PC LUG" or "2PC STUD" (can be in comments)
        """
        # Collect all text to search (title + all comments in file)
        search_texts = []
        if title:
            search_texts.append(title)

        # Extract all comments from G-code file
        if lines:
            for line in lines[:100]:  # Scan first 100 lines for comments
                # G-code comments are in parentheses or after semicolon
                # Example: (2PC STUD) or ; 2PC LUG
                if '(' in line:
                    # Extract text between parentheses
                    comment_match = re.findall(r'\(([^)]+)\)', line)
                    search_texts.extend(comment_match)
                if ';' in line:
                    # Extract text after semicolon
                    comment_text = line.split(';', 1)[1].strip()
                    if comment_text:
                        search_texts.append(comment_text)

        if not search_texts:
            return None, 'NONE'

        # Combine all search text
        combined_text = ' '.join(search_texts)
        combined_upper = combined_text.upper()

        # Track detection source for better confidence
        title_upper = title.upper() if title else ''
        found_in_title = False
        found_in_comments = False

        # STEP indicators (highest priority)
        step_keywords = ['STEP', 'DEEP', 'B/C']
        if any(word in combined_upper for word in step_keywords):
            found_in_title = any(word in title_upper for word in step_keywords)
            found_in_comments = not found_in_title and any(word in combined_upper for word in step_keywords)
            confidence = 'HIGH' if found_in_title else 'MEDIUM'
            return 'step', confidence

        # Steel Ring indicators
        # Patterns: "STEEL S-1", "HCS-1", "STEEL HCS-2", "STEEL HCS-1"
        if re.search(r'STEEL\s+S-\d|HCS-\d|STEEL\s+HCS-\d', combined_upper):
            found_in_title = re.search(r'STEEL\s+S-\d|HCS-\d|STEEL\s+HCS-\d', title_upper) is not None
            confidence = 'HIGH' if found_in_title else 'MEDIUM'
            return 'steel_ring', confidence

        # 2-piece indicators (check before other patterns that might match parts of 2PC titles)
        # 2PC = 2-piece spacer, comes in LUG or STUD variants
        # IMPORTANT: If title has "HC", prioritize hub_centric over 2PC (2PC might be in comments)
        if '2PC' in combined_upper and 'HC' not in title_upper:
            found_in_title = '2PC' in title_upper

            if 'LUG' in combined_upper:
                confidence = 'HIGH' if (found_in_title and 'LUG' in title_upper) else 'MEDIUM'
                return '2PC LUG', confidence
            elif 'STUD' in combined_upper:
                confidence = 'HIGH' if (found_in_title and 'STUD' in title_upper) else 'MEDIUM'
                return '2PC STUD', confidence
            else:
                # 2PC without specifying LUG or STUD
                confidence = 'MEDIUM' if found_in_title else 'LOW'
                return '2PC UNSURE', confidence

        # Thin hub centric indicator
        if 'THIN' in combined_upper and 'HC' in combined_upper:
            found_in_title = 'THIN' in title_upper
            confidence = 'HIGH' if found_in_title else 'MEDIUM'
            return 'thin_hub_centric', confidence

        # HC keyword
        if 'HC' in combined_upper:
            found_in_title = 'HC' in title_upper
            # Check for CB/OB pattern (XX/YY format)
            if re.search(r'\d+\.?\d*\s*/\s*\d+\.?\d*', combined_text):
                confidence = 'HIGH' if found_in_title else 'MEDIUM'
                return 'hub_centric', confidence
            else:
                confidence = 'MEDIUM' if found_in_title else 'LOW'
                return 'hub_centric', confidence

        # Check for CB/OB slash pattern without HC keyword
        # XX/YY MM ID or OD (without HC) = step pattern (shelf/CB format, larger first)
        # XX/YY MM HC = hub_centric pattern (CB/OB format, smaller first)
        if re.search(r'\d+\.?\d*\s*/\s*\d+\.?\d*\s*MM', combined_text, re.IGNORECASE):
            # If has "ID" or "OD" marker but not "HC", it's STEP format (outer/inner)
            # "ID" = specifying inner diameter, "OD" = specifying outer diameter
            if ('ID' in combined_upper or 'OD' in combined_upper) and 'HC' not in combined_upper:
                return 'step', 'MEDIUM'
            else:
                return 'hub_centric', 'MEDIUM'

        # Single CB/ID pattern
        if re.search(r'\d+\.?\d+\s*MM\s+ID', combined_text, re.IGNORECASE):
            return 'standard', 'LOW'

        return None, 'NONE'

    def _detect_by_pattern(self, lines: List[str], title: str = '') -> Tuple[Optional[str], str]:
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
                    # Scale threshold based on OD (use 95% of OD as threshold)
                    if x_match:
                        x_val = float(x_match.group(1))
                        # Dynamic threshold: for 5.75" OD use 5.5, for 7" use 6.6, for 13" use 12.35
                        od_threshold = max(5.5, (od * 0.95 if od else 5.5))
                        small_x_threshold = min(4.0, od * 0.55 if od else 4.0)  # Scale small X threshold too
                        if x_val > od_threshold:
                            for k in range(max(0, i-3), i):
                                prev_x = re.search(r'X\s*([\d.]+)', lines[k], re.IGNORECASE)
                                if prev_x:
                                    prev_x_val = float(prev_x.group(1))
                                    if prev_x_val < small_x_threshold:
                                        progressive_facing_count += 1
                                        break

            # ANALYZE PATTERNS

            # PRIORITY 1: HC keyword in title (highest priority)
            # If "HC" appears in title, it's hub-centric regardless of machining pattern
            # Example: "5.75 IN 71.6/71.6mm 1.5 HC L1" - HC trumps step patterns
            if title and 'HC' in title.upper():
                # Verify there are hub-centric indicators (CB marker, OB, chamfer, or progressive facing)
                if cb_marker_found or ob_after_chamfer or chamfer_found or progressive_facing_count > 0:
                    return 'hub_centric', 'HIGH'

            # PRIORITY 2: Hub-centric pattern detection (before STEP)
            # Strong hub-centric indicators should override step patterns
            if cb_marker_found and ob_after_chamfer and chamfer_found:
                return 'hub_centric', 'HIGH'
            elif progressive_facing_count >= 2:
                return 'hub_centric', 'HIGH'

            # PRIORITY 3: STEP pattern detection
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
            r'(\d+\.?\d*)\s*IN[\$]?\s+DIA',     # Match "5.75IN$ DIA" or "5.75IN DIA"
            r'(\d+\.?\d*)\s*IN\s+(?!DIA)\d',    # Match "5.75 IN 60MM" (IN followed by number, not DIA)
            r'(\d+\.?\d*)\s*IN\s+ROUND',
            r'(\d+\.?\d*)\s*"\s*(?:DIA|ROUND)',
            r'^(\d+\.?\d*)\s+\d+\.?\d*[/\d\.]*(?:IN|MM)',  # OD at start before IN or MM pattern (e.g., "13.0 170.1/220MM")
        ]
        for pattern in od_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                try:
                    od_value = float(match.group(1))
                    # Validate OD is in reasonable range (3-14 inches to include 13" rounds)
                    if 3.0 <= od_value <= 14.0:
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

        # Only run decimal patterns if fraction didn't find thickness
        # This prevents "7/8 THK" from being overwritten by THK pattern matching just "8"
        if not result.thickness:
            thick_patterns = [
                (r'\s+(\d+)\s*HC(?:\s|$)', 'MM', True),      # "15HC" or " 15 HC" - MM thickness with hub (no "MM" in text)
                (r'(\d+\.?\d*)\s*MM\s+HC', 'MM', True),      # "15MM HC" - MM thickness with hub (explicit MM)
                (r'(\d+\.?\d*)\s*MM\s+THK', 'MM', False),    # "10MM THK" - MM thickness standard
                (r'\s+(\d+\.?\d*)\s*MM\s*$', 'MM', False),   # "10MM" at end
                (r'ID\s+(\d+\.?\d*)\s*MM\s+', 'MM', False),  # "ID 10MM SPACER"
                (r'ID\s+(\d*\.?\d+)\s+2PC', 'IN', False),    # "ID 1.25 2PC" - thickness before 2PC
                (r'ID\s+(\d*\.?\d+)(?:\s+|$)', 'IN', False), # "ID 1.5" - inches
                (r'(\d*\.?\d+)\s+2PC', 'IN', False),         # "1.75 2PC" - thickness before 2PC
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
            r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*(?:MM?)?\s*(?:ID|B/C)',  # 90/74 B/C or 108/71.5 B/C (with optional MM)
            r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\s*(?:MM?)?\s+(?:ID|B/C)',  # 90/74 B/C with space before B/C
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

                # Check if first value is in inches (for large rounds like "6.25/220MM")
                # Pattern: OD >= 10", first < 10, second has MM but first doesn't
                # Example: "13.0 6.25/220MM" -> 6.25" CB / 220mm OB
                matched_pattern = cb_ob_match.group(0)
                first_has_mm = 'MM' in matched_pattern.split('/')[0].upper() if '/' in matched_pattern else False
                second_has_mm = 'MM' in matched_pattern.upper()

                if (result.outer_diameter and result.outer_diameter >= 10.0 and
                    first_val < 10 and not first_has_mm and second_has_mm):
                    # First value is likely in inches - convert to mm
                    first_val = first_val * 25.4

                # Determine which is CB and which is OB/Counterbore
                if result.spacer_type == 'step':
                    # For STEP: first is counterbore (larger), second is CB (smaller)
                    result.counter_bore_diameter = first_val
                    result.center_bore = second_val
                else:
                    # For hub-centric: format depends on title markers
                    # Check if it's "ID" format (like STEP: outer/inner) or "HC" format (CB/OB)
                    title_upper = title.upper()

                    # If "ID" marker present (not "HC"), treat like STEP format: large/small
                    # This handles hub-centric with support shelf where first=shelf, second=CB
                    if 'ID' in title_upper and 'HC' not in title_upper:
                        # Hub-centric with support shelf: outer shelf / CB
                        # First value is the shelf (like counterbore), second is CB
                        # OB (hub) will be determined from G-code
                        result.center_bore = second_val
                        # Store the shelf dimension - we can use counter_bore_diameter temporarily
                        # or just ignore it since it's not the final hub
                    else:
                        # For HC parts, check if first > second (indicates Shelf/OB format)
                        # Standard HC: CB/OB where CB < OB (e.g., 66.9/106mm)
                        # Shelf/OB HC: first > second (e.g., 108/82.5mm) where first=shelf, second=OB
                        if first_val > second_val * 1.1:  # First is >10% larger = Shelf/OB format
                            # Hub-centric with support shelf: Shelf/OB format
                            # First value is shelf (not CB), second is OB
                            # CB will be determined from G-code
                            result.hub_diameter = second_val  # OB
                            # Don't set center_bore - let G-code extraction find it
                        else:
                            # Standard HC format: CB/OB (e.g., 70.5-60.1mm means CB=70.5, OB=60.1)
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
            # Try to extract from title
            # Pattern 1: "number HC number" format where first=thickness, second=hub height
            # Example: "1.0 HC 1.5" means 1.0" thick + 1.5" hub height
            # Also handles trailing decimals: "2. HC 1.5" = 2.0" thick + 1.5" hub
            # Also handles leading decimals: "5.5 HC .5" = 5.5" thick + 0.5" hub
            # Also handles no space: "1.0 HC.5" = 1.0" thick + 0.5" hub
            dual_hc_match = re.search(r'(\d+\.?\d*)\s*HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
            if dual_hc_match:
                try:
                    first_val = float(dual_hc_match.group(1))
                    second_val = float(dual_hc_match.group(2))

                    # First value is thickness (override any previous thickness detection)
                    # Extended range to 6.5" to handle thick two-operation parts (e.g., 5.5" + 0.5" hub = 6.0" total)
                    if 0.25 <= first_val <= 6.5:
                        result.thickness = first_val
                        result.thickness_display = str(first_val)

                    # Second value is hub height (can be up to 3.5" for larger parts like 13" rounds)
                    if 0.2 <= second_val <= 3.5:
                        result.hub_height = second_val
                except:
                    pass

            # Pattern 2: Single value pattern "HC 0.5" (only value AFTER HC)
            # IMPORTANT: Do NOT match value before HC (that's the thickness)
            if not result.hub_height:
                # Only match HC followed by a value (e.g., "HC 0.5", "HC.5")
                hub_match = re.search(r'HC\s*(\d*\.?\d+)', title, re.IGNORECASE)
                if hub_match:
                    try:
                        hub_val = float(hub_match.group(1))
                        # Hub height can be up to 3.5" for larger parts like 13" rounds
                        if 0.2 <= hub_val <= 3.5:
                            result.hub_height = hub_val
                    except:
                        pass

            # If not found in title, use standard 0.50" hub height as placeholder
            # This will be recalculated from drill depth later if available
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
        cb_found = False  # Stop collecting after finding definitive CB
        ob_candidates = []
        od_candidates = []  # Track OD from turning operations
        op2_z_depths = []  # Track Z depths in OP2 for hub height extraction
        last_z_before_ob = None  # Last Z depth before reaching OB

        # Extract drill depth early (needed for CB depth verification)
        drill_depth = None
        in_drill_op = False
        for line in lines:
            line_upper = line.upper()

            # Track when we're in drill operation
            if 'T101' in line_upper or 'DRILL' in line_upper:
                in_drill_op = True
            elif re.search(r'T[12][0-9]{2}', line_upper) and 'T101' not in line_upper:
                # Moved to different tool
                in_drill_op = False

            # Look for drill depth in canned cycles
            if line.strip().startswith(('G81', 'G83')):
                z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
                if z_match:
                    drill_depth = float(z_match.group(1))
                    break

            # Also look for simple G01 Z movements in drill operation
            if in_drill_op and line.strip().startswith('G01'):
                z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
                # Make sure it's not a rapid positioning (needs Z > 0.3 for actual drill)
                if z_match:
                    z_val = float(z_match.group(1))
                    if z_val > 0.3:  # Actual drill depth, not positioning
                        drill_depth = z_val
                        break

        # Track Z depth after CB chamfer for step depth extraction
        step_depth_candidate = None
        last_bore_x = None  # Track previous X for chamfer detection

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

                # Track step depth: Z depth after chamfer creates CB
                # Pattern: X with Z (chamfer move) -> Z-only (step depth)
                # Detect chamfer by: explicit comment OR 45-degree diagonal move (Z = X_change / 2)
                is_chamfer_line = False
                if 'CHAMFER' in line_upper or '(X IS CB)' in line_upper:
                    is_chamfer_line = True
                elif x_match and z_match and last_bore_x:
                    # Check for 45-degree chamfer: Z depth should be ~half of X change
                    x_val = float(x_match.group(1))
                    z_val = float(z_match.group(1))
                    x_change = abs(last_bore_x - x_val)
                    # 45-degree chamfer: Z should be approximately half of X change
                    # Allow some tolerance (0.4 to 0.6 ratio)
                    if x_change > 0.1 and 0.4 <= z_val / x_change <= 0.6:
                        is_chamfer_line = True

                # Track X positions for chamfer detection
                if x_match:
                    last_bore_x = float(x_match.group(1))

                if is_chamfer_line:
                    # The chamfer X value itself is the CB diameter
                    # Pattern in o10007: X6.701 Z-0.12 (chamfer) → this X6.701 is the CB
                    # Pattern in o13009: X8.665 Z-0.15 (chamfer) → this X8.665 is the CB
                    if x_match:
                        chamfer_x = float(x_match.group(1))
                        if 1.5 < chamfer_x < 10.0:  # Extended to 10.0 for large 13" parts
                            # Add chamfer X as CB candidate
                            cb_candidates.append(chamfer_x)
                            cb_found = True  # This is definitive CB

                    # Also look ahead for step depth (Z-only movement after chamfer)
                    for j in range(i+1, min(i+5, len(lines))):
                        next_line = lines[j]
                        next_x = re.search(r'X\s*([\d.]+)', next_line, re.IGNORECASE)
                        next_z = re.search(r'Z\s*-\s*([\d.]+)', next_line, re.IGNORECASE)

                        # Step depth: Z-only movement right after chamfer
                        if next_z and not next_x and step_depth_candidate is None:
                            z_val = float(next_z.group(1))
                            if 0.1 < z_val < 5.0:  # Step depth range (up to 5" for thick parts)
                                step_depth_candidate = z_val
                        elif next_x:
                            # Stop when we hit another X value
                            break

                # Check for explicit CB marker comment
                has_cb_marker = '(X IS CB)' in line_upper or 'X IS CB' in line

                if x_match:
                    x_val = float(x_match.group(1))
                    # CB is typically 2.0-9.0 inches in diameter (extended for large 13" parts)
                    if 1.5 < x_val < 10.0:
                        # Check if there's a Z depth on same or next lines
                        max_z_depth = None
                        initial_z_depth = None  # First Z with this X (for chamfer detection)
                        if z_match:
                            max_z_depth = float(z_match.group(1))
                            initial_z_depth = max_z_depth

                        # Look ahead for Z movements (check if reaches full drill depth)
                        for j in range(i+1, min(i+5, len(lines))):
                            next_z = re.search(r'Z\s*-\s*([\d.]+)', lines[j], re.IGNORECASE)
                            next_x = re.search(r'X\s*([\d.]+)', lines[j], re.IGNORECASE)

                            if next_z:
                                z_val = float(next_z.group(1))
                                if initial_z_depth is None:
                                    initial_z_depth = z_val
                                if max_z_depth is None or z_val > max_z_depth:
                                    max_z_depth = z_val

                            # Stop if we see another X value (next operation)
                            if next_x:
                                break

                        if max_z_depth and max_z_depth > 0.3:
                            # Check if this X reaches full drill depth
                            reaches_full_depth = False
                            if drill_depth and max_z_depth >= drill_depth * 0.95:
                                reaches_full_depth = True
                            
                            # SPECIAL CASES for shelf patterns:
                            # 1. Thin hub (CB and OB within 5mm): Shelf in OP1 to preserve hub material
                            # 2. Hub inside CB (OB < CB): Hub is smaller than CB, shelf supports it
                            # 3. CB=Counterbore in title: (X IS CB) marker refers to CB, not counterbore
                            is_special_case = False
                            is_hub_inside_cb = False  # Hub OB < CB case
                            if result.center_bore and result.hub_diameter:
                                cb_ob_diff = abs(result.hub_diameter - result.center_bore)
                                if cb_ob_diff <= 5.0:  # Thin hub
                                    is_special_case = True
                                elif result.hub_diameter < result.center_bore:  # Hub inside CB
                                    is_special_case = True
                                    is_hub_inside_cb = True
                            elif result.center_bore and result.counter_bore_diameter:
                                if abs(result.counter_bore_diameter - result.center_bore) < 1.0:  # CB = Counterbore
                                    is_special_case = True

                            # For hub-inside-CB: Check for chamfer pattern (initial Z around -0.15)
                            # The end-of-chamfer X is the CB
                            # Pattern: X3.063 Z-0.15 (chamfer end) then Z-2.28 (shelf depth)
                            is_chamfer_end = False
                            if is_hub_inside_cb and initial_z_depth:
                                if 0.1 <= initial_z_depth <= 0.2:  # Chamfer depth range
                                    is_chamfer_end = True

                            # Rule for CB detection:
                            # 1. SPECIAL CASE + (X IS CB): Trust marker even at partial depth
                            # 2. NORMAL + (X IS CB): Only valid if reaches full drill depth
                            # 3. SPECIAL CASE (thin hub) + no marker: CB is LARGEST X at partial depth (shelf)
                            # 4. NO MARKER: X must reach full drill depth to be CB candidate

                            if has_cb_marker:
                                if is_special_case or reaches_full_depth:
                                    cb_candidates = [x_val]  # Definitive CB
                                    cb_found = True  # Stop collecting more candidates
                                # Else: marker at partial depth on normal part = counterbore, skip
                            elif is_chamfer_end:
                                # Hub-inside-CB case: end of chamfer X is the CB
                                # This happens at Z ~0.15 (chamfer depth)
                                cb_candidates = [x_val]  # End of chamfer = CB
                                cb_found = True  # Stop collecting more candidates
                            elif is_special_case and not cb_found:
                                # For thin-hub parts without marker, collect candidates at partial depth
                                # The CB is the largest X at the shelf depth (not full depth)
                                if not reaches_full_depth:
                                    # This is at partial depth = shelf = CB for thin hub
                                    cb_candidates.append(x_val)
                                # Also collect full depth values for comparison
                                elif reaches_full_depth:
                                    # Full depth is initial bore, but keep it as fallback
                                    if not cb_candidates:  # Only add if no partial depth found
                                        cb_candidates.append(x_val)
                            elif reaches_full_depth and not cb_found:
                                cb_candidates.append(x_val)
                            # If doesn't reach full depth and no marker, skip

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
                        # OD is typically 3.0-14.0 inches (filter out small X values which are CB/OB)
                        # Extended to 14.0 to include 13" rounds
                        if 3.0 < x_val < 14.0:
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

                # ENHANCED: Look for "(X IS OB)" keyword comment
                has_ob_marker = '(X IS OB)' in line_upper or 'X IS OB' in line

                if x_match and result.spacer_type == 'hub_centric':
                    x_val = float(x_match.group(1))
                    z_val = float(z_match.group(1)) if z_match else None

                    # If line has "(X IS OB)" marker, prioritize this value
                    if has_ob_marker:
                        ob_candidates.append((x_val, z_val, i, True, False))  # True = has marker, False = has_following_z (N/A for marked)

                    # OB (Hub D) is typically 2.2-4.0 inches (filter out OD facing operations > 4.0)
                    # Progressive facing cuts down to the OB, then retracts to smaller X (CB)
                    # Exclude values too large (OD facing) and too small (CB)
                    elif 2.2 < x_val < 4.0:
                        # Check if next line is a Z movement (indicates X is OB)
                        # Pattern: X3.168 (line i) -> Z-0.05 (line i+1) confirms X3.168 is OB
                        has_following_z = False
                        if i + 1 < len(lines):
                            next_line = lines[i+1].strip()
                            # Check if next line has Z movement without X (pure Z move)
                            if re.search(r'Z\s*-?\s*([\d.]+)', next_line, re.IGNORECASE) and not re.search(r'X\s*([\d.]+)', next_line, re.IGNORECASE):
                                next_z_match = re.search(r'Z\s*-?\s*([\d.]+)', next_line, re.IGNORECASE)
                                if next_z_match:
                                    next_z_val = float(next_z_match.group(1))
                                    # If Z is within hub height range (0.05" to 2.0"), this confirms X is OB
                                    if 0.05 <= next_z_val <= 2.0:
                                        has_following_z = True

                        # Store X with its Z depth, line index, and following_z flag for detection
                        ob_candidates.append((x_val, z_val, i, False, has_following_z))  # Added has_following_z flag

                    # Also collect CB candidates from OP2 chamfer area (for hub-centric parts)
                    # CB chamfer is at shallow Z (< 0.15) and smaller than OB
                    # Use title spec to filter: CB should be close to title CB, not title OB
                    # IMPORTANT: Only do this if we have a title CB to compare against
                    # Otherwise OP2 chamfer values will incorrectly be selected as CB
                    if z_val and z_val < 0.15:  # Shallow Z = chamfer area
                        if 2.0 < x_val < 3.2:  # CB range
                            # Only add if we have title CB to compare and it's closer to CB than OB
                            if result.center_bore:  # Have title CB to compare
                                title_cb_inches = result.center_bore / 25.4
                                title_ob_inches = result.hub_diameter / 25.4 if result.hub_diameter else 999
                                # Distance from title CB vs distance from title OB
                                dist_to_cb = abs(x_val - title_cb_inches)
                                dist_to_ob = abs(x_val - title_ob_inches)
                                # Only add if closer to CB spec than OB spec
                                if dist_to_cb < dist_to_ob:
                                    cb_candidates.append(x_val)
                            # If no title CB, don't add OP2 values - rely on OP1 full depth extraction

        # Select CB: largest from candidates (final bore diameter after all passes)
        # The finishing bore pass is typically larger than roughing passes
        if cb_candidates:
            result.cb_from_gcode = max(cb_candidates) * 25.4  # Convert to mm

        # Set step depth for STEP programs
        # Step depth is the Z after chamfer creates CB, before moving inward
        if step_depth_candidate and result.spacer_type == 'step':
            result.counter_bore_depth = step_depth_candidate

        # Select OB: Enhanced detection with multiple strategies
        # Strategy 1: "(X IS OB)" keyword marker (highest priority)
        # Strategy 2: X value followed by Z movement (new pattern: X3.168 -> Z-0.05)
        # Strategy 3: X value after chamfer, before moving to positive Z
        # Strategy 4: Chamfer pattern detection
        if ob_candidates:
            # First, check if any candidate has the "(X IS OB)" marker
            marked_ob = [x for x, z, idx, has_marker, has_z in ob_candidates if has_marker]
            if marked_ob:
                result.ob_from_gcode = marked_ob[0] * 25.4  # Use first marked value, convert to mm
            else:
                # Strategy 2: X followed by Z movement (highest confidence for unmarked)
                # Pattern: X3.168 (OB position) -> Z-0.05 (hub height creation)
                ob_with_following_z = [x for x, z, idx, has_marker, has_z in ob_candidates if has_z]
                if ob_with_following_z:
                    # Use the largest X with following Z (typically the final OB after all passes)
                    result.ob_from_gcode = max(ob_with_following_z) * 25.4  # Convert to mm
                else:
                    # Strategy 3: Look for X value after chamfer and before moving to positive Z
                    # Pattern from O10040:
                    # Line 78: G01 X10.17 Z-0.05 F0.008 (chamfer at OD)
                    # Lines 109-137: Progressive facing at negative Z (Z-0.1 to Z-1.55)
                    # Line 138: G01 X6.688 F0.013 (X IS OB) <- OB at deepest Z
                    # Line 139: Z-0.05  <- Move to shallow Z (before positive)
                    # Line 140: X6.588 Z0.  <- Move to Z0 (positive)

                    ob_after_chamfer = []
                    for j, (x_val, z_val, line_idx, has_marker, has_z) in enumerate(ob_candidates):
                        if z_val is None:
                            continue

                        # Look at next 2 lines to see if Z moves toward positive (less negative)
                        # Z-1.55 -> Z-0.05 -> Z0.0 indicates we found OB before retraction
                        if j < len(ob_candidates) - 2:
                            _, next1_z, _, _, _ = ob_candidates[j+1]
                            _, next2_z, _, _, _ = ob_candidates[j+2] if j < len(ob_candidates) - 2 else (None, None, None, None, None)

                            # Check if Z is moving from deep (negative) toward shallow/positive
                            if next1_z and next1_z < z_val:  # Next Z is shallower (less negative)
                                # And if there's a second move that goes even shallower or to positive
                                if next2_z and next2_z < next1_z:
                                    ob_after_chamfer.append((x_val, z_val))

                    if ob_after_chamfer:
                        # Use the X value with the deepest Z (most negative) before retraction
                        deepest_ob = max(ob_after_chamfer, key=lambda pair: pair[1])
                        result.ob_from_gcode = deepest_ob[0] * 25.4  # Convert to mm
                    elif result.hub_diameter:  # Fallback to title spec matching
                        title_ob_inches = result.hub_diameter / 25.4  # Convert title spec to inches

                        # Look for chamfer pattern: X value between two Z direction changes
                        ob_with_chamfer_pattern = []

                        for j, (x_val, z_val, line_idx, has_marker, has_z) in enumerate(ob_candidates):
                            if z_val is None:
                                continue

                            # Look at previous and next movements to detect chamfer pattern
                            has_chamfer_before = False
                            has_chamfer_after = False

                            # Check previous lines for chamfer (larger X, Z movement)
                            if j > 0:
                                prev_x, prev_z, _, _, _ = ob_candidates[j-1]
                                if prev_x and prev_x > x_val + 0.1:  # X decreased (faced inward)
                                    has_chamfer_before = True

                            # Check next lines for Z going up (shallower) = chamfer to CB
                            if j < len(ob_candidates) - 1:
                                next_x, next_z, _, _, _ = ob_candidates[j+1]
                                if next_z and next_z < z_val:  # Z went up (shallower depth)
                                    has_chamfer_after = True

                            # If between chamfers, this is likely the OB
                            if has_chamfer_before and has_chamfer_after:
                                ob_with_chamfer_pattern.append(x_val)

                            # Also check if this X is very close to title spec (within 0.05")
                            if abs(x_val - title_ob_inches) < 0.05:
                                ob_with_chamfer_pattern.append(x_val)

                        # Select OB from chamfer pattern candidates, or use closest to title
                        if ob_with_chamfer_pattern:
                            closest_x = min(ob_with_chamfer_pattern, key=lambda x: abs(x - title_ob_inches))
                            result.ob_from_gcode = closest_x * 25.4  # Convert to mm
                        else:
                            # Fallback: find X closest to title spec from all candidates
                            all_x_values = [x for x, z, idx, marker, has_z in ob_candidates]
                            closest_x = min(all_x_values, key=lambda x: abs(x - title_ob_inches))
                            result.ob_from_gcode = closest_x * 25.4
                    else:
                        # No title OB available, use largest value > CB
                        all_x_values = [x for x, z, idx, marker, has_z in ob_candidates]
                        if cb_candidates:
                            cb_inches = max(cb_candidates)
                            valid_ob = [x for x in all_x_values if x > cb_inches + 0.15]
                            if valid_ob:
                                result.ob_from_gcode = max(valid_ob) * 25.4
                            else:
                                result.ob_from_gcode = max(all_x_values) * 25.4
                        else:
                            result.ob_from_gcode = max(all_x_values) * 25.4

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
                # Validate it's reasonable (0.20" to 3.50" for larger parts like 13" rounds)
                if 0.2 <= calculated_hub_height <= 3.5:
                    # IMPORTANT: Only override if title didn't have hub height at all
                    # Do NOT override if title has a valid hub height (even if it's 0.50)
                    if not result.hub_height:
                        result.hub_height = round(calculated_hub_height, 2)

        # Multi-method thickness calculation (fallback if not in title)
        if not result.thickness:
            # Method 1: From P-codes (work offset indicates total height) - ALWAYS try this first
            thickness_from_pcode = self._calculate_thickness_from_pcode(result.pcodes_found, result.spacer_type, result.lathe, result.hub_height)
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

        # OD fallback - round to standard size
        if not result.outer_diameter and result.od_from_gcode:
            result.outer_diameter = self._round_to_standard_od(result.od_from_gcode)

        # Also round title-extracted OD to standard size
        if result.outer_diameter:
            result.outer_diameter = self._round_to_standard_od(result.outer_diameter)

        # CB fallback
        if not result.center_bore and result.cb_from_gcode:
            result.center_bore = result.cb_from_gcode

        # OB/Hub Diameter fallback (hub-centric only)
        if result.spacer_type == 'hub_centric' and not result.hub_diameter and result.ob_from_gcode:
            result.hub_diameter = result.ob_from_gcode

    def _calculate_thickness_from_pcode(self, pcodes: List[int], spacer_type: str, lathe: Optional[str], hub_height: Optional[float] = None) -> Optional[float]:
        """
        Calculate thickness from P-codes (work offsets) using lathe-specific P-code tables

        P-code indicates TOTAL part thickness/height for ALL part types.
        For hub-centric: thickness = total_height - hub_height

        Lathe-specific P-code tables:
        - L1: Legacy mapping (P7=17MM, P17=1.25", etc.)
        - L2/L3: New mapping (P5=1.00", P7=1.25", 0.25" increments)
        """
        if not pcodes:
            return None

        # Get the correct P-code table based on lathe
        if lathe == 'L1':
            pcode_map = self._get_pcode_table_l1()
        elif lathe in ('L2', 'L3', 'L2/L3'):
            pcode_map = self._get_pcode_table_l2_l3()
        else:
            # Unknown lathe - try both tables
            pcode_map_l1 = self._get_pcode_table_l1()
            pcode_map_l2_l3 = self._get_pcode_table_l2_l3()

            # Check L1 first
            for pcode in pcodes:
                if pcode in pcode_map_l1:
                    total_height = pcode_map_l1[pcode]
                    if spacer_type == 'hub_centric':
                        hub_h = hub_height if hub_height else 0.50
                        return round(total_height - hub_h, 2)
                    else:
                        return total_height

            # Then try L2/L3
            for pcode in pcodes:
                if pcode in pcode_map_l2_l3:
                    total_height = pcode_map_l2_l3[pcode]
                    if spacer_type == 'hub_centric':
                        hub_h = hub_height if hub_height else 0.50
                        return round(total_height - hub_h, 2)
                    else:
                        return total_height

            return None

        # Find matching P-code in the selected table
        for pcode in pcodes:
            if pcode in pcode_map:
                total_height = pcode_map[pcode]

                # For hub-centric, subtract hub height to get thickness
                if spacer_type == 'hub_centric':
                    hub_h = hub_height if hub_height else 0.50
                    return round(total_height - hub_h, 2)
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

    def _assign_lathe(self, od: Optional[float]) -> Optional[str]:
        """
        Assign lathe based on outer diameter

        Lathe assignments:
        - L1: 5.75", 6.0", 6.25", 6.5"
        - L2: 7", 7.5", 8", 8.5", 9.5", 10.25", 10.5", 13"
        - L3: 7", 7.5", 8", 8.5" (overlaps with L2)

        For overlapping sizes, return 'L2/L3'
        """
        if od is None:
            return None

        # Round OD to nearest common size (to handle small variations)
        od_rounded = round(od * 4) / 4  # Round to nearest 0.25"

        # L1 sizes (exclusive)
        l1_sizes = {5.75, 6.0, 6.25, 6.5}

        # L2 sizes
        l2_sizes = {7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0}

        # L3 sizes (overlap with L2)
        l3_sizes = {7.0, 7.5, 8.0, 8.5}

        # Check for exact match or close match (within 0.01")
        tolerance = 0.01

        # Check L1 (exclusive)
        for size in l1_sizes:
            if abs(od - size) < tolerance:
                return 'L1'

        # Check for L2/L3 overlap
        for size in l3_sizes:
            if abs(od - size) < tolerance:
                return 'L2/L3'  # Both lathes can handle this size

        # Check L2 (non-overlap)
        for size in l2_sizes:
            if abs(od - size) < tolerance:
                return 'L2'

        # Unknown size
        return None

    def _get_pcode_table_l1(self) -> Dict[int, float]:
        """
        L1 P-code table (for 5.75", 6.0", 6.25", 6.5" rounds)
        Current/legacy P-code mapping
        """
        return self.PCODE_TABLE_L1

    def _get_pcode_table_l2_l3(self) -> Dict[int, float]:
        """
        L2/L3 P-code table (for 7", 7.5", 8", 8.5", 9.5", 10.25", 10.5", 13" rounds)
        New P-code mapping: 1.00" = P5/P6, increments by 0.25"
        """
        return self.PCODE_TABLE_L2_L3

    def _extract_pcodes(self, lines: List[str]) -> List[int]:
        """
        Extract work offset P-codes from G-code

        P-codes for work offsets are used with G54.1 (extended work coordinates)
        Format: G54.1 P## where ## is the offset number

        Excludes P values from:
        - G04 P## (dwell commands - P is time in seconds/milliseconds)
        - Other non-work-offset contexts
        """
        pcodes = set()
        for line in lines:
            line_upper = line.upper().strip()

            # Skip dwell commands - P is time, not work offset
            if 'G04' in line_upper or 'G4' in line_upper:
                continue

            # Look for G54.1 P## pattern (extended work offsets)
            # This is the standard way to use P-codes as work offsets
            g54_match = re.search(r'G54\.1\s*P(\d+)', line, re.IGNORECASE)
            if g54_match:
                pcodes.add(int(g54_match.group(1)))
                continue

            # Also check for standalone P## that looks like a work offset call
            # Work offset P-codes are typically 1-99 range
            # Skip if line contains other P uses (like subroutine calls)
            if 'M98' in line_upper:  # M98 P## is subroutine call, not work offset
                continue

            # Look for P## at start of line or after space (common work offset usage)
            p_match = re.search(r'(?:^|\s)P(\d{1,2})(?:\s|$)', line, re.IGNORECASE)
            if p_match:
                pcode = int(p_match.group(1))
                # Work offsets are typically in specific ranges (1-99)
                if 1 <= pcode <= 99:
                    pcodes.add(pcode)

        return sorted(pcodes)

    def _extract_drill_depth(self, lines: List[str]) -> Optional[float]:
        """
        Extract drill depth from G81/G83 commands or G01 center drilling

        For thick parts (>4.00" total), drilling is split into two operations:
        - OP1: Max drill depth Z-4.15" (machine limitation)
        - OP2: Remaining depth (total - 4.15")

        Example: 3.0" thick + 1.25" hub = 4.25" total
        - OP1: Z-4.15
        - OP2: Z-0.25 (includes 0.15" clearance, so 4.15 + 0.10 = 4.25")

        This function detects both operations and sums them.

        Also detects G01 drilling pattern in OP2 (used for shallow depths):
        - T101 (DRILL)
        - G00 X0 (center position)
        - G01 Z-0.5 (feed to depth)
        """
        drill_depths = []
        in_op2 = False
        drill_tool_active = False

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Detect OP2 section
            if 'OP2' in line_upper or '(OP2)' in line_upper:
                in_op2 = True

            # Track if DRILL tool is active
            if 'DRILL' in line_upper and ('T1' in line_upper or 'T2' in line_upper):
                drill_tool_active = True
            elif line_upper.strip().startswith('T') and 'DRILL' not in line_upper:
                # Different tool activated, DRILL no longer active
                drill_tool_active = False

            stripped = line.strip()

            # Standard drill cycles (G81/G83)
            if stripped.startswith(('G81', 'G83')):
                z_match = re.search(r'Z\s*-\s*([\d.]+)', stripped, re.IGNORECASE)
                if z_match:
                    depth = float(z_match.group(1))
                    drill_depths.append((depth, in_op2))

            # G01 drilling (common in OP2 for shallow depths)
            # Pattern: DRILL tool + X0 (center) + G01 Z-depth
            elif in_op2 and drill_tool_active and stripped.startswith('G01'):
                # Check if at center (X0 or no X movement)
                x_match = re.search(r'X\s*([\d.]+)', stripped, re.IGNORECASE)
                z_match = re.search(r'Z\s*-\s*([\d.]+)', stripped, re.IGNORECASE)

                if z_match:
                    # If no X or X is 0, this is center drilling
                    if not x_match or (x_match and abs(float(x_match.group(1))) < 0.1):
                        depth = float(z_match.group(1))
                        # Only add if it's a reasonable drill depth (not a tiny facing move)
                        if depth >= 0.15:
                            drill_depths.append((depth, in_op2))

        if not drill_depths:
            return None

        # If we have multiple drill operations, check for two-operation pattern
        if len(drill_depths) >= 2:
            # Look for OP1 drill close to 4.15" and OP2 drill
            op1_drills = [d for d, is_op2 in drill_depths if not is_op2]
            op2_drills = [d for d, is_op2 in drill_depths if is_op2]

            # Check if OP1 has a drill near 4.15" (within 0.05" tolerance)
            large_op1_drills = [d for d in op1_drills if 4.1 <= d <= 4.2]

            if large_op1_drills and op2_drills:
                # Two-operation drilling detected
                op1_depth = max(large_op1_drills)  # Usually 4.15"
                op2_depth = max(op2_drills)  # Remaining depth

                # Total depth = OP1 + OP2 (direct sum)
                # The clearance (0.15") is accounted for separately in thickness calculation
                # Examples:
                #   o10038: 4.15 + 0.25 = 4.40" (3.0" thick + 1.25" hub + 0.15" clearance)
                #   o10045: 4.15 + 0.50 = 4.65" (3.0" thick + 1.5" hub + 0.15" clearance)
                total_depth = op1_depth + op2_depth

                return total_depth

        # Single operation drilling - return deepest drill
        return max(d for d, _ in drill_depths)

    def _detect_hub_from_gcode(self, result: GCodeParseResult, lines: List[str]):
        """
        Detect hub-centric parts from G-code even without "HC" in title

        Logic:
        1. If already classified as hub_centric (has "HC" in title) → skip
        2. Check if title has CB/OB where CB < OB (indicates potential hub)
        3. Look for OP2 facing operations that create a raised hub
        4. If hub detected in OP2 → reclassify as hub_centric
        5. If no hub but has CB/OB → could be step piece

        Hub pattern in OP2:
        - Progressive facing: Z-0.25, Z-0.5, Z-0.75, ... Z-2.0
        - Large X values (> 4.0") indicate facing the outer diameter
        - Deep Z values (0.5" to 3.5") indicate hub height
        """
        # Skip if already hub_centric
        if result.spacer_type == 'hub_centric':
            return

        # Skip if no CB/OB to check
        if not result.center_bore or not result.hub_diameter:
            return

        # Check if CB < OB (potential for hub)
        cb_mm = result.center_bore
        ob_mm = result.hub_diameter

        if cb_mm >= ob_mm:
            # CB >= OB means no hub (standard spacer or step)
            return

        # Look for OP2 facing operations
        in_op2 = False
        facing_z_values = []
        last_x_value = None  # Track modal X position

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Detect OP2 section
            if 'OP2' in line_upper or '(OP2)' in line_upper:
                in_op2 = True

            if in_op2:
                stripped = line.strip()

                # Track X movements for modal programming
                x_match = re.search(r'X\s*([\d.]+)', stripped, re.IGNORECASE)
                if x_match:
                    last_x_value = float(x_match.group(1))

                # Look for G01 facing moves
                if stripped.startswith('G01'):
                    z_match = re.search(r'Z\s*-\s*([\d.]+)', stripped, re.IGNORECASE)

                    if z_match:
                        z_val = float(z_match.group(1))

                        # Check if Z is in hub range
                        if 0.2 <= z_val <= 3.5:
                            # Pattern 1: X and Z on same line
                            if x_match:
                                x_val = float(x_match.group(1))
                                if x_val > 4.0:
                                    facing_z_values.append(z_val)
                            # Pattern 2: Z on this line, X on next line (modal programming)
                            # Check next line for X movement to small value (hub/center)
                            elif i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                next_x_match = re.search(r'^X\s*([\d.]+)', next_line, re.IGNORECASE)
                                if next_x_match:
                                    next_x_val = float(next_x_match.group(1))
                                    # If next X is small (< 10"), this is facing to hub diameter
                                    # The Z-depth before moving to small X indicates hub height
                                    if next_x_val < 10.0:
                                        facing_z_values.append(z_val)
                            # Pattern 3: Progressive Z using last X position
                            elif last_x_value and last_x_value > 4.0:
                                facing_z_values.append(z_val)

        # If we found significant facing operations in OP2, it's hub-centric
        if facing_z_values:
            # Need at least 3 progressive facing moves to confirm hub
            if len(facing_z_values) >= 3:
                max_hub_height = max(facing_z_values)

                # Validate hub height is reasonable
                if 0.3 <= max_hub_height <= 3.5:
                    # Reclassify as hub_centric
                    result.spacer_type = 'hub_centric'
                    result.detection_method = 'GCODE'
                    result.detection_confidence = 'MEDIUM'

                    # Set hub height from OP2 facing
                    if not result.hub_height or result.hub_height == 0.50:
                        result.hub_height = round(max_hub_height, 2)

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
        file_prog_match = re.search(r'[oO](\d{4,})', filename)
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
            # Lower bound: title_cb - 0.25mm (critical threshold)
            # Upper bound: title_cb + 0.4mm (critical threshold)
            diff = gcode_cb - title_cb

            if diff < -0.25:
                # CRITICAL: CB way too small - RED
                result.validation_issues.append(
                    f'CB TOO SMALL: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif diff > 0.4:
                # CRITICAL: CB way too large - RED
                result.validation_issues.append(
                    f'CB TOO LARGE: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif abs(diff) > 0.2:
                # BORE WARNING: At tolerance limit - ORANGE
                result.bore_warnings.append(
                    f'CB at tolerance limit: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm)'
                )

        # OB Validation: Title is SPEC, G-code should be within tolerance
        # Acceptable range: (title_ob - 0.2mm) to title_ob
        if result.hub_diameter and result.ob_from_gcode:
            title_ob = result.hub_diameter  # SPECIFICATION
            gcode_ob = result.ob_from_gcode  # IMPLEMENTATION

            # Check if G-code is within acceptable range
            # Lower bound: title_ob - 0.4mm (critical threshold)
            # Upper bound: title_ob + 0.25mm (critical threshold)
            diff = gcode_ob - title_ob

            if diff < -0.4:
                # CRITICAL: OB way too small - RED
                result.validation_issues.append(
                    f'OB TOO SMALL: Spec={title_ob:.1f}mm, G-code={gcode_ob:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif diff > 0.25:
                # CRITICAL: OB way too large - RED
                result.validation_issues.append(
                    f'OB TOO LARGE: Spec={title_ob:.1f}mm, G-code={gcode_ob:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif abs(diff) > 0.2:
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
            # Hub-Centric: thickness = drill_depth - hub_height - 0.15" clearance
            # 2PC with hub: title shows body thickness, but drill includes 0.25" hub
            #               so thickness = drill_depth - 0.40" (0.25" hub + 0.15" clearance)
            if result.spacer_type == 'hub_centric':
                # Use actual hub height from title/G-code (not fixed 0.50")
                hub_h = result.hub_height if result.hub_height else 0.50
                calculated_thickness = result.drill_depth - hub_h - 0.15
            elif result.spacer_type in ('2PC LUG', '2PC STUD', '2PC UNSURE'):
                # 2PC parts: check if it has a hub
                # If has hub, title shows body thickness, drill includes 0.25" hub
                # If no hub (step only), use standard calculation
                title_upper = result.title.upper() if result.title else ''
                # Check for hub indicators: "HC" in title, or hub_height was extracted
                has_hub = 'HC' in title_upper or result.hub_height is not None
                if has_hub:
                    # Title shows body thickness, actual full thickness = body + 0.25" hub
                    calculated_thickness = result.drill_depth - 0.40  # 0.25" hub + 0.15" clearance
                else:
                    # 2PC without hub (step type) - standard calculation
                    calculated_thickness = result.drill_depth - 0.15
            else:
                calculated_thickness = result.drill_depth - 0.15

            # Tolerance: ±0.01" is acceptable, flag at ±0.02"
            # For two-operation drilling (>4.2" total), allow extra tolerance since OP2
            # intentionally drills deeper to ensure punch-through
            diff = calculated_thickness - title_thickness

            # Two-operation drilling gets ±0.30" tolerance (OP2 drills extra to punch through)
            # OP2 must drill at least 0.10" to breach, but often drills 0.25-0.50" to ensure complete separation
            # Standard drilling gets ±0.12" tolerance (drills may go slightly deeper for safety)
            is_two_operation = result.drill_depth and result.drill_depth > 4.2
            critical_tolerance = 0.30 if is_two_operation else 0.12
            warning_tolerance = 0.25 if is_two_operation else 0.08

            if abs(diff) > critical_tolerance:  # Beyond tolerance is critical
                # Check if this might be a mislabeled title
                # If P-codes also indicate the calculated thickness, title is wrong
                pcode_agrees_with_drill = False
                if result.pcodes_found and result.lathe:
                    # Get P-code table
                    if result.lathe == 'L1':
                        pcode_map = self._get_pcode_table_l1()
                    elif result.lathe in ('L2', 'L3', 'L2/L3'):
                        pcode_map = self._get_pcode_table_l2_l3()
                    else:
                        pcode_map = {}

                    # Check what thickness the P-codes indicate
                    for pcode in result.pcodes_found:
                        if pcode in pcode_map:
                            pcode_total_height = pcode_map[pcode]
                            if result.spacer_type == 'hub_centric':
                                # Use actual hub height from title/G-code, not fixed 0.50"
                                hub_h = result.hub_height if result.hub_height else 0.50
                                pcode_thickness = pcode_total_height - hub_h
                            else:
                                pcode_thickness = pcode_total_height

                            # If P-code thickness matches calculated (within 0.02")
                            if abs(pcode_thickness - calculated_thickness) < 0.02:
                                pcode_agrees_with_drill = True
                                break

                if pcode_agrees_with_drill:
                    # Title is mislabeled - both P-code and drill agree
                    result.dimensional_issues.append(
                        f'TITLE MISLABELED: Title says {title_thickness:.2f}" but drill depth ({calculated_thickness:.2f}") and P-codes both indicate different thickness - TITLE NEEDS CORRECTION'
                    )
                else:
                    # CRITICAL: Thickness way off - RED
                    result.validation_issues.append(
                        f'THICKNESS ERROR: Spec={title_thickness:.2f}", Calculated from drill={calculated_thickness:.2f}" ({diff:+.3f}") - CRITICAL ERROR'
                    )
            elif abs(diff) > warning_tolerance:  # Warning zone
                # DIMENSIONAL: Thickness mismatch - PURPLE
                result.dimensional_issues.append(
                    f'Thickness mismatch: Spec={title_thickness:.2f}", Calculated={calculated_thickness:.2f}" ({diff:+.3f}")'
                )
            # ±0.01" or less is acceptable - no warning

        # OD Validation: Title is SPEC, G-code should match within tolerance
        # Tolerance varies by size:
        # - Small parts (< 10"): ±0.1" tolerance
        # - Large parts (≥ 10"): ±0.25" tolerance (e.g., 13" rounds can be X12.8 in G-code)
        if result.outer_diameter and result.od_from_gcode:
            title_od = result.outer_diameter  # SPECIFICATION
            gcode_od = result.od_from_gcode  # IMPLEMENTATION

            diff = gcode_od - title_od

            # Set tolerance based on part size
            if title_od >= 10.0:
                error_tolerance = 0.25  # Large parts: ±0.25"
                warning_tolerance = 0.15  # Warning zone: ±0.15-0.25"
            else:
                error_tolerance = 0.1  # Small parts: ±0.1"
                warning_tolerance = 0.05  # Warning zone: ±0.05-0.1"

            if abs(diff) > error_tolerance:
                result.validation_issues.append(
                    f'OD MISMATCH: Spec={title_od:.2f}", G-code={gcode_od:.2f}" ({diff:+.3f}") - G-CODE ERROR'
                )
            elif abs(diff) > warning_tolerance:
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
            # Calculate expected P-codes for the thickness using correct lathe table
            if result.thickness and result.lathe:
                # For hub-centric, P-code = thickness + 0.50"
                if result.spacer_type == 'hub_centric':
                    total_height = result.thickness + 0.50
                else:
                    total_height = result.thickness

                # Get correct P-code table based on lathe
                if result.lathe == 'L1':
                    pcode_map = self._get_pcode_table_l1()
                elif result.lathe in ('L2', 'L3', 'L2/L3'):
                    pcode_map = self._get_pcode_table_l2_l3()
                else:
                    pcode_map = {}  # Unknown lathe, skip validation

                # Find expected P-code (odd number, OP1)
                expected_pcode = None
                for pcode, height in pcode_map.items():
                    if pcode % 2 == 1 and abs(height - total_height) < 0.01:  # Match within 0.01", odd P-codes only
                        expected_pcode = pcode
                        break

                if expected_pcode and pcode_map:
                    # Check if any found P-code matches expected pair
                    if expected_pcode not in result.pcodes_found and (expected_pcode + 1) not in result.pcodes_found:
                        actual_pcodes = [p for p in result.pcodes_found if p in pcode_map]
                        if actual_pcodes:
                            # DIMENSIONAL: P-code doesn't match thickness - PURPLE
                            # Build descriptive message showing what each P-code means
                            actual_thickness_strs = []
                            for p in actual_pcodes:
                                if p in pcode_map:
                                    actual_thick = pcode_map[p]
                                    # Format thickness nicely
                                    if actual_thick < 0.5:
                                        # Show in MM
                                        actual_thickness_strs.append(f'P{p}={actual_thick*25.4:.0f}MM')
                                    else:
                                        # Show in inches
                                        actual_thickness_strs.append(f'P{p}={actual_thick:.2f}"')

                            actual_desc = ', '.join(actual_thickness_strs) if actual_thickness_strs else str(actual_pcodes)

                            # Check if P-code and drill depth AGREE with each other but disagree with title
                            # If so, the title is likely mislabeled
                            pcode_thickness = None
                            for p in actual_pcodes:
                                if p in pcode_map:
                                    if result.spacer_type == 'hub_centric':
                                        pcode_thickness = pcode_map[p] - 0.50
                                    else:
                                        pcode_thickness = pcode_map[p]
                                    break

                            drill_thickness = None
                            if result.drill_depth:
                                if result.spacer_type == 'hub_centric':
                                    drill_thickness = result.drill_depth - 0.65
                                else:
                                    drill_thickness = result.drill_depth - 0.15

                            # Check if P-code and drill depth agree (within 0.02")
                            if pcode_thickness and drill_thickness:
                                if abs(pcode_thickness - drill_thickness) < 0.02:
                                    # Both agree! Title is mislabeled
                                    result.dimensional_issues.append(
                                        f'TITLE MISLABELED: Title says {result.thickness}" but P-code ({actual_desc}) and drill depth ({drill_thickness:.2f}") both indicate {pcode_thickness:.2f}" - TITLE NEEDS CORRECTION'
                                    )
                                else:
                                    # P-code and drill depth disagree with each other
                                    result.dimensional_issues.append(
                                        f'P-CODE MISMATCH: Title thickness {result.thickness}" requires P{expected_pcode}/P{expected_pcode+1} ({result.lathe}), but G-code uses {actual_desc}'
                                    )
                            else:
                                result.dimensional_issues.append(
                                    f'P-CODE MISMATCH: Title thickness {result.thickness}" requires P{expected_pcode}/P{expected_pcode+1} ({result.lathe}), but G-code uses {actual_desc}'
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
        if result.lathe:
            print(f"Lathe: {result.lathe}")
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
