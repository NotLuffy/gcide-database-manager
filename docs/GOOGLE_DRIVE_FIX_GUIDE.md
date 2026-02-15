# Google Drive Letter Fix - Complete Guide

## The Problem

Google Drive assigns different drive letters on different computers:
- **Computer 1**: Google Drive is `L:\My Drive\`
- **Computer 2**: Google Drive is `M:\My Drive\`
- **Computer 3**: Google Drive is `N:\My Drive\`

When files are scanned, the database stores paths like:
```
L:\My Drive\Home\File organizer\repository\o00809.nc
```

When you switch to Computer 2, this path doesn't work because Google Drive is at `M:\` instead!

---

## ✅ Solution 1: Auto-Fix Drive Letter (Quick Fix)

**Use this when**: You need an immediate fix or switching between computers.

### Steps:
1. Open G-Code Database Manager
2. Go to **Maintenance** tab
3. Click **"💾 Fix Drive Letter"** button
4. Confirm the detected Google Drive location
5. Wait for it to update all paths

**What it does**:
- Detects where the database file currently is
- Finds the repository folder relative to the database
- Updates ALL file paths to use the current drive letter
- You can run this every time you switch computers

**Pros**:
- Works immediately
- No Windows configuration needed
- Safe and reversible

**Cons**:
- Need to click the button each time you switch computers
- Doesn't prevent the drive letter from changing

---

## ✅ Solution 2: Force Same Drive Letter (Permanent Fix)

**Use this when**: You want Google Drive to ALWAYS be the same drive letter on ALL computers.

### Steps:

#### On EACH Computer:

1. **Locate the batch script**:
   - It's in your Google Drive: `Fix_Google_Drive_Letter.bat`

2. **Run as Administrator**:
   - Right-click `Fix_Google_Drive_Letter.bat`
   - Select **"Run as administrator"**
   - Click **Yes** on the UAC prompt

3. **Follow the prompts**:
   - Script will find Google Drive automatically
   - It will create a **G:** drive that points to Google Drive
   - Press any key to confirm

4. **Verify**:
   - Open File Explorer
   - You should see **G:** drive
   - Navigate to `G:\Home\File organizer`
   - Your files should be there

5. **Update Database Settings** (ONE TIME ONLY):
   - Open G-Code Database Manager
   - Go to Settings
   - Update repository path to: `G:\Home\File organizer\repository`
   - Save settings

6. **Fix Existing Paths**:
   - Go to Maintenance tab
   - Click **"💾 Fix Drive Letter"**
   - All paths will update to use `G:\`

### After Setup:

Now on ALL computers:
- Google Drive appears as **G:** drive
- Database uses paths like: `G:\Home\File organizer\repository\o00809.nc`
- These paths work on EVERY computer because they all use `G:\`

---

## 🔧 Technical Details

### What the Batch Script Does:

```batch
# Creates a virtual drive G: that points to wherever Google Drive actually is:
subst G: "L:\My Drive"  # On Computer 1
subst G: "M:\My Drive"  # On Computer 2
subst G: "N:\My Drive"  # On Computer 3

# Makes it persistent (survives reboots):
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\DOS Devices" /v G: /t REG_SZ /d "\??\L:\My Drive" /f
```

### Alternative: Use Network Drive Mapping

If `subst` doesn't work, you can use network mapping:

1. Open **File Explorer**
2. Click **This PC** → **Map network drive**
3. Choose drive letter: **G:**
4. Folder: `\\localhost\L$\My Drive`
5. Check **"Reconnect at sign-in"**
6. Click **Finish**

---

## 📋 Recommended Workflow

**Best approach**: Use **Solution 2** (Force Same Drive Letter)

1. **On First Computer**:
   - Run `Fix_Google_Drive_Letter.bat` as admin
   - Update database settings to use `G:\`
   - Click "Fix Drive Letter" in Maintenance

2. **On Second Computer**:
   - Run `Fix_Google_Drive_Letter.bat` as admin
   - That's it! Database already uses `G:\` from sync

3. **On Third Computer**:
   - Run `Fix_Google_Drive_Letter.bat` as admin
   - That's it! Database already uses `G:\` from sync

### Benefits:
- Set up once per computer
- Never worry about drive letters again
- Files open correctly everywhere
- Database syncs perfectly via Google Drive

---

## 🛠️ Troubleshooting

### "G: drive already exists"
The script will remove the old G: mapping and create a new one.

### "Access Denied" error
You didn't run as administrator. Right-click → "Run as administrator"

### "G: drive disappears after reboot"
The registry setting didn't apply. Re-run the script as administrator.

### Files still won't open
1. Check if G: drive exists: `dir G:\` in Command Prompt
2. Click "Fix Drive Letter" button in Maintenance tab
3. Verify repository path in Settings

### Google Drive sync conflicts
- Google Drive syncs the database file
- When you click "Fix Drive Letter", it updates paths instantly
- Let Google Drive sync before switching computers
- Wait ~30 seconds for sync to complete

---

## 📝 Summary

| Solution | When to Use | Setup Time | Maintenance |
|----------|-------------|------------|-------------|
| **Solution 1**: Auto-Fix | Quick fix, occasional use | 10 seconds | Click button each computer switch |
| **Solution 2**: Force G: Drive | Permanent fix, multiple computers | 5 min per computer | None - automatic |

**Recommendation**: Use **Solution 2** for the best experience!

---

## 🎯 Quick Reference

### Fix Drive Letter Button:
- **Location**: Maintenance tab → "💾 Fix Drive Letter"
- **What it does**: Updates all paths to current drive letter
- **When to use**: After switching computers, after running batch script

### Batch Script:
- **File**: `Fix_Google_Drive_Letter.bat`
- **Location**: `L:\My Drive\Home\File organizer\` (or wherever Google Drive is now)
- **Run as**: Administrator
- **Purpose**: Makes Google Drive always appear as G: drive

---

**Questions?** Check the database logs or run "Integrity Check" in Maintenance tab.
