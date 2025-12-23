"""
Depth Tables

Contains lookup tables for drill depths and profile depths based on part thickness.
These values are critical for proper machining - too shallow won't complete the part,
too deep could crash the tool or damage the part.

All values are in INCHES (negative Z direction).
"""

from typing import Dict, Optional, Tuple


class DepthTable:
    """Manages drill and profile depth lookup tables."""

    # Drill depth and outer profile depth lookup table
    # Key: thickness (metric like "10MM" or imperial like "1.00")
    # Values: all in inches (negative Z direction)
    DEPTH_TABLE: Dict[str, Dict[str, float]] = {
        # Metric thicknesses (common for thin spacers)
        "10MM": {"drill": -0.54, "profile": -0.10},
        "12MM": {"drill": -0.65, "profile": -0.10},
        "15MM": {"drill": -0.80, "profile": -0.10},
        "17MM": {"drill": -0.82, "profile": -0.10},
        "19MM": {"drill": -0.95, "profile": -0.35},

        # Imperial thicknesses (common for thicker spacers)
        "0.50": {"drill": -0.65, "profile": -0.10},
        "0.75": {"drill": -0.95, "profile": -0.30},
        "1.00": {"drill": -1.15, "profile": -0.55},
        "1.25": {"drill": -1.40, "profile": -0.70},
        "1.50": {"drill": -1.65, "profile": -0.80},
        "1.75": {"drill": -1.90, "profile": -1.00},
        "2.00": {"drill": -2.15, "profile": -1.10},
        "2.25": {"drill": -2.40, "profile": -1.20},
        "2.50": {"drill": -2.65, "profile": -1.30},
        "2.75": {"drill": -2.90, "profile": -1.50},
        "3.00": {"drill": -3.15, "profile": -1.60},
        "3.25": {"drill": -3.40, "profile": -1.70},
        "3.50": {"drill": -3.65, "profile": -1.80},
        "3.75": {"drill": -3.90, "profile": -2.00},
        "4.00": {"drill": -4.15, "profile": -2.10},
    }

    # Safety margins
    DRILL_MARGIN = 0.15  # Extra depth for drill to ensure through-hole
    PROFILE_MARGIN = 0.05  # Safety margin for profile depth

    @classmethod
    def normalize_thickness_key(cls, thickness_key: str) -> str:
        """
        Normalize thickness key to match lookup tables.

        Accepts:
        - Metric: "10MM", "12mm", "15MM"
        - Imperial: "1", "1.0", "1.00", "1.5", "1.50"

        Returns normalized key like "1.00" or "10MM"
        """
        # If it's a metric measurement, return uppercase
        if thickness_key.upper().endswith("MM"):
            return thickness_key.upper()

        # For imperial, convert to float and format to 2 decimal places
        try:
            thickness_float = float(thickness_key)
            return f"{thickness_float:.2f}"
        except ValueError:
            return thickness_key

    @classmethod
    def get_drill_depth(cls, thickness_key: str) -> float:
        """
        Get drill depth for a given thickness.

        Args:
            thickness_key: Thickness like "1.50" or "10MM"

        Returns:
            Drill depth in inches (negative value)

        Raises:
            KeyError: If thickness not found
        """
        normalized = cls.normalize_thickness_key(thickness_key)

        if normalized not in cls.DEPTH_TABLE:
            raise KeyError(
                f"Thickness '{normalized}' not found in depth table. "
                f"Available: {list(cls.DEPTH_TABLE.keys())}"
            )

        return cls.DEPTH_TABLE[normalized]["drill"]

    @classmethod
    def get_profile_depth(cls, thickness_key: str) -> float:
        """
        Get profile (turning) depth for a given thickness.

        Args:
            thickness_key: Thickness like "1.50" or "10MM"

        Returns:
            Profile depth in inches (negative value)
        """
        normalized = cls.normalize_thickness_key(thickness_key)

        if normalized not in cls.DEPTH_TABLE:
            raise KeyError(
                f"Thickness '{normalized}' not found in depth table. "
                f"Available: {list(cls.DEPTH_TABLE.keys())}"
            )

        return cls.DEPTH_TABLE[normalized]["profile"]

    @classmethod
    def get_depths(cls, thickness_key: str) -> Tuple[float, float]:
        """
        Get both drill and profile depths.

        Returns:
            Tuple of (drill_depth, profile_depth)
        """
        normalized = cls.normalize_thickness_key(thickness_key)

        if normalized not in cls.DEPTH_TABLE:
            raise KeyError(f"Thickness '{normalized}' not found in depth table.")

        depths = cls.DEPTH_TABLE[normalized]
        return (depths["drill"], depths["profile"])

    @classmethod
    def calculate_drill_depth(cls, thickness_inches: float) -> float:
        """
        Calculate drill depth when thickness is not in the table.

        Uses linear interpolation based on known values.

        Args:
            thickness_inches: Part thickness in inches

        Returns:
            Calculated drill depth (negative value)
        """
        # Base formula: drill_depth = thickness + margin
        # From table analysis: drill is typically thickness + 0.15" to 0.25"
        base_depth = thickness_inches + cls.DRILL_MARGIN
        return -base_depth

    @classmethod
    def calculate_profile_depth(cls, thickness_inches: float) -> float:
        """
        Calculate profile depth when thickness is not in the table.

        Profile depth is typically about 50-55% of thickness for thicker parts.

        Args:
            thickness_inches: Part thickness in inches

        Returns:
            Calculated profile depth (negative value)
        """
        if thickness_inches <= 0.75:
            # Thin parts: shallow profile
            return -0.10
        elif thickness_inches <= 1.0:
            # Transition range
            return -(thickness_inches * 0.5)
        else:
            # Thicker parts: approximately 50-55% of thickness
            return -(thickness_inches * 0.525)

    @classmethod
    def get_or_calculate_depths(
        cls,
        thickness_key: str,
        thickness_inches: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Get depths from table or calculate if not found.

        This is the preferred method - tries table first, falls back to calculation.

        Args:
            thickness_key: Thickness key like "1.50" or "10MM"
            thickness_inches: Actual thickness in inches (for calculation fallback)

        Returns:
            Tuple of (drill_depth, profile_depth)
        """
        normalized = cls.normalize_thickness_key(thickness_key)

        if normalized in cls.DEPTH_TABLE:
            depths = cls.DEPTH_TABLE[normalized]
            return (depths["drill"], depths["profile"])

        # Not in table - calculate if we have the actual thickness
        if thickness_inches is not None:
            return (
                cls.calculate_drill_depth(thickness_inches),
                cls.calculate_profile_depth(thickness_inches)
            )

        raise KeyError(
            f"Thickness '{normalized}' not in table and no thickness_inches "
            "provided for calculation."
        )

    @classmethod
    def get_available_thicknesses(cls) -> list:
        """Get list of all available thickness keys."""
        return list(cls.DEPTH_TABLE.keys())

    @classmethod
    def get_metric_thicknesses(cls) -> list:
        """Get list of metric thickness keys only."""
        return [k for k in cls.DEPTH_TABLE.keys() if k.endswith("MM")]

    @classmethod
    def get_imperial_thicknesses(cls) -> list:
        """Get list of imperial thickness keys only."""
        return [k for k in cls.DEPTH_TABLE.keys() if not k.endswith("MM")]
