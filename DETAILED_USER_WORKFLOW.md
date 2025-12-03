# Detailed User Workflow - Step by Step Guide

## 🎯 Two Main Workflows

This system supports two workflows depending on how you want to manage your files:

1. **Repository Workflow** - Full management with renames and organization
2. **External Workflow** - Just catalog files where they are

---

## 📁 FIRST TIME USE - Repository Workflow (Recommended)

Use this if you want the system to manage, rename, and organize your files.

### **Step 1: Launch the Application**

```bash
python gcode_database_manager.py
```

The app opens with 3 tabs:
- **Repository Tab** - Your managed files
- **External Tab** - Scanned/temporary files
- **All Programs Tab** - Everything combined

---

### **Step 2: Scan Your First Folder**

**Where:** Click on **"External"** tab (middle tab)

**What you see:** Empty tree (no files yet)

**What to do:**
1. Click the **"Scan Folder"** button at the top
2. Browse to your G-code folder (e.g., `I:\My Drive\NC Master\REVISED PROGRAMS\`)
3. Select the folder and click OK

**Dialog appears:** "Choose Import Mode"

```
┌────────────────────────────────────────┐
│   📁 Choose Import Mode                │
├────────────────────────────────────────┤
│                                        │
│ How would you like to handle scanned   │
│ files?                                 │
│                                        │
│ • Repository: Copy files to managed    │
│   repository folder                    │
│   (Files under your control, organized)│
│                                        │
│ • External: Reference files in current │
│   location                             │
│   (Files stay where they are)          │
│                                        │
│   [Repository]      [External]         │
└────────────────────────────────────────┘
```

**First time users: Click "Repository"**

This will:
- Copy files to the `repository` folder
- Give you full control over the files
- Enable renaming and version control
- Mark files as `is_managed = 1`

---

### **Step 3: Watch the Scan Progress**

A progress window appears showing:
```
Processing file 1/150: o62000.nc
Processing file 2/150: o62500.nc
...
```

**What's happening:**
- Reading each G-code file
- Extracting program number, dimensions, title
- Adding to database
- Copying files to `repository` folder (if you chose Repository)

**If duplicates found during scan:**
```
DUPLICATE: o12345 -> saved as o12345(1)
```
The system automatically handles this by adding suffix numbers.

**When complete:**
```
Scan complete!
Added: 148 programs
Updated: 2 programs
Errors: 0
```

Click "Close"

---

### **Step 4: Check What Was Imported**

**Where:** Still on **External tab** (or switch to **Repository tab** if you chose Repository mode)

**What you see:**
- Tree view populated with your programs
- Columns: Program #, Title, Type, Diameter, Thickness, etc.

**Optional:** Click **"Stats"** button to see summary statistics

---

### **Step 5: Sync the Registry**

**IMPORTANT:** This does NOT happen automatically after scanning!

**Why needed:** The registry tracks all 98,001 possible program numbers. After scanning, it needs to know which numbers are now in use.

**How to sync:**

1. **Option A: Using UI Button (Recommended)**

   - Click the **"🔄 Workflow"** tab at the top
   - Click **"🔄 Sync Registry"** button
   - Click **"Yes"** to confirm
   - Watch the progress window with live log
   - See completion summary

   You'll see:
   ```
   ✅ REGISTRY SYNC COMPLETE
   Total numbers: 97,001
   In use: 12,046
   Available: 84,955
   Duplicates: 0
   ```

   **Time:** About 0.4 seconds

2. **Option B: Using Command Line (Alternative)**
   ```bash
   python populate_registry.py
   ```

**When to sync:**
- After every scan session
- Before using batch rename
- Once a week if scanning frequently

---

### **Step 6: Detect Round Sizes**

**IMPORTANT:** This does NOT happen automatically during scan!

**Why needed:** To identify which programs are in the wrong ranges so they can be renamed.

**How to detect:**

1. **Option A: Using UI Button (Recommended)**

   - Stay on the **"🔄 Workflow"** tab
   - Click **"🎯 Detect Round Sizes"** button
   - Click **"Yes"** to confirm
   - Watch progress bar as it processes all programs
   - See real-time detection statistics
   - View completion summary

   You'll see:
   ```
   ✅ DETECTION COMPLETE
   Total processed: 12,046
   Detected from title: 11,134 (92.4%)
   Detected from G-code: 803 (6.7%)
   Detected from dimensions: 97 (0.8%)
   Manual input needed: 12 (0.1%)

   In correct range: 10,523
   Out of range: 1,511
   ```

   **Time:** 10-30 seconds depending on number of programs

2. **Option B: Using Command Line (Alternative)**
   ```bash
   python run_batch_detection.py
   ```

   You'll see similar output in the terminal

   Processing 12,046 programs...

   [1/12046] Processing o62000...
   [2/12046] Processing o62500...
   ...

   DETECTION COMPLETE
   Processed: 12,031
   From titles: 11,114 (92.4%)
   From dimensions: 908 (7.5%)
   Manual needed: 9 (0.1%)

   Out of range: 1,225 (10.2%)
   ```

   **Time:** About 30-60 seconds for 12,000 programs

2. **Option B: No Button Available**
   Currently there is NO automatic detection button in the UI. You **must** use the command line script.

**When to detect:**
- After scanning new files
- After adding to repository
- Before batch renaming

---

### **Step 7: Review Out-of-Range Programs**

**Where:** **Repository tab** (top left tab)

**What to do:**
1. Look for the button: **"⚠️ Out-of-Range Programs"** (purple/red button)
2. Click it

**Window opens showing:**
```
┌──────────────────────────────────────────────┐
│  ⚠️ Programs in Wrong Ranges                 │
├──────────────────────────────────────────────┤
│ Found 1,225 programs in wrong ranges         │
│                                              │
│ Program# │Round Size│Current Range│Correct   │
│──────────┼──────────┼─────────────┼─────────│
│ o62000   │ 6.25     │o60000-62499 │o62500-  │
│          │          │(6.0)        │o64999   │
│ o62001   │ 6.25     │o60000-62499 │o62500-  │
│          │          │(6.0)        │o64999   │
│ ...      │          │             │         │
└──────────────────────────────────────────────┘

[Export to CSV]  [Refresh]  [Close]
```

**What this means:**
- These programs have the wrong number for their round size
- Example: o62000 is a 6.25" spacer but in the 6.0" range
- Should be renamed to o62500 or higher

**Optional:** Export to CSV to review offline

---

### **Step 8: Batch Rename Out-of-Range Programs**

**Where:** **Repository tab**

**What to do:**
1. Click **"🔧 Resolve Out-of-Range (Batch Rename)"** button (purple button)

**Window opens:**
```
┌──────────────────────────────────────────────┐
│  🔧 Batch Rename Resolution                  │
├──────────────────────────────────────────────┤
│ This will rename programs to correct ranges  │
│                                              │
│ [Generate Preview]  Limit: [50___]          │
│                                              │
│ (empty - no preview yet)                     │
│                                              │
│ No preview generated yet                     │
│                                              │
│ [⚠️ EXECUTE] [Export] [Close]                │
│ (disabled)                                   │
└──────────────────────────────────────────────┘
```

---

### **Step 8a: Generate Preview**

**What to do:**
1. In the "Limit" field, type: **10** (start small!)
2. Click **"Generate Preview"**

**What happens:**
- System finds next available number for each program
- Shows you what will change

**Preview table appears:**
```
Old #   │New #   │Round Size│Current Range │Correct Range│Title
────────┼────────┼──────────┼──────────────┼─────────────┼──────
o62000  │o62500  │6.25      │o60000-o62499 │o62500-64999 │6.25 OD...
o62001  │o62501  │6.25      │o60000-o62499 │o62500-64999 │6.25 OD...
o62002  │o62502  │6.25      │o60000-o62499 │o62500-64999 │6.25 OD...
...
```

**Status line shows:**
```
Preview: 10 programs | 10 ready | 0 errors
```

**The execute button is NOW ENABLED** (red warning button)

---

### **Step 8b: Execute Small Test Batch**

**CRITICAL: Start with 10 programs to test!**

**What to do:**
1. Review the preview carefully
2. Optional: Click **"Export Preview to CSV"** to keep a record
3. Click **"⚠️ EXECUTE BATCH RENAME ⚠️"**

**Confirmation dialog appears:**
```
┌────────────────────────────────────┐
│  Confirm Batch Rename              │
├────────────────────────────────────┤
│ This will rename 10 programs.      │
│                                    │
│ Each program will:                 │
│  - Get new number in correct range │
│  - Have legacy name in database    │
│  - Have comment added to file      │
│  - Be logged in audit table        │
│                                    │
│ This cannot be easily undone.      │
│                                    │
│ Do you want to proceed?            │
│                                    │
│        [Yes]  [No]                 │
└────────────────────────────────────┘
```

Click **"Yes"**

---

### **Step 8c: Watch Progress**

**Progress window appears:**
```
┌────────────────────────────────────┐
│  🔧 Renaming Programs...           │
├────────────────────────────────────┤
│ [████████░░] 80%                   │
│                                    │
│ Processing 8/10: o62007            │
│                                    │
│ LOG:                               │
│ [1/10] Processing o62000...        │
│ [2/10] Processing o62001...        │
│ ...                                │
│ [10/10] Processing o62009...       │
│ ──────────────────────────────────│
│ BATCH RENAME COMPLETE              │
│ Total: 10                          │
│ Successful: 10                     │
│ Failed: 0                          │
│ Skipped: 0                         │
│                                    │
│           [Close]                  │
└────────────────────────────────────┘
```

---

### **Step 8d: Verify Results**

**What to check:**

1. **Check a renamed file:**
   - Open one of the renamed files in notepad
   - Look for the legacy comment at the top:
     ```gcode
     O62500
     (RENAMED FROM O62000 ON 2025-12-03 - OUT OF RANGE)
     (6.25 OD SPACER CB 54MM)
     ...
     ```

2. **Check Out-of-Range count:**
   - Click "⚠️ Out-of-Range Programs" again
   - Count should be 10 less (was 1,225, now 1,215)

3. **Check Registry Statistics:**
   - Click "📋 Program Number Registry" button
   - Should show updated usage

**If everything looks good:** Proceed to rename more!

---

### **Step 9: Scale Up Batch Rename**

Once you've verified the test batch works:

1. **Preview 100 programs:**
   - Limit: **100**
   - Generate Preview
   - Execute

2. **Preview 500 programs:**
   - Limit: **500**
   - Generate Preview
   - Execute

3. **Preview ALL remaining:**
   - Limit: **all**
   - Generate Preview
   - Execute

**Total time for 1,225 programs:** About 5-10 minutes

---

### **Step 10: Final Check**

**What to verify:**

1. **Out-of-Range Programs:**
   - Should be down to ~20 (the ones that can't be auto-renamed)
   - These need manual review

2. **Registry Statistics:**
   - Click "📋 Program Number Registry"
   - Check usage percentages
   - Verify numbers make sense

3. **Files in Repository:**
   - Navigate to `repository` folder
   - Spot-check a few files
   - All should have correct program numbers

---

## 🔄 RETURNING USER WORKFLOW - Repository Mode

When you scan more files after the initial setup:

### **Quick Workflow (5-10 minutes):**

```
1. Scan Folder
   Files tab → Scan Folder → Choose Repository
   Result: New files added to repository

2. Sync Registry
   Workflow tab → 🔄 Sync Registry button
   Result: Registry updated with new program numbers

3. Detect Round Sizes
   Workflow tab → 🎯 Detect Round Sizes button
   Result: Round sizes detected for new programs

4. Check Out-of-Range
   Repository tab → ⚠️ Out-of-Range Programs
   Result: See how many new programs need renaming

5. Manage Duplicates FIRST ⚠️
   Repository tab → 🔍 Manage Duplicates
   Review programs with suffixes like o12345(1), o12345(2)
   Delete duplicate copies, keep only correct versions
   Result: Only unique programs remain

6. Batch Rename (after duplicates removed)
   Repository tab → 🔧 Resolve Out-of-Range
   Preview → Execute
   Result: Programs renamed to correct ranges

7. Done!
```

**Time:** 5-10 minutes depending on file count

**All done in the UI - no command line needed!**

**⚠️ CRITICAL:** Step 5 (Manage Duplicates) MUST happen before Step 6 (Batch Rename).
If you skip this, you'll waste program numbers renaming files you're going to delete!

---

## 📂 EXTERNAL WORKFLOW (Read-Only Catalog)

Use this if you just want to catalog files without moving or renaming them.

### **First Time Setup:**

```
1. Scan Folder
   Files tab → Scan Folder → Choose EXTERNAL
   Result: Files referenced in place (not copied)

2. Sync Registry
   Workflow tab → 🔄 Sync Registry button
   Result: Registry updated

3. Detect Round Sizes
   Workflow tab → 🎯 Detect Round Sizes button
   Result: Round sizes detected

4. Review Statistics
   Workflow tab → 📊 Round Size Stats button
   OR External tab → Stats button
   Result: See what you have

5. Done!
```

**All done in the UI - no command line needed!**

**What you CAN do:**
- View all programs in database
- Search and filter
- Export to CSV
- View statistics
- Check out-of-range programs

**What you CANNOT do:**
- Rename programs (they're not in repository)
- Version control
- Delete from repository (they're not there)

---

### **Returning User - External Mode:**

```
1. Scan Folder → Choose EXTERNAL
2. Workflow tab → 🔄 Sync Registry button
3. Workflow tab → 🎯 Detect Round Sizes button
4. Workflow tab → 📊 Round Size Stats button
```

**Time:** 2-3 minutes

**All done in the UI - no command line needed!**

---

## 🔀 SWITCHING FROM EXTERNAL TO REPOSITORY

If you scanned as External but want to move files to Repository:

### **Migration Workflow:**

```
1. External tab → Select programs you want in repository
   (Ctrl+Click to multi-select, or Ctrl+A for all)

2. Click "Add to Repository" button
   Result: Files copied to repository folder
           is_managed flag set to 1

3. Now you can rename them
   Repository tab → 🔧 Resolve Out-of-Range
```

---

## 📋 COMMAND LINE SCRIPTS - WHEN TO USE

### **populate_registry.py**

**What it does:** Updates the registry of all 98,001 program numbers

**When to run:**
- ✅ After scanning new files
- ✅ After deleting programs
- ✅ After batch rename (auto-updates, but good to verify)
- ✅ Once a week if actively scanning
- ✅ Before using batch rename

**How to run:**
```bash
python populate_registry.py
```

**Takes:** 0.4-0.5 seconds

---

### **run_batch_detection.py**

**What it does:** Detects round sizes for all programs

**When to run:**
- ✅ After scanning new files
- ✅ After adding to repository
- ✅ Before batch rename
- ✅ When you want to see out-of-range counts

**How to run:**
```bash
python run_batch_detection.py
```

**Takes:** 30-60 seconds for 12,000 programs

---

### **test_phase3_rename.py**

**What it does:** Tests the rename system without making changes

**When to run:**
- ✅ First time using batch rename
- ✅ After database schema changes
- ✅ To see what would be renamed

**How to run:**
```bash
python test_phase3_rename.py
```

**Takes:** 5 seconds

---

## 🚫 COMMON MISTAKES TO AVOID

### ❌ Mistake 1: Forgetting to Sync Registry
**Problem:** Registry shows old data
**Solution:** Run `populate_registry.py` after scanning

### ❌ Mistake 2: Trying to Rename External Files
**Problem:** "Program not in repository" error
**Solution:** Add to repository first (External tab → Add to Repository)

### ❌ Mistake 3: Not Running Round Size Detection
**Problem:** Can't see out-of-range programs
**Solution:** Run `run_batch_detection.py` after scanning

### ❌ Mistake 4: Renaming All 1,225 Programs at Once
**Problem:** If something goes wrong, hard to recover
**Solution:** Start with 10, then 100, then 500, then all

### ❌ Mistake 5: Not Creating Database Backup
**Problem:** Can't undo if something goes wrong
**Solution:** Use app's backup feature before major operations

---

## 💾 CREATING DATABASE BACKUP

**Before batch rename or major changes:**

### **Option 1: Built-in Backup (Recommended)**
The app automatically creates backups in `Database_Backups` folder on startup and keeps the last 10.

### **Option 2: Manual Backup**
Copy `gcode_database.db` to a safe location:
```bash
copy gcode_database.db gcode_database_backup_2025-12-03.db
```

---

## 📊 UI BUTTONS QUICK REFERENCE

### **External Tab:**
- **Scan Folder** - Import new files (choose Repository or External)
- **Stats** - View statistics
- **Add to Repository** - Move selected external files to repository
- **Remove from Database** - Delete external entries

### **Repository Tab:**
- **📋 Program Number Registry** - View registry statistics
- **⚠️ Out-of-Range Programs** - See programs needing rename
- **🔧 Resolve Out-of-Range** - Preview and execute batch rename
- **🔍 Manage Duplicates** - Handle duplicate programs
- **Export/Import/Delete** - File operations

### **All Programs Tab:**
- Shows combined view (Repository + External)
- Stats show combined counts

---

## ⏱️ TIME ESTIMATES

### **First Time Setup (200 programs):**
- Scan folder: 2 minutes
- Sync registry: < 1 second
- Detect round sizes: 30 seconds
- Review out-of-range: 2 minutes
- Preview rename: 1 minute
- Test batch (10): 1 minute
- Full batch rename (45): 3 minutes
- **Total: ~10 minutes**

### **Returning User (100 new programs):**
- Scan: 1 minute
- Sync: < 1 second
- Detect: 15 seconds
- Review: 1 minute
- Rename if needed: 2 minutes
- **Total: ~5 minutes**

---

## 🎯 RECOMMENDED WORKFLOW SUMMARY

### **For Full Management (Repository):**

```
┌─────────────────────────────────────────┐
│ 1. Scan Folder → Choose REPOSITORY     │
│    Result: Files copied to repository   │
├─────────────────────────────────────────┤
│ 2. python populate_registry.py         │
│    Result: Registry synced              │
├─────────────────────────────────────────┤
│ 3. python run_batch_detection.py       │
│    Result: Round sizes detected         │
├─────────────────────────────────────────┤
│ 4. ⚠️ Out-of-Range Programs (button)    │
│    Result: See what needs fixing        │
├─────────────────────────────────────────┤
│ 5. 🔧 Resolve Out-of-Range (button)     │
│    → Preview (limit=10)                 │
│    → Execute test batch                 │
│    → Scale up to all                    │
│    Result: Programs renamed             │
└─────────────────────────────────────────┘
```

### **For Read-Only Catalog (External):**

```
┌─────────────────────────────────────────┐
│ 1. Scan Folder → Choose EXTERNAL       │
│    Result: Files referenced in place    │
├─────────────────────────────────────────┤
│ 2. python populate_registry.py         │
│    Result: Registry synced              │
├─────────────────────────────────────────┤
│ 3. python run_batch_detection.py       │
│    Result: Round sizes detected         │
├─────────────────────────────────────────┤
│ 4. View stats and analyze              │
│    Result: Understand your collection   │
└─────────────────────────────────────────┘
```

---

## ❓ FAQ

**Q: Do I have to use Repository mode?**
A: No, External mode works for read-only catalog. But you need Repository for renaming.

**Q: Why isn't there a button to sync registry?**
A: Currently must use command line: `python populate_registry.py`

**Q: Does round size detection happen automatically?**
A: No, must run manually: `python run_batch_detection.py`

**Q: How often should I sync registry?**
A: After every scan session, or at least weekly if scanning frequently.

**Q: Can I undo a batch rename?**
A: Not easily. That's why we start with small test batches. Create database backup first.

**Q: What if a file can't be renamed?**
A: Check the out-of-range window - shows status. Usually means no space in range or invalid round size.

**Q: Should I scan all my files at once?**
A: You can, but starting with one folder helps you learn the workflow.

---

*Created: 2025-12-03*
*All features tested and verified*
