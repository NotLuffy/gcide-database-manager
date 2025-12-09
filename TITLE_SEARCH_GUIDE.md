# Multi-Term Title Search - User Guide

## Overview
The title search bar now supports powerful multi-term searching using the `+` operator. This allows you to find programs that match **ALL** of your search terms, regardless of order.

## Location
The search bar is located at the **very top** of the filter section in the database manager.

## How to Use

### Single Term Search
Just type one keyword:
- `FORD` → Finds all programs with "FORD" in the title
- `5.75` → Finds all programs with "5.75" in the title
- `ALUMINUM` → Finds all programs with "ALUMINUM" in the title

### Multi-Term Search (AND Logic)
Use `+` to search for multiple terms that must ALL be present:

```
lug + 1.25 + 74
```

This finds programs where the title contains:
- "lug" **AND**
- "1.25" **AND**
- "74"

### Real Examples from Your Database

**Search:** `lug + 1.25 + 74`

**Results Found (5 programs):**
- o58635: 5.75IN  74MM LUG 1.25--2PC
- o62317: 6.25IN  74.4 MM  LUG 1.25 2PC
- o62382: 6.25IN  74 MM  LUG 1.25 2PC
- o62829: 6.25IN$ 74 MM  LUG 1.25 2PC
- o75647: 7.5IN DIA 74.4MM ID 1.25 2PC LUG

**Search:** `6.0 + 70`

**Results Found (10 programs):**
- o60333: 6.00IN 70.6MM/70.3MM 3/8 HC
- o60365: 6.00 IN DIA 70.3MM ID 1.00
- o60427: 6.00 IN 70.3MM ID 1.25
- And 7 more...

## Key Features

### 1. Order Doesn't Matter
These searches are identical:
- `lug + 1.25 + 74`
- `74 + lug + 1.25`
- `1.25 + 74 + lug`

All will find the same programs.

### 2. Case Insensitive
- `FORD` = `ford` = `Ford`
- `LUG` = `lug` = `Lug`

### 3. Partial Matches
- `6.0` matches "6.00", "6.0", and "6.000"
- `74` matches "74", "74.4", "74MM", "740", etc.

### 4. Whitespace Flexible
These are the same:
- `lug + 1.25 + 74`
- `lug+1.25+74`
- `lug  +  1.25  +  74`

### 5. Combines with All Other Filters
You can use multi-term search AND dimensional filters at the same time:

**Example:**
- Title Search: `lug + 1.25`
- OD Range: 5.75 to 6.5
- Material: ALUMINUM

This finds all aluminum lug spacers with 1.25" thickness and OD between 5.75-6.5 inches.

## Practical Use Cases

### Find Specific Vehicle Parts
```
FORD + F150 + 5.75
```
Finds Ford F150 parts with 5.75" dimension

### Find by Dimensions
```
6.0 + 70 + 1.25
```
Finds 6.0" OD, 70mm CB, 1.25" thick spacers

### Find Lug-Centric Wheels
```
lug + 74
```
Finds all lug-centric spacers with 74mm bore

### Find Hub-Centric Parts
```
hub + centric + 66
```
Finds hub-centric parts with 66mm hub diameter

### Find Two-Piece Sets
```
2PC + 6.25
```
Finds two-piece spacers with 6.25" dimension

### Find by Material & Type
```
ALUMINUM + STEP
```
Finds aluminum step-type spacers

## Quick Reference

| Search Pattern | What It Finds |
|---------------|---------------|
| `FORD` | Single term: Contains "FORD" |
| `lug + 74` | Two terms: Contains both "lug" AND "74" |
| `6.0 + 70 + 1.25` | Three terms: Contains all three |
| `hub + centric + 66 + 1.0` | Four terms: Contains all four |

## Tips

1. **Start broad, then narrow:**
   - First: `FORD`
   - Then: `FORD + 5.75`
   - Finally: `FORD + 5.75 + 1.25`

2. **Use dimensions you know:**
   - If you know OD and CB: `6.25 + 74`
   - If you know thickness: `+ 1.25`

3. **Combine with filters:**
   - Multi-term search for text patterns
   - Dimensional filters for exact ranges
   - Material/Type filters for categorization

4. **Press Enter to search:**
   - No need to click the Search button
   - Just type and press Enter

5. **Quick clear:**
   - Click the `✕` button to clear just the search
   - Or "Clear Filters" to reset everything

## Implementation Details

**File:** [gcode_database_manager.py](gcode_database_manager.py)

**Search Logic (lines 2938-2954):**
- Detects `+` in search string
- Splits into individual terms
- Creates AND query for each term
- Case-insensitive LIKE matching

**UI (lines 602-622):**
- Prominent search bar at top
- Enter key binding for quick search
- Clear button for easy reset
- Helpful hint text with examples

## Testing

Run the test script to see it in action:
```bash
python test_title_search.py
```

This will demonstrate:
- Multi-term search examples
- Search result counts
- Sample matching programs
- How the + operator works
