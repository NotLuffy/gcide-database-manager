# Fuzzy Search - User Guide

## What is Fuzzy Search?

Fuzzy search helps you find programs even when you don't remember the exact program number or title. It's forgiving with typos, missing characters, and partial matches.

## How to Use It

### Step 1: Find the Fuzzy Checkbox
Look at the top of the filter panel, you'll see:
```
🔍 Title Search: [________________] [✕] [☑ Fuzzy]
                                         ↑
                                    Check this box!
```

### Step 2: Enter Your Search
Type what you remember in the "Title Search" box

### Step 3: Check the "Fuzzy" Box
☑ Enable fuzzy matching

### Step 4: Press Enter
Results will appear, ranked by how closely they match

---

## What Can You Search For?

### 1. Program Numbers (with typos!)

| You type | It finds | Why it works |
|----------|----------|--------------|
| `o1300` | `o13002` | Finds closest match |
| `13002` | `o13002` | Missing 'o' prefix is OK |
| `130` | `o13002`, `o13890` | Partial match |
| `61045` | `o61045` | Exact match works too |
| `o6104` | `o61045` | Missing last digit |

**✅ Great for**: Quick lookups when you remember most of the program number

### 2. Dimensions in Title

| You type | It finds |
|----------|----------|
| `142/220` | "13.0 142/220MM 2.0 HC .5" |
| `142` | All programs with 142 in title |
| `63.4/80` | "6.00 DIA 63.4/80MM 1.5 HC" |
| `108/165` | "13.0 DIA 108/165MM 1.875 HC .75" |
| `1.5` | All programs with 1.5 in title |

**✅ Great for**: Finding programs by center bore, hub diameter, or thickness

### 3. Spacer Types

| You type | It finds |
|----------|----------|
| `HC` | All hub-centric programs |
| `hub` | All hub-centric programs |
| `LUG` | All lug-centric programs |
| `2PC` | All 2-piece programs |
| `STUD` | All stud programs |

**✅ Great for**: Browsing programs by type

### 4. Partial Text

| You type | It finds |
|----------|----------|
| `13.0 DIA` | "13.0 DIA ..." programs |
| `2.0 HC` | Programs with 2.0 thickness, hub-centric |
| `1.875` | Programs with 1.875 thickness |
| `.75` | Programs with .75 hub height |

**✅ Great for**: Flexible searches when you know part of the title

---

## Comparison: Exact vs Fuzzy

### Example: Looking for o13002

#### Without Fuzzy (Exact Search) ❌
- Type `o13002` → ✅ Found
- Type `o1300` → ❌ Not found
- Type `13002` → ❌ Not found (needs the 'o')
- Type `O13002` → ❌ Not found (wrong case)

#### With Fuzzy (Smart Search) ✅
- Type `o13002` → ✅ Found (100% match)
- Type `o1300` → ✅ Found (close match)
- Type `13002` → ✅ Found (missing 'o' is OK)
- Type `O13002` → ✅ Found (case insensitive)
- Type `130` → ✅ Found (partial match)

---

## Real-World Examples

### Scenario 1: "I need the 142/220 spacer"
**Without remembering the program number:**
1. Check ☑ Fuzzy
2. Type: `142/220`
3. Press Enter
4. **Result**: Finds `o13002` - "13.0 142/220MM 2.0 HC .5"

### Scenario 2: "Something like o13000-something"
**Vague memory of program number:**
1. Check ☑ Fuzzy
2. Type: `o130`
3. Press Enter
4. **Result**: Shows all programs starting with o130XX:
   - `o13002`
   - `o13004`
   - `o13890`
   - etc.

### Scenario 3: "I need all 1.5 inch thick hub-centric"
**Multiple criteria:**
1. Check ☑ Fuzzy
2. Type: `1.5 HC` (fuzzy works with multi-term search!)
3. Press Enter
4. **Result**: All 1.5" thick hub-centric spacers

### Scenario 4: "Customer called, needs 63.4 center bore"
**Search by one dimension:**
1. Check ☑ Fuzzy
2. Type: `63.4`
3. Press Enter
4. **Result**: All programs with 63.4mm center bore

---

## Tips & Tricks

### Tip 1: Start Broad, Then Narrow
- Start with `130` to see all o130XX programs
- Then add more details: `130 + HC` for hub-centric only

### Tip 2: Use the + Operator
Fuzzy search works with the `+` multi-term operator:
- `lug + 1.25 + 74` → Lug-centric, 1.25" thick, 74mm CB
- `13 + HC + 2.0` → 13" OD, hub-centric, 2.0" thick

### Tip 3: Don't Overthink Spacing
These all work the same:
- `142/220`
- `142 / 220`
- `142/220MM`

### Tip 4: Typos are OK!
- `o1300` finds `o13002`
- `63.4/80` finds exact match
- `63/80` still finds it (missing .4)

### Tip 5: Case Doesn't Matter
- `hc` = `HC` = `Hc`
- `o13002` = `O13002`

---

## When to Use Fuzzy vs Exact Search

### Use Fuzzy Search When:
- ✅ You don't remember exact program number
- ✅ You're searching by dimensions or features
- ✅ You want to see similar programs
- ✅ You're browsing by category
- ✅ You have a typo in your notes

### Use Exact Search When:
- ✅ You know the exact program number
- ✅ You need very precise filtering
- ✅ You're using complex multi-term searches with +
- ✅ You want only exact substring matches

---

## How It Works (Technical)

Fuzzy search uses the **Levenshtein distance** algorithm to calculate similarity between strings:

1. **For program numbers**: Uses strict matching (60-100% similarity)
   - Searches program number field directly
   - Lower threshold for short queries

2. **For titles**: Uses partial matching (70-100% similarity)
   - Searches combined "program_number + title" field
   - More forgiving with longer text

3. **Results are ranked**: Higher similarity scores appear first
   - 100% = Perfect match
   - 90-99% = Very close
   - 70-89% = Good match
   - < 70% = Not shown (below threshold)

---

## Performance

- **Fast**: Searches 1000+ programs in under 200ms
- **Smart**: Only runs when checkbox is enabled
- **Efficient**: Applied after SQL query, not during

---

## Troubleshooting

### "Fuzzy search doesn't find anything"
- Make sure the **☑ Fuzzy** checkbox is checked
- Try a shorter search term (e.g., `130` instead of `o13002xxx`)
- Try searching just one dimension (e.g., `142` instead of full title)

### "Too many results"
- Use the `+` operator to combine terms: `130 + HC`
- Use other filters (Type, Material, Status) to narrow down
- Be more specific in your search

### "Results seem random"
- Results are ranked by similarity score
- Top results are closest matches
- Scroll down to see lower-scoring matches

---

## Examples to Try Right Now

Copy these into the Title Search box with **☑ Fuzzy** enabled:

1. `o1300` → See what matches
2. `142` → See all programs with 142
3. `HC` → See all hub-centric programs
4. `1.5` → See all 1.5" programs
5. `63.4/80` → Find specific dimension
6. Your actual program numbers with typos! 😊

---

**Pro Tip**: Keep Fuzzy enabled most of the time. It doesn't hurt exact searches, and it makes finding programs much easier!
