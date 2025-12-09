# ML Fallback Toggle - Usage Guide

## Overview
The ML fallback feature is now fully integrated into the main database GUI with optional toggle control. You can choose whether to use ML predictions during each rescan operation.

## How to Use

### Step 1: Start the Database Manager
```bash
python gcode_database_manager.py
```

### Step 2: Click "Rescan Database"
Navigate to: **Database Management → Rescan Database**

### Step 3: Choose ML Fallback Option
A custom dialog will appear with:
- Information about what the rescan does
- **Checkbox: "Use ML Fallback for missing dimensions"**
- Note: "(Slower but fills all missing dimensions automatically)"
- Proceed and Cancel buttons

### Step 4: Make Your Choice

**Option A: Fast Rescan (Default)**
- Leave checkbox UNCHECKED
- Click "Proceed"
- Result: Quick rescan without ML predictions

**Option B: ML-Enhanced Rescan**
- CHECK the checkbox
- Click "Proceed"
- Result: Slower rescan with ML predictions for missing dimensions

## When to Use ML Fallback

### Use ML (Check the box) when:
- You have many files with missing dimensions
- You want the most complete data possible
- Time is not a critical factor
- You're doing a comprehensive database refresh

### Don't Use ML (Leave unchecked) when:
- You just want to refresh parser improvements
- You need a quick rescan
- Most files already have dimensions
- You're testing parser changes

## Performance Comparison

| Mode | Speed | Coverage | Resource Usage |
|------|-------|----------|----------------|
| Without ML | Fast | Parser-detected only | Low |
| With ML | Slower | Parser + ML predictions | High |

## What ML Fallback Does

When enabled, the ML system:
1. Loads pre-trained Random Forest models
2. For each file with missing dimensions:
   - Analyzes the title text
   - Uses G-code features (CB, OB)
   - Predicts missing OD, thickness, or center bore
3. Marks predictions with 'ML_FALLBACK' confidence
4. Adds notes showing which dimensions were ML-predicted

## Technical Details

- **Default State**: Checkbox is UNCHECKED (OFF)
- **ML Initialization**: Only happens when checkbox is checked
- **Models Used**: Random Forest regressors for OD, thickness, CB
- **Feature Sources**: Title text, G-code measurements, known dimensions
- **Confidence Marking**: All ML predictions marked as 'ML_FALLBACK'

## Example Output

### Without ML:
```
ML Fallback disabled (for faster scanning)

Rescanning... 871/871 files
Updated: 871
Skipped: 0
Errors: 0
```

### With ML:
```
[ML Fallback] Loaded ML models for missing dimensions

Rescanning... 871/871 files
Updated: 871
Skipped: 0
Errors: 0
ML Predictions: 247
```

## Status

✅ **Implementation Complete**
- Custom dialog with checkbox: ✅
- Conditional ML initialization: ✅
- Default to OFF for speed: ✅
- Clear user messaging: ✅
- Integrated into GUI: ✅

## Files Modified

- `gcode_database_manager.py` (lines 1660-1817)
  - Custom rescan dialog with ML checkbox
  - Conditional ML initialization
  - ML prediction helper method

## Notes

- The checkbox defaults to OFF because ML scanning is resource-intensive
- You have full control over when ML runs
- No need to run separate scripts anymore
- All ML predictions are saved directly to the database
- You can toggle between fast and comprehensive rescans as needed
