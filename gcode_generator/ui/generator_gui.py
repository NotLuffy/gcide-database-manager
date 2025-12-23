"""
G-Code Generator GUI

Standalone Tkinter GUI for generating G-code for wheel spacers.
Can be run independently or integrated into the database manager.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import sys

# Add the File organizer directory to path for proper imports
file_organizer_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if file_organizer_dir not in sys.path:
    sys.path.insert(0, file_organizer_dir)

from gcode_generator.generator import GCodeGenerator, SpacerType
from gcode_generator.rules.lathe_config import LatheConfig


class GCodeGeneratorGUI:
    """Main GUI application for G-code generation."""

    def __init__(self, root: tk.Tk, db_path: str = None):
        """
        Initialize the GUI.

        Args:
            root: Tkinter root window
            db_path: Optional path to database for template matching
        """
        self.root = root
        self.root.title("G-Code Generator V2.0 - Wheel Spacers")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)

        # Initialize generator
        self.generator = GCodeGenerator(use_templates=bool(db_path), db_path=db_path)

        # Variables
        self.spacer_type_var = tk.StringVar(value="standard")
        self.program_number_var = tk.StringVar()
        self.round_size_var = tk.StringVar()
        self.thickness_var = tk.StringVar()
        self.cb_var = tk.StringVar()
        self.ob_var = tk.StringVar()
        self.hub_height_var = tk.StringVar()
        self.counterbore_var = tk.StringVar()
        self.step_depth_var = tk.StringVar()
        self.lathe_var = tk.StringVar(value="auto")
        self.use_tolerance_var = tk.BooleanVar(value=True)
        self.use_calculated_var = tk.BooleanVar(value=False)
        self.is_male_var = tk.BooleanVar(value=True)

        # Generated G-code storage
        self.generated_gcode = ""

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - inputs
        left_frame = ttk.LabelFrame(main_frame, text="Part Parameters", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # Right panel - preview
        right_frame = ttk.LabelFrame(main_frame, text="G-Code Preview", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Build input sections
        self._build_spacer_type_section(left_frame)
        self._build_basic_inputs(left_frame)
        self._build_hub_centric_inputs(left_frame)
        self._build_step_inputs(left_frame)
        self._build_two_piece_inputs(left_frame)
        self._build_options(left_frame)
        self._build_buttons(left_frame)

        # Build preview section
        self._build_preview(right_frame)

        # Initial visibility update
        self._update_field_visibility()

    def _build_spacer_type_section(self, parent):
        """Build spacer type selection."""
        frame = ttk.LabelFrame(parent, text="Spacer Type", padding="5")
        frame.pack(fill=tk.X, pady=(0, 10))

        types = [
            ("Standard", "standard"),
            ("Hub-Centric", "hub_centric"),
            ("Thin-Lip HC", "thin_lip"),
            ("STEP", "step"),
            ("Steel Ring", "steel_ring"),
            ("2-Piece", "two_piece"),
        ]

        for i, (text, value) in enumerate(types):
            rb = ttk.Radiobutton(
                frame, text=text, value=value,
                variable=self.spacer_type_var,
                command=self._update_field_visibility
            )
            rb.grid(row=i // 3, column=i % 3, sticky=tk.W, padx=5, pady=2)

    def _build_basic_inputs(self, parent):
        """Build basic input fields."""
        frame = ttk.LabelFrame(parent, text="Basic Dimensions", padding="5")
        frame.pack(fill=tk.X, pady=(0, 10))

        # Program Number
        ttk.Label(frame, text="Program Number:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.program_number_var, width=15).grid(
            row=0, column=1, sticky=tk.W, pady=2
        )
        ttk.Label(frame, text="(e.g., O12345)").grid(row=0, column=2, sticky=tk.W, padx=5)

        # Round Size
        ttk.Label(frame, text="Round Size (in):").grid(row=1, column=0, sticky=tk.W, pady=2)
        round_combo = ttk.Combobox(
            frame, textvariable=self.round_size_var, width=12,
            values=LatheConfig.get_all_round_sizes()
        )
        round_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Thickness
        ttk.Label(frame, text="Thickness:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.thickness_var, width=15).grid(
            row=2, column=1, sticky=tk.W, pady=2
        )
        ttk.Label(frame, text="(e.g., 1.50 or 15MM)").grid(row=2, column=2, sticky=tk.W, padx=5)

        # Center Bore
        ttk.Label(frame, text="Center Bore (mm):").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.cb_var, width=15).grid(
            row=3, column=1, sticky=tk.W, pady=2
        )

        # Lathe
        ttk.Label(frame, text="Lathe:").grid(row=4, column=0, sticky=tk.W, pady=2)
        lathe_combo = ttk.Combobox(
            frame, textvariable=self.lathe_var, width=12,
            values=["auto", "L1", "L2", "L3"]
        )
        lathe_combo.grid(row=4, column=1, sticky=tk.W, pady=2)

    def _build_hub_centric_inputs(self, parent):
        """Build hub-centric specific inputs."""
        self.hc_frame = ttk.LabelFrame(parent, text="Hub-Centric Options", padding="5")
        self.hc_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(self.hc_frame, text="Outer Bore (mm):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.hc_frame, textvariable=self.ob_var, width=15).grid(
            row=0, column=1, sticky=tk.W, pady=2
        )

        ttk.Label(self.hc_frame, text="Hub Height (in):").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.hc_frame, textvariable=self.hub_height_var, width=15).grid(
            row=1, column=1, sticky=tk.W, pady=2
        )

    def _build_step_inputs(self, parent):
        """Build STEP spacer specific inputs."""
        self.step_frame = ttk.LabelFrame(parent, text="STEP Options", padding="5")
        self.step_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(self.step_frame, text="Counterbore (mm):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.step_frame, textvariable=self.counterbore_var, width=15).grid(
            row=0, column=1, sticky=tk.W, pady=2
        )

        ttk.Label(self.step_frame, text="Step Depth (in):").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.step_frame, textvariable=self.step_depth_var, width=15).grid(
            row=1, column=1, sticky=tk.W, pady=2
        )

    def _build_two_piece_inputs(self, parent):
        """Build 2-piece specific inputs."""
        self.tp_frame = ttk.LabelFrame(parent, text="2-Piece Options", padding="5")
        self.tp_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Radiobutton(
            self.tp_frame, text="Male Piece", value=True,
            variable=self.is_male_var
        ).grid(row=0, column=0, sticky=tk.W, pady=2)

        ttk.Radiobutton(
            self.tp_frame, text="Female Piece", value=False,
            variable=self.is_male_var
        ).grid(row=0, column=1, sticky=tk.W, pady=2)

    def _build_options(self, parent):
        """Build options section."""
        frame = ttk.LabelFrame(parent, text="Options", padding="5")
        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            frame, text="Apply Tolerances (CB +0.1mm, OB -0.1mm)",
            variable=self.use_tolerance_var
        ).pack(anchor=tk.W)

        ttk.Checkbutton(
            frame, text="Use Calculated Feeds/Speeds",
            variable=self.use_calculated_var
        ).pack(anchor=tk.W)

    def _build_buttons(self, parent):
        """Build action buttons."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=10)

        ttk.Button(frame, text="Generate G-Code", command=self._generate).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(frame, text="Save to File", command=self._save).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(frame, text="Clear", command=self._clear).pack(
            side=tk.LEFT, padx=5
        )

    def _build_preview(self, parent):
        """Build preview section."""
        self.preview_text = scrolledtext.ScrolledText(
            parent, wrap=tk.NONE, font=("Consolas", 10)
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # Add horizontal scrollbar
        h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.preview_text.xview)
        h_scroll.pack(fill=tk.X)
        self.preview_text.configure(xscrollcommand=h_scroll.set)

    def _update_field_visibility(self):
        """Show/hide fields based on spacer type."""
        spacer_type = self.spacer_type_var.get()

        # Hub-centric fields
        if spacer_type in ["hub_centric", "thin_lip"]:
            self.hc_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.hc_frame.pack_forget()

        # STEP fields
        if spacer_type == "step":
            self.step_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.step_frame.pack_forget()

        # Two-piece fields
        if spacer_type == "two_piece":
            self.tp_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            self.tp_frame.pack_forget()

    def _validate_inputs(self) -> bool:
        """Validate user inputs."""
        errors = []

        if not self.program_number_var.get().strip():
            errors.append("Program number is required")

        if not self.round_size_var.get().strip():
            errors.append("Round size is required")
        else:
            try:
                float(self.round_size_var.get())
            except ValueError:
                errors.append("Round size must be a number")

        if not self.thickness_var.get().strip():
            errors.append("Thickness is required")

        if not self.cb_var.get().strip():
            errors.append("Center bore is required")
        else:
            try:
                float(self.cb_var.get())
            except ValueError:
                errors.append("Center bore must be a number")

        spacer_type = self.spacer_type_var.get()

        if spacer_type in ["hub_centric", "thin_lip"]:
            if not self.ob_var.get().strip():
                errors.append("Outer bore is required for hub-centric")
            if not self.hub_height_var.get().strip():
                errors.append("Hub height is required for hub-centric")

        if spacer_type == "step":
            if not self.counterbore_var.get().strip():
                errors.append("Counterbore is required for STEP")
            if not self.step_depth_var.get().strip():
                errors.append("Step depth is required for STEP")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False

        return True

    def _generate(self):
        """Generate G-code."""
        if not self._validate_inputs():
            return

        try:
            spacer_type = self.spacer_type_var.get()
            lathe = self.lathe_var.get()
            if lathe == "auto":
                lathe = None

            kwargs = {
                "spacer_type": spacer_type,
                "program_number": self.program_number_var.get().strip(),
                "round_size": float(self.round_size_var.get()),
                "thickness": self.thickness_var.get().strip(),
                "cb_mm": float(self.cb_var.get()),
                "lathe": lathe,
                "use_tolerance": self.use_tolerance_var.get(),
                "use_calculated_feeds": self.use_calculated_var.get(),
            }

            # Add type-specific parameters
            if spacer_type in ["hub_centric", "thin_lip"]:
                kwargs["ob_mm"] = float(self.ob_var.get())
                kwargs["hub_height"] = float(self.hub_height_var.get())

            if spacer_type == "step":
                kwargs["counterbore_mm"] = float(self.counterbore_var.get())
                kwargs["step_depth"] = float(self.step_depth_var.get())

            if spacer_type == "two_piece":
                kwargs["is_male_piece"] = self.is_male_var.get()

            # Generate
            self.generated_gcode = self.generator.generate(**kwargs)

            # Display in preview
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", self.generated_gcode)

            messagebox.showinfo("Success", "G-code generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Generation failed:\n{str(e)}")

    def _save(self):
        """Save generated G-code to file."""
        if not self.generated_gcode:
            messagebox.showwarning("Warning", "Generate G-code first!")
            return

        program_num = self.program_number_var.get().strip().upper()
        if not program_num.startswith('O'):
            program_num = 'O' + program_num

        default_filename = f"{program_num}.nc"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".nc",
            filetypes=[("NC Files", "*.nc"), ("All Files", "*.*")],
            initialfile=default_filename,
        )

        if filepath:
            try:
                gcode_ascii = self.generated_gcode.encode('ascii', 'replace').decode('ascii')
                with open(filepath, 'w', encoding='ascii') as f:
                    f.write(gcode_ascii)
                messagebox.showinfo("Success", f"Saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed:\n{str(e)}")

    def _clear(self):
        """Clear all inputs and preview."""
        self.program_number_var.set("")
        self.round_size_var.set("")
        self.thickness_var.set("")
        self.cb_var.set("")
        self.ob_var.set("")
        self.hub_height_var.set("")
        self.counterbore_var.set("")
        self.step_depth_var.set("")
        self.preview_text.delete("1.0", tk.END)
        self.generated_gcode = ""


def main():
    """Main entry point for standalone GUI."""
    root = tk.Tk()

    # Check for database path argument
    db_path = None
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    app = GCodeGeneratorGUI(root, db_path)
    root.mainloop()


if __name__ == "__main__":
    main()
