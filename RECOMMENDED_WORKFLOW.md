# Recommended Workflow After Scanning

## 📋 Complete Workflow Overview

Here's the optimal workflow from scanning new files through to having clean, properly organized programs:

---

## Workflow Steps

### **Step 1: Scan Folder** 📂
**What:** Import new G-code files from external folders
**Where:** External tab → "Scan Folder" button
**Result:** Files added to database (marked as external, is_managed=0)

```
Example:
- Scanned folder: I:\My Drive\NC Master\REVISED PROGRAMS\
- Found: 150 new programs
- Added to database
- Duplicates handled with suffix (o12345 → o12345(1))
```

---

### **Step 2: Review Scan Results** 👀
**What:** Check what was imported
**Where:** External tab (shows all scanned files)
**Look for:**
- Any errors during scan
- Duplicate notices (programs with (1), (2) suffixes)
- Programs with missing data

**Optional:** Export stats to review quality

---

### **Step 3: Sync Registry** 🔄
**What:** Update program number registry with newly scanned programs
**How:** Run `populate_registry.py` script
**Why:** Registry needs to know which program numbers are now in use

```bash
python populate_registry.py
```

**Takes:** ~0.4 seconds
**Updates:** Marks scanned program numbers as IN_USE

---

### **Step 4: Detect Round Sizes** 🎯
**What:** Detect round sizes for all programs
**How:** Run batch detection
**Why:** Needed to identify out-of-range programs

```bash
python run_batch_detection.py
```

**Results:**
- 92.4% detected from titles
- 7.5% detected from dimensions
- 0.1% need manual input

**Updates:** Programs table with round_size, confidence, source

---

### **Step 5: Review Out-of-Range Programs** ⚠️
**What:** See which programs are in wrong ranges
**Where:** Repository tab → "⚠️ Out-of-Range Programs" button
**Shows:**
- Program number
- Detected round size
- Current range (wrong)
- Correct range (where it should be)

**Decision Point:**
- Small number (< 50): Can rename manually if desired
- Large number (> 50): Use batch rename

---

### **Step 6: Import to Repository (Optional)** 📥
**What:** Move files from external to repository
**When:** When you want managed files
**How:** External tab → Select files → "Add to Repository"

**What happens:**
- Files copied to repository folder
- is_managed flag set to 1
- Enables version control
- Enables rename operations

**Note:** You can skip this if you prefer to keep files external

---

### **Step 7: Batch Rename Out-of-Range Programs** 🔧
**What:** Automatically rename programs to correct ranges
**Where:** Repository tab → "🔧 Resolve Out-of-Range (Batch Rename)"
**Prerequisites:** Programs must be in repository (is_managed=1)

**Workflow:**
1. **Preview First:**
   - Set limit (start with 10-50)
   - Click "Generate Preview"
   - Review old → new mappings
   - Export to CSV if desired

2. **Test Small Batch:**
   - Execute on 10 programs
   - Verify results
   - Check files have legacy comments
   - Check registry updated

3. **Scale Up:**
   - Increase to 100, then 500
   - Finally run on all remaining

**What happens per program:**
- Finds next available number in correct range
- Updates file content with new program number
- Adds legacy comment: `(RENAMED FROM O62000 ON 2025-12-02)`
- Updates database program_number
- Tracks legacy name in database
- Updates registry (old=AVAILABLE, new=IN_USE)
- Creates audit log entry

---

### **Step 8: Handle Remaining Issues** 🔍
**What:** Deal with programs that couldn't be auto-renamed
**Examples:**
- Invalid round sizes (6.4355, 7.2934)
- Full ranges (10.5" range)
- Programs with no round size detected

**Options:**
1. Manually assign round sizes
2. Use free ranges (o1000-o9999, o14000-o49999)
3. Keep as-is if external files

---

### **Step 9: Manage Duplicates** 🔎
**What:** Handle duplicate programs
**Where:** Repository tab → "🔍 Manage Duplicates"
**Types:**
- **Type 1:** Same name, different content (now fixed by rename)
- **Type 2:** Same name, same content (keep newest)
- **Type 3:** Different name, same content (keep lowest number)

**Actions:**
- Review duplicates
- Keep or delete
- Merge if needed

---

### **Step 10: Final Sync** ✅
**What:** Final registry update
**When:** After all renames and duplicates handled
**How:** Run `populate_registry.py` one more time

**Result:** Registry perfectly in sync with database

---

## 📊 Simplified Quick Workflow

For most users, the minimal workflow is:

```
1. Scan Folder           (External tab)
   ↓
2. Sync Registry         (python populate_registry.py)
   ↓
3. Detect Round Sizes    (python run_batch_detection.py)
   ↓
4. Add to Repository     (External tab → Add Selected)
   ↓
5. Batch Rename          (Repository tab → Resolve Out-of-Range)
   ↓
6. Done!
```

---

## 🎯 Workflow Variations

### **For External Files Only (No Repository)**

```
1. Scan Folder
2. Sync Registry
3. Detect Round Sizes
4. Review stats and out-of-range list
5. Done (keep files external)
```

**Use Case:** Just want to catalog files, not manage them

---

### **For Repository Management**

```
1. Scan Folder
2. Sync Registry
3. Detect Round Sizes
4. Add to Repository
5. Batch Rename
6. Manage Duplicates
7. Final Sync
```

**Use Case:** Full program number management with renames

---

### **For Quick Import Without Renames**

```
1. Scan Folder
2. Add to Repository
3. Done
```

**Use Case:** Files already have correct numbers, just importing

---

## 📅 Maintenance Workflow

### **Weekly/Monthly Maintenance**

1. **Scan new folders** for recent programs
2. **Sync registry** after scanning
3. **Detect round sizes** for new programs
4. **Review out-of-range** count trend
5. **Batch rename** when count gets high (>100)

### **Before Major Changes**

1. **Create database backup**
   ```bash
   # Use app's backup feature or manual copy
   ```
2. **Export registry stats** for baseline
3. **Make changes** (rename, delete, etc.)
4. **Verify results**
5. **Sync registry** if needed

---

## ⚙️ Automation Ideas

### **Batch Script for Post-Scan Workflow**

Create `post_scan_workflow.bat`:
```batch
@echo off
echo === Post-Scan Workflow ===
echo.
echo Step 1: Syncing registry...
python populate_registry.py
echo.
echo Step 2: Detecting round sizes...
python run_batch_detection.py
echo.
echo === Workflow Complete ===
echo.
echo Next: Review out-of-range programs in the app
pause
```

**Usage:** Run this after every scan session

---

## 📈 Workflow Decision Tree

```
Scanned new files?
    │
    ├─→ Yes → Sync Registry
    │         ↓
    │         Detect Round Sizes
    │         ↓
    │         Any out-of-range?
    │         │
    │         ├─→ Yes → Want to fix?
    │         │         │
    │         │         ├─→ Yes → Add to Repository → Batch Rename
    │         │         └─→ No  → Leave as-is
    │         │
    │         └─→ No  → All good!
    │
    └─→ No  → Skip to maintenance
```

---

## 🛡️ Safety Checkpoints

### **Before Batch Rename:**
- ✅ Database backup created
- ✅ Preview generated and reviewed
- ✅ Test batch (10 programs) successful
- ✅ Registry is synced
- ✅ Files are in repository (is_managed=1)

### **After Batch Rename:**
- ✅ Check log for errors
- ✅ Verify a few renamed files have legacy comments
- ✅ Check registry statistics updated
- ✅ Out-of-range count decreased

---

## 📊 Typical Session Example

**Scenario:** You scanned 200 new programs

```
1. Scan Folder
   Result: 200 programs added to database

2. Sync Registry
   Result: Registry updated in 0.4 seconds
   Status: 200 new numbers marked IN_USE

3. Detect Round Sizes
   Result: 185 detected from title
           12 detected from dimensions
           3 need manual input
   Status: 197/200 auto-detected (98.5%)

4. Review Out-of-Range
   Result: 45 programs in wrong ranges

5. Add to Repository
   Selected: All 200 programs
   Result: Files copied to repository folder

6. Batch Rename (Preview)
   Limit: 10
   Result: Shows old → new mappings
   Status: All 10 ready to rename

7. Batch Rename (Execute)
   Batch 1: 10 programs → Success
   Batch 2: 35 programs → Success
   Total: 45 programs renamed

8. Final Check
   Out-of-range: 0 (down from 45)
   Registry: Synced automatically during rename
   Status: All clean!
```

**Time:** ~15 minutes total

---

## 🎓 Learning Curve

### **First Time:** ~30 minutes
- Read workflow
- Test on small batch (10 files)
- Learn UI features

### **Regular Use:** ~5 minutes per scan
- Scan folder
- Run two scripts
- Maybe batch rename

### **Expert Use:** ~2 minutes per scan
- Automated with batch script
- Just review results

---

## 💡 Pro Tips

1. **Always sync registry after scanning**
   - Keeps everything in sync
   - Only takes 0.4 seconds
   - Prevents confusion

2. **Preview before renaming**
   - Export CSV for records
   - Review carefully
   - Test small batch first

3. **Keep naming consistent**
   - Let system detect round sizes
   - Let system assign correct ranges
   - Don't fight the automation

4. **Regular maintenance beats crisis cleanup**
   - Weekly scan sessions
   - Keep out-of-range count low
   - Don't let 1,000+ pile up

5. **Use the statistics**
   - Registry Statistics shows capacity
   - Out-of-Range shows cleanup needed
   - Track trends over time

---

## 📞 When Things Go Wrong

### **Problem: Too many out-of-range programs**
**Solution:** Batch rename in chunks (100 at a time)

### **Problem: Registry out of sync**
**Solution:** Run `populate_registry.py`

### **Problem: Round sizes not detecting**
**Solution:** Check titles have format like "6.25 OD" or "6.25IN"

### **Problem: Range is full (10.5")**
**Solution:** Use free ranges or manual assignment

### **Problem: Renamed wrong program**
**Solution:** Check version history, restore old version, or use legacy_names to track

---

## 🎯 Summary

**The Golden Workflow:**
```
Scan → Sync → Detect → Review → Import → Rename → Done
```

**Time Investment:**
- First time: 30 min learning
- Regular use: 5 min per session
- Automation: 2 min per session

**Benefits:**
- Clean program number ranges
- Easy to find programs
- No duplicates or conflicts
- Full audit trail
- Always know what's available

---

*Created: 2025-12-02*
*All 3 phases implemented and tested*
