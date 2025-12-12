# Duplicate Management - Quick Reference

## 🎯 Complete Workflow (After Scanning)

```
1. Scan Folder           → Import files to database
2. Sync Registry         → Mark program numbers as IN_USE
3. Detect Round Sizes    → Identify which round sizes (8.5", 6.25", etc.)
4. Add to Repository     → Copy to managed repository folder
5. MANAGE DUPLICATES ⚠️  → (Complete ALL 3 passes below)
6. Batch Rename          → Fix out-of-range programs
7. Done!
```

---

## 🔍 Step 5: Manage Duplicates (3 Passes)

**Location:** Repository tab → "🔍 Manage Duplicates" button

**⚠️ CRITICAL: Must complete ALL 3 passes BEFORE batch rename!**

---

### **PASS 1: Delete Content Duplicates (Type 2 & 3)**

**Button:** "🗑️ Delete Content Duplicates (Type 2 & 3)"

**What it handles:**
- **Type 2:** Same name, same content (exact copies)
- **Type 3:** Different names, same content (one part, multiple numbers)

**Example:**
```
Type 2:
- o12345 (identical content)
- o12345 (identical content) ← delete this

Type 3:
- o62000 (6.25" spacer - wrong range)
- o62500 (6.25" spacer - correct range, same content) ← keep this
```

**How to use:**
1. Click "🗑️ Delete Content Duplicates" button
2. Review list of duplicates
3. Mark which to keep (✓)
4. Click "Delete Selected Duplicates"
5. Confirm

**Result:** Only unique files remain (one file per unique content)

---

### **PASS 2: Review Name Conflicts (Type 1)**

**Button:** "✏️ Rename Name Duplicates (Type 1)"

**What it handles:**
- **Type 1:** Same name, different content (versions/revisions)

**Example:**
```
- o12345     (6.25" x 1.0" - current version)
- o12345(1)  (6.25" x 0.75" - old version)
- o12345(2)  (6.25" x 1.5" - prototype)
```

**Two options:**

**Option A: Manual Delete (Recommended)**
1. Review each group
2. Compare files (dimensions, dates, etc.)
3. Keep current/correct version
4. Delete outdated versions manually
5. Close window

**Option B: Auto-Rename (Keep all versions)**
1. Click "✏️ Rename Name Duplicates" button
2. System keeps first file (o12345)
3. System renames duplicates to correct ranges:
   - o12345(1) with 8.5" → o85000
   - o12345(2) with 6.25" → o62501
4. Useful if you need all versions

**Result:** No name conflicts, each version has unique number

---

### **PASS 3: Fix Underscore Suffixes (Cleanup)**

**Button:** "🔧 Fix Underscore Suffix Files"

**What it handles:**
- Files with invalid program number suffixes
- Patterns: `o12345_1`, `o12345_2`, `o62000(1)`, etc.

**Example:**
```
Before:
- o12345_1.nc (8.5" spacer - invalid format)
- o12345_2.nc (8.5" spacer - invalid format)

After:
- o85000.nc (8.5" range - valid format)
- o85001.nc (8.5" range - valid format)
```

**How to use:**
1. Scroll to STEP 3 in Manage Duplicates window
2. Click "🔧 Fix Underscore Suffix Files" button
3. Review preview:
   ```
   o12345_1 → o85000 (8.5")
   o12345_2 → o85001 (8.5")
   o62000(1) → o62501 (6.25")
   ```
4. Click "✓ Confirm Rename"
5. Watch progress

**Result:** All files have valid program numbers (o##### format)

---

## 📊 Visual Flow

```
🔍 Manage Duplicates Button (Repository tab)
        ↓
┌───────────────────────────────────────┐
│  STEP 1: Content Duplicates (Type 2 & 3)  │
│  🗑️ Delete Content Duplicates         │
│                                       │
│  • Same content = one program         │
│  • Keep best version/range            │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  STEP 2: Name Conflicts (Type 1)      │
│  ✏️ Rename Name Duplicates            │
│                                       │
│  • Same name, different content       │
│  • Manual delete OR auto-rename       │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  STEP 3: Underscore Suffixes (Cleanup)│
│  🔧 Fix Underscore Suffix Files       │
│                                       │
│  • Invalid o12345_1 format            │
│  • Rename to correct ranges           │
└───────────────────────────────────────┘
        ↓
    ✅ Clean database
    Ready for batch rename!
```

---

## ⚠️ Important Rules

### **Rule 1: Complete ALL 3 Passes Before Batch Rename**
```
❌ WRONG:
1. Delete some duplicates
2. Batch rename out-of-range
3. Come back to delete more duplicates
→ Result: Wasted program numbers!

✅ CORRECT:
1. Complete Pass 1 (content duplicates)
2. Complete Pass 2 (name conflicts)
3. Complete Pass 3 (underscore suffixes)
4. THEN batch rename
→ Result: Only unique programs renamed!
```

### **Rule 2: Process in Order (Pass 1 → Pass 2 → Pass 3)**
```
Pass 1 deletes most duplicates (easy, automated)
   ↓
Pass 2 handles version conflicts (needs review)
   ↓
Pass 3 cleans up invalid suffixes (automated)
   ↓
Clean, ready for batch rename
```

### **Rule 3: Don't Skip Pass 3**
```
Files with underscore suffixes (o12345_1.nc):
- Not detected as out-of-range
- Have invalid program number format
- Must be fixed before batch rename
- Pass 3 handles this automatically
```

---

## 💡 Quick Tips

### **Tip 1: Use Pass 1 First**
- Deletes exact copies and content duplicates
- Fastest and easiest
- Clears out most duplicates
- Example: If you scanned same folder twice

### **Tip 2: Type 3 Saves Program Numbers**
```
If o62000 and o62500 are identical content:
- o62500 is already in correct range (6.25")
- Delete o62000, don't rename it!
- Saves using another program number
→ This is why Pass 1 happens BEFORE batch rename
```

### **Tip 3: Pass 2 Needs Judgment**
```
Name conflicts require human decision:
- Which version is current?
- Which dimensions are correct?
- Which is production vs prototype?

Options:
A. Manual review and delete (most common)
B. Auto-rename to keep all versions (rare)
```

### **Tip 4: Pass 3 is Cleanup**
```
After Pass 1 & 2, you may have:
- o12345_1.nc (leftover from scanning)
- o62000(1).nc (leftover from import)

Pass 3 fixes these automatically:
- o12345_1 (8.5") → o85000
- o62000(1) (6.25") → o62501
```

---

## 📈 Impact Example

**Scenario: 200 files scanned**

### Without Duplicate Management (Wrong):
```
200 files scanned
→ 180 are out-of-range
→ Batch rename: All 180 get new numbers
→ Uses 180 program numbers
→ Then discover 150 are duplicates
→ Delete 150 files
→ 150 program numbers WASTED!
```

### With Duplicate Management (Correct):
```
200 files scanned
→ 180 are out-of-range
→ Pass 1: Delete 80 exact copies (120 remain)
→ Pass 2: Delete 50 old versions (70 remain)
→ Pass 3: Fix 20 underscore suffixes (50 remain)
→ Batch rename: Only 50 unique programs renamed
→ Uses 50 program numbers
→ Saved 130 program numbers!
```

---

## 🎯 Summary

**The Golden Rule:**
> Complete ALL 3 passes of duplicate management BEFORE batch rename

**The Order:**
```
PASS 1: Content Duplicates (🗑️ button)
PASS 2: Name Conflicts (✏️ button or manual)
PASS 3: Underscore Suffixes (🔧 button)
THEN: Batch Rename
```

**Why It Matters:**
- Saves program numbers (don't rename files you'll delete)
- Cleans database (only unique programs remain)
- Standardizes format (all valid o##### numbers)
- Efficient workflow (batch operations)

**Time Investment:**
- Pass 1: 2-5 minutes (automated)
- Pass 2: 5-15 minutes (manual review)
- Pass 3: 1-2 minutes (automated)
- Total: 10-25 minutes
- Saves: Hours of manual cleanup later!

---

*Quick Reference - Keep this handy when managing duplicates!*
*Created: 2025-12-03*
