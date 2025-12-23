"""
P-Code Manager

P-codes are work offsets used on Haas lathes to position the part correctly
for each operation. Different lathes (L1, L2, L3) use different P-code progressions.

The P-code is selected based on:
1. Which lathe is being used (L1 vs L2/L3)
2. The total part thickness (including hub height for hub-centric spacers)
"""

from typing import Dict, Optional, Tuple


class PCodeManager:
    """Manages P-code lookup for different lathes and thicknesses."""

    # P-code progression for Lathe 1 (smaller parts)
    # Uses P1-P40 range
    PCODE_L1: Dict[str, Dict[str, str]] = {
        "10MM": {"op1": "P1", "op2": "P2"},
        "12MM": {"op1": "P3", "op2": "P4"},
        "0.50": {"op1": "P5", "op2": "P6"},
        "0.75": {"op1": "P13", "op2": "P14"},
        "1.00": {"op1": "P15", "op2": "P16"},
        "1.25": {"op1": "P17", "op2": "P18"},
        "1.50": {"op1": "P19", "op2": "P20"},
        "1.75": {"op1": "P21", "op2": "P22"},
        "2.00": {"op1": "P23", "op2": "P24"},
        "2.25": {"op1": "P25", "op2": "P26"},
        "2.50": {"op1": "P27", "op2": "P28"},
        "2.75": {"op1": "P29", "op2": "P30"},
        "3.00": {"op1": "P31", "op2": "P32"},
        "3.25": {"op1": "P33", "op2": "P34"},
        "3.50": {"op1": "P35", "op2": "P36"},
        "3.75": {"op1": "P37", "op2": "P38"},
        "4.00": {"op1": "P39", "op2": "P40"},
    }

    # P-code progression for Lathe 2 and Lathe 3 (larger parts)
    # Uses P5-P30 range (offset from L1)
    PCODE_L2_L3: Dict[str, Dict[str, str]] = {
        "1.00": {"op1": "P5", "op2": "P6"},
        "1.25": {"op1": "P7", "op2": "P8"},
        "1.50": {"op1": "P9", "op2": "P10"},
        "1.75": {"op1": "P11", "op2": "P12"},
        "2.00": {"op1": "P13", "op2": "P14"},
        "2.25": {"op1": "P15", "op2": "P16"},
        "2.50": {"op1": "P17", "op2": "P18"},
        "2.75": {"op1": "P19", "op2": "P20"},
        "3.00": {"op1": "P21", "op2": "P22"},
        "3.25": {"op1": "P23", "op2": "P24"},
        "3.50": {"op1": "P25", "op2": "P26"},
        "3.75": {"op1": "P27", "op2": "P28"},
        "4.00": {"op1": "P29", "op2": "P30"},
    }

    # Alternative G154 P-code mapping used in some files
    # This maps P48/P49 style codes used with G154
    G154_PCODES: Dict[str, Dict[str, int]] = {
        # These are paired: op1 uses the lower number, op2 uses the higher
        "default": {"op1": 48, "op2": 49},
    }

    @classmethod
    def normalize_thickness_key(cls, thickness_key: str) -> str:
        """
        Normalize thickness key to match lookup tables.

        Accepts:
        - Metric: "10MM", "12MM", "15MM"
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
    def get_pcode(cls, lathe: str, thickness_key: str, operation: str) -> str:
        """
        Get the appropriate P-code based on lathe and thickness.

        Args:
            lathe: "L1", "L2", or "L3"
            thickness_key: Thickness like "1.50" or "10MM"
            operation: "op1" or "op2"

        Returns:
            P-code string like "P19" or "P20"

        Raises:
            KeyError: If thickness not found in lookup table
        """
        normalized_key = cls.normalize_thickness_key(thickness_key)

        if lathe == "L1":
            table = cls.PCODE_L1
        else:  # L2 or L3
            table = cls.PCODE_L2_L3

        if normalized_key not in table:
            raise KeyError(
                f"Thickness '{normalized_key}' not found in P-code table for {lathe}. "
                f"Available thicknesses: {list(table.keys())}"
            )

        return table[normalized_key][operation]

    @classmethod
    def get_g154_pcode(cls, operation: str, thickness_key: Optional[str] = None) -> int:
        """
        Get G154 P-code (numeric) for work offset.

        Some files use G154 P48/P49 format instead of the standard P-codes.

        Args:
            operation: "op1" or "op2"
            thickness_key: Optional thickness (for future expansion)

        Returns:
            Numeric P-code value (e.g., 48 or 49)
        """
        return cls.G154_PCODES["default"][operation]

    @classmethod
    def get_pcode_pair(cls, lathe: str, thickness_key: str) -> Tuple[str, str]:
        """
        Get both OP1 and OP2 P-codes as a tuple.

        Args:
            lathe: "L1", "L2", or "L3"
            thickness_key: Thickness like "1.50" or "10MM"

        Returns:
            Tuple of (op1_pcode, op2_pcode)
        """
        return (
            cls.get_pcode(lathe, thickness_key, "op1"),
            cls.get_pcode(lathe, thickness_key, "op2")
        )

    @classmethod
    def thickness_to_pcode_range(cls, lathe: str) -> Dict[str, Tuple[str, str]]:
        """
        Get the full mapping of thicknesses to P-code pairs for a lathe.

        Useful for displaying available options in UI.

        Returns:
            Dict mapping thickness to (op1_pcode, op2_pcode)
        """
        table = cls.PCODE_L1 if lathe == "L1" else cls.PCODE_L2_L3

        return {
            thickness: (codes["op1"], codes["op2"])
            for thickness, codes in table.items()
        }

    @classmethod
    def get_available_thicknesses(cls, lathe: str) -> list:
        """Get list of available thickness keys for a lathe."""
        table = cls.PCODE_L1 if lathe == "L1" else cls.PCODE_L2_L3
        return list(table.keys())

    @classmethod
    def detect_lathe_from_pcode(cls, pcode: str) -> Optional[str]:
        """
        Attempt to detect which lathe a P-code belongs to.

        This is useful when parsing existing files to determine the lathe.

        Returns:
            "L1", "L2/L3", or None if ambiguous
        """
        pcode_upper = pcode.upper()

        # Extract numeric value
        try:
            if pcode_upper.startswith("P"):
                pcode_num = int(pcode_upper[1:])
            else:
                pcode_num = int(pcode_upper)
        except ValueError:
            return None

        # L1 uses higher P-codes for common thicknesses
        # Check if this P-code is unique to L1
        l1_only_pcodes = set()
        for codes in cls.PCODE_L1.values():
            l1_only_pcodes.add(codes["op1"])
            l1_only_pcodes.add(codes["op2"])

        l2l3_pcodes = set()
        for codes in cls.PCODE_L2_L3.values():
            l2l3_pcodes.add(codes["op1"])
            l2l3_pcodes.add(codes["op2"])

        pcode_str = f"P{pcode_num}"

        if pcode_str in l1_only_pcodes and pcode_str not in l2l3_pcodes:
            return "L1"
        elif pcode_str in l2l3_pcodes and pcode_str not in l1_only_pcodes:
            return "L2/L3"

        return None  # Ambiguous or not found
