# Pre-Import File Scanner - Visual Overview

## What It Looks Like

### Main Window Layout
```
┌────────────────────────────────────────────────────────────────┐
│ G-Code File Scanner - Phase 1 Test               [_][□][X]    │
├────────────────────────────────────────────────────────────────┤
│  Phase 1 Test Environment - Pre-Import File Scanner            │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Select File to Scan ─────────────────────────────────────┐│
│  │ File: [C:\...\repository\o13002.nc          ] [Browse...] ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                 │
│                      [ 🔍 Scan File ]                           │
│                                                                 │
│  ┌─ Results ──────────────────────────────────────────────────┐│
│  │ [Summary] [Issues Details] [Raw Parse Data]                ││
│  │                                                             ││
│  │  ════════════════════════════════════════════════════════  ││
│  │  G-CODE FILE SCAN RESULTS                                  ││
│  │  ════════════════════════════════════════════════════════  ││
│  │                                                             ││
│  │  File: o13002.nc                                           ││
│  │  Path: C:\...\repository\o13002.nc                         ││
│  │                                                             ││
│  │  ✓ File parsed successfully                                ││
│  │                                                             ││
│  │  PROGRAM INFORMATION                                        ││
│  │  ────────────────────────────────────────────────────────  ││
│  │    Program Number:  o13002                                 ││
│  │    Title:           13.0 142/220MM 2.0 HC .5               ││
│  │    Round Size:      13.0"                                  ││
│  │    Spacer Type:     hub_centric                            ││
│  │    Material:        6061-T6                                ││
│  │    Tools Used:      T101, T121, T202                       ││
│  │                                                             ││
│  │  DIMENSIONS                                                 ││
│  │  ────────────────────────────────────────────────────────  ││
│  │    ✓ Outer Diameter (OD)        13.0                       ││
│  │    ✓ Thickness                  2.0                        ││
│  │    ✓ Center Bore (CB)           142                        ││
│  │    ✓ Hub Diameter (OB)          220                        ││
│  │    ✓ Hub Height                 0.5                        ││
│  │                                                             ││
│  │  ISSUES                                                     ││
│  │  ────────────────────────────────────────────────────────  ││
│  │                                                             ││
│  │  ⚠️  WARNINGS (2)                                           ││
│  │                                                             ││
│  │    Tool Home Position:                                     ││
│  │      1. Z-13.0 detected (expected Z-10.0 for 13" OD)       ││
│  │                                                             ││
│  │    Validation:                                             ││
│  │      1. M09 should come before M05                         ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [📄 View File] [💾 Export Report]                    [❌ Close]│
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Scan complete: 2 warning(s), 0 error(s)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tab Views

### Tab 1: Summary
**Purpose**: Quick overview of scan results

**Shows**:
- ✅ File information
- ✅ Program details (number, title, type, material)
- ✅ Dimensions with status (detected ✓ or missing -)
- ✅ Issues grouped by category
- ✅ Color-coded (green=success, orange=warning, red=error, blue=info)

**Best for**: Quick scan to see if file is clean

---

### Tab 2: Issues Details
**Purpose**: Organized view of all issues

```
┌─ Issues Details Tab ─────────────────────────────────────┐
│                                                           │
│  [Tree View with expand/collapse]                        │
│                                                           │
│  ▼ ⚠️  WARNING  |  Warnings  |  2 warning(s)             │
│    ▼ 📁  WARNING  |  Tool Home Position  |  1 warning(s)│
│      •  WARNING  |  Tool Home Position  |  Z-13.0...    │
│    ▼ 📁  WARNING  |  Validation  |  1 warning(s)        │
│      •  WARNING  |  Validation  |  M09 should come...   │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

**Shows**:
- Tree structure of issues
- Grouped by type and category
- Can expand/collapse groups
- Full message text

**Best for**: Understanding specific issues and their categories

---

### Tab 3: Raw Parse Data
**Purpose**: Complete parse result for debugging

**Shows**:
- All fields from GCodeParseResult dataclass
- Lists of detected elements
- Tool sequences
- P-codes found
- All metadata
- Raw values (not formatted)

**Best for**: Debugging parser issues, verifying detection accuracy

---

## Color Coding

### Summary Tab Colors

| Color | Meaning | Examples |
|-------|---------|----------|
| **Green** ✓ | Success/Detected | "✓ Outer Diameter: 13.0" |
| **Orange** ⚠️ | Warning | "⚠️ WARNINGS (2)" |
| **Red** ❌ | Error/Critical | "❌ ERRORS (1)" |
| **Blue** - | Info/Missing | "- Thickness: Not detected" |
| **Bold** | Headers | "PROGRAM INFORMATION" |

---

## Button Functions

### During Scan

| Button | State | Function |
|--------|-------|----------|
| Browse | ✅ Enabled | Opens file browser |
| Scan File | ✅ Enabled | Starts scan |
| View File | ❌ Disabled | (until scan complete) |
| Export Report | ❌ Disabled | (until scan complete) |
| Close | ✅ Enabled | Closes window |

### After Scan

| Button | State | Function |
|--------|-------|----------|
| Browse | ✅ Enabled | Select different file |
| Scan File | ✅ Enabled | Rescan or scan new file |
| View File | ✅ Enabled | Opens file in text editor |
| Export Report | ✅ Enabled | Saves results to .txt |
| Close | ✅ Enabled | Closes window |

---

## Workflow Examples

### Example 1: Clean File (No Issues)
```
1. Browse → Select o10247.nc
2. Scan File
3. Results show:
   ✓ File parsed successfully
   ✓ All dimensions detected (green)
   ✓ No issues found
4. Status: "Scan complete: 0 warning(s), 0 error(s)"
```

### Example 2: File with Warnings
```
1. Browse → Select o13002.nc
2. Scan File
3. Results show:
   ✓ File parsed successfully
   ✓ Most dimensions detected
   ⚠️ WARNINGS (2)
     - Tool home Z-13.0 (should be Z-10.0)
     - M09 should come before M05
4. Status: "Scan complete: 2 warning(s), 0 error(s)"
5. Review warnings in Issues Details tab
6. View File to check specific lines
```

### Example 3: File with Missing Data
```
1. Browse → Select file_no_dimensions.nc
2. Scan File
3. Results show:
   ✓ File parsed successfully
   ✓ Program number detected
   - Outer Diameter: Not detected (blue)
   - Thickness: Not detected (blue)
   - Center Bore: Not detected (blue)
4. Status: "Scan complete: 3 warning(s), 0 error(s)"
   (Missing data counts as warnings)
```

### Example 4: Invalid File
```
1. Browse → Select corrupted.nc
2. Scan File
3. Results show:
   ❌ Failed to parse file
   ❌ ERRORS (1)
     - Parse error: [specific error message]
4. Status: "Scan failed - see errors"
5. File cannot be imported until fixed
```

---

## Status Bar Messages

| Message | Meaning |
|---------|---------|
| "Ready to scan" | Initial state, no file scanned yet |
| "Scanning o13002.nc..." | Scan in progress |
| "Scan complete: 2 warning(s), 0 error(s)" | Scan finished successfully |
| "Scan complete: 0 warning(s), 0 error(s)" | Clean file, no issues |
| "Scan failed - see errors" | Parse error or critical failure |

---

## Export Report Format

When you click "💾 Export Report", you get a text file:

```
================================================================================
G-CODE FILE SCAN RESULTS
================================================================================

File: o13002.nc
Path: C:\Users\...\repository\o13002.nc

✓ File parsed successfully

PROGRAM INFORMATION
--------------------------------------------------------------------------------
  Program Number:  o13002
  Title:           13.0 142/220MM 2.0 HC .5
  Round Size:      13.0"
  Spacer Type:     hub_centric
  Material:        6061-T6
  Tools Used:      T101, T121, T202

DIMENSIONS
--------------------------------------------------------------------------------
  ✓ Outer Diameter (OD)        13.0
  ✓ Thickness                  2.0
  ✓ Center Bore (CB)           142
  ✓ Hub Diameter (OB)          220
  ✓ Hub Height                 0.5

ISSUES
--------------------------------------------------------------------------------

⚠️  WARNINGS (2)

  Tool Home Position:
    1. Z-13.0 detected (expected Z-10.0 for 13" OD)

  Validation:
    1. M09 should come before M05


================================================================================
RAW PARSE DATA
================================================================================

[Complete parse result with all fields]
...
```

---

## Quick Reference Card

### Keyboard Shortcuts (Future)
Currently no keyboard shortcuts in test environment.
Will be added during main app integration:
- `Ctrl+O` - Browse for file
- `Ctrl+R` - Scan/Rescan file
- `Ctrl+S` - Export report
- `Ctrl+W` - Close window

### File Types Supported
- `.nc` files (G-code)
- `.txt` files (if they contain G-code)
- Any text file with G-code content

### Scan Speed
- Small files (< 100 lines): < 1 second
- Medium files (100-500 lines): 1-3 seconds
- Large files (500-2000 lines): 3-10 seconds
- Very large files (2000+ lines): 10-30 seconds

---

## Tips for Testing

### What to Test
1. ✅ **Various file types**: Standard, Hub-Centric, STEP, 2PC
2. ✅ **Different sizes**: Small, medium, large files
3. ✅ **Clean files**: Should show no warnings
4. ✅ **Problem files**: Should detect known issues
5. ✅ **Edge cases**: Empty, corrupted, missing data

### How to Verify Accuracy
1. Pick a file you know well
2. Check what issues you know it has
3. Scan with the scanner
4. Verify it detects the known issues
5. Check for false positives (issues that aren't real)

### What to Report
- ✅ Issues detected correctly
- ❌ Issues missed (false negatives)
- ⚠️ Incorrect warnings (false positives)
- 💡 Suggestions for improvements
- 🐛 Bugs or crashes

---

## Integration Preview

When this feature is integrated into the main application:

### New Menu Item
```
File
  ├─ Import Single File...
  ├─ Import Multiple Files...
  ├─ Batch Import from Folder...
  ├─────────────────────────────
  ├─ 🔍 Scan G-Code File...        ← NEW!
  ├─────────────────────────────
  ├─ Export...
  └─ Exit
```

### Keyboard Shortcut
`Ctrl+Shift+S` - Scan G-Code File

### Integration Points
1. **Before import**: Optional scan before adding to database
2. **On duplicate**: Automatic scan when duplicating program
3. **Maintenance**: Scan existing files to check for issues
4. **Troubleshooting**: Scan files when debugging problems

---

## Comparison: Test vs. Integrated Version

| Feature | Test Version | Integrated Version |
|---------|--------------|-------------------|
| Window | Standalone | Part of main app |
| Database | Not accessed | Can import after scan |
| Import | Not available | "Import Anyway" button |
| Auto-fix | Not available | Will be available |
| Shortcuts | None | Ctrl+Shift+S |
| Menu access | Run separately | File menu |
| Context menu | No | Right-click file |

---

**Ready to try it? Run `run_test.bat` and start scanning!**

See [QUICK_START.md](QUICK_START.md) for a 5-minute quick start guide.
