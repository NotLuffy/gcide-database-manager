# Google Drive Setup — G-Code Database Manager

Keep your database and repository on Google Drive so data persists across
GitHub re-downloads and is accessible from multiple machines.

---

## Step 1 — Install Google Drive Desktop

Download and install Google Drive for Desktop:
https://www.google.com/drive/download/

Sign in and let it sync. Your Drive will appear as a local folder, typically:
- Windows: `G:\My Drive\` or `C:\Users\<name>\Google Drive\`

---

## Step 2 — Move Database and Repository to Google Drive

1. Close the G-Code Database Manager app completely.
2. Create a folder on Google Drive, e.g.:
   `G:\My Drive\GCode Manager\`
3. Copy (or move) these two items into that folder:
   - `gcode_database.db`  — your main database file
   - `repository\`        — the folder containing all NC files
4. Wait for Google Drive to finish syncing both.

---

## Step 3 — Configure the App to Use Google Drive Paths

1. Open the G-Code Database Manager.
2. Go to the **Repository** tab.
3. Click **Configure Paths** (bottom button row).
4. Set:
   - **Database file**: `G:\My Drive\GCode Manager\gcode_database.db`
   - **Repository folder**: `G:\My Drive\GCode Manager\repository`
5. Click **Save**.
6. Restart the app — it will now use the Google Drive paths.

---

## Step 4 — After Downloading a New Version from GitHub

When you re-download the app from GitHub, your data stays safe:

1. Download and extract the new version.
2. Copy `gcode_manager_config.json` from the old folder to the new folder.
   (This file remembers your configured paths.)
3. Open the app — it reads the config and reconnects to your Drive data automatically.
   No re-importing needed.

Alternatively, if you don't copy the config file:
1. Open the new app version.
2. Go to Repository tab → Configure Paths.
3. Re-enter the Google Drive paths and save.
4. Restart.

---

## Troubleshooting

**App says "Database not found"**
- Google Drive may still be syncing. Wait for the Drive icon to show sync complete.
- Verify the path in Configure Paths matches exactly where the `.db` file is.

**Files show in database but can't be opened**
- Use **Rebase Paths** (Repository tab) after moving to a new machine.
  This updates all stored file paths to the new Drive location.

**"Database is locked" error**
- Another instance of the app is open, or Drive is mid-sync.
- Close all app windows and wait for Drive sync to finish.

**Changes on one machine don't appear on another**
- Google Drive syncs on a delay. Wait ~30 seconds after saving on one machine
  before opening on another.

---

## Notes

- The `repository/` folder should stay inside Google Drive — never reference files
  on a local path that other machines can't see.
- Backups (`backups/`) and versions (`versions/`) folders are created automatically
  next to the repository folder on Drive.
- The app config file (`gcode_manager_config.json`) stays local to each machine —
  copy it when setting up a new machine to skip re-configuration.
