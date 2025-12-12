"""
ML-based validation analyzer to identify false positives/negatives in our detection logic.

This will:
1. Analyze patterns in PASS vs CRITICAL/WARNING files
2. Identify potential false negatives (PASS but should be error)
3. Identify potential false positives (CRITICAL/WARNING but should be PASS)
4. Suggest improved detection thresholds
"""

import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import json

db_path = 'gcode_database.db'

print("Loading data from database...")
print("=" * 100)

conn = sqlite3.connect(db_path)

# Get all programs with dimensional data
query = """
    SELECT
        program_number,
        spacer_type,
        outer_diameter,
        thickness,
        center_bore,
        hub_diameter,
        cb_from_gcode,
        ob_from_gcode,
        validation_status,
        validation_issues,
        validation_warnings,
        bore_warnings,
        dimensional_issues,
        file_path
    FROM programs
    WHERE file_path IS NOT NULL
    AND outer_diameter IS NOT NULL
    AND thickness IS NOT NULL
    AND center_bore IS NOT NULL
    AND cb_from_gcode IS NOT NULL
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f"Loaded {len(df)} programs with complete data")
print(f"\nValidation Status Distribution:")
print(df['validation_status'].value_counts())

# Calculate error metrics
df['cb_error_mm'] = abs(df['cb_from_gcode'] - df['center_bore'])
df['cb_error_pct'] = (df['cb_error_mm'] / df['center_bore']) * 100

# For programs with OB
df['ob_error_mm'] = abs(df['ob_from_gcode'] - df['hub_diameter']).fillna(0)
df['ob_error_pct'] = ((df['ob_error_mm'] / df['hub_diameter']) * 100).fillna(0)

# Categorize validation status for ML
df['has_error'] = df['validation_status'].isin(['CRITICAL', 'BORE_WARNING']).astype(int)
df['has_warning'] = df['validation_status'].isin(['WARNING', 'DIMENSIONAL']).astype(int)

print("\n" + "=" * 100)
print("ERROR STATISTICS BY STATUS")
print("=" * 100)

for status in ['PASS', 'WARNING', 'DIMENSIONAL', 'BORE_WARNING', 'CRITICAL']:
    subset = df[df['validation_status'] == status]
    if len(subset) > 0:
        print(f"\n{status} ({len(subset)} programs):")
        print(f"  CB Error: mean={subset['cb_error_mm'].mean():.2f}mm, median={subset['cb_error_mm'].median():.2f}mm, max={subset['cb_error_mm'].max():.2f}mm")
        if subset['ob_error_mm'].sum() > 0:
            ob_subset = subset[subset['hub_diameter'].notna()]
            if len(ob_subset) > 0:
                print(f"  OB Error: mean={ob_subset['ob_error_mm'].mean():.2f}mm, median={ob_subset['ob_error_mm'].median():.2f}mm, max={ob_subset['ob_error_mm'].max():.2f}mm")

# Find potential false negatives - PASS but large errors
print("\n" + "=" * 100)
print("POTENTIAL FALSE NEGATIVES (PASS but high error)")
print("=" * 100)

false_neg_threshold = 2.0  # 2mm error while marked as PASS
potential_false_neg = df[(df['validation_status'] == 'PASS') & (df['cb_error_mm'] > false_neg_threshold)]

print(f"\nFound {len(potential_false_neg)} PASS programs with CB error > {false_neg_threshold}mm:")
for idx, row in potential_false_neg.head(20).iterrows():
    print(f"  {row['program_number']}: CB error={row['cb_error_mm']:.2f}mm (spec={row['center_bore']:.1f}mm, extracted={row['cb_from_gcode']:.1f}mm)")

# Find potential false positives - CRITICAL but small errors
print("\n" + "=" * 100)
print("POTENTIAL FALSE POSITIVES (CRITICAL but low error)")
print("=" * 100)

false_pos_threshold = 1.0  # Less than 1mm error but marked CRITICAL
potential_false_pos = df[(df['validation_status'] == 'CRITICAL') & (df['cb_error_mm'] < false_pos_threshold)]

print(f"\nFound {len(potential_false_pos)} CRITICAL programs with CB error < {false_pos_threshold}mm:")
for idx, row in potential_false_pos.head(20).iterrows():
    issues = row['validation_issues'] if pd.notna(row['validation_issues']) else 'None'
    print(f"  {row['program_number']}: CB error={row['cb_error_mm']:.2f}mm - Issues: {issues[:80]}")

# Prepare features for ML
print("\n" + "=" * 100)
print("TRAINING ML MODEL TO PREDICT ACTUAL ERRORS")
print("=" * 100)

# Create feature matrix
features = df[['outer_diameter', 'thickness', 'center_bore']].copy()
features['spacer_type_hc'] = (df['spacer_type'] == 'hub_centric').astype(int)
features['spacer_type_step'] = (df['spacer_type'] == 'step').astype(int)
features['spacer_type_2pc'] = df['spacer_type'].str.contains('2PC', na=False).astype(int)
features['has_ob'] = df['hub_diameter'].notna().astype(int)
features['cb_extracted'] = df['cb_from_gcode']
features['ob_extracted'] = df['ob_from_gcode'].fillna(0)

# Target: Is there actually a significant error? (CB > 1mm OR OB > 2mm)
actual_error = ((df['cb_error_mm'] > 1.0) | (df['ob_error_mm'] > 2.0)).astype(int)

# Split data
X_train, X_test, y_train, y_test = train_test_split(features, actual_error, test_size=0.3, random_state=42)

# Train model
clf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
clf.fit(X_train, y_train)

# Predict
y_pred = clf.predict(X_test)

print("\nML Model Performance:")
print("=" * 100)
print(classification_report(y_test, y_pred, target_names=['No Significant Error', 'Significant Error']))

print("\nConfusion Matrix:")
print("=" * 100)
cm = confusion_matrix(y_test, y_pred)
print(f"{'':20} {'Predicted PASS':20} {'Predicted ERROR':20}")
print(f"{'Actual PASS':20} {cm[0][0]:20} {cm[0][1]:20} (False Positives)")
print(f"{'Actual ERROR':20} {cm[1][0]:20} {cm[1][1]:20} (False Negatives)")

# Feature importance
print("\nFeature Importance:")
print("=" * 100)
feature_names = features.columns
importances = clf.feature_importances_
indices = np.argsort(importances)[::-1]

for i in range(len(feature_names)):
    print(f"{i+1}. {feature_names[indices[i]]}: {importances[indices[i]]:.4f}")

# Identify misclassifications
print("\n" + "=" * 100)
print("MISCLASSIFICATIONS - Programs ML thinks are wrong")
print("=" * 100)

# Get predictions for all data
all_predictions = clf.predict(features)
df['ml_predicted_error'] = all_predictions

# False Positives: ML says ERROR but validation says PASS
ml_false_pos = df[(df['ml_predicted_error'] == 1) & (df['validation_status'] == 'PASS')]
print(f"\nML predicts ERROR but marked PASS ({len(ml_false_pos)} programs):")
print("These might be false negatives in our validation logic!")
for idx, row in ml_false_pos.head(10).iterrows():
    print(f"  {row['program_number']}: CB error={row['cb_error_mm']:.2f}mm, OB error={row['ob_error_mm']:.2f}mm")
    print(f"    Spec: CB={row['center_bore']:.1f}mm, OB={row['hub_diameter']:.1f}mm" if pd.notna(row['hub_diameter']) else f"    Spec: CB={row['center_bore']:.1f}mm")
    print(f"    Extracted: CB={row['cb_from_gcode']:.1f}mm, OB={row['ob_from_gcode']:.1f}mm" if pd.notna(row['ob_from_gcode']) else f"    Extracted: CB={row['cb_from_gcode']:.1f}mm")

# False Negatives: ML says PASS but validation says CRITICAL
ml_false_neg = df[(df['ml_predicted_error'] == 0) & (df['validation_status'] == 'CRITICAL')]
print(f"\nML predicts PASS but marked CRITICAL ({len(ml_false_neg)} programs):")
print("These might be false positives in our validation logic!")
for idx, row in ml_false_neg.head(10).iterrows():
    issues = row['validation_issues'] if pd.notna(row['validation_issues']) else 'None'
    print(f"  {row['program_number']}: CB error={row['cb_error_mm']:.2f}mm, OB error={row['ob_error_mm']:.2f}mm")
    print(f"    Issues: {issues[:100]}")

print("\n" + "=" * 100)
print("RECOMMENDATIONS FOR IMPROVED THRESHOLDS")
print("=" * 100)

# Analyze current thresholds
pass_errors = df[df['validation_status'] == 'PASS']['cb_error_mm']
critical_errors = df[df['validation_status'] == 'CRITICAL']['cb_error_mm']

if len(pass_errors) > 0 and len(critical_errors) > 0:
    print(f"\nCurrent CB tolerance appears to be:")
    print(f"  PASS max error: {pass_errors.max():.2f}mm")
    print(f"  CRITICAL min error: {critical_errors.min():.2f}mm")

    # Suggest optimal threshold (minimize misclassifications)
    percentile_95 = pass_errors.quantile(0.95)
    percentile_99 = pass_errors.quantile(0.99)

    print(f"\nSuggested CB thresholds:")
    print(f"  Conservative (99% of PASS): {percentile_99:.2f}mm")
    print(f"  Balanced (95% of PASS): {percentile_95:.2f}mm")
    print(f"  Current threshold: ~0.4mm (based on code)")

print("\nDone!")
