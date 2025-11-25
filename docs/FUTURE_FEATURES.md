# Future Features - Roadmap

Features to implement after database and parsing are fully trained and stable.

---

## 3D Model Generation

**Description:**
Generate 3D models based on selected G-code file dimensions.

**Details:**
- Read dimensions from database (OD, thickness, CB, hub height, hub diameter, etc.)
- Generate 3D model file (STL, STEP, or similar format)
- Allow user to select a file and generate its 3D representation
- Useful for:
  - Visual verification of part geometry
  - Documentation
  - Customer presentations
  - Assembly planning

**Prerequisites:**
- Database parsing must be accurate and reliable
- All dimensional data properly extracted and validated
- May need library like `cadquery`, `build123d`, or similar for 3D generation

**Status:** 📋 Planned for future implementation

---

## Lug and Stud Generator

**Description:**
Use existing database dimensions to generate G-code for lug and stud features.

**Details:**
- Leverage current parsing and dimensional data
- Generate G-code for:
  - Lug features (mounting tabs/ears)
  - Stud holes/threads
  - Based on selected spacer dimensions
- Further develop existing G-code generation capabilities
- Could use templates + dimension substitution
- Integration with main database GUI (right-click → "Generate Lug/Stud")

**Prerequisites:**
- Database parsing accurate and stable
- Understanding of lug/stud dimensional relationships to spacer geometry
- G-code generation templates/logic

**Status:** 📋 Planned for future implementation

---

## Additional Future Features

_Add more features here as they are identified..._

