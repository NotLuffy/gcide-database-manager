# Phase 1.4 - Duplicate with Automatic Scan

## Overview

**Duplicate with Automatic Scan** improves the program duplication workflow by:
- Scanning the source file before duplication
- Showing warnings to help you decide
- Auto-fixing common issues in the new file
- Opening the new file in an editor

---

## Quick Start

```bash
cd "l:\My Drive\Home\File organizer\test_phase1"
python duplicate_with_scan_test.py
# or double-click: run_duplicate_test.bat
```

---

## Features

### 1. Automatic Source Scan
- Scans source file when selected
- Shows all warnings and errors
- Helps you know if starting from a clean base

### 2. Auto-Fix Warnings
- Checkbox to enable auto-fix
- Fixes common issues automatically:
  - Tool home Z position
  - M09/M05 sequence
- New file gets the fixes applied

### 3. Editor Integration
- Checkbox to open in editor after creation
- Opens file in your default text editor
- Start editing immediately

### 4. Safety Checks
- Warns if warnings detected in source
- Confirms before overwriting existing files
- Shows which fixes were applied

---

## How to Use

### Step-by-Step

1. **Select Source File**
   - Click "Browse..."
   - Navigate to repository folder
   - Select a .nc file

2. **Scan Source**
   - Click "🔍 Scan Source File"
   - Review the scan results
   - See any warnings or errors

3. **Configure Options**
   - New file name is auto-generated (_copy suffix)
   - Check "Auto-fix warnings" if you want fixes applied
   - Check "Open in editor" if you want to edit after

4. **Create Duplicate**
   - Click "📄 Create Duplicate"
   - Confirm if warnings exist
   - Done! New file is created

---

## Auto-Fix Capabilities

### What Gets Fixed

**Tool Home Z Position**
- Detects: Z-13.0 when should be Z-10.0
- Fixes: Updates to correct Z value
- Example: `G43 H01 Z-13.0` → `G43 H01 Z-10.0`

**M09/M05 Sequence**
- Detects: M05 before M09
- Fixes: Inserts M09 before M05
- Example: `M05` → `M09\nM05`

### What Doesn't Get Fixed
- Missing dimensions (requires manual input)
- Invalid G-code syntax (needs review)
- Complex logic errors (requires expertise)

---

## Testing Scenarios

### Test 1: Clean File (2 minutes)
1. Select a clean file (no warnings)
2. Scan source
3. Should show "No issues found"
4. Create duplicate
5. New file should be identical

### Test 2: File with Warnings (3 minutes)
1. Select a file with tool home warning
2. Scan source
3. Should show warning
4. Enable "Auto-fix warnings"
5. Create duplicate
6. Check that new file has fix applied

### Test 3: Open in Editor (2 minutes)
1. Select any file
2. Enable "Open in editor after creation"
3. Create duplicate
4. File should open in default text editor

### Test 4: Overwrite Protection (1 minute)
1. Create a duplicate
2. Try to create another with same name
3. Should warn before overwriting
4. Can cancel or proceed

---

## Integration into Main App

When integrated into the main application:

### Right-Click Menu
```
Right-click on program in database →
  ├─ View File
  ├─ Edit Program
  ├─ Duplicate...                    ← Shows scan dialog
  ├─ Delete
  └─ ...
```

### Duplicate Dialog
```
┌────────────────────────────────────────────────────────┐
│ Duplicate Program o13002                               │
├────────────────────────────────────────────────────────┤
│ Source: o13002.nc                                       │
│ New program number: [o13003___________]                │
│                                                         │
│ ⚠️ Source file has warnings (2):                        │
│   • Tool home Z-13.0 (should be Z-10.0)                │
│   • M09 should come before M05                         │
│                                                         │
│ [✓] Auto-fix warnings in new file                      │
│ [ ] Open in editor after creation                      │
│                                                         │
│ [Create Duplicate] [Scan Source] [Cancel]              │
└────────────────────────────────────────────────────────┘
```

---

## Status

- ✅ **Implementation**: COMPLETE
- ⏳ **Testing**: READY
- 📋 **Integration**: PENDING

**Dependencies**: FileScanner from Phase 1.1 ✅

**Test Command**: `python duplicate_with_scan_test.py`

---

## Benefits

### Before (Without Scanning)
1. Duplicate program
2. Discover issues later
3. Have to fix manually
4. Risk propagating errors

### After (With Scanning)
1. Scan shows issues immediately
2. Auto-fix applies corrections
3. Start with clean file
4. Reduce error propagation

---

## Quick Reference

| Action | What It Does |
|--------|--------------|
| Browse | Select source G-code file |
| Scan Source | Analyze file for issues |
| Auto-fix | Automatically fix warnings in new file |
| Open in editor | Launch editor after creation |
| Create Duplicate | Generate new file |

---

**Phase 1.4 Complete!** 🎉

This completes all 4 features of Phase 1!
