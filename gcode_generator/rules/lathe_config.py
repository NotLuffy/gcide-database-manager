"""
Lathe Configuration

Contains configuration for the different Haas lathes (L1, L2, L3) including:
- Round size assignments (which lathe handles which sizes)
- Machine limits (max RPM, travel limits, etc.)
- Tool turret positions
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LatheSpecs:
    """Specifications for a single lathe."""
    name: str
    round_sizes: List[float]  # Supported round sizes in inches
    max_rpm: int
    max_css: int  # Max constant surface speed
    x_home: float  # X home position
    z_home: float  # Z home position
    x_min: float  # Minimum X travel
    z_min: float  # Minimum Z travel
    chuck_max: float  # Maximum chuck capacity


class LatheConfig:
    """Manages lathe configurations and assignments."""

    # Lathe round size assignments
    # These define which round sizes each lathe is set up to handle
    LATHE_ASSIGNMENTS: Dict[str, List[float]] = {
        "L1": [5.75, 6.0, 6.25, 6.5],
        "L2": [7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0],
        "L3": [7.0, 7.5, 8.0, 8.5],
    }

    # Machine specifications
    LATHE_SPECS: Dict[str, LatheSpecs] = {
        "L1": LatheSpecs(
            name="Lathe 1",
            round_sizes=[5.75, 6.0, 6.25, 6.5],
            max_rpm=4000,
            max_css=2800,
            x_home=-11.0,
            z_home=-13.0,
            x_min=-11.0,
            z_min=-15.0,
            chuck_max=8.0,
        ),
        "L2": LatheSpecs(
            name="Lathe 2",
            round_sizes=[7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0],
            max_rpm=3500,
            max_css=3000,
            x_home=-11.0,
            z_home=-13.0,
            x_min=-11.0,
            z_min=-15.0,
            chuck_max=15.0,
        ),
        "L3": LatheSpecs(
            name="Lathe 3",
            round_sizes=[7.0, 7.5, 8.0, 8.5],
            max_rpm=3500,
            max_css=3000,
            x_home=-11.0,
            z_home=-13.0,
            x_min=-11.0,
            z_min=-15.0,
            chuck_max=10.0,
        ),
    }

    # Standard tool positions
    TOOL_POSITIONS: Dict[str, Dict[str, int]] = {
        "drill": {"turret": 101, "offset": 1},
        "bore": {"turret": 121, "offset": 21},
        "turn": {"turret": 303, "offset": 3},
        "chamfer": {"turret": 121, "offset": 21},  # Same as bore tool
    }

    # Common G-code positions
    HOME_POSITION = "G00 G53 X-11. Z-13."
    TOOL_CHANGE_POSITION = "G00 G53 X-11. Z-13."

    @classmethod
    def get_lathe_for_size(cls, round_size: float) -> Optional[str]:
        """
        Determine which lathe to use based on round size.

        Args:
            round_size: Round stock size in inches

        Returns:
            Lathe name ("L1", "L2", "L3") or None if size is shared/unknown
        """
        matching_lathes = []

        for lathe, sizes in cls.LATHE_ASSIGNMENTS.items():
            if round_size in sizes:
                matching_lathes.append(lathe)

        if len(matching_lathes) == 1:
            return matching_lathes[0]
        elif len(matching_lathes) > 1:
            # Size is on multiple lathes - user must choose
            return None
        else:
            # Size not found in any lathe assignment
            return None

    @classmethod
    def get_available_lathes_for_size(cls, round_size: float) -> List[str]:
        """
        Get all lathes that can handle a given round size.

        Args:
            round_size: Round stock size in inches

        Returns:
            List of lathe names
        """
        return [
            lathe for lathe, sizes in cls.LATHE_ASSIGNMENTS.items()
            if round_size in sizes
        ]

    @classmethod
    def get_lathe_specs(cls, lathe: str) -> LatheSpecs:
        """
        Get specifications for a specific lathe.

        Args:
            lathe: Lathe name ("L1", "L2", or "L3")

        Returns:
            LatheSpecs dataclass with machine specifications
        """
        if lathe not in cls.LATHE_SPECS:
            raise KeyError(f"Unknown lathe '{lathe}'. Available: {list(cls.LATHE_SPECS.keys())}")

        return cls.LATHE_SPECS[lathe]

    @classmethod
    def get_round_sizes(cls, lathe: str) -> List[float]:
        """Get list of round sizes for a specific lathe."""
        if lathe not in cls.LATHE_ASSIGNMENTS:
            raise KeyError(f"Unknown lathe '{lathe}'")

        return cls.LATHE_ASSIGNMENTS[lathe]

    @classmethod
    def get_all_round_sizes(cls) -> List[float]:
        """Get sorted list of all available round sizes across all lathes."""
        all_sizes = set()
        for sizes in cls.LATHE_ASSIGNMENTS.values():
            all_sizes.update(sizes)
        return sorted(all_sizes)

    @classmethod
    def get_tool_code(cls, tool_type: str) -> str:
        """
        Get the tool code string for G-code output.

        Args:
            tool_type: "drill", "bore", "turn", or "chamfer"

        Returns:
            Tool code like "T101" or "T303"
        """
        if tool_type not in cls.TOOL_POSITIONS:
            raise KeyError(f"Unknown tool type '{tool_type}'")

        return f"T{cls.TOOL_POSITIONS[tool_type]['turret']}"

    @classmethod
    def get_home_position(cls, lathe: Optional[str] = None) -> str:
        """
        Get the home position G-code.

        Args:
            lathe: Optional lathe name for lathe-specific positions

        Returns:
            G-code string for home position
        """
        if lathe and lathe in cls.LATHE_SPECS:
            specs = cls.LATHE_SPECS[lathe]
            return f"G00 G53 X{specs.x_home} Z{specs.z_home}"

        return cls.HOME_POSITION

    @classmethod
    def validate_lathe_selection(cls, lathe: str, round_size: float) -> Tuple[bool, str]:
        """
        Validate that a lathe can handle the given round size.

        Returns:
            Tuple of (is_valid, message)
        """
        if lathe not in cls.LATHE_ASSIGNMENTS:
            return (False, f"Unknown lathe '{lathe}'")

        if round_size not in cls.LATHE_ASSIGNMENTS[lathe]:
            available_sizes = cls.LATHE_ASSIGNMENTS[lathe]
            return (
                False,
                f"Lathe {lathe} is not configured for {round_size}\" round. "
                f"Available sizes: {available_sizes}"
            )

        # Check against chuck capacity
        specs = cls.LATHE_SPECS[lathe]
        if round_size > specs.chuck_max:
            return (
                False,
                f"Round size {round_size}\" exceeds {lathe} chuck capacity of {specs.chuck_max}\""
            )

        return (True, "OK")

    @classmethod
    def get_max_rpm(cls, lathe: str) -> int:
        """Get maximum RPM for a lathe."""
        return cls.LATHE_SPECS[lathe].max_rpm

    @classmethod
    def get_max_css(cls, lathe: str) -> int:
        """Get maximum constant surface speed for a lathe."""
        return cls.LATHE_SPECS[lathe].max_css
