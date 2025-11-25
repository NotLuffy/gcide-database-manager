# Documentation

This folder contains all project documentation organized by category.

## User Documentation

- [QUICK_START.md](QUICK_START.md) - Quick start guide for using the G-Code Database Manager
- [FUTURE_FEATURES.md](FUTURE_FEATURES.md) - Planned features and roadmap
- [TODO_LIST.md](TODO_LIST.md) - Current project tasks and priorities

## Architecture Documentation ([architecture/](architecture/))

Technical documentation about system design and architecture:

- **GCODE_DATABASE_ARCHITECTURE.md** - Overall database schema and design
- **GUI_INTEGRATION_COMPLETE.md** - GUI architecture and integration
- **PATTERN_RECOGNITION_GUIDE.md** - How pattern recognition works
- **MULTI_METHOD_EXTRACTION.md** - Multi-method dimension extraction strategy
- **MULTI_SELECT_FILTERS.md** - Multi-select filter implementation
- **COLOR_CODED_VALIDATION_SYSTEM.md** - Validation status color coding system
- **COLUMN_MAPPING_VERIFIED.md** - Database column mapping verification

## Improvements Documentation ([improvements/](improvements/))

Documentation of features added and problems solved:

### 2PC Detection Improvements
- **2PC_DETECTION_IMPROVEMENTS.md** - Initial 2PC detection improvements
- **2PC_IMPROVEMENTS_IMPLEMENTED.md** - Phase 2 advanced 2PC detection
- **2PC_LUG_VS_STUD_PATTERNS.md** - Patterns for distinguishing LUG vs STUD

### Hub Detection Improvements
- **HUB_DETECTION_STATISTICS_IMPROVEMENT.md** - Hub detection accuracy improvements
- **HUB_HEIGHT_AND_NA_FIXES.md** - Hub height calculation fixes
- **HUB_HEIGHT_FIX_IMPACT.md** - Impact analysis of hub height fixes

### Validation Improvements
- **ADDITIONAL_VALIDATIONS_AND_UPDATE_PROCESS.md** - Additional validation checks
- **PHASE_1_VALIDATIONS_COMPLETE.md** - Phase 1 validation implementation
- **CB_TOO_LARGE_FIXES.md** - Center bore validation fixes
- **FLIP_PART_OP2_FIX.md** - OP2 flip part detection
- **SCAN_FIXES.md** - Various scan and parsing fixes

## Investigation Reports ([investigations/](investigations/))

Deep-dive analyses of specific issues and their resolutions:

- **CRITICAL_ERROR_INVESTIGATION_SUMMARY.md** - Analysis of critical validation errors
- **FALSE_POSITIVE_ANALYSIS.md** - Analysis of false positive detections
- **THICKNESS_ERROR_DEEP_DIVE.md** - Deep analysis of thickness parsing errors
- **THICKNESS_ERROR_FIX_SUMMARY.md** - Summary of thickness error fixes
- **TWO_OP_TOLERANCE_ANALYSIS.md** - Two-operation tolerance issue analysis

## Document Categories

### By Purpose:
- **User Guides**: QUICK_START.md
- **Architecture**: 7 documents covering system design
- **Feature Improvements**: 11 documents tracking enhancements
- **Problem Analysis**: 5 investigation reports

### By Status:
- **Active**: QUICK_START.md, TODO_LIST.md, FUTURE_FEATURES.md
- **Reference**: Architecture and improvements documents
- **Historical**: Investigation reports (problems solved)

## Contributing

When adding new documentation:
- Place user-facing docs in `docs/` root
- Place technical architecture docs in `docs/architecture/`
- Place feature/fix documentation in `docs/improvements/`
- Place problem investigation reports in `docs/investigations/`
