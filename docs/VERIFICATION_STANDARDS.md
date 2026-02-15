# G-Code Program Verification Standards

**Version 1.0** | Last Updated: 2026-02-06

## Overview

This document defines the verification standards for G-code programs in the G-Code Database Manager. These standards ensure that programs are physically runnable on their assigned lathes and meet manufacturing requirements before reaching the shop floor.

## Purpose

The verification system checks two levels:
1. **Correctness Validation**: Is the G-code syntactically correct? (CB/OB tolerances, P-code pairing, etc.)
2. **Feasibility Validation**: Can this program physically run on the assigned lathe? (Chuck capacity, thickness range, etc.)

This document focuses on **Feasibility Validation** standards.

---

## Lathe Specifications

### L1 - Small Parts Lathe

| Specification | Value |
|---------------|-------|
| **Supported Round Sizes** | 5.75", 6.0", 6.25", 6.5" |
| **Chuck Capacity** | 8.0" maximum |
| **Thickness Range** | 0.394" (10MM) to 4.00" |
| **P-Code Table** | L1 specific table |
| **Drill Depth Limit** | 4.15" (single operation) |
| **Z Travel Limit** | -15.0" (absolute minimum) |
| **Z Home Position** | -13.0" (typical) |

**Use Case**: Exclusively handles 5.75" - 6.5" round sizes. Cannot run larger parts.

---

### L2 - Large Parts Lathe

| Specification | Value |
|---------------|-------|
| **Supported Round Sizes** | 7.0", 7.5", 8.0", 8.5", 9.5", 10.25", 10.5", 13.0" |
| **Chuck Capacity** | 15.0" maximum |
| **Thickness Range** | 1.0" to 4.00" |
| **P-Code Table** | L2/L3 shared table |
| **Drill Depth Limit** | 4.15" (single operation) |
| **Z Travel Limit** | -15.0" |
| **Z Home Position** | -13.0" |

**Use Case**: Handles large parts from 7" to 13". Some sizes (7"-8.5") shared with L3.

---

### L3 - Shared Sizes Lathe

| Specification | Value |
|---------------|-------|
| **Supported Round Sizes** | 7.0", 7.5", 8.0", 8.5" |
| **Chuck Capacity** | 10.0" maximum |
| **Thickness Range** | 1.0" to 4.00" |
| **P-Code Table** | L2/L3 shared table |
| **Drill Depth Limit** | 4.15" (single operation) |
| **Z Travel Limit** | -15.0" |
| **Z Home Position** | -13.0" |

**Use Case**: Handles 7"-8.5" sizes only. Shares these sizes with L2.

---

### L2/L3 - Hybrid Designation

When a program is designated **L2/L3**, it means the part can run on either L2 or L3 (typically 7"-8.5" sizes). The system validates against the **more restrictive** constraints:
- Uses L3's chuck capacity (10.0")
- Uses shared round sizes only (7"-8.5")
- Uses L2/L3 P-code table

---

## Piece Type Compatibility

### Standard Piece

**Description**: Single bore spacer with no hub or special features.

| Lathe | Allowed | Thickness Range | Notes |
|-------|---------|-----------------|-------|
| L1 | ✓ Yes | 0.394" - 4.0" | All thicknesses supported |
| L2 | ✓ Yes | 1.0" - 4.0" | Minimum 1.0" for L2 |
| L3 | ✓ Yes | 1.0" - 4.0" | Minimum 1.0" for L3 |

---

### Hub-Centric Piece

**Description**: CB/OB with 0.50" hub height.

| Lathe | Allowed | Thickness Range | Hub Height | Notes |
|-------|---------|-----------------|------------|-------|
| L1 | ✓ Yes | 0.5" - 4.0" | Max 0.75" | Min 0.5" for hub clearance |
| L2 | ✓ Yes | 1.0" - 4.0" | Max 0.75" | Standard hub: 0.50" |
| L3 | ✓ Yes | 1.0" - 4.0" | Max 0.75" | Standard hub: 0.50" |

**Special Rules**:
- Hub height typically 0.50"
- Maximum hub height: 0.75"
- Total height (thickness + hub) must not exceed 4.15" for single operation

---

### STEP Piece

**Description**: Counterbore with shelf at specific depth (0.30"-0.32").

| Lathe | Allowed | Thickness Range | Shelf Depth | Notes |
|-------|---------|-----------------|-------------|-------|
| L1 | ✓ Yes | 0.5" - 4.0" | 0.28" - 0.35" | Typical: 0.31" |
| L2 | ✓ Yes | 1.0" - 4.0" | 0.28" - 0.35" | Typical: 0.31" |
| L3 | ✓ Yes | 1.0" - 4.0" | 0.28" - 0.35" | Typical: 0.31" |

**Special Rules**:
- Shelf depth must be within tolerance range
- Requires precise counterbore positioning

---

### 2PC LUG (Receiver)

**Description**: Thick receiver part with shelf for 2-piece assembly.

| Lathe | Allowed | Thickness Range | Notes |
|-------|---------|-----------------|-------|
| L1 | ✓ Yes | 1.0" - 4.0" | Thick part only |
| L2 | ✓ Yes | 1.0" - 4.0" | |
| L3 | ✓ Yes | 1.0" - 4.0" | |

**Special Rules**:
- Minimum thickness: 1.0" (receiver is always thick)
- Paired with 2PC STUD insert

---

### 2PC STUD (Insert)

**Description**: Thin insert part with 0.25" hub for 2-piece assembly.

| Lathe | Allowed | Thickness Range | Hub Height | Notes |
|-------|---------|-----------------|------------|-------|
| L1 | ✓ Yes | 0.394" - 0.75" | Typical 0.25" | Thin insert only |
| L2 | ✓ Yes | 1.0" - 4.0" | Typical 0.25" | L2 can handle thicker studs |
| L3 | ✓ Yes | 1.0" - 4.0" | Typical 0.25" | L3 can handle thicker studs |

**Special Rules**:
- L1: Maximum thickness 0.75" (thin inserts only)
- L2/L3: Can handle thicker stud variations
- Paired with 2PC LUG receiver

---

### Steel Ring

**Description**: Steel material spacer (versus standard aluminum).

| Lathe | Allowed | Thickness Range | Material | Notes |
|-------|---------|-----------------|----------|-------|
| L1 | ✓ Yes | 0.394" - 4.0" | Steel | May require different speeds/feeds |
| L2 | ✓ Yes | 1.0" - 4.0" | Steel | |
| L3 | ✓ Yes | 1.0" - 4.0" | Steel | |

**Special Rules**:
- Material-specific tool wear considerations
- May require adjusted cutting parameters

---

### Metric Spacer

**Description**: Metric dimensioned spacer.

| Lathe | Allowed | Thickness Range | Notes |
|-------|---------|-----------------|-------|
| L1 | ✓ Yes | 0.394" - 4.0" | Dimensions in metric |
| L2 | ✓ Yes | 1.0" - 4.0" | |
| L3 | ✓ Yes | 1.0" - 4.0" | |

**Special Rules**:
- Metric dimensions converted for validation
- 10MM minimum = 0.394"

---

### 2PC Unsure

**Description**: 2-piece part with unclear type classification.

| Lathe | Allowed | Thickness Range | Notes |
|-------|---------|-----------------|-------|
| L1 | ✓ Yes | 0.394" - 4.0" | Type needs verification |
| L2 | ✓ Yes | 1.0" - 4.0" | |
| L3 | ✓ Yes | 1.0" - 4.0" | |

**Special Rules**:
- Manual verification recommended
- May need reclassification as LUG or STUD

---

## Physical Constraints

### Chuck Capacity

Programs are checked against the lathe's chuck capacity. If the outer diameter exceeds the chuck capacity, the program **cannot physically run** on that lathe.

| Lathe | Chuck Capacity | Action if Exceeded |
|-------|----------------|-------------------|
| L1 | 8.0" | CRITICAL - Program blocked |
| L2 | 15.0" | CRITICAL - Program blocked |
| L3 | 10.0" | CRITICAL - Program blocked |
| L2/L3 | 10.0" (L3 limit) | CRITICAL - Program blocked |

**Example**: An 11" OD part assigned to L1 (8.0" capacity) will fail feasibility validation.

---

### Thickness Range

Each lathe has minimum and maximum thickness limits based on P-code tables.

| Lathe | Minimum | Maximum | P-Code Table |
|-------|---------|---------|--------------|
| L1 | 0.394" (10MM) | 4.00" | L1 table |
| L2 | 1.0" | 4.00" | L2/L3 table |
| L3 | 1.0" | 4.00" | L2/L3 table |
| L2/L3 | 1.0" | 4.00" | L2/L3 table |

**Action if Violated**: CRITICAL - Program blocked.

---

### Drill Depth Limit

All lathes have a **4.15" single-operation drill depth limit**. If total height (thickness + hub height) exceeds this, the part requires an OP2 flip operation.

**Formula**: `Total Height = Thickness + Hub Height`

| Total Height | Status | Action |
|--------------|--------|--------|
| ≤ 4.15" | OK | Single operation |
| > 4.15" | WARNING | Requires OP2 flip |

**Example**: A 3.75" thick hub-centric part with 0.50" hub has total height 4.25", requiring OP2.

---

### Round Size Compatibility

Each lathe only supports specific round sizes (stock material diameters).

| Lathe | Supported Sizes |
|-------|-----------------|
| L1 | 5.75", 6.0", 6.25", 6.5" |
| L2 | 7.0", 7.5", 8.0", 8.5", 9.5", 10.25", 10.5", 13.0" |
| L3 | 7.0", 7.5", 8.0", 8.5" |
| L2/L3 | 7.0", 7.5", 8.0", 8.5" (shared sizes only) |

**Tolerance**: ±0.05" from standard size is acceptable.

**Action if Not Supported**: CRITICAL - Part size not available for this lathe.

---

## Tool Home Safety Rules

G53 tool home/tool change commands require specific Z clearance for safety.

### Minimum Safe Clearance

Before executing G53 tool home, the tool must be at **Z ≥ 0.1** (0.100" above Z0).

| Z Position Before G53 | Status | Risk |
|----------------------|--------|------|
| Z < 0 (below surface) | CRITICAL ⛔ | Tool will crash into part |
| 0 ≤ Z < 0.1 | WARNING ⚠️ | Insufficient clearance |
| Z ≥ 0.1 | PASS ✅ | Safe clearance |

**Validation**: Parser looks back 30 lines before each G53 to find the last Z movement.

### Expected Tool Home Z Positions

Tool home Z position varies by part thickness:

| Thickness Range | Expected Z Home | Description |
|-----------------|----------------|-------------|
| ≤ 2.5" | Z-13.0 | Thin parts |
| 2.75" - 3.75" | Z-11.0 | Medium parts |
| 4.0" - 5.0" | Z-9.0 | Thick parts |

**Note**: These are expected values. Actual tool home position depends on part setup.

---

## Validation Severity Levels

### CRITICAL (❌ RED)
- **Physical impossibility**: Program cannot run as written
- **Examples**:
  - OD exceeds chuck capacity
  - Thickness outside lathe's range
  - Round size not supported on lathe
  - Z position below surface before G53 tool home
  - Z travel exceeds machine limits

**Action**: Program **blocked** from production. Must be corrected.

---

### WARNING (⚠️ YELLOW)
- **Potential issue**: Program may work but requires attention
- **Examples**:
  - Total height > 4.15" (needs OP2)
  - Z clearance < 0.1" before G53
  - Thickness at edge of typical range
  - Piece type characteristics unusual

**Action**: Program flagged for review. May proceed with caution.

---

### PASS (✅ GREEN)
- **Feasible**: Program meets all standards
- **No issues** detected in feasibility validation

**Action**: Program approved for production (pending correctness validation).

---

## Troubleshooting Common Issues

### "OD exceeds chuck capacity"

**Cause**: Part outer diameter is larger than lathe's chuck can hold.

**Solutions**:
1. Reassign program to larger lathe (L2 has 15" capacity)
2. Check if OD is correct in program
3. Verify lathe assignment is appropriate

---

### "Round size not supported on this lathe"

**Cause**: Stock size not available for assigned lathe.

**Solutions**:
1. Check available sizes for lathe
2. Reassign to correct lathe for this size
3. For 7"-8.5" sizes: Use L2, L3, or L2/L3 designation

---

### "Thickness below lathe minimum"

**Cause**: Part too thin for lathe's P-code table.

**Solutions**:
1. L1 can handle thinner parts (0.394" min)
2. L2/L3 require 1.0" minimum
3. Check thickness value in program

---

### "Total height exceeds drill depth limit"

**Cause**: Thickness + hub height > 4.15".

**Solutions**:
1. This is not an error - OP2 flip operation required
2. Ensure program includes OP2 instructions
3. Verify total height calculation is correct

---

### "CRITICAL: G53 executed while Z < 0"

**Cause**: Tool home command executed while tool is below part surface.

**Solutions**:
1. Add Z clearance move before G53 (e.g., G0 Z0.2)
2. Ensure tool retracts to safe Z before tool change
3. Check Z movements in lines before G53

---

## Quick Reference Tables

### Lathe Capacity Summary

| Lathe | Chuck (max) | Sizes | Thickness (min-max) |
|-------|-------------|-------|---------------------|
| L1 | 8.0" | 5.75-6.5" | 0.394-4.0" |
| L2 | 15.0" | 7.0-13.0" | 1.0-4.0" |
| L3 | 10.0" | 7.0-8.5" | 1.0-4.0" |
| L2/L3 | 10.0" | 7.0-8.5" | 1.0-4.0" |

### Piece Type Minimum Thickness

| Piece Type | L1 Min | L2/L3 Min | Notes |
|------------|--------|-----------|-------|
| Standard | 0.394" | 1.0" | |
| Hub-Centric | 0.5" | 1.0" | Hub clearance |
| STEP | 0.5" | 1.0" | Shelf clearance |
| 2PC LUG | 1.0" | 1.0" | Thick receiver |
| 2PC STUD | 0.394" | 1.0" | Thin insert (L1 max 0.75") |
| Steel Ring | 0.394" | 1.0" | |
| Metric | 0.394" | 1.0" | |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-06 | Initial standards documentation |

---

## Contact

For questions about verification standards or to report incorrect validations, contact the development team or submit feedback through the G-Code Database Manager.
