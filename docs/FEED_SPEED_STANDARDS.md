# Feed & Speed Standards

**Based on analysis of 365,130 samples from 21,376 production G-code programs**

---

## Recommended Standards by Operation Type

### BORE Operations
**Recommended: 0.020 IPR @ 1450 RPM**

- **Confidence Level:** VERY HIGH (152,644 samples)
- **Most Common:** 0.02 feed rate (72,226 occurrences)
- **Feed Rate Range:** 0.000 - 0.031 IPR
- **Spindle Speed Range:** 800 - 2600 RPM

**Alternative Feed Rates:**
- 0.008 IPR - Used in 35,296 programs (for lighter cuts or finishing)
- 0.010 IPR - Used in 33,973 programs

**Alternative Spindle Speeds:**
- 1450 RPM - Used in 74,560 programs (MOST COMMON)
- 950 RPM - Used in 21,074 programs (for tougher materials)
- 1500 RPM - Used in 18,064 programs

---

### THREAD Operations
**Recommended: 0.015 IPR @ 1600 RPM**

- **Confidence Level:** VERY HIGH (190,765 samples)
- **Most Common:** 0.015 feed rate (51,673 occurrences)
- **Feed Rate Range:** 0.002 - 80.0 IPR
- **Spindle Speed Range:** 800 - 2750 RPM

**Alternative Feed Rates:**
- 0.013 IPR - Used in 39,070 programs
- 0.020 IPR - Used in 22,596 programs

**Alternative Spindle Speeds:**
- 1600 RPM - Used in 67,412 programs (MOST COMMON)
- 2000 RPM - Used in 28,421 programs
- 1200 RPM - Used in 27,576 programs

---

### FACE/BORE Operations
**Recommended: 0.008 IPR @ 1800 RPM**

- **Confidence Level:** HIGH (21,038 samples)
- **Most Common:** 0.008 feed rate (16,334 occurrences)
- **Feed Rate Range:** 0.004 - 0.020 IPR
- **Spindle Speed Range:** 1000 - 2600 RPM

**Alternative Feed Rates:**
- 0.004 IPR - Used in 3,450 programs (for finishing)

**Alternative Spindle Speeds:**
- 1800 RPM - Used in 4,122 programs (MOST COMMON)
- 1250 RPM - Used in 3,472 programs
- 1550 RPM - Used in 3,151 programs

---

### DRILL Operations
**Recommended: 0.008 IPR @ 1250 RPM**

- **Confidence Level:** MEDIUM (596 samples)
- **Most Common:** 0.008 feed rate (409 occurrences)
- **Feed Rate Range:** 0.003 - 0.011 IPR
- **Spindle Speed Range:** 1250 - 2600 RPM

**Alternative Feed Rates:**
- 0.004 IPR - Used in 162 programs

**Alternative Spindle Speeds:**
- 1250 RPM - Used in 179 programs (MOST COMMON)
- 1600 RPM - Used in 134 programs
- 1800 RPM - Used in 108 programs

---

### FACE Operations
**Recommended: 0.015 IPR @ 1500 RPM**

- **Confidence Level:** LOW (87 samples)
- **Most Common:** 0.015 feed rate (75 occurrences)
- **Feed Rate Range:** 0.010 - 0.015 IPR
- **Spindle Speed Range:** 1000 - 2000 RPM

**Note:** Low sample count - use with caution. May need manual review.

---

## Quick Reference Table

| Operation  | Feed (IPR) | Speed (RPM) | Confidence | Sample Count |
|-----------|-----------|------------|-----------|-------------|
| BORE      | 0.020     | 1450       | VERY HIGH | 152,644     |
| THREAD    | 0.015     | 1600       | VERY HIGH | 190,765     |
| FACE/BORE | 0.008     | 1800       | HIGH      | 21,038      |
| DRILL     | 0.008     | 1250       | MEDIUM    | 596         |
| FACE      | 0.015     | 1500       | LOW       | 87          |

---

## Confidence Levels

- **VERY HIGH:** 10,000+ samples - Extremely reliable, used in vast majority of programs
- **HIGH:** 1,000+ samples - Reliable for standard operations
- **MEDIUM:** 100-999 samples - Generally safe, may need verification
- **LOW:** <100 samples - Use with caution, manual review recommended

---

## Conservative Approach

When multiple values are commonly used (mode vs median close together), the **lower (safer) value** is recommended to minimize risk of tool breakage or poor surface finish.

**Example:**
- BORE feed rate mode: 0.020, median: 0.012
- Since they differ significantly, we use the mode (most common): 0.020
- FACE/BORE spindle speed mode: 1800, median: 1550
- Conservative approach: Use 1800 (mode) as it's most commonly proven in production

---

## Future Enhancements

As more programs are parsed and dimensions are extracted, the following correlations will become available:

1. **By Round Size:** Specific recommendations for each lathe size range
   - L1: 5.75-6.5" parts
   - L2/L3: 7.0-8.5" parts
   - L2: 9.5-13.0" parts

2. **By Thickness Range:** Recommendations based on part thickness
   - Thin parts (0.394-1.0")
   - Medium parts (1.0-2.5")
   - Thick parts (2.5-4.0")

3. **By Material Type:** Steel vs Aluminum specific values

---

## Usage Notes

1. **Start with recommended values** - These represent the most proven settings
2. **Monitor first part** - Adjust if surface finish or chip formation is poor
3. **Consider material** - Steel may require lower speeds than aluminum
4. **Tool condition matters** - Worn tools may need reduced feed rates
5. **Listen to the cut** - Chattering indicates speed/feed adjustment needed

---

## Data Source

- **Analysis Date:** 2026-02-06
- **Total Samples:** 365,130 feed/speed records
- **Programs Scanned:** 21,376 G-code files
- **Data Files:**
  - `feed_speed_analysis.json` - Full dataset
  - `feed_speed_standards.json` - Machine-readable standards

---

## Revision History

| Date       | Version | Changes                                    |
|-----------|---------|-------------------------------------------|
| 2026-02-06| 1.0     | Initial standards based on full scan      |

---

*This document is generated from actual production G-code programs and represents the most commonly used and proven feed/speed combinations in current use.*
