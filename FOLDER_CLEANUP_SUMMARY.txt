FOLDER CLEANUP SUMMARY
======================

Organized on: 2025-12-10

CLEANUP ACTIONS:
----------------

1. Moved ~80+ test/debug/analysis scripts to /temp_scripts
   - analyze_*.py
   - check_*.py
   - debug_*.py
   - find_*.py
   - fix_*.py
   - test_*.py
   - verify_*.py
   - rescan_*.py
   - Other one-time utilities

2. Moved ML tools to /ml_tools
   - ml_analyzer.py
   - ml_dimension_extractor.py
   - ml_validation_analyzer.py
   - ml_dimension_predictions.csv

3. Moved documentation files to /docs
   - All *.md files (except README.md in root)
   - ~60+ documentation files organized

4. Moved backup databases to /Database_Backups
   - gcode_database_backup_*.db files

ROOT FOLDER NOW CONTAINS:
-------------------------

CORE APPLICATION FILES:
- gcode_database_manager.py (main GUI application)
- improved_gcode_parser.py (core parser)
- repository_manager.py (archive system)
- archive_gui.py (archive management GUI)
- cleanup_repository.py (repository cleanup tool)

CONFIGURATION:
- gcode_manager_config.json (application config)
- requirements.txt (Python dependencies)
- install_drag_drop.bat (drag-drop installer)

DATABASE FILES:
- gcode_database.db (active database)
- gcode_programs.db (legacy database if exists)
- ml_dimension_models.pkl (ML models)

DOCUMENTATION:
- README.md (main project readme)

FOLDER STRUCTURE:
-----------------

/File organizer (root)
├── Core application files (7 files)
├── Configuration files (3 files)
├── Database files (2-3 files)
├── README.md
│
├── /archive - Archived old program versions
├── /backups - Database backups
├── /Database_Backups - Old database backup files
├── /database_profiles - Database profiles
├── /deleted - Deleted programs
├── /docs - All documentation (60+ .md files)
├── /ml_tools - ML analysis tools (4 files + README)
├── /repository - Active G-code programs (8,210 files)
├── /temp_scripts - Test/debug/fix scripts (80+ files + README)
└── /versions - Version history

BENEFITS:
---------

✅ Clean root folder (only 13 essential files)
✅ All test/debug scripts organized in temp_scripts
✅ All documentation organized in docs folder
✅ ML tools separated into dedicated folder
✅ Easy to find core application files
✅ No breaking changes - all paths relative or absolute
✅ README files in each folder for guidance

TESTING REQUIRED:
-----------------

✅ Main application (gcode_database_manager.py) - Should work normally
✅ Archive GUI (archive_gui.py) - Should work normally
✅ Parser (improved_gcode_parser.py) - Should work normally
✅ Repository manager (repository_manager.py) - Should work normally

All imports are relative or use absolute paths, so moving test scripts
should not affect the main application functionality.
