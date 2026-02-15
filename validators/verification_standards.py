"""
Verification Standards Module
Defines standards matrix for G-code program verification across different lathes,
piece types, and thickness ranges.

Part of Phase 3+: Program Verification Standards System
"""

from typing import Dict, List, Optional, Tuple, Any


# ============================================================================
# VERIFICATION STANDARDS MATRIX
# ============================================================================

VERIFICATION_STANDARDS = {
    "L1": {
        "name": "Lathe 1 (Small Parts)",
        "round_sizes": [5.75, 6.0, 6.25, 6.5],
        "chuck_capacity": 8.0,  # inches
        "z_travel_limit": -15.0,  # inches (absolute minimum)
        "z_home_position": -13.0,  # inches (typical home position)

        "thickness_range": {
            "min": 0.394,  # 10MM minimum
            "max": 4.00,   # P-code table maximum
            "pcodes": "PCODE_TABLE_L1"
        },

        "drill_depth_limit": 4.15,  # inches (single operation maximum)

        "piece_types": {
            "standard": {
                "allowed": True,
                "thickness_limits": (0.394, 4.0),
                "description": "Standard single bore spacer",
                "special_rules": []
            },
            "hub_centric": {
                "allowed": True,
                "thickness_limits": (0.5, 4.0),  # Min 0.5" for hub clearance
                "hub_height_max": 0.75,
                "hub_height_typical": 0.50,
                "description": "Hub-centric with CB/OB and 0.50\" hub",
                "special_rules": ["verify_hub_clearance"]
            },
            "step": {
                "allowed": True,
                "thickness_limits": (0.5, 4.0),
                "shelf_depth_range": (0.28, 0.35),
                "shelf_depth_typical": 0.31,
                "description": "STEP piece with counterbore shelf",
                "special_rules": ["verify_shelf_clearance"]
            },
            "2pc_lug": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),  # LUG receiver is thick
                "description": "2PC LUG receiver (thick part with shelf)",
                "special_rules": []
            },
            "2pc_stud": {
                "allowed": True,
                "thickness_limits": (0.394, 0.75),  # STUD insert is thin
                "hub_height_typical": 0.25,
                "description": "2PC STUD insert (thin part with 0.25\" hub)",
                "special_rules": []
            },
            "2pc_unsure": {
                "allowed": True,
                "thickness_limits": (0.394, 4.0),
                "description": "2PC part with unclear type",
                "special_rules": []
            },
            "steel_ring": {
                "allowed": True,
                "thickness_limits": (0.394, 4.0),
                "material": "steel",
                "description": "Steel ring spacer",
                "special_rules": ["steel_material_check"]
            },
            "metric_spacer": {
                "allowed": True,
                "thickness_limits": (0.394, 4.0),
                "description": "Metric dimensioned spacer",
                "special_rules": []
            }
        },

        "tool_home_rules": {
            "thickness_le_2.5": {
                "expected_z": -13.0,
                "min_safe_z": -13.0,
                "description": "Thickness ≤ 2.5\""
            },
            "thickness_2.75_3.75": {
                "expected_z": -11.0,
                "min_safe_z": -11.0,
                "description": "Thickness 2.75\" - 3.75\""
            },
            "thickness_4.0_5.0": {
                "expected_z": -9.0,
                "min_safe_z": -9.0,
                "description": "Thickness 4.0\" - 5.0\""
            }
        },

        "z_clearance_before_g53": 0.1  # Minimum safe Z clearance before tool home
    },

    "L2": {
        "name": "Lathe 2 (Large Parts)",
        "round_sizes": [7.0, 7.5, 8.0, 8.5, 9.5, 10.25, 10.5, 13.0],
        "chuck_capacity": 15.0,  # inches
        "z_travel_limit": -15.0,  # inches
        "z_home_position": -13.0,  # inches

        "thickness_range": {
            "min": 1.0,    # 1" minimum for L2
            "max": 4.00,   # P-code table maximum
            "pcodes": "PCODE_TABLE_L2_L3"
        },

        "drill_depth_limit": 4.15,  # inches

        "piece_types": {
            "standard": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "Standard single bore spacer",
                "special_rules": []
            },
            "hub_centric": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "hub_height_max": 0.75,
                "hub_height_typical": 0.50,
                "description": "Hub-centric with CB/OB and 0.50\" hub",
                "special_rules": ["verify_hub_clearance"]
            },
            "step": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "shelf_depth_range": (0.28, 0.35),
                "shelf_depth_typical": 0.31,
                "description": "STEP piece with counterbore shelf",
                "special_rules": ["verify_shelf_clearance"]
            },
            "2pc_lug": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "2PC LUG receiver (thick part with shelf)",
                "special_rules": []
            },
            "2pc_stud": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),  # L2 can handle thicker studs
                "hub_height_typical": 0.25,
                "description": "2PC STUD insert (thin part with 0.25\" hub)",
                "special_rules": []
            },
            "2pc_unsure": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "2PC part with unclear type",
                "special_rules": []
            },
            "steel_ring": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "material": "steel",
                "description": "Steel ring spacer",
                "special_rules": ["steel_material_check"]
            },
            "metric_spacer": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "Metric dimensioned spacer",
                "special_rules": []
            }
        },

        "tool_home_rules": {
            "thickness_le_2.5": {
                "expected_z": -13.0,
                "min_safe_z": -13.0,
                "description": "Thickness ≤ 2.5\""
            },
            "thickness_2.75_3.75": {
                "expected_z": -11.0,
                "min_safe_z": -11.0,
                "description": "Thickness 2.75\" - 3.75\""
            },
            "thickness_4.0_5.0": {
                "expected_z": -9.0,
                "min_safe_z": -9.0,
                "description": "Thickness 4.0\" - 5.0\""
            }
        },

        "z_clearance_before_g53": 0.1
    },

    "L3": {
        "name": "Lathe 3 (Shared Sizes)",
        "round_sizes": [7.0, 7.5, 8.0, 8.5],
        "chuck_capacity": 10.0,  # inches
        "z_travel_limit": -15.0,  # inches
        "z_home_position": -13.0,  # inches

        "thickness_range": {
            "min": 1.0,    # 1" minimum for L3
            "max": 4.00,   # P-code table maximum
            "pcodes": "PCODE_TABLE_L2_L3"
        },

        "drill_depth_limit": 4.15,  # inches

        "piece_types": {
            "standard": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "Standard single bore spacer",
                "special_rules": []
            },
            "hub_centric": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "hub_height_max": 0.75,
                "hub_height_typical": 0.50,
                "description": "Hub-centric with CB/OB and 0.50\" hub",
                "special_rules": ["verify_hub_clearance"]
            },
            "step": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "shelf_depth_range": (0.28, 0.35),
                "shelf_depth_typical": 0.31,
                "description": "STEP piece with counterbore shelf",
                "special_rules": ["verify_shelf_clearance"]
            },
            "2pc_lug": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "2PC LUG receiver (thick part with shelf)",
                "special_rules": []
            },
            "2pc_stud": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "hub_height_typical": 0.25,
                "description": "2PC STUD insert (thin part with 0.25\" hub)",
                "special_rules": []
            },
            "2pc_unsure": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "2PC part with unclear type",
                "special_rules": []
            },
            "steel_ring": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "material": "steel",
                "description": "Steel ring spacer",
                "special_rules": ["steel_material_check"]
            },
            "metric_spacer": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "Metric dimensioned spacer",
                "special_rules": []
            }
        },

        "tool_home_rules": {
            "thickness_le_2.5": {
                "expected_z": -13.0,
                "min_safe_z": -13.0,
                "description": "Thickness ≤ 2.5\""
            },
            "thickness_2.75_3.75": {
                "expected_z": -11.0,
                "min_safe_z": -11.0,
                "description": "Thickness 2.75\" - 3.75\""
            },
            "thickness_4.0_5.0": {
                "expected_z": -9.0,
                "min_safe_z": -9.0,
                "description": "Thickness 4.0\" - 5.0\""
            }
        },

        "z_clearance_before_g53": 0.1
    },

    "L2/L3": {
        "name": "Lathe 2/3 (Hybrid/Shared)",
        "round_sizes": [7.0, 7.5, 8.0, 8.5],  # Shared sizes only
        "chuck_capacity": 10.0,  # Use more restrictive L3 capacity
        "z_travel_limit": -15.0,
        "z_home_position": -13.0,

        "thickness_range": {
            "min": 1.0,
            "max": 4.00,
            "pcodes": "PCODE_TABLE_L2_L3"
        },

        "drill_depth_limit": 4.15,

        # Piece types same as L2/L3
        "piece_types": {
            "standard": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "Standard single bore spacer",
                "special_rules": []
            },
            "hub_centric": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "hub_height_max": 0.75,
                "hub_height_typical": 0.50,
                "description": "Hub-centric with CB/OB and 0.50\" hub",
                "special_rules": ["verify_hub_clearance"]
            },
            "step": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "shelf_depth_range": (0.28, 0.35),
                "shelf_depth_typical": 0.31,
                "description": "STEP piece with counterbore shelf",
                "special_rules": ["verify_shelf_clearance"]
            },
            "2pc_lug": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "2PC LUG receiver (thick part with shelf)",
                "special_rules": []
            },
            "2pc_stud": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "hub_height_typical": 0.25,
                "description": "2PC STUD insert (thin part with 0.25\" hub)",
                "special_rules": []
            },
            "2pc_unsure": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "2PC part with unclear type",
                "special_rules": []
            },
            "steel_ring": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "material": "steel",
                "description": "Steel ring spacer",
                "special_rules": ["steel_material_check"]
            },
            "metric_spacer": {
                "allowed": True,
                "thickness_limits": (1.0, 4.0),
                "description": "Metric dimensioned spacer",
                "special_rules": []
            }
        },

        "tool_home_rules": {
            "thickness_le_2.5": {
                "expected_z": -13.0,
                "min_safe_z": -13.0,
                "description": "Thickness ≤ 2.5\""
            },
            "thickness_2.75_3.75": {
                "expected_z": -11.0,
                "min_safe_z": -11.0,
                "description": "Thickness 2.75\" - 3.75\""
            },
            "thickness_4.0_5.0": {
                "expected_z": -9.0,
                "min_safe_z": -9.0,
                "description": "Thickness 4.0\" - 5.0\""
            }
        },

        "z_clearance_before_g53": 0.1
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_lathe_standards(lathe: str) -> Optional[Dict[str, Any]]:
    """
    Get complete standards dictionary for a specific lathe.

    Args:
        lathe: Lathe identifier ("L1", "L2", "L3", or "L2/L3")

    Returns:
        Standards dictionary or None if lathe not found
    """
    return VERIFICATION_STANDARDS.get(lathe)


def get_piece_type_rules(lathe: str, piece_type: str) -> Optional[Dict[str, Any]]:
    """
    Get rules for a specific piece type on a specific lathe.

    Args:
        lathe: Lathe identifier
        piece_type: Piece type (e.g., "standard", "hub_centric", "step")

    Returns:
        Piece type rules dictionary or None if not found
    """
    standards = get_lathe_standards(lathe)
    if not standards:
        return None

    return standards.get("piece_types", {}).get(piece_type)


def check_thickness_compatibility(lathe: str, thickness: float) -> Tuple[bool, Optional[str]]:
    """
    Check if thickness is compatible with lathe's range.

    Args:
        lathe: Lathe identifier
        thickness: Thickness value in inches

    Returns:
        Tuple of (is_compatible, error_message)
        - is_compatible: True if thickness is in range
        - error_message: None if compatible, error string otherwise
    """
    standards = get_lathe_standards(lathe)
    if not standards:
        return (True, None)  # Can't validate without standards

    thickness_range = standards.get("thickness_range", {})
    min_thick = thickness_range.get("min", 0)
    max_thick = thickness_range.get("max", 999)

    if thickness < min_thick:
        return (False, f"Thickness {thickness}\" below {lathe} minimum ({min_thick}\")")

    if thickness > max_thick:
        return (False, f"Thickness {thickness}\" exceeds {lathe} maximum ({max_thick}\")")

    return (True, None)


def check_od_compatibility(lathe: str, outer_diameter: float) -> Tuple[bool, Optional[str]]:
    """
    Check if outer diameter is compatible with lathe's chuck capacity.

    Args:
        lathe: Lathe identifier
        outer_diameter: OD value in inches

    Returns:
        Tuple of (is_compatible, error_message)
    """
    standards = get_lathe_standards(lathe)
    if not standards:
        return (True, None)

    chuck_capacity = standards.get("chuck_capacity", 999)

    if outer_diameter > chuck_capacity:
        return (False, f"OD {outer_diameter}\" exceeds {lathe} chuck capacity ({chuck_capacity}\")")

    return (True, None)


def check_round_size_compatibility(lathe: str, outer_diameter: float, tolerance: float = 0.05) -> Tuple[bool, Optional[str]]:
    """
    Check if OD matches one of the lathe's supported round sizes.

    Args:
        lathe: Lathe identifier
        outer_diameter: OD value in inches
        tolerance: Acceptable deviation from standard sizes (default 0.05")

    Returns:
        Tuple of (is_supported, error_message)
    """
    standards = get_lathe_standards(lathe)
    if not standards:
        return (True, None)

    round_sizes = standards.get("round_sizes", [])
    if not round_sizes:
        return (True, None)  # No size restrictions defined

    # Check if OD is within tolerance of any supported size
    for size in round_sizes:
        if abs(outer_diameter - size) <= tolerance:
            return (True, None)

    # Not a match
    sizes_str = ", ".join([f"{s}\"" for s in round_sizes])
    return (False, f"Round size {outer_diameter}\" not supported on {lathe}. Supported: {sizes_str}")


def get_tool_home_rule(lathe: str, thickness: float) -> Optional[Dict[str, Any]]:
    """
    Get expected tool home Z position rules for given thickness.

    Args:
        lathe: Lathe identifier
        thickness: Thickness value in inches

    Returns:
        Tool home rule dictionary with expected_z, min_safe_z, description
        or None if no rule applies
    """
    standards = get_lathe_standards(lathe)
    if not standards:
        return None

    tool_home_rules = standards.get("tool_home_rules", {})

    # Determine which rule applies based on thickness
    if thickness <= 2.5:
        return tool_home_rules.get("thickness_le_2.5")
    elif thickness <= 3.75:
        return tool_home_rules.get("thickness_2.75_3.75")
    elif thickness <= 5.0:
        return tool_home_rules.get("thickness_4.0_5.0")

    return None


def check_drill_depth_limit(thickness: float, hub_height: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if total part height exceeds single-operation drill depth limit.

    Args:
        thickness: Thickness value in inches
        hub_height: Optional hub height in inches

    Returns:
        Tuple of (is_within_limit, warning_message)
        - is_within_limit: True if within 4.15" limit
        - warning_message: None if OK, warning string if exceeds limit
    """
    DRILL_DEPTH_LIMIT = 4.15  # inches

    total_height = thickness
    if hub_height:
        total_height += hub_height

    if total_height > DRILL_DEPTH_LIMIT:
        return (False,
                f"Total height {total_height:.3f}\" exceeds single-op drill depth ({DRILL_DEPTH_LIMIT}\"). "
                f"Requires OP2 flip operation.")

    return (True, None)


def validate_z_travel(z_position: float, lathe: str = None) -> Tuple[bool, Optional[str]]:
    """
    Check if Z position is within travel limits.

    Args:
        z_position: Z position value (typically negative)
        lathe: Optional lathe identifier for specific limits

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Use global limit or lathe-specific limit
    if lathe:
        standards = get_lathe_standards(lathe)
        z_limit = standards.get("z_travel_limit", -15.0) if standards else -15.0
    else:
        z_limit = -15.0  # Global limit

    if z_position < z_limit:
        return (False, f"Z position {z_position}\" exceeds travel limit ({z_limit}\")")

    return (True, None)


def get_all_lathes() -> List[str]:
    """
    Get list of all lathe identifiers.

    Returns:
        List of lathe names
    """
    return list(VERIFICATION_STANDARDS.keys())


def get_all_piece_types(lathe: str = None) -> List[str]:
    """
    Get list of all piece types, optionally filtered by lathe.

    Args:
        lathe: Optional lathe identifier to filter by

    Returns:
        List of piece type names
    """
    if lathe:
        standards = get_lathe_standards(lathe)
        if standards:
            return list(standards.get("piece_types", {}).keys())
        return []

    # Get unique piece types across all lathes
    all_types = set()
    for lathe_name in VERIFICATION_STANDARDS.keys():
        standards = get_lathe_standards(lathe_name)
        if standards:
            all_types.update(standards.get("piece_types", {}).keys())

    return sorted(list(all_types))


def format_standards_summary(lathe: str) -> str:
    """
    Generate human-readable summary of standards for a lathe.

    Args:
        lathe: Lathe identifier

    Returns:
        Formatted string with standards summary
    """
    standards = get_lathe_standards(lathe)
    if not standards:
        return f"No standards defined for {lathe}"

    lines = []
    lines.append(f"=== {standards['name']} ({lathe}) ===")
    lines.append(f"Chuck Capacity: {standards['chuck_capacity']}\"")
    lines.append(f"Supported Sizes: {', '.join([str(s) for s in standards['round_sizes']])}\"")

    thickness_range = standards['thickness_range']
    lines.append(f"Thickness Range: {thickness_range['min']}\" - {thickness_range['max']}\"")
    lines.append(f"Drill Depth Limit: {standards['drill_depth_limit']}\"")

    lines.append(f"\nPiece Types ({len(standards['piece_types'])}):")
    for pt_name, pt_rules in standards['piece_types'].items():
        status = "✓" if pt_rules['allowed'] else "✗"
        min_t, max_t = pt_rules['thickness_limits']
        lines.append(f"  {status} {pt_name}: {min_t}\" - {max_t}\"")

    return "\n".join(lines)
