# View-Specific Statistics Feature

## Overview

Each tab now has its own dedicated **📊 Stats** button that shows statistics specific to that view only, preventing duplicate counts and confusion.

---

## 🎯 What Was Fixed

### Problem
Previously, the Repository tab showed combined statistics from ALL programs (repository + external), which caused confusion and duplicate results when trying to understand what was in each section.

### Solution
Created three separate statistics methods, each showing data specific to its tab:

1. **All Programs Tab** → Shows combined statistics
2. **Repository Tab** → Shows ONLY managed files (is_managed = 1)
3. **External Tab** → Shows ONLY external files (is_managed = 0 or NULL)

---

## 📊 Statistics by Tab

### 1. All Programs Tab Statistics

**Button Location:** Top right of All Programs tab
**Shows:**
- Total Programs (all files)
- Managed Files (Repository) - count and percentage
- External Files - count and percentage
- Total Versions
- Repository Size (MB)
- Versions Size (MB)
- Total Storage (MB)

**Subtitle:** "(Repository + External files combined)"

**Use Case:** Get an overview of your entire database

---

### 2. Repository Tab Statistics

**Button Location:** Top right of Repository tab
**Shows:**
- Repository Files (only is_managed = 1)
- Total Versions
- Repository Size (MB)
- Versions Size (MB)
- Total Storage (MB)

**Subtitle:** "(Managed files in repository/ folder only)"

**Use Case:** See how much space your managed files are taking up

---

### 3. External Tab Statistics

**Button Location:** Top right of External tab
**Shows:**
- External Files (only is_managed = 0 or NULL)
- Note about files remaining in original locations

**Subtitle:** "(Scanned files NOT in repository)"

**Use Case:** See how many external/scanned files are referenced in the database

---

## 🔧 Technical Implementation

### Code Changes

#### Tab Setup Changes

**All Programs Tab** ([gcode_database_manager.py:1054-1067](gcode_database_manager.py#L1054-L1067))
```python
def setup_all_programs_tab(self):
    # Info and action buttons
    info_frame = tk.Frame(self.all_programs_tab, bg=self.bg_color)
    info_frame.pack(fill=tk.X, pady=5, padx=10)

    # Info label
    tk.Label(info_frame, text="Viewing all programs (repository + external files)",
            bg=self.bg_color, fg=self.fg_color, font=("Arial", 10, "italic")).pack(side=tk.LEFT)

    # Stats button
    tk.Button(info_frame, text="📊 Stats", command=self.show_all_programs_stats,
             bg=self.accent_color, fg=self.fg_color, font=("Arial", 9, "bold"),
             width=10, height=1).pack(side=tk.RIGHT, padx=5)
```

**External Tab** ([gcode_database_manager.py:1114-1117](gcode_database_manager.py#L1114-L1117))
```python
# Stats button
tk.Button(info_frame, text="📊 Stats", command=self.show_external_stats,
         bg=self.accent_color, fg=self.fg_color, font=("Arial", 9, "bold"),
         width=10, height=1).pack(side=tk.RIGHT, padx=5)
```

#### Statistics Methods

**Repository Stats** ([gcode_database_manager.py:7559-7654](gcode_database_manager.py#L7559-L7654))
```python
def show_repository_stats(self):
    """Show ONLY repository (managed) files statistics"""
    # Only count managed files (is_managed = 1)
    cursor.execute("SELECT COUNT(*) FROM programs WHERE is_managed = 1")
    managed_count = cursor.fetchone()[0]
    # ... repository size, versions size calculation
```

**All Programs Stats** ([gcode_database_manager.py:7656-7750](gcode_database_manager.py#L7656-L7750))
```python
def show_all_programs_stats(self):
    """Show ALL programs statistics (repository + external combined)"""
    # Count all programs
    cursor.execute("SELECT COUNT(*) FROM programs WHERE file_path IS NOT NULL")
    total_count = cursor.fetchone()[0]

    # Count managed files
    cursor.execute("SELECT COUNT(*) FROM programs WHERE is_managed = 1")
    managed_count = cursor.fetchone()[0]

    # Count external files
    external_count = total_count - managed_count
    # ... show combined stats with percentages
```

**External Stats** ([gcode_database_manager.py:7752-7816](gcode_database_manager.py#L7752-L7816))
```python
def show_external_stats(self):
    """Show ONLY external (non-managed) files statistics"""
    # Only count external files (is_managed = 0 or NULL)
    cursor.execute("SELECT COUNT(*) FROM programs WHERE (is_managed = 0 OR is_managed IS NULL) AND file_path IS NOT NULL")
    external_count = cursor.fetchone()[0]
    # ... show external file count with notes
```

---

## 💡 Usage Examples

### Example 1: Check Repository Storage

**Scenario:** You want to know how much disk space your managed files are using.

**Steps:**
1. Click **📁 Repository** tab
2. Click **📊 Stats** button (top right)
3. View dialog showing:
   - Repository Files: 150
   - Total Versions: 12
   - Repository Size: 3.2 MB
   - Versions Size: 0.5 MB
   - Total Storage: 3.7 MB
4. Click **Close**

**Result:** You now know exactly how much space your managed files occupy.

---

### Example 2: Check External References

**Scenario:** You want to know how many external files you've scanned.

**Steps:**
1. Click **🔍 External/Scanned** tab
2. Click **📊 Stats** button (top right)
3. View dialog showing:
   - External Files: 6063
   - Note: External files remain in their original locations
4. Click **Close**

**Result:** You know you have 6063 external file references that aren't taking up repository space.

---

### Example 3: Get Complete Overview

**Scenario:** You want to see the breakdown of all files.

**Steps:**
1. Click **📋 All Programs** tab
2. Click **📊 Stats** button (top right)
3. View dialog showing:
   - Total Programs: 6213
   - Managed Files (Repository): 150 (2.4%)
   - External Files: 6063 (97.6%)
   - Total Versions: 12
   - Repository Size: 3.2 MB
   - Versions Size: 0.5 MB
   - Total Storage: 3.7 MB
4. Click **Close**

**Result:** You see the complete breakdown with percentages.

---

## ✅ Benefits

### No More Duplicates
- Each view shows ONLY its own data
- Repository stats don't include external files
- External stats don't include repository files
- All Programs shows the complete picture

### Clear Separation
- Repository Tab: "Managed files in repository/ folder only"
- External Tab: "Scanned files NOT in repository"
- All Programs: "Repository + External files combined"

### Accurate Counts
- SQL queries filter by `is_managed` flag
- No overlap between views
- Each count is independent

---

## 📋 Summary

### What Changed

| Tab | Stats Button | Shows | SQL Filter |
|-----|-------------|-------|------------|
| **All Programs** | ✅ Added | All files + breakdown | `WHERE file_path IS NOT NULL` |
| **Repository** | ✅ Modified | Only managed files | `WHERE is_managed = 1` |
| **External** | ✅ Added | Only external files | `WHERE is_managed = 0 OR is_managed IS NULL` |

### Files Modified

**gcode_database_manager.py:**
- Lines 1054-1067: Added stats button to All Programs tab
- Lines 1114-1117: Added stats button to External tab
- Lines 7559-7654: Modified `show_repository_stats()` to show only managed files
- Lines 7656-7750: Added `show_all_programs_stats()` method
- Lines 7752-7816: Added `show_external_stats()` method

### User Impact

✅ **No more confusion** - Each tab shows its own statistics
✅ **No duplicate counts** - Repository and External are separate
✅ **Better understanding** - See exactly what's in each section
✅ **Consistent UI** - All three tabs now have Stats buttons

---

## 🎉 Complete!

Each view now has its own dedicated statistics that show accurate, non-duplicated counts specific to that tab!

**Usage:**
- 📋 **All Programs** → Click 📊 Stats → See combined overview
- 📁 **Repository** → Click 📊 Stats → See only managed files
- 🔍 **External** → Click 📊 Stats → See only external files

---

*Feature implemented: 2025-11-26*
*Session: View-Specific Statistics Separation*
