# Tool Analysis & Safety Validation Guide

## Quick Start

### First Time Setup
1. **Files** tab → Click **⚡ Rescan Changed** (or **🔄 Rescan Database** for first time)
2. Wait for scan to complete
3. Tool and safety data now available for all files

### View Tool Statistics
**Reports** tab → Click **🔧 Tool Analysis**

---

## What Gets Analyzed

### Tool Extraction
Automatically finds all tool numbers in your G-code:
- T101 (Face/Turn)
- T121 (Bore)
- T202 (Drill)
- T303 (Tap)
- T404 (Groove)
- Any other T### tools

### Tool Validation
Checks if correct tools are used for each part type:

| Part Type | Required Tools |
|-----------|---------------|
| Hub-Centric | T121 (Boring) |
| STEP | T101 (Facing) + T121 (Boring) |
| Parts with drill depth | T202 (Drill) |

### Safety Block Validation
Ensures critical safety blocks are present:

| Safety Block | Purpose |
|--------------|---------|
| G28 | Return to home position |
| G54/G55/G56 | Work coordinate system |
| M30 or M02 | Program end |
| M03/M04 | Spindle start |
| M05 | Spindle stop |

---

## Tool Analysis Window

### Tab 1: Tool Summary

**Shows:**
- Total programs analyzed
- Programs with tool issues
- Programs with safety issues
- Most common tools (all parts)
- Tools by part type
- Most common tool sequences

**Example:**
```
T101: 7,892 programs (96.8%)  ← Most programs use facing tool
T121: 3,456 programs (42.4%)  ← 42% are hub-centric or STEP
T202: 2,134 programs (26.2%)  ← 26% have drilling operations
```

**Use This To:**
- Understand tool usage patterns
- Identify standard tool sequences
- See which tools are most critical
- Compare tool usage across part types

### Tab 2: Tool Issues

**Shows programs with:**
- Missing required tools
- Unexpected tool usage
- Tool sequence problems

**Example:**
```
o12345 (hub_centric):
  ⚠ Hub-centric part missing boring tool (T121)

o67890 (step):
  ⚠ STEP part missing facing tool (T101)

o54321 (standard):
  ⚠ Drill depth 1.50" detected but no drill tool (T202)
```

**Use This To:**
- Find programs that need tool corrections
- Identify potential machining problems
- Quality control before production

### Tab 3: Safety Issues

**Shows programs with:**
- Missing safety blocks
- Incomplete safety sequences
- Spindle control problems

**Example:**
```
o11111 (hub_centric):
  ⚠ Missing G28 (return to home position)
  ⚠ Spindle started (M03/M04) but not stopped (M05)

o22222 (standard):
  ⚠ Missing work coordinate system (G54/G55/G56)
  ⚠ Missing program end (M30 or M02)
```

**Use This To:**
- Ensure safe machine operation
- Prevent crashes and collisions
- Meet safety standards
- Audit programs before running

---

## Understanding Tool Sequences

### Common Sequences

**Simple Parts:**
```
T101 → T202
(Face, then drill)
```

**Hub-Centric Parts:**
```
T101 → T121 → T202
(Face, bore hub, drill holes)
```

**STEP Parts:**
```
T101 → T121 → T202 → T303
(Face, bore counterbore, drill holes, tap threads)
```

### Sequence Analysis Benefits
- **Identify standards:** See what sequence is used most often
- **Find outliers:** Programs with unusual tool sequences
- **Optimize operations:** Reduce tool changes by grouping similar programs

---

## Fixing Issues

### Tool Issues

**Problem:** "Hub-centric part missing boring tool (T121)"

**Solution:**
1. Open the G-code file
2. Add boring operation with T121
3. Rescan the file: **Files** → **⚡ Rescan Changed**
4. Verify fix: **Reports** → **🔧 Tool Analysis**

**Problem:** "Drill depth detected but no drill tool (T202)"

**Solution:**
1. Check if T202 is actually used (parser might have missed it)
2. If missing, add drill operation
3. If present, the parser regex might need adjustment

### Safety Issues

**Problem:** "Missing G28 (return to home position)"

**Solution:**
1. Add `G28 U0 W0` at end of program (before M30)
2. Rescan the file

**Problem:** "Spindle started but not stopped"

**Solution:**
1. Add `M05` (spindle stop) before program end
2. Typical placement: after all operations, before G28

**Problem:** "Missing work coordinate system (G54/G55/G56)"

**Solution:**
1. Add `G54` (or G55/G56) at beginning of program
2. Place after tool selection, before operations

---

## Best Practices

### Before Production
1. ✅ Run **Tool Analysis** to check all programs
2. ✅ Fix any tool issues (missing required tools)
3. ✅ Fix all safety issues (CRITICAL)
4. ✅ Verify common tool sequences match standards

### After Making Changes
1. ✅ Modify G-code files
2. ✅ Run **⚡ Rescan Changed** (fast, only updates modified files)
3. ✅ Check **Tool Analysis** to verify fixes
4. ✅ Confirm no new issues introduced

### Regular Maintenance
1. ✅ Weekly: Check for new safety issues
2. ✅ Monthly: Review tool usage statistics
3. ✅ Quarterly: Audit tool sequences for optimization

---

## Advanced: Tool Statistics Insights

### Analyzing Tool Usage Percentage

**High Usage (>90%):**
- T101: Almost all parts need facing → Standard operation

**Medium Usage (30-60%):**
- T121: Hub-centric and STEP parts → Selective operation

**Low Usage (<10%):**
- T303: Tapping → Special requirements
- T404: Grooving → Rare operation

### Part Type Tool Patterns

**Hub-Centric Pattern:**
```
Must have: T101, T121
Often has: T202
Sometimes: T303, T404
```

**Standard Pattern:**
```
Must have: T101
Often has: T202
Sometimes: T303
```

**STEP Pattern:**
```
Must have: T101, T121
Often has: T202
Sometimes: T303
```

Use these patterns to:
- Validate new programs
- Identify misclassified part types
- Ensure consistency across similar parts

---

## Troubleshooting

### "No tool data found"
**Cause:** Database hasn't been scanned yet
**Solution:** Run **Files** → **⚡ Rescan Changed** (or full rescan)

### Tool extraction seems incomplete
**Cause:** Non-standard tool numbering in G-code
**Solution:** Tool regex is `\bT(\d{3})\b` - only matches T### format

### Safety warnings on known-good programs
**Cause:** Different G-code format or conventions
**Solution:** This is informational - review and verify manually

### Statistics window is empty
**Cause:** No programs have tool data yet
**Solution:** Must rescan database first to populate tool data

---

## Summary

**Tool Analysis provides:**
- ✅ Comprehensive tool usage statistics
- ✅ Automatic validation of tool requirements
- ✅ Safety block verification
- ✅ Quality control before production
- ✅ Insights into tool usage patterns

**Access it:**
**Reports** tab → **🔧 Tool Analysis**

**Update data:**
**Files** tab → **⚡ Rescan Changed**

**Perfect for:**
- Quality control
- Safety auditing
- Process optimization
- Understanding your G-code library
