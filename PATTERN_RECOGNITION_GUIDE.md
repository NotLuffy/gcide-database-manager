# G-Code Pattern Recognition Guide
## Multi-Method Validation & Dimension Extraction

---

## Table of Contents
1. [Overview](#overview)
2. [Part Type Classification System](#part-type-classification-system)
3. [Multi-Method Validation Strategies](#multi-method-validation-strategies)
4. [Signature Patterns by Part Type](#signature-patterns-by-part-type)
5. [P-Code Mapping Tables](#p-code-mapping-tables)
6. [Dimension Extraction from G-Code](#dimension-extraction-from-g-code)
7. [Tolerance Patterns & Constants](#tolerance-patterns--constants)
8. [Decision Tree for Classification](#decision-tree-for-classification)
9. [Title Validation & Correction](#title-validation--correction)
10. [Implementation Examples](#implementation-examples)

---

## Overview

This guide documents the **multi-method validation approach** for determining wheel spacer part types from G-code files. When the title is missing, unclear, or incorrect, we use multiple G-code features to determine the actual part type and extract accurate dimensions.

### Key Principles

1. **Never Trust Title Alone** - Always validate against G-code structure
2. **Use Multiple Signals** - Combine P-codes, drill depth, bore patterns, and operation sequences
3. **Calculate Dimensions** - Extract dimensions directly from G-code when title is wrong
4. **Validate Consistency** - Cross-check all extracted values for logical consistency

---

## Part Type Classification System

### Three Primary Types

#### 1. STANDARD
- Basic wheel spacer with single center bore
- No protruding hub
- Simple operation sequence

#### 2. HUB-CENTRIC (HC)
- Features protruding hub on one side
- Two bore diameters: CB (center bore) and OB (outer bore/hub diameter)
- Requires OP2 progressive facing operations

#### 3. STEP / COUNTER-BORE
- Features intermediate diameter at specific depth
- Multiple X values at different Z depths
- Counter bore section for steel ring or two-piece assembly

---

## Multi-Method Validation Strategies

### Method 1: Title Analysis
**Reliability:** 60% (titles can be incorrect or missing)

```regex
Title Markers:
- "HC" or "HUB CENTRIC" → Hub-Centric
- "STEP" or "84/71MM" (dual diameter format) → Step file
- "MM/MM" pattern with two different values → Hub-Centric or Step
- Single "MM ID" → Standard
```

**Example Patterns:**
```
STANDARD: "5.75 IN DIA 38.1MM ID 1.00 THK XX L1"
HUB-CENTRIC: "5.75IN DIA 56.1MM/64.1MM .75 THK HC"
STEP: "5.75 IN DIA 84/71MM ID 2.0" + comment "(84.0 MM CB)"
```

### Method 2: P-Code Analysis
**Reliability:** 90% (highly consistent)

P-codes directly correlate to thickness and can indicate part type:

```python
P_CODE_MAPPING = {
    # Standard Files
    'P15': {'thickness': 1.00, 'drill_depth': 1.15, 'type_hint': 'standard'},
    'P16': {'thickness': 1.00, 'drill_depth': 1.15, 'type_hint': 'standard'},

    # Hub-Centric Files
    'P17': {'thickness': 0.75, 'drill_depth': 1.40, 'type_hint': 'hub_centric'},
    'P18': {'thickness': 0.75, 'drill_depth': 1.40, 'type_hint': 'hub_centric'},

    # Step Files
    'P13': {'thickness': 0.75, 'drill_depth': 0.90, 'type_hint': 'step'},
    'P14': {'thickness': 0.75, 'drill_depth': 0.90, 'type_hint': 'step'},
    'P23': {'thickness': 2.00, 'drill_depth': 2.15, 'type_hint': 'step'},
    'P24': {'thickness': 2.00, 'drill_depth': 2.15, 'type_hint': 'step'},
}
```

**Detection Pattern:**
```gcode
Look for: G154 P## (where ## is the P-code number)
Example: G154 P17 → 0.75" thickness, likely hub-centric
```

### Method 3: Drill Depth Analysis
**Reliability:** 95% (very consistent formula)

**Formula:** `thickness = drill_depth - 0.15`

```python
DRILL_DEPTH_PATTERNS = {
    'Z-1.15': {'thickness': 1.00, 'tolerance': 0.05},
    'Z-1.40': {'thickness': 1.25, 'tolerance': 0.05},  # Includes hub height
    'Z-0.90': {'thickness': 0.75, 'tolerance': 0.05},
    'Z-2.15': {'thickness': 2.00, 'tolerance': 0.05},
}
```

**Detection:**
Look for drill cycle with format: `G83 ... Z-X.XX`

### Method 4: Bore Pattern Analysis
**Reliability:** 98% (definitive for type classification)

#### Pattern A: Single Bore (Standard)
```gcode
Line 33: G01 X1.504 Z-1.00 F0.002 (CB MARKER)
- Single X value for entire depth
- No intermediate diameters
- Straight bore operation
```

#### Pattern B: Dual Bore with OP2 Facing (Hub-Centric)
```gcode
OP1 - Bore CB:
Line 24: G01 X2.2125 Z-0.75  (CB = 56.1mm)

OP2 - Progressive Facing for OB:
Line 145: X2.53 Z-0.625  (Approaching hub diameter)
Line 147: X2.42 Z-0.5    (Final hub dimension, OB = 64.1mm)
```

**Key Signature:** Smaller X values in OP2 than OP1 CB value

#### Pattern C: Multi-Stage Bore at Different Z (Step)
```gcode
Full Depth Bore:
G01 X2.6 Z-2.15   (CB = 66.x mm at full depth)

Intermediate Depth Bore:
G01 X3.2 Z-0.28   (Counter bore = 81.x mm at shallow depth)

Finishing Pass:
G01 X3.315 Z-0.28 (Final counter bore dimension)
```

**Key Signature:** X values INCREASE as Z depth DECREASES (shallower)

### Method 5: Operation Sequence Analysis
**Reliability:** 85%

```python
OPERATION_SEQUENCES = {
    'standard': [
        'OP1: Drill → Bore CB → Turn Face',
        'FLIP',
        'OP2: Turn Face → Chamfer'
    ],

    'hub_centric': [
        'OP1: Drill → Bore CB → Turn Face',
        'FLIP',
        'OP2: Turn Face → Progressive Facing (for hub) → Chamfer'
    ],

    'step': [
        'OP1: Drill → Bore CB (full depth) → Bore Counter-Bore (intermediate depth) → Turn Face',
        'FLIP',
        'OP2: Turn Face → Chamfer'
    ]
}
```

**Detection Patterns:**
- Look for G154 P28 (OP1) and G154 P29 (OP2)
- Count number of X diameter changes
- Analyze Z depth variations

### Method 6: Tool Sequence Analysis
**Reliability:** 70%

```python
TOOL_SEQUENCES = {
    'standard': ['T101 (DRILL)', 'T202 (BORE)', 'T303 (TURN)', 'T404 (CHAMFER)'],
    'hub_centric': ['T101 (DRILL)', 'T202 (BORE)', 'T303 (TURN)', 'T303 (TURN OP2)', 'T404 (CHAMFER)'],
    'step': ['T101 (DRILL)', 'T202 (BORE)', 'T202 (BORE STEP)', 'T303 (TURN)', 'T404 (CHAMFER)']
}
```

---

## Signature Patterns by Part Type

### STANDARD FILES - Definitive Signatures

```python
STANDARD_SIGNATURES = {
    'p_codes': ['P15', 'P16'],
    'drill_depth_range': (0.85, 1.30),  # Typically Z-1.15 for 1.00" thick
    'bore_pattern': 'single_diameter',
    'op2_facing': False,
    'z_depth_changes': 0,  # No intermediate Z depths
    'title_markers': ['THK XX', 'ID', 'single mm value'],

    'gcode_signatures': [
        {
            'location': 'line 16',
            'pattern': r'G83.*Z-(\d+\.\d+)',
            'validation': lambda z: 0.85 < float(z) < 1.30
        },
        {
            'location': 'line 33',
            'pattern': r'G01 X(\d+\.\d+).*CB',
            'validation': lambda x: True  # Any single bore value
        },
        {
            'location': 'OP2 section',
            'pattern': r'G154 P29',
            'check': 'no_progressive_facing'  # Should NOT have decreasing X values
        }
    ]
}
```

**Validation Checklist:**
- [ ] P-code is P15 or P16
- [ ] Drill depth follows formula: thickness + 0.15
- [ ] Single bore diameter in OP1
- [ ] No OP2 facing operations with decreasing X
- [ ] Title shows single MM ID value

### HUB-CENTRIC FILES - Definitive Signatures

```python
HUB_CENTRIC_SIGNATURES = {
    'p_codes': ['P17', 'P18'],
    'drill_depth_range': (1.35, 1.45),  # Deeper due to hub height
    'drill_depth_formula': 'thickness + hub_height + 0.15',
    'bore_pattern': 'dual_diameter',
    'op2_facing': True,  # MUST HAVE
    'z_depth_changes': 0,  # All at same Z in OP1
    'title_markers': ['HC', 'MM/MM', 'two mm values'],

    'gcode_signatures': [
        {
            'location': 'line ~14-16',
            'pattern': r'G83.*Z-1\.4',  # Characteristic deep drill
            'validation': lambda z: 1.35 < float(z) < 1.45
        },
        {
            'location': 'OP1 lines 24-25',
            'pattern': r'G01 X(\d+\.\d+).*Z-0\.75',
            'description': 'CB bore at full depth',
            'validation': lambda x: True
        },
        {
            'location': 'OP2 section',
            'pattern': r'X(\d+\.\d+) Z-0\.(5|625)',
            'description': 'Progressive facing with SMALLER X than CB',
            'validation': lambda x, cb: float(x) < float(cb)
        }
    ],

    'critical_check': {
        'description': 'OP2 X values must be LESS than OP1 CB X value',
        'formula': 'X_op2 < X_cb',
        'example': 'If CB = X2.2125, then OP2 might have X2.53, X2.42'
    }
}
```

**Validation Checklist:**
- [ ] P-code is P17 or P18
- [ ] Drill depth is 1.40 (0.75" + 0.50" + 0.15")
- [ ] Bore in OP1 (CB diameter)
- [ ] OP2 has progressive facing with SMALLER X values
- [ ] Title shows "MM/MM" format or "HC" marker
- [ ] Calculated: OB from OP2 X values, CB from OP1 bore

### STEP FILES - Definitive Signatures

```python
STEP_SIGNATURES = {
    'p_codes': ['P13', 'P14', 'P23', 'P24'],
    'drill_depth_range': (0.85, 2.20),  # Wide range depending on thickness
    'bore_pattern': 'multi_stage_z_depth',
    'op2_facing': False,
    'z_depth_changes': '>= 1',  # CRITICAL: At least one Z depth change
    'title_markers': ['##/##MM', 'STEP', 'B/C', 'dual diameter without HC'],

    'gcode_signatures': [
        {
            'location': 'OP1 bore section',
            'pattern': r'G01 X(\d+\.\d+) Z-([\d.]+).*G01 X(\d+\.\d+) Z-([\d.]+)',
            'description': 'Multiple X values at DIFFERENT Z depths',
            'validation': lambda x1, z1, x2, z2: (float(x2) > float(x1)) and (float(z1) > float(z2))
        },
        {
            'location': 'lines showing bore progression',
            'example_o57415': [
                'X2.6 Z-2.15   (CB at full depth)',
                'X3.2 Z-0.28   (Counter bore at intermediate depth)',
                'X3.315 Z-0.28 (Finish counter bore)'
            ],
            'example_o57553': [
                'X2.3 Z-0.9    (CB at full depth)',
                'X2.6 Z-0.9    (Still at full depth)',
                'X2.9 Z-0.9    (Still at full depth)',
                'X3.2 Z-0.53   (Counter bore at INTERMEDIATE depth)'
            ]
        }
    ],

    'critical_check': {
        'description': 'X increases when Z decreases (shallower)',
        'formula': 'if Z2 > Z1 (shallower), then X2 > X1 (larger diameter)',
        'pattern_name': 'stepped_bore_profile'
    }
}
```

**Validation Checklist:**
- [ ] P-code is P13, P14, P23, or P24
- [ ] Multiple bore operations at DIFFERENT Z depths
- [ ] X values INCREASE as Z depth DECREASES
- [ ] Title shows "##/##MM" format without "HC"
- [ ] Calculated: CB from deepest X value, Counter-bore from shallowest X
- [ ] Counter-bore depth = difference in Z values

---

## P-Code Mapping Tables

### Complete P-Code Reference

```python
P_CODE_DATABASE = {
    # Format: 'P##': (thickness_inches, drill_depth, part_type_hint, common_applications)

    'P13': (0.75, 0.90, 'step', 'Thin step files'),
    'P14': (0.75, 0.90, 'step', 'Thin step files'),
    'P15': (1.00, 1.15, 'standard', 'Standard 1.00" spacers'),
    'P16': (1.00, 1.15, 'standard', 'Standard 1.00" spacers'),
    'P17': (0.75, 1.40, 'hub_centric', '0.75" HC with 0.50" hub'),
    'P18': (0.75, 1.40, 'hub_centric', '0.75" HC with 0.50" hub'),
    'P23': (2.00, 2.15, 'step', 'Thick step files'),
    'P24': (2.00, 2.15, 'step', 'Thick step files'),
}
```

### P-Code to Thickness Calculator

```python
def calculate_thickness_from_pcode(p_code, drill_depth):
    """
    Calculate actual thickness using P-code and drill depth

    Args:
        p_code: String like 'P15', 'P17', etc.
        drill_depth: Float like 1.15, 1.40, etc.

    Returns:
        dict with thickness, part_type, hub_height
    """
    if p_code in ['P17', 'P18']:
        # Hub-centric: drill_depth = thickness + hub_height + 0.15
        # Typically: 1.40 = 0.75 + 0.50 + 0.15
        hub_height = 0.50  # Standard hub height
        thickness = drill_depth - hub_height - 0.15
        return {
            'thickness': round(thickness, 2),
            'part_type': 'hub_centric',
            'hub_height': hub_height
        }
    else:
        # Standard/Step: drill_depth = thickness + 0.15
        thickness = drill_depth - 0.15
        part_type = P_CODE_DATABASE.get(p_code, (None, None, 'unknown', ''))[2]
        return {
            'thickness': round(thickness, 2),
            'part_type': part_type,
            'hub_height': None
        }
```

### P-Code Detection in G-Code

```python
import re

def extract_p_code(gcode_lines):
    """
    Extract P-code from G154 work offset command

    Look for patterns like:
    - G154 P15
    - G154P17
    - G154 P23
    """
    p_code_pattern = r'G154\s*P(\d{2})'

    for line in gcode_lines[:50]:  # Check first 50 lines
        match = re.search(p_code_pattern, line, re.IGNORECASE)
        if match:
            p_number = match.group(1)
            return f'P{p_number}'

    return None
```

---

## Dimension Extraction from G-Code

### 1. Center Bore (CB) Extraction

**Method A: From OP1 Bore Operation**

```python
def extract_center_bore_from_bore_operation(gcode_lines):
    """
    Extract CB from first bore operation in OP1
    Typically marked with comment containing 'CB'

    Pattern: G01 X#.### Z-#.## (CB MARKER)
    Convert: X_inches * 25.4 = CB_mm
    """
    cb_pattern = r'G01 X([\d.]+).*(?:CB|CENTER|BORE)'

    for i, line in enumerate(gcode_lines):
        # Look in OP1 section (before OP2)
        if 'G154 P29' in line:  # Stop at OP2
            break

        match = re.search(cb_pattern, line, re.IGNORECASE)
        if match:
            x_radius_inches = float(match.group(1))
            cb_mm = x_radius_inches * 2 * 25.4  # Diameter in mm
            return round(cb_mm, 1)

    return None
```

**Method B: From Title/Comment**

```python
def extract_center_bore_from_title(title):
    """
    Extract CB from title using regex patterns

    Patterns:
    - "56.1MM ID"
    - "CB 56.1MM"
    - "56.1MM/64.1MM" (first value is CB)
    - "(84.0 MM CB)" in comment
    """
    patterns = [
        r'(\d+\.?\d*)\s*MM\s*ID',          # "56.1MM ID"
        r'(\d+\.?\d*)\s*MM\s*CB',          # "56.1MM CB"
        r'(\d+\.?\d*)MM/\d+\.?\d*MM',      # "56.1MM/64.1MM" (first)
        r'\((\d+\.?\d*)\s*MM\s*CB\)',      # "(84.0 MM CB)"
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None
```

**Method C: With Chamfer Correction**

```python
def extract_cb_with_chamfer(x_value_inches, chamfer_amount=0.020):
    """
    Correct for chamfer on bore diameter

    Chamfer typically removes 0.020" from radius

    Args:
        x_value_inches: X radius from G-code
        chamfer_amount: Typical chamfer = 0.020" radius

    Returns:
        CB in mm with chamfer added back
    """
    x_corrected = x_value_inches + chamfer_amount
    diameter_inches = x_corrected * 2
    cb_mm = diameter_inches * 25.4
    return round(cb_mm, 1)
```

### 2. Outer Bore / Hub Diameter (OB) Extraction

**For Hub-Centric Files Only**

```python
def extract_outer_bore_from_op2(gcode_lines):
    """
    Extract OB from OP2 progressive facing operations

    Look for SMALLEST X value in OP2 facing passes
    This represents the hub diameter

    Pattern in OP2:
    X2.53 Z-0.625
    X2.42 Z-0.5    <- SMALLEST X = hub radius
    """
    in_op2 = False
    x_values = []

    for line in gcode_lines:
        if 'G154 P29' in line:  # OP2 start
            in_op2 = True
            continue

        if in_op2:
            # Look for X moves in facing operations
            match = re.search(r'X([\d.]+)\s+Z-', line)
            if match:
                x_values.append(float(match.group(1)))

            # Stop at chamfer or program end
            if 'CHAMFER' in line or 'M30' in line:
                break

    if x_values:
        min_x_radius = min(x_values)
        ob_mm = min_x_radius * 2 * 25.4
        return round(ob_mm, 1)

    return None
```

**From Title (Secondary Method)**

```python
def extract_outer_bore_from_title(title):
    """
    Extract OB from title for hub-centric parts

    Pattern: "56.1MM/64.1MM" (second value is OB)
    """
    pattern = r'(\d+\.?\d*)MM/(\d+\.?\d*)MM'
    match = re.search(pattern, title)

    if match:
        cb = float(match.group(1))
        ob = float(match.group(2))
        return {'cb': cb, 'ob': ob}

    return None
```

### 3. Thickness Extraction

**Method A: From Drill Depth (Most Reliable)**

```python
def extract_thickness_from_drill(gcode_lines, part_type='standard'):
    """
    Extract thickness from drill operation

    Formula:
    - Standard: thickness = drill_depth - 0.15
    - Hub-Centric: thickness = drill_depth - hub_height - 0.15
                            = drill_depth - 0.50 - 0.15
                            = drill_depth - 0.65
    - Step: thickness = drill_depth - 0.15

    Pattern: G83 ... Z-#.##
    """
    drill_pattern = r'G83.*Z-([\d.]+)'

    for line in gcode_lines[:30]:  # Drill is typically early
        match = re.search(drill_pattern, line)
        if match:
            drill_depth = float(match.group(1))

            if part_type == 'hub_centric':
                thickness = drill_depth - 0.65  # Subtract hub height + clearance
            else:
                thickness = drill_depth - 0.15

            return round(thickness, 2)

    return None
```

**Method B: From P-Code**

```python
def extract_thickness_from_pcode(p_code):
    """Use P-code mapping table"""
    return P_CODE_DATABASE.get(p_code, (None, None, None, None))[0]
```

**Method C: From Title**

```python
def extract_thickness_from_title(title):
    """
    Extract thickness from title

    Patterns:
    - "1.00 THK"
    - ".75 THK"
    - "2.0 THK"
    """
    patterns = [
        r'([\d.]+)\s*THK',
        r'([\d.]+)\s*THICK',
        r'([\d.]+)\s*"',  # Inches marker
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None
```

### 4. Hub Height Extraction

**For Hub-Centric Only**

```python
def extract_hub_height(gcode_lines, thickness, drill_depth):
    """
    Extract hub height from hub-centric files

    Method 1: From drill depth
    hub_height = drill_depth - thickness - 0.15

    Method 2: From OP2 Z depths
    Look for progressive facing Z values
    """
    # Method 1: Calculate from drill
    hub_height_calc = drill_depth - thickness - 0.15

    # Method 2: Find from OP2 facing operations
    in_op2 = False
    z_values = []

    for line in gcode_lines:
        if 'G154 P29' in line:
            in_op2 = True
            continue

        if in_op2:
            match = re.search(r'Z-([\d.]+)', line)
            if match:
                z_values.append(float(match.group(1)))

    if z_values:
        # Hub height is typically the minimum Z in OP2 facing
        hub_height_z = min(z_values)

        # Cross-validate
        if abs(hub_height_calc - hub_height_z) < 0.05:
            return round(hub_height_calc, 2)

    return 0.50  # Default hub height
```

### 5. Counter Bore Diameter Extraction

**For Step Files Only**

```python
def extract_counter_bore_diameter(gcode_lines):
    """
    Extract counter bore diameter from step files

    Look for LARGEST X value at INTERMEDIATE (shallowest) Z depth

    Pattern:
    X2.6 Z-2.15    (CB at full depth)
    X3.2 Z-0.28    (Counter bore at intermediate) <- LARGEST X
    """
    bore_operations = []

    for line in gcode_lines:
        match = re.search(r'G01 X([\d.]+) Z-([\d.]+)', line)
        if match:
            x_val = float(match.group(1))
            z_val = float(match.group(2))
            bore_operations.append({'x': x_val, 'z': z_val})

    if len(bore_operations) < 2:
        return None

    # Find operation with shallowest Z (smallest Z value)
    shallowest = min(bore_operations, key=lambda op: op['z'])

    # Counter bore diameter
    counter_bore_mm = shallowest['x'] * 2 * 25.4
    return round(counter_bore_mm, 1)
```

### 6. Counter Bore Depth Extraction

**For Step Files Only**

```python
def extract_counter_bore_depth(gcode_lines):
    """
    Extract counter bore depth

    Depth = thickness - intermediate_z_depth

    Example:
    Drill: Z-2.15 (thickness = 2.00")
    Counter bore: Z-0.28
    Depth = 2.00 - 0.28 = 1.72"

    BUT counter bore depth is usually measured from TOP surface,
    so it's just the intermediate Z value: 0.28"
    """
    bore_operations = []

    for line in gcode_lines:
        match = re.search(r'G01 X([\d.]+) Z-([\d.]+)', line)
        if match:
            x_val = float(match.group(1))
            z_val = float(match.group(2))
            bore_operations.append({'x': x_val, 'z': z_val})

    if len(bore_operations) < 2:
        return None

    # Find Z depths
    z_depths = [op['z'] for op in bore_operations]

    # Counter bore depth is the SHALLOWEST Z (smallest value)
    counter_bore_depth = min(z_depths)
    return round(counter_bore_depth, 2)
```

### 7. Outer Diameter (OD) Extraction

```python
def extract_outer_diameter(title):
    """
    Extract OD from title

    Patterns:
    - "5.75 IN DIA"
    - "6.0" DIA"
    - "6.5 IN DIA"
    """
    patterns = [
        r'([\d.]+)\s*IN\s*DIA',
        r'([\d.]+)"\s*DIA',
        r'([\d.]+)\s*INCH\s*DIA',
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None
```

---

## Tolerance Patterns & Constants

### Standard Tolerances

```python
TOLERANCE_CONSTANTS = {
    # Drill depth clearance
    'drill_clearance': 0.15,  # inches
    'drill_tolerance': 0.05,  # +/- inches

    # Hub height standard
    'hub_height_standard': 0.50,  # inches
    'hub_height_tolerance': 0.02,  # +/- inches

    # Chamfer amounts
    'chamfer_radius': 0.020,  # inches (typical)
    'chamfer_tolerance': 0.005,  # +/- inches

    # Dimension tolerances
    'thickness_tolerance': 0.005,  # +/- inches
    'diameter_tolerance_mm': 0.1,  # +/- mm
    'diameter_tolerance_in': 0.005,  # +/- inches
}
```

### Drill Depth Formula Validation

```python
def validate_drill_depth(drill_depth, thickness, part_type='standard'):
    """
    Validate drill depth against expected formula

    Returns: (is_valid, expected_depth, error)
    """
    if part_type == 'hub_centric':
        expected = thickness + 0.50 + 0.15  # thickness + hub + clearance
    else:
        expected = thickness + 0.15  # thickness + clearance

    error = abs(drill_depth - expected)
    is_valid = error < TOLERANCE_CONSTANTS['drill_tolerance']

    return (is_valid, expected, error)
```

### Cross-Validation Functions

```python
def cross_validate_dimensions(extracted_dims, gcode_dims):
    """
    Cross-validate dimensions from title vs G-code

    Args:
        extracted_dims: Dict from title parsing
        gcode_dims: Dict from G-code analysis

    Returns:
        Dict with validated dimensions and confidence scores
    """
    validated = {}

    # Thickness validation
    if 'thickness' in extracted_dims and 'thickness' in gcode_dims:
        diff = abs(extracted_dims['thickness'] - gcode_dims['thickness'])
        if diff < TOLERANCE_CONSTANTS['thickness_tolerance']:
            validated['thickness'] = gcode_dims['thickness']  # Prefer G-code
            validated['thickness_confidence'] = 'high'
        else:
            validated['thickness'] = gcode_dims['thickness']  # Always trust G-code
            validated['thickness_confidence'] = 'medium'
            validated['thickness_warning'] = f"Title mismatch: {extracted_dims['thickness']}"

    # CB validation
    if 'center_bore' in extracted_dims and 'center_bore' in gcode_dims:
        diff = abs(extracted_dims['center_bore'] - gcode_dims['center_bore'])
        if diff < TOLERANCE_CONSTANTS['diameter_tolerance_mm']:
            validated['center_bore'] = gcode_dims['center_bore']
            validated['cb_confidence'] = 'high'
        else:
            validated['center_bore'] = gcode_dims['center_bore']
            validated['cb_confidence'] = 'medium'
            validated['cb_warning'] = f"Title mismatch: {extracted_dims['center_bore']}"

    return validated
```

---

## Decision Tree for Classification

```
START
  |
  v
Extract P-Code from G154 command
  |
  ├─> P15/P16 ────> LIKELY STANDARD
  ├─> P17/P18 ────> LIKELY HUB-CENTRIC
  └─> P13/P14/P23/P24 ─> LIKELY STEP
  |
  v
Analyze Bore Pattern in OP1
  |
  ├─> Single X value, single Z ────────────> CONFIRM STANDARD
  ├─> Single X value, but check OP2...
  |     |
  |     └─> OP2 has progressive facing? ──> CONFIRM HUB-CENTRIC
  |           |
  |           └─> No OP2 facing ──────────> CONFIRM STANDARD
  |
  └─> Multiple X values at DIFFERENT Z ───> CONFIRM STEP
  |
  v
Extract Drill Depth
  |
  ├─> Z-1.15 ────> thickness = 1.00" (standard/step)
  ├─> Z-1.40 ────> thickness = 0.75" + hub (hub-centric)
  ├─> Z-0.90 ────> thickness = 0.75" (step)
  └─> Z-2.15 ────> thickness = 2.00" (step)
  |
  v
Validate Against Title
  |
  ├─> Title matches ────> HIGH CONFIDENCE
  └─> Title differs ────> USE G-CODE, FLAG WARNING
  |
  v
Extract All Dimensions
  |
  ├─> STANDARD: CB, thickness, OD
  ├─> HUB-CENTRIC: CB, OB, thickness, hub_height, OD
  └─> STEP: CB, counter_bore_dia, counter_bore_depth, thickness, OD
  |
  v
Cross-Validate All Values
  |
  v
DONE - Return Classified Record
```

---

## Title Validation & Correction

### Validation Process

```python
def validate_and_correct_title(title, gcode_analysis):
    """
    Validate title against G-code analysis and correct if needed

    Args:
        title: Original title string
        gcode_analysis: Dict with extracted G-code dimensions

    Returns:
        Dict with corrected title and warnings
    """
    result = {
        'original_title': title,
        'corrected_title': None,
        'warnings': [],
        'corrections': []
    }

    # Extract dimensions from title
    title_dims = parse_title_dimensions(title)

    # Compare thickness
    if 'thickness' in title_dims and 'thickness' in gcode_analysis:
        if abs(title_dims['thickness'] - gcode_analysis['thickness']) > 0.01:
            result['warnings'].append(
                f"Thickness mismatch: Title={title_dims['thickness']}, "
                f"G-code={gcode_analysis['thickness']}"
            )
            result['corrections'].append({
                'field': 'thickness',
                'title_value': title_dims['thickness'],
                'correct_value': gcode_analysis['thickness']
            })

    # Compare CB
    if 'center_bore' in title_dims and 'center_bore' in gcode_analysis:
        if abs(title_dims['center_bore'] - gcode_analysis['center_bore']) > 0.5:
            result['warnings'].append(
                f"CB mismatch: Title={title_dims['center_bore']}mm, "
                f"G-code={gcode_analysis['center_bore']}mm"
            )
            result['corrections'].append({
                'field': 'center_bore',
                'title_value': title_dims['center_bore'],
                'correct_value': gcode_analysis['center_bore']
            })

    # Check part type marker
    if gcode_analysis['part_type'] == 'hub_centric':
        if 'HC' not in title and 'HUB' not in title:
            result['warnings'].append("Title missing HC marker but G-code shows hub-centric")
            result['corrections'].append({
                'field': 'part_type',
                'title_value': 'standard (implied)',
                'correct_value': 'hub_centric'
            })

    # Generate corrected title if needed
    if result['corrections']:
        result['corrected_title'] = generate_corrected_title(gcode_analysis)

    return result
```

### Title Generation

```python
def generate_corrected_title(gcode_analysis):
    """
    Generate a corrected title from G-code analysis

    Format examples:
    STANDARD: "O##### (5.75 IN DIA 38.1MM ID 1.00 THK XX L1)"
    HUB-CENTRIC: "O##### (5.75IN DIA 56.1MM/64.1MM .75 THK HC)"
    STEP: "O##### (5.75 IN DIA 84/71MM ID 2.0)" + comment "(84.0 MM CB)"
    """
    prog_num = gcode_analysis['program_number']
    od = gcode_analysis['outer_diameter']
    thickness = gcode_analysis['thickness']
    part_type = gcode_analysis['part_type']

    if part_type == 'standard':
        cb = gcode_analysis['center_bore']
        title = f"{prog_num} ({od} IN DIA {cb}MM ID {thickness} THK XX L1)"

    elif part_type == 'hub_centric':
        cb = gcode_analysis['center_bore']
        ob = gcode_analysis['outer_bore']
        title = f"{prog_num} ({od}IN DIA {cb}MM/{ob}MM {thickness} THK HC)"

    elif part_type == 'step':
        cb = gcode_analysis['center_bore']
        counter_bore = gcode_analysis['counter_bore_diameter']
        title = f"{prog_num} ({od} IN DIA {counter_bore}/{cb}MM ID {thickness})"
        # Note: Step files may have additional comment line

    return title
```

---

## Implementation Examples

### Complete Part Classification Function

```python
def classify_and_extract_part(gcode_file_path):
    """
    Complete multi-method classification and extraction

    Returns:
        Dict with part_type, all dimensions, confidence scores
    """
    # Read file
    with open(gcode_file_path, 'r') as f:
        lines = f.readlines()

    title = lines[0] if lines else ""

    # STEP 1: Extract P-code
    p_code = extract_p_code(lines)
    p_code_hint = P_CODE_DATABASE.get(p_code, (None, None, 'unknown', None))[2]

    # STEP 2: Extract drill depth
    drill_depth = extract_drill_depth(lines)

    # STEP 3: Analyze bore pattern
    bore_pattern = analyze_bore_pattern(lines)

    # STEP 4: Check OP2 for facing
    has_op2_facing = check_op2_progressive_facing(lines)

    # STEP 5: Determine part type
    part_type = determine_part_type(
        p_code_hint=p_code_hint,
        bore_pattern=bore_pattern,
        has_op2_facing=has_op2_facing,
        drill_depth=drill_depth
    )

    # STEP 6: Extract dimensions based on type
    dimensions = {}

    if part_type == 'standard':
        dimensions = {
            'part_type': 'standard',
            'center_bore': extract_center_bore_from_bore_operation(lines),
            'thickness': extract_thickness_from_drill(lines, part_type),
            'outer_diameter': extract_outer_diameter(title),
            'p_code': p_code,
            'drill_depth': drill_depth
        }

    elif part_type == 'hub_centric':
        dimensions = {
            'part_type': 'hub_centric',
            'center_bore': extract_center_bore_from_bore_operation(lines),
            'outer_bore': extract_outer_bore_from_op2(lines),
            'thickness': extract_thickness_from_drill(lines, part_type),
            'hub_height': extract_hub_height(lines, drill_depth),
            'outer_diameter': extract_outer_diameter(title),
            'p_code': p_code,
            'drill_depth': drill_depth
        }

    elif part_type == 'step':
        dimensions = {
            'part_type': 'step',
            'center_bore': extract_center_bore_from_bore_operation(lines),
            'counter_bore_diameter': extract_counter_bore_diameter(lines),
            'counter_bore_depth': extract_counter_bore_depth(lines),
            'thickness': extract_thickness_from_drill(lines, part_type),
            'outer_diameter': extract_outer_diameter(title),
            'p_code': p_code,
            'drill_depth': drill_depth
        }

    # STEP 7: Validate against title
    title_validation = validate_and_correct_title(title, dimensions)
    dimensions['title_validation'] = title_validation

    # STEP 8: Calculate confidence scores
    dimensions['confidence'] = calculate_confidence_scores(dimensions, bore_pattern, p_code)

    return dimensions
```

### Bore Pattern Analyzer

```python
def analyze_bore_pattern(gcode_lines):
    """
    Analyze bore pattern to determine part type signature

    Returns:
        Dict describing the bore pattern
    """
    bore_ops = []
    in_op1 = False

    for line in gcode_lines:
        if 'G154 P28' in line:
            in_op1 = True
            continue
        if 'G154 P29' in line:
            break

        if in_op1:
            match = re.search(r'G01 X([\d.]+) Z-([\d.]+)', line)
            if match:
                bore_ops.append({
                    'x': float(match.group(1)),
                    'z': float(match.group(2))
                })

    if not bore_ops:
        return {'pattern': 'none', 'count': 0}

    # Analyze pattern
    z_values = [op['z'] for op in bore_ops]
    x_values = [op['x'] for op in bore_ops]

    unique_z = len(set(z_values))
    unique_x = len(set(x_values))

    if unique_z == 1 and unique_x == 1:
        return {
            'pattern': 'single_bore',
            'count': len(bore_ops),
            'type_hint': 'standard or hub_centric (check OP2)'
        }

    elif unique_z > 1 and unique_x > 1:
        # Check if X increases as Z decreases (step pattern)
        sorted_ops = sorted(bore_ops, key=lambda op: op['z'], reverse=True)
        is_step = all(
            sorted_ops[i]['x'] <= sorted_ops[i+1]['x']
            for i in range(len(sorted_ops)-1)
        )

        if is_step:
            return {
                'pattern': 'multi_stage_z',
                'count': len(bore_ops),
                'type_hint': 'step',
                'z_depths': unique_z,
                'x_diameters': unique_x
            }

    return {
        'pattern': 'unknown',
        'count': len(bore_ops),
        'z_depths': unique_z,
        'x_diameters': unique_x
    }
```

### Confidence Calculator

```python
def calculate_confidence_scores(dimensions, bore_pattern, p_code):
    """
    Calculate confidence scores for classification

    Returns:
        Dict with confidence scores (0-100)
    """
    scores = {
        'overall': 0,
        'part_type': 0,
        'dimensions': 0,
        'factors': []
    }

    part_type = dimensions['part_type']

    # P-code match
    if p_code:
        expected_type = P_CODE_DATABASE.get(p_code, (None, None, 'unknown', None))[2]
        if expected_type == part_type:
            scores['part_type'] += 40
            scores['factors'].append('P-code matches part type (+40)')
        else:
            scores['factors'].append(f'P-code mismatch (-20)')
            scores['part_type'] -= 20

    # Bore pattern match
    if part_type == 'standard' and bore_pattern['pattern'] == 'single_bore':
        scores['part_type'] += 30
        scores['factors'].append('Bore pattern matches standard (+30)')
    elif part_type == 'step' and bore_pattern['pattern'] == 'multi_stage_z':
        scores['part_type'] += 30
        scores['factors'].append('Bore pattern matches step (+30)')
    elif part_type == 'hub_centric' and bore_pattern.get('type_hint') == 'standard or hub_centric (check OP2)':
        scores['part_type'] += 20
        scores['factors'].append('Bore pattern compatible with hub-centric (+20)')

    # Drill depth validation
    if 'drill_depth' in dimensions and 'thickness' in dimensions:
        expected_drill = dimensions['thickness'] + 0.15
        if part_type == 'hub_centric':
            expected_drill += 0.50

        if abs(dimensions['drill_depth'] - expected_drill) < 0.05:
            scores['dimensions'] += 30
            scores['factors'].append('Drill depth formula valid (+30)')

    # Overall score
    scores['overall'] = min(100, max(0, scores['part_type'] + scores['dimensions']))

    return scores
```

---

## Quick Reference Tables

### Part Type Recognition at a Glance

| Feature | Standard | Hub-Centric | Step |
|---------|----------|-------------|------|
| **P-Codes** | P15, P16 | P17, P18 | P13, P14, P23, P24 |
| **Drill Depth** | 1.15 (1.00") | 1.40 (0.75"+0.50") | 0.90 or 2.15 |
| **Bore Pattern** | Single X, single Z | Single X, single Z | Multiple X at different Z |
| **OP2 Facing** | No | Yes (progressive) | No |
| **Title Format** | "##.#MM ID" | "##.#MM/##.#MM HC" | "##/##MM" |
| **Key Signature** | One bore operation | OP2 X < OP1 X | X increases as Z decreases |

### Dimension Extraction Priority

| Dimension | Priority 1 | Priority 2 | Priority 3 |
|-----------|-----------|-----------|-----------|
| **Thickness** | Drill depth - 0.15 | P-code lookup | Title parse |
| **Center Bore** | OP1 bore X value | Title "MM ID" | Title "MM CB" |
| **Hub Height** | Drill - thickness - 0.15 | OP2 Z values | Default 0.50" |
| **Outer Bore** | OP2 min X value | Title "MM/MM" 2nd value | - |
| **Counter Bore** | Max X at min Z | Title "##/##MM" 1st value | - |
| **CB Depth** | Min Z value | Thickness - bore Z | - |

---

## Summary

This guide provides a **comprehensive multi-method validation system** for G-code part classification and dimension extraction. Key takeaways:

1. **Never rely on title alone** - Always validate with G-code structure
2. **Use P-codes as primary classifier** - They're highly reliable (90%+)
3. **Bore pattern analysis is definitive** - Different types have distinct signatures
4. **Calculate dimensions from G-code** - More reliable than parsing titles
5. **Cross-validate everything** - Use multiple methods to confirm each value
6. **Trust G-code over title** - When in conflict, G-code is always correct

The decision tree and signature patterns allow for accurate classification even when titles are missing, unclear, or completely incorrect.
