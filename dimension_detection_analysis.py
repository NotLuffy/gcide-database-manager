"""
Dimension Detection Analysis - ML-Based Pattern Discovery

This analyzes how well current dimension detection works and suggests improvements
using machine learning to discover patterns in titles and G-code.

Usage:
    python dimension_detection_analysis.py
"""

import sqlite3
import re
from collections import defaultdict, Counter

try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("WARNING: ML libraries not installed. Install with:")
    print("  pip install pandas scikit-learn numpy")
    print("\nRunning limited analysis without ML...")


class DimensionDetectionAnalyzer:
    """Analyzes dimension detection patterns to improve parsing"""

    def __init__(self, db_path='gcode_database.db'):
        self.db_path = db_path
        self.df = None

    def load_data(self):
        """Load programs with dimension data"""
        conn = sqlite3.connect(self.db_path)

        self.df = pd.read_sql_query("""
            SELECT
                program_number, title, spacer_type,
                outer_diameter, thickness, center_bore,
                hub_diameter, hub_height,
                counter_bore_diameter, counter_bore_depth,
                cb_from_gcode, ob_from_gcode,
                validation_status, detection_confidence
            FROM programs
        """, conn)

        conn.close()
        print(f"Loaded {len(self.df)} programs")

    def analyze_title_patterns(self):
        """Analyze what patterns exist in titles for dimension extraction"""
        print("\n" + "="*80)
        print("TITLE PATTERN ANALYSIS")
        print("="*80)

        if self.df is None:
            self.load_data()

        # Common title formats
        title_patterns = defaultdict(list)

        for idx, row in self.df.iterrows():
            title = str(row['title'])

            # Categorize by pattern
            if 'IN DIA' in title or 'IN$ DIA' in title:
                title_patterns['IN_DIA_format'].append(title)
            elif re.search(r'\d+\.?\d*IN', title):
                title_patterns['IN_format'].append(title)
            elif 'MM' in title and '/' in title:
                title_patterns['MM_slash_format'].append(title)
            elif 'HC' in title:
                title_patterns['HC_format'].append(title)
            elif '2PC' in title:
                title_patterns['2PC_format'].append(title)
            else:
                title_patterns['other'].append(title)

        print("\nTitle Format Distribution:")
        for pattern, titles in sorted(title_patterns.items(), key=lambda x: -len(x[1])):
            print(f"  {pattern:20s}: {len(titles):4d} programs")
            if titles:
                print(f"    Example: {titles[0][:70]}")

        # Analyze successful dimension extraction
        print("\n" + "-"*80)
        print("DIMENSION EXTRACTION SUCCESS RATE")
        print("-"*80)

        total = len(self.df)
        print(f"\nTotal programs: {total}")
        print(f"  OD extracted:         {self.df['outer_diameter'].notna().sum():5d} ({self.df['outer_diameter'].notna().sum()/total*100:.1f}%)")
        print(f"  Thickness extracted:  {self.df['thickness'].notna().sum():5d} ({self.df['thickness'].notna().sum()/total*100:.1f}%)")
        print(f"  CB extracted:         {self.df['center_bore'].notna().sum():5d} ({self.df['center_bore'].notna().sum()/total*100:.1f}%)")
        print(f"  Hub D extracted:      {self.df['hub_diameter'].notna().sum():5d} ({self.df['hub_diameter'].notna().sum()/total*100:.1f}%)")
        print(f"  Hub H extracted:      {self.df['hub_height'].notna().sum():5d} ({self.df['hub_height'].notna().sum()/total*100:.1f}%)")

        # Programs with missing dimensions
        missing_od = self.df[self.df['outer_diameter'].isna()]
        missing_thickness = self.df[self.df['thickness'].isna()]
        missing_cb = self.df[self.df['center_bore'].isna()]

        print(f"\n  Missing OD:           {len(missing_od):5d}")
        print(f"  Missing Thickness:    {len(missing_thickness):5d}")
        print(f"  Missing CB:           {len(missing_cb):5d}")

        if len(missing_od) > 0:
            print(f"\nExamples of titles missing OD:")
            for title in missing_od['title'].head(5):
                print(f"  - {title}")

        if len(missing_thickness) > 0:
            print(f"\nExamples of titles missing Thickness:")
            for title in missing_thickness['title'].head(5):
                print(f"  - {title}")

    def analyze_gcode_vs_title(self):
        """Compare G-code extracted dimensions vs title dimensions"""
        print("\n" + "="*80)
        print("G-CODE vs TITLE DIMENSION COMPARISON")
        print("="*80)

        if self.df is None:
            self.load_data()

        # CB comparison
        cb_both = self.df[(self.df['center_bore'].notna()) & (self.df['cb_from_gcode'].notna())].copy()
        if len(cb_both) > 0:
            cb_both['cb_diff'] = cb_both['cb_from_gcode'] - cb_both['center_bore']

            print(f"\nCenter Bore (CB) - Title vs G-code:")
            print(f"  Programs with both: {len(cb_both)}")
            print(f"  Mean difference: {cb_both['cb_diff'].mean():.2f}mm")
            print(f"  Std deviation:   {cb_both['cb_diff'].std():.2f}mm")
            print(f"  Max difference:  {cb_both['cb_diff'].abs().max():.2f}mm")

            # How accurate is title extraction?
            accurate = (cb_both['cb_diff'].abs() < 0.5).sum()
            print(f"  Within 0.5mm:    {accurate}/{len(cb_both)} ({accurate/len(cb_both)*100:.1f}%)")

            # Show cases where they differ significantly
            big_diff = cb_both[cb_both['cb_diff'].abs() > 1.0]
            if len(big_diff) > 0:
                print(f"\n  {len(big_diff)} programs with >1mm difference:")
                for idx, row in big_diff.head(5).iterrows():
                    print(f"    {row['program_number']}: Title={row['center_bore']:.1f}mm, G-code={row['cb_from_gcode']:.1f}mm, Diff={row['cb_diff']:.2f}mm")
                    print(f"      {row['title']}")

        # OB comparison
        ob_both = self.df[(self.df['hub_diameter'].notna()) & (self.df['ob_from_gcode'].notna())].copy()
        if len(ob_both) > 0:
            ob_both['ob_diff'] = ob_both['ob_from_gcode'] - ob_both['hub_diameter']

            print(f"\nOuter Bore (OB/Hub D) - Title vs G-code:")
            print(f"  Programs with both: {len(ob_both)}")
            print(f"  Mean difference: {ob_both['ob_diff'].mean():.2f}mm")
            print(f"  Std deviation:   {ob_both['ob_diff'].std():.2f}mm")
            print(f"  Max difference:  {ob_both['ob_diff'].abs().max():.2f}mm")

    def find_extraction_patterns(self):
        """Use ML to find patterns in successful extractions"""
        print("\n" + "="*80)
        print("ML PATTERN DISCOVERY - What makes extraction successful?")
        print("="*80)

        if not ML_AVAILABLE:
            print("Skipping - ML libraries not installed")
            return

        if self.df is None:
            self.load_data()

        # Extract features from titles
        self.df['title_length'] = self.df['title'].astype(str).str.len()
        self.df['has_IN'] = self.df['title'].astype(str).str.contains('IN', na=False).astype(int)
        self.df['has_MM'] = self.df['title'].astype(str).str.contains('MM', na=False).astype(int)
        self.df['has_HC'] = self.df['title'].astype(str).str.contains('HC', na=False).astype(int)
        self.df['has_slash'] = self.df['title'].astype(str).str.contains('/', na=False).astype(int)
        self.df['has_2PC'] = self.df['title'].astype(str).str.contains('2PC', na=False).astype(int)
        self.df['num_numbers'] = self.df['title'].astype(str).apply(lambda x: len(re.findall(r'\d+\.?\d*', x)))

        # Predict success of dimension extraction
        features = ['title_length', 'has_IN', 'has_MM', 'has_HC', 'has_slash', 'has_2PC', 'num_numbers']

        # Predict if CB will be extracted
        self.df['cb_extracted'] = self.df['center_bore'].notna().astype(int)
        X = self.df[features]
        y = self.df['cb_extracted']

        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X, y)

        print("\nFeature importance for CB extraction success:")
        feature_importance = pd.DataFrame({
            'feature': features,
            'importance': clf.feature_importances_
        }).sort_values('importance', ascending=False)
        print(feature_importance)

        # What title patterns predict successful extraction?
        print("\nTitle characteristics for successful CB extraction:")
        success = self.df[self.df['cb_extracted'] == 1]
        fail = self.df[self.df['cb_extracted'] == 0]

        print(f"  Success has 'MM': {success['has_MM'].mean()*100:.1f}%  vs  Fail: {fail['has_MM'].mean()*100:.1f}%")
        print(f"  Success has '/':  {success['has_slash'].mean()*100:.1f}%  vs  Fail: {fail['has_slash'].mean()*100:.1f}%")
        print(f"  Success has 'HC': {success['has_HC'].mean()*100:.1f}%  vs  Fail: {fail['has_HC'].mean()*100:.1f}%")

    def suggest_improvements(self):
        """Suggest specific improvements to dimension extraction"""
        print("\n" + "="*80)
        print("RECOMMENDED IMPROVEMENTS")
        print("="*80)

        if self.df is None:
            self.load_data()

        # Analyze failed extractions
        missing_cb = self.df[self.df['center_bore'].isna()]
        missing_thickness = self.df[self.df['thickness'].isna()]

        print("\n1. THICKNESS EXTRACTION IMPROVEMENTS:")
        print(f"   Currently missing: {len(missing_thickness)} programs")

        # Find common patterns in titles with missing thickness
        if len(missing_thickness) > 0:
            # Check for "TH" abbreviation
            has_th = missing_thickness['title'].astype(str).str.contains(r'\.\d+\s*TH', na=False, regex=True).sum()
            if has_th > 0:
                print(f"   - {has_th} titles have '.XX TH' pattern (not parsed)")
                print(f"     Example: {missing_thickness[missing_thickness['title'].str.contains(r'\.\d+\s*TH', na=False, regex=True)]['title'].iloc[0]}")

            # Check for thickness after 2PC
            has_2pc_num = missing_thickness['title'].astype(str).str.contains(r'2PC\s+\d+\.?\d*', na=False, regex=True).sum()
            if has_2pc_num > 0:
                print(f"   - {has_2pc_num} titles have number after '2PC' (might be thickness)")

        print("\n2. CENTER BORE EXTRACTION IMPROVEMENTS:")
        print(f"   Currently missing: {len(missing_cb)} programs")

        if len(missing_cb) > 0:
            # Programs that should have CB
            hc_missing_cb = missing_cb[missing_cb['spacer_type'] == 'hub_centric']
            print(f"   - {len(hc_missing_cb)} hub_centric programs missing CB (should have it!)")
            if len(hc_missing_cb) > 0:
                print(f"     Examples:")
                for title in hc_missing_cb['title'].head(3):
                    print(f"       {title}")

        print("\n3. G-CODE EXTRACTION ACCURACY:")
        # Check validation status of programs
        critical = self.df[self.df['validation_status'] == 'CRITICAL']
        print(f"   {len(critical)} programs marked CRITICAL")
        print(f"   Most common issues:")

        # Would need validation_issues column to analyze

        print("\n4. SUGGESTED NEW PATTERNS:")
        print("   Based on analysis, add these patterns:")
        print("   - Thickness: r'\\.(\d+)\\s+TH' for '.75 TH' format")
        print("   - CB: Improve slash pattern for 'XX.X/YY.Y' format")
        print("   - Hub height: Better detection from 'HC X.XX' patterns")
        print("   - Use G-code as validation/correction for title extraction")

    def run_all_analyses(self):
        """Run complete analysis suite"""
        self.analyze_title_patterns()
        self.analyze_gcode_vs_title()
        if ML_AVAILABLE:
            self.find_extraction_patterns()
        self.suggest_improvements()


def main():
    """Main entry point"""
    if not ML_AVAILABLE:
        import sys
        print("\nML libraries not installed. Some features will be limited.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Install with: pip install pandas scikit-learn numpy")
            sys.exit(1)

    analyzer = DimensionDetectionAnalyzer()
    analyzer.run_all_analyses()

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review suggested improvements above")
    print("2. Test new regex patterns on sample programs")
    print("3. Update improved_gcode_parser.py with new patterns")
    print("4. Rescan database to apply improvements")
    print("5. Re-run this analysis to measure improvement")


if __name__ == '__main__':
    main()
