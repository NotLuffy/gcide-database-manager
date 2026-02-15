# Version & Archive System - Analysis & Recommendations

## Current System Analysis

### What You Have (Three Systems!)

You currently have **THREE different version/archive systems** running:

#### 1. **`archive/` Folder System** (Most Active)
- **Location**: `archive/[date]/program_version.nc`
- **Usage**: 7,915 archived files across 10 date folders
- **Managed by**: `repository_manager.py`
- **How it works**:
  - When you update a file, old version moves to `archive/2026-02-02/o13002_1.nc`
  - Files organized by date archived
  - Version numbers increment: `_1`, `_2`, `_3`, etc.
  - **4,148 archive operations logged** (very actively used!)

#### 2. **`versions/` Folder + Database**
- **Location**: `versions/o13002/v1.0.nc` + `program_versions` table
- **Usage**: Only 1 program (o10000) with 2 versions
- **Managed by**: `gcode_database_manager.py`
- **How it works**:
  - Stores versions in program-specific folders
  - Tracks metadata in database (date, user, change summary)
  - **Barely used** (only 2 versions for 1 program)

#### 3. **`revised_repository/` Folder**
- **Location**: `revised_repository/`
- **Usage**: 0 files currently
- **Purpose**: Store revised/edited files
- **Status**: Empty, not actively used

---

## Issues Identified

### ⚠️ Problem 1: Redundant Systems
You have **two separate version tracking systems** doing similar things:
- `archive/` folder (actively used - 7,915 files)
- `versions/` folder (barely used - 2 files)

**Impact**: Confusion, wasted space, no single source of truth

### ⚠️ Problem 2: No Version Metadata in Archive
The `archive/` system doesn't store:
- Who made the change
- Why the change was made
- What was changed
- Dimensions before/after

**Impact**: Can't easily understand history or find "when did we change X?"

### ⚠️ Problem 3: No Easy Way to Compare Versions
Currently to compare versions you need to:
1. Manually browse `archive/` folders
2. Find the old version file
3. Open both files manually
4. Compare by eye

**Impact**: Time-consuming, error-prone

### ⚠️ Problem 4: No Retention Policy
Files stay in archive forever:
- 7,915 files taking up space
- No automatic cleanup
- Hard to find relevant versions among all the noise

**Impact**: Growing disk usage, slower backups

### ⚠️ Problem 5: Archive in Backups
When you backup, you're backing up 7,915+ archived files:
- Most you probably never need
- Slows down backup process
- Takes up backup space

**Impact**: Larger backups, longer backup times

---

## Recommendations

### 🎯 Option 1: Consolidate to ONE System (Recommended)

**Merge everything into an improved version tracking system**

#### Proposed Structure:
```
versions/
├── o13002/
│   ├── v1.0.nc                    ← Original version
│   ├── v2.0.nc                    ← First edit
│   ├── v3.0.nc                    ← Second edit
│   └── metadata.json              ← Version metadata
├── o61045/
│   ├── v1.0.nc
│   ├── v2.0.nc
│   └── metadata.json
└── ...
```

#### metadata.json Example:
```json
{
  "v1.0": {
    "date": "2025-11-25T10:30:00",
    "user": "john",
    "change_summary": "Initial import",
    "dimensions": {"od": 13.0, "thickness": 2.0},
    "file_hash": "abc123..."
  },
  "v2.0": {
    "date": "2025-12-15T14:22:00",
    "user": "john",
    "change_summary": "Fixed tool home position",
    "dimensions": {"od": 13.0, "thickness": 2.0},
    "file_hash": "def456..."
  }
}
```

#### Benefits:
✅ Single system - no confusion
✅ Rich metadata - know who/what/when/why
✅ Organized by program number (easy to find)
✅ Can add features like tags, notes, comparisons
✅ Database stays in sync

---

### 🎯 Option 2: Keep Archive, Add Metadata (Simpler)

**Keep current `archive/` system but enhance it**

#### What to Add:
1. **Metadata file per archive**
   ```
   archive/
   ├── 2026-02-02/
   │   ├── o13002_1.nc
   │   ├── o13002_1.json         ← Metadata
   │   ├── o61045_2.nc
   │   └── o61045_2.json         ← Metadata
   └── ...
   ```

2. **Archive management UI**
   - View archived versions for a program
   - See who/when/why each version was archived
   - Compare versions side-by-side
   - Restore old versions

#### Benefits:
✅ Minimal changes to existing system
✅ Keeps date-based organization
✅ Adds missing metadata
✅ Already have 7,915 files in this system

---

### 🎯 Option 3: Tiered Archiving (Best for Large Scale)

**Multiple archive tiers based on age**

#### Structure:
```
versions/
├── o13002/
│   ├── current.nc              ← Always points to latest
│   ├── v1.0.nc                 ← Keep forever (original)
│   ├── v-latest.nc             ← Previous version
│   └── metadata.json
archive_recent/                  ← Last 90 days
├── 2026-02-02/
│   └── o13002_2.nc
archive_long_term/               ← 90-365 days
├── 2025-12/
│   └── o13002_1.nc
archive_cold/                    ← >365 days (compressed)
└── 2024/
    └── archived_2024.zip       ← Compressed old versions
```

#### Benefits:
✅ Keep everything but optimize space
✅ Fast access to recent changes
✅ Compressed old archives
✅ Clear retention policy

---

## Specific Improvements to Implement

### 1. **Add Version Comparison Tool** (High Priority)

```python
def compare_versions(program_number, version1, version2):
    """
    Compare two versions of a program
    Shows:
    - Line-by-line differences
    - Dimensional changes
    - Tool changes
    - G-code pattern changes
    """
```

**Why**: Currently no easy way to see "what changed"

### 2. **Version History Viewer** (High Priority)

Add to right-click menu:
```
Right-click program → "View Version History"
```

Shows:
```
o13002 - Version History

v3.0 (current) - 2026-02-03 14:30
  ✓ User: john
  ✓ Change: "Fixed coolant sequence (M09 before M05)"

v2.0 - 2026-01-27 10:15
  ✓ User: john
  ✓ Change: "Updated tool home to Z-13"
  [Restore] [Compare to Current] [View File]

v1.0 - 2025-11-25 09:00
  ✓ User: john
  ✓ Change: "Initial import"
  [Restore] [Compare to Current] [View File]
```

**Why**: Can't easily browse history right now

### 3. **Automated Change Detection** (Medium Priority)

When saving a version, automatically detect and log:
- ✅ Tool home position changes
- ✅ Coolant sequence changes
- ✅ Dimensional changes
- ✅ Tool changes
- ✅ Feed/speed changes

**Why**: Better than manual change summaries

### 4. **Archive Cleanup Tool** (Medium Priority)

Add a maintenance tool:
```
Maintenance → Clean Up Old Archives

Options:
- Delete versions older than [365] days
- Keep only: [✓] Original version (v1.0)
            [✓] Last 5 versions
            [ ] Compress versions older than [180] days
```

**Why**: 7,915 files will keep growing forever

### 5. **Version Tags & Notes** (Low Priority)

Allow tagging versions:
```
v2.0 [STABLE] [PRODUCTION]
  "This version is validated and in production"

v3.0 [TESTING]
  "Experimental - testing new tool path"
```

**Why**: Easy to mark known-good versions

---

## Migration Plan

### Phase 1: Add Metadata to Current System
1. Create metadata tracking for new archives
2. Don't touch existing 7,915 files yet
3. Add version history viewer UI
4. Add comparison tool

### Phase 2: Consolidate Systems
1. Migrate `archive/` → `versions/` structure
2. Generate metadata for existing files (where possible)
3. Deprecate `archive/` folder
4. Update backup system

### Phase 3: Optimize Storage
1. Implement retention policies
2. Add compression for old versions
3. Create archive cleanup tools

---

## Recommended Immediate Actions

### Quick Wins (This Week):

1. **Add Version History Viewer to UI** ⭐
   - Right-click → "View Version History"
   - Shows all versions from `archive/` folders
   - Allows restore and comparison

2. **Add Metadata to New Archives** ⭐
   - When archiving, create `.json` file with:
     - User who made change
     - Timestamp
     - Change summary (auto-detected if possible)
     - Dimension snapshot

3. **Fix Archive Backup Issue** ⭐
   - Add option: "Full Backup (exclude old archives)"
   - Only backup last 30-90 days of archives
   - Keep full archive locally, not in backups

### Medium Term (This Month):

4. **Version Comparison Tool**
   - Side-by-side file comparison
   - Highlight differences
   - Show dimension changes

5. **Archive Maintenance Tool**
   - View archive statistics
   - Clean up old archives
   - Compress rarely-accessed versions

### Long Term (Next Quarter):

6. **Migrate to Unified System**
   - Plan migration of 7,915 files
   - Test with subset first
   - Update all code to use new system

---

## Storage Impact Analysis

### Current Situation:
```
Repository files:     6,992 files (let's say ~5 GB)
Archive files:        7,915 files (~6 GB)
Versions DB:          2 files (negligible)
Total:                ~11 GB
```

### With Improvements:

#### Option A: Keep All Archives
- Add metadata: +8 MB (JSON files)
- **Total: ~11 GB**
- Backups: ~11 GB each

#### Option B: Retention Policy (Keep 90 days)
- Assume 50% of archives >90 days old
- Archive: ~3 GB (vs 6 GB)
- **Total: ~8 GB** (27% reduction)
- Backups: ~8 GB each (27% smaller)

#### Option C: Compression (>365 days)
- Assume 30% of archives >1 year
- Compressed: 0.5 GB (vs 1.8 GB)
- **Total: ~9.7 GB** (12% reduction)
- Better for rarely-accessed old versions

---

## Technical Implementation Guide

### 1. Enhanced Archive Function

```python
def archive_with_metadata(old_file_path, program_number, user, change_summary=None):
    """Archive file with rich metadata"""

    # Archive file (existing code)
    version = get_next_version_number(program_number)
    archive_path = move_to_archive(old_file_path, program_number, version)

    # NEW: Create metadata
    metadata = {
        "program_number": program_number,
        "version": version,
        "date_archived": datetime.now().isoformat(),
        "archived_by": user,
        "change_summary": change_summary or detect_changes(old_file_path),
        "dimensions": get_dimensions_snapshot(program_number),
        "file_size": os.path.getsize(old_file_path),
        "file_hash": calculate_hash(old_file_path)
    }

    # Save metadata
    metadata_path = archive_path.replace('.nc', '.json')
    save_json(metadata_path, metadata)

    return archive_path
```

### 2. Version History Viewer

```python
def show_version_history(program_number):
    """Show version history for a program"""

    # Find all archived versions
    versions = []
    for date_folder in archive_path.iterdir():
        for file in date_folder.glob(f'{program_number}_*.nc'):
            # Load metadata if exists
            metadata_file = file.replace('.nc', '.json')
            if os.path.exists(metadata_file):
                metadata = load_json(metadata_file)
            else:
                # Generate basic metadata from file
                metadata = {
                    "version": extract_version(file.name),
                    "date_archived": get_file_date(file),
                    "archived_by": "unknown"
                }
            versions.append(metadata)

    # Sort by version/date
    versions.sort(key=lambda v: v['date_archived'], reverse=True)

    # Display in UI
    display_version_history_window(program_number, versions)
```

### 3. Version Comparison

```python
def compare_versions(program_number, version1_path, version2_path):
    """Compare two versions and show differences"""

    # Parse both files
    result1 = parse_gcode_file(version1_path)
    result2 = parse_gcode_file(version2_path)

    # Compare dimensions
    dim_changes = compare_dimensions(result1, result2)

    # Compare G-code line by line
    line_changes = compare_gcode_lines(version1_path, version2_path)

    # Compare tools
    tool_changes = compare_tools(result1, result2)

    # Display comparison window
    show_comparison_window(dim_changes, line_changes, tool_changes)
```

---

## Questions to Answer

Before implementing, decide:

1. **How long to keep archives?**
   - Forever? 1 year? 90 days?
   - Always keep v1.0 (original)?

2. **Compression strategy?**
   - Compress old versions?
   - When? >90 days? >1 year?

3. **What to track in metadata?**
   - User who made change?
   - Change reason/summary?
   - Dimensions before/after?
   - Validation status?

4. **Backup strategy?**
   - Include all archives in backup?
   - Or only recent (30-90 days)?
   - Separate archive backup?

5. **Migration approach?**
   - Migrate all 7,915 existing files?
   - Or only track new archives going forward?
   - Hybrid: metadata for new, keep old as-is?

---

## Recommendation Summary

### 🏆 Best Approach: Hybrid (Recommended)

1. **Keep existing `archive/` system** (7,915 files as-is)
2. **Add metadata for NEW archives** (from today forward)
3. **Build version history UI** (shows old + new archives)
4. **Add comparison tools**
5. **Implement retention policy** (delete archives >1 year)
6. **Eventually migrate** to unified `versions/` system

### Why This Approach?
✅ Minimal disruption to working system
✅ Immediate benefits (UI improvements)
✅ Don't need to touch 7,915 existing files
✅ Can test with new data first
✅ Gradual migration path
✅ User sees improvements immediately

---

## Next Steps

1. **Review this analysis** - Any questions or concerns?
2. **Decide on retention policy** - How long to keep archives?
3. **Prioritize features** - Which improvements matter most?
4. **Start with UI improvements** - Version history viewer first?
5. **Implement metadata tracking** - For new archives going forward

Would you like me to implement any of these improvements?
