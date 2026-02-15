"""
Counterbore Depth Validator

Validates counterbore depth for STEP spacer parts.

STEP parts have two-stage boring:
1. Counterbore: Wider, shallower hole (e.g., 60mm @ 0.75" deep)
2. Center bore: Narrower, deeper hole (e.g., 54mm @ 2.0" deep)

Validation Rules:
- CB depth must be < total thickness
- CB depth should be 25-90% of thickness (typical range)
- CB depth should match title specification (if present)

Author: G-Code Database Manager
Date: 2026-02-14
"""

import re
from typing import List, Tuple, Optional


class CounterboreDepthValidator:
    """Validates counterbore depth for STEP parts"""

    def __init__(self):
        """Initialize validator with threshold values"""
        self.min_depth_ratio = 0.25  # CB depth should be at least 25% of thickness
        self.max_depth_ratio = 0.90  # CB depth should be no more than 90% of thickness
        self.depth_tolerance = 0.05  # ±0.05" tolerance when comparing to title

    def applies_to_part(self, spacer_type: str) -> bool:
        """
        Check if validation applies to this part type.

        Args:
            spacer_type: Part type (e.g., 'step', 'hub_centric', etc.)

        Returns:
            True if this is a STEP part that needs CB depth validation
        """
        if not spacer_type:
            return False
        return 'step' in spacer_type.lower()

    def extract_counterbore_depth_from_title(self, title: str) -> Optional[float]:
        """
        Extract expected counterbore depth from title.

        Patterns:
        - "0.75 STEP" → 0.75"
        - "0.75 DEEP CB" → 0.75"
        - "0.75\" STEP" → 0.75"

        Args:
            title: Program title

        Returns:
            Expected CB depth in inches, or None if not found
        """
        if not title:
            return None

        # Pattern: decimal number followed by STEP or DEEP or CB
        patterns = [
            r'(\d+\.?\d*)\s*STEP',
            r'(\d+\.?\d*)\s*DEEP\s*CB',
            r'(\d+\.?\d*)\s*"?\s*STEP',
            r'(\d+\.?\d*)\s*MM\s*STEP',  # Convert from MM if needed
        ]

        for pattern in patterns:
            match = re.search(pattern, title.upper())
            if match:
                depth = float(match.group(1))

                # If MM pattern, convert to inches
                if 'MM' in pattern:
                    depth = depth / 25.4

                return depth

        return None

    def extract_counterbore_depth_from_gcode(self,
                                            lines: List[str],
                                            thickness: float) -> Optional[float]:
        """
        Extract counterbore depth from G-code.

        Logic:
        - Look for T121 (BORE tool) operations
        - Find all Z depths during boring
        - Counterbore depth = shallowest (least negative) Z
        - Full depth = deepest (most negative) Z
        - CB depth must be shallower than full depth

        Args:
            lines: G-code lines
            thickness: Total part thickness in inches

        Returns:
            Counterbore depth in inches, or None if not found
        """
        in_bore_operation = False
        z_depths = []

        for line in lines:
            line_upper = line.upper()

            # Detect bore tool start
            if 'T121' in line_upper or ('BORE' in line_upper and 'T1' in line_upper):
                in_bore_operation = True
                continue

            # Detect tool change (exit bore operation)
            if re.search(r'T[^1]\d{2}', line_upper):
                in_bore_operation = False

            # Collect Z depths during boring
            if in_bore_operation:
                # Look for Z moves (G00 or G01)
                if re.search(r'G0?[01]\b', line_upper):
                    z_match = re.search(r'Z\s*(-?\d+\.?\d*)', line, re.IGNORECASE)
                    if z_match:
                        z_val = float(z_match.group(1))

                        # Only collect negative Z (into the part)
                        if z_val < 0:
                            z_depths.append(abs(z_val))

        # Analyze collected depths
        if len(z_depths) < 2:
            # Need at least 2 depths (CB + full depth) for STEP part
            return None

        # Sort depths (shallow to deep)
        z_depths.sort()

        # Counterbore depth = shallowest Z (first in sorted list)
        cb_depth = z_depths[0]
        full_depth = z_depths[-1]

        # Sanity checks
        if cb_depth >= full_depth:
            # CB should be shallower than full depth
            return None

        # NOTE: Don't check if cb_depth > thickness here - let validation method flag that as critical error

        # CB depth should be significantly less than full depth (at least 0.1" difference)
        if (full_depth - cb_depth) < 0.1:
            # Too similar - might not be a STEP part
            return None

        return cb_depth

    def validate_file(self,
                     lines: List[str],
                     spacer_type: str,
                     thickness: Optional[float],
                     title: Optional[str] = None) -> Tuple[List[str], List[str]]:
        """
        Validate counterbore depth for STEP part.

        Args:
            lines: G-code lines
            spacer_type: Part type
            thickness: Total thickness in inches
            title: Program title (optional, for cross-validation)

        Returns:
            Tuple of (critical_issues, warnings)
        """
        critical_issues = []
        warnings = []

        # Check if validation applies
        if not self.applies_to_part(spacer_type):
            return critical_issues, warnings

        if not thickness or thickness <= 0:
            warnings.append("STEP part detected but thickness unknown - cannot validate CB depth")
            return critical_issues, warnings

        # Extract CB depth from G-code
        cb_depth = self.extract_counterbore_depth_from_gcode(lines, thickness)

        if cb_depth is None:
            warnings.append(
                f"STEP part but counterbore depth not detected in G-code "
                f"(expected two-stage boring with T121)"
            )
            return critical_issues, warnings

        # Validate CB depth against thickness
        if cb_depth >= thickness:
            critical_issues.append(
                f"Counterbore depth ({cb_depth:.3f}\") exceeds total thickness ({thickness:.3f}\") "
                f"- will break through part!"
            )

        # Check depth ratio (typical range 25-90% of thickness)
        depth_ratio = cb_depth / thickness

        if depth_ratio < self.min_depth_ratio:
            warnings.append(
                f"Counterbore very shallow ({cb_depth:.3f}\" = {depth_ratio*100:.0f}% of {thickness:.3f}\" thickness) "
                f"- step shoulder may be too thin"
            )

        if depth_ratio > self.max_depth_ratio:
            warnings.append(
                f"Counterbore very deep ({cb_depth:.3f}\" = {depth_ratio*100:.0f}% of {thickness:.3f}\" thickness) "
                f"- little material left for step shoulder"
            )

        # Cross-validate with title (if available)
        if title:
            title_depth = self.extract_counterbore_depth_from_title(title)

            if title_depth:
                depth_diff = abs(cb_depth - title_depth)

                if depth_diff > self.depth_tolerance:
                    warnings.append(
                        f"Counterbore depth in G-code ({cb_depth:.3f}\") "
                        f"doesn't match title specification ({title_depth:.3f}\") "
                        f"- difference: {depth_diff:.3f}\""
                    )

        return critical_issues, warnings
