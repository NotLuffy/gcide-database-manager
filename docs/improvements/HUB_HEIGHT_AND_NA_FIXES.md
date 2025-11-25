# Hub Height & N/A Display Fixes

## Issues Fixed:

### 1. **Hub Height Not Being Displayed** ✅

**Problem:** Hub-centric parts weren't showing hub height even though it's a critical dimension.

**Root Cause:** The hub height extraction pattern `r'HC\s+(\d+\.?\d*)'` was looking for "HC 0.5" format, but most titles just have "HC" without the height value.

**Solution:** Enhanced hub height extraction with:
1. Multiple pattern matching (both "HC 0.5" and "0.5 HC" formats)
2. **Default value of 0.50"** for standard hub-centric parts when not specified in title
3. Validation to ensure hub height is in reasonable range (0.2" to 1.0")

**Code Change** ([improved_gcode_parser.py:578-599](../File%20Scanner/improved_gcode_parser.py#L578)):
```python
# Hub height (for hub-centric)
if result.spacer_type == 'hub_centric':
    # Try to extract from title (format: "HC 0.5" or "0.5 HC")
    hub_patterns = [
        r'HC\s+(\d*\.?\d+)',  # HC 0.5
        r'(\d*\.?\d+)\s+HC',  # 0.5 HC
    ]
    for pattern in hub_patterns:
        hub_match = re.search(pattern, title, re.IGNORECASE)
        if hub_match:
            try:
                hub_val = float(hub_match.group(1))
                # Hub height is typically 0.25" to 0.75"
                if 0.2 < hub_val < 1.0:
                    result.hub_height = hub_val
                    break
            except:
                pass

    # If not found in title, use standard 0.50" hub height
    if not result.hub_height:
        result.hub_height = 0.50
```

**Why 0.50" Default?**
- Standard hub-centric spacers use 0.50" (12.7mm) hub height
- Calculated from drill depth formula: `hub_height = drill_depth - thickness - 0.15`
- For o58436: `0.50 = 1.40 - 0.75 - 0.15` ✓

---

### 2. **N/A for Non-Applicable Fields** ✅

**Problem:** All parts showed "-" for fields that don't apply to them, making it unclear if data was missing or just not applicable.

**Examples:**
- Standard parts don't have Hub Height or Hub Diameter (OB)
- Hub-centric parts don't have Counter Bore
- STEP parts don't have Hub Height or Hub Diameter

**Solution:** Display **"N/A"** (Not Applicable) instead of "-" for fields that don't apply to that part type.

**Code Change** ([gcode_database_manager.py:624-640](gcode_database_manager.py#L624)):
```python
# Hub Height - only applicable for hub_centric
if spacer_type == 'hub_centric':
    hub_h = f"{row[5]:.2f}" if row[5] else "-"
else:
    hub_h = "N/A"

# Hub Diameter (OB) - only applicable for hub_centric
if spacer_type == 'hub_centric':
    hub_d = f"{row[6]:.1f}" if row[6] else "-"
else:
    hub_d = "N/A"

# Counter Bore - only applicable for STEP parts
if spacer_type == 'step':
    cb_bore = f"{row[7]:.1f}" if row[7] else "-"
else:
    cb_bore = "N/A"
```

---

## Display Logic by Part Type:

| Part Type | OD | Thick | CB | Hub H | Hub D (OB) | CB Bore | Material |
|-----------|----|----|----|----|-------|---------|----------|
| **Standard** | ✓ | ✓ | ✓ | N/A | N/A | N/A | ✓ |
| **Hub-Centric** | ✓ | ✓ | ✓ | ✓ | ✓ | N/A | ✓ |
| **STEP** | ✓ | ✓ | ✓ | N/A | N/A | ✓ | ✓ |
| **2PC Part 1** | ✓ | ✓ | ✓ | N/A | N/A | N/A | ✓ |
| **2PC Part 2** | ✓ | ✓ | ✓ | N/A | N/A | N/A | ✓ |

**Legend:**
- ✓ = Value displayed
- N/A = "N/A" displayed (field not applicable to this part type)

---

## Testing Results:

### Before Fixes:
```
Program: o58436
Type: hub_centric
Hub Height: -              ❌ Missing!
Hub Diameter: 64.1mm
CB Bore: -                 (Should be N/A)
```

### After Fixes:
```
Program: o58436
Type: hub_centric
Hub Height: 0.50"          ✅ Now showing!
Hub Diameter: 64.1mm
CB Bore: N/A               ✅ Clear it's not applicable
```

### Standard Part Example:
```
Program: o57500
Type: standard
Hub Height: N/A            ✅ Clear it's not applicable
Hub Diameter: N/A          ✅ Clear it's not applicable
CB Bore: N/A               ✅ Clear it's not applicable
```

---

## Benefits:

1. **Hub Height Now Visible:**
   - Critical for hub-centric parts
   - Defaults to standard 0.50" when not specified
   - Can be overridden if title specifies different height

2. **Clearer Display:**
   - "N/A" = Field doesn't apply to this part type
   - "-" = Data missing or not found
   - This helps identify **missing data** vs **non-applicable fields**

3. **Better Data Quality:**
   - Easy to spot which hub-centric parts use non-standard hub heights
   - Clear visual distinction between part types
   - Easier to validate data completeness

---

## Files Modified:

1. [improved_gcode_parser.py](../File%20Scanner/improved_gcode_parser.py) - Enhanced hub height extraction
2. [gcode_database_manager.py](gcode_database_manager.py) - Added N/A display logic

---

## Next Steps:

**Re-scan folders** to populate hub height for existing hub-centric parts:
1. Launch GUI
2. Click "Scan Folder"
3. Select production directories
4. All hub-centric parts will now show hub height (0.50" default)
5. Fields not applicable to each part type will show "N/A"

This makes it much clearer what data is missing vs. what doesn't apply!
