"""
Standards Validator Module
Validates G-code programs against verification standards for feasibility.

Part of Phase 3+: Program Verification Standards System
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from . import verification_standards as vs


@dataclass
class ValidationResult:
    """Result of feasibility validation"""
    feasible: bool
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    status: str  # 'FEASIBLE', 'NOT_FEASIBLE', 'UNKNOWN'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'feasible': self.feasible,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'status': self.status
        }


class StandardsValidator:
    """Validates programs against lathe-specific standards"""

    def __init__(self, standards_dict: Optional[Dict] = None):
        """
        Initialize validator.

        Args:
            standards_dict: Optional custom standards dictionary.
                           If None, uses default VERIFICATION_STANDARDS
        """
        self.standards = standards_dict if standards_dict else vs.VERIFICATION_STANDARDS

    def validate_program_feasibility(self, parse_result) -> ValidationResult:
        """
        Check if program is physically runnable on assigned lathe.

        Args:
            parse_result: GCodeParseResult object from parser

        Returns:
            ValidationResult with feasibility status and issues
        """
        critical_issues = []
        warnings = []
        recommendations = []

        # Extract key attributes from parse result
        lathe = getattr(parse_result, 'lathe', None)
        outer_diameter = getattr(parse_result, 'outer_diameter', None)
        thickness = getattr(parse_result, 'thickness', None)
        piece_type = getattr(parse_result, 'spacer_type', None)
        hub_height = getattr(parse_result, 'hub_height', None)
        center_bore = getattr(parse_result, 'center_bore', None)

        # If no lathe assigned, can't validate feasibility
        if not lathe or lathe == "N/A":
            warnings.append("No lathe assigned - cannot verify feasibility")
            return ValidationResult(
                feasible=True,
                critical_issues=[],
                warnings=warnings,
                recommendations=["Assign lathe to enable feasibility validation"],
                status='UNKNOWN'
            )

        # Get standards for this lathe
        lathe_standards = vs.get_lathe_standards(lathe)
        if not lathe_standards:
            warnings.append(f"No standards defined for lathe '{lathe}'")
            return ValidationResult(
                feasible=True,
                critical_issues=[],
                warnings=warnings,
                recommendations=[],
                status='UNKNOWN'
            )

        # ===================================================================
        # CRITICAL CHECKS - Program cannot run if these fail
        # ===================================================================

        # 1. Check round size compatibility
        if outer_diameter:
            is_supported, error_msg = vs.check_round_size_compatibility(lathe, outer_diameter)
            if not is_supported:
                critical_issues.append(error_msg)

        # 2. Check chuck capacity
        if outer_diameter:
            is_compatible, error_msg = vs.check_od_compatibility(lathe, outer_diameter)
            if not is_compatible:
                critical_issues.append(error_msg)

        # 3. Check thickness range
        if thickness:
            is_compatible, error_msg = vs.check_thickness_compatibility(lathe, thickness)
            if not is_compatible:
                critical_issues.append(error_msg)

        # 4. Check piece type compatibility
        if piece_type:
            piece_rules = vs.get_piece_type_rules(lathe, piece_type)
            if piece_rules:
                if not piece_rules.get('allowed', True):
                    critical_issues.append(
                        f"Piece type '{piece_type}' is not allowed on {lathe}"
                    )
                else:
                    # Check thickness limits for this piece type
                    if thickness:
                        min_t, max_t = piece_rules['thickness_limits']
                        if thickness < min_t:
                            critical_issues.append(
                                f"{piece_type} minimum thickness is {min_t}\", "
                                f"program has {thickness:.3f}\""
                            )
                        if thickness > max_t:
                            critical_issues.append(
                                f"{piece_type} maximum thickness is {max_t}\", "
                                f"program has {thickness:.3f}\""
                            )

                        # Check hub height limits for hub-centric pieces
                        if piece_type == "hub_centric" and hub_height:
                            max_hub = piece_rules.get('hub_height_max')
                            if max_hub and hub_height > max_hub:
                                critical_issues.append(
                                    f"Hub height {hub_height:.3f}\" exceeds maximum "
                                    f"({max_hub}\" for {piece_type} on {lathe})"
                                )

        # ===================================================================
        # WARNING CHECKS - Program may work but requires attention
        # ===================================================================

        # 5. Check drill depth limit
        if thickness:
            is_within_limit, warning_msg = vs.check_drill_depth_limit(thickness, hub_height)
            if not is_within_limit:
                warnings.append(warning_msg)

        # 6. Apply special rules for piece type
        if piece_type:
            piece_rules = vs.get_piece_type_rules(lathe, piece_type)
            if piece_rules and 'special_rules' in piece_rules:
                for rule_name in piece_rules['special_rules']:
                    rule_warnings = self._apply_special_rule(
                        rule_name, parse_result, lathe_standards
                    )
                    if rule_warnings:
                        warnings.extend(rule_warnings)

        # 7. Check for unusual configurations
        unusual_configs = self._check_unusual_configurations(
            parse_result, lathe_standards
        )
        if unusual_configs:
            warnings.extend(unusual_configs)

        # ===================================================================
        # RECOMMENDATIONS - Helpful suggestions
        # ===================================================================

        # Recommend OP2 if close to drill depth limit
        if thickness and hub_height:
            total_height = thickness + hub_height
            if 4.0 <= total_height <= 4.15:
                recommendations.append(
                    f"Total height {total_height:.3f}\" is near drill depth limit. "
                    f"Consider OP2 for safety margin."
                )

        # Recommend lathe reassignment if size is shared
        if outer_diameter and lathe in ["L2", "L3"]:
            # Check if size is shared between L2 and L3
            if 7.0 <= outer_diameter <= 8.5:
                if lathe == "L2":
                    recommendations.append(
                        f"Size {outer_diameter}\" can also run on L3. "
                        f"Consider L2/L3 designation for flexibility."
                    )
                elif lathe == "L3":
                    recommendations.append(
                        f"Size {outer_diameter}\" can also run on L2. "
                        f"Consider L2/L3 designation for flexibility."
                    )

        # ===================================================================
        # DETERMINE FINAL STATUS
        # ===================================================================

        if critical_issues:
            feasible = False
            status = 'NOT_FEASIBLE'
        else:
            feasible = True
            status = 'FEASIBLE'

        return ValidationResult(
            feasible=feasible,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
            status=status
        )

    def _apply_special_rule(self, rule_name: str, parse_result,
                           lathe_standards: Dict) -> List[str]:
        """
        Apply piece-type specific special rules.

        Args:
            rule_name: Name of special rule to apply
            parse_result: GCodeParseResult object
            lathe_standards: Standards dictionary for lathe

        Returns:
            List of warning messages (empty if rule passes)
        """
        warnings = []

        if rule_name == "verify_hub_clearance":
            # Check if hub height is reasonable for hub-centric parts
            hub_height = getattr(parse_result, 'hub_height', None)
            if hub_height:
                typical_hub = 0.50
                if abs(hub_height - typical_hub) > 0.15:
                    warnings.append(
                        f"Hub height {hub_height:.3f}\" differs from typical {typical_hub}\" "
                        f"for hub-centric parts. Verify this is correct."
                    )

        elif rule_name == "verify_shelf_clearance":
            # Check if shelf depth is within typical range for STEP pieces
            # Note: This would require additional detection in parser
            # For now, just add a note
            warnings.append(
                "STEP piece detected. Verify shelf depth is 0.30\"-0.32\" as required."
            )

        elif rule_name == "steel_material_check":
            # Steel rings may require different tool settings
            warnings.append(
                "Steel material detected. Ensure appropriate cutting speeds/feeds are used."
            )

        return warnings

    def _check_unusual_configurations(self, parse_result,
                                     lathe_standards: Dict) -> List[str]:
        """
        Check for unusual but valid configurations.

        Args:
            parse_result: GCodeParseResult object
            lathe_standards: Standards dictionary for lathe

        Returns:
            List of warning messages
        """
        warnings = []

        thickness = getattr(parse_result, 'thickness', None)
        outer_diameter = getattr(parse_result, 'outer_diameter', None)
        piece_type = getattr(parse_result, 'spacer_type', None)

        # Check for very thin parts relative to diameter
        if thickness and outer_diameter:
            aspect_ratio = outer_diameter / thickness
            if aspect_ratio > 15:
                warnings.append(
                    f"Very thin part: OD/thickness ratio is {aspect_ratio:.1f}. "
                    f"May require special handling to prevent warping."
                )

        # Check for very thick parts
        if thickness and thickness >= 3.75:
            warnings.append(
                f"Very thick part ({thickness:.3f}\"). Ensure adequate tool reach "
                f"and verify P-code for proper positioning."
            )

        # Check for 2PC UNSURE type - needs manual verification
        if piece_type == "2pc_unsure":
            warnings.append(
                "2PC piece type is unclear. Manually verify if this is LUG or STUD "
                "and update classification if needed."
            )

        return warnings

    def get_lathe_compatibility_summary(self, parse_result) -> Dict[str, Any]:
        """
        Get compatibility summary for all lathes.

        Args:
            parse_result: GCodeParseResult object

        Returns:
            Dictionary mapping lathe names to compatibility status
        """
        summary = {}

        for lathe_name in vs.get_all_lathes():
            # Create a modified parse result with this lathe
            # (This is a simplified approach - in production you'd clone the object)
            original_lathe = getattr(parse_result, 'lathe', None)

            # Temporarily set lathe for validation
            parse_result.lathe = lathe_name

            # Validate
            result = self.validate_program_feasibility(parse_result)

            # Store summary
            summary[lathe_name] = {
                'feasible': result.feasible,
                'status': result.status,
                'critical_count': len(result.critical_issues),
                'warning_count': len(result.warnings),
                'issues': result.critical_issues[:3]  # Top 3 issues
            }

            # Restore original lathe
            parse_result.lathe = original_lathe

        return summary

    def format_validation_report(self, result: ValidationResult,
                                program_number: str = "Unknown") -> str:
        """
        Generate human-readable validation report.

        Args:
            result: ValidationResult from validation
            program_number: Program number for report header

        Returns:
            Formatted string report
        """
        lines = []
        lines.append(f"=== Feasibility Validation Report: {program_number} ===")
        lines.append(f"Status: {result.status}")
        lines.append("")

        if result.critical_issues:
            lines.append(f"CRITICAL ISSUES ({len(result.critical_issues)}):")
            for i, issue in enumerate(result.critical_issues, 1):
                lines.append(f"  {i}. ❌ {issue}")
            lines.append("")

        if result.warnings:
            lines.append(f"WARNINGS ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                lines.append(f"  {i}. ⚠️  {warning}")
            lines.append("")

        if result.recommendations:
            lines.append(f"RECOMMENDATIONS ({len(result.recommendations)}):")
            for i, rec in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. 💡 {rec}")
            lines.append("")

        if result.feasible and not result.warnings:
            lines.append("✅ Program is FEASIBLE with no issues detected.")

        return "\n".join(lines)
