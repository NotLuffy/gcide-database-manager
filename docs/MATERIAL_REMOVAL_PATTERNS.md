# Material Removal Patterns - How G-Code Actually Works

## Understanding the Difference: What vs How

**Current Parser**: Looks at WHAT operations exist (DRILL, BORE, TURN)
**This Document**: Shows HOW material is removed (loops, increments, sequences)

---

## Pattern 1: Incremental Roughing Loops

### How Most Programmers Remove Material

Instead of taking the full cut in one pass, they **loop through increasing X values** to remove material gradually.

### Example from o13223.nc (Lines 29-58):

```gcode
T121 (BORE)
G154 P13X2.3 Z2.     <- Starting diameter 2.3" (radius)
Z0.2
G01 Z-2.15 F0.02     <- Full depth

G00 Z0.2
X2.6                 <- Increment +0.3"
G01 Z-2.15 F0.02     <- Full depth again

G00 Z0.2
X2.9                 <- Increment +0.3"
G01 Z-2.15 F0.02     <- Full depth again

G00 Z0.2
X3.2                 <- Increment +0.3"
G01 Z-2.15 F0.02     <- Full depth again

G00 Z0.2
X3.5                 <- Increment +0.3"
G01 Z-2.15 F0.02     <- Keep going...

X3.8                 <- Increment +0.3"
X4.1                 <- Increment +0.3"
X4.4                 <- Increment +0.3"
X4.902               <- LAST roughing pass

G01 Z0 F0.012        <- Switch to finish feed rate
X4.602 Z-0.15        <- FINAL DIMENSION with chamfer
(X IS CB)            <- Comment marks final centerbore diameter
```

**What's Happening**:
- 8 roughing passes: X2.3 → X2.6 → X2.9 → X3.2 → X3.5 → X3.8 → X4.1 → X4.4 → X4.902
- All increment by ~0.3" (removing material gradually)
- Final pass: X4.602 with chamfer = **ACTUAL FINAL DIMENSION**

**Parser Issue**:
- Currently extracts X4.902 (last roughing pass) as final dimension
- Should extract X4.602 (line with chamfer comment)

---

## Pattern 2: Single-Pass Operations (No Loops)

### When Programmers DON'T Use Incremental Passes

Some operations go straight to final dimension in one cut.

### Example from o57172.nc (Lines 24-35):

```gcode
T121 (BORE)
G154 P17G00 X2.6 Z0.2   <- Start at 2.6" (small roughing)
G01 Z-1.4 F0.01

X2.9                    <- One roughing pass
G01 Z-1.4 F0.01

X3.327                  <- Final diameter approach
G01 Z0 F0.01
G01 X3.087 Z-0.12 F0.008  <- FINAL with chamfer
(COMMENT: 78.4MM CB = 3.087")
Z-1.4                     <- Full depth
```

**What's Happening**:
- Only 2 roughing passes (vs 8 in previous example)
- Goes directly to final dimension X3.087
- Less looping = faster cycle time (but more tool wear)

---

## Pattern 3: Stepped Turning for Hubs (Z-Depth Loops)

### How Programmers Create Hub Profiles

Instead of incrementing X (diameter), they **loop through Z depths** to create a stepped shoulder.

### Example from o10280.nc (Lines 112-130):

```gcode
T303 (TURN TOOL)
G154 P34X10.17 Z0.1      <- Starting OD (10.17" radius)

G01 Z-0.1 F0.013         <- Depth pass 1 (0.1" deep)
X6.7                     <- Step down to hub diameter
G00 X10.17               <- Return to OD

G01 Z-0.2 F0.013         <- Depth pass 2 (increment +0.1")
X6.7                     <- Same hub diameter
G00 X10.17               <- Return to OD

G01 Z-0.4 F0.013         <- Depth pass 3 (increment +0.2")
X6.7                     <- Same hub diameter
G00 X10.17

G01 Z-0.45 F0.013        <- Depth pass 4 (increment +0.05")
X6.7
G00 X10.17

G01 Z-1.0 F0.01          <- Final depth
Z-0.55
G01 X10.12 Z-0.5 F0.009  <- Chamfer OD
G01 X6.688 F0.013        <- FINAL hub diameter
(X IS OB)                <- "OB" = Outer Bore
Z-0.05
X6.588 Z0.
```

**What's Happening**:
- Z depths increment: -0.1, -0.2, -0.4, -0.45, -0.55
- Each pass: Start at X10.17 (OD) → Cut to X6.7 (hub) → Return to X10.17
- This creates a **stepped profile**: Large OD, then step down to smaller hub diameter
- Final hub diameter: X6.688 (marked with "(X IS OB)" comment)

**Visual Result**:
```
     |<-- 10.17" OD -->|
     |                 |
     |=================|  <- Side face
     |                 |
     |                 |  <- Full OD section
     |                 |
     |=====|           |  <- Step (hub height = 0.55")
           |<- 6.688 ->|  <- Hub diameter (OB)
           |           |
           |    Hub    |
           |  Section  |
           |           |
           |===========|
```

**Parser Issue**:
- Doesn't recognize this as a hub profile
- Doesn't extract hub diameter (X6.688) or hub height (0.55")

---

## Pattern 4: Counterbore + Centerbore (Two-Step Bore)

### How Programmers Create Stepped Bores

**Side 1**: Bore full depth (centerbore)
**Side 2**: Bore shallow depth (counterbore pocket)

### Example from o10280.nc:

**Side 1 Operation** (Lines 58-61):
```gcode
T121 (BORE)
G154 P33                 <- Work offset Side 1
X5.228
G01 Z0. F0.009
G01 X4.928 Z-0.15 F0.008 (X IS CB)  <- Chamfer
Z-4.15                               <- FULL DEPTH (through-hole)
```

**Side 2 Operation** (Lines 184-187):
```gcode
T121 (BORE)
G154 P34                 <- Work offset Side 2 (flipped part)
X5.128
G01 Z0. F0.009
G01 X4.928 Z-0.1 F0.008 (X IS CB)   <- SAME diameter, different chamfer
Z-0.75                               <- SHALLOW DEPTH (counterbore pocket)
```

**What's Happening**:
- SAME diameter (4.928") on both sides
- DIFFERENT depths:
  - Side 1: 4.15" deep (through the entire part thickness)
  - Side 2: 0.75" deep (only a shallow pocket)

**Visual Result**:
```
   Side 1              Part              Side 2
   ======================================
   |                                    |
   |  <-- 0.75" deep -->                |
   |  |===============|  <- Counterbore pocket
   |  |               |
   |  |   4.928" dia  |  <- Same diameter
   |  |               |
   |  |               |  <- Centerbore (through-hole)
   |  |               |
   |  |               |
   |  |===============|
   |                                    |
   ======================================
        <--- 4.15" total depth --->
```

**Purpose**: Counterbore creates pocket for hub to press into.

**Parser Issue**:
- Sees this as TWO separate bores
- Doesn't recognize stepped bore relationship
- Doesn't distinguish "counterbore" from "centerbore"

---

## Pattern 5: How Centerbores are Created

### Standard Process (Most Common)

1. **Drill center hole** (T101)
2. **Rough bore to size** (T121, incremental passes)
3. **Finish bore with chamfer** (T121, final pass)

### Example from o75243.nc (Lines 23-36):

```gcode
(Step 1: Drill)
T101 (DRILL)
G01 Z-2.15 F0.008        <- Drill through

(Step 2: Rough bore)
T121 (BORE)
X2.6                     <- Pass 1
G01 Z-2.15 F0.01
X3.2                     <- Pass 2 (+0.6")
G01 Z-2.15
X3.8                     <- Pass 3 (+0.6")
G01 Z-2.15
X4.413                   <- Pass 4 (+0.613", near final)

(Step 3: Finish bore with chamfer)
G01 Z0.
G01 X4.169 Z-0.12 F0.008 (X IS CB)  <- FINAL dimension + chamfer
Z-2.15                               <- Full depth
```

**What's Happening**:
- 4 roughing passes remove most material
- Final pass (X4.169 with chamfer) creates finished surface
- Comment "(X IS CB)" marks this as centerbore diameter

**Dimension to Extract**: X4.169 (NOT X4.413 from roughing)

---

## Pattern 6: Steel Ring Assemblies (Special Case)

### Aluminum Ring + Steel Hub Press-Fit

**Part Title Pattern**:
```gcode
O75243 (7.5 IN DIA 106MM ID 2.00)
(CHECK CB 106 = 4.173)
(106MM CB)
```

**What This Means**:
- 7.5" OD = Aluminum ring outer diameter
- 106MM ID = Steel ring inner diameter (predetermined size)
- 106MM CB = Counterbore to accept steel ring
- 4.173" = 106mm converted to inches (106 / 25.4 = 4.173")

**Material Clarification**:
- The PART is aluminum
- Titled "RING" because a STEEL ring will be pressed into it
- Steel rings come in standard OD/ID sizes (predetermined)
- That's why counterbore dimensions are similar across multiple programs

**Manufacturing Process**:
1. Machine aluminum part with counterbore
2. Press steel ring into counterbore
3. Assembly becomes "steel ring" (even though base part is aluminum)

**Parser Should**:
- Detect "MM ID" or "MM CB" in title
- Extract steel ring dimension (106MM)
- Validate counterbore diameter matches (4.173" ± 0.05")
- Validate counterbore depth (typically 0.30-0.40")

---

## Summary: What Parser Needs to Do Differently

### Current Approach (Wrong)
1. Extract ALL X values
2. Take largest X value as dimension
3. Don't distinguish operation types
4. Don't recognize loop patterns

### Correct Approach (What We Learned)
1. **Detect incremental loops** (X values incrementing 0.2-0.4")
2. **Ignore roughing passes** (all but last X value)
3. **Extract final dimension** from line with chamfer comment "(X IS CB)"
4. **Distinguish feature types**:
   - Centerbore: depth ≥ 50% thickness
   - Counterbore: depth < 50% thickness
   - Hub: stepped turning with "(X IS OB)" comment
5. **Track Side 1 vs Side 2** separately (different work offsets)
6. **Recognize stepped bores** (same diameter, different depths on each side)
7. **Detect steel ring assemblies** from title pattern "MM ID" or "MM CB"

---

## Code Examples for Implementation

### Detect Loop Pattern
```python
def is_incremental_loop(x_values: List[float]) -> bool:
    """Check if X values form incremental roughing pattern"""
    if len(x_values) < 3:
        return False

    increments = [x_values[i+1] - x_values[i] for i in range(len(x_values)-1)]
    avg = sum(increments) / len(increments)

    # Consistent increments of 0.2-0.4" indicate roughing loop
    return 0.15 < avg < 0.5
```

### Extract Final Dimension
```python
def extract_final_dimension(lines: List[str]) -> Optional[float]:
    """Extract dimension from chamfer comment line"""
    for i, line in enumerate(lines):
        # Look for chamfer comment
        if '(X IS CB)' in line.upper() or '(X IS OB)' in line.upper():
            # Extract X value from THIS line (not previous lines)
            match = re.search(r'X\s*(\d+\.?\d*)', line)
            if match:
                return float(match.group(1))

        # Fallback: line with chamfer angle (Z-0.1 to Z-0.15)
        if re.search(r'Z\s*(-0\.1\d*)', line):
            match = re.search(r'X\s*(\d+\.?\d*)', line)
            if match:
                return float(match.group(1))

    return None
```

### Detect Hub Profile
```python
def detect_hub_profile(lines: List[str]) -> Optional[Dict]:
    """Detect stepped turning creating hub"""
    z_depths = []

    for i, line in enumerate(lines):
        # Look for repeated Z-depth pattern
        if 'G01 Z-' in line:
            z_match = re.search(r'Z\s*(-\d+\.?\d*)', line)
            if z_match:
                z_depth = abs(float(z_match.group(1)))

                # Next line should have X value (hub diameter)
                if i+1 < len(lines):
                    next_line = lines[i+1]
                    if 'X' in next_line:
                        z_depths.append(z_depth)

                        # Check for hub diameter marker
                        if '(X IS OB)' in next_line:
                            hub_dia = extract_x_value(next_line)
                            return {
                                'hub_diameter': hub_dia,
                                'hub_height': max(z_depths)
                            }

    return None
```

---

## Testing Files

Validate these patterns against:
- **o13223.nc** - 8-pass incremental roughing loop
- **o57172.nc** - 2-pass minimal roughing
- **o10280.nc** - Stepped turning hub + counterbore/centerbore
- **o75243.nc** - Steel ring assembly pattern
- **o10276.nc** - Hub without counterbore
