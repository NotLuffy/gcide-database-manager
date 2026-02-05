# Phase 1 Test Checklist - Pre-Import File Scanner

## Purpose
Use this checklist to systematically test the file scanner feature before integration into the main application.

---

## Pre-Testing Setup

- [ ] Verified `improved_gcode_parser.py` exists in parent directory
- [ ] Python 3.7+ is installed
- [ ] Test environment directory structure is correct
- [ ] Read the README.md

---

## Test Session Information

**Date**: _______________
**Tester**: _______________
**Python Version**: _______________
**OS**: _______________

---

## Functional Tests

### 1. Application Launch
- [ ] Application launches without errors
- [ ] Window opens with correct title
- [ ] All UI elements visible
- [ ] No console errors

**Notes**: _______________________________________________

---

### 2. File Selection

#### 2.1 Browse Button
- [ ] Browse button opens file dialog
- [ ] Can navigate to repository folder
- [ ] Can select .nc file
- [ ] Selected file path shows in entry field

#### 2.2 Manual Entry
- [ ] Can type/paste file path directly
- [ ] Path is accepted

**Notes**: _______________________________________________

---

### 3. File Scanning

#### 3.1 Valid File Scan
- [ ] Scan button activates
- [ ] Status bar shows "Scanning..." message
- [ ] Scan completes in reasonable time (< 5 seconds)
- [ ] "Scan complete" message shows in status bar
- [ ] Warning/error counts displayed

**Test file used**: _______________
**Scan time**: _______ seconds

#### 3.2 Summary Tab
- [ ] Summary tab shows results
- [ ] File name displayed
- [ ] Program information section present
- [ ] Dimensions section present
- [ ] Issues section present
- [ ] Color coding works (green/orange/red)
- [ ] Text is readable and formatted

**Screenshot/Notes**: _______________________________________________

#### 3.3 Issues Details Tab
- [ ] Issues tree view displays
- [ ] Issues grouped by category
- [ ] Can expand/collapse groups
- [ ] Error count correct
- [ ] Warning count correct
- [ ] Categories make sense

**Screenshot/Notes**: _______________________________________________

#### 3.4 Raw Parse Data Tab
- [ ] Raw data displays
- [ ] All parse result fields shown
- [ ] Data is readable
- [ ] Lists formatted correctly

**Screenshot/Notes**: _______________________________________________

---

### 4. Edge Cases

#### 4.1 Non-Existent File
- [ ] Error message displays
- [ ] Application doesn't crash
- [ ] Can continue to scan other files

**Expected behavior**: Error message "File not found"
**Actual behavior**: _______________________________________________

#### 4.2 Empty File Path
- [ ] Error message displays
- [ ] Prompts to select a file

**Expected behavior**: Error message "Please select a file"
**Actual behavior**: _______________________________________________

#### 4.3 Invalid G-Code File
- [ ] Parse errors shown
- [ ] Application doesn't crash
- [ ] Error messages are helpful

**Test file used**: _______________
**Notes**: _______________________________________________

#### 4.4 File Without Dimensions
- [ ] Scan completes
- [ ] Shows "Not detected" for missing dimensions
- [ ] Info messages for missing data
- [ ] No crash or error

**Test file used**: _______________
**Notes**: _______________________________________________

---

### 5. Action Buttons

#### 5.1 View File Button
- [ ] Button is disabled before scan
- [ ] Button enabled after successful scan
- [ ] Clicking opens file in default editor
- [ ] File opens correctly

**Notes**: _______________________________________________

#### 5.2 Export Report Button
- [ ] Button disabled before scan
- [ ] Button enabled after successful scan
- [ ] Save dialog opens
- [ ] Default filename is appropriate
- [ ] Report file is created
- [ ] Report file contains all scan results
- [ ] Report file is readable

**Test file**: _______________
**Report location**: _______________
**Notes**: _______________________________________________

#### 5.3 Close Button
- [ ] Close button works
- [ ] Application closes cleanly
- [ ] No errors on close

---

### 6. Issue Detection Tests

Test with various files to verify issue detection:

#### 6.1 Tool Home Position Warnings
**Test file**: _______________
- [ ] Tool home issue detected
- [ ] Warning message is clear
- [ ] Category is "Tool Home Position"
- [ ] Severity is "WARNING"

**Issue message**: _______________________________________________

#### 6.2 Bore Dimension Warnings
**Test file**: _______________
- [ ] Bore warning detected
- [ ] Warning message is clear
- [ ] Category is "Bore Dimensions"
- [ ] Severity is "WARNING"

**Issue message**: _______________________________________________

#### 6.3 Dimensional Issues
**Test file**: _______________
- [ ] Dimensional issue detected
- [ ] Warning message is clear
- [ ] Category is "Dimensional"
- [ ] Severity is "WARNING"

**Issue message**: _______________________________________________

#### 6.4 Missing Data
**Test file**: _______________
- [ ] Missing dimensions noted
- [ ] Info messages for each missing field
- [ ] Category is "Missing Data"
- [ ] Severity is "INFO"

**Missing fields detected**: _______________________________________________

#### 6.5 Multiple Issues
**Test file**: _______________
- [ ] All issues detected
- [ ] Issues grouped by category
- [ ] Total count is correct
- [ ] No duplicate warnings

**Total warnings**: _______
**Total errors**: _______
**Notes**: _______________________________________________

---

### 7. Data Extraction Tests

Verify correct data extraction:

#### 7.1 Program Information
**Test file**: _______________

| Field | Expected | Detected | ✓/✗ |
|-------|----------|----------|-----|
| Program Number | _________ | _________ | ___ |
| Title | _________ | _________ | ___ |
| Round Size | _________ | _________ | ___ |
| Spacer Type | _________ | _________ | ___ |
| Material | _________ | _________ | ___ |

#### 7.2 Dimensions
**Test file**: _______________

| Field | Expected | Detected | ✓/✗ |
|-------|----------|----------|-----|
| Outer Diameter | _________ | _________ | ___ |
| Thickness | _________ | _________ | ___ |
| Center Bore | _________ | _________ | ___ |
| Hub Diameter | _________ | _________ | ___ |
| Hub Height | _________ | _________ | ___ |

---

### 8. Performance Tests

#### 8.1 Small File (< 100 lines)
**Test file**: _______________
**File size**: _______ lines
**Scan time**: _______ seconds
- [ ] Scan completes quickly (< 1 second)

#### 8.2 Medium File (100-500 lines)
**Test file**: _______________
**File size**: _______ lines
**Scan time**: _______ seconds
- [ ] Scan completes reasonably (< 3 seconds)

#### 8.3 Large File (500+ lines)
**Test file**: _______________
**File size**: _______ lines
**Scan time**: _______ seconds
- [ ] Scan completes (< 10 seconds)
- [ ] UI remains responsive

#### 8.4 Multiple Consecutive Scans
- [ ] Can scan multiple files in a row
- [ ] No memory leaks (performance doesn't degrade)
- [ ] Results clear between scans

**Number of files scanned**: _______
**Notes**: _______________________________________________

---

### 9. Usability Tests

#### 9.1 UI Layout
- [ ] Window size is appropriate
- [ ] All elements fit without scrolling (main window)
- [ ] Font sizes are readable
- [ ] Colors are distinct and clear
- [ ] Tabs are easy to switch between

**Suggestions**: _______________________________________________

#### 9.2 Error Messages
- [ ] Error messages are clear
- [ ] Error messages suggest solutions
- [ ] No confusing technical jargon

**Examples**: _______________________________________________

#### 9.3 Workflow
- [ ] Workflow is intuitive
- [ ] Can scan file without reading instructions
- [ ] Button labels are clear
- [ ] Status messages are helpful

**Suggestions**: _______________________________________________

---

### 10. Comparison with Real Files

Test with actual repository files:

#### Test 1
**File**: _______________
**Known issues**: _______________________________________________
- [ ] Scanner detects known issues
- [ ] No false positives
- [ ] Results match expectations

#### Test 2
**File**: _______________
**Known issues**: _______________________________________________
- [ ] Scanner detects known issues
- [ ] No false positives
- [ ] Results match expectations

#### Test 3
**File**: _______________
**Known issues**: _______________________________________________
- [ ] Scanner detects known issues
- [ ] No false positives
- [ ] Results match expectations

---

## Bugs Found

| # | Description | Severity | Steps to Reproduce |
|---|-------------|----------|-------------------|
| 1 | ___________ | High/Med/Low | ________________ |
| 2 | ___________ | High/Med/Low | ________________ |
| 3 | ___________ | High/Med/Low | ________________ |

---

## Feature Requests / Improvements

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________
4. _______________________________________________
5. _______________________________________________

---

## Overall Assessment

### What Works Well
- _______________________________________________
- _______________________________________________
- _______________________________________________

### What Needs Improvement
- _______________________________________________
- _______________________________________________
- _______________________________________________

### Readiness for Integration
- [ ] **Ready** - No major issues found
- [ ] **Ready with minor fixes** - Minor issues noted but not blocking
- [ ] **Not ready** - Significant issues found

**Recommendation**: _______________________________________________

---

## Sign-Off

**Tester**: _______________
**Date**: _______________
**Status**: PASS / FAIL / CONDITIONAL PASS

**Notes**: _______________________________________________
_______________________________________________
_______________________________________________

---

## Next Steps

After testing is complete:

- [ ] Review all bugs found
- [ ] Prioritize bug fixes
- [ ] Implement improvements
- [ ] Re-test if changes made
- [ ] Proceed to integration if approved
- [ ] Move to Phase 1.2 (Database File Monitor)

---

**Test Session Complete**
