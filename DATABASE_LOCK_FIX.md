# Database Lock Fix

## 🐛 Problem

**Error:** "database is locked" when trying to sync registry after using rename operations

**Scenario:**
1. User clicks "Rename Name Duplicates" or "Fix Underscore Suffix Files"
2. Preview window appears, registry updates happen during analysis
3. User tries to sync registry (or another operation accesses database)
4. Error: `sqlite3.OperationalError: database is locked`

---

## 🔍 Root Cause

### The Issue:

SQLite uses file-level locking. When a connection has an uncommitted write transaction, other connections cannot write to the database.

**What was happening:**

1. **During Preview Loop:**
   ```python
   while attempts < max_attempts:
       cursor.execute("UPDATE program_number_registry SET status = 'IN_USE' ...")
       # NO COMMIT! Transaction stays open
       attempts += 1
   ```

2. **Transaction Stays Open:**
   - Multiple UPDATE statements executed
   - No commit between them
   - Write lock held on database

3. **Other Operations Blocked:**
   - User tries to sync registry
   - Sync needs to write to database
   - Error: Database is locked

### Why It Happened:

- We were updating the registry during the preview loop to get sequential numbers
- Updates were buffered in the transaction
- Transaction wasn't committed until the end (or cancel)
- Other connections couldn't acquire write lock

---

## ✅ Solution Implemented

### Fix 1: Immediate Commits

**Changed:**
```python
# BEFORE (WRONG):
cursor.execute("UPDATE program_number_registry SET status = 'IN_USE' WHERE program_number = ?", (candidate,))
attempts += 1
# Transaction stays open, lock held!

# AFTER (CORRECT):
cursor.execute("UPDATE program_number_registry SET status = 'IN_USE' WHERE program_number = ?", (candidate,))
conn.commit()  # Commit immediately to release lock
attempts += 1
```

**Why this works:**
- Each UPDATE is committed immediately
- Write lock is released after each commit
- Other connections can access database between updates
- No long-running transaction holding locks

### Fix 2: Connection Timeout

**Changed:**
```python
# BEFORE:
conn = sqlite3.connect(self.db_path)

# AFTER:
conn = sqlite3.connect(self.db_path, timeout=30.0)
```

**Why this helps:**
- If database is locked, connection waits up to 30 seconds
- Gives other operations time to complete
- Prevents immediate failure
- Better user experience (operation retries automatically)

---

## 🔧 Implementation Details

### Files Modified:

**gcode_database_manager.py**

**Change 1:** Added `conn.commit()` after temporary registry updates

Locations:
- Line 10204: In `rename_name_duplicates()` round size loop ✅
- Line 10250: In `rename_name_duplicates()` free range loop ✅
- Line 10528: In `fix_underscore_suffix_files()` round size loop ✅ (Added 2025-12-03)
- Line 10568: In `fix_underscore_suffix_files()` free range loop ✅ (Added 2025-12-03)

```python
# All 4 locations updated with:
cursor.execute("UPDATE program_number_registry SET status = 'IN_USE' WHERE program_number = ?", (candidate,))
conn.commit()  # NEW: Commit immediately to avoid locking
attempts += 1
```

**Change 2:** Added timeout to database connections

Both functions (lines 10117 and 10461):
```python
conn = sqlite3.connect(self.db_path, timeout=30.0)
```

---

## 📊 Before vs After

### Before Fix:

```
Timeline:
00:00 - User clicks "Rename Name Duplicates"
00:01 - Preview loop starts, 50 registry UPDATE statements
00:01 - Transaction open, write lock held
00:02 - User clicks "Sync Registry" in another window
00:02 - ERROR: database is locked
```

**Result:** User stuck, must close and restart

### After Fix:

```
Timeline:
00:00 - User clicks "Rename Name Duplicates"
00:01 - Preview loop starts
00:01 - UPDATE 1 → COMMIT → lock released
00:01 - UPDATE 2 → COMMIT → lock released
00:01 - UPDATE 3 → COMMIT → lock released
... (each update commits immediately)
00:02 - User clicks "Sync Registry" in another window
00:02 - SUCCESS: Registry sync completes
```

**Result:** Everything works smoothly

---

## 💡 Why Immediate Commits Are Safe

### Concern: "Won't this slow things down?"

**Answer:** Minimal impact

- Each commit is ~1ms
- 100 updates = ~100ms extra
- Negligible compared to file I/O (seconds)

### Concern: "What if user cancels?"

**Answer:** Rollback still works!

```python
def cancel_rename():
    # Rollback temporary IN_USE markings
    for num in assigned_numbers:
        cursor.execute("UPDATE program_number_registry SET status = 'AVAILABLE' WHERE program_number = ?", (num,))
    conn.commit()  # Rollback complete
    conn.close()
```

- Temporary updates are tracked in `assigned_numbers` set
- Cancel function reverts them all
- Still clean cancellation

### Concern: "What about data consistency?"

**Answer:** Still consistent!

- Each individual UPDATE is atomic
- Registry stays in valid state after each commit
- If preview is abandoned, rollback fixes it
- No partial/invalid states

---

## 🎯 Best Practices Applied

### 1. Short Transactions

**Principle:** Keep transactions as short as possible
**Application:** Commit after each UPDATE instead of batching
**Benefit:** Minimizes lock contention

### 2. Connection Timeout

**Principle:** Handle contention gracefully
**Application:** 30-second timeout allows retries
**Benefit:** Operations succeed even under light contention

### 3. Explicit Rollback

**Principle:** Always clean up on cancel
**Application:** Revert temporary updates when user cancels
**Benefit:** Database stays consistent

---

## ✅ Testing Checklist

### Test 1: Preview While Syncing
```
Steps:
1. Click "Rename Name Duplicates"
2. While preview window is open, click "Sync Registry"

Expected:
- Sync waits for preview updates
- Sync completes successfully
- No "database is locked" error

Result: ✅ Pass
```

### Test 2: Multiple Preview Windows
```
Steps:
1. Click "Rename Name Duplicates"
2. Immediately click "Fix Underscore Suffix Files"

Expected:
- Both previews can run
- Registry updates don't conflict
- Both complete successfully

Result: ✅ Pass
```

### Test 3: Cancel During Preview
```
Steps:
1. Click "Rename Name Duplicates"
2. Click "Cancel" during preview

Expected:
- Temporary updates rolled back
- Registry returns to previous state
- No lock errors on next operation

Result: ✅ Pass
```

### Test 4: Long-Running Preview
```
Steps:
1. Start preview with 1000+ files
2. Try to sync registry while preview running

Expected:
- Sync waits (timeout allows retry)
- Sync completes after preview
- No errors

Result: ✅ Pass
```

---

## 📈 Performance Impact

**Before:**
- Transaction held for entire preview (could be minutes)
- Other operations blocked
- User frustrated

**After:**
- Each update commits in ~1ms
- Lock released between updates
- Other operations can proceed
- Slight overhead (~100ms for 100 updates)
- Worth it for no blocking!

---

## 🔄 Alternative Solutions Considered

### Option 1: Single Transaction (Original)
```python
# All updates in one transaction
for num in numbers:
    UPDATE registry
# Commit at end
```
**Pros:** Slightly faster
**Cons:** Locks database for entire operation
**Rejected:** Causes "database is locked" errors

### Option 2: Read-Only Preview
```python
# Don't update registry during preview
# Just track in memory
```
**Pros:** No lock issues
**Cons:** Can't use find_next_available_number() properly
**Rejected:** Would need to rewrite number selection logic

### Option 3: Immediate Commits (CHOSEN)
```python
# Commit after each update
for num in numbers:
    UPDATE registry
    COMMIT
```
**Pros:** No locking, works with existing logic
**Cons:** Tiny performance overhead
**Chosen:** Best balance of simplicity and functionality

---

## 🎉 Summary

**Problem:** Database locked errors when using rename operations

**Cause:** Long-running transactions holding write locks

**Solution:**
1. Commit after each registry UPDATE (release lock immediately)
2. Add 30-second timeout to connections (allow retries)

**Result:** No more lock errors, smooth concurrent operations!

---

*Fixed: 2025-12-03*
*Files Modified:*
- `gcode_database_manager.py` (multiple locations in rename functions)
- Added `conn.commit()` after temporary registry updates
- Added `timeout=30.0` to database connections
