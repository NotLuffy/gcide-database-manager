# Multi-Computer Sync & Google Sheets Automation

## Current Situation Analysis

### What You Have Now

#### Google Drive Setup (Files)
- ✅ **Repository files** stored in Google Drive
- ✅ **Multiple computers** can access same files
- ✅ **File sync** handled automatically by Google Drive
- ✅ **NC files** are synchronized across computers

#### Database (SQLite) - THE PROBLEM
- ❌ **SQLite database** (gcode_database.db) stored in Google Drive
- ⚠️ **Major issue**: SQLite is NOT designed for concurrent multi-computer access
- ⚠️ **Data corruption risk**: Two computers opening database at same time
- ❌ **No automatic sync**: Changes on one computer don't appear on others until manual refresh
- ❌ **Conflict potential**: Google Drive may create conflicted copies

#### Google Sheets Export
- ❌ **Manual only**: Click button → Save Excel → Upload to Google Sheets
- ❌ **No automation**: Must manually update when programs change
- ❌ **Two-step process**: Excel export, then Google Sheets import
- ❌ **No live updates**: Google Sheet doesn't reflect database changes

---

## Problems Identified

### Problem 1: SQLite + Google Drive = Danger ⚠️

**Why it's bad:**
```
Computer A: Opens database → Writes data → Closes database
Computer B: Opens database → Writes data → Closes database
Google Drive: Syncing... conflict detected!
Result: ⚠️ Corrupted database or conflicted copies
```

**SQLite limitations:**
- Single-writer design
- File locking issues across network
- Google Drive sync delays
- Risk of database corruption

**Your current setup works ONLY if:**
- ✅ Only one computer accesses database at a time
- ✅ Wait for Google Drive to sync before switching computers
- ✅ No simultaneous access
- ✅ Manual coordination between users

### Problem 2: No Real-Time Updates

When Computer A adds a program:
- ❌ Computer B doesn't see it until app restart
- ❌ Google Sheet doesn't update automatically
- ❌ Manual export/import required

### Problem 3: Manual Google Sheets Updates

Current process:
1. Make changes in database
2. Click "📈 Google Sheets" button
3. Save Excel file
4. Open Google Sheets
5. Import Excel file
6. Replace existing data

**Issues:**
- ⏱️ Time-consuming (5+ steps)
- 🔄 Easy to forget to update
- 📊 Google Sheet often out of date
- 🔴 No automation

---

## Solutions

### 🎯 Option 1: Keep Current Setup with Improvements (Easiest)

**Best for**: Small team, controlled access, minimal changes

#### What to do:

1. **Add Database Lock Indicator**
   - Show which computer has database open
   - Prevent simultaneous access
   - Warning when another computer is using it

2. **Add Auto-Refresh**
   - Automatically reload when database changes detected
   - Show notification when updates available
   - Refresh button in UI

3. **Add Conflict Prevention**
   - Check if database modified by another computer
   - Prompt to reload before making changes
   - Create backup before any write operation

4. **Add Semi-Automated Google Sheets Export**
   - Button to export AND upload to Google Sheets
   - Use Google Sheets API
   - One-click update instead of multi-step

#### Implementation difficulty: ⭐⭐ (Easy)
#### Cost: Free
#### Risk: Low

---

### 🎯 Option 2: Centralized Database (Recommended)

**Best for**: Multiple users, real-time updates, professional setup

#### Architecture:
```
┌─────────────────────────────────────────┐
│         Shared Network Database         │
│  (MySQL/PostgreSQL on network server)   │
└─────────────────────────────────────────┘
           ↑         ↑         ↑
           │         │         │
    ┌──────┴───┐ ┌──┴─────┐ ┌─┴──────┐
    │Computer A│ │Computer B│ │Computer C│
    │  (GUI)   │ │  (GUI)   │ │  (GUI)   │
    └──────────┘ └──────────┘ └──────────┘
```

#### What to do:

1. **Set up central database server**
   - Use MySQL or PostgreSQL
   - Host on network computer or cloud service
   - Configure for multi-user access

2. **Modify application**
   - Replace SQLite with MySQL/PostgreSQL connector
   - Add connection settings dialog
   - Handle network errors gracefully

3. **Keep files in Google Drive**
   - NC files still in Google Drive (works great)
   - Only database centralized
   - Best of both worlds

#### Benefits:
- ✅ Real-time updates across all computers
- ✅ No corruption risk
- ✅ Multiple users simultaneously
- ✅ Proper concurrency control
- ✅ Transaction support
- ✅ Backup/restore tools available

#### Implementation difficulty: ⭐⭐⭐⭐ (Moderate-Hard)
#### Cost: Free (self-hosted) or $5-20/month (cloud-hosted)
#### Risk: Moderate (requires testing)

---

### 🎯 Option 3: Cloud Database Service (Premium)

**Best for**: Professional setup, no IT management, scalable

#### Services to consider:

1. **Google Cloud SQL** (PostgreSQL)
   - Integrates with Google ecosystem
   - Automatic backups
   - $10-50/month depending on size

2. **AWS RDS** (MySQL/PostgreSQL)
   - Very reliable
   - Many backup options
   - $15-100/month depending on size

3. **PlanetScale** (MySQL)
   - Free tier available
   - Designed for real-time apps
   - Easy to set up

4. **Supabase** (PostgreSQL)
   - Free tier available
   - Built-in API
   - Modern interface

#### Benefits:
- ✅ Professional-grade reliability
- ✅ Automatic backups
- ✅ No server maintenance
- ✅ Scales as you grow
- ✅ 99.9% uptime guarantee

#### Implementation difficulty: ⭐⭐⭐ (Moderate)
#### Cost: $0-50/month
#### Risk: Low (managed service)

---

## Google Sheets Automation Solutions

### 🎯 Option 1: Direct Google Sheets API Integration (Recommended)

**How it works:**
```python
Program → Database → Google Sheets API → Live Update
                      ↑
                   Automatic!
```

#### Implementation:

1. **Set up Google Sheets API**
   - Create Google Cloud project
   - Enable Google Sheets API
   - Get credentials (OAuth or Service Account)
   - Install gspread library

2. **Add auto-update triggers**
   - After adding new program → Update sheet
   - After editing program → Update sheet
   - After deleting program → Update sheet
   - Batch updates every 5 minutes

3. **Configure update modes**
   - Real-time: Update immediately (slower)
   - Batched: Queue updates, send every N minutes (faster)
   - Manual: Keep current button, but one-click

#### Code example:
```python
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class GoogleSheetsSync:
    def __init__(self, credentials_file, spreadsheet_id):
        scope = ['https://spreadsheets.google.com/feeds']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            credentials_file, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(spreadsheet_id)

    def update_programs(self, programs_data):
        """Update Google Sheet with latest program data"""
        worksheet = self.sheet.worksheet('All Programs')

        # Clear old data
        worksheet.clear()

        # Write headers
        headers = ['Program #', 'Round Size', 'Thickness', 'CB',
                   'OB', 'Hub Height', 'Type', 'Title']
        worksheet.append_row(headers)

        # Write data
        for program in programs_data:
            worksheet.append_row(program)

    def add_program(self, program_data):
        """Add single program to sheet"""
        worksheet = self.sheet.worksheet('All Programs')
        worksheet.append_row(program_data)
```

#### Integration points:
- In `add_program()` method → Call `sheets_sync.add_program()`
- In `update_program()` method → Call `sheets_sync.update_program()`
- In `delete_program()` method → Call `sheets_sync.delete_program()`
- Add settings dialog for Google Sheets credentials
- Add enable/disable toggle in preferences

#### Benefits:
- ✅ No manual export needed
- ✅ Google Sheet always up-to-date
- ✅ Real-time or batched updates
- ✅ One-time setup
- ✅ Works from any computer

#### Implementation difficulty: ⭐⭐⭐ (Moderate)
#### Cost: Free (Google Sheets API is free)
#### Libraries needed:
```bash
pip install gspread oauth2client
```

---

### 🎯 Option 2: Scheduled Auto-Export

**How it works:**
- Background task runs every N minutes
- Exports database to Excel
- Uploads to Google Drive folder
- You manually import to Google Sheets (or use Google Apps Script)

#### Implementation:

1. **Add background export task**
```python
import threading
import time

def auto_export_worker(self):
    """Background thread for automatic exports"""
    while self.auto_export_enabled:
        time.sleep(300)  # 5 minutes

        if self.has_pending_changes:
            # Export to Google Drive folder
            export_path = os.path.join(
                self.google_drive_export_folder,
                f"GCode_Auto_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )
            self.export_google_sheets_to_file(export_path)
            self.has_pending_changes = False

# Start background thread on app launch
self.auto_export_enabled = True
threading.Thread(target=self.auto_export_worker, daemon=True).start()
```

2. **Track changes**
```python
def add_program(self, ...):
    # ... existing code ...
    self.has_pending_changes = True

def update_program(self, ...):
    # ... existing code ...
    self.has_pending_changes = True
```

3. **Google Apps Script (optional)**
Create script in Google Sheets to auto-import newest file:
```javascript
function autoImportNewestExcel() {
  var folder = DriveApp.getFolderById('YOUR_FOLDER_ID');
  var files = folder.getFilesByType('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');

  // Find newest file
  var newestFile = null;
  var newestDate = new Date(0);

  while (files.hasNext()) {
    var file = files.next();
    if (file.getLastUpdated() > newestDate) {
      newestDate = file.getLastUpdated();
      newestFile = file;
    }
  }

  // Import to sheet
  if (newestFile) {
    var blob = newestFile.getBlob();
    // ... import logic ...
  }
}

// Run every 10 minutes
function createTimeDrivenTriggers() {
  ScriptApp.newTrigger('autoImportNewestExcel')
    .timeBased()
    .everyMinutes(10)
    .create();
}
```

#### Benefits:
- ✅ Automatic exports
- ✅ No manual button clicking
- ✅ Configurable frequency
- ✅ Backup files in Google Drive

#### Drawbacks:
- ⚠️ Google Sheet not instantly updated
- ⚠️ Creates many export files
- ⚠️ Still requires import step (unless using Apps Script)

#### Implementation difficulty: ⭐⭐ (Easy)
#### Cost: Free

---

## Recommended Implementation Plan

### Phase 1: Immediate Improvements (This Week)

**Goal**: Make current setup safer and more convenient

1. **Add database file monitor** ⭐
   - Detect when database changes externally
   - Show notification to refresh
   - Auto-refresh option

2. **Add one-click Google Sheets update** ⭐
   - Simplify export process
   - Export + upload in one step
   - Use Google Sheets API

3. **Add safety warnings** ⭐
   - Warn when database might be in use
   - Show last modified by/time
   - Create automatic backups before writes

**Time estimate**: 4-8 hours development
**Difficulty**: Easy to Moderate
**Cost**: Free

---

### Phase 2: Google Sheets Automation (Next 2 Weeks)

**Goal**: Eliminate manual Google Sheets updates

1. **Set up Google Sheets API** ⭐⭐
   - Create Google Cloud project
   - Configure credentials
   - Test connection

2. **Implement auto-sync** ⭐⭐⭐
   - Add GoogleSheetsSync class
   - Integrate with add/edit/delete operations
   - Add batching for performance
   - Add settings dialog

3. **Add status monitoring** ⭐
   - Show last sync time
   - Show sync status (syncing/success/error)
   - Add manual sync button

**Time estimate**: 8-16 hours development
**Difficulty**: Moderate
**Cost**: Free

---

### Phase 3: Database Upgrade (Next Month)

**Goal**: Proper multi-computer support

**Option A: Self-Hosted MySQL**
1. Set up MySQL on one computer (acts as server)
2. Modify app to connect to MySQL
3. Update all computers to use central database
4. Keep NC files in Google Drive

**Option B: Cloud Database**
1. Sign up for PlanetScale or Supabase (free tier)
2. Create database
3. Import SQLite data
4. Update app connection settings
5. Deploy to all computers

**Time estimate**: 16-40 hours development + testing
**Difficulty**: Moderate to Hard
**Cost**: Free (self-hosted) or $0-20/month (cloud)

---

## File Watching & Auto-Refresh Implementation

### Simple File Monitor (Python watchdog)

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class DatabaseWatcher(FileSystemEventHandler):
    def __init__(self, db_path, callback):
        self.db_path = db_path
        self.callback = callback
        self.last_modified = os.path.getmtime(db_path)

    def on_modified(self, event):
        if event.src_path == self.db_path:
            current_modified = os.path.getmtime(self.db_path)

            # Check if actually changed (avoid duplicate events)
            if current_modified != self.last_modified:
                self.last_modified = current_modified

                # Wait a bit for file to finish writing
                time.sleep(0.5)

                # Notify app
                self.callback()

# Usage in main app:
def on_database_changed(self):
    """Called when external database change detected"""
    response = messagebox.askyesno(
        "Database Updated",
        "The database was modified by another computer.\n\n"
        "Do you want to refresh and see the latest changes?",
        icon='info'
    )

    if response:
        self.refresh_results()
        messagebox.showinfo("Refreshed", "Database reloaded with latest changes.")

# Start file watcher
observer = Observer()
handler = DatabaseWatcher(self.db_path, self.on_database_changed)
observer.schedule(handler, path=os.path.dirname(self.db_path), recursive=False)
observer.start()
```

**Install watchdog:**
```bash
pip install watchdog
```

---

## Google Sheets API Setup Guide

### Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click "Create Project"
3. Name it "GCode Database Manager"
4. Click "Create"

### Step 2: Enable Google Sheets API

1. In Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click on it, then click "Enable"

### Step 3: Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Name it "gcode-sheets-sync"
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

### Step 4: Create JSON Key

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" → "Create New Key"
4. Choose "JSON"
5. Click "Create"
6. **Save the JSON file** - this is your credentials file!

### Step 5: Share Google Sheet with Service Account

1. Open the JSON credentials file
2. Find the `client_email` field (looks like: `gcode-sheets-sync@your-project.iam.gserviceaccount.com`)
3. Copy this email
4. Open your Google Sheet
5. Click "Share"
6. Paste the service account email
7. Give it "Editor" permission
8. Click "Send"

### Step 6: Get Spreadsheet ID

Your Google Sheets URL looks like:
```
https://docs.google.com/spreadsheets/d/1abc123XYZ456/edit
                                      ↑ This is the ID
```

Copy the spreadsheet ID (the part between `/d/` and `/edit`)

### Step 7: Configure in App

Save these values in application settings:
- **Credentials file path**: Where you saved the JSON file
- **Spreadsheet ID**: From step 6

---

## Configuration Options to Add

### Settings Dialog - New Section: "Sync & Export"

```
┌────────────────────────────────────────────────┐
│ Sync & Export Settings                         │
├────────────────────────────────────────────────┤
│                                                 │
│ Database Sync:                                  │
│   [✓] Monitor for external changes              │
│   [✓] Auto-refresh when changes detected        │
│   [ ] Warn before refreshing                    │
│                                                 │
│ Google Sheets Integration:                      │
│   [✓] Enable automatic sync                     │
│   Credentials file: [Browse...]                 │
│   Spreadsheet ID: [___________________________] │
│   Sync mode: ● Real-time  ○ Batched (5 min)   │
│   [✓] Update on add/edit/delete                │
│                                                 │
│ Backup:                                         │
│   [✓] Auto-backup before database writes        │
│   Keep last [5] backups                         │
│                                                 │
│         [Test Connection]  [Save]  [Cancel]     │
└────────────────────────────────────────────────┘
```

---

## Migration Path for Existing Users

### If Moving to Centralized Database:

1. **Backup current database**
   ```bash
   cp gcode_database.db gcode_database_backup_$(date +%Y%m%d).db
   ```

2. **Export SQLite to SQL**
   ```bash
   sqlite3 gcode_database.db .dump > database_export.sql
   ```

3. **Create MySQL/PostgreSQL database**
   ```sql
   CREATE DATABASE gcode_manager;
   ```

4. **Import data** (after converting SQL syntax)

5. **Update app connection settings**

6. **Test on one computer first**

7. **Roll out to other computers**

---

## Troubleshooting

### Issue: Database conflicts in Google Drive

**Solution:**
- Only open app on one computer at a time
- Wait for Google Drive sync before switching
- Use database locking indicator (Phase 1)
- Better: Upgrade to centralized database (Phase 3)

### Issue: Google Sheets API authentication fails

**Solutions:**
- Verify JSON credentials file is valid
- Check service account has Editor permission on sheet
- Ensure Google Sheets API is enabled in Cloud Console
- Check internet connection
- Verify spreadsheet ID is correct

### Issue: Slow Google Sheets updates

**Solutions:**
- Use batched mode instead of real-time
- Update sheet every 5-10 minutes instead of immediately
- Use bulk update API calls instead of individual rows
- Limit to active programs only (filter unused/old programs)

### Issue: Two computers editing same program

**Solution:**
- Add "last modified by" tracking
- Show warning if program edited recently by another user
- Add optimistic locking (version numbers)
- Better: Use centralized database with proper locking

---

## Security Considerations

### Google Sheets Service Account

✅ **Do:**
- Keep JSON credentials file secure
- Don't commit to Git
- Store in secure location (not in repository folder)
- Restrict permissions to specific spreadsheet only

❌ **Don't:**
- Share credentials file publicly
- Store in cloud-synced folder
- Give service account owner/admin permissions
- Use same credentials across multiple apps

### Database Access

✅ **Do:**
- Regular backups
- Test restores periodically
- Use read-only mode when browsing
- Lock database during critical operations

❌ **Don't:**
- Allow simultaneous writes from multiple computers (current SQLite setup)
- Skip backups
- Ignore corruption warnings

---

## Cost Summary

### Current Setup (Google Drive + SQLite)
- **Cost**: Free
- **Limitation**: No concurrent access, manual Google Sheets updates

### Recommended Improvements

| Feature | Cost | Difficulty |
|---------|------|------------|
| File monitoring & auto-refresh | Free | Easy |
| Google Sheets API integration | Free | Moderate |
| Watchdog library | Free | Easy |
| gspread library | Free | Easy |

### Optional Upgrades

| Solution | Setup Cost | Monthly Cost | Difficulty |
|----------|------------|--------------|------------|
| Self-hosted MySQL | Free | Free | Hard |
| PlanetScale (cloud MySQL) | Free | Free tier | Moderate |
| Supabase (cloud PostgreSQL) | Free | Free tier | Moderate |
| Google Cloud SQL | Free | $10-30/mo | Moderate |
| AWS RDS | Free | $15-50/mo | Moderate |

---

## Next Steps

### Immediate Actions (You)

1. **Decide on approach:**
   - Quick fixes only? (Phase 1)
   - Add Google Sheets automation? (Phase 2)
   - Full database upgrade? (Phase 3)

2. **Answer questions:**
   - How many computers access database?
   - How often do multiple people work simultaneously?
   - Budget for cloud database (if any)?
   - Comfort level with setting up MySQL?

3. **Test current setup:**
   - Do you see database conflicts?
   - How often do you update Google Sheets?
   - Is manual process acceptable or major pain point?

### Implementation Order (Me)

**If you want quick improvements:**
1. Add file monitoring
2. Add Google Sheets API integration
3. Test on one computer
4. Deploy to all computers

**If you want proper solution:**
1. Set up cloud database (PlanetScale/Supabase)
2. Migrate SQLite data
3. Update app connection code
4. Add Google Sheets API
5. Test thoroughly
6. Deploy to all computers

---

## Questions to Answer

Before implementing, decide:

1. **How many computers/users?**
   - 2 computers, same user → Keep current setup with monitoring
   - 3+ computers or multiple users → Need centralized database

2. **How important is real-time?**
   - Can wait 5-10 minutes → Batched updates OK
   - Need instant updates → Real-time sync required

3. **Budget?**
   - $0 → Self-hosted MySQL or free tier cloud DB
   - $10-30/month → Professional cloud database

4. **Technical comfort?**
   - Want simple → Phase 1 + 2 only
   - OK with more complex → Phase 3 (centralized DB)

5. **Google Sheets usage?**
   - Critical for daily work → Automate (Phase 2)
   - Occasional reference → Manual export OK

---

## Conclusion

### Current State:
- ❌ SQLite in Google Drive = corruption risk
- ❌ Manual Google Sheets updates = time waste
- ❌ No auto-refresh = stale data

### Recommended Path:
1. **Week 1**: Add file monitoring + safety warnings
2. **Week 2-3**: Add Google Sheets API automation
3. **Month 2**: Evaluate if centralized database needed

### Expected Outcome:
- ✅ Safer multi-computer access
- ✅ Automatic Google Sheets updates
- ✅ No more manual export/import
- ✅ Real-time or near-real-time sync
- ✅ Better user experience

**Total implementation time**: 20-40 hours
**Total cost**: Free (using free tiers)
**Risk level**: Low to Moderate

---

Would you like me to implement any of these solutions? Start with Phase 1 (quick fixes) or jump to Phase 2 (Google Sheets automation)?
