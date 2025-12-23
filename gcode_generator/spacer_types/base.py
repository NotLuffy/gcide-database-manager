"""
Base Spacer Generator

Abstract base class that all spacer type generators inherit from.
Provides common functionality and defines the interface that each
spacer type must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SpacerDimensions:
    """Common dimensions for all spacer types."""
    # Program identification
    program_number: str

    # Basic dimensions
    round_size: float  # OD of round stock in inches
    thickness_inches: float  # Part thickness in inches
    thickness_key: str  # Key for lookup tables (e.g., "1.50" or "15MM")

    # Center bore (all spacers have this)
    cb_mm: float  # Center bore in mm (as specified)
    cb_mm_adjusted: float  # CB with tolerance applied
    cb_inches: float  # CB in inches (with tolerance)

    # Machine settings
    lathe: str  # "L1", "L2", or "L3"

    # Options
    use_tolerance: bool = True
    use_calculated_feeds: bool = False


@dataclass
class HubCentricDimensions(SpacerDimensions):
    """Additional dimensions for hub-centric spacers."""
    ob_mm: float = 0.0  # Outer bore/diameter in mm
    ob_mm_adjusted: float = 0.0  # OB with tolerance
    ob_inches: float = 0.0  # OB in inches
    hub_height_inches: float = 0.0  # Hub projection height


@dataclass
class StepSpacerDimensions(SpacerDimensions):
    """Additional dimensions for STEP spacers."""
    counterbore_mm: float = 0.0  # Counterbore diameter in mm
    counterbore_mm_adjusted: float = 0.0
    counterbore_inches: float = 0.0
    step_depth_inches: float = 0.0  # Depth of the step/shelf


@dataclass
class TwoPieceDimensions(SpacerDimensions):
    """
    Additional dimensions for 2-Piece spacers (both LUG and STUD).

    2PC spacers can have various combinations:
    - CB (center bore) - always present
    - OB + hub pocket (hub-centric style, 0.25" typical)
    - Counterbore + recess (lug pocket style, 0.31" typical)

    The specific 2PC type (LUG vs STUD) determines which features are used,
    but both can support all options.
    """
    # Hub-centric style features (OB + hub pocket)
    ob_mm: float = 0.0  # Outer bore/hub diameter in mm
    ob_mm_adjusted: float = 0.0
    ob_inches: float = 0.0
    hub_height_inches: float = 0.25  # Hub pocket depth (0.25" typical)

    # Lug pocket style features (counterbore + recess)
    counterbore_mm: float = 0.0  # Counterbore/recess diameter in mm
    counterbore_mm_adjusted: float = 0.0
    counterbore_inches: float = 0.0
    recess_depth_inches: float = 0.31  # Recess depth (0.31" typical)


# Aliases for backwards compatibility
TwoPieceLugDimensions = TwoPieceDimensions
TwoPieceStudDimensions = TwoPieceDimensions


@dataclass
class GCodeSection:
    """Represents a section of G-code with metadata."""
    name: str
    lines: List[str] = field(default_factory=list)
    operation: str = ""  # "op1" or "op2"
    tool: str = ""  # Tool name


class BaseSpacerGenerator(ABC):
    """
    Abstract base class for all spacer type generators.

    Each spacer type (Standard, Hub-Centric, Thin-Lip, STEP, Steel Ring, 2-Piece)
    must inherit from this class and implement the abstract methods.
    """

    # Tolerance values (mm)
    CB_TOLERANCE = 0.1  # Add to CB (makes hole slightly larger)
    OB_TOLERANCE = -0.1  # Subtract from OB/OD (makes diameter slightly smaller)

    def __init__(self, dimensions: SpacerDimensions):
        """
        Initialize the generator with part dimensions.

        Args:
            dimensions: SpacerDimensions dataclass with all part parameters
        """
        self.dimensions = dimensions
        self.gcode_lines: List[str] = []
        self.sections: List[GCodeSection] = []

    @staticmethod
    def mm_to_inches(mm_value: float) -> float:
        """Convert millimeters to inches with 4 decimal places."""
        return round(mm_value / 25.4, 4)

    @staticmethod
    def inches_to_mm(inch_value: float) -> float:
        """Convert inches to millimeters."""
        return round(inch_value * 25.4, 2)

    @staticmethod
    def format_gcode_value(value: float, max_decimals: int = 4) -> str:
        """
        Format a numeric value for G-code output.

        - Removes trailing zeros
        - Ensures decimal point for coordinates (G-code convention)
        - Max 4 decimal places for machine compatibility

        Args:
            value: Numeric value to format
            max_decimals: Maximum decimal places

        Returns:
            Formatted string like "1.5" or "0." or "-0.15"
        """
        if value == 0:
            return "0."

        # Round to max decimals
        rounded = round(value, max_decimals)

        # Format and remove trailing zeros
        formatted = f"{rounded:.{max_decimals}f}".rstrip('0').rstrip('.')

        # Ensure there's at least a decimal point (G-code convention)
        if '.' not in formatted:
            formatted += '.'

        return formatted

    @classmethod
    def apply_tolerance(cls, value_mm: float, is_cb: bool = True) -> float:
        """
        Apply tolerance to a dimension.

        - CB (Center Bore): add 0.1mm (hole is slightly larger)
        - OB/OD (Outer Bore/Diameter): subtract 0.1mm (diameter is slightly smaller)

        Args:
            value_mm: Original value in millimeters
            is_cb: True for center bore, False for outer bore/diameter

        Returns:
            Adjusted value in millimeters
        """
        if is_cb:
            return value_mm + cls.CB_TOLERANCE
        else:
            return value_mm + cls.OB_TOLERANCE  # OB_TOLERANCE is negative

    def add_line(self, line: str) -> None:
        """Add a single line to the G-code output."""
        self.gcode_lines.append(line)

    def add_lines(self, lines: List[str]) -> None:
        """Add multiple lines to the G-code output."""
        self.gcode_lines.extend(lines)

    def add_blank_lines(self, count: int = 1) -> None:
        """Add blank lines for readability."""
        for _ in range(count):
            self.gcode_lines.append("")

    def add_comment(self, comment: str) -> None:
        """Add a comment line."""
        self.gcode_lines.append(f"({comment})")

    def add_section_header(self, title: str) -> None:
        """Add a section header with dividers."""
        self.add_blank_lines(1)
        self.add_line("(---------------------------)")
        self.add_comment(title)
        self.add_line("(---------------------------)")

    # =========================================================================
    # Abstract Methods - Must be implemented by each spacer type
    # =========================================================================

    @abstractmethod
    def generate_header(self) -> List[str]:
        """
        Generate the program header with description.

        Returns:
            List of G-code lines for the header
        """
        pass

    @abstractmethod
    def generate_op1_drilling(self) -> Tuple[List[str], float]:
        """
        Generate OP1 drilling operation.

        Returns:
            Tuple of (G-code lines, drill_depth)
        """
        pass

    @abstractmethod
    def generate_op1_boring(self, drill_depth: float) -> List[str]:
        """
        Generate OP1 boring operation.

        Args:
            drill_depth: Depth from drilling operation (negative value)

        Returns:
            List of G-code lines
        """
        pass

    @abstractmethod
    def generate_op1_turning(self) -> List[str]:
        """
        Generate OP1 outer profile turning operation.

        Returns:
            List of G-code lines
        """
        pass

    @abstractmethod
    def generate_op2_turning(self) -> List[str]:
        """
        Generate OP2 turning/facing operation.

        Returns:
            List of G-code lines
        """
        pass

    @abstractmethod
    def generate_op2_chamfer(self) -> List[str]:
        """
        Generate OP2 chamfer bore operation.

        Returns:
            List of G-code lines
        """
        pass

    @abstractmethod
    def generate_footer(self) -> List[str]:
        """
        Generate program footer.

        Returns:
            List of G-code lines
        """
        pass

    # =========================================================================
    # Common Implementation Methods
    # =========================================================================

    def generate_common_header(self) -> List[str]:
        """Generate common header elements used by all spacer types."""
        lines = [
            "%",
            # Program line is added by specific implementation
        ]
        return lines

    def generate_common_footer(self) -> List[str]:
        """Generate common footer elements."""
        return [
            "",
            "M30 (End program and reset)",
            "%"
        ]

    # =========================================================================
    # Lathe-Specific Tool Change Positions
    # =========================================================================
    # L1: X-11, Z-11 (uses P11/P12, P21/P22, P25/P26, P29/P30, P31/P32)
    # L2: X-11, Z-13 (uses P13/P14, P15/P16, P17/P18, P23/P24) - some use X-10
    # L3: X-6, Z-10  (uses P3-P10, larger diameter machine)

    TOOL_CHANGE_POSITIONS = {
        "L1": {"x": -11, "z": -11},
        "L2": {"x": -11, "z": -13},
        "L3": {"x": -6, "z": -10},
    }

    def get_tool_change_position(self) -> tuple:
        """Get the tool change X, Z position for the current lathe."""
        lathe = self.dimensions.lathe
        pos = self.TOOL_CHANGE_POSITIONS.get(lathe, {"x": -11, "z": -13})
        return (pos["x"], pos["z"])

    def generate_home_position(self) -> str:
        """Generate home position command based on lathe."""
        x, z = self.get_tool_change_position()
        return f"G00 G53 X{x}. Z{z}."

    def generate_tool_change_position(self) -> str:
        """Generate tool change position command based on lathe."""
        x, z = self.get_tool_change_position()
        return f"G00 G53 X{x}. Z{z}. (TOOL CHANGE POS.)"

    def generate_flip_part_section(self) -> List[str]:
        """Generate the flip part operator instructions."""
        return [
            "",
            "(---------------------------)",
            "(OP2: FLIP PART)",
            "(---------------------------)",
            "(REMOVE & CLEAN JAWS)",
            "(FLIP PART)",
            "/ M00 (Stop for operator to flip part)",
            "(IS PART FLIPPED?) (Operator check)",
            "",
            "M00 (Wait for confirmation)",
        ]

    # =========================================================================
    # Main Generation Method
    # =========================================================================

    def generate(self) -> str:
        """
        Generate the complete G-code program.

        Calls each abstract method in order and combines the output.

        Returns:
            Complete G-code program as a string
        """
        self.gcode_lines = []

        # Generate each section
        header = self.generate_header()
        self.add_lines(header)

        drilling, drill_depth = self.generate_op1_drilling()
        self.add_lines(drilling)

        boring = self.generate_op1_boring(drill_depth)
        self.add_lines(boring)

        turning = self.generate_op1_turning()
        self.add_lines(turning)

        op2_turning = self.generate_op2_turning()
        self.add_lines(op2_turning)

        op2_chamfer = self.generate_op2_chamfer()
        self.add_lines(op2_chamfer)

        footer = self.generate_footer()
        self.add_lines(footer)

        return "\n".join(self.gcode_lines)

    def get_gcode(self) -> str:
        """Get the generated G-code (generates if not already done)."""
        if not self.gcode_lines:
            return self.generate()
        return "\n".join(self.gcode_lines)

    def save(self, filepath: str) -> str:
        """
        Save the generated G-code to a file.

        Args:
            filepath: Path to save the file

        Returns:
            Path where file was saved
        """
        gcode = self.get_gcode()

        # Convert to ASCII for machine compatibility
        gcode_ascii = gcode.encode('ascii', 'replace').decode('ascii')

        with open(filepath, 'w', encoding='ascii') as f:
            f.write(gcode_ascii)

        return filepath

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_spacer_type_name(self) -> str:
        """Get the human-readable name of this spacer type."""
        return self.__class__.__name__.replace("SpacerGenerator", "").replace("Generator", "")

    def validate_dimensions(self) -> Tuple[bool, List[str]]:
        """
        Validate that all required dimensions are present and valid.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        dim = self.dimensions

        if dim.round_size <= 0:
            errors.append("Round size must be positive")

        if dim.thickness_inches <= 0:
            errors.append("Thickness must be positive")

        if dim.cb_inches <= 0:
            errors.append("Center bore must be positive")

        if dim.cb_inches >= dim.round_size:
            errors.append("Center bore cannot be larger than round size")

        if dim.lathe not in ["L1", "L2", "L3"]:
            errors.append(f"Invalid lathe '{dim.lathe}'. Must be L1, L2, or L3")

        return (len(errors) == 0, errors)
