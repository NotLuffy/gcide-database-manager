# Duplicate Management Order - Before Batch Rename

## 🎯 Critical Question: What Order Should We Handle Duplicates?

When preparing for batch rename, you need to handle duplicates in a specific order to avoid wasting program numbers and causing conflicts.

---

## 📋 The Three Types of Duplicates

### **Type 1: Same Name, Different Content** (Scan-Time Conflicts)
- Created during scanning when multiple files have same program number
- Example: `o12345`, `o12345(1)`, `o12345(2)`
- These are different parts/versions with conflicting names
- **Issue:** ALL versions will be marked as out-of-range and would ALL get renamed

### **Type 2: Same Name, Same Content** (Exact Duplicates)
- Multiple files with identical content (same hash)
- Same program number, same file content
- Example: `o12345` appears 3 times in different folders during scan
- **Issue:** Wasting storage space with identical copies

### **Type 3: Different Name, Same Content** (Content Duplicates)
- Files with different program numbers but identical content
- Example: `o62000` and `o62500` have exactly the same G-code
- **Issue:** Same part stored under multiple program numbers

---

## ✅ Recommended Order (Most Efficient)

### **FIRST: Handle Type 2 (Exact Duplicates)**

**Why First:**
- These are the easiest to identify (same hash)
- No decision-making needed - they're identical
- Frees up the most space quickly
- Reduces the total count of files to process

**What to do:**
1. Click "🔍 Manage Duplicates" → Scan for content duplicates
2. For each exact duplicate group:
   - Keep the one in the correct range (if any)
   - Or keep the lowest program number
   - Or keep the newest file
3. Delete all other copies
4. Result: No more exact copies wasting space

**Example:**
```
Before:
- o12345 (same content)
- o12345(1) (same content)
- o12345(2) (same content)

After:
- o12345 (kept - original)
- Deleted: o12345(1), o12345(2)
```

---

### **SECOND: Handle Type 3 (Content Duplicates - Different Names)**

**Why Second:**
- These are wasting program numbers
- Same part exists under multiple numbers
- Should consolidate to one canonical program number

**What to do:**
1. Scan for files with same content hash but different program numbers
2. For each content duplicate group:
   - Keep the one in the correct range (if any)
   - Or keep the lowest program number
   - Or keep the most descriptive title
3. Delete other copies
4. Result: Each unique part has only one program number

**Example:**
```
Before:
- o62000 (6.25" spacer - wrong range)
- o62500 (6.25" spacer - correct range, same content as o62000)

After:
- o62500 (kept - already in correct range)
- Deleted: o62000 (duplicate content)

Benefit: o62000 is now AVAILABLE, and we don't waste another number renaming it
```

---

### **THIRD: Handle Type 1 (Same Name, Different Content)**

**Why Last:**
- These require human decision-making
- You need to determine which version is correct
- Cannot be automated based on content alone

**What to do:**
1. Review programs with suffixes: `o12345`, `o12345(1)`, `o12345(2)`
2. For each conflict group:
   - Compare the files (dimensions, dates, etc.)
   - Determine which is the correct/current version
   - Keep the correct one
   - Delete outdated versions
3. Result: Only current versions remain

**Example:**
```
Before:
- o12345 (6.25" x 1.0" - current version)
- o12345(1) (6.25" x 0.75" - old version)
- o12345(2) (6.25" x 1.5" - prototype version)

After:
- o12345 (kept - current version)
- Deleted: o12345(1), o12345(2)

Human decision required!
```

---

### **FINALLY: Batch Rename Out-of-Range**

**Why Last:**
- Only rename files you're keeping
- Don't waste numbers on files you'll delete
- Clean dataset ensures efficient use of ranges

**What happens:**
```
Remaining unique programs:
- o12345 (6.25" spacer) → Rename to o62500
- o67890 (7.0" spacer) → Rename to o70000
- o54321 (5.75" spacer) → Rename to o50000

All duplicates already removed, only unique programs renamed!
```

---

## 🔢 Complete Workflow Order

```
1. Scan Folder
   ↓
2. Sync Registry
   ↓
3. Detect Round Sizes
   ↓
4. Add to Repository
   ↓
5. Manage Type 2 Duplicates (Exact copies - same name, same content)
   → Delete identical copies
   ↓
6. Manage Type 3 Duplicates (Content duplicates - different name, same content)
   → Consolidate to one program number per part
   ↓
7. Manage Type 1 Duplicates (Name conflicts - same name, different content)
   → Keep correct version, delete old versions
   ↓
8. Batch Rename Out-of-Range
   → Only remaining unique programs get renamed
   ↓
9. Final Sync
   ↓
10. Done!
```

---

## 📊 Impact Example

**Scenario: You scanned 200 files**

### Without Proper Order:
```
200 files scanned
→ 150 are duplicates (Type 1, 2, 3 mixed)
→ Detect round sizes: All 200 get sizes detected
→ Out-of-range: 180 are in wrong ranges
→ Batch rename: All 180 get new numbers assigned
   Uses 180 program numbers!
→ Then manage duplicates: Delete 150 files
   150 program numbers WASTED!

Result: Wasted 150 program numbers
```

### With Proper Order:
```
200 files scanned
→ 150 are duplicates (Type 1, 2, 3 mixed)
→ Detect round sizes: All 200 get sizes detected
→ Out-of-range: 180 are in wrong ranges
→ Manage Type 2: Delete 80 exact copies (120 remain)
→ Manage Type 3: Delete 50 content duplicates (70 remain)
→ Manage Type 1: Delete 20 old versions (50 remain)
→ Batch rename: Only 50 unique programs renamed
   Uses 50 program numbers!

Result: Saved 130 program numbers!
```

---

## 🎯 Quick Reference Card

| Order | Type | Action | Automation |
|-------|------|--------|------------|
| 1st | Type 2 (Exact) | Delete identical copies | ✅ Can automate (keep first/newest) |
| 2nd | Type 3 (Content) | Consolidate program numbers | ⚠️ Semi-auto (keep lowest number) |
| 3rd | Type 1 (Conflict) | Keep correct version | ❌ Requires human review |
| 4th | N/A | Batch rename remaining | ✅ Fully automated |

---

## 💡 Pro Tips

### **Tip 1: Run Type 2 First - It's Fast and Easy**
- Same content hash = definitely duplicates
- No decision needed
- Clears out most duplicates quickly
- Example: If you accidentally scanned same folder twice

### **Tip 2: Type 3 Saves Program Numbers**
- If `o62000` and `o62500` are identical
- And o62500 is already in correct range
- Delete o62000, don't rename it!
- Saves using another program number

### **Tip 3: Type 1 Needs Careful Review**
- These are often different revisions
- Look at dates, titles, dimensions
- Keep the current production version
- Archive old versions if needed

### **Tip 4: Check Out-of-Range Count After Each Step**
- After Type 2: Count should decrease
- After Type 3: Count should decrease more
- After Type 1: Only unique programs remain
- Final batch rename only processes what's left

---

## ⚠️ What Happens If You Do It Wrong?

### **Scenario: Rename Before Deduplication**

```
Start: o12345, o12345(1), o12345(2) (all 6.25" spacers, all out-of-range)

Batch rename first:
→ o12345 → o62500
→ o12345(1) → o62501
→ o12345(2) → o62502

Then deduplicate:
→ Keep o62500
→ Delete o62501, o62502

Result:
- Wasted 2 program numbers (o62501, o62502 now empty)
- Those numbers are marked IN_USE in registry
- Can't easily reclaim them
```

### **Scenario: Deduplicate in Correct Order**

```
Start: o12345, o12345(1), o12345(2) (all 6.25" spacers, all out-of-range)

Deduplicate first:
→ Review and keep o12345 (current version)
→ Delete o12345(1), o12345(2)

Then batch rename:
→ o12345 → o62500

Result:
- Used only 1 program number
- Clean and efficient
- o62501, o62502 remain AVAILABLE for future use
```

---

## 🔍 How to Tell Which Duplicates You Have

### **In the UI:**

1. **Repository Tab → 🔍 Manage Duplicates**
   - Shows all duplicate groups
   - Identifies Type 1, 2, and 3

2. **Filter by Duplicate Type:**
   - Search & Filter → Dup Type dropdown
   - Select "CONTENT_DUP" for Type 2/3
   - Select "NAME_COLLISION" for Type 1

3. **Check Program Numbers:**
   - Look for suffixes: `(1)`, `(2)`, `(3)` = Type 1
   - Look for same name in list = Type 2
   - Different names, same content = Type 3

---

## 📝 Summary

**The Golden Rule:**
> Delete duplicates BEFORE renaming. Do it in order: Type 2 → Type 3 → Type 1 → Rename

**Why:**
> Each duplicate you delete is one less program number you need to assign during batch rename.

**Result:**
> Efficient use of program number ranges, no wasted numbers, clean organized repository.

---

*Created: 2025-12-03*
*This document explains the critical order for duplicate management before batch rename operations.*
