"""
Main G-Code Generator

The central orchestrator that:
1. Accepts part parameters
2. Selects appropriate spacer type generator
3. Optionally uses template matching for hybrid generation
4. Produces validated G-code output
"""

import os
import sys
from typing import Dict, Optional, Tuple, Type, Union
from enum import Enum

# Handle both direct execution and module import
if __name__ == "__main__" or __package__ is None:
    # Running directly - add parent to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from gcode_generator.spacer_types.base import (
        BaseSpacerGenerator,
        SpacerDimensions,
        HubCentricDimensions,
        StepSpacerDimensions,
    )
    from gcode_generator.spacer_types.standard import StandardSpacerGenerator
    from gcode_generator.spacer_types.hub_centric import HubCentricSpacerGenerator
    from gcode_generator.spacer_types.thin_lip import ThinLipSpacerGenerator
    from gcode_generator.spacer_types.step import StepSpacerGenerator
    from gcode_generator.spacer_types.steel_ring import SteelRingSpacerGenerator
    from gcode_generator.spacer_types.two_piece import TwoPieceSpacerGenerator
    from gcode_generator.templates.template_matcher import TemplateMatcher
    from gcode_generator.rules.lathe_config import LatheConfig
else:
    # Running as module
    from .spacer_types.base import (
        BaseSpacerGenerator,
        SpacerDimensions,
        HubCentricDimensions,
        StepSpacerDimensions,
    )
    from .spacer_types.standard import StandardSpacerGenerator
    from .spacer_types.hub_centric import HubCentricSpacerGenerator
    from .spacer_types.thin_lip import ThinLipSpacerGenerator
    from .spacer_types.step import StepSpacerGenerator
    from .spacer_types.steel_ring import SteelRingSpacerGenerator
    from .spacer_types.two_piece import TwoPieceSpacerGenerator
    from .templates.template_matcher import TemplateMatcher
    from .rules.lathe_config import LatheConfig


class SpacerType(Enum):
    """Enum of supported spacer types."""
    STANDARD = "standard"
    HUB_CENTRIC = "hub_centric"
    THIN_LIP = "thin_lip"
    STEP = "step"
    STEEL_RING = "steel_ring"
    TWO_PIECE = "two_piece"


class GCodeGenerator:
    """
    Main G-Code Generator class.

    Orchestrates the generation process by:
    1. Validating input parameters
    2. Selecting the appropriate spacer type generator
    3. Optionally using templates for hybrid generation
    4. Generating and returning G-code
    """

    # Map spacer types to generator classes
    GENERATOR_MAP: Dict[SpacerType, Type[BaseSpacerGenerator]] = {
        SpacerType.STANDARD: StandardSpacerGenerator,
        SpacerType.HUB_CENTRIC: HubCentricSpacerGenerator,
        SpacerType.THIN_LIP: ThinLipSpacerGenerator,
        SpacerType.STEP: StepSpacerGenerator,
        SpacerType.STEEL_RING: SteelRingSpacerGenerator,
        SpacerType.TWO_PIECE: TwoPieceSpacerGenerator,
    }

    # Map spacer types to folder names for saving
    FOLDER_MAP: Dict[SpacerType, str] = {
        SpacerType.STANDARD: "1_Standard_Spacer",
        SpacerType.HUB_CENTRIC: "2_Hub_Centric",
        SpacerType.THIN_LIP: "3_Thin_Lip",
        SpacerType.STEP: "5_STEP_Spacer",
        SpacerType.STEEL_RING: "4_Steel_Ring",
        SpacerType.TWO_PIECE: "6_Two_Piece_Interlocking",
    }

    def __init__(self, use_templates: bool = True, db_path: Optional[str] = None):
        """
        Initialize the G-Code Generator.

        Args:
            use_templates: Whether to use template matching (hybrid mode)
            db_path: Path to the SQLite database for template matching
        """
        self.use_templates = use_templates
        self.db_path = db_path
        self.template_matcher = None

        if use_templates and db_path:
            self.template_matcher = TemplateMatcher(db_path)

    @staticmethod
    def mm_to_inches(mm_value: float) -> float:
        """Convert millimeters to inches."""
        return round(mm_value / 25.4, 4)

    @staticmethod
    def apply_tolerance(value_mm: float, is_cb: bool = True) -> float:
        """Apply tolerance to dimension (CB +0.1mm, OB -0.1mm)."""
        if is_cb:
            return value_mm + 0.1
        return value_mm - 0.1

    def determine_lathe(self, round_size: float) -> Optional[str]:
        """Determine which lathe to use based on round size."""
        return LatheConfig.get_lathe_for_size(round_size)

    def detect_thin_lip(self, cb_mm: float, ob_mm: float, threshold: float = 5.0) -> bool:
        """
        Detect if spacer qualifies as thin-lip.

        Args:
            cb_mm: Center bore in mm
            ob_mm: Outer bore in mm
            threshold: Maximum wall thickness for thin-lip (default 5mm)

        Returns:
            True if wall thickness is <= threshold
        """
        wall_thickness = ob_mm - cb_mm
        return wall_thickness <= threshold

    def normalize_thickness_key(self, thickness: Union[str, float]) -> str:
        """
        Normalize thickness to a standard key format.

        Accepts: "1.5", 1.5, "1.50", "15MM", etc.
        Returns: "1.50" or "15MM"
        """
        if isinstance(thickness, str):
            if thickness.upper().endswith("MM"):
                return thickness.upper()
            try:
                return f"{float(thickness):.2f}"
            except ValueError:
                return thickness
        return f"{float(thickness):.2f}"

    def create_dimensions(
        self,
        spacer_type: SpacerType,
        program_number: str,
        round_size: float,
        thickness: Union[str, float],
        cb_mm: float,
        lathe: str,
        ob_mm: Optional[float] = None,
        hub_height: Optional[float] = None,
        counterbore_mm: Optional[float] = None,
        step_depth: Optional[float] = None,
        use_tolerance: bool = True,
        use_calculated_feeds: bool = False,
    ) -> Union[SpacerDimensions, HubCentricDimensions, StepSpacerDimensions]:
        """
        Create the appropriate dimensions dataclass for the spacer type.

        Returns the correct dimension type for the generator.
        """
        thickness_key = self.normalize_thickness_key(thickness)

        # Calculate thickness in inches
        if thickness_key.endswith("MM"):
            thickness_inches = self.mm_to_inches(float(thickness_key[:-2]))
        else:
            thickness_inches = float(thickness_key)

        # Apply tolerance to CB
        cb_adjusted = self.apply_tolerance(cb_mm, is_cb=True) if use_tolerance else cb_mm
        cb_inches = self.mm_to_inches(cb_adjusted)

        # Ensure program number starts with O
        if not program_number.upper().startswith('O'):
            program_number = 'O' + program_number

        # Base dimensions (used by all types)
        base_kwargs = {
            "program_number": program_number.upper(),
            "round_size": round_size,
            "thickness_inches": thickness_inches,
            "thickness_key": thickness_key,
            "cb_mm": cb_mm,
            "cb_mm_adjusted": cb_adjusted,
            "cb_inches": cb_inches,
            "lathe": lathe.upper(),
            "use_tolerance": use_tolerance,
            "use_calculated_feeds": use_calculated_feeds,
        }

        # Return appropriate dimension type
        if spacer_type in [SpacerType.HUB_CENTRIC, SpacerType.THIN_LIP]:
            if ob_mm is None or hub_height is None:
                raise ValueError(
                    f"{spacer_type.value} requires ob_mm and hub_height"
                )

            ob_adjusted = self.apply_tolerance(ob_mm, is_cb=False) if use_tolerance else ob_mm
            ob_inches = self.mm_to_inches(ob_adjusted)

            return HubCentricDimensions(
                **base_kwargs,
                ob_mm=ob_mm,
                ob_mm_adjusted=ob_adjusted,
                ob_inches=ob_inches,
                hub_height_inches=hub_height,
            )

        elif spacer_type == SpacerType.STEP:
            if counterbore_mm is None or step_depth is None:
                raise ValueError(
                    "STEP spacer requires counterbore_mm and step_depth"
                )

            cb_adjusted_step = self.apply_tolerance(cb_mm, is_cb=True) if use_tolerance else cb_mm
            counterbore_adjusted = self.apply_tolerance(counterbore_mm, is_cb=False) if use_tolerance else counterbore_mm

            return StepSpacerDimensions(
                **base_kwargs,
                counterbore_mm=counterbore_mm,
                counterbore_mm_adjusted=counterbore_adjusted,
                counterbore_inches=self.mm_to_inches(counterbore_adjusted),
                step_depth_inches=step_depth,
            )

        else:
            # Standard, Steel Ring, Two-Piece
            return SpacerDimensions(**base_kwargs)

    def generate(
        self,
        spacer_type: Union[SpacerType, str],
        program_number: str,
        round_size: float,
        thickness: Union[str, float],
        cb_mm: float,
        lathe: Optional[str] = None,
        ob_mm: Optional[float] = None,
        hub_height: Optional[float] = None,
        counterbore_mm: Optional[float] = None,
        step_depth: Optional[float] = None,
        use_tolerance: bool = True,
        use_calculated_feeds: bool = False,
        is_male_piece: bool = True,  # For two-piece only
    ) -> str:
        """
        Generate G-code for a wheel spacer.

        Args:
            spacer_type: Type of spacer to generate
            program_number: O-number for the program
            round_size: Round stock diameter in inches
            thickness: Part thickness (e.g., "1.50" or "15MM")
            cb_mm: Center bore in millimeters
            lathe: Lathe to use (L1, L2, L3) - auto-detected if None
            ob_mm: Outer bore in mm (hub-centric only)
            hub_height: Hub projection height in inches (hub-centric only)
            counterbore_mm: Counterbore diameter in mm (STEP only)
            step_depth: Step depth in inches (STEP only)
            use_tolerance: Apply standard tolerances
            use_calculated_feeds: Use formula-based feeds/speeds
            is_male_piece: For two-piece, True=male, False=female

        Returns:
            Generated G-code as a string
        """
        # Convert string to enum if needed
        if isinstance(spacer_type, str):
            spacer_type = SpacerType(spacer_type.lower())

        # Auto-detect thin-lip if hub-centric with narrow wall
        if spacer_type == SpacerType.HUB_CENTRIC and ob_mm is not None:
            if self.detect_thin_lip(cb_mm, ob_mm):
                spacer_type = SpacerType.THIN_LIP

        # Auto-detect lathe if not specified
        if lathe is None:
            lathe = self.determine_lathe(round_size)
            if lathe is None:
                available = LatheConfig.get_available_lathes_for_size(round_size)
                if available:
                    lathe = available[0]  # Default to first available
                else:
                    raise ValueError(
                        f"Cannot determine lathe for round size {round_size}. "
                        "Please specify lathe explicitly."
                    )

        # Create dimensions
        dimensions = self.create_dimensions(
            spacer_type=spacer_type,
            program_number=program_number,
            round_size=round_size,
            thickness=thickness,
            cb_mm=cb_mm,
            lathe=lathe,
            ob_mm=ob_mm,
            hub_height=hub_height,
            counterbore_mm=counterbore_mm,
            step_depth=step_depth,
            use_tolerance=use_tolerance,
            use_calculated_feeds=use_calculated_feeds,
        )

        # Get the appropriate generator
        generator_class = self.GENERATOR_MAP[spacer_type]

        # Create generator instance
        if spacer_type == SpacerType.TWO_PIECE:
            generator = generator_class(dimensions, is_male_piece=is_male_piece)
        else:
            generator = generator_class(dimensions)

        # Validate dimensions
        is_valid, errors = generator.validate_dimensions()
        if not is_valid:
            raise ValueError(f"Invalid dimensions: {'; '.join(errors)}")

        # Generate G-code
        return generator.generate()

    def generate_and_save(
        self,
        output_dir: str,
        **kwargs,
    ) -> Tuple[str, str]:
        """
        Generate G-code and save to file.

        Args:
            output_dir: Base directory for output
            **kwargs: All arguments passed to generate()

        Returns:
            Tuple of (gcode_content, filepath)
        """
        gcode = self.generate(**kwargs)

        # Build output path
        spacer_type = kwargs.get('spacer_type')
        if isinstance(spacer_type, str):
            spacer_type = SpacerType(spacer_type.lower())

        round_size = kwargs.get('round_size', 0)
        program_number = kwargs.get('program_number', 'O00000')

        type_folder = self.FOLDER_MAP.get(spacer_type, "Unknown")
        size_folder = f"{str(round_size).replace('.', '_')}_inch"

        full_dir = os.path.join(output_dir, type_folder, size_folder)
        os.makedirs(full_dir, exist_ok=True)

        filename = f"{program_number.upper()}.nc"
        filepath = os.path.join(full_dir, filename)

        # Write file
        gcode_ascii = gcode.encode('ascii', 'replace').decode('ascii')
        with open(filepath, 'w', encoding='ascii') as f:
            f.write(gcode_ascii)

        return (gcode, filepath)

    def get_available_spacer_types(self) -> list:
        """Get list of available spacer types."""
        return [t.value for t in SpacerType]

    def get_spacer_type_info(self, spacer_type: Union[SpacerType, str]) -> Dict:
        """
        Get information about a spacer type.

        Returns dict with required fields and description.
        """
        if isinstance(spacer_type, str):
            spacer_type = SpacerType(spacer_type.lower())

        info = {
            SpacerType.STANDARD: {
                "name": "Standard Wheel Spacer",
                "description": "Simple flat disc with center bore",
                "required": ["cb_mm"],
                "optional": [],
            },
            SpacerType.HUB_CENTRIC: {
                "name": "Hub-Centric Wheel Spacer",
                "description": "Spacer with raised hub ring for centering",
                "required": ["cb_mm", "ob_mm", "hub_height"],
                "optional": [],
            },
            SpacerType.THIN_LIP: {
                "name": "Thin-Lip Hub-Centric",
                "description": "Hub-centric with thin wall (CB/OB within 5mm)",
                "required": ["cb_mm", "ob_mm", "hub_height"],
                "optional": [],
            },
            SpacerType.STEP: {
                "name": "STEP Spacer",
                "description": "Spacer with counterbore shelf",
                "required": ["cb_mm", "counterbore_mm", "step_depth"],
                "optional": [],
            },
            SpacerType.STEEL_RING: {
                "name": "Steel Ring Spacer",
                "description": "Spacer with press-fit bore for steel ring",
                "required": ["cb_mm"],
                "optional": [],
            },
            SpacerType.TWO_PIECE: {
                "name": "2-Piece Interlocking",
                "description": "Matched pair of interlocking spacers",
                "required": ["cb_mm"],
                "optional": ["is_male_piece"],
            },
        }

        return info.get(spacer_type, {})
