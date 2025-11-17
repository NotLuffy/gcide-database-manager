# G-Code Parser & Database Manager - TODO List

## Current Status

### ✅ COMPLETED (Phase 1)
- [x] Multi-method dimension extraction (Thickness, Hub Height, CB, OB)
- [x] P-code to thickness mapping (complete P1-P40 table)
- [x] OD validation from G-code
- [x] P-code consistency checks (pairing, multiple, match)
- [x] Program number cross-validation
- [x] Hub height default (0.50") for hub-centric parts
- [x] N/A display for non-applicable fields
- [x] Color-coded validation in GUI (RED/YELLOW/GREEN)
- [x] Improved folder scanning (files with and without extensions)
- [x] Database auto-upgrade for validation columns

---

## 🎯 PHASE 2 - Medium Priority (Recommended Next)

### 1. **Material Validation from Feeds & Speeds** ⚡ HIGH IMPACT
**Priority:** HIGH | **Difficulty:** MEDIUM | **Time:** ~1 hour

**Why Important:**
- **Critical for safety** - Wrong speeds destroy tools and parts
- Prevents running aluminum programs on steel (and vice versa)
- Catches material mismatches before job starts

**Implementation:**
```python
def _extract_feeds_and_speeds(self, lines):
    """
    Extract feed rates and spindle speeds from G-code

    Material indicators:
    - Aluminum: F=0.006-0.012 IPR, RPM=600-1200
    - Steel: F=0.003-0.006 IPR, RPM=300-600
    - Stainless: F=0.002-0.004 IPR, RPM=200-400
    """
    feeds = []
    rpms = []

    for line in lines:
        # Feed rate: F0.006
        f_match = re.search(r'F\s*([\d.]+)', line, re.IGNORECASE)
        if f_match:
            feeds.append(float(f_match.group(1)))

        # Spindle speed: S550 or G97 S550
        s_match = re.search(r'S\s*(\d+)', line, re.IGNORECASE)
        if s_match:
            rpms.append(int(s_match.group(1)))

    if feeds and rpms:
        avg_feed = sum(feeds) / len(feeds)
        avg_rpm = sum(rpms) / len(rpms)

        # Determine material from feeds/speeds
        if avg_feed > 0.008 and avg_rpm > 500:
            return 'Aluminum (from speeds)'
        elif avg_feed < 0.005 and avg_rpm < 400:
            return 'Steel/Stainless (from speeds)'

    return None
```

**Validation:**
- Compare extracted material vs title material
- Flag if title says "Aluminum" but speeds indicate "Steel"

**Benefits:**
- Prevent catastrophic tool failures
- Ensure correct cutting parameters
- Cross-validate material specification

---

### 2. **"Re-Scan Changed Files" Button** ⚡ EFFICIENCY
**Priority:** MEDIUM | **Difficulty:** EASY | **Time:** ~30 min

**Why Important:**
- Much faster than full folder scan
- Only processes modified files
- Better workflow for iterative G-code fixes

**Implementation:**
```python
def rescan_changed_files(self):
    """Re-scan only files modified since last database update"""
    cursor = self.conn.cursor()
    cursor.execute("SELECT program_number, file_path, last_modified FROM programs")

    updated = 0
    skipped = 0

    for row in cursor.fetchall():
        prog_num, file_path, db_modified = row

        if os.path.exists(file_path):
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

            # Only re-parse if file is newer than database record
            if file_modified > db_modified:
                result = self.parse_gcode_file(file_path)
                if result:
                    # Update database
                    self.update_database_record(result)
                    updated += 1
            else:
                skipped += 1

    messagebox.showinfo("Re-Scan Complete",
                       f"Updated: {updated}\nSkipped (unchanged): {skipped}")
    self.refresh_list()
```

**UI Changes:**
- Add "Re-Scan Changed Files" button next to "Scan Folder"
- Show progress: "Checking 500 files... Updated 12, Skipped 488"

**Benefits:**
- 10-50x faster for incremental updates
- Only validates files you've edited
- Perfect for fixing errors one-by-one

---

### 3. **Counterbore Depth Validation (STEP Parts)** 📏
**Priority:** MEDIUM | **Difficulty:** MEDIUM | **Time:** ~45 min

**Why Important:**
- STEP parts have two bore depths that need validation
- Currently only validating CB diameter, not CB depth
- Completes STEP part validation

**Implementation:**
```python
def _extract_counterbore_depth(self, lines, spacer_type):
    """
    Extract counterbore depth from two-stage boring (STEP parts only)

    Pattern:
    T121 (BORE)
    G01 X3.307 Z-0.75    ← Counterbore depth = 0.75"
    G01 X2.795 Z-2.0     ← Full depth = 2.0"
    """
    if spacer_type != 'step':
        return None

    in_bore = False
    z_depths = []

    for line in lines:
        if 'T121' in line.upper() or 'BORE' in line.upper():
            in_bore = True
        elif re.search(r'T[^1]\d{2}', line.upper()):
            in_bore = False

        if in_bore:
            z_match = re.search(r'Z\s*-\s*([\d.]+)', line, re.IGNORECASE)
            if z_match:
                z_depths.append(float(z_match.group(1)))

    # Counterbore depth is the shallowest Z (first stage)
    if len(z_depths) >= 2:
        return min(z_depths)

    return None
```

**Validation:**
- Compare against expected CB depth (if in title)
- Validate CB depth < total thickness

**Benefits:**
- Complete STEP part dimensional validation
- Catch CB depth errors before machining

---

## 🔮 PHASE 3 - Future Enhancements

### 4. **2-Piece Part Matching** 🔗
**Priority:** LOW | **Difficulty:** HARD | **Time:** ~2-3 hours

**What It Does:**
- Automatically find LUG + STUD pairs
- Match by OD, CB, and combined thickness
- Suggest which programs go together

**Implementation:**
```python
def find_2pc_pairs(self):
    """Find matching 2-piece part pairs in database"""
    cursor = self.conn.cursor()
    cursor.execute("""
        SELECT program_number, outer_diameter, center_bore, thickness
        FROM programs
        WHERE spacer_type LIKE '2pc%'
        ORDER BY outer_diameter, center_bore
    """)

    parts = cursor.fetchall()
    pairs = []

    for i, part1 in enumerate(parts):
        for part2 in parts[i+1:]:
            # Match if same OD and CB within tolerance
            if (abs(part1[1] - part2[1]) < 0.05 and  # OD match
                abs(part1[2] - part2[2]) < 0.5):     # CB match

                combined_thickness = part1[3] + part2[3]
                pairs.append({
                    'lug': part1[0],
                    'stud': part2[0],
                    'combined_thickness': combined_thickness
                })

    return pairs
```

**UI:**
- New "Find 2PC Pairs" button
- Shows suggested pairs in popup window
- "Combined thickness: 1.00\" (0.75\" LUG + 0.25\" STUD)"

---

### 5. **Spindle Speed Calculation & Validation** 🔄
**Priority:** LOW | **Difficulty:** MEDIUM | **Time:** ~1 hour

**Formula:**
```
RPM = (SFM × 12) / (π × OD)

Where:
- SFM = Surface Feet per Minute (constant for material)
- Aluminum: 550-650 SFM
- Steel: 250-350 SFM
- OD = Outer Diameter (inches)
```

**Validation:**
- Calculate expected RPM from OD and material
- Compare against actual RPM in G-code
- Flag if speeds are dangerously high/low

---

### 6. **Database Search & Filter** 🔍
**Priority:** MEDIUM | **Difficulty:** EASY | **Time:** ~45 min

**Features:**
- Search by: Program #, OD, Thickness, CB, Material
- Filter by: Part Type, Validation Status
- Sort by: Any column

**UI Mockup:**
```
[Search: _______] [Type: All ▼] [Status: All ▼] [Material: All ▼]

Results:
o58436  hub_centric  5.75"  0.75"  56.1mm  ERROR
o57500  standard     5.75"  1.00"  38.1mm  WARNING
```

---

### 7. **Export Validation Report** 📊
**Priority:** LOW | **Difficulty:** EASY | **Time:** ~30 min

**Export Formats:**
- CSV: For Excel analysis
- PDF: For printing/sharing
- HTML: For web viewing

**Report Contents:**
- Summary: X errors, Y warnings, Z passing
- Detailed list of all validation issues
- Grouped by part type or error type

---

### 8. **Batch G-Code Correction** 🔧
**Priority:** LOW | **Difficulty:** HARD | **Time:** ~3-4 hours

**Automatic Fixes:**
- Adjust CB to match title spec
- Fix P-codes based on thickness
- Update drill depth for correct thickness

**Safety:**
- Show preview before applying
- Create backup of original file
- Log all changes made

---

### 9. **Integration with CAM Software** 🔗
**Priority:** LOW | **Difficulty:** HARD | **Time:** ~5+ hours

**Features:**
- Import CAM post-processor output
- Validate before generating G-code
- Auto-generate title from CAM data

---

### 10. **Statistical Analysis** 📈
**Priority:** LOW | **Difficulty:** MEDIUM | **Time:** ~2 hours

**Metrics:**
- Most common part types
- Average tolerances (CB, OB, OD)
- Error rate by part type
- P-code usage distribution
- Material breakdown

**Visualizations:**
- Charts showing error trends
- Histogram of part thickness distribution
- Scatter plot: OD vs CB

---

## 🐛 Known Issues / Tech Debt

### Minor Issues:
- [ ] OD extraction could be more robust (handle more G-code variations)
- [ ] Drill depth not always found (some files missing G81/G83)
- [ ] Detection confidence could be numerical score (0-100%)
- [ ] Some metric parts (10MM, 12MM) rarely used - test coverage low

### Performance:
- [ ] Full folder scan can be slow (500+ files)
  - **Solution:** Re-Scan Changed Files button (Phase 2 #2)
- [ ] Database could use indexing for large datasets (10,000+ programs)

### UI/UX:
- [ ] No keyboard shortcuts
- [ ] Can't sort table by clicking columns
- [ ] Details window not resizable
- [ ] No dark mode (if desired)

---

## 📊 Priority Matrix

| Task | Priority | Impact | Effort | ROI |
|------|----------|--------|--------|-----|
| **Material from Feeds/Speeds** | HIGH | HIGH | MEDIUM | ⭐⭐⭐⭐⭐ |
| **Re-Scan Changed Files** | MEDIUM | HIGH | LOW | ⭐⭐⭐⭐⭐ |
| **Counterbore Depth** | MEDIUM | MEDIUM | MEDIUM | ⭐⭐⭐ |
| **Database Search** | MEDIUM | MEDIUM | LOW | ⭐⭐⭐⭐ |
| **2PC Pair Matching** | LOW | MEDIUM | HIGH | ⭐⭐ |
| **Spindle Speed Calc** | LOW | LOW | MEDIUM | ⭐⭐ |
| **Export Reports** | LOW | LOW | LOW | ⭐⭐⭐ |
| **Batch Correction** | LOW | HIGH | HIGH | ⭐⭐ |

**ROI = Return on Investment** (Impact / Effort)

---

## 🎯 Recommended Implementation Order

### Week 1: Quick Wins
1. **Re-Scan Changed Files** button (~30 min)
   - Immediate productivity boost
   - Very easy to implement

2. **Database Search & Filter** (~45 min)
   - Improves usability significantly
   - Easy to implement

### Week 2: High-Impact Features
3. **Material from Feeds/Speeds** (~1 hour)
   - Critical safety feature
   - Prevents expensive mistakes

4. **Counterbore Depth** (~45 min)
   - Completes STEP validation
   - Medium difficulty

### Week 3: Nice-to-Haves
5. **Export Reports** (~30 min)
   - Useful for documentation
   - Easy to implement

6. **2PC Pair Matching** (~2-3 hours)
   - Helpful but not critical
   - More complex

### Future:
7. Other Phase 3 items as needed

---

## 🚀 Quick Start: Implementing Phase 2

Ready to implement Phase 2? Here's the order:

1. **Start here:** "Re-Scan Changed Files" (30 min, easy, high value)
2. **Then:** Material validation (1 hour, medium, critical for safety)
3. **Finally:** Counterbore depth (45 min, medium, completes STEP)

**Total time: ~2.25 hours for all Phase 2 features**

Would you like me to implement any of these? Just say which one(s) and I'll get started!

---

## 📝 Notes

- All times are estimates for implementation + testing
- Priorities can shift based on production needs
- Some features may reveal need for additional features
- User feedback should drive priority changes

**Last Updated:** 2025-01-16 (Phase 1 Complete)
