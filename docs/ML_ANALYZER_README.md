# ML Analyzer - Experimental Machine Learning Analysis

## Overview

`ml_analyzer.py` is a **separate, experimental** tool that uses machine learning to analyze G-code programs. It runs alongside the main parser **without modifying your database** - it only reads and analyzes.

## Purpose

- Test ML-based approaches before integrating them
- Discover patterns automatically
- Validate current rule-based logic
- Identify potential improvements

## Installation

### 1. Install ML Libraries (Optional)

The main program works without these. Only install if you want to try ML analysis:

```bash
pip install pandas scikit-learn numpy scipy
```

### 2. Verify Installation

```bash
python ml_analyzer.py --help
```

If libraries are missing, you'll get a helpful error message with install instructions.

## Usage

### Analyze Patterns in Your Data

```bash
python ml_analyzer.py --analyze
```

Shows:
- Spacer type distribution
- Validation status breakdown
- Dimension statistics by type
- Correlations between dimensions
- 2PC program analysis

### Detect Anomalies

```bash
python ml_analyzer.py --detect-anomalies
```

Uses **Isolation Forest** to find unusual programs:
- Trains on all your data
- Identifies outliers (default: 5% flagged)
- Compares to current validation status
- Shows top anomalies for review

### Predict 2PC Classification

```bash
python ml_analyzer.py --predict-2pc
```

Trains **Random Forest classifier** on labeled 2PC programs:
- Learns patterns from LUG/STUD examples
- Tests accuracy on held-out data
- Shows which features matter most (thickness, hub height, etc.)
- Predicts classification for "2PC UNSURE" programs

### Run Everything

```bash
python ml_analyzer.py --all
```

Or just:
```bash
python ml_analyzer.py
```

## What It Does

### 1. Pattern Analysis
- Loads all 6,200+ programs into pandas DataFrame
- Calculates statistics and correlations
- Groups by spacer type, validation status, etc.
- Helps you understand your data

### 2. Anomaly Detection
- Trains Isolation Forest on your programs
- Finds unusual dimension combinations
- Compares ML anomalies vs current validation
- **Read-only** - doesn't change database

### 3. 2PC Classification
- Trains on existing LUG/STUD labels
- Learns distinguishing features
- Provides accuracy metrics
- Tests on UNSURE programs
- Shows confidence scores

## Example Output

```
Loading data from database...
Loaded 6213 programs

================================================================================
DATA ANALYSIS - PATTERN DISCOVERY
================================================================================

1. SPACER TYPE DISTRIBUTION:
standard           3245
hub_centric        1823
2PC LUG             492
2PC STUD            311
step                285
...

2PC Thickness patterns:
              count   mean    std    min   25%   50%   75%    max
2PC LUG       492    1.45   0.65   0.75  1.00  1.25  1.75   3.25
2PC STUD      311    0.75   0.02   0.70  0.75  0.75  0.75   0.80

================================================================================
ANOMALY DETECTION - Isolation Forest
================================================================================

Found 311 anomalies (5.0%)

Top 10 anomalies:
  program_number                   title  outer_diameter  thickness  center_bore
  o13025         13.0 220MM 0.75 HC       13.0           0.75       220.0
  o58516         5.75IN 40MM STEP         5.75           2.50       40.0
  ...

================================================================================
2PC LUG/STUD CLASSIFICATION - Random Forest
================================================================================

Training data: 803 labeled 2PC programs
  LUG: 492
  STUD: 311

Training Random Forest classifier...

Test Accuracy: 94.6%

Feature Importance:
           feature  importance
    0   thickness      0.523
    1  hub_height      0.248
    2  drill_depth     0.142
    ...

Testing on 7 '2PC UNSURE' programs:
  program_number  ml_prediction  ml_confidence
  o62260         2PC STUD        0.89
  o62265         2PC LUG         0.76
  ...
```

## Safety Features

1. **Read-Only**: Never writes to database
2. **Separate**: Doesn't affect main program
3. **Optional**: Works without ML libraries installed
4. **Experimental**: Clearly labeled as testing

## Integration Path

If ML proves valuable:
1. Test predictions vs current system
2. Identify where ML performs better
3. Gradually integrate successful approaches
4. Keep rule-based logic for clear cases
5. Use ML for ambiguous cases

## Performance

- Loading 6,200 programs: ~1-2 seconds
- Pattern analysis: ~5 seconds
- Anomaly detection: ~10 seconds
- 2PC classification: ~15 seconds
- **Total runtime**: ~30-40 seconds

## Limitations

- Requires labeled training data (for classification)
- Black-box predictions (less interpretable than rules)
- Needs periodic retraining as data changes
- Larger memory footprint than rule-based

## Future Enhancements

- Deep learning for G-code sequence analysis
- Automatic tolerance threshold learning
- Confidence scores for all predictions
- Active learning (learn from corrections)
- Export predictions for review

## Comparison with Current System

| Feature | Rule-Based (Current) | ML-Based (Experimental) |
|---------|---------------------|------------------------|
| Speed | Fast (instant) | Slower (seconds) |
| Interpretability | High (clear rules) | Low (black box) |
| Adaptability | Manual updates | Learns automatically |
| Edge cases | Requires new rules | Handles naturally |
| Confidence | Binary (yes/no) | Probabilistic scores |
| Maintenance | Rule updates | Retraining |

## When to Use

**Use Rule-Based (current):**
- Clear-cut cases (STEP, standard, etc.)
- Production parsing
- When you need explainability
- Fast execution required

**Use ML (experimental):**
- Finding patterns you haven't discovered
- Handling ambiguous cases (2PC UNSURE)
- Validating current logic
- Research and analysis

## Questions?

This is an experimental tool for exploration. Your current parser still works perfectly without it!
