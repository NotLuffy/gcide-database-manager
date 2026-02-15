# G-Code Database Manager - Development Roadmap

## Document Purpose
This roadmap outlines all planned improvements, their priorities, timelines, and implementation order. Use this document to track what's next and make decisions about development direction.

---

## Quick Reference

### Current Status
- ✅ **Recently Completed**: Fuzzy search, clipboard integration, progress tracking
- 🔄 **In Planning**: File scanner, editor, multi-computer sync, version improvements
- 📋 **Awaiting Decisions**: See "Decision Points" section below

### Timeline Overview
- **Short-term** (1-2 weeks): Quick wins and high-value features
- **Medium-term** (1-2 months): Moderate complexity features
- **Long-term** (3+ months): Major architectural improvements

---

## Development Phases

### Phase 1: Quick Wins & Safety Features (1-2 Weeks)

**Goal**: Improve safety and add immediate-value features with minimal effort

#### 1.1 Pre-Import File Scanner ⭐ RECOMMENDED START
- **Priority**: HIGH
- **Effort**: 12 hours
- **Value**: HIGH
- **Dependencies**: None
- **Status**: 📋 Planned

**What it does:**
- Scan any G-code file before importing
- Show warnings, errors, and dimensions
- Decide whether to import or fix first
- Prevents importing problematic files

**Implementation tasks:**
- [ ] Create `scan_file_for_issues()` method (4h)
- [ ] Create `FileScannerWindow` UI (4h)
- [ ] Add menu integration (1h)
- [ ] Testing and refinement (3h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Feature 1

---

#### 1.2 Database File Monitor (Safety)
- **Priority**: HIGH
- **Effort**: 6 hours
- **Value**: HIGH
- **Dependencies**: None
- **Status**: 📋 Planned

**What it does:**
- Detect when database changes externally (another computer)
- Show notification to refresh
- Prevent data loss from stale data
- Auto-refresh option

**Implementation tasks:**
- [ ] Install watchdog library (5min)
- [ ] Create `DatabaseWatcher` class (3h)
- [ ] Add notification system (2h)
- [ ] Add auto-refresh toggle (1h)

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Phase 1

---

#### 1.3 Safety Warnings Before Writes
- **Priority**: HIGH
- **Effort**: 4 hours
- **Value**: MEDIUM
- **Dependencies**: None
- **Status**: 📋 Planned

**What it does:**
- Warn when database might be in use by another computer
- Show last modified time/user
- Create automatic backup before writes
- Prevent conflicts

**Implementation tasks:**
- [ ] Add last-modified tracking (2h)
- [ ] Add pre-write backup (1h)
- [ ] Add conflict warning dialog (1h)

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Phase 1

---

#### 1.4 Duplicate with Automatic Scan
- **Priority**: MEDIUM
- **Effort**: 6 hours
- **Value**: MEDIUM
- **Dependencies**: Pre-Import Scanner (1.1)
- **Status**: 📋 Planned

**What it does:**
- Scan source file when duplicating program
- Show warnings before creating duplicate
- Option to auto-fix warnings in new file
- Option to open editor after creation

**Implementation tasks:**
- [ ] Enhance duplicate dialog (2h)
- [ ] Add warning display (2h)
- [ ] Add auto-fix capability (2h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Feature 3

---

**Phase 1 Total Time**: 28 hours (1-2 weeks part-time)
**Phase 1 Value**: Immediate safety improvements + useful scanning features

---

### Phase 2: Google Sheets Automation (2-4 Weeks)

**Goal**: Eliminate manual Google Sheets export/import process

#### 2.1 Google Sheets API Setup
- **Priority**: HIGH (if using Google Sheets regularly)
- **Effort**: 3 hours
- **Value**: HIGH
- **Dependencies**: None
- **Status**: 📋 Planned

**What it does:**
- Set up Google Cloud project
- Configure Google Sheets API
- Create service account credentials
- Test connection

**Implementation tasks:**
- [ ] Create Google Cloud project (30min)
- [ ] Enable Google Sheets API (15min)
- [ ] Create service account + JSON key (30min)
- [ ] Share sheet with service account (15min)
- [ ] Test connection in Python (1h)

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Google Sheets API Setup Guide

---

#### 2.2 Basic Google Sheets Sync
- **Priority**: HIGH
- **Effort**: 12 hours
- **Value**: HIGH
- **Dependencies**: Google Sheets API Setup (2.1)
- **Status**: 📋 Planned

**What it does:**
- One-click export to Google Sheets
- Direct API upload (no manual import)
- Update existing sheet instead of replace
- Much faster than current process

**Implementation tasks:**
- [ ] Install gspread library (5min)
- [ ] Create `GoogleSheetsSync` class (4h)
- [ ] Add one-click export button (2h)
- [ ] Test with actual sheets (2h)
- [ ] Error handling and retry logic (2h)
- [ ] Add progress indicator (1h)
- [ ] Documentation (1h)

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Phase 2

---

#### 2.3 Automatic Google Sheets Updates
- **Priority**: MEDIUM
- **Effort**: 10 hours
- **Value**: HIGH
- **Dependencies**: Basic Google Sheets Sync (2.2)
- **Status**: 📋 Planned

**What it does:**
- Automatically update Google Sheets when programs added/edited/deleted
- Batched updates (every 5-10 minutes) for performance
- Status indicator showing sync status
- Manual sync button as backup

**Implementation tasks:**
- [ ] Add update hooks to add/edit/delete methods (3h)
- [ ] Implement batching system (3h)
- [ ] Add settings dialog for credentials (2h)
- [ ] Add sync status indicator (1h)
- [ ] Testing and refinement (1h)

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Phase 2

---

#### 2.4 Settings & Configuration
- **Priority**: MEDIUM
- **Effort**: 4 hours
- **Value**: MEDIUM
- **Dependencies**: Automatic Google Sheets Updates (2.3)
- **Status**: 📋 Planned

**What it does:**
- Settings dialog for Google Sheets configuration
- Enable/disable automatic sync
- Choose sync mode (real-time vs batched)
- Test connection button

**Implementation tasks:**
- [ ] Create settings dialog UI (2h)
- [ ] Add enable/disable toggle (1h)
- [ ] Add test connection feature (1h)

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Configuration Options

---

**Phase 2 Total Time**: 29 hours (2-4 weeks part-time)
**Phase 2 Value**: Eliminates manual Google Sheets updates completely

---

### Phase 3: Version History & Archive Improvements (3-4 Weeks)

**Goal**: Better version tracking, comparison, and cleanup

⚠️ **REQUIRES DECISIONS**: See "Decision Points" section before starting

#### 3.1 Version History Viewer
- **Priority**: MEDIUM
- **Effort**: 12 hours
- **Value**: HIGH
- **Dependencies**: None
- **Status**: 📋 Planned (awaiting decisions)

**What it does:**
- Right-click menu: "View Version History"
- Shows all versions with dates and metadata
- Buttons: Restore, Compare, View File
- See complete timeline of program changes

**Implementation tasks:**
- [ ] Create version history window (4h)
- [ ] Add database queries for versions (2h)
- [ ] Add restore functionality (2h)
- [ ] Add view file functionality (1h)
- [ ] Testing (3h)

**Reference**: [FUTURE_IMPROVEMENTS_TODO.md](FUTURE_IMPROVEMENTS_TODO.md) - Feature 1

---

#### 3.2 Version Comparison Tool
- **Priority**: MEDIUM
- **Effort**: 16 hours
- **Value**: MEDIUM
- **Dependencies**: Version History Viewer (3.1)
- **Status**: 📋 Planned (awaiting decisions)

**What it does:**
- Compare two versions side-by-side
- Show dimensional changes highlighted
- Show tool changes
- Highlight G-code differences
- Useful for troubleshooting

**Implementation tasks:**
- [ ] Create comparison window (6h)
- [ ] Implement diff algorithm (4h)
- [ ] Add dimension comparison (2h)
- [ ] Add tool change detection (2h)
- [ ] Testing (2h)

**Reference**: [FUTURE_IMPROVEMENTS_TODO.md](FUTURE_IMPROVEMENTS_TODO.md) - Feature 2

---

#### 3.3 Archive Metadata Tracking
- **Priority**: MEDIUM
- **Effort**: 8 hours
- **Value**: MEDIUM
- **Dependencies**: None
- **Status**: 📋 Planned (awaiting decisions)

**What it does:**
- Track metadata for each archived version
- Who made the change
- Why (change summary)
- What changed (dimensions, tools, etc.)
- Auto-detect changes when possible

**Implementation tasks:**
- [ ] Design metadata JSON format (1h)
- [ ] Add metadata collection on archive (3h)
- [ ] Add auto-detection of changes (3h)
- [ ] Testing (1h)

**Reference**: [FUTURE_IMPROVEMENTS_TODO.md](FUTURE_IMPROVEMENTS_TODO.md) - Feature 3

---

#### 3.4 Archive Cleanup & Retention
- **Priority**: LOW
- **Effort**: 8 hours
- **Value**: MEDIUM
- **Dependencies**: None (but benefits from 3.3)
- **Status**: 📋 Planned (awaiting decisions)

**What it does:**
- Maintenance tool for managing archives
- Delete old versions (keep last N or >X days)
- Compress old versions to save space
- Always keep v1.0 (original)
- Preview before deletion

**Implementation tasks:**
- [ ] Create cleanup tool UI (3h)
- [ ] Add deletion logic with safety checks (2h)
- [ ] Add compression option (2h)
- [ ] Testing (1h)

**Reference**: [FUTURE_IMPROVEMENTS_TODO.md](FUTURE_IMPROVEMENTS_TODO.md) - Feature 4

---

#### 3.5 Consolidate Version Systems
- **Priority**: LOW
- **Effort**: 16 hours
- **Value**: MEDIUM
- **Dependencies**: 3.1, 3.2, 3.3
- **Status**: 📋 Planned (awaiting decisions)

**What it does:**
- Consolidate `archive/`, `versions/`, `revised_repository/` into one system
- Migrate 7,915 existing archived files
- Generate metadata where possible
- Cleaner, more organized structure

**Implementation tasks:**
- [ ] Design unified structure (2h)
- [ ] Create migration script (6h)
- [ ] Test migration on subset (2h)
- [ ] Run full migration (2h)
- [ ] Update all code references (2h)
- [ ] Testing (2h)

**Reference**: [VERSION_SYSTEM_ANALYSIS.md](VERSION_SYSTEM_ANALYSIS.md)

---

**Phase 3 Total Time**: 60 hours (3-4 weeks part-time)
**Phase 3 Value**: Better organization and troubleshooting capabilities

---

### Phase 4: Built-In G-Code Editor (4-6 Weeks)

**Goal**: Edit G-code files directly in application with real-time validation

⚠️ **OPTIONAL**: This is high-effort. Assess user demand before committing.

#### 4.1 Basic Editor UI
- **Priority**: LOW (until user demand confirmed)
- **Effort**: 10 hours
- **Value**: HIGH (once built)
- **Dependencies**: Pre-Import Scanner (1.1)
- **Status**: 📋 Planned (optional)

**What it does:**
- Open G-code files in built-in editor
- Line numbers
- Basic text editing features
- Save, save-as, revert
- Undo/redo

**Implementation tasks:**
- [ ] Create editor window (4h)
- [ ] Add line numbers (2h)
- [ ] Add save/load functionality (2h)
- [ ] Add undo/redo (1h)
- [ ] Testing (1h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Feature 2

---

#### 4.2 Syntax Highlighting
- **Priority**: LOW
- **Effort**: 6 hours
- **Value**: MEDIUM
- **Dependencies**: Basic Editor (4.1)
- **Status**: 📋 Planned (optional)

**What it does:**
- Color code G-codes, M-codes, coordinates
- Highlight comments
- Highlight program numbers
- Easier to read and understand

**Implementation tasks:**
- [ ] Define syntax patterns (1h)
- [ ] Implement highlighting engine (3h)
- [ ] Test with various files (1h)
- [ ] Performance optimization (1h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Feature 2

---

#### 4.3 Real-Time Validation
- **Priority**: LOW
- **Effort**: 8 hours
- **Value**: HIGH
- **Dependencies**: Basic Editor (4.1), Pre-Import Scanner (1.1)
- **Status**: 📋 Planned (optional)

**What it does:**
- Validate G-code as you type (with debouncing)
- Highlight problematic lines
- Show warning indicators in margin
- Issues panel at bottom
- See problems immediately

**Implementation tasks:**
- [ ] Add validation debouncing (2h)
- [ ] Integrate scanner (2h)
- [ ] Add warning indicators (2h)
- [ ] Add issues panel (1h)
- [ ] Testing (1h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Feature 2

---

#### 4.4 Auto-Fix Features
- **Priority**: LOW
- **Effort**: 8 hours
- **Value**: MEDIUM
- **Dependencies**: Real-Time Validation (4.3)
- **Status**: 📋 Planned (optional)

**What it does:**
- Suggest fixes for common issues
- One-click fix for tool home Z
- One-click fix for M09/M05 sequence
- Add missing commands
- Preview before applying

**Implementation tasks:**
- [ ] Create fix suggestion system (3h)
- [ ] Implement tool home fix (1h)
- [ ] Implement M09/M05 fix (1h)
- [ ] Implement missing command fixes (2h)
- [ ] Testing (1h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Auto-Fix Capabilities

---

#### 4.5 Advanced Editor Features
- **Priority**: LOW
- **Effort**: 8 hours
- **Value**: LOW
- **Dependencies**: Basic Editor (4.1)
- **Status**: 📋 Planned (optional)

**What it does:**
- Search and replace
- Jump to line
- Find next/previous
- Case-sensitive search
- Regex support

**Implementation tasks:**
- [ ] Create search dialog (3h)
- [ ] Implement search logic (2h)
- [ ] Add replace functionality (2h)
- [ ] Testing (1h)

**Reference**: [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) - Feature 2

---

**Phase 4 Total Time**: 40 hours (4-6 weeks part-time)
**Phase 4 Value**: HIGH (but only if needed - assess user demand first)

---

### Phase 5: Multi-Computer Database (6-8 Weeks)

**Goal**: Proper multi-computer concurrent access without corruption risk

⚠️ **REQUIRES DECISIONS**: See "Decision Points" section before starting
⚠️ **ONLY IF NEEDED**: Assess whether current setup with monitoring (Phase 1) is sufficient

#### 5.1 Decision: Database Choice
- **Priority**: LOW (only if Phase 1 monitoring insufficient)
- **Effort**: 4 hours (research)
- **Value**: N/A (decision phase)
- **Dependencies**: None
- **Status**: 📋 Not started

**What to decide:**
- Self-hosted MySQL (free, more setup)
- Cloud database - PlanetScale (free tier)
- Cloud database - Supabase (free tier)
- Cloud database - Google Cloud SQL ($10-30/month)
- Stay with SQLite + monitoring

**Reference**: [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) - Phase 3

---

#### 5.2 Database Migration Planning
- **Priority**: LOW
- **Effort**: 8 hours
- **Value**: N/A (planning phase)
- **Dependencies**: Database Choice (5.1)
- **Status**: 📋 Not started

**What to plan:**
- Migration strategy
- Data integrity checks
- Rollback plan
- Testing approach
- Deployment timeline

---

#### 5.3 Database Setup & Migration
- **Priority**: LOW
- **Effort**: 16 hours
- **Value**: HIGH (if needed)
- **Dependencies**: Database Migration Planning (5.2)
- **Status**: 📋 Not started

**What it does:**
- Set up new database
- Migrate SQLite data to new DB
- Verify data integrity
- Test with one computer first

**Implementation tasks:**
- [ ] Set up database server/service (4h)
- [ ] Export SQLite data (2h)
- [ ] Import to new database (2h)
- [ ] Verify data integrity (2h)
- [ ] Test single-computer access (2h)
- [ ] Document connection settings (1h)
- [ ] Create rollback procedure (3h)

---

#### 5.4 Application Database Layer Update
- **Priority**: LOW
- **Effort**: 20 hours
- **Value**: HIGH (if needed)
- **Dependencies**: Database Setup (5.3)
- **Status**: 📋 Not started

**What it does:**
- Replace SQLite connector with MySQL/PostgreSQL
- Add connection configuration
- Handle network errors gracefully
- Add connection pooling
- Maintain backward compatibility (for rollback)

**Implementation tasks:**
- [ ] Install database connector library (5min)
- [ ] Create abstraction layer (6h)
- [ ] Update all database calls (8h)
- [ ] Add error handling (3h)
- [ ] Add connection retry logic (2h)
- [ ] Testing (1h)

---

#### 5.5 Multi-Computer Testing & Deployment
- **Priority**: LOW
- **Effort**: 12 hours
- **Value**: N/A (testing phase)
- **Dependencies**: Application Update (5.4)
- **Status**: 📋 Not started

**What to do:**
- Test with 2 computers simultaneously
- Test concurrent writes
- Test network interruption handling
- Deploy to all computers
- Monitor for issues

---

**Phase 5 Total Time**: 60 hours (6-8 weeks part-time)
**Phase 5 Value**: HIGH (but only if multi-computer issues are frequent)

---

## Priority Matrix

### High Priority (Do First)
1. ⭐ **Pre-Import File Scanner** (Phase 1.1)
   - Effort: 12h | Value: HIGH | Dependencies: None
   - **Recommended starting point**

2. ⭐ **Database File Monitor** (Phase 1.2)
   - Effort: 6h | Value: HIGH | Dependencies: None
   - Safety feature

3. ⭐ **Safety Warnings** (Phase 1.3)
   - Effort: 4h | Value: MEDIUM | Dependencies: None
   - Safety feature

4. ⭐ **Google Sheets API Setup** (Phase 2.1) - *if using Google Sheets*
   - Effort: 3h | Value: HIGH | Dependencies: None

5. ⭐ **Basic Google Sheets Sync** (Phase 2.2) - *if using Google Sheets*
   - Effort: 12h | Value: HIGH | Dependencies: 2.1

### Medium Priority (Do Second)
6. **Duplicate with Scan** (Phase 1.4)
   - Effort: 6h | Value: MEDIUM | Dependencies: 1.1

7. **Automatic Google Sheets Updates** (Phase 2.3) - *if using Google Sheets*
   - Effort: 10h | Value: HIGH | Dependencies: 2.2

8. **Version History Viewer** (Phase 3.1) - *after decisions*
   - Effort: 12h | Value: HIGH | Dependencies: None

9. **Archive Metadata Tracking** (Phase 3.3) - *after decisions*
   - Effort: 8h | Value: MEDIUM | Dependencies: None

### Low Priority (Optional/Future)
10. **Version Comparison Tool** (Phase 3.2)
    - Effort: 16h | Value: MEDIUM | Dependencies: 3.1

11. **Archive Cleanup** (Phase 3.4)
    - Effort: 8h | Value: MEDIUM | Dependencies: None

12. **Built-In Editor** (Phase 4) - *assess demand first*
    - Effort: 40h | Value: HIGH (once built) | Dependencies: 1.1

13. **Centralized Database** (Phase 5) - *only if monitoring insufficient*
    - Effort: 60h | Value: HIGH (if needed) | Dependencies: None

---

## Decision Points

### Before Starting Phase 2 (Google Sheets)

**Questions to answer:**
1. ❓ How often do you export to Google Sheets?
   - Daily → High priority
   - Weekly → Medium priority
   - Monthly → Low priority

2. ❓ How many people use the Google Sheet?
   - Multiple people → High priority
   - Just you → Medium priority

3. ❓ Is manual export/import painful?
   - Very → High priority
   - Somewhat → Medium priority
   - Not really → Low priority

**Decision template:**
```
GOOGLE SHEETS AUTOMATION:
☐ Priority: High / Medium / Low
☐ Start after Phase 1? Yes / No
☐ Reason: ___________________________
```

---

### Before Starting Phase 3 (Version System)

**Questions to answer:**
1. ❓ How long to keep archives?
   - Forever / 1 year / 90 days / Keep v1.0 only

2. ❓ Compression strategy?
   - Yes after 1 year / No / Yes after 90 days

3. ❓ What metadata to track?
   - Full (user, reason, dimensions, tools)
   - Basic (user, timestamp)
   - Minimal (timestamp only)

4. ❓ Migrate existing 7,915 archive files?
   - Yes, migrate all
   - No, only track new archives
   - Hybrid (basic metadata for existing)

**Decision template:**
```
VERSION SYSTEM DECISIONS:
☐ Retention: Forever / 1 year / 90 days / Keep v1.0 only
☐ Compression: Yes after 1 year / No / Yes after 90 days
☐ Metadata: Full / Basic / Minimal
☐ Migration: All files / New only / Hybrid
```

---

### Before Starting Phase 4 (Built-In Editor)

**Questions to answer:**
1. ❓ How often do you edit G-code files?
   - Daily → Consider building
   - Weekly → Consider building
   - Rarely → Low priority

2. ❓ Do you use an external editor you like?
   - Yes, happy with it → Low priority
   - No, would prefer built-in → High priority

3. ❓ Would real-time validation be valuable?
   - Very → Build editor
   - Somewhat → Maybe build
   - Not really → Don't build

**Decision template:**
```
BUILT-IN EDITOR:
☐ Priority: High / Medium / Low
☐ Build it? Yes / No / Maybe Later
☐ Reason: ___________________________
```

---

### Before Starting Phase 5 (Centralized Database)

**Questions to answer:**
1. ❓ How many computers access database?
   - 2 computers, same user → Maybe not needed
   - 3+ computers → Probably needed
   - Multiple users → Definitely needed

2. ❓ How often do database conflicts occur?
   - Never/Rarely → Not needed (use monitoring)
   - Occasionally → Consider it
   - Frequently → Needed

3. ❓ Budget for cloud database?
   - $0 → Self-host or use free tier
   - $10-30/month → Cloud database OK
   - $50+/month → Premium solutions available

4. ❓ Technical comfort level?
   - Simple only → Use monitoring (Phase 1)
   - Moderate OK → Cloud database
   - Advanced OK → Self-hosted MySQL

**Decision template:**
```
CENTRALIZED DATABASE:
☐ Is it needed? Yes / No / Not yet
☐ If yes, which option: Self-hosted / PlanetScale / Supabase / Google Cloud SQL
☐ Budget: $0 / $10-30/mo / $50+/mo
☐ When to implement: After Phase 1 monitoring / Later / Not at all
```

---

## Recommended Implementation Sequence

### Option A: Minimum Viable Improvements (Fastest)
**Timeline**: 3-4 weeks part-time

1. Pre-Import File Scanner (12h)
2. Database File Monitor (6h)
3. Safety Warnings (4h)

**Total**: 22 hours
**Benefits**: Safety + useful scanner
**Skip**: Google Sheets, versions, editor, database

---

### Option B: Safety + Google Sheets (Most Common)
**Timeline**: 6-8 weeks part-time

1. Pre-Import File Scanner (12h)
2. Database File Monitor (6h)
3. Safety Warnings (4h)
4. Google Sheets API Setup (3h)
5. Basic Google Sheets Sync (12h)
6. Automatic Google Sheets Updates (10h)
7. Duplicate with Scan (6h)

**Total**: 53 hours
**Benefits**: Safety + scanner + automated Google Sheets
**Skip**: Versions, editor, database

---

### Option C: Complete (Except Database)
**Timeline**: 4-5 months part-time

Phase 1 + Phase 2 + Phase 3 (after decisions)

**Total**: 117 hours
**Benefits**: Safety + Google Sheets + version improvements + scanner
**Skip**: Editor (unless demand), centralized database (unless needed)

---

### Option D: Everything (Maximum)
**Timeline**: 6-8 months part-time

All phases

**Total**: 217+ hours
**Benefits**: Complete overhaul with all features
**Note**: Probably overkill unless team grows significantly

---

## Time Investment Summary

| Phase | Features | Effort | Timeline | Prerequisites |
|-------|----------|--------|----------|---------------|
| Phase 1 | Safety + Scanner | 28h | 1-2 weeks | None |
| Phase 2 | Google Sheets | 29h | 2-4 weeks | Phase 1 recommended |
| Phase 3 | Version System | 60h | 3-4 weeks | Decisions needed |
| Phase 4 | Built-In Editor | 40h | 4-6 weeks | Phase 1, assess demand |
| Phase 5 | Centralized DB | 60h | 6-8 weeks | Assess if needed |

**Quick wins total**: 57 hours (Phase 1 + 2)
**Full roadmap total**: 217+ hours

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ Can scan files before import
- ✅ Zero database corruption incidents
- ✅ All users aware when another computer modifies database
- ✅ Auto-backup before every write

### Phase 2 Success Criteria
- ✅ Google Sheets updates with one click
- ✅ No manual import needed
- ✅ Sheet updates automatically after program changes
- ✅ Sync status visible in UI

### Phase 3 Success Criteria
- ✅ Can view complete version history for any program
- ✅ Can compare any two versions
- ✅ Metadata tracked for all new archives
- ✅ Archive cleanup tool available

### Phase 4 Success Criteria
- ✅ Can edit G-code files in application
- ✅ Real-time validation shows issues as you type
- ✅ Auto-fix available for common issues
- ✅ No need for external editor

### Phase 5 Success Criteria
- ✅ Multiple computers can access database simultaneously
- ✅ Zero corruption incidents
- ✅ Real-time updates across all computers
- ✅ Network error handling works correctly

---

## Current Recommendations

### Start Here (Recommended)
1. **Implement Phase 1** (Safety + Scanner)
   - High value, low effort
   - No prerequisites
   - Immediate benefits
   - 28 hours total

2. **Decide on Google Sheets** (answer questions)
   - If yes → Implement Phase 2
   - If no → Skip to Phase 3 or 4

3. **Use for 2-4 weeks**, then assess:
   - Is database monitoring sufficient?
   - Do we need Google Sheets automation?
   - Are version improvements needed?
   - Is editor wanted?

### Don't Do Yet
- ❌ **Centralized Database** - Wait and see if monitoring solves issues
- ❌ **Built-In Editor** - Assess demand first
- ❌ **Version System** - Answer decision questions first

---

## Questions for You

### To Determine Priority

1. **Which pain points are most urgent?**
   - [ ] Database conflicts/corruption
   - [ ] Manual Google Sheets updates
   - [ ] Can't scan files before import
   - [ ] Hard to track version changes
   - [ ] Need better editor

2. **How much time can you invest?**
   - [ ] 10-15 hours/week (complete Phase 1 in 2 weeks)
   - [ ] 5-10 hours/week (complete Phase 1 in 4 weeks)
   - [ ] 2-5 hours/week (complete Phase 1 in 8 weeks)

3. **What's the top priority?**
   - Rank these 1-5:
   - [ ] Safety features (prevent corruption)
   - [ ] File scanner
   - [ ] Google Sheets automation
   - [ ] Version improvements
   - [ ] Built-in editor

---

## Next Actions

### To Start Phase 1:
1. Review [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md)
2. Confirm starting with Pre-Import Scanner
3. Set aside 12 hours over 1-2 weeks
4. Begin implementation

### To Start Phase 2:
1. Answer Google Sheets questions above
2. Review [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md)
3. Follow Google Sheets API setup guide
4. Begin implementation

### To Start Phase 3:
1. Answer version system decision questions
2. Review [VERSION_SYSTEM_ANALYSIS.md](VERSION_SYSTEM_ANALYSIS.md)
3. Review [FUTURE_IMPROVEMENTS_TODO.md](FUTURE_IMPROVEMENTS_TODO.md)
4. Begin implementation

---

## Document References

| Document | Purpose |
|----------|---------|
| [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) | This document - master plan |
| [FUTURE_IMPROVEMENTS_TODO.md](FUTURE_IMPROVEMENTS_TODO.md) | Detailed questions and plans |
| [FILE_EDITOR_AND_SCANNER_PLAN.md](FILE_EDITOR_AND_SCANNER_PLAN.md) | File scanner & editor details |
| [MULTI_COMPUTER_SYNC_GUIDE.md](MULTI_COMPUTER_SYNC_GUIDE.md) | Database sync & Google Sheets |
| [VERSION_SYSTEM_ANALYSIS.md](VERSION_SYSTEM_ANALYSIS.md) | Version system analysis |
| [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) | Recently completed features |

---

**Last Updated**: 2026-02-04
**Status**: 📋 Planning Phase - Ready to Start Phase 1
**Recommended Next Step**: Begin Phase 1 with Pre-Import File Scanner
