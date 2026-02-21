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
from validators.standards_validator import StandardsValidator, ValidationResult
from validators.crash_prevention_validator import CrashPreventionValidator
from validators.od_turndown_validator import ODTurnDownValidator
from validators.hub_breakthrough_validator import HubBreakThroughValidator
from validators.turning_tool_depth_validator import TurningToolDepthValidator
from validators.bore_chamfer_safety_validator import BoreChamferSafetyValidator
from validators.counterbore_depth_validator import CounterboreDepthValidator
from validators.g154_presence_validator import G154PresenceValidator
from validators.steel_ring_recess_validator import SteelRingRecessValidator
from validators.twopc_ring_size_validator import TwoPCRingSizeValidator


# ── Known CB equivalence pairs ────────────────────────────────────────────────
# Some bore sizes are specified one way in the title but programmed a few
# thousandths larger in the G-code as an accepted machining convention.
# Each entry: (title_spec_mm, gcode_actual_mm, match_tolerance_mm)
#
# 116.7mm / 116.9mm (X4.602):
#   Title says 116.7mm but the bore is routinely programmed at X4.602"
#   (4.602 × 25.4 = 116.891mm).  The 0.19mm difference is intentional —
#   it ensures a clean chamfer lead-in while staying within hub tolerance.
_CB_EQUIVALENCES = [
    (116.7, 116.8908, 0.05),   # X4.594 title → X4.602 gcode convention
]


def _resolve_effective_cb(title_cb_mm, gcode_cb_mm):
    """Return the best CB reference for validators.

    For known equivalent pairs the actual G-code bore is more precise
    than the rounded title value, so prefer it for comparisons.
    Returns title_cb_mm unchanged when no equivalence applies.
    """
    if title_cb_mm is None or gcode_cb_mm is None:
        return title_cb_mm
    for spec, actual, tol in _CB_EQUIVALENCES:
        if abs(title_cb_mm - spec) < tol and abs(gcode_cb_mm - actual) < tol:
            return actual
    return title_cb_mm


def _is_known_cb_equivalent(title_cb_mm, gcode_cb_mm):
    """Return True when (title_cb_mm, gcode_cb_mm) is a known acceptable pair."""
    if title_cb_mm is None or gcode_cb_mm is None:
        return False
    for spec, actual, tol in _CB_EQUIVALENCES:
        if abs(title_cb_mm - spec) < tol and abs(gcode_cb_mm - actual) < tol:
            return True
    return False


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
    bore_type: Optional[str]  # 'centerbore', 'counterbore', 'unknown' (depth-based classification)

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
    best_practice_suggestions: List[str]  # Suggestions (not warnings - don't affect PASS status)

    # Tool Analysis
    tools_used: List[str]                 # List of tool numbers used (e.g., ["T101", "T121", "T202"])
    tool_sequence: List[str]              # Ordered list of tools in sequence

    # G53 Tool Home Position Validation (L1-L3 lathes only)
    # Z position depends on thickness (minimum safe values):
    #   <= 2.50" thick: Z-13 or higher (Z-10, Z-8, etc. are safe)
    #   2.75" - 3.75" thick: Z-11 or higher
    #   4.00" - 5.00" thick: Z-9 or higher
    #   Z-16 is ALWAYS CRITICAL (dangerous - too far out)
    # SAFETY: Higher Z (less negative) = tool further from part = SAFER
    #   So Z-10 is safe for Z-13 parts, Z-8 is safe for all parts
    #   Only warn when Z is LOWER than expected (tool too close)
    tool_home_positions: List[Dict]       # List of {line_num, line, z_value, expected_z, status}
    tool_home_status: str                 # 'PASS', 'WARNING', 'CRITICAL', 'UNKNOWN'
    tool_home_issues: List[str]           # List of tool home position issues

    # Feasibility Validation (Standards-based validation)
    feasibility_status: str               # 'FEASIBLE', 'NOT_FEASIBLE', 'UNKNOWN'
    feasibility_issues: List[str]         # Critical issues preventing feasibility
    feasibility_warnings: List[str]       # Warnings about feasibility concerns

    # Crash Prevention Validation (G-code pattern safety)
    crash_issues: List[str]               # Critical crash risks (G00 to negative Z, etc.)
    crash_warnings: List[str]             # Crash warnings (jaw clearance, etc.)

    # 2PC Part Field Usage (reuses existing fields):
    # - hub_height: 2PC hub height (0.25" typical for STUD, 0.50" for special)
    # - hub_diameter: OB diameter of the 2PC hub (mm)
    # - counter_bore_depth: 2PC step/shelf depth (0.30-0.32" typical for LUG)
    # - counter_bore_diameter: 2PC step/shelf diameter (mm)
    # Detection: If BOTH hub_height AND counter_bore_depth are set for 2PC → part has BOTH hub AND step

    # DISABLED - Tool/Safety validation temporarily disabled (needs tuning)
    # Uncomment these fields to re-enable tool/safety validation later
    # tool_validation_status: str           # 'PASS', 'WARNING', 'ERROR'
    # tool_validation_issues: List[str]     # List of tool-related issues
    # safety_blocks_status: str             # 'PASS', 'WARNING', 'MISSING'
    # safety_blocks_issues: List[str]       # List of missing safety blocks


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
        self.od_validator = ODTurnDownValidator()

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
                bore_type=None,
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
                detection_notes=[],
                best_practice_suggestions=[],
                tools_used=[],
                tool_sequence=[],
                tool_home_positions=[],
                tool_home_status='UNKNOWN',
                tool_home_issues=[],
                feasibility_status='UNKNOWN',
                feasibility_issues=[],
                feasibility_warnings=[],
                crash_issues=[],
                crash_warnings=[]
                # DISABLED - Tool/Safety validation fields removed
                # tool_validation_status='PASS',
                # tool_validation_issues=[],
                # safety_blocks_status='PASS',
                # safety_blocks_issues=[]
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

            # 3a. Refine 2PC UNSURE classification using G-code comments
            # 50% of LUG files have "(LUG PLATE)" comment, 80% of STUD files have "(STUD PLATE)" comment
            if result.spacer_type == '2PC UNSURE' and lines:
                # Scan first 20 lines for LUG/STUD PLATE comments
                for line in lines[:20]:
                    line_upper = line.upper()

                    if 'LUG PLATE' in line_upper or '(LUG' in line_upper and 'PLATE' in line_upper:
                        result.spacer_type = '2PC LUG'
                        result.detection_method = 'GCODE_COMMENT'
                        result.detection_confidence = 'HIGH'
                        result.detection_notes.append('LUG detected from G-code comment')
                        break
                    elif 'STUD PLATE' in line_upper or '(STUD' in line_upper and 'PLATE' in line_upper:
                        result.spacer_type = '2PC STUD'
                        result.detection_method = 'GCODE_COMMENT'
                        result.detection_confidence = 'HIGH'
                        result.detection_notes.append('STUD detected from G-code comment')
                        break

            # 4. Extract dimensions from title
            self._extract_dimensions_from_title(result)

            # 5. Extract dimensions from G-code
            self._extract_dimensions_from_gcode(result, lines)

            # 5b. Auto-correct title dimensions using G-code (when title parsing failed or is inaccurate)
            self._auto_correct_dimensions(result)

            # 5b. Advanced 2PC classification and dimension extraction using G-code analysis
            # Run for ALL 2PC types to extract hub/step dimensions
            if '2PC' in result.spacer_type and lines:
                twopc_analysis = self._analyze_2pc_gcode(lines, result.thickness, result.hub_height)

                # Update type if UNSURE
                if result.spacer_type == '2PC UNSURE' and twopc_analysis['type']:
                    result.spacer_type = twopc_analysis['type']
                    result.detection_method = twopc_analysis['method']
                    result.detection_confidence = twopc_analysis['confidence']
                    if twopc_analysis['note']:
                        result.detection_notes.append(twopc_analysis['note'])

                # Populate 2PC dimensions into existing fields:
                # - hub_height: 2PC hub (0.25" or 0.50")
                # - hub_diameter: OB of the hub (mm) - ALWAYS use G-code value (title is often wrong)
                # - counter_bore_depth: step depth (0.30-0.32")
                # - counter_bore_diameter: step/shelf diameter (mm)
                if twopc_analysis['hub_height'] and not result.hub_height:
                    result.hub_height = twopc_analysis['hub_height']
                # For 2PC parts, ALWAYS use G-code hub_diameter (title parsing often gets it wrong)
                if twopc_analysis['hub_diameter']:
                    result.hub_diameter = twopc_analysis['hub_diameter']
                if twopc_analysis['step_depth'] and not result.counter_bore_depth:
                    result.counter_bore_depth = twopc_analysis['step_depth']
                if twopc_analysis['step_diameter'] and not result.counter_bore_diameter:
                    result.counter_bore_diameter = twopc_analysis['step_diameter']

                # Add note if part has BOTH hub AND step (special labeling)
                if result.hub_height and result.counter_bore_depth:
                    result.detection_notes.append(
                        f'2PC with BOTH: {result.hub_height:.2f}" hub + {result.counter_bore_depth:.2f}" step'
                    )

            # 5c. Use thickness heuristic for remaining 2PC UNSURE files
            # LUG parts are typically thicker (>=1.0"), STUD parts are thinner (<1.0")
            if result.spacer_type == '2PC UNSURE' and result.thickness:
                if result.thickness >= 1.0:
                    # Thicker parts typically LUG (receiver)
                    result.spacer_type = '2PC LUG'
                    result.detection_method = 'THICKNESS_HEURISTIC'
                    result.detection_confidence = 'LOW'
                    result.detection_notes.append(f'LUG inferred from thickness {result.thickness}" (>=1.0")')
                else:
                    # Thinner parts typically STUD (insert)
                    result.spacer_type = '2PC STUD'
                    result.detection_method = 'THICKNESS_HEURISTIC'
                    result.detection_confidence = 'LOW'
                    result.detection_notes.append(f'STUD inferred from thickness {result.thickness}" (<1.0")')

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
            # EXCEPT 2PC parts (their dimensions refer to mating parts, not actual bores)
            # IMPORTANT: Only reclassify to hub_centric if there's EVIDENCE of a hub (OB cut in OP2)
            # Don't reclassify based on drill depth alone - standard parts may have extra clearance
            if result.drill_depth and result.thickness:
                # Calculate potential hub from drill depth
                potential_hub = result.drill_depth - result.thickness - 0.15

                # If potential hub is reasonable (0.3" to 3.5"), this might be hub-centric
                # BUT only reclassify if we have actual evidence of OB (hub diameter) from G-code
                if 0.3 <= potential_hub <= 3.5:
                    # If not already hub_centric, check if we should reclassify
                    # IMPORTANT: Don't reclassify 2PC parts - they have hubs but title dimensions are for mating parts
                    # IMPORTANT: Don't reclassify based on drill depth alone - need OB evidence
                    if result.spacer_type != 'hub_centric' and '2PC' not in result.spacer_type:
                        # Only reclassify if we found OB from G-code (evidence of actual hub)
                        if result.ob_from_gcode:
                            result.spacer_type = 'hub_centric'
                            result.detection_method = 'DRILL_DEPTH'
                            result.detection_confidence = 'MEDIUM'
                            result.hub_height = round(potential_hub, 2)
                    # If already hub_centric but hub_height is default 0.50, update it
                    elif result.spacer_type == 'hub_centric' and (not result.hub_height or result.hub_height == 0.50):
                        result.hub_height = round(potential_hub, 2)

            # 8c. Enhanced hub detection from roughing pattern (OP2 oscillating X with stepped Z)
            # Run AFTER spacer type classification is complete
            # Try this if OB wasn't extracted or hub_height is default (0.50")
            if result.spacer_type == 'hub_centric' or '2PC' in result.spacer_type:
                try:
                    od_estimate = result.outer_diameter if result.outer_diameter else None
                    hub_roughing = self._detect_hub_from_roughing_pattern(lines, od_estimate)

                    if hub_roughing['detected']:
                        # Use roughing-detected hub diameter if OB not extracted
                        if not result.ob_from_gcode:
                            result.ob_from_gcode = hub_roughing['hub_diameter'] * 25.4  # Convert to mm
                            result.hub_diameter = hub_roughing['hub_diameter'] * 25.4
                            result.detection_notes.append(
                                f"OB from hub roughing pattern: {hub_roughing['hub_diameter']:.3f}\" ({hub_roughing['confidence']} confidence)"
                            )

                        # Use roughing-detected hub height if not set or default
                        if not result.hub_height or result.hub_height == 0.50:
                            result.hub_height = hub_roughing['hub_height']
                            result.detection_notes.append(
                                f"Hub height from roughing pattern: {hub_roughing['hub_height']:.2f}\" ({hub_roughing['note']})"
                            )

                        # Check for aggressive Z step warning
                        if hub_roughing.get('warning'):
                            result.validation_warnings.append(
                                f"Hub roughing: {hub_roughing['warning']}"
                            )
                except Exception as e:
                    # Silently continue if hub roughing detection fails
                    pass

            # 9. Extract tool usage (for reference only)
            self._extract_tools(result, lines)

            # 10. Validate G53 tool home positions (L1-L3 lathes)
            self._validate_tool_home_positions(result, lines)

            # 10a. Validate program feasibility against standards
            self._validate_feasibility(result)

            # 10b. Validate crash prevention patterns (CRITICAL safety checks)
            self._validate_crash_prevention(result, lines)

            # DISABLED - Tool/Safety validation temporarily disabled (needs tuning)
            # Uncomment to re-enable tool and safety validation
            # self._validate_tools(result)
            # self._validate_safety_blocks(result, lines)

            # 11. Validate consistency
            self._validate_consistency(result)

            # 11a. Haas lathe-specific G-code validations
            self._validate_haas_gcode_patterns(result, lines)

            # 11b. OD turn-down validation (common practice checks)
            self._validate_od_turndown(result, lines)

            # 11c. Hub breakthrough validation (hub-centric parts only)
            self._validate_hub_breakthrough(result, lines)

            # 11d. Turning tool depth validation (production standards)
            self._validate_turning_depth(result, lines)

            # 11e. Bore chamfer safety validation (hub crash prevention)
            self._validate_bore_chamfer_safety(result, lines)

            # 11f. Counterbore depth validation (STEP parts only)
            self._validate_counterbore_depth(result, lines)

            # 11g. G154 / work offset presence (every operation must declare WCS)
            self._validate_g154_presence(result, lines)

            # 11h. Steel ring recess diameter (interference-fit tolerance check)
            self._validate_steel_ring_recess(result)

            # 11i. 2PC mating hub ring size (CB → expected ring OD lookup)
            self._validate_2pc_ring_size(result)

            # 12. Get file timestamps
            try:
                from datetime import datetime
                stat = os.stat(file_path)
                result.date_created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                result.last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except:
                pass

            # 13. Classify bore type (centerbore vs counterbore)
            self._classify_bore_type(result)

            # 14. Steel ring round size validation
            # CRITICAL: Steel rings are ONLY used for 8", 8.5", and 9.5" round sizes
            # Other round sizes with "STEEL" keyword or MM ID notation are standard spacers
            if result.spacer_type == 'steel_ring' and result.outer_diameter:
                # Define allowed steel ring round sizes (with tolerance)
                allowed_steel_ring_sizes = [
                    (7.75, 8.25),   # 8.0" nominal
                    (8.25, 8.75),   # 8.5" nominal
                    (9.25, 9.75)    # 9.5" nominal
                ]

                # Check if OD falls within allowed ranges
                is_valid_steel_ring_size = any(
                    low <= result.outer_diameter <= high
                    for low, high in allowed_steel_ring_sizes
                )

                if not is_valid_steel_ring_size:
                    # Reclassify as standard spacer
                    result.detection_notes.append(
                        f"Reclassified from steel_ring to standard: "
                        f"Round size {result.outer_diameter:.2f}\" not in allowed steel ring sizes (8\", 8.5\", 9.5\")"
                    )
                    result.spacer_type = 'standard'
                    result.detection_confidence = 'HIGH'

            # 15. Steel ring counterbore-based detection
            # A program WITHOUT STEEL keyword but with correct size + counterbore may still be steel ring
            # Check if: 8"/8.5"/9.5" + counterbore on Side 2 + CB matches common steel ring values
            if result.spacer_type == 'standard' and result.outer_diameter and result.counter_bore_diameter:
                # Define allowed steel ring round sizes (with tolerance)
                allowed_steel_ring_sizes = [
                    (7.75, 8.25),   # 8.0" nominal
                    (8.25, 8.75),   # 8.5" nominal
                    (9.25, 9.75)    # 9.5" nominal
                ]

                # Common steel ring counterbore diameters (±2mm tolerance)
                # From production data: ~127mm, ~133mm, ~152mm, ~165mm
                common_steel_cb_values = [
                    (125.0, 129.0),  # ~127mm range (126.7-126.9mm)
                    (131.0, 135.0),  # ~133mm range (133.0-133.2mm)
                    (150.0, 154.0),  # ~152mm range (151.5-152.3mm)
                    (163.0, 167.0)   # ~165mm range (164.8-164.9mm)
                ]

                # Check if OD is in allowed steel ring sizes
                is_valid_steel_ring_size = any(
                    low <= result.outer_diameter <= high
                    for low, high in allowed_steel_ring_sizes
                )

                # Check if CB diameter matches common steel ring values
                cb_matches_steel_ring = any(
                    low <= result.counter_bore_diameter <= high
                    for low, high in common_steel_cb_values
                )

                if is_valid_steel_ring_size and cb_matches_steel_ring:
                    # Reclassify as steel ring based on counterbore evidence
                    result.detection_notes.append(
                        f"Classified as steel_ring based on counterbore evidence: "
                        f"{result.outer_diameter:.2f}\" size + {result.counter_bore_diameter:.1f}mm CB "
                        f"(matches common steel ring CB values)"
                    )
                    result.spacer_type = 'steel_ring'
                    result.detection_confidence = 'MEDIUM'

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
            for line in lines:  # Scan ALL lines for comments (not just first 100)
                # G-code comments are in parentheses or after semicolon
                # Example: (2PC STUD) or ; 2PC LUG
                # Also: (LUG PLATE) or (STUD PLATE) or just (LUG) or (STUD)
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

        # STEP pattern with dash: "90MM-74MM" or "90-74 MM" (counterbore-CB format)
        # Dash is used instead of slash in some titles
        # Pattern: number-number MM (with optional spaces)
        if re.search(r'\d+\.?\d*\s*MM?\s*-\s*\d+\.?\d*\s*MM?', combined_upper, re.IGNORECASE):
            found_in_title = re.search(r'\d+\.?\d*\s*MM?\s*-\s*\d+\.?\d*\s*MM?', title_upper, re.IGNORECASE) is not None
            confidence = 'MEDIUM' if found_in_title else 'LOW'
            return 'step', confidence

        # Steel Ring indicators
        # Patterns: "STEEL S-1", "HCS-1", "STEEL HCS-2", "STEEL HCS-1"
        if re.search(r'STEEL\s+S-\d|HCS-\d|STEEL\s+HCS-\d', combined_upper):
            found_in_title = re.search(r'STEEL\s+S-\d|HCS-\d|STEEL\s+HCS-\d', title_upper) is not None
            confidence = 'HIGH' if found_in_title else 'MEDIUM'
            return 'steel_ring', confidence

        # Steel Ring Assembly patterns: "MM ID" or "MM CB" + "STEEL" keyword
        # Examples: "8IN 116.7MM 1.5 STEEL HCS-1", "9.5IN 142MM 2.0 STL S-1", "8IN 4.56 STEEL HCS-2"
        # The MM ID/CB value is the steel ring's inner diameter, NOT the aluminum spacer's CB
        # Often combined with 2PC (steel ring + spacer assembly)
        # IMPORTANT: Regular spacers commonly use "MM ID" for center bore notation (like "125MM ID")
        # STEEL keyword (or STL/HCS variations) is REQUIRED - cannot rely on MM value alone
        mm_id_match = re.search(r'(\d+\.?\d*)\s*MM\s+(ID|CB)', combined_upper)
        if mm_id_match:
            # Check for STEEL keyword variations: STEEL, STL, STL-1, HCS-1, HCS-2, etc.
            has_steel_keyword = bool(re.search(r'\bSTEEL\b|\bSTL\b|\bSTL-\d\b|\bHCS-\d\b', combined_upper))

            # Steel ring ONLY if has "STEEL" keyword (or STL variation)
            # Many standard spacers use MM ID notation (e.g., "8IN DIA 125 MM ID 2.0")
            # These are NOT steel rings, just center bore specified in MM
            if has_steel_keyword:
                mm_value = float(mm_id_match.group(1))
                found_in_title = re.search(r'\d+\.?\d*\s*MM\s+(ID|CB)', title_upper) is not None
                confidence = 'HIGH' if found_in_title else 'MEDIUM'
                return 'steel_ring', confidence

        # 2-piece indicators (check before hub_centric - 2PC takes priority)
        # 2PC = 2-piece spacer, comes in LUG or STUD variants
        # Many 2PC parts have "HC" in title (e.g., ".75 HC 2PC STUD") - the HC refers to hub-centric INTERFACE
        # The title dimensions (XX/YY) often refer to the MATING part, not this part's actual bores
        # IMPORTANT: 2PC classification takes priority over HC keyword
        if '2PC' in combined_upper or '2 PC' in combined_upper:
            found_in_title = '2PC' in title_upper or '2 PC' in title_upper

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

        # Standalone LUG/STUD detection (even without "2PC" keyword)
        # Some files have "LUG PLATE", "STUD PLATE", or just "LUG"/"STUD" in comments
        # Look for these patterns anywhere in the file
        lug_patterns = ['LUG PLATE', 'LUG', 'LUGS']
        stud_patterns = ['STUD PLATE', 'STUD', 'STUDS']

        # Check for LUG patterns
        for pattern in lug_patterns:
            if pattern in combined_upper:
                # Make sure it's not part of another word (e.g., "PLUG")
                if re.search(r'\b' + pattern + r'\b', combined_upper):
                    found_in_title = pattern in title_upper
                    # If found in title, high confidence; if in comments, medium
                    confidence = 'HIGH' if found_in_title else 'MEDIUM'
                    return '2PC LUG', confidence

        # Check for STUD patterns
        for pattern in stud_patterns:
            if pattern in combined_upper:
                # Make sure it's not part of another word
                if re.search(r'\b' + pattern + r'\b', combined_upper):
                    found_in_title = pattern in title_upper
                    # If found in title, high confidence; if in comments, medium
                    confidence = 'HIGH' if found_in_title else 'MEDIUM'
                    return '2PC STUD', confidence

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
                        in_turn_op2 = False
                    else:
                        in_bore_op2 = True
                        # T121 in OP2 is for chamfering, not OB turning
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
        # CRITICAL: First number before DIA or at start of title is ALWAYS OD in inches (even without "IN")
        od_patterns = [
            r'^(\d+\.?\d*)\s+DIA',              # Match "6.00 DIA" - first value before DIA is ALWAYS OD in inches
            r'(\d+\.?\d*)\s*IN[\$]?\s+DIA',     # Match "5.75IN$ DIA" or "5.75IN DIA"
            r'(\d+\.?\d*)\s*IN\s+(?!DIA)\d',    # Match "5.75 IN 60MM" (IN followed by number, not DIA)
            r'(\d+\.?\d*)\s*IN\s+ROUND',
            r'(\d+\.?\d*)\s*"\s*(?:DIA|ROUND)',
            r'^(\d+\.?\d*)\s+\d+\.?\d*[/\d\.]*(?:IN|MM)',  # OD at start before IN or MM pattern (e.g., "13.0 170.1/220MM")
            r'^(\d+\.?\d*)\s+\d+\.?\d*CB',      # Match "13.0 220CB" - OD followed by CB value (no IN/DIA needed)
            r'^(\d+\.?\d*)\s+\d+\s*MM',         # Match "8 125 MM" - OD followed by MM value
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

        # First check for mixed fractions like "1-1/8" (1 and 1/8 = 1.125")
        mixed_fraction_match = re.search(r'(\d+)-(\d+)/(\d+)(?:\s*"|\s+|$)', title)
        if mixed_fraction_match:
            whole = int(mixed_fraction_match.group(1))
            numerator = int(mixed_fraction_match.group(2))
            denominator = int(mixed_fraction_match.group(3))
            thickness_inches = whole + (numerator / denominator)

            if 0.25 <= thickness_inches <= 6.0:
                result.thickness = thickness_inches
                result.thickness_display = f"{whole}-{numerator}/{denominator}"

        # Then check for simple fractions like "7/8"
        # EXCLUDE fractions followed by B/C or MM (those are bore dimensions, not thickness)
        if not result.thickness:
            fraction_match = re.search(r'(\d+)/(\d+)(?!\s*(?:B/C|MM|ID))(?:\s*"|\s+|$)', title)
            if fraction_match:
                numerator = int(fraction_match.group(1))
                denominator = int(fraction_match.group(2))
                thickness_inches = numerator / denominator

                # Validate reasonable thickness range (up to 6" for thick parts)
                if 0.25 <= thickness_inches <= 6.0:
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
                # IMPORTANT: "XMM DEEP" patterns - extract thickness AFTER "DEEP", not the MM value
                (r'DEEP\s+(\d*\.?\d+)\s*$', 'IN', False),    # "6MM DEEP 1.0" - thickness at end after DEEP
                (r'DEEP\s+(\d*\.?\d+)\s+', 'IN', False),     # "6MM DEEP 1.25 XX" - thickness after DEEP
                (r'(\d*\.?\d+)--HC', 'IN', True),            # "2.0--HC", "1.5--HC" - number directly followed by --HC
                (r'(\d*\.?\d+)\s*MM\s+--HC', 'MM', True),    # "15MM --HC" - MM then --HC
                (r'(\d*\.?\d+)\s*IN\s+THK\s+--HC', 'IN', True), # "1.00IN THK --HCH" - IN THK --HC pattern
                (r'(\d*\.?\d+)\s*IN\s+--HC', 'IN', True),    # "1.0IN --HC" - IN then --HC
                (r'(\d*\.?\d+)\s*IN\s+HC', 'IN', True),      # "1.0 IN HC" - IN then HC
                (r'(\d*\.?\d+)\s*MM\s+HC', 'MM', True),      # "1.50MM HC" - MM before HC
                (r'(\d*\.?\d+)\s+---HC', 'IN', True),        # "2.0 ---HCXX" - three dashes
                (r'(\d+)\s*MM\s+---HC', 'MM', True),         # "10MM ---HCXX" - MM thickness with triple dash HC
                (r'\s+(\d+)\s*MM\s*-HC', 'MM', True),        # "10MM -HC" - MM thickness with dash before HC
                (r'(\d*\.?\d+)\s+--HC', 'IN', True),         # "4.0 --HCXX", "1.0 --HC" - thickness before -- and HC
                (r'(\d*\.?\d+)\s+-HC', 'IN', True),          # "3.25 -HC" - space dash HC
                (r'(\d*\.?\d+)-HC', 'IN', True),             # "3.0-HC" - thickness with dash before HC
                (r'(\d+)\s*mmhc', 'MM', True),               # "17mmhc" - mmhc together
                (r'(\d*\.?\d+)HC\b', 'IN', True),            # "1.25HC" - thickness directly before HC (no space)
                (r'\s+(\d+)\s*HC(?:\s|$)', 'MM', True),      # "15HC" or " 15 HC" - MM thickness with hub (no "MM" in text)
                (r'\s+\.(\d+)\s*MM\s+HC', 'DECIMAL_MM', True),  # ".75MM HC" - decimal MM without leading zero (actually inches)
                (r'(\d+\.?\d*)\s*MM\s+HC', 'MM', True),      # "15MM HC" - MM thickness with hub (explicit MM)
                (r'\s+([5-9]\.?\d*)\s+HC', 'MM', True),      # " 6.4 HC" - small number (5-9) before HC is likely mm thickness
                (r'(\d*\.?\d+)\s+HC', 'IN', True),           # "1.75 HC" - decimal inches before HC (no MM/IN/THK keyword)
                (r'\s+\.(\d+)\s*MM\s+THK', 'DECIMAL_MM', False),  # ".75MM THK" - decimal MM without leading zero (actually inches)
                (r'(\d+\.?\d*)\s*MM\s+THK', 'MM', False),    # "10MM THK" - MM thickness standard
                (r'\s+\.(\d+)\s*MM\s*$', 'DECIMAL_MM', False),   # ".75MM" at end - decimal without leading zero (actually inches)
                (r'\s+(\d+\.?\d*)\s*MM\s*$', 'MM', False),   # "10MM" at end
                (r'ID\s+(\d*\.?\d+)\s+THK', 'IN', False),    # "ID 5.00 THK" - thickness after ID before THK (must be before ID MM patterns)
                (r'ID\s+\.(\d+)\s*MM\s+', 'DECIMAL_MM', False),  # "ID .75MM" - decimal without leading zero (actually inches)
                (r'ID\s+(\d+\.?\d*)\s*MM\s+', 'MM', False),  # "ID 10MM SPACER"
                (r'ID\s+(\d*\.?\d+)\s+2PC', 'IN', False),    # "ID 1.25 2PC" - thickness before 2PC
                (r'ID\s+(\d*\.?\d+)(?:\s+|$)', 'IN', False), # "ID 1.5" - inches
                (r'(\d*\.?\d+)\s*--2PC', 'IN', False),        # "1.25--2PC" or "1.00  --2PC" - thickness with -- separator before 2PC
                (r'(\d*\.?\d+)\s+-2PC', 'IN', False),        # ".75 -2PC" - thickness with single dash before 2PC
                (r'(\d*\.?\d+)\s+2PC', 'IN', False),         # "1.75 2PC" - thickness before 2PC
                (r'2PC\s+(\d*\.?\d+)\s+LUG', 'IN', False),   # "2PC 1.25 LUG" - thickness between 2PC and LUG
                (r'\.(\d+)\s+IS\s+2PC', 'DECIMAL', False),   # ".75 IS 2PC" - decimal thickness before IS 2PC
                (r'\.(\d+)\s+LUG', 'DECIMAL', False),        # ".75 LUG" - decimal thickness before LUG
                (r'\.(\d+)IN\s+2PC', 'DECIMAL', False),      # ".6IN 2PC" - decimal with IN before 2PC
                (r'(\d*\.?\d+)HK\s+XX', 'IN', False),        # "1.0HK XX" - thickness with HK suffix before XX
                (r'(\d+)\.HC', 'IN', False),                 # "1.HC" - number with dot before HC (missing decimal)
                (r'\s(\d+\.?\d*)\s*MM\s+HC', 'MM', False),   # " 6.4 HC" after MM context - small mm value before HC
                (r'(\d*\.?\d+)\s+IN\s+THK', 'IN', False),    # "1.25IN THK" - inches with IN and THK
                (r'(\d*\.?\d+)\s+THK\s+XX', 'IN', False),    # "5.00 THK XX" - thickness before THK XX
                (r'(\d*\.?\d+)THK', 'IN', False),            # "1.00THK" - no space before THK
                (r'(\d*\.?\d+)\s+THK?(?:\s|$)', 'IN', False), # "0.75 THK" or "0.75 TH" - inches (TH abbreviation)
                (r'\.(\d+)\s+TH(?:\s|$)', 'DECIMAL', False), # ".75 TH" - decimal without leading digit
                (r'(\d+\.?\d*)\s+THK(?:\s|$)', 'IN', False), # "4.5 THK" - thickness before THK keyword
                (r'MM\s+(\d*\.?\d+)\s+XX', 'IN', False),     # "85MM 3.00 XX" - thickness between MM and XX
                (r'OD\s+(\d*\.?\d+)-?\s*XX', 'IN', False),   # "OD 2.25- XX" or "OD 2.5 XX" - thickness after OD before XX
                (r'(\d*\.?\d+)-\s*XX', 'IN', False),         # "2.25- XX" or "1.5- XX" - thickness with dash before XX
                (r'(\d*\.?\d+)\s+XX', 'IN', False),          # "2.5 XX" - thickness with space before XX
                (r'(\d*\.?\d+)XX', 'IN', False),             # "1.00XX" - thickness directly before XX (no space)
                (r'\.(\d+)HCXX', 'DECIMAL', True),           # ".75HCXX" - decimal before HCXX
                (r'(\d*\.?\d+)\s+STEP', 'IN', False),        # "2.25 STEP" - thickness before STEP keyword
                (r'(\d*\.?\d+)-\s*RTS', 'IN', False),        # "1.25- RTS" - thickness with dash before RTS
                (r'(\d+)\.\s+XX', 'IN', False),              # "2.  XX" or "1. XX" - number with trailing dot before XX
                (r'CB\s+(\d+)MM\s', 'MM', False),            # "220CB 22MM SPACER" - MM thickness after CB
                (r'CB\s+\.(\d+)\s', 'DECIMAL', False),       # "220CB .5 SPACER" - decimal thickness after CB
                (r'CB\s+(\d*\.?\d+)\s+SPACER', 'IN', False), # "220CB 1.0 SPACER" - thickness after CB
                (r'CB\s+(\d+)\.\s+\w', 'IN', False),         # "221CB 5. PRESSPLATE" - number with trailing dot after CB
                (r'B/C\s+(\d*\.?\d+)(?!\s*MM\s*DEEP)', 'IN', False),  # "B/C 1.50" but NOT "B/C 6MM DEEP"
                (r'MM\s+(\d*\.?\d+)\s+(?:THK|HC)', 'IN', False),  # "MM 1.50 THK"
                (r'/[\d.]+MM\s+(\d*\.?\d+)', 'IN', False),   # After slash pattern
                (r'(\d*\.?\d+)\s+(?:STEEL|STAINLESS|STL)', 'IN', False),  # "1.25 STEEL/STL" - thickness before material keywords (protects from S-X/HCS-X suffixes)
                (r'(\d*\.?\d+)\s*$', 'IN', False),           # End of line (last resort)
            ]

            for pattern, unit, is_hub_centric_mm in thick_patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    try:
                        thickness_val_str = match.group(1)

                        # Handle DECIMAL unit (e.g., ".75 TH" → 0.75)
                        if unit == 'DECIMAL':
                            thickness_val = float('0.' + thickness_val_str)
                        # Handle DECIMAL_MM unit (e.g., ".75MM" → 0.75 inches, NOT millimeters)
                        # When MM is written as ".75MM", it's actually inches (0.75"), not 75MM
                        elif unit == 'DECIMAL_MM':
                            thickness_val = float('0.' + thickness_val_str)
                        else:
                            thickness_val = float(thickness_val_str)

                        # Determine if this is MM or inches
                        # DECIMAL_MM is always inches (despite the MM in the title - it's a notation error)
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

                        # Validate thickness is in reasonable range (up to 6" for thick parts)
                        if 0.25 <= result.thickness <= 6.0:
                            break  # Found valid thickness
                        else:
                            # Reset if out of range
                            result.thickness = None
                            result.thickness_display = None
                    except:
                        pass

        # CB/OB pattern (XX/YY or XX-YY format) - more flexible matching
        cb_ob_patterns = [
            r'(\d+\.?\d*)\s*IN\s*/\s*(\d+\.?\d*)\s*MM',  # 8.7IN/220MM (inches/mm - for large rounds, first=hub_diameter in inches, second=OB in mm)
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

                # Check for special "IN/MM" pattern (e.g., "8.7IN/220MM")
                # This pattern indicates hub diameter in inches / OB in mm
                # Common in 13" rounds where hub diameter is specified in inches
                matched_pattern = cb_ob_match.group(0)
                first_has_in = 'IN' in matched_pattern.split('/')[0].upper() if '/' in matched_pattern else False
                second_has_mm = 'MM' in matched_pattern.split('/')[1].upper() if '/' in matched_pattern and len(matched_pattern.split('/')) > 1 else False

                if first_has_in and second_has_mm:
                    # Special case: "IN/MM" format (e.g., "6.25IN/220MM" or "8.7IN/220MM")
                    # Two possible interpretations:
                    # 1. "8.7IN/220MM" = OB in inches / OB in mm (same value, two units)
                    # 2. "6.25IN/220MM" = CB in inches / OB in mm (different values)
                    # Distinguish by checking if first_val (inches) ≈ second_val (mm) when converted
                    first_val_mm = first_val * 25.4

                    # SANITY CHECK: If converted value is > 500mm (~20"), it's likely a title typo
                    # Example: "125IN/220MM" should be "125MM/220MM" (CB=125mm, not 125 inches!)
                    if first_val_mm > 500.0:
                        # Treat first value as mm, not inches (title typo)
                        result.center_bore = first_val  # Use value as-is in mm
                        result.hub_diameter = second_val  # OB in mm
                    elif abs(first_val_mm - second_val) < 5.0:
                        # Values are close → same dimension in two units (OB/OB)
                        result.hub_diameter = first_val_mm  # Use converted inches value (more precise)
                        # CB will be determined from G-code
                    else:
                        # Values are different → CB/OB pattern
                        result.center_bore = first_val_mm  # CB in mm (converted from inches)
                        result.hub_diameter = second_val  # OB in mm
                else:
                    # Standard CB/OB patterns
                    first_has_mm = 'MM' in matched_pattern.split('/')[0].upper() if '/' in matched_pattern else False

                    if (result.outer_diameter and result.outer_diameter >= 10.0 and
                        first_val < 10 and not first_has_mm and second_has_mm):
                        # Check if first value is in inches (for large rounds like "6.25/220MM")
                        # Pattern: OD >= 10", first < 10, second has MM but first doesn't
                        # Example: "13.0 6.25/220MM" -> 6.25" CB / 220mm OB
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

                        # Check if "ID" is actually part of the CB/OB pattern (like "90/74 ID" or "90/74 B/C")
                        # vs just appearing elsewhere in title (like "65.1MM/72.56MM ID 1.0" where ID is description)
                        # If both values have "MM" explicitly (like "XXmm/YYmm"), it's a CB/OB format regardless of ID marker
                        matched_pattern_upper = matched_pattern.upper()
                        both_have_mm = matched_pattern_upper.count('MM') >= 2

                        # If "ID" marker present RIGHT AFTER the pattern (not "HC"), treat like STEP format: large/small
                        # This handles hub-centric with support shelf where first=shelf, second=CB
                        # BUT: If both values have MM (like "65.1MM/72.56MM"), always treat as CB/OB
                        if 'ID' in title_upper and 'HC' not in title_upper and not both_have_mm:
                            # Check if ID appears right after the pattern (within 5 chars)
                            # Pattern: "90/74 ID" or "90/74 B/C" → shelf/CB format
                            # NOT Pattern: "65.1MM/72.56MM ID 1.0" → CB/OB format (ID is elsewhere)
                            pattern_end_pos = title_upper.find(matched_pattern_upper) + len(matched_pattern_upper)
                            id_pos = title_upper.find('ID', pattern_end_pos)
                            id_is_adjacent = id_pos >= 0 and (id_pos - pattern_end_pos) < 10

                            if id_is_adjacent:
                                # ID is adjacent - need to determine format based on value order
                                # RULE: First value is ALWAYS the inner bore (CB), second is outer (shelf/counterbore)
                                # This is true for dash-separated patterns like "65.1-121 MM ID"
                                # The smaller value is the CB (inner), larger is the shelf/counterbore (outer)
                                if first_val < second_val:
                                    # Standard CB/Shelf format: first=CB (smaller), second=Shelf (larger)
                                    # Example: "65.1-121 MM ID" -> CB=65.1, Shelf=121
                                    result.center_bore = first_val
                                    result.counter_bore_diameter = second_val  # Store shelf as counterbore
                                else:
                                    # Reversed format: first=Shelf (larger), second=CB (smaller)
                                    # Example: "121-65.1 MM ID" -> Shelf=121, CB=65.1
                                    result.center_bore = second_val
                                    result.counter_bore_diameter = first_val
                            else:
                                # ID is elsewhere in title - treat as standard CB/OB
                                result.center_bore = first_val
                                result.hub_diameter = second_val  # OB = Hub OD
                        else:
                            # Check if "ID" marker is in title (but not HC) - could be HC part without keyword
                            # For MM/MM ID patterns like "70.3MM/66.9MM ID", need to determine CB vs OB
                            if 'ID' in title_upper and 'HC' not in title_upper:
                                # For hub-centric parts (unlabeled), CB is always smaller, OB is always larger
                                # Title may have OB/CB or CB/OB format - sort by size
                                # CB = inner bore (smaller), OB = outer bore of hub (larger)
                                if first_val > second_val:
                                    # First is larger = OB, second is smaller = CB
                                    # Example: "70.3MM/66.9MM ID" -> OB=70.3, CB=66.9
                                    result.center_bore = second_val   # CB (smaller)
                                    result.hub_diameter = first_val   # OB (larger)
                                else:
                                    # First is smaller = CB, second is larger = OB
                                    # Example: "66.9MM/70.3MM ID" -> CB=66.9, OB=70.3
                                    result.center_bore = first_val    # CB (smaller)
                                    result.hub_diameter = second_val  # OB (larger)
                            # For HC parts, check if first > second (indicates Shelf/OB format)
                            # Standard HC: CB/OB where CB < OB (e.g., 66.9/106mm)
                            # Shelf/OB HC: first > second (e.g., 108/82.5mm) where first=shelf, second=OB
                            elif first_val > second_val * 1.1:  # First is >10% larger = Shelf/OB format
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
            # Pattern handles typos like "78.3.MM" (extra dot before MM)
            cb_match = re.search(r'(\d+\.?\d*)\s*\.?\s*(?:MM|M)\s+(?:ID|CB|B/C)', title, re.IGNORECASE)
            if cb_match:
                try:
                    cb_val = float(cb_match.group(1))
                    # Validate CB is in reasonable range (38-250mm for typical wheel spacers)
                    # Values like 15mm are thickness, not CB!
                    if 38.0 <= cb_val <= 250.0:
                        result.center_bore = cb_val
                    # Else: value too small/large to be CB, leave it unset for G-code extraction
                except:
                    pass

            # Fallback: "DIA XXX MM" pattern without ID/CB marker (common in steel parts)
            # Example: "8IN DIA 125 MM STEEL" - 125 is the CB
            if not result.center_bore:
                cb_match2 = re.search(r'DIA\s+(\d+\.?\d*)\s*MM', title, re.IGNORECASE)
                if cb_match2:
                    try:
                        cb_val = float(cb_match2.group(1))
                        if 38.0 <= cb_val <= 250.0:
                            result.center_bore = cb_val
                    except:
                        pass

            # Fallback: "DIA XXX.X ID" pattern (no MM, just ID marker)
            # Example: "9.5IN DIA 154.2 ID .5" - 154.2 is the CB
            if not result.center_bore:
                cb_match3 = re.search(r'DIA\s+(\d+\.?\d*)\s+ID', title, re.IGNORECASE)
                if cb_match3:
                    try:
                        cb_val = float(cb_match3.group(1))
                        if 38.0 <= cb_val <= 250.0:
                            result.center_bore = cb_val
                    except:
                        pass

            # Fallback: "DIA X.XXIN" pattern (CB in inches after DIA)
            # Example: "4.75 DIA 1.58IN 1.375 THK" - 1.58IN is the CB (convert to mm)
            if not result.center_bore:
                cb_match4 = re.search(r'DIA\s+(\d+\.?\d*)IN', title, re.IGNORECASE)
                if cb_match4:
                    try:
                        cb_inches = float(cb_match4.group(1))
                        cb_val = cb_inches * 25.4  # Convert to mm
                        if 25.0 <= cb_val <= 250.0:  # Reasonable range in mm
                            result.center_bore = cb_val
                    except:
                        pass

        # Hub height extraction - works for ALL files with HC in title (hub-centric, 2PC, etc.)
        # Many 2PC files have HC dimensions (e.g., "1.75 HC 2PC") where HC indicates hub-centric interface
        # Extract HC dimensions EARLY so they're available regardless of spacer_type classification
        # Pattern 1: "number HC number" format where first=thickness, second=hub height
        # Example: "1.0 HC 1.5" means 1.0" thick + 1.5" hub height
        # Also handles trailing decimals: "2. HC 1.5" = 2.0" thick + 1.5" hub (WITHOUT digit after decimal)
        # Also handles leading decimals: ".75 HC 2.0" = 0.75" thick + 2.0" hub (WITHOUT digit before decimal)
        # Also handles no space: "1.0 HC.5" = 1.0" thick + 0.5" hub
        # Also handles dashes: "1.0 --HC 0.50", "1.0 -HC 0.50"
        # Regex uses alternation to handle ALL decimal formats: (\d+\.?\d*|\d*\.\d+) matches .75, 1., or 1.75
        # IMPORTANT: Use negative lookahead (?!PC) to avoid matching "2" from "2PC" as hub height
        if 'HC' in title.upper():
            dual_hc_match = re.search(r'(\d+\.?\d*|\d*\.\d+)\s*-*HC\s*(\d+\.?\d*|\d*\.\d+)(?!\s*PC)', title, re.IGNORECASE)
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
            # IMPORTANT: Use negative lookahead to avoid matching "2" from "2PC"
            if not result.hub_height:
                # Only match HC followed by a value (e.g., "HC 0.5", "HC.5", "--HC 0.5", "-HC 0.5")
                # But NOT "HC 2PC" (use negative lookahead to exclude "2" from "2PC")
                hub_match = re.search(r'-*HC\s*(\d+\.?\d*|\d*\.\d+)(?!\s*PC)', title, re.IGNORECASE)
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

    def _auto_correct_dimensions(self, result: GCodeParseResult):
        """
        Auto-correct title dimensions using G-code when title parsing failed.

        IMPORTANT: Only use G-code as fallback when title missing, NOT for correction.
        Differences >0.1mm between title and G-code often indicate CB/OB confusion in
        G-code extraction, not title parsing errors.

        Analysis showed:
        - 92.9% of programs have title CB within 0.5mm of G-code CB
        - When they differ significantly, it's often G-code extracting wrong bore
        - Example: Title "141.3/170MM" (CB/OB) but G-code finds 169.9mm for both
        """

        # 1. Center Bore - ONLY use G-code if title completely missing
        if result.cb_from_gcode and not result.center_bore:
            # Title parsing failed - use G-code as fallback
            result.center_bore = result.cb_from_gcode
            result.detection_notes.append(f'CB from G-code: {result.cb_from_gcode:.1f}mm (title missing)')

        # 2. Outer Bore / Hub Diameter - ONLY use G-code if title completely missing
        if result.ob_from_gcode and not result.hub_diameter:
            # Title parsing failed for hub-centric - use G-code as fallback
            result.hub_diameter = result.ob_from_gcode
            result.detection_notes.append(f'OB from G-code: {result.ob_from_gcode:.1f}mm (title missing)')

        # Note: We DON'T auto-correct existing title values because:
        # - Title is the specification (what should be made)
        # - G-code CB/OB extraction sometimes confuses which bore is which
        # - Differences >0.1mm suggest G-code extraction error, not title error
        # - Validation system will flag significant mismatches for review

    def _analyze_2pc_gcode(self, lines: List[str], thickness: Optional[float], hub_height: Optional[float]) -> dict:
        """
        Advanced 2PC LUG vs STUD classification using G-code analysis.
        Also extracts 2PC-specific dimensions (hub height, step depth, diameters).

        Rules (from user specification):
        STUD indicators:
        - Typically 1.00" in title (but 0.75" actual thickness)
        - Creates ~0.25" hub (0.75" thick + 0.25" hub ≈ 1.00" total)
        - Thickness ≤ 0.75"
        - Hub height ≈ 0.25" (with tolerance)
        - Special case: 0.5" hub with recess on opposite side

        LUG indicators:
        - Thickness ≥ 0.75" (typically 1.0" or greater)
        - If thickness > 0.75" with 0.25" hub → LUG (studs never exceed 0.75")
        - Creates shelf/recess in OP1: Z-0.30 to Z-0.32 depth
        - Receives the STUD insert

        Special 2PC with BOTH hub AND step:
        - Has 0.50" hub machined in OP2
        - Has step/shelf in OP1 at 0.30-0.55" depth
        - Usually labeled "2PC AND HUB" or has "(HUB IS .5 THK)" comment

        Returns:
            dict with keys: 'type', 'method', 'confidence', 'note',
                           'hub_height', 'hub_diameter', 'step_depth', 'step_diameter'
        """
        # print(f"DEBUG: _analyze_2pc_gcode called")
        result = {
            'type': None, 'method': None, 'confidence': None, 'note': '',
            'hub_height': None, 'hub_diameter': None,
            'step_depth': None, 'step_diameter': None
        }

        # Track state for OP1 vs OP2
        in_op2 = False
        in_bore_op1 = False
        in_turn_op2 = False  # Track if we're in a T303 turning operation in OP2

        # Collect Z depths and X values by operation
        op1_bore_depths = []  # (z_depth, x_diameter) tuples from OP1 boring
        op2_facing_depths = []  # (z_depth, x_diameter) tuples from OP2 facing

        # Check for explicit hub comment like "(HUB IS .5 THK)"
        explicit_hub_comment = None
        for line in lines[:50]:
            line_upper = line.upper()
            hub_match = re.search(r'\(HUB\s+IS\s+\.?(\d+\.?\d*)\s*(?:THK|THICK)?\)', line_upper)
            if hub_match:
                explicit_hub_comment = float(hub_match.group(1))
                if explicit_hub_comment < 1:  # Handle ".5" vs "0.5"
                    pass  # Already correct
                break

        # Scan G-code for patterns
        current_x = None
        current_z = None
        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Detect OP2 boundary
            if any(marker in line_upper for marker in ['OP2', 'OP 2', 'FLIP PART', 'FLIP', 'SIDE 2']):
                in_op2 = True
                in_bore_op1 = False

            # Track tool changes
            if 'T121' in line_upper or 'BORE' in line_upper:
                if not in_op2:
                    in_bore_op1 = True
                in_turn_op2 = False
            elif 'T303' in line_upper or 'TURN TOOL' in line_upper:
                in_bore_op1 = False
                if in_op2:
                    in_turn_op2 = True

            # Extract X and Z values
            x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
            # Match both positive and negative Z values to properly track tool position
            z_match = re.search(r'Z\s*(-?\s*[\d.]+)', line, re.IGNORECASE)

            # Update current X and Z values (they persist across lines)
            if x_match:
                current_x = float(x_match.group(1))

            if z_match:
                z_val = float(z_match.group(1).replace(' ', ''))
                # Only track negative Z (below the face) for depth tracking
                # Positive Z means tool moved back above the part
                if z_val < 0:
                    current_z = abs(z_val)
                else:
                    current_z = None  # Reset when moving back up

            # Capture (Z, X) pairs when we have both values
            if current_z and current_x:
                # OP1 boring - look for step depths (0.28-0.55" range, shallower than full bore)
                if in_bore_op1 and not in_op2:
                    if 0.28 <= current_z <= 0.55:
                        # Only add if not already in list
                        if (current_z, current_x) not in op1_bore_depths:
                            op1_bore_depths.append((current_z, current_x))

                # OP2 turning/facing - look for hub depths
                if in_op2 and in_turn_op2:
                    if 0.15 <= current_z <= 1.6:  # Hub range
                        # Only add if not already in list
                        if (current_z, current_x) not in op2_facing_depths:
                            op2_facing_depths.append((current_z, current_x))

        # Analyze OP1 for step detection (counter bore)
        # Step pattern: multiple bores at same shallow depth, then deeper bores at smaller X
        step_depth = None
        step_diameter = None
        if op1_bore_depths:
            # Filter out very large X values (> 5.0") which are likely facing operations
            step_ops = [(z, x) for z, x in op1_bore_depths if x < 5.0]

            if step_ops:
                # Find depths in the step range (0.28-0.55")
                step_range_ops = [(z, x) for z, x in step_ops if 0.28 <= z <= 0.55]

                if step_range_ops:
                    # Find the most common depth (the actual step depth)
                    depth_counts = {}
                    for z, x in step_range_ops:
                        rounded_z = round(z, 2)
                        if rounded_z not in depth_counts:
                            depth_counts[rounded_z] = []
                        depth_counts[rounded_z].append(x)

                    # Step is the depth with multiple passes
                    for depth, x_vals in sorted(depth_counts.items()):
                        if len(x_vals) >= 2:
                            step_depth = depth
                            # Use tight tolerance (0.02") to only get final pass, not rough cuts
                            # Similar to hub detection: exclude values significantly smaller than max
                            max_x = max(x_vals)
                            final_pass_vals = [x for x in x_vals if abs(x - max_x) < 0.02]
                            if final_pass_vals:
                                step_diameter = max(final_pass_vals) * 25.4  # Convert to mm
                            else:
                                step_diameter = max_x * 25.4
                            break

        # Analyze OP2 for hub detection
        # Hub pattern: progressive facing to final depth
        detected_hub_height = None
        hub_diameter = None
        if op2_facing_depths:
            # Filter out OD values (X > 5.0") - these are facing operations, not hub
            # Hub diameters are typically X < 5.0"
            hub_ops = [(z, x) for z, x in op2_facing_depths if x < 5.0]

            if hub_ops:
                max_depth = max(z for z, x in hub_ops)
                # Hub height is the maximum facing depth in OP2
                if 0.20 <= max_depth <= 1.6:
                    detected_hub_height = max_depth
                    # Hub diameter: Get X value AT the maximum hub depth (final pass)
                    # Use tight tolerance (0.02") to only get final pass, not rough cuts
                    # Example: X3.71 at Z-0.15 (rough), X3.703 at Z-0.22 (final) - we want 3.703
                    deep_ops = [(z, x) for z, x in hub_ops if abs(z - max_depth) < 0.02]
                    if deep_ops:
                        # Get the largest diameter at the deepest Z (final pass before cleanup)
                        hub_diameter = max(x for z, x in deep_ops) * 25.4  # Convert to mm

        # Use explicit comment if available
        if explicit_hub_comment:
            detected_hub_height = explicit_hub_comment

        # Populate result dimensions
        if detected_hub_height:
            result['hub_height'] = round(detected_hub_height, 2)
            # Snap to standard hub sizes: machining variance causes the final facing pass
            # to read slightly short (e.g. Z-0.22 instead of Z-0.25).
            h = result['hub_height']
            if 0.20 <= h <= 0.27:
                result['hub_height'] = 0.25
            elif 0.45 <= h < 0.50:
                result['hub_height'] = 0.50
        if hub_diameter:
            result['hub_diameter'] = round(hub_diameter, 1)
        if step_depth:
            result['step_depth'] = round(step_depth, 2)
        if step_diameter:
            result['step_diameter'] = round(step_diameter, 1)

        # Determine 2PC type based on patterns found
        has_step = step_depth is not None and 0.28 <= step_depth <= 0.35
        has_large_hub = detected_hub_height is not None and detected_hub_height >= 0.45
        has_small_hub = detected_hub_height is not None and 0.20 <= detected_hub_height <= 0.30

        # Special case: 2PC with BOTH hub AND step
        if has_step and has_large_hub:
            result['type'] = '2PC LUG'  # LUG with 0.50" hub is a special case
            result['method'] = 'GCODE_HUB_AND_STEP'
            result['confidence'] = 'HIGH'
            result['note'] = f'2PC with BOTH: {step_depth:.2f}" step AND {detected_hub_height:.2f}" hub'
            return result

        # Rule 1: Check for LUG shelf pattern (Z-0.30 to Z-0.32)
        if has_step:
            result['type'] = '2PC LUG'
            result['method'] = 'GCODE_SHELF_DEPTH'
            result['confidence'] = 'HIGH'
            result['note'] = f'LUG shelf detected at Z-{step_depth:.2f}" (0.30-0.32" range)'
            return result

        # Rule 2: Thickness > 0.75" with 0.25" hub = LUG (studs never exceed 0.75")
        if thickness and thickness > 0.75:
            if has_small_hub or (hub_height and 0.20 <= hub_height <= 0.30):
                result['type'] = '2PC LUG'
                result['method'] = 'THICKNESS_HUB_COMBO'
                result['confidence'] = 'HIGH'
                hub_h = detected_hub_height or hub_height
                result['note'] = f'LUG: thickness {thickness}" > 0.75" with {hub_h}" hub (studs max 0.75")'
                return result
            else:
                # Thickness > 0.75" alone is strong LUG indicator
                result['type'] = '2PC LUG'
                result['method'] = 'THICKNESS_ANALYSIS'
                result['confidence'] = 'MEDIUM'
                result['note'] = f'LUG: thickness {thickness}" > 0.75" (studs max 0.75")'
                return result

        # Rule 3: Thickness = 0.75" with 0.25" hub = STUD pattern
        if thickness and 0.70 <= thickness <= 0.80:  # Allow tolerance
            if has_small_hub or (hub_height and 0.20 <= hub_height <= 0.30):
                result['type'] = '2PC STUD'
                result['method'] = 'THICKNESS_HUB_COMBO'
                result['confidence'] = 'HIGH'
                hub_h = detected_hub_height or hub_height
                result['note'] = f'STUD: thickness {thickness}" ≈ 0.75" with {hub_h}" hub (typical pattern)'
                return result

        # Rule 4: Hub height detection alone
        if has_small_hub or (hub_height and 0.20 <= hub_height <= 0.30):
            result['type'] = '2PC STUD'
            result['method'] = 'HUB_HEIGHT_ANALYSIS'
            result['confidence'] = 'MEDIUM'
            hub_h = detected_hub_height or hub_height
            result['note'] = f'STUD: {hub_h}" hub (0.25" typical for STUD)'
            return result

        # No definitive pattern found
        return result

    def _detect_roughing_sequence(self, x_values: List[Tuple[float, int, str]]) -> Tuple[List[int], Optional[int]]:
        """
        Detect incremental roughing passes and identify finish pass.

        Patterns Recognized:
        1. Incremental X values (0.15-0.5" steps) = roughing sequence
        2. Last pass in sequence = finish pass (final dimension)
        3. Slower feed rate (F0.006-0.009 vs F0.015-0.020) = finish indicator

        Args:
            x_values: List of (x_diameter, line_number, line_text) tuples

        Returns:
            (roughing_line_numbers, finish_line_number)

        Example from o10280.nc:
            X2.3, X2.6, X2.9, X3.2 → roughing (F0.02)
            X4.928 Z-0.15 → finish (F0.015, chamfer depth)
        """
        if len(x_values) < 3:
            return [], None  # Need 3+ values to detect pattern

        roughing_lines = []
        finish_line = None

        # Extract X values for increment analysis
        x_only = [x for x, ln, txt in x_values]

        # Calculate increments between consecutive values
        increments = [x_only[i+1] - x_only[i] for i in range(len(x_only)-1)]

        # Check for consistent incremental pattern
        if len(increments) >= 2:
            avg_increment = sum(increments) / len(increments)

            # Roughing signature: 0.15-0.5" consistent steps
            if 0.15 < avg_increment < 0.5:
                # All but last are roughing
                roughing_lines = [ln for _, ln, _ in x_values[:-1]]
                finish_line = x_values[-1][1]
                return roughing_lines, finish_line

        # Alternative: Check feed rates for finish pass
        # Slower feed = finish (F0.006-0.009 vs F0.015-0.020)
        for i, (x, ln, txt) in enumerate(x_values):
            f_match = re.search(r'F0\.00([6-9])', txt, re.IGNORECASE)
            if f_match:
                # Slow feed = finish pass
                finish_line = ln
                roughing_lines = [ln2 for _, ln2, _ in x_values[:i]]
                return roughing_lines, finish_line

        return [], None

    def _extract_chamfer_dimension_from_comment(self, lines: List[str], operation: str = 'BORE') -> Optional[float]:
        """
        Extract final dimension from chamfer tool operations.

        Pattern:
            T121 (CHAMFER BORE)  ← Chamfer tool comment
            ...
            G01 X4.177 Z-0.1 F0.008  ← Final dimension

        Returns diameter in inches or None
        """
        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Look for chamfer tool comment
            if 'CHAMFER' in line_upper and operation in line_upper:
                # Scan next 10-20 lines for X at chamfer depth
                for j in range(i+1, min(i+20, len(lines))):
                    scan_line = lines[j]
                    x_match = re.search(r'X\s*([\d.]+)', scan_line, re.IGNORECASE)
                    z_match = re.search(r'Z\s*-\s*([\d.]+)', scan_line, re.IGNORECASE)

                    # Chamfer signature: X with shallow Z (0.05-0.15")
                    if x_match and z_match:
                        x_val = float(x_match.group(1))
                        z_val = float(z_match.group(1))

                        if 0.05 <= z_val <= 0.2 and 1.5 < x_val < 10.0:
                            return x_val  # Final dimension

                    # Stop at next tool change
                    if re.search(r'T[0-9]{3}', scan_line.upper()):
                        break

        return None

    def _classify_bore_type(self, result: GCodeParseResult):
        """
        Classify bore as centerbore (through-hole) or counterbore (partial recess).

        Pattern-Based Classification (not depth ratio):
        - Centerbore: Single bore operation to full drill depth (through-hole)
        - Counterbore: Shelf/step detected in G-code (counter_bore_depth is set)

        Logic:
        1. STEP spacers → ALWAYS counterbore (shelf + through-hole design)
        2. 2PC with counter_bore_depth → counterbore (step feature)
        3. Any part with counter_bore_depth → counterbore (shelf detected)
        4. Standard/HC without counter_bore_depth → centerbore (through-hole)

        Note: counter_bore_depth only gets set when we detect a shelf/step pattern
        in the G-code (shallow bore < drill depth). This is the key indicator.

        Updates result.bore_type field: 'centerbore', 'counterbore', or 'unknown'
        """
        # Default to unknown
        result.bore_type = 'unknown'

        # PRIORITY 1: STEP spacers are ALWAYS counterbore (by definition)
        # STEP = counterbore (shelf) + centerbore (through-hole)
        if result.spacer_type == 'step':
            result.bore_type = 'counterbore'
            if result.counter_bore_depth:
                result.detection_notes.append(
                    f"Bore type: COUNTERBORE (STEP spacer with shelf depth {result.counter_bore_depth:.2f}\")"
                )
            else:
                result.detection_notes.append(
                    f"Bore type: COUNTERBORE (STEP spacer pattern detected)"
                )
            return

        # PRIORITY 2: 2PC with counter_bore_depth set → counterbore
        # 2PC parts with step/shelf feature have counterbore
        if '2PC' in result.spacer_type and result.counter_bore_depth:
            result.bore_type = 'counterbore'
            result.detection_notes.append(
                f"Bore type: COUNTERBORE (2PC with step depth {result.counter_bore_depth:.2f}\")"
            )
            return

        # PRIORITY 3: If counter_bore_depth is set but not STEP/2PC, it's still counterbore
        # This field only gets set when we detect a shelf/step pattern in G-code
        if result.counter_bore_depth:
            result.bore_type = 'counterbore'
            result.detection_notes.append(
                f"Bore type: COUNTERBORE (shelf/step depth {result.counter_bore_depth:.2f}\")"
            )
            return

        # PRIORITY 4: Standard and HC parts without counter_bore_depth → centerbore
        # These are through-hole designs (no shelf/step detected in G-code)
        if result.spacer_type in ['standard', 'hub_centric']:
            result.bore_type = 'centerbore'
            if result.drill_depth:
                result.detection_notes.append(
                    f"Bore type: CENTERBORE (through-hole to drill depth {result.drill_depth:.2f}\")"
                )
            else:
                result.detection_notes.append(
                    f"Bore type: CENTERBORE (standard through-hole pattern)"
                )
            return

        # FALLBACK: Unknown type (shouldn't happen often)
        # This handles edge cases where spacer_type is unusual or missing data

    def _detect_hub_from_roughing_pattern(self, lines: List[str], od_estimate: Optional[float] = None) -> dict:
        """
        Detect hub profile from OP2 roughing pattern (oscillating X with stepped Z).

        Roughing Pattern (Side 2):
        X10.0 Z-0.2   ← OD position, down 0.2"
        X6.71         ← Turn in to hub rough (OB + 0.01" allowance)
        X10.0         ← Back to OD
        Z-0.4         ← Down another 0.2"
        X6.71         ← Turn in to hub rough again
        ...           ← Repeat 2-5 times

        Returns:
            {
                'detected': bool,
                'hub_diameter': float (inches, OB minus roughing allowance),
                'hub_height': float (inches, max Z depth),
                'confidence': str ('HIGH', 'MEDIUM', 'LOW'),
                'note': str (detection details)
            }
        """
        result = {
            'detected': False,
            'hub_diameter': None,
            'hub_height': None,
            'confidence': 'NONE',
            'note': ''
        }

        # Track OP2 section
        in_op2 = False
        in_turn_op2 = False

        # Track X oscillations and Z steps
        x_movements = []  # (x_val, z_val, line_no)
        last_x = None
        last_z = None
        current_z = None

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Detect OP2 (Side 2)
            if any(marker in line_upper for marker in ['OP2', 'OP 2', 'FLIP PART', 'FLIP', 'SIDE 2']):
                in_op2 = True

            # Track turning operations in OP2
            if in_op2:
                if 'T303' in line_upper or ('TURN' in line_upper and 'TOOL' in line_upper):
                    in_turn_op2 = True
                elif re.search(r'T[12]\d{2}', line_upper):
                    in_turn_op2 = False

            # Extract X and Z movements in OP2 turning
            if in_turn_op2:
                x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)

                # Update current Z depth (modal tracking)
                if z_match:
                    current_z = float(z_match.group(1))

                # Track X movements with their Z depth
                if x_match:
                    x_val = float(x_match.group(1))
                    x_movements.append((x_val, current_z, i))
                    last_x = x_val

        # Analyze X movements for oscillating pattern
        if len(x_movements) < 6:  # Need at least 3 cycles (6 movements)
            return result

        # Group movements into oscillation cycles
        # Pattern: Large X (OD) → Small X (hub rough) → Large X → Small X...
        cycles = []
        for j in range(len(x_movements) - 1):
            x1, z1, ln1 = x_movements[j]
            x2, z2, ln2 = x_movements[j + 1]

            # Check for X oscillation: large → small (facing → hub)
            if x1 > x2 + 0.3:  # X decreased by >0.3" (turned inward)
                # Accept oscillation if x1 is reasonable facing diameter (>4.0")
                # Note: x1 may not match full OD - OP2 may only face the hub area
                # Example: 13" part may only face to ~7" around hub
                if x1 > 4.0:
                    cycles.append({
                        'od_x': x1,
                        'hub_x': x2,
                        'z_depth': z2 if z2 else z1,
                        'line': ln2
                    })

        # Validate pattern: need 2+ cycles with stepped Z depths
        if len(cycles) < 2:
            return result

        # FIRST: Filter out cycles with shallow Z depths (chamfer operations, cleanup moves)
        # Main roughing pattern typically starts at Z >= 0.15"
        min_z_for_roughing = 0.15
        roughing_cycles = [c for c in cycles if c['z_depth'] and c['z_depth'] >= min_z_for_roughing]

        if len(roughing_cycles) < 2:
            result['note'] = f"Too few valid roughing cycles after filtering (found {len(roughing_cycles)})"
            return result

        # SECOND: Calculate Z steps from FILTERED roughing cycles only
        z_depths = [c['z_depth'] for c in roughing_cycles]
        z_steps = [z_depths[i+1] - z_depths[i] for i in range(len(z_depths)-1)]
        if not z_steps:
            return result

        # Calculate average for reporting
        avg_step = sum([abs(s) for s in z_steps]) / len(z_steps)

        # THIRD: Validate Z steps are in safe range (0.10-0.20")
        # First rough can be Z-0.1 or Z-0.15, max step should be 0.20"
        # Accept if MOST steps are valid (handles occasional outliers)
        valid_steps = [abs(s) for s in z_steps if 0.10 <= abs(s) <= 0.20]
        valid_ratio = len(valid_steps) / len(z_steps)

        # Check for aggressive steps (> 0.20" + small tolerance for floating point)
        # Tolerance of 0.005" to avoid false warnings from rounding
        aggressive_steps = [abs(s) for s in z_steps if abs(s) > 0.205]
        if aggressive_steps and len(aggressive_steps) > 1:  # More than one aggressive step
            max_aggressive = max(aggressive_steps)
            result['warning'] = f"Aggressive Z steps detected: {len(aggressive_steps)} steps > 0.20\" (max: {max_aggressive:.2f}\")"

        # Accept if at least 70% of steps are in the safe range
        if valid_ratio < 0.70:
            result['note'] = f"Z steps irregular ({valid_ratio*100:.0f}% valid, avg {avg_step:.2f}\")"
            return result

        # Extract hub diameter (minimum X value minus roughing allowance)
        hub_x_values = [c['hub_x'] for c in roughing_cycles]
        min_hub_x = min(hub_x_values)

        # Roughing allowance is typically 0.01" (subtract to get finish dimension)
        hub_diameter = min_hub_x - 0.01

        # Extract hub height (maximum Z depth from filtered roughing cycles)
        roughing_z_depths = [c['z_depth'] for c in roughing_cycles if c['z_depth']]
        hub_height = max(roughing_z_depths) if roughing_z_depths else 0

        # Validate hub dimensions
        if not (2.0 < hub_diameter < 10.0):
            result['note'] = f"Hub diameter {hub_diameter:.2f}\" outside valid range (2.0-10.0\")"
            return result

        if not (0.2 <= hub_height <= 3.5):
            result['note'] = f"Hub height {hub_height:.2f}\" outside valid range (0.2-3.5\")"
            return result

        # Success! Hub detected from roughing pattern
        result['detected'] = True
        result['hub_diameter'] = round(hub_diameter, 3)
        result['hub_height'] = round(hub_height, 2)
        result['confidence'] = 'HIGH' if len(cycles) >= 3 else 'MEDIUM'
        result['note'] = f"Hub roughing pattern: {len(cycles)} cycles, Z steps avg {avg_step:.2f}\""

        return result

    def _detect_dual_counterbore_pattern(self, lines: List[str]) -> Dict:
        """
        Detect dual counterbore pattern for steel ring assemblies.

        Pattern (from o80152.nc):
        1. First counterbore operation (T121 CHAMFER BORE)
        2. M30 (end program)
        3. M00 (optional stop - operator decision point)
        4. Second counterbore operation (larger diameter, same depth)

        This allows one program to support TWO steel ring sizes.

        Returns:
            dict: {
                'detected': bool,
                'first_cb': float (inches),
                'second_cb': float (inches),
                'depth': float (inches)
            }
        """
        result = {
            'detected': False,
            'first_cb': None,
            'second_cb': None,
            'depth': None
        }

        # Look for M30 followed by M00 pattern
        m30_found = False
        m00_line = None
        first_cb_x = None
        first_cb_z = None

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Track M30
            if 'M30' in line_upper:
                m30_found = True
                continue

            # Look for M00 after M30
            if m30_found and 'M00' in line_upper:
                m00_line = i
                break

        if m00_line is None:
            return result  # No M30/M00 pattern found

        # Scan backwards from M30 to find T121 (CHAMFER BORE) section
        t121_line = None
        for i in range(m00_line - 1, max(0, m00_line - 100), -1):
            if 'T121' in lines[i].upper() or 'CHAMFER BORE' in lines[i].upper():
                t121_line = i
                break

        if t121_line is None:
            return result  # No T121 found before M00

        # Scan FORWARD from T121 to find first counterbore operation
        # Track modal X coordinate
        modal_x = None
        for i in range(t121_line, m00_line):
            line = lines[i]
            line_upper = line.upper()

            # Update modal X (but ignore X values after G01 Z-negative)
            x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
            if x_match:
                x_val = float(x_match.group(1))
                # Only update modal_x if not a small inward movement
                # Counterbore X should be > 4.0", inward movements are typically < 4.5"
                if x_val > 4.5:
                    modal_x = x_val

            # Look for G01 Z-negative (counterbore depth operation)
            z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
            if z_match and line.strip().startswith('G01'):
                z_val = float(z_match.group(1))
                # Counterbore depth typically 0.3-1.0" (not full drill depth)
                if 0.3 <= z_val <= 1.0 and modal_x:
                    first_cb_x = modal_x
                    first_cb_z = z_val
                    break

        if first_cb_x is None:
            return result  # No first counterbore found before M00

        # Scan forward from M00 to find second counterbore operation
        # Reset modal X for second section
        modal_x = None
        for i in range(m00_line + 1, min(m00_line + 20, len(lines))):
            line = lines[i]
            line_upper = line.upper()

            # Update modal X
            x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
            if x_match:
                modal_x = float(x_match.group(1))

            # Look for G01 Z-negative (counterbore depth operation)
            z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
            if z_match and line.strip().startswith('G01'):
                second_cb_z = float(z_match.group(1))

                # Validate: same depth as first CB (within 0.1")
                if abs(second_cb_z - first_cb_z) < 0.1 and modal_x:
                    # Validate: second CB is larger (indicates replacement)
                    if modal_x > first_cb_x + 0.1:  # At least 0.1" larger
                        result['detected'] = True
                        result['first_cb'] = first_cb_x
                        result['second_cb'] = modal_x
                        result['depth'] = first_cb_z
                        return result

        return result

    def _detect_side_from_line(self, line: str, current_side: int) -> int:
        """
        Detect which side of the part (Side 1 or Side 2) based on G-code markers.

        Detection Patterns:
        1. Work offsets: G54 = Side 1, G55 = Side 2
        2. Comments: "OP1"/"SIDE 1" = Side 1, "OP2"/"SIDE 2" = Side 2
        3. "FLIP PART" = toggle side (1 → 2 or 2 → 1)

        Args:
            line: G-code line to analyze
            current_side: Current side (1 or 2)

        Returns:
            Updated side number (1 or 2)
        """
        line_upper = line.upper()

        # Work offset changes (most reliable)
        if 'G54' in line_upper:
            return 1  # Side 1 (primary work offset)
        elif 'G55' in line_upper:
            return 2  # Side 2 (secondary work offset)

        # Comment markers
        if 'OP1' in line_upper or 'SIDE 1' in line_upper or '(SIDE 1)' in line_upper:
            return 1
        elif 'OP2' in line_upper or 'SIDE 2' in line_upper or '(SIDE 2)' in line_upper:
            return 2

        # Flip part comment (toggle side)
        if 'FLIP' in line_upper and 'PART' in line_upper:
            return 2 if current_side == 1 else 1

        # No change detected
        return current_side

    def _extract_dimensions_from_gcode(self, result: GCodeParseResult, lines: List[str]):
        """
        Extract dimensions directly from G-code operations

        Multi-Method Strategy:
        1. CB: Smallest X value in BORE operation (OP1/Side 1) with Z depth
        2. OB: Smallest X value in OP2 progressive facing (hub-centric only)
        3. Hub Height: Final Z depth in OP2 facing before OB (hub-centric)
        4. Thickness: Calculate from drill_depth - hub_height - 0.15 (hub-centric)
                      or drill_depth - 0.15 (standard/STEP)
        5. OD: Maximum X value in turning operations (lathe in diameter mode)
        """
        in_bore_op1 = False
        in_bore_op2 = False  # Track boring operations on Side 2 (for steel rings)
        in_flip = False
        in_turn_op2 = False

        # Side tracking (Side 1 or Side 2)
        current_side = 1  # Start on Side 1
        cb_side = None    # Track which side CB was extracted from
        ob_side = None    # Track which side OB was extracted from
        cb_tool = None    # Track which tool extracted CB
        ob_tool = None    # Track which tool extracted OB

        cb_candidates = []
        cb_values_with_context = []  # ROUGHING DETECTION: Store (x_val, line_no, line_text, is_finish)
        cb_found = False  # Stop collecting after finding definitive CB
        ob_candidates = []
        od_candidates = []  # Track OD from turning operations
        op2_z_depths = []  # Track Z depths in OP2 for hub height extraction
        last_z_before_ob = None  # Last Z depth before reaching OB
        steel_ring_side2_x_values = []  # Track X diameters on Side 2 for steel ring counterbore

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

            # Update side tracking
            current_side = self._detect_side_from_line(line, current_side)

            # Track operations
            if 'FLIP' in line_upper:
                in_flip = True
                in_bore_op1 = False
            elif 'T121' in line_upper or 'BORE' in line_upper:
                if not in_flip:
                    in_bore_op1 = True
                    in_bore_op2 = False
                    in_turn_op2 = False
                else:
                    # T121 in OP2 - boring/chamfering on Side 2 (steel ring counterbore)
                    in_bore_op1 = False
                    in_bore_op2 = True
                    in_turn_op2 = False
            elif 'T303' in line_upper or ('TURN' in line_upper and 'TOOL' in line_upper):
                in_bore_op1 = False
                in_bore_op2 = False
                if in_flip:
                    in_turn_op2 = True
            elif 'T101' in line_upper or 'DRILL' in line_upper:
                in_bore_op1 = in_bore_op2 = in_turn_op2 = False

            # Extract CB from OP1 BORE (should be on Side 1)
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
                    # CRITICAL FIX: Chamfer detection was assuming chamfers are always at CB
                    # But in files like o10511, chamfer at X6.69 Z-0.15 is at counterbore/shelf, NOT CB!
                    # The actual CB is the smaller bore that reaches full drill depth (X5.6 at Z-2.4)
                    #
                    # NEW LOGIC: Chamfers at shallow depths (~0.15") are NOT the CB
                    # Only trust chamfers that are followed by full-depth boring operations
                    if x_match and z_match:
                        chamfer_x = float(x_match.group(1))
                        chamfer_z = float(z_match.group(1))

                        # Check if this is a shallow chamfer (counterbore/shelf) or deep chamfer (actual CB)
                        is_shallow_chamfer = chamfer_z < 0.3  # Chamfer depth < 0.3" is likely counterbore

                        if 1.5 < chamfer_x < 10.0:  # Extended to 10.0 for large 13" parts
                            # For STEP spacers: chamfer is at counterbore, NOT CB
                            # CB is the smaller bore that goes to full depth
                            if result.spacer_type == 'step':
                                # Store chamfer as counterbore diameter (if not already set)
                                if not result.counter_bore_diameter:
                                    result.counter_bore_diameter = chamfer_x * 25.4  # Convert to mm
                                # Don't set cb_found - continue looking for actual CB at full depth
                            elif is_shallow_chamfer:
                                # Shallow chamfer in hub-centric = counterbore/shelf, NOT CB
                                # Don't add to cb_candidates - let full-depth detection find actual CB
                                pass
                            else:
                                # Deep chamfer in hub-centric = likely actual CB
                                cb_candidates.append(chamfer_x)
                                cb_found = True  # This is definitive CB
                                # Track side and tool for CB extraction
                                if cb_side is None:
                                    cb_side = current_side
                                    cb_tool = 'T121' if 'T121' in line_upper else 'BORE'

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

                        # =============================================================
                        # CHAMFER DIAGONAL PATTERN DETECTION (PRIORITY CHECK)
                        # =============================================================
                        # Pattern: X[CB] Z-0.15 (chamfer diagonal) followed by Z-[full_depth]
                        # Example from o57798:
                        #   Line 34: G01 X2.567 Z-0.15 F0.009  <- X is CB, Z is chamfer depth
                        #   Line 35: Z-2.15                    <- Full depth confirms CB
                        #
                        # The chamfer start is ~0.3" larger than CB (creates chamfer by moving diagonally)
                        # CB value is the X in the diagonal move, NOT the chamfer start position
                        # =============================================================
                        is_chamfer_diagonal = False
                        if z_match:
                            z_on_same_line = float(z_match.group(1))
                            # Chamfer diagonal: Z is shallow (0.1-0.2") on SAME line as X
                            if 0.1 <= z_on_same_line <= 0.25:
                                # Check if NEXT line is Z-only to full depth (confirms this X is CB)
                                for j in range(i+1, min(i+3, len(lines))):
                                    next_line = lines[j].strip()
                                    next_z = re.search(r'Z\s*-\s*([\d.]+)', next_line, re.IGNORECASE)
                                    next_x = re.search(r'X\s*([\d.]+)', next_line, re.IGNORECASE)

                                    # Z-only line to full depth = confirms chamfer diagonal pattern
                                    if next_z and not next_x:
                                        full_z = float(next_z.group(1))
                                        # Check if this Z reaches thickness or drill depth
                                        reaches_depth = False
                                        if drill_depth and full_z >= drill_depth * 0.9:
                                            reaches_depth = True
                                        elif result.thickness and full_z >= result.thickness * 0.9:
                                            reaches_depth = True
                                        elif full_z >= 0.8:  # At least 0.8" deep (most parts are > 1")
                                            reaches_depth = True

                                        if reaches_depth:
                                            # This is the chamfer diagonal pattern - X IS the CB!
                                            is_chamfer_diagonal = True
                                            max_z_depth = full_z
                                            break
                                    elif next_x:
                                        # Another X before deep Z - not chamfer diagonal
                                        break

                        # If chamfer diagonal detected, this X is the CB (high confidence)
                        if is_chamfer_diagonal and not cb_found:
                            # Validate against title CB if available
                            if result.center_bore:
                                x_val_mm = x_val * 25.4
                                # Allow up to 2mm difference (machining tolerance)
                                if abs(x_val_mm - result.center_bore) < 5.0:
                                    cb_candidates = [x_val]  # Definitive CB
                                    cb_found = True
                                    # Track side and tool for CB extraction
                                    if cb_side is None:
                                        cb_side = current_side
                                        cb_tool = 'T121' if 'T121' in line_upper else 'BORE'
                                # If doesn't match title, still add as candidate but don't set cb_found
                                else:
                                    cb_candidates.append(x_val)
                                    # Track side and tool for CB extraction (on first candidate)
                                    if cb_side is None:
                                        cb_side = current_side
                                        cb_tool = 'T121' if 'T121' in line_upper else 'BORE'
                            else:
                                # No title CB - trust chamfer pattern
                                cb_candidates = [x_val]
                                cb_found = True
                                # Track side and tool for CB extraction
                                if cb_side is None:
                                    cb_side = current_side
                                    cb_tool = 'T121' if 'T121' in line_upper else 'BORE'
                            continue  # Skip the rest of the X processing for this line

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
                            # Check if this X reaches full drill depth OR thickness depth
                            # CRITICAL FIX: Final CB boring often goes to thickness, not full drill depth
                            # Example: drill_depth=1.4", thickness=1.25", final bore=Z-1.25" (not Z-1.4")
                            reaches_full_depth = False
                            if drill_depth and max_z_depth >= drill_depth * 0.95:
                                reaches_full_depth = True
                            elif result.thickness and max_z_depth >= result.thickness * 0.95:
                                # Boring to thickness depth (common for final CB dimension)
                                reaches_full_depth = True
                            
                            # SPECIAL CASES for shelf patterns:
                            # 1. Thin hub (CB and OB within 5mm): Shelf in OP1 to preserve hub material
                            # 2. Hub inside CB (OB < CB): Hub is smaller than CB, shelf supports it
                            # 3. CB=Counterbore in title: (X IS CB) marker refers to CB, not counterbore
                            # CRITICAL: Only apply to SMALL parts (CB < 100mm), not large 13" rounds
                            is_special_case = False
                            is_hub_inside_cb = False  # Hub OB < CB case
                            if result.center_bore and result.hub_diameter:
                                cb_ob_diff = abs(result.hub_diameter - result.center_bore)
                                # Thin hub detection: Only for small parts (CB < 100mm)
                                # Large parts like 13" rounds can have CB≈OB but aren't "thin hub"
                                if cb_ob_diff <= 5.0 and result.center_bore < 100.0:  # Thin hub on small parts
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
                            # CRITICAL FIX: "(X IS CB)" comments are often WRONG - they mark the counterbore/shelf
                            # at chamfer depth (Z-0.15) instead of the actual CB at full drill depth (Z-2.4)
                            # Example o10511: X6.69 Z-0.15 (X IS CB) <- WRONG! Actual CB is X5.6 at Z-2.4
                            #
                            # NEW RULES:
                            # 1. (X IS CB) at FULL DRILL DEPTH: Trust it (rare but valid)
                            # 2. (X IS CB) at CHAMFER DEPTH: IGNORE IT - it's the counterbore/shelf, not CB
                            # 3. NO MARKER: X must reach full drill depth to be CB candidate
                            # 4. SPECIAL CASE (thin hub) + no marker: CB is LARGEST X at partial depth (shelf)

                            # Check if marker is at chamfer depth (Z ~0.15") vs full depth
                            is_at_chamfer_depth = False
                            if initial_z_depth and 0.05 <= initial_z_depth <= 0.25:
                                is_at_chamfer_depth = True

                            if has_cb_marker:
                                # VALIDATION STRATEGY: Check if marked value matches title spec
                                # If marker value is within 5mm of title CB, trust it (even at chamfer depth)
                                # This fixes the Dec 4 over-correction that ignored too many correct markers
                                marker_matches_title = False
                                if result.center_bore:
                                    marker_value_mm = x_val * 25.4
                                    if abs(marker_value_mm - result.center_bore) < 5.0:
                                        marker_matches_title = True

                                if marker_matches_title:
                                    # Marker value matches title spec - trust it!
                                    cb_candidates = [x_val]  # Definitive CB
                                    cb_found = True  # Stop collecting more candidates
                                elif reaches_full_depth and not is_at_chamfer_depth:
                                    # Trust markers at full drill depth (original logic)
                                    cb_candidates = [x_val]  # Definitive CB
                                    cb_found = True  # Stop collecting more candidates
                                # Else: marker at chamfer depth and doesn't match title = counterbore/shelf, skip it!
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
                                    cb_values_with_context.append((x_val, i, line, False))
                                # Also collect full depth values for comparison
                                elif reaches_full_depth:
                                    # Full depth is initial bore, but keep it as fallback
                                    if not cb_candidates:  # Only add if no partial depth found
                                        cb_candidates.append(x_val)
                                        cb_values_with_context.append((x_val, i, line, False))
                            elif reaches_full_depth and not cb_found:
                                # CRITICAL FIX: Filter out G00 rapid moves!
                                # G00 X4.4 is a retraction move, not a boring operation
                                is_rapid_move = line.strip().startswith('G00')
                                if not is_rapid_move:
                                    cb_candidates.append(x_val)
                                    # ROUGHING DETECTION: Track context for this candidate
                                    cb_values_with_context.append((x_val, i, line, False))
                                    # Track side and tool for CB extraction (on first candidate)
                                    if cb_side is None:
                                        cb_side = current_side
                                        cb_tool = 'T121' if 'T121' in line_upper else 'BORE'
                            # If doesn't reach full depth and no marker, skip

            # ================================================================
            # STEEL RING COUNTERBORE EXTRACTION (Side 2)
            # ================================================================
            # Steel rings machine center bore on Side 1, then flip and machine
            # counterbore (larger diameter) on Side 2 in T121 CHAMFER BORE operation
            # Pattern: After FLIP PART comment, look for largest X diameter in boring ops
            # ================================================================
            if result.spacer_type == 'steel_ring' and in_bore_op2:
                # Collect X values in boring operations on Side 2
                x_match = re.search(r'X\s*([\d.]+)', line, re.IGNORECASE)
                if x_match:
                    x_val = float(x_match.group(1))
                    # Counterbore should be larger than center bore (typically 4.5-7.0")
                    # Filter out small X values (cleanup moves, etc.)
                    if x_val > 4.0:
                        steel_ring_side2_x_values.append(x_val)

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

            # Extract OB and hub height from OP2 progressive facing (hub-centric and 2PC)
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

                # OB detection works for hub-centric AND 2PC files (2PC can have HC interface)
                is_hc_or_2pc = result.spacer_type == 'hub_centric' or '2PC' in result.spacer_type

                if x_match and is_hc_or_2pc:
                    x_val = float(x_match.group(1))
                    z_val = float(z_match.group(1)) if z_match else None

                    # If line has "(X IS OB)" marker, prioritize this value
                    if has_ob_marker:
                        ob_candidates.append((x_val, z_val, i, True, False))  # True = has marker, False = has_following_z (N/A for marked)
                        # Track side and tool for OB extraction
                        if ob_side is None:
                            ob_side = current_side
                            ob_tool = 'T303' if 'T303' in line_upper else 'TURN'

                    # OB (Hub D) range depends on part size:
                    # - Small parts (OD ~6"): OB typically 2.0-4.0" (50-100mm)
                    # - Large parts (OD ~13"): OB can be 6-9" (e.g., X8.661 for 220mm OB)
                    # CRITICAL FIX: Extended range to 10.0" to handle 13" rounds
                    # CRITICAL FIX: Lowered minimum from 2.2" to 2.0" to catch small OB values (50-56mm)
                    # Progressive facing cuts down to the OB, then retracts to smaller X (CB)
                    # Exclude values too large (OD facing > 10.5") and too small (CB < 2.0")
                    elif 2.0 < x_val < 10.5:
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
                                    # If Z is within hub height range (0.02" to 2.0"), this confirms X is OB
                                    # Lowered from 0.05 to 0.02 to catch shallow movements like Z-0.04
                                    if 0.02 <= next_z_val <= 2.0:
                                        has_following_z = True

                        # Store X with its Z depth, line index, and following_z flag for detection
                        ob_candidates.append((x_val, z_val, i, False, has_following_z))  # Added has_following_z flag
                        # Track side and tool for OB extraction (on first candidate)
                        if ob_side is None:
                            ob_side = current_side
                            ob_tool = 'T303' if 'T303' in line_upper else 'TURN'

                    # Also collect CB candidates from OP2 chamfer area (for hub-centric parts)
                    # CB chamfer is at shallow Z (< 0.15) and smaller than OB
                    # Use title spec to filter: CB should be close to title CB, not title OB
                    # IMPORTANT: Only do this if we have a title CB to compare against
                    # Otherwise OP2 chamfer values will incorrectly be selected as CB

                    # Check if this is a SHELF DESIGN (CB ≈ OB within 2mm)
                    is_shelf_design = False
                    if result.center_bore and result.hub_diameter:
                        cb_ob_diff = abs(result.center_bore - result.hub_diameter)
                        is_shelf_design = cb_ob_diff < 2.0  # CB and OB within 2mm = shelf design

                    # For shelf designs: collect from deeper Z values (shelf is cut at Z > 0.15)
                    # For normal designs: only collect from shallow Z (chamfer area < 0.15)
                    z_threshold = 0.6 if is_shelf_design else 0.15

                    if z_val and z_val < z_threshold:
                        if 2.0 < x_val < 3.2:  # CB range
                            # Only add if we have title CB to compare and it's closer to CB than OB
                            if result.center_bore:  # Have title CB to compare
                                title_cb_inches = result.center_bore / 25.4
                                title_ob_inches = result.hub_diameter / 25.4 if result.hub_diameter else 999
                                # Distance from title CB vs distance from title OB
                                dist_to_cb = abs(x_val - title_cb_inches)
                                dist_to_ob = abs(x_val - title_ob_inches)
                                # Only add if closer to CB spec than OB spec
                                # For shelf designs, be more lenient (within 0.2")
                                # For normal designs, require closer to CB than OB
                                if is_shelf_design:
                                    # Shelf design: accept if within 0.2" of CB/OB spec
                                    if dist_to_cb < 0.2 or dist_to_ob < 0.2:
                                        cb_candidates.append(x_val)
                                        cb_values_with_context.append((x_val, i, line, False))
                                else:
                                    # Normal design: only if closer to CB than OB
                                    if dist_to_cb < dist_to_ob:
                                        cb_candidates.append(x_val)
                                        cb_values_with_context.append((x_val, i, line, False))
                            # If no title CB, don't add OP2 values - rely on OP1 full depth extraction

        # ===================================================================
        # ROUGHING DETECTION: Apply incremental roughing detection to CB candidates
        # ===================================================================
        # If we collected multiple CB candidates without finding a definitive one,
        # apply roughing detection to filter out roughing passes and prioritize finish passes
        if cb_values_with_context and not cb_found and len(cb_values_with_context) >= 3:
            # Extract (x, line_no, line_text) for roughing detection
            x_for_detection = [(x, ln, txt) for x, ln, txt, is_fin in cb_values_with_context]

            # Apply roughing sequence detection
            roughing_lines, finish_line = self._detect_roughing_sequence(x_for_detection)

            if roughing_lines or finish_line:
                # Mark finish passes in our context list
                cb_values_updated = []
                for x, ln, txt, is_fin in cb_values_with_context:
                    # A value is a finish pass if:
                    # 1. It's the identified finish line, OR
                    # 2. It's not in the roughing lines list
                    is_finish = (ln == finish_line or ln not in roughing_lines)
                    cb_values_updated.append((x, ln, txt, is_finish))

                cb_values_with_context = cb_values_updated

                # Reconstruct cb_candidates with ONLY finish passes
                finish_candidates = [x for x, ln, txt, is_fin in cb_values_with_context if is_fin]

                if finish_candidates:
                    # Success! Use only finish passes for CB selection
                    cb_candidates = finish_candidates
                    # Note: Keep all cb_values_with_context for potential debugging/logging
                # Else: No finish candidates identified, keep all candidates (fallback)

        # Select CB: FIXED to use closest to title spec instead of max
        # Issue: max() fails when chamfer creates oversized CB (e.g., X6.941 vs spec X6.701)
        # Solution: Select candidate closest to title spec for better accuracy
        if cb_candidates:
            if result.center_bore:
                # Select candidate closest to title spec (in inches)
                title_cb_inches = result.center_bore / 25.4
                closest_cb = min(cb_candidates, key=lambda x: abs(x - title_cb_inches))
                result.cb_from_gcode = closest_cb * 25.4  # Convert to mm
            else:
                # Fallback: use max if no title spec to compare
                result.cb_from_gcode = max(cb_candidates) * 25.4  # Convert to mm

            # Add detection note showing which side CB was extracted from
            if cb_side is not None:
                side_text = f"Side {cb_side}" if cb_side in [1, 2] else f"Side {cb_side}"
                tool_text = f" ({cb_tool})" if cb_tool else ""
                result.detection_notes.append(f"CB extracted from {side_text}{tool_text}: {result.cb_from_gcode:.1f}mm")

        # ================================================================
        # STEEL RING COUNTERBORE (Side 2) - Set from collected values
        # ================================================================
        # For steel rings: center bore machined on Side 1, counterbore on Side 2
        # Counterbore is the larger diameter on Side 2 (typically in T121 CHAMFER BORE)
        # ================================================================
        if result.spacer_type == 'steel_ring' and steel_ring_side2_x_values:
            # Largest X value on Side 2 is the counterbore diameter
            result.counter_bore_diameter = max(steel_ring_side2_x_values) * 25.4  # Convert to mm
            result.detection_notes.append(
                f"Steel ring counterbore from Side 2: {result.counter_bore_diameter:.1f}mm"
            )

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
                # CRITICAL FIX: Check ALL candidates for near-matches FIRST, not just those with following Z
                # Issue: Best OB values (X2.8, X2.764) don't have following Z flag, so they were excluded
                # Solution: Prioritize near-matches from ALL candidates, use following_z as tiebreaker

                # Filter out OD values from ALL candidates
                od_mm = result.outer_diameter * 25.4 if result.outer_diameter else None
                all_filtered_ob = []
                for x_val, z_val, idx, has_marker, has_z in ob_candidates:
                    x_mm = x_val * 25.4
                    # Exclude if close to OD (OD facing operations)
                    if od_mm and abs(x_mm - od_mm) > 8.0:  # More than 8mm away from OD
                        all_filtered_ob.append((x_val, has_z))
                    elif not od_mm:  # No OD to compare, keep all
                        all_filtered_ob.append((x_val, has_z))

                if all_filtered_ob:
                    # CRITICAL FIX: Use closest-to-spec with HIGH PRIORITY for near-matches
                    # Issue: Parser selects OD chamfer (X5.87) instead of actual OB (X2.857)
                    # Solution: If any candidate is within 5mm of title OB, use it (exact match priority)
                    if result.hub_diameter:
                        title_ob_inches = result.hub_diameter / 25.4
                        title_ob_mm = result.hub_diameter

                        # Check for near-exact matches first (within 5mm of spec)
                        near_matches = [(x, has_z) for x, has_z in all_filtered_ob if abs(x * 25.4 - title_ob_mm) < 5.0]

                        if near_matches:
                            # Use the closest near-match (high confidence - matches title!)
                            # If multiple near-matches, prefer one with following_z as tiebreaker
                            closest_ob = min(near_matches, key=lambda pair: (abs(pair[0] - title_ob_inches), not pair[1]))
                            result.ob_from_gcode = closest_ob[0] * 25.4
                        else:
                            # No near-matches, use overall closest (prefer following_z as tiebreaker)
                            closest_ob = min(all_filtered_ob, key=lambda pair: (abs(pair[0] - title_ob_inches), not pair[1]))
                            result.ob_from_gcode = closest_ob[0] * 25.4
                    else:
                        # Fallback: use min if no title spec to compare (prefer following_z as tiebreaker)
                        result.ob_from_gcode = min(all_filtered_ob, key=lambda pair: (pair[0], not pair[1]))[0] * 25.4
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

            # Add detection note showing which side OB was extracted from
            if result.ob_from_gcode and ob_side is not None:
                side_text = f"Side {ob_side}" if ob_side in [1, 2] else f"Side {ob_side}"
                tool_text = f" ({ob_tool})" if ob_tool else ""
                result.detection_notes.append(f"OB extracted from {side_text}{tool_text}: {result.ob_from_gcode:.1f}mm")

        # Select OD: maximum from turning operations (already in diameter mode)
        if od_candidates:
            result.od_from_gcode = max(od_candidates)  # Already in inches, no conversion needed

        # Detect dual counterbore pattern for steel ring assemblies
        # Pattern: M30 M00 followed by second counterbore operation (larger diameter, same depth)
        dual_cb_info = self._detect_dual_counterbore_pattern(lines)
        if dual_cb_info['detected']:
            cb1_mm = dual_cb_info['first_cb'] * 25.4
            cb2_mm = dual_cb_info['second_cb'] * 25.4
            depth = dual_cb_info['depth']
            result.detection_notes.append(
                f"Dual steel ring support: {cb1_mm:.1f}mm / {cb2_mm:.1f}mm (depth: {depth:.2f}\")"
            )

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

            # ONLY trust G154 P## or G54.1 P## patterns (extended work offsets)
            # These are the ONLY reliable indicators of fixture P-codes
            # G154 P## is common in Okuma/Fanuc controllers
            # CRITICAL: Do NOT detect P-codes from comments or standalone P## - those are false positives
            # Examples of FALSE positives we're avoiding:
            #   - (OP1), (OP2), (OP22) - operation labels, not P-codes
            #   - Standalone P## in comments
            # G154 P##, G54 P##, or G54.1 P## — G54(?:\.1)? makes ".1" optional
            # so plain G54 P## is now also captured.  [ \t]* avoids crossing lines.
            g54_match = re.search(r'G(?:154|54(?:\.1)?)[ \t]*P(\d+)', line, re.IGNORECASE)
            if g54_match:
                pcode = int(g54_match.group(1))
                # Work offsets are typically in range 1-99
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
            # Check for various OP2 markers: "OP2", "(OP2)", "FLIP PART", "FLIP", etc.
            if 'OP2' in line_upper or '(OP2)' in line_upper or 'FLIP' in line_upper:
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
        # Skip if already hub_centric or 2PC (don't reclassify 2PC parts)
        if result.spacer_type == 'hub_centric' or '2PC' in result.spacer_type:
            return

        # Don't skip based on CB/OB comparison - some HC parts have CB == OB in title
        # (thin-lipped hub-centric where machinist wrote same value twice, or CB matches OB)
        # Example: "71MM/71MM ID" - still need to check G-code for hub machining

        # Look for OP2 facing operations
        in_op2 = False
        facing_z_values = []
        last_x_value = None  # Track modal X position

        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Detect OP2 section - multiple markers used in different files
            # Common markers: "OP2", "(OP2)", "FLIP PART", "(FLIP PART)", "OP 2", "SIDE 2"
            if any(marker in line_upper for marker in ['OP2', 'OP 2', 'FLIP PART', 'SIDE 2', 'FLIP']):
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

    def _validate_tool_home_positions(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate G53 X Z tool home position lines for L1, L2, L3 lathes.

        SAFETY CHECKS:
        1. Z Clearance Before G53 (NEW):
           - CRITICAL: Z < 0 before G53 → tool will crash into part
           - WARNING: Z < 0.1 before G53 → insufficient clearance
           - PASS: Z >= 0.1 (0.100") → safe clearance
           - Looks back 30 lines to find last Z position before G53

        2. G53 Z-Value Rules (thickness-based minimum safe values):
           - Thickness <= 2.50": Z-13 or higher (Z-10, Z-8 are safe)
           - Thickness 2.75" - 3.75": Z-11 or higher
           - Thickness 4.00" - 5.00": Z-9 or higher
           - Z-16 is ALWAYS CRITICAL (dangerous, too far out)

        SAFETY LOGIC: Higher Z (less negative) = tool further from part = SAFER
        - Z-10 is safe for Z-13 parts (moves tool further away)
        - Z-8 is safe for all parts
        - Only warn when Z is LOWER than expected (tool too close to part)

        Only applies to lathes L1, L2, L3, L2/L3.
        """
        # Only validate for L1-L3 lathes
        if result.lathe not in ('L1', 'L2', 'L3', 'L2/L3'):
            result.tool_home_status = 'N/A'
            return

        # Need thickness to determine expected Z
        thickness = result.thickness

        # Determine expected Z based on thickness
        expected_z = None
        if thickness is not None:
            if thickness <= 2.50:
                expected_z = -13
            elif 2.75 <= thickness <= 3.75:
                expected_z = -11
            elif 4.00 <= thickness <= 5.00:
                expected_z = -9
            # Other thicknesses: expected_z stays None (unknown expected value)

        # Pattern to match G53 lines with X and Z coordinates
        # Examples: G53 X0 Z-13, G53 X0. Z-11., G53X0Z-9
        g53_pattern = re.compile(r'G53\s*X[\d.\-]*\s*Z([\-\d.]+)', re.IGNORECASE)

        # Pattern to match Z movements (G0 Z, G1 Z, etc.)
        z_move_pattern = re.compile(r'[G][01]\s*.*Z([\-\d.]+)', re.IGNORECASE)

        found_positions = []
        has_critical = False
        has_warning = False
        issues = []

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments
            if line_stripped.startswith('(') or line_stripped.startswith(';'):
                continue

            match = g53_pattern.search(line_stripped)
            if match:
                try:
                    z_value = float(match.group(1))
                except ValueError:
                    continue

                # Determine status for this line
                status = 'PASS'

                # Z-clearance-before-G53 check is now handled by crash_prevention_validator
                # (_detect_negative_z_before_tool_home) which correctly:
                # - Skips first 10 lines (initialization)
                # - Skips G53 lines during lookback (machine coordinates)
                # - Only flags when last Z movement is negative
                # The check below only validates G53 Z machine coordinate values

                # Z-16 is ALWAYS critical (dangerous)
                if z_value <= -16:
                    status = 'CRITICAL'
                    has_critical = True
                    issues.append(f"CRITICAL: Line {line_num} has Z{z_value} (Z-16 or beyond is dangerous)")
                elif expected_z is not None:
                    # Check against expected Z for this thickness
                    # IMPORTANT: A HIGHER Z value (less negative) is SAFER because it moves
                    # the tool FURTHER from the part. So:
                    #   - Z-10 is safe for Z-13 parts (tool goes further away)
                    #   - Z-8 is safe for Z-10, Z-11, Z-13 parts
                    #   - But Z-13 is NOT safe for Z-10 parts (tool would be too close)
                    # Only warn if z_value < expected_z (tool is closer than it should be)
                    if z_value < expected_z:
                        status = 'WARNING'
                        has_warning = True
                        issues.append(f"WARNING: Line {line_num} has Z{int(z_value)}, expected Z{int(expected_z)} or higher for {thickness}\" thick part")
                else:
                    # Unknown thickness range - flag for review
                    if thickness is not None:
                        status = 'UNKNOWN'
                        issues.append(f"REVIEW: Line {line_num} has Z{int(z_value)}, thickness {thickness}\" has no defined Z rule")

                found_positions.append({
                    'line_num': line_num,
                    'line': line_stripped,
                    'z_value': z_value,
                    'expected_z': expected_z,
                    'status': status
                })

        # Set overall status
        if has_critical:
            result.tool_home_status = 'CRITICAL'
        elif has_warning:
            result.tool_home_status = 'WARNING'
        elif found_positions:
            result.tool_home_status = 'PASS'
        else:
            result.tool_home_status = 'N/A'  # No G53 lines found

        result.tool_home_positions = found_positions
        result.tool_home_issues = issues

    def _validate_feasibility(self, result: GCodeParseResult):
        """
        Validate program feasibility against verification standards.

        Checks if program can physically run on assigned lathe:
        - Chuck capacity vs OD
        - Thickness range for lathe
        - Round size compatibility
        - Piece type compatibility
        - Physical constraints (drill depth, Z travel)

        This is separate from correctness validation - a program can be
        syntactically correct but physically impossible to run.
        """
        try:
            # Initialize feasibility validator
            validator = StandardsValidator()

            # Validate program feasibility
            validation_result = validator.validate_program_feasibility(result)

            # Store results in parse result
            result.feasibility_status = validation_result.status
            result.feasibility_issues = validation_result.critical_issues
            result.feasibility_warnings = validation_result.warnings

            # Optionally add recommendations to best practice suggestions
            if validation_result.recommendations:
                result.best_practice_suggestions.extend(validation_result.recommendations)

        except Exception as e:
            # If validation fails, set to UNKNOWN and log error
            result.feasibility_status = 'UNKNOWN'
            result.feasibility_issues = []
            result.feasibility_warnings = [f"Feasibility validation error: {str(e)}"]
            if self.debug:
                print(f"Error in feasibility validation: {e}")

    def _validate_crash_prevention(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate G-code for crash-prone patterns.

        CRITICAL SAFETY CHECKS:
        1. G00 rapid to negative Z (tool crashes into part)
        2. Diagonal rapid movements with negative Z
        3. Negative Z before tool home (redundant with tool_home validation)
        4. Jaw clearance violations

        Based on real-world crash analysis from shop floor.
        """
        try:
            # Initialize crash prevention validator
            crash_validator = CrashPreventionValidator()

            # Run all crash prevention checks
            crash_result = crash_validator.validate_all_crash_patterns(lines, result)

            # Store results in parse result
            result.crash_issues = crash_result['crash_issues']
            result.crash_warnings = crash_result['crash_warnings']

        except Exception as e:
            # If validation fails, log error but don't crash the parser
            result.crash_issues = []
            result.crash_warnings = [f"Crash prevention validation error: {str(e)}"]
            if self.debug:
                print(f"Error in crash prevention validation: {e}")

    def _validate_od_turndown(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate OD turn-down values match common practice standards.

        In T303 (TURN TOOL) operations, checks the X value immediately before
        cutting down the side (G01 Z-negative). This X value should match the
        standard OD turn-down for that round size.

        Adds warnings when actual values don't match standard practice.
        """
        try:
            # Skip if no round_size field (need to determine from outer_diameter)
            round_size = result.outer_diameter
            if not round_size:
                return

            # Run OD turn-down validation
            warnings, notes = self.od_validator.validate_file(lines, round_size)

            # Add warnings to validation_warnings (YELLOW)
            if warnings:
                result.validation_warnings.extend(warnings)

            # Add notes to detection_notes (informational)
            if notes:
                result.detection_notes.extend(notes)

        except Exception as e:
            # If validation fails, log error but don't crash the parser
            if self.debug:
                print(f"Error in OD turn-down validation: {e}")

    def _validate_hub_breakthrough(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate hub-centric parts for hub break-through risks during boring.

        Checks that boring operations don't go too deep and break through the hub
        material. Only applies to hub-centric parts where hub_diameter (OB) <= center_bore (CB).

        Key rule: Operations at or inside hub diameter (X <= hub) are bore cleanup
        and depth is unrestricted. Only operations OUTSIDE hub diameter need depth checks.
        """
        try:
            # Initialize validator
            hub_validator = HubBreakThroughValidator()

            # Check if validation applies to this part
            if not hub_validator.applies_to_part(
                result.spacer_type,
                result.hub_height,
                result.center_bore,
                result.hub_diameter
            ):
                return  # Skip validation for non-applicable parts

            # Run validation
            hub_result = hub_validator.validate_file(
                lines=lines,
                spacer_type=result.spacer_type,
                thickness=result.thickness,
                hub_height=result.hub_height,
                center_bore=result.center_bore,
                hub_diameter=result.hub_diameter
            )

            # Add critical issues (breaking through hub)
            if hub_result.critical_issues:
                result.validation_issues.extend(hub_result.critical_issues)

            # Add warnings (approaching limits)
            if hub_result.warnings:
                result.validation_warnings.extend(hub_result.warnings)

            # Add notes (proper practices observed)
            if hub_result.notes:
                result.detection_notes.extend(hub_result.notes)

        except Exception as e:
            # If validation fails, log error but don't crash the parser
            if self.debug:
                print(f"Error in hub breakthrough validation: {e}")

    def _validate_turning_depth(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate turning tool (T3xx) depth against production standards.

        Checks that turning tool operations don't exceed conservative depth limits
        based on part total height (body thickness + hub height). These are best-practice
        standards - warnings indicate deviation from standards but not necessarily danger.

        Absolute jaw clearance limits (thickness - 0.3") are enforced separately by
        crash_prevention_validator as CRITICAL issues.
        """
        try:
            # Need thickness for validation
            if not result.thickness or result.thickness <= 0:
                return

            # Initialize validator
            turning_validator = TurningToolDepthValidator()

            # Run validation
            turning_result = turning_validator.validate_file(
                lines=lines,
                thickness=result.thickness,
                hub_height=result.hub_height or 0.0,
                outer_diameter=result.outer_diameter or 0.0
            )

            # Add warnings (exceeding conservative standards)
            if turning_result.warnings:
                result.validation_warnings.extend(turning_result.warnings)

            # Add notes (following proper standards)
            if turning_result.notes:
                result.detection_notes.extend(turning_result.notes)

        except Exception as e:
            # If validation fails, log error but don't crash the parser
            if self.debug:
                print(f"Error in turning depth validation: {e}")

    def _validate_bore_chamfer_safety(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate Side 2 bore chamfer setup positioning to prevent hub crashes.

        CRITICAL SAFETY CHECK: When positioning for Side 2 chamfer/bore operations,
        the X value must be at the PRE-CHAMFER position (close to CB), NOT at or
        near OD.

        UNSAFE: G154 P16 G00 X8.445 Z0.0  ; At OD - CRASH RISK when moving inward!
        SAFE:   G154 P16 G00 X4.702 Z1.0  ; At pre-chamfer X (CB + margin)

        The danger: Positioning at OD with Z at/near part surface, then moving
        inward to CB causes the tool to crash into the hub material.
        """
        try:
            # Need OD and CB for validation
            if not result.outer_diameter or not result.center_bore:
                return

            # Initialize validator
            chamfer_validator = BoreChamferSafetyValidator()

            # For known equivalence pairs, use the actual G-code bore as the
            # CB reference so the chamfer safety boundary is accurate.
            effective_cb = _resolve_effective_cb(result.center_bore, result.cb_from_gcode)

            # Run validation
            chamfer_result = chamfer_validator.validate_file(
                lines=lines,
                outer_diameter=result.outer_diameter,
                center_bore=effective_cb,
                spacer_type=result.spacer_type
            )

            # Add critical issues (setup at OD - crash risk)
            if chamfer_result.critical_issues:
                result.validation_issues.extend(chamfer_result.critical_issues)

            # Add warnings (approaching OD)
            if chamfer_result.warnings:
                result.validation_warnings.extend(chamfer_result.warnings)

            # Add notes (proper pre-chamfer positioning)
            if chamfer_result.notes:
                result.detection_notes.extend(chamfer_result.notes)

        except Exception as e:
            # If validation fails, log error but don't crash the parser
            if self.debug:
                print(f"Error in bore chamfer safety validation: {e}")

    def _validate_counterbore_depth(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate counterbore depth for STEP parts.

        STEP spacers have two-stage boring:
        1. Counterbore: Wider, shallower hole (e.g., 60mm @ 0.75" deep)
        2. Center bore: Narrower, deeper hole (e.g., 54mm @ 2.0" deep)

        Validation checks:
        - CB depth < total thickness (critical)
        - CB depth in typical range (25-90% of thickness)
        - CB depth matches title specification (if present)
        """
        try:
            # Initialize validator
            cb_validator = CounterboreDepthValidator()

            # Check if validation applies
            if not cb_validator.applies_to_part(result.spacer_type):
                return

            # Need thickness for validation
            if not result.thickness or result.thickness <= 0:
                return

            # Run validation
            critical_issues, warnings = cb_validator.validate_file(
                lines=lines,
                spacer_type=result.spacer_type,
                thickness=result.thickness,
                title=result.title
            )

            # Add critical issues (CB depth exceeds thickness)
            if critical_issues:
                result.validation_issues.extend(critical_issues)

            # Add warnings (depth ratio issues, title mismatch)
            if warnings:
                result.validation_warnings.extend(warnings)

        except Exception as e:
            # If validation fails, log error but don't crash the parser
            if self.debug:
                print(f"Error in counterbore depth validation: {e}")

    def _validate_g154_presence(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate that every tool operation declares a work coordinate system
        (G154 P#, G54, G54.1 P#, or G55) within its first 5 code lines.

        Missing work offsets cause the tool to cut in whatever coordinate
        space was last active, which can produce wrong dimensions if the
        previous operation used a different fixture offset (P-code).

        Real-world catch: o73876 T121 (BORE) had no G154 P11 — it ran on
        the inherited P11 from the drill and happened to be correct, but
        the omission is a latent error for any file where fixture offsets
        differ between operations.
        """
        try:
            validator = G154PresenceValidator()
            errors, _ = validator.validate_file(lines)
            if errors:
                result.validation_warnings.extend(errors)
        except Exception as e:
            if self.debug:
                print(f"Error in G154 presence validation: {e}")

    def _validate_steel_ring_recess(self, result: GCodeParseResult):
        """
        Validate the Side-2 recess diameter for steel ring spacers.

        The recess bore must be 0.008"–0.010" smaller than the steel ring
        OD to create the required interference fit.  Recognised ring sizes:
        5.000", 5.250", 6.000", 6.500".

        Errors   → recess too tight (ring cannot be pressed in safely)
        Warnings → recess too loose (ring will not be retained)
        """
        try:
            validator = SteelRingRecessValidator()
            errors, warnings = validator.validate(
                result.spacer_type,
                result.counter_bore_diameter,
            )
            if errors:
                result.validation_issues.extend(errors)
            if warnings:
                result.validation_warnings.extend(warnings)
        except Exception as e:
            if self.debug:
                print(f"Error in steel ring recess validation: {e}")

    def _validate_2pc_ring_size(self, result: GCodeParseResult):
        """
        Validate the ring OD for 2-piece spacer programs.

        For each CB size class there is a standard ring (or small set of
        accepted rings) used to retain the STUD insert in the LUG half.

        Ring OD lives in:
          • counter_bore_diameter — step bore on LUG parts; inner hub on HC STUDs
          • hub_diameter           — hub OD on simple STUD parts (fallback)

        Warnings → detected ring OD does not match the lookup expectation.
        """
        try:
            validator = TwoPCRingSizeValidator()
            errors, warnings = validator.validate(
                spacer_type=result.spacer_type,
                center_bore_mm=result.center_bore,
                counter_bore_diameter_mm=result.counter_bore_diameter,
                hub_diameter_mm=result.hub_diameter,
                counter_bore_depth_in=result.counter_bore_depth,
            )
            if errors:
                result.validation_issues.extend(errors)
            if warnings:
                result.validation_warnings.extend(warnings)
        except Exception as e:
            if self.debug:
                print(f"Error in 2PC ring size validation: {e}")

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
        # SKIP for 2PC parts - their title dimensions refer to mating part interface, not actual bores
        # SKIP for steel_ring parts - title MM ID is steel ring dimension, not aluminum spacer CB
        if result.center_bore and result.cb_from_gcode and '2PC' not in result.spacer_type and result.spacer_type != 'steel_ring':
            title_cb = result.center_bore  # SPECIFICATION
            gcode_cb = result.cb_from_gcode  # IMPLEMENTATION

            # Skip comparison for known equivalent pairs (e.g. 116.7mm title
            # vs 116.9mm / X4.602 gcode — accepted machining convention).
            if _is_known_cb_equivalent(title_cb, gcode_cb):
                pass  # known pair — no mismatch check needed

            # Check if G-code is within acceptable range
            # Lower bound: title_cb - 0.25mm (critical threshold)
            # Upper bound: title_cb + 0.4mm (critical threshold)
            elif (diff := gcode_cb - title_cb) < -0.25:
                # CRITICAL: CB way too small - RED
                result.validation_issues.append(
                    f'CB TOO SMALL: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif diff > 0.4:
                # CRITICAL: CB way too large - RED
                result.validation_issues.append(
                    f'CB TOO LARGE: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm) - CRITICAL ERROR'
                )
            elif abs(diff) > 0.25:
                # BORE WARNING: At tolerance limit - ORANGE (only warn if >0.25mm off)
                result.bore_warnings.append(
                    f'CB at tolerance limit: Spec={title_cb:.1f}mm, G-code={gcode_cb:.1f}mm ({diff:+.2f}mm)'
                )

        # OB Validation: Title is SPEC, G-code should be within tolerance
        # Acceptable range: (title_ob - 0.2mm) to title_ob
        # SKIP for 2PC parts - their title dimensions refer to mating part interface, not actual bores
        if result.hub_diameter and result.ob_from_gcode and '2PC' not in result.spacer_type:
            title_ob = result.hub_diameter  # SPECIFICATION
            gcode_ob = result.ob_from_gcode  # IMPLEMENTATION

            # Sanity check: If extracted OB is close to the outer diameter, we likely extracted OD instead of OB
            # For hub-centric parts, OB should be much smaller than OD (OB is the hub recess, OD is the outer edge)
            od_mm = result.outer_diameter * 25.4 if result.outer_diameter else None
            if od_mm and abs(gcode_ob - od_mm) < 5.0:
                # Skip validation - extracted OB is actually the OD
                result.validation_warnings.append(
                    f'OB extraction uncertain: extracted {gcode_ob:.1f}mm matches OD, skipping OB validation'
                )
            else:
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
                        f'OB TOO LARGE: Spec={title_ob:.1f}mm, G-code={gcode_ob:.1f}mm) - CRITICAL ERROR'
                    )
                elif abs(diff) > 0.25:
                    # BORE WARNING: At tolerance limit - ORANGE (only warn if >0.25mm off)
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
                # 2PC parts: Many have unstated hub height (0.25" typical for LUG/STUD)
                # Pattern: Title shows body thickness, drill = body + hub + 0.15" breach
                # If hub_height in title: use it directly
                # If hub NOT in title: check if drill suggests unstated hub
                title_upper = result.title.upper() if result.title else ''

                # First check if hub_height was extracted from title
                if result.hub_height:
                    # Hub height detected - use it
                    hub_h = result.hub_height
                    calculated_thickness = result.drill_depth - hub_h - 0.15

                    # 2PC mating-hub false-positive suppression:
                    # On 2PC parts the mating hub (0.20-0.35") is NOT included in the title
                    # thickness. When the programmer drills through the full part height
                    # (body + hub + extra safety clearance), the formula above yields
                    # calc ≈ title_thickness + hub_h instead of title_thickness.
                    # Detect that pattern and revert to title thickness.
                    is_small_mating_hub = 0.20 <= hub_h <= 0.35
                    if is_small_mating_hub and abs(calculated_thickness - (title_thickness + hub_h)) < 0.15:
                        calculated_thickness = title_thickness

                    # 2PC HC STUD false-positive suppression for large stated hubs (≥ 0.35"):
                    # These parts (e.g. 0.75" body + 0.50" HC hub) are drilled through the
                    # full part height with variable extra clearance (0.15-0.40").
                    # Formula gives: calc = drill - hub_h - 0.15 = body + extra_clearance
                    # Extra clearance of 0.25" → calc = body + 0.25" → false TITLE MISLABELED.
                    # Rule: if calc is within 0-0.30" above title_thickness, trust the title.
                    is_large_stated_hub = hub_h >= 0.35
                    if is_large_stated_hub and 0 <= (calculated_thickness - title_thickness) < 0.30:
                        calculated_thickness = title_thickness
                else:
                    # No hub in title - check if drill pattern suggests unstated hub
                    # Calculate implied hub from drill depth
                    implied_hub = result.drill_depth - title_thickness - 0.15

                    # 2PC Unstated Hub Pattern Detection:
                    # Many 2PC parts (LUG, STUD, UNSURE) have hub not stated in title
                    # Typical hub range: 0.15-0.35" (most common is 0.25")
                    # Accept ANY 2PC with implied hub in this range

                    # Check if implied hub is in typical 2PC range (0.15-0.35")
                    is_valid_2pc_hub = 0.15 <= implied_hub <= 0.35

                    if is_valid_2pc_hub:
                        # 2PC with unstated hub: title thickness is correct, drill includes hub
                        calculated_thickness = title_thickness
                        # Populate hub_height with calculated value; snap to standard sizes
                        h = implied_hub
                        if 0.20 <= h <= 0.27:
                            h = 0.25
                        elif 0.45 <= h < 0.50:
                            h = 0.50
                        result.hub_height = h
                    else:
                        # Not a recognized 2PC hub pattern - standard 2PC calculation
                        calculated_thickness = result.drill_depth - 0.15
            elif result.spacer_type == 'steel_ring':
                # STEEL RING Unstated Hub Pattern:
                # Some steel rings have unstated 0.25" hub machined in OP2
                # Pattern: Title shows body thickness, drill = body + hub + 0.15" breach
                # Similar to 2PC STUD rule

                # Calculate implied hub from drill depth
                implied_hub = result.drill_depth - title_thickness - 0.15

                # Steel ring typical unstated hub: 0.20-0.30" (most common is 0.25")
                # More strict range than 2PC since this is a specific pattern
                is_valid_steel_hub = 0.20 <= implied_hub <= 0.30

                if is_valid_steel_hub:
                    # Steel ring with unstated hub: title thickness is correct, drill includes hub
                    calculated_thickness = title_thickness
                    # Populate hub_height with calculated value
                    result.hub_height = implied_hub
                else:
                    # Not unstated hub pattern - standard steel ring calculation
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
                    # CRITICAL FIX: P-code represents TOTAL height for ALL part types
                    # For hub-centric: Compare P-code total against (body + hub)
                    # For standard: Compare P-code total against body thickness
                    for pcode in result.pcodes_found:
                        if pcode in pcode_map:
                            pcode_total_height = pcode_map[pcode]

                            # Calculate expected total height from drill
                            if result.spacer_type == 'hub_centric':
                                # For hub-centric: P-code should match drill total (drill - 0.15")
                                # NOT body thickness alone
                                hub_h = result.hub_height if result.hub_height else 0.50
                                expected_total_from_drill = result.drill_depth - 0.15

                                # If P-code total matches drill total (within 0.02")
                                if abs(pcode_total_height - expected_total_from_drill) < 0.02:
                                    pcode_agrees_with_drill = True
                                    break
                            else:
                                # For standard/2PC: P-code = body thickness
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
                    # For hub-centric, show total heights for clarity
                    if result.spacer_type == 'hub_centric':
                        hub_h = result.hub_height if result.hub_height else 0.50
                        title_total = title_thickness + hub_h
                        drilled_total = result.drill_depth - 0.15
                        result.validation_issues.append(
                            f'THICKNESS ERROR: Title={title_thickness:.2f}"+{hub_h:.2f}"hub={title_total:.2f}"total, Drilled={drilled_total:.2f}"total (thickness={calculated_thickness:.2f}") ({diff:+.3f}") - CRITICAL ERROR'
                        )
                    else:
                        result.validation_issues.append(
                            f'THICKNESS ERROR: Spec={title_thickness:.2f}", Calculated from drill={calculated_thickness:.2f}" ({diff:+.3f}") - CRITICAL ERROR'
                        )
            elif abs(diff) > warning_tolerance:  # Warning zone
                # DIMENSIONAL: Thickness mismatch - PURPLE
                # For hub-centric, show total heights for clarity
                if result.spacer_type == 'hub_centric':
                    hub_h = result.hub_height if result.hub_height else 0.50
                    title_total = title_thickness + hub_h
                    drilled_total = result.drill_depth - 0.15
                    result.dimensional_issues.append(
                        f'Thickness mismatch: Title={title_thickness:.2f}"+{hub_h:.2f}"hub={title_total:.2f}"total, Drilled={drilled_total:.2f}"total ({diff:+.3f}")'
                    )
                else:
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
            # CRITICAL FIX: Increased small parts warning tolerance from 0.05" to 0.15"
            # User specification: "allow special od pass if the od is working 0.15 tolerance"
            if title_od >= 10.0:
                error_tolerance = 0.25  # Large parts: ±0.25"
                warning_tolerance = 0.15  # Warning zone: ±0.15-0.25"
            else:
                error_tolerance = 0.1  # Small parts: ±0.1"
                warning_tolerance = 0.15  # Warning zone: ±0.15-0.1" (relaxed from 0.05")

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
                # For hub-centric, P-code = thickness + actual hub_height (not fixed 0.50")
                # CRITICAL FIX: Use actual hub height from title, not fixed value
                if result.spacer_type == 'hub_centric':
                    hub_h = result.hub_height if result.hub_height else 0.50
                    total_height = result.thickness + hub_h
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
                            # CRITICAL FIX: For hub-centric, compare TOTAL heights, not body thickness
                            pcode_total = None
                            for p in actual_pcodes:
                                if p in pcode_map:
                                    pcode_total = pcode_map[p]  # P-code is ALWAYS total height
                                    break

                            drill_total = None
                            if result.drill_depth:
                                drill_total = result.drill_depth - 0.15  # Drill total = drill - clearance

                            # For hub-centric, 2PC with hub, and steel_ring with hub, calculate expected total from title
                            # CRITICAL FIX: 2PC and steel_ring parts can have unstated hubs (e.g., 0.75" 2PC STUD with 0.25" hub)
                            if result.spacer_type == 'hub_centric':
                                hub_h = result.hub_height if result.hub_height else 0.50
                                title_total = result.thickness + hub_h
                            elif result.spacer_type in ('2PC LUG', '2PC STUD', '2PC UNSURE') and result.hub_height:
                                # 2PC with detected hub - title shows body, total = body + hub
                                title_total = result.thickness + result.hub_height
                            elif result.spacer_type == 'steel_ring' and result.hub_height:
                                # Steel ring with detected unstated hub - title shows body, total = body + hub
                                title_total = result.thickness + result.hub_height
                            else:
                                title_total = result.thickness

                            # Check if P-code and drill depth agree (within 0.02")
                            if pcode_total and drill_total:
                                if abs(pcode_total - drill_total) < 0.02:
                                    # Both agree! Check if title matches
                                    if abs(title_total - pcode_total) > 0.02:
                                        # Title is mislabeled
                                        if result.spacer_type == 'hub_centric':
                                            hub_h = result.hub_height if result.hub_height else 0.50
                                            result.dimensional_issues.append(
                                                f'TITLE MISLABELED: Title says {result.thickness}"+{hub_h}"hub={title_total:.2f}"total but P-code ({actual_desc}) and drill depth ({drill_total:.2f}"total) both indicate {pcode_total:.2f}"total - TITLE NEEDS CORRECTION'
                                            )
                                        elif result.spacer_type in ('2PC LUG', '2PC STUD', '2PC UNSURE') and result.hub_height:
                                            # 2PC with hub - show hub in error message
                                            result.dimensional_issues.append(
                                                f'TITLE MISLABELED: Title says {result.thickness}"+{result.hub_height:.2f}"hub={title_total:.2f}"total but P-code ({actual_desc}) and drill depth ({drill_total:.2f}"total) both indicate {pcode_total:.2f}"total - TITLE NEEDS CORRECTION'
                                            )
                                        elif result.spacer_type == 'steel_ring' and result.hub_height:
                                            # Steel ring with unstated hub - show hub in error message
                                            result.dimensional_issues.append(
                                                f'TITLE MISLABELED: Title says {result.thickness}"+{result.hub_height:.2f}"unstated hub={title_total:.2f}"total but P-code ({actual_desc}) and drill depth ({drill_total:.2f}"total) both indicate {pcode_total:.2f}"total - TITLE NEEDS CORRECTION'
                                            )
                                        else:
                                            result.dimensional_issues.append(
                                                f'TITLE MISLABELED: Title says {result.thickness}" but P-code ({actual_desc}) and drill depth ({drill_total:.2f}") both indicate {pcode_total:.2f}" - TITLE NEEDS CORRECTION'
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

    def _validate_haas_gcode_patterns(self, result: GCodeParseResult, lines: List[str]):
        """
        Validate Haas lathe-specific G-code patterns and common errors.

        Checks for:
        1. G00/G01 mixing on same line
        2. G01 without feedrate (F word)
        3. G96 (CSS) without G50 (max RPM limit)
        4. M-code sequence (M03 before M08, M09 before M05)
        5. Missing decimal points on coordinates and feedrates
        """
        if not lines:
            return

        # Track modal states
        current_feedrate = None  # Last F word seen
        g50_seen = False  # Has G50 been set before G96?
        g96_active = False  # Is CSS mode active?
        spindle_running = False  # M03/M04 seen
        coolant_on = False  # M08 seen

        issues = []
        warnings = []
        suggestions = []  # Best practice suggestions (don't affect PASS status)

        for line_num, line in enumerate(lines, 1):
            # Clean line - remove comments and whitespace
            clean_line = re.sub(r'\(.*?\)', '', line).strip().upper()
            if not clean_line:
                continue

            # === CHECK 1: G00/G01 mixing ===
            if 'G00' in clean_line and 'G01' in clean_line:
                issues.append(
                    f'Line {line_num}: G00 and G01 on same line - "{line.strip()}"'
                )

            # === CHECK 2: G01 without feedrate ===
            # Check if G01 is present (but not G00, G02, G03, etc.)
            # Use word boundary to match G01 or G1 (standalone, not part of other codes)
            has_g01 = bool(re.search(r'\bG0?1\b', clean_line))

            if has_g01:
                # Update feedrate if F word is present
                f_match = re.search(r'F(\d+\.?\d*)', clean_line)
                if f_match:
                    current_feedrate = float(f_match.group(1))
                # Check if feedrate is established
                elif current_feedrate is None:
                    issues.append(
                        f'Line {line_num}: G01 without feedrate (no F word) - "{line.strip()}"'
                    )

            # === CHECK 3: G96 without G50 ===
            # Track G50 (max RPM limit)
            if 'G50' in clean_line:
                g50_seen = True
                g96_active = False  # Reset CSS mode when new G50 is set

            # Track G96 (CSS mode)
            if 'G96' in clean_line:
                if not g50_seen:
                    issues.append(
                        f'Line {line_num}: G96 (CSS) without prior G50 (max RPM) - "{line.strip()}"'
                    )
                g96_active = True

            # Track G97 (RPM mode - exits CSS)
            if 'G97' in clean_line:
                g96_active = False

            # === CHECK 4: M-code sequence validation ===
            # M03/M04: Spindle start
            if 'M03' in clean_line or 'M04' in clean_line:
                spindle_running = True
                # Reset coolant state (new operation)
                coolant_on = False

            # M08: Coolant on
            if 'M08' in clean_line:
                if not spindle_running:
                    warnings.append(
                        f'Line {line_num}: M08 (coolant on) before spindle started (M03/M04) - "{line.strip()}"'
                    )
                coolant_on = True

            # M09: Coolant off
            if 'M09' in clean_line:
                coolant_on = False

            # M05: Spindle stop
            if 'M05' in clean_line:
                if coolant_on:
                    warnings.append(
                        f'Line {line_num}: M05 (spindle stop) while coolant still on (M08) - should M09 first - "{line.strip()}"'
                    )
                spindle_running = False

            # M30/M02: Program end
            # Note: M30/M02 automatically turns off coolant, so M09 is optional (best practice)
            if 'M30' in clean_line or 'M02' in clean_line:
                if coolant_on:
                    suggestions.append(
                        f'Line {line_num}: Best practice - add M09 before M30/M02 (M30 turns off coolant automatically, but explicit M09 is clearer)'
                    )

            # === CHECK 5: Missing decimal points ===
            # Check X and Z coordinates for missing decimals (e.g., "X3" should be "X3.0", "X10" should be "X10.0")
            # Only check on G00/G01 lines (movement commands)
            # SPECIAL CASE: X0 and Z0 are suggestions (common and unambiguous), others are critical errors
            if 'G00' in clean_line or 'G01' in clean_line or 'G0' in clean_line or 'G1' in clean_line:
                # Check X coordinates - any number of digits without decimal
                # Matches: X0, X1, X10, X100 but NOT X1.0, X10.5
                x_matches = re.findall(r'X(-?\d+)(?![.\d])', clean_line)
                for x_val in x_matches:
                    # X0 is a suggestion (common practice, functionally identical)
                    if x_val == '0' or x_val == '-0':
                        suggestions.append(
                            f'Line {line_num}: Best practice - add decimal to X0 (X0.0 is clearer, though functionally identical)'
                        )
                    else:
                        # X1, X10, etc. are critical errors (ambiguous, could be typos)
                        issues.append(
                            f'Line {line_num}: X coordinate missing decimal point - "X{x_val}" should be "X{x_val}.0" - "{line.strip()}"'
                        )

                # Check Z coordinates - any number of digits without decimal
                # Matches: Z0, Z1, Z10, Z100 but NOT Z1.0, Z10.5
                z_matches = re.findall(r'Z(-?\d+)(?![.\d])', clean_line)
                for z_val in z_matches:
                    # Z0 is a suggestion (common practice, functionally identical)
                    if z_val == '0' or z_val == '-0':
                        suggestions.append(
                            f'Line {line_num}: Best practice - add decimal to Z0 (Z0.0 is clearer, though functionally identical)'
                        )
                    else:
                        # Z1, Z10, etc. are critical errors (ambiguous, could be typos)
                        issues.append(
                            f'Line {line_num}: Z coordinate missing decimal point - "Z{z_val}" should be "Z{z_val}.0" - "{line.strip()}"'
                        )

            # Check feedrates for missing decimals (less critical, but good practice)
            # F008 should be F0.008
            f_no_decimal = re.search(r'F(\d{3,})(?!\.)', clean_line)
            if f_no_decimal:
                f_val = f_no_decimal.group(1)
                # Only flag if it's 3+ digits without decimal (likely missing decimal)
                warnings.append(
                    f'Line {line_num}: Feed rate missing decimal point - "F{f_val}" (should be F0.{f_val}?) - "{line.strip()}"'
                )

        # Add issues, warnings, and suggestions to result
        if issues:
            result.validation_issues.extend(issues)
        if warnings:
            result.validation_warnings.extend(warnings)
        if suggestions:
            result.best_practice_suggestions.extend(suggestions)

    def _extract_tools(self, result: GCodeParseResult, lines: List[str]):
        """
        Extract all tool numbers used in the G-code and their sequence.

        Populates:
        - result.tools_used: Unique list of all tools (e.g., ["T101", "T121", "T202"])
        - result.tool_sequence: Ordered list showing tool usage sequence
        """
        tools_set = set()
        tool_sequence = []

        for line in lines:
            # Match tool calls: T101, T121, etc.
            # Look for T followed by digits
            tool_match = re.search(r'\bT(\d{3})\b', line, re.IGNORECASE)
            if tool_match:
                tool_num = f"T{tool_match.group(1)}"
                tools_set.add(tool_num)

                # Add to sequence (avoid consecutive duplicates)
                if not tool_sequence or tool_sequence[-1] != tool_num:
                    tool_sequence.append(tool_num)

        result.tools_used = sorted(list(tools_set))
        result.tool_sequence = tool_sequence

    # DISABLED - Tool validation temporarily disabled (needs tuning)
    # Uncomment this entire method to re-enable tool validation
    # def _validate_tools(self, result: GCodeParseResult):
    #     """
    #     Validate tool usage based on part type, size, and operations.
    #
    #     Checks for:
    #     - Expected tool numbers for specific operations
    #     - Tool sequence appropriateness
    #     - Missing critical tools
    #     """
    #     if not result.tools_used:
    #         result.tool_validation_status = 'WARNING'
    #         result.tool_validation_issues.append('No tools detected in G-code')
    #         return
    #
    #     issues = []
    #
    #     # Common tool expectations for spacer parts
    #     common_tools = {
    #         'T101': 'Face/Turn',  # Facing/Turning
    #         'T121': 'Bore',       # Boring
    #         'T202': 'Drill',      # Drilling
    #         'T303': 'Tap',        # Tapping
    #         'T404': 'Groove'      # Grooving
    #     }
    #
    #     # Check for hub-centric parts - should have boring tool (T121)
    #     if result.spacer_type == 'hub_centric' and result.hub_height:
    #         if 'T121' not in result.tools_used:
    #             issues.append('Hub-centric part missing boring tool (T121)')
    #
    #     # Check for STEP parts - should have both facing and boring
    #     if result.spacer_type == 'step':
    #         if 'T101' not in result.tools_used:
    #             issues.append('STEP part missing facing tool (T101)')
    #         if 'T121' not in result.tools_used:
    #             issues.append('STEP part missing boring tool (T121)')
    #
    #     # Check for drilling operation if drill_depth is detected
    #     if result.drill_depth and 'T202' not in result.tools_used:
    #         issues.append(f'Drill depth {result.drill_depth:.2f}" detected but no drill tool (T202)')
    #
    #     # Update validation status
    #     if issues:
    #         result.tool_validation_status = 'WARNING'
    #         result.tool_validation_issues = issues
    #     else:
    #         result.tool_validation_status = 'PASS'

    # DISABLED - Safety block validation temporarily disabled (needs tuning)
    # Uncomment this entire method to re-enable safety validation
    # def _validate_safety_blocks(self, result: GCodeParseResult, lines: List[str]):
    #     """
    #     Validate presence of critical safety blocks in G-code.
    #
    #     Checks for:
    #     - G28 (Return to home position)
    #     - G54/G55 (Work coordinate system)
    #     - M01 (Optional stop)
    #     - M30 (Program end)
    #     - Spindle stop commands
    #     """
    #     issues = []
    #
    #     # Join all lines for searching
    #     all_code = '\n'.join(lines).upper()
    #
    #     # Check for home position (G28)
    #     if 'G28' not in all_code:
    #         issues.append('Missing G28 (return to home position)')
    #
    #     # Check for work coordinate system (G54, G55, G56, etc.)
    #     if not re.search(r'G5[4-9]', all_code):
    #         issues.append('Missing work coordinate system (G54/G55/G56)')
    #
    #     # Check for program end (M30 or M02)
    #     if 'M30' not in all_code and 'M02' not in all_code:
    #         issues.append('Missing program end (M30 or M02)')
    #
    #     # Check for spindle commands (M03/M04 for start, M05 for stop)
    #     has_spindle_start = 'M03' in all_code or 'M04' in all_code
    #     has_spindle_stop = 'M05' in all_code
    #
    #     if has_spindle_start and not has_spindle_stop:
    #         issues.append('Spindle started (M03/M04) but not stopped (M05)')
    #
    #     # Update safety status
    #     if issues:
    #         result.safety_blocks_status = 'MISSING'
    #         result.safety_blocks_issues = issues
    #     elif not has_spindle_start:
    #         # No spindle commands at all - might be a warning
    #         result.safety_blocks_status = 'WARNING'
    #         result.safety_blocks_issues = ['No spindle commands detected (M03/M04/M05)']
    #     else:
    #         result.safety_blocks_status = 'PASS'


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
