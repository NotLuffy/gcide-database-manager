# Quick Start Guide - Phase 1 Test Environment

## 🚀 Launch the Test Application

### Windows (Easiest)
Double-click: `run_test.bat`

### Command Line
```bash
cd "l:\My Drive\Home\File organizer\test_phase1"
python file_scanner_test.py
```

---

## ✅ Quick Test (5 Minutes)

### Step 1: Launch
Run the test application using one of the methods above.

### Step 2: Select a File
1. Click **"Browse..."**
2. Navigate to `l:\My Drive\Home\File organizer\repository\`
3. Select any `.nc` file (try `o13002.nc` or similar)

### Step 3: Scan
Click **"🔍 Scan File"** button

### Step 4: Review Results
Look at all three tabs:
- **Summary**: Overview with color-coded issues
- **Issues Details**: Tree view of problems
- **Raw Parse Data**: All extracted data

### Step 5: Test Actions
- Click **"📄 View File"** to open file in editor
- Click **"💾 Export Report"** to save results

---

## 📋 What to Look For

### ✅ Good Signs
- Scan completes in 1-5 seconds
- Program number detected correctly
- Dimensions show in green
- Warnings (if any) are clear and actionable

### ⚠️ Issues to Report
- Application crashes
- Scan takes > 10 seconds
- Wrong data detected
- Confusing error messages
- UI elements not visible

---

## 🎯 Test These Files

### Clean File Test
**File**: `o13002.nc` (or any standard spacer)
**Expected**: Few or no warnings

### Warning Test
**File**: Any file with known issues
**Expected**: Warnings display in orange

### Missing Data Test
**File**: File without dimensions in title
**Expected**: Blue "Not detected" messages

---

## 📝 Give Feedback

As you test, note:
1. What's confusing?
2. What's helpful?
3. What's missing?
4. Any bugs?

Use `TEST_CHECKLIST.md` for detailed testing, or just note quick observations.

---

## 🔧 Troubleshooting

### "Import Error: improved_gcode_parser"
**Fix**: Make sure you're in the test_phase1 directory when running

### "File not found"
**Fix**: Browse to the repository folder and select a valid .nc file

### Application doesn't open
**Fix**:
1. Check Python is installed: `python --version`
2. Try running from command line to see errors
3. Verify improved_gcode_parser.py exists in parent directory

---

## ⏭️ Next Steps

After testing this scanner:
1. Report any issues found
2. Suggest improvements
3. Move to Phase 1.2 (Database File Monitor)
4. Eventually integrate into main application

---

## 🛡️ Safety Note

This is a **TEST ENVIRONMENT** - it does NOT:
- ❌ Modify your database
- ❌ Import files
- ❌ Change any repository files
- ❌ Affect the main application

**Safe to test with any files!**

---

## Quick Reference

| Action | What It Does |
|--------|--------------|
| Browse | Select G-code file to scan |
| Scan File | Analyze file for issues |
| View File | Open in text editor |
| Export Report | Save results to .txt file |
| Summary Tab | Overview of results |
| Issues Tab | Detailed issue list |
| Raw Data Tab | Complete parse data |

---

**Ready to test? Run `run_test.bat` and start scanning!**
