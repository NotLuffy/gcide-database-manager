# Future Improvements - TODO List

## Document Purpose
This document contains questions and proposed improvements for future implementation. These are saved for later consideration and are NOT currently being worked on.

---

## 1. Version & Archive System Improvements

### Status: 📋 Saved for Later

### Current Situation
- Three competing systems: `archive/` (7,915 files), `versions/` (2 files), `revised_repository/` (empty)
- Archive system actively used but lacks metadata
- No version comparison tools
- No retention policy

### Questions to Answer Before Implementation

#### Q1: How long to keep archives?
- **Options:**
  - Forever? (current behavior)
  - 1 year?
  - 90 days?
  - Always keep v1.0 (original)?
- **Impact:** Storage space, backup size, organization

#### Q2: Compression strategy?
- **Options:**
  - Compress old versions?
  - When to compress? (>90 days? >1 year?)
  - Which format? (zip, 7z, tar.gz)
- **Impact:** Storage savings vs access speed

#### Q3: What to track in metadata?
- **Options:**
  - User who made change?
  - Change reason/summary?
  - Dimensions before/after?
  - Validation status?
  - Tool changes?
  - Feed/speed changes?
- **Impact:** Database size, usefulness for troubleshooting

#### Q4: Backup strategy for archives?
- **Options:**
  - Include all archives in backup?
  - Only recent archives (30-90 days)?
  - Separate archive backup?
  - Exclude from cloud backups?
- **Impact:** Backup size, time, cloud storage costs

#### Q5: Migration approach for existing 7,915 files?
- **Options:**
  - Migrate all existing files to new system?
  - Only track new archives going forward?
  - Hybrid: metadata for new, keep old as-is?
  - Generate metadata for existing files where possible?
- **Impact:** Migration time, data completeness

### Proposed Features

#### High Priority Features
1. **Version History Viewer**
   - Right-click menu: "View Version History"
   - Shows all versions with dates
   - Buttons: Restore, Compare, View File
   - Estimated time: 8-12 hours

2. **Version Comparison Tool**
   - Compare two versions side-by-side
   - Show dimensional changes
   - Show tool changes
   - Highlight G-code differences
   - Estimated time: 12-16 hours

3. **Metadata Tracking for New Archives**
   - JSON file per archived version
   - Track: user, timestamp, change summary, dimensions
   - Auto-detect changes when possible
   - Estimated time: 6-8 hours

#### Medium Priority Features
4. **Archive Cleanup Tool**
   - Maintenance menu option
   - Options: Delete old, compress old, keep last N versions
   - Keep v1.0 always
   - Preview before deletion
   - Estimated time: 6-8 hours

5. **Automated Change Detection**
   - Detect tool home position changes
   - Detect coolant sequence changes
   - Detect dimensional changes
   - Auto-generate change summary
   - Estimated time: 8-10 hours

#### Low Priority Features
6. **Version Tags & Notes**
   - Tag versions: STABLE, PRODUCTION, TESTING, etc.
   - Add notes to versions
   - Search by tag
   - Estimated time: 4-6 hours

### Recommended Implementation Approach

**Phase 1: Add Metadata to Current System** (2-3 days)
1. Create metadata tracking for NEW archives
2. Don't touch existing 7,915 files yet
3. Add version history viewer UI
4. Add comparison tool

**Phase 2: Consolidate Systems** (1 week)
1. Migrate `archive/` → `versions/` structure
2. Generate metadata for existing files (where possible)
3. Deprecate `archive/` folder
4. Update backup system

**Phase 3: Optimize Storage** (3-5 days)
1. Implement retention policies
2. Add compression for old versions
3. Create archive cleanup tools

### Reference Documents
- Full analysis: [VERSION_SYSTEM_ANALYSIS.md](VERSION_SYSTEM_ANALYSIS.md)
- Backup system: [BACKUP_SYSTEM_GUIDE.md](BACKUP_SYSTEM_GUIDE.md)

---

## 2. Multi-Computer Sync & Google Sheets Automation

### Status: 📋 Saved for Later

### Current Situation
- Using Google Drive for file storage (works well)
- SQLite database in Google Drive (⚠️ corruption risk with concurrent access)
- Manual Google Sheets export/import (time-consuming)

### Questions to Answer Before Implementation

#### Q1: How many computers/users?
- **Current:** ? (need to confirm)
- **Options:**
  - 2 computers, same user → Keep SQLite with monitoring
  - 3+ computers → Need centralized database
  - Multiple users → Definitely need centralized database
- **Impact:** Choice of database solution

#### Q2: How important is real-time sync?
- **Options:**
  - Can wait 5-10 minutes → Batched updates OK
  - Need instant updates → Real-time sync required
  - Only care about avoiding conflicts → Monitoring + warnings OK
- **Impact:** Complexity, performance, user experience

#### Q3: Budget for database hosting?
- **Options:**
  - $0 → Self-hosted MySQL or free tier cloud DB
  - $10-30/month → Professional cloud database
  - $50+/month → Enterprise solution
- **Impact:** Reliability, features, support

#### Q4: Technical comfort level?
- **Options:**
  - Want simple → Phase 1 + 2 only (file monitoring + Google Sheets API)
  - OK with moderate complexity → Cloud database (PlanetScale/Supabase)
  - Comfortable with advanced → Self-hosted MySQL/PostgreSQL
- **Impact:** Implementation choice, maintenance burden

#### Q5: Google Sheets usage pattern?
- **Options:**
  - Critical for daily work → Automate (high priority)
  - Weekly reference → Manual export acceptable
  - Occasional use → Low priority
- **Impact:** Implementation priority

#### Q6: How often are database conflicts happening now?
- **Current experience:** ? (need to confirm)
- **Options:**
  - Never/rarely → Low priority, add monitoring only
  - Occasionally → Medium priority, add warnings
  - Frequently → High priority, need centralized DB
- **Impact:** Urgency of solution

### Proposed Solutions

#### Phase 1: Immediate Improvements (Free, Easy)
**Goal:** Make current setup safer and more convenient

1. **Add Database File Monitor**
   - Detect when database changes externally
   - Show notification to refresh
   - Auto-refresh option
   - Estimated time: 4-6 hours

2. **Add One-Click Google Sheets Update**
   - Simplify export process
   - Export + upload in one step
   - Use Google Sheets API
   - Estimated time: 8-12 hours

3. **Add Safety Warnings**
   - Warn when database might be in use
   - Show last modified by/time
   - Create automatic backups before writes
   - Estimated time: 4-6 hours

**Libraries needed:**
```bash
pip install watchdog  # File monitoring
pip install gspread oauth2client  # Google Sheets API
```

#### Phase 2: Google Sheets Automation (Free, Moderate)
**Goal:** Eliminate manual Google Sheets updates

1. **Set up Google Sheets API**
   - Create Google Cloud project
   - Configure credentials
   - Test connection
   - Estimated time: 2-3 hours

2. **Implement Auto-Sync**
   - Add GoogleSheetsSync class
   - Integrate with add/edit/delete operations
   - Add batching for performance
   - Add settings dialog
   - Estimated time: 12-16 hours

3. **Add Status Monitoring**
   - Show last sync time
   - Show sync status (syncing/success/error)
   - Add manual sync button
   - Estimated time: 3-4 hours

#### Phase 3: Database Upgrade (Free-$30/month, Hard)
**Goal:** Proper multi-computer support

**Option A: Self-Hosted MySQL** (Free)
- Set up MySQL on one computer
- Modify app to connect to MySQL
- Keep NC files in Google Drive
- Estimated time: 20-30 hours

**Option B: Cloud Database** ($0-30/month)
- Sign up for PlanetScale/Supabase (free tier)
- Create database and import data
- Update app connection settings
- Estimated time: 16-24 hours

### Detailed Implementation Steps

#### Google Sheets API Setup (Step-by-step)
1. Create Google Cloud project
2. Enable Google Sheets API
3. Create Service Account
4. Create JSON key
5. Share Google Sheet with service account email
6. Get spreadsheet ID
7. Configure in app settings

*Full guide in: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md)*

#### Code Integration Points
- `add_program()` → Trigger sheet update
- `update_program()` → Trigger sheet update
- `delete_program()` → Trigger sheet update
- Add GoogleSheetsSync class (new file)
- Add settings dialog for credentials
- Add status indicator in UI

### Reference Documents
- Full analysis: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md)

---

## 3. Additional Features (From Integration Analysis)

### Status: 📋 Future Enhancements

### Suggested Improvements

1. **Keyboard Shortcuts for Clipboard**
   - Add Ctrl+C to copy program number
   - Add Ctrl+Shift+C to copy full details
   - Estimated time: 2-3 hours

2. **Status Bar for Confirmations**
   - Show copy confirmations in status bar
   - Show sync status
   - Show last operation result
   - Estimated time: 3-4 hours

3. **Expand Progress Tracking**
   - Add to file imports
   - Add to export operations
   - Add to repository scanning
   - Add to batch validation
   - Estimated time: 6-8 hours

4. **Fuzzy Search Enhancements**
   - Add fuzzy search to program number field
   - Add "Did you mean...?" suggestions
   - Add search history
   - Estimated time: 4-6 hours

---

## Priority Matrix

### High Priority (When Ready to Implement)
1. ⭐ Google Sheets Automation (Phase 1 + 2)
   - Most requested
   - Clear value proposition
   - Free implementation

2. ⭐ Version History Viewer
   - High value for troubleshooting
   - Moderate complexity
   - Uses existing archive data

### Medium Priority
3. Database File Monitoring
   - Safety improvement
   - Prevents data loss
   - Easy to implement

4. Version Comparison Tool
   - Useful but not critical
   - Moderate complexity
   - Can be added after history viewer

5. Archive Cleanup/Retention
   - Space savings
   - Organizational benefit
   - Easy to implement

### Low Priority
6. Centralized Database (Phase 3)
   - Only if multi-user issues arise
   - Significant complexity
   - Consider after Phase 1+2

7. Version Tags & Notes
   - Nice to have
   - Low complexity
   - Can wait

---

## Decision Log

### Decisions Needed Before Implementation

For each major feature area, need to decide:

**Version System:**
- [ ] Retention policy duration
- [ ] Metadata fields to track
- [ ] Compression strategy
- [ ] Migration approach for 7,915 existing files

**Multi-Computer Sync:**
- [ ] Number of concurrent users
- [ ] Real-time vs batched updates
- [ ] Budget for cloud database (if any)
- [ ] Technical comfort level
- [ ] Google Sheets update frequency needed

**Archive System:**
- [ ] Keep all versions or implement cleanup?
- [ ] Backup all archives or just recent?
- [ ] Consolidate to single version system?

### Answers Template

Copy this when ready to decide:

```
VERSION SYSTEM DECISIONS:
1. Retention: [ Forever / 1 year / 90 days / Keep v1.0 only ]
2. Metadata: [ Full / Basic / Minimal ]
3. Compression: [ Yes after 1 year / No / Yes after 90 days ]
4. Migration: [ All files / New only / Hybrid ]

MULTI-COMPUTER DECISIONS:
1. Users: [ 1 user/2 computers / 2-3 users / 4+ users ]
2. Sync: [ Real-time / 5-10 min batched / Manual ]
3. Budget: [ $0 / $10-30/mo / $50+/mo ]
4. Complexity: [ Simple only / Moderate OK / Advanced OK ]
5. Google Sheets: [ Critical / Weekly / Occasional ]

IMPLEMENTATION PRIORITY:
1. First: [ Google Sheets automation / Version viewer / Multi-computer fix ]
2. Second: [ ... ]
3. Third: [ ... ]
```

---

## Time Estimates Summary

### Quick Wins (< 1 day each)
- Database file monitoring: 4-6 hours
- Safety warnings: 4-6 hours
- Status bar: 3-4 hours
- Keyboard shortcuts: 2-3 hours

### Medium Projects (2-4 days each)
- Version history viewer: 8-12 hours
- Google Sheets API setup + basic sync: 10-15 hours
- Archive metadata tracking: 6-8 hours
- Version comparison tool: 12-16 hours

### Large Projects (1-2 weeks each)
- Full Google Sheets automation: 20-30 hours
- Archive system consolidation: 30-40 hours
- Centralized database migration: 40-60 hours

---

## Notes

- All estimates assume existing codebase knowledge
- Testing time not included (add 30-50%)
- Documentation time not included (add 20%)
- User training/onboarding not included

---

## When to Revisit This Document

Review this document when:
- Current projects are completed
- User reports issues with current systems
- Storage space becomes a concern
- Multi-computer conflicts increase
- Manual processes become too time-consuming
- Ready to invest in improvements

---

## Quick Reference Links

| Document | Purpose |
|----------|---------|
| [VERSION_SYSTEM_ANALYSIS.md](VERSION_SYSTEM_ANALYSIS.md) | Full version system analysis |
| [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) | Database sync & Google Sheets automation |
| [BACKUP_SYSTEM_GUIDE.md](BACKUP_SYSTEM_GUIDE.md) | Backup system documentation |
| [FUZZY_SEARCH_GUIDE.md](FUZZY_SEARCH_GUIDE.md) | Fuzzy search user guide |
| [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) | Recently completed features |

---

**Last Updated:** 2026-02-03
**Status:** 📋 Saved for future reference
**Action Required:** Review questions and make decisions before implementation
