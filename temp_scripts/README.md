# Temporary Scripts Folder

This folder contains testing, debugging, and one-time fix scripts used during development.

## Categories

### Analysis Scripts (analyze_*.py)
Scripts that analyze data patterns, errors, or specific issues in the database or G-code files.

### Check Scripts (check_*.py)
Scripts that verify specific conditions, database states, or validate fixes.

### Debug Scripts (debug_*.py)
Debugging tools for investigating specific parsing or validation issues.

### Find Scripts (find_*.py)
Scripts that search for specific patterns, errors, or edge cases in the codebase.

### Fix Scripts (fix_*.py)
One-time scripts that apply specific fixes to data or code. Most have been run once and are kept for reference.

### Test Scripts (test_*.py)
Unit tests and integration tests for parser features and validation logic.

### Rescan Scripts (rescan_*.py)
Scripts that trigger database rescans with specific fixes or validation updates.

### Verify Scripts (verify_*.py)
Scripts that verify fixes were applied correctly or validate data integrity.

### Other Utilities
- populate_registry.py - Registry population tool
- refresh_filename_validations.py - Filename validation refresh
- remove_tool_safety_validation.py - Removed tool safety checks
- reset_registry_cleanup.py - Registry cleanup utility
- run_batch_detection.py - Batch detection runner
- cleanup_missing_files.py - One-time cleanup for missing files
- cleanup_stale_entries.py - One-time cleanup for stale database entries

## Usage

These scripts are NOT part of the main application. They are development tools and should not be run unless you understand their purpose.

Most fix/rescan scripts have already been run and their changes are incorporated into the main parser and database.
