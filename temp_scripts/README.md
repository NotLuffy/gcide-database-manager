# Temporary Scripts and Test Files

This folder contains temporary analysis, debugging, and test scripts used during development and troubleshooting of the G-Code Database Manager.

## Categories

### Analysis Scripts
- `analyze_13_round_thickness_errors.py` - Analyzed thickness parsing errors in 13" round programs
- `analyze_2pc_gcode.py` - Analyzed G-code patterns for 2PC LUG vs STUD detection
- `analyze_facing_pattern.py` - Analyzed facing operations for hub detection
- `analyze_two_op_tolerance.py` - Analyzed two-operation tolerance issues

### Check/Verification Scripts
- `check_2pc_unsure.py` - Checked 2PC UNSURE programs
- `check_o57604.py` - Specific program debugging
- `check_remaining_errors.py` - Checked remaining validation errors
- `check_rescan_stats.py` - Verified database statistics after rescan
- `check_types_sample.py` - Sampled spacer type classifications

### Debug Scripts
- `debug_o10076.py` - Debugged specific program issues
- `debug_o10076_drill.py` - Debugged drill depth detection
- `debug_o13025.py` - Debugged hub-centric detection
- `debug_o13045.py` - Debugged parsing issues
- `debug_o58516.py` - Debugged specific program

### Fix/Migration Scripts
- `add_title_column.py` - Added title column to database schema
- `fix_database_schema.py` - Fixed database schema issues
- `fix_details_indices.py` - Fixed detail window column indices
- `fix_details_window.py` - Fixed detail window display
- `fix_duplicates_columns.py` - Fixed duplicate detection columns
- `fix_hc_priority.py` - Fixed hub-centric priority detection
- `fix_thin_hub_cb.py` - Fixed thin hub counterbore issues

### Reparse Scripts
- `reparse_o10040.py` - Reparsed specific program
- `reparse_o10076.py` - Reparsed specific program
- `reparse_o13045.py` - Reparsed specific program

### Rescan Scripts
- `rescan_13_round.py` - Rescanned 13" round programs
- `rescan_13_round_updated.py` - Updated rescan for 13" programs

### Scan Scripts
- `scan_false_positive_patterns.py` - Scanned for false positive patterns
- `scan_hub_detection.py` - Scanned hub detection accuracy

### Test Scripts
- `test_2pc_classification.py` - Tested 2PC classification logic
- `test_2pc_logic_improvements.py` - Tested improved 2PC detection
- `test_all_warning_types.py` - Tested warning display logic
- `test_copy_issue.py` - Tested copy functionality
- `test_details_display.py` - Tested details window display
- `test_excel_export.py` - Tested Excel export functionality
- `test_export_alignment.py` - Tested export column alignment
- `test_fraction_parsing.py` - Tested fraction thickness parsing
- `test_gui_display.py` - Tested GUI display
- `test_hc_pattern.py` - Tested hub-centric pattern detection
- `test_leading_decimal.py` - Tested decimal parsing (.75 format)
- `test_performance.py` - Performance testing
- `test_status_breakdown.py` - Tested status classification

### List/Report Scripts
- `list_thickness_errors.py` - Listed all thickness parsing errors

## Usage

These scripts are development/debugging tools and are not part of the main application. They can be:
- Referenced for understanding past issues and solutions
- Re-run if similar issues occur
- Modified for new debugging scenarios
- Deleted if no longer needed

## Note

Most of these scripts were created during specific troubleshooting sessions and may reference specific program numbers or database states. They may not work correctly on different database states without modification.
