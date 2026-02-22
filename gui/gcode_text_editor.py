"""
G-Code Text Editor
Integrated text editor with validation and auto-backup support.

Features:
- Line numbers synchronized with text content
- Syntax highlighting for G-code elements
- Find/Replace dialog
- Error line highlighting
- Animation/playback controls
- Dark theme matching existing UI
- Validation on save (improved_gcode_parser)
- Auto-backup before saving (repository_manager)
- Undo/redo support
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import os
import re
from datetime import datetime
from typing import Optional, Callable, List
import logging

logger = logging.getLogger(__name__)


class FindReplaceDialog:
    """Find and Replace dialog for text editor"""

    def __init__(self, parent, text_widget):
        """Initialize Find/Replace dialog"""
        self.text_widget = text_widget
        self.last_search_pos = '1.0'

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Find/Replace")
        self.dialog.geometry("500x200")
        self.dialog.transient(parent)
        self.dialog.configure(bg='#1e1e1e')

        # Find frame
        find_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        find_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(find_frame, text="Find:", bg='#1e1e1e', fg='#d4d4d4',
                font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)

        self.find_entry = tk.Entry(find_frame, bg='#2d2d30', fg='#d4d4d4',
                                   font=('Consolas', 10), insertbackground='white')
        self.find_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Replace frame
        replace_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        replace_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(replace_frame, text="Replace:", bg='#1e1e1e', fg='#d4d4d4',
                font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)

        self.replace_entry = tk.Entry(replace_frame, bg='#2d2d30', fg='#d4d4d4',
                                      font=('Consolas', 10), insertbackground='white')
        self.replace_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Options frame
        options_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        self.case_sensitive = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="Case Sensitive",
                      variable=self.case_sensitive,
                      bg='#1e1e1e', fg='#d4d4d4',
                      selectcolor='#2d2d30',
                      font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)

        # Button frame
        button_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(button_frame, text="Find Next", command=self.find_next,
                 bg='#4a90e2', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(button_frame, text="Replace", command=self.replace_current,
                 bg='#28a745', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(button_frame, text="Replace All", command=self.replace_all,
                 bg='#ffc107', fg='black', font=('Segoe UI', 9),
                 padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(button_frame, text="Close", command=self.dialog.destroy,
                 bg='#6c757d', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=3).pack(side=tk.RIGHT, padx=2)

        # Bind Enter key
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        self.find_entry.focus_set()

    def find_next(self):
        """Find next occurrence of search term"""
        search_term = self.find_entry.get()
        if not search_term:
            return

        # Remove previous selection
        self.text_widget.tag_remove('sel', '1.0', tk.END)

        # Search options
        nocase = 1 if not self.case_sensitive.get() else 0

        # Search from last position
        pos = self.text_widget.search(search_term, self.last_search_pos,
                                      stopindex=tk.END, nocase=nocase)

        if not pos:
            # Wrap around to beginning
            pos = self.text_widget.search(search_term, '1.0',
                                         stopindex=tk.END, nocase=nocase)
            if not pos:
                messagebox.showinfo("Not Found", f"'{search_term}' not found.")
                return

        # Highlight found text
        end_pos = f"{pos}+{len(search_term)}c"
        self.text_widget.tag_add('sel', pos, end_pos)
        self.text_widget.mark_set('insert', end_pos)
        self.text_widget.see(pos)

        # Update last search position
        self.last_search_pos = end_pos

    def replace_current(self):
        """Replace currently selected occurrence"""
        try:
            selection = self.text_widget.get('sel.first', 'sel.last')
            replace_text = self.replace_entry.get()

            self.text_widget.delete('sel.first', 'sel.last')
            self.text_widget.insert('insert', replace_text)

            # Find next occurrence
            self.find_next()
        except tk.TclError:
            # No selection
            messagebox.showinfo("No Selection", "No text selected. Use 'Find Next' first.")

    def replace_all(self):
        """Replace all occurrences"""
        search_term = self.find_entry.get()
        replace_text = self.replace_entry.get()

        if not search_term:
            return

        # Count replacements
        count = 0
        nocase = 1 if not self.case_sensitive.get() else 0

        # Start from beginning
        pos = '1.0'
        while True:
            pos = self.text_widget.search(search_term, pos,
                                         stopindex=tk.END, nocase=nocase)
            if not pos:
                break

            end_pos = f"{pos}+{len(search_term)}c"
            self.text_widget.delete(pos, end_pos)
            self.text_widget.insert(pos, replace_text)
            count += 1

            # Move to next position
            pos = f"{pos}+{len(replace_text)}c"

        messagebox.showinfo("Replace All",
                           f"Replaced {count} occurrence(s) of '{search_term}'")


class LineNumberCanvas(tk.Canvas):
    """Canvas widget to display line numbers alongside text widget"""

    def __init__(self, parent, text_widget=None, **kwargs):
        """
        Initialize line number canvas.

        Args:
            parent: Parent widget
            text_widget: Text widget to track (can be set later)
            **kwargs: Additional canvas parameters
        """
        super().__init__(parent, width=50, bg='#2d2d30',
                        highlightthickness=0, **kwargs)
        self.text_widget = text_widget

    def redraw(self, *args):
        """Redraw line numbers when text changes"""
        self.delete("all")

        if not self.text_widget:
            return

        # Get the line number of the first visible line
        i = self.text_widget.index("@0,0")

        while True:
            # Get display info for this line
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break

            # Extract y coordinate and line number
            y = dline[1]
            linenum = str(i).split(".")[0]

            # Draw line number
            self.create_text(2, y, anchor="nw", text=linenum,
                           fill='#858585', font=('Consolas', 9))

            # Move to next line
            i = self.text_widget.index(f"{i}+1line")


class GCodeTextEditor:
    """Modal text editor for G-code files with validation and backup"""

    def __init__(self, parent, file_path: str, program_number: str,
                 on_save_callback: Optional[Callable] = None,
                 bg_color: str = '#1e1e1e', fg_color: str = '#d4d4d4',
                 repository_manager = None,
                 crash_lines: list = None):
        """
        Initialize G-code text editor.

        Args:
            parent: Parent window
            file_path: Path to G-code file
            program_number: Program number (for backup)
            on_save_callback: Function to call after successful save
            bg_color: Background color
            fg_color: Foreground color
            repository_manager: RepositoryManager instance for versioning
            crash_lines: Line numbers of known crash risks to highlight on open
        """
        self.file_path = file_path
        self.program_number = program_number
        self.on_save_callback = on_save_callback
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.repository_manager = repository_manager
        self.modified = False
        self.original_content = ""
        self.error_lines = list(crash_lines) if crash_lines else []
        self.current_playback_line = 1  # Current line for playback
        self.syntax_highlighting_enabled = True

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit G-Code: {program_number}")
        self.dialog.geometry("1200x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=bg_color)

        # Load file content
        self._load_file()

        # Create UI
        self._create_ui()

        # If crash lines were passed, scroll to the first one after the UI renders
        if self.error_lines:
            self.dialog.after(200, self._scroll_to_first_error)

        # Bind close event
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_file(self):
        """Load file content"""
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.original_content = f.read()
        except Exception as e:
            messagebox.showerror("Error Loading File",
                               f"Failed to load file:\n{str(e)}")
            self.original_content = ""

    def _create_ui(self):
        """Build editor interface"""
        # Title bar with file info
        header = tk.Frame(self.dialog, bg='#2d2d30', pady=10)
        header.pack(fill=tk.X)

        # File title
        title_text = f"Editing: {self.program_number} - {os.path.basename(self.file_path)}"
        tk.Label(header,
                text=title_text,
                bg='#2d2d30', fg='#ffffff',
                font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT, padx=10)

        # Status indicator
        self.status_label = tk.Label(header, text="",
                                    bg='#2d2d30', fg='#ffc107',
                                    font=('Segoe UI', 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Editor frame with line numbers
        editor_frame = tk.Frame(self.dialog, bg=self.bg_color)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Line numbers
        self.line_numbers = LineNumberCanvas(editor_frame, None)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Text widget
        self.text_widget = tk.Text(
            editor_frame,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground='#ffffff',
            font=('Consolas', 10),
            wrap=tk.NONE,
            undo=True,
            maxundo=-1,
            tabs='4'  # 4-space tabs
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.line_numbers.text_widget = self.text_widget

        # Configure syntax highlighting tags
        self._configure_text_tags()

        # Insert initial content
        self.text_widget.insert('1.0', self.original_content)
        self.text_widget.edit_reset()  # Reset undo stack

        # Apply initial syntax highlighting
        self._apply_syntax_highlighting()

        # Scrollbars
        vscroll = tk.Scrollbar(editor_frame, orient=tk.VERTICAL,
                              command=self._on_scroll)
        hscroll = tk.Scrollbar(self.dialog, orient=tk.HORIZONTAL,
                              command=self.text_widget.xview)
        self.text_widget.config(yscrollcommand=vscroll.set,
                              xscrollcommand=hscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        hscroll.pack(fill=tk.X, padx=10)

        # Bind events for line number updates
        self.text_widget.bind('<<Modified>>', self._on_text_modified)
        self.text_widget.bind('<KeyRelease>', lambda e: self.line_numbers.redraw())
        self.text_widget.bind('<MouseWheel>', lambda e: self.line_numbers.redraw())
        self.text_widget.bind('<Button-1>', lambda e: self.line_numbers.redraw())

        # Bind keyboard shortcuts
        self.text_widget.bind('<Control-s>', lambda e: self.save_file())
        self.text_widget.bind('<Control-S>', lambda e: self.save_file())
        self.text_widget.bind('<Control-f>', lambda e: self.show_find_dialog())
        self.text_widget.bind('<Control-F>', lambda e: self.show_find_dialog())
        self.dialog.bind('<Escape>', lambda e: self._on_close())

        # Bottom toolbar
        self._create_toolbar()

        # Initial line number draw
        self.dialog.after(100, self.line_numbers.redraw)

    def _on_scroll(self, *args):
        """Handle scrollbar interaction"""
        self.text_widget.yview(*args)
        self.line_numbers.redraw()

    def _on_text_modified(self, event=None):
        """Handle text modification"""
        if self.text_widget.edit_modified():
            self.modified = True
            self.status_label.config(text="Modified *", fg='#ffc107')
            self.text_widget.edit_modified(False)

            # Reapply syntax highlighting after modification
            if self.syntax_highlighting_enabled:
                self.dialog.after(100, self._apply_syntax_highlighting)

    def _configure_text_tags(self):
        """Configure text tags for syntax highlighting and error display"""
        # Syntax highlighting tags
        self.text_widget.tag_config('gcode', foreground='#4FC1FF')  # Blue - G-codes
        self.text_widget.tag_config('mcode', foreground='#C586C0')  # Purple - M-codes
        self.text_widget.tag_config('tcode', foreground='#4EC9B0')  # Teal - Tool numbers
        self.text_widget.tag_config('comment', foreground='#6A9955')  # Green - Comments
        self.text_widget.tag_config('coordinate', foreground='#DCDCAA')  # Yellow - Coordinates
        self.text_widget.tag_config('program', foreground='#CE9178')  # Orange - Program numbers

        # Error highlighting (highest priority)
        self.text_widget.tag_config('error', background='#3d1f1f', foreground='#ff6b6b')
        self.text_widget.tag_raise('error')

        # Playback highlight
        self.text_widget.tag_config('playback', background='#264f78', foreground='#ffffff')
        self.text_widget.tag_raise('playback')

    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting to entire text"""
        if not self.syntax_highlighting_enabled:
            return

        # Remove all syntax tags
        for tag in ['gcode', 'mcode', 'tcode', 'comment', 'coordinate', 'program']:
            self.text_widget.tag_remove(tag, '1.0', tk.END)

        content = self.text_widget.get('1.0', 'end-1c')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Comments (entire line or inline)
            if '(' in line:
                comment_start = line.index('(')
                self.text_widget.tag_add('comment',
                                        f"{line_num}.{comment_start}",
                                        f"{line_num}.end")
                # Only process non-comment part for other patterns
                line = line[:comment_start]

            # Program numbers (O followed by digits)
            for match in re.finditer(r'\bO\d+', line, re.IGNORECASE):
                start, end = match.span()
                self.text_widget.tag_add('program',
                                        f"{line_num}.{start}",
                                        f"{line_num}.{end}")

            # G-codes (G followed by digits/decimals)
            for match in re.finditer(r'\bG\d+\.?\d*', line, re.IGNORECASE):
                start, end = match.span()
                self.text_widget.tag_add('gcode',
                                        f"{line_num}.{start}",
                                        f"{line_num}.{end}")

            # M-codes (M followed by digits)
            for match in re.finditer(r'\bM\d+', line, re.IGNORECASE):
                start, end = match.span()
                self.text_widget.tag_add('mcode',
                                        f"{line_num}.{start}",
                                        f"{line_num}.{end}")

            # Tool numbers (T followed by digits)
            for match in re.finditer(r'\bT\d+', line, re.IGNORECASE):
                start, end = match.span()
                self.text_widget.tag_add('tcode',
                                        f"{line_num}.{start}",
                                        f"{line_num}.{end}")

            # Coordinates (X, Y, Z, I, J, K, R, F, S followed by numbers)
            for match in re.finditer(r'\b[XYZIJKRFS]-?\d+\.?\d*', line, re.IGNORECASE):
                start, end = match.span()
                self.text_widget.tag_add('coordinate',
                                        f"{line_num}.{start}",
                                        f"{line_num}.{end}")

        # Reapply error highlighting if present
        self._highlight_error_lines()

    def _highlight_error_lines(self):
        """Highlight lines with validation errors"""
        self.text_widget.tag_remove('error', '1.0', tk.END)
        for line_num in self.error_lines:
            self.text_widget.tag_add('error',
                                    f"{line_num}.0",
                                    f"{line_num}.end")

    def _scroll_to_first_error(self):
        """Highlight crash-risk lines and scroll to the first one."""
        self._highlight_error_lines()
        self.line_numbers.redraw()
        if self.error_lines:
            first = min(self.error_lines)
            self.text_widget.see(f"{first}.0")
            # Centre the line in the viewport
            self.text_widget.mark_set("insert", f"{first}.0")
            self.line_numbers.redraw()

    def show_find_dialog(self):
        """Show Find/Replace dialog"""
        FindReplaceDialog(self.dialog, self.text_widget)

    def goto_first_line(self):
        """Jump to first line"""
        self.current_playback_line = 1
        self._highlight_playback_line()

    def goto_last_line(self):
        """Jump to last line"""
        content = self.text_widget.get('1.0', 'end-1c')
        total_lines = len(content.split('\n'))
        self.current_playback_line = total_lines
        self._highlight_playback_line()

    def goto_next_line(self):
        """Move to next line"""
        content = self.text_widget.get('1.0', 'end-1c')
        total_lines = len(content.split('\n'))

        if self.current_playback_line < total_lines:
            self.current_playback_line += 1
            self._highlight_playback_line()

    def goto_prev_line(self):
        """Move to previous line"""
        if self.current_playback_line > 1:
            self.current_playback_line -= 1
            self._highlight_playback_line()

    def _highlight_playback_line(self):
        """Highlight current playback line"""
        # Remove previous playback highlight
        self.text_widget.tag_remove('playback', '1.0', tk.END)

        # Highlight current line
        line_num = self.current_playback_line
        self.text_widget.tag_add('playback',
                                f"{line_num}.0",
                                f"{line_num}.end")

        # Scroll to make line visible
        self.text_widget.see(f"{line_num}.0")

        # Update status
        content = self.text_widget.get('1.0', 'end-1c')
        total_lines = len(content.split('\n'))
        self.status_label.config(
            text=f"Line {line_num}/{total_lines}",
            fg='#4a90e2'
        )

    def _create_toolbar(self):
        """Create bottom toolbar with buttons"""
        toolbar = tk.Frame(self.dialog, bg='#2d2d30', pady=10)
        toolbar.pack(fill=tk.X, padx=10)

        # Left side - action buttons
        left_frame = tk.Frame(toolbar, bg='#2d2d30')
        left_frame.pack(side=tk.LEFT)

        tk.Button(
            left_frame,
            text="💾 Save",
            command=self.save_file,
            bg='#28a745',
            fg='#ffffff',
            font=('Segoe UI', 10, 'bold'),
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            left_frame,
            text="✓ Validate",
            command=self.validate_only,
            bg='#4a90e2',
            fg='#ffffff',
            font=('Segoe UI', 10),
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            left_frame,
            text="🔍 Find",
            command=self.show_find_dialog,
            bg='#6c757d',
            fg='#ffffff',
            font=('Segoe UI', 10),
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        # Playback controls
        playback_frame = tk.Frame(toolbar, bg='#2d2d30')
        playback_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(playback_frame, text="Playback:",
                bg='#2d2d30', fg='#d4d4d4',
                font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)

        tk.Button(
            playback_frame,
            text="⏮ First",
            command=self.goto_first_line,
            bg='#6c757d',
            fg='#ffffff',
            font=('Segoe UI', 9),
            padx=8,
            pady=3
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            playback_frame,
            text="◀ Prev",
            command=self.goto_prev_line,
            bg='#6c757d',
            fg='#ffffff',
            font=('Segoe UI', 9),
            padx=8,
            pady=3
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            playback_frame,
            text="▶ Next",
            command=self.goto_next_line,
            bg='#6c757d',
            fg='#ffffff',
            font=('Segoe UI', 9),
            padx=8,
            pady=3
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            playback_frame,
            text="⏭ Last",
            command=self.goto_last_line,
            bg='#6c757d',
            fg='#ffffff',
            font=('Segoe UI', 9),
            padx=8,
            pady=3
        ).pack(side=tk.LEFT, padx=2)

        # Right side - close button
        tk.Button(
            toolbar,
            text="Close",
            command=self._on_close,
            bg='#6c757d',
            fg='#ffffff',
            font=('Segoe UI', 10),
            padx=15,
            pady=5
        ).pack(side=tk.RIGHT, padx=5)

    def validate_only(self):
        """Validate G-code without saving"""
        content = self.text_widget.get('1.0', 'end-1c')

        # Write to temp file for validation
        temp_path = self.file_path + '.validate.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Validate
            validation_result = self._validate_gcode(temp_path)

            # Extract error line numbers and highlight them
            self.error_lines = validation_result['error_lines']
            self._highlight_error_lines()

            # Clean up temp file
            os.remove(temp_path)

            # Show results
            if validation_result['has_critical_errors']:
                error_text = "\n".join(validation_result['critical_errors'][:10])
                if len(validation_result['critical_errors']) > 10:
                    error_text += f"\n\n... and {len(validation_result['critical_errors']) - 10} more errors"

                error_text += f"\n\n{len(self.error_lines)} line(s) highlighted in red."

                messagebox.showerror(
                    "Validation Errors",
                    f"Found {len(validation_result['critical_errors'])} critical errors:\n\n{error_text}"
                )
            elif validation_result['warnings']:
                warning_text = "\n".join(validation_result['warnings'][:10])
                if len(validation_result['warnings']) > 10:
                    warning_text += f"\n\n... and {len(validation_result['warnings']) - 10} more warnings"

                messagebox.showwarning(
                    "Validation Warnings",
                    f"Found {len(validation_result['warnings'])} warnings:\n\n{warning_text}"
                )
            else:
                messagebox.showinfo(
                    "Validation Passed",
                    "G-code validation passed with no errors!"
                )
                self.status_label.config(text="Validation passed ✓", fg='#28a745')

        except Exception as e:
            messagebox.showerror("Validation Error", f"Failed to validate:\n{str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def save_file(self):
        """Save file with validation and backup"""
        content = self.text_widget.get('1.0', 'end-1c')

        # Create backup before saving
        if self.repository_manager and os.path.exists(self.file_path):
            try:
                backup_path = self.repository_manager.archive_old_file(
                    old_file_path=self.file_path,
                    program_number=self.program_number,
                    reason='edit_backup'
                )
                if backup_path:
                    logger.info(f"Auto-backup created: {backup_path}")
                    self.status_label.config(
                        text=f"Backup: {os.path.basename(backup_path)}",
                        fg='#28a745'
                    )
            except Exception as e:
                # Don't block save if backup fails
                logger.warning(f"Backup failed: {e}")
                messagebox.showwarning(
                    "Backup Warning",
                    f"Auto-backup failed:\n{str(e)}\n\nContinue saving anyway?"
                )

        # Write to temp file first
        temp_path = self.file_path + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to write file:\n{str(e)}")
            return

        # Validate G-code
        validation_result = self._validate_gcode(temp_path)

        if validation_result['has_critical_errors']:
            error_text = "\n".join(validation_result['critical_errors'][:5])
            if len(validation_result['critical_errors']) > 5:
                error_text += f"\n\n... and {len(validation_result['critical_errors']) - 5} more"

            response = messagebox.askyesno(
                "Validation Errors",
                f"Critical validation errors detected:\n\n{error_text}\n\nSave anyway?"
            )
            if not response:
                os.remove(temp_path)
                return

        # Replace original file
        try:
            os.replace(temp_path, self.file_path)
            self.modified = False
            self.original_content = content
            self.status_label.config(text="Saved successfully ✓", fg='#28a745')

            # Call callback to refresh database
            if self.on_save_callback:
                self.on_save_callback()

            messagebox.showinfo("Saved", f"File saved successfully:\n{os.path.basename(self.file_path)}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save:\n{str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _validate_gcode(self, file_path: str) -> dict:
        """
        Run improved_gcode_parser validation.

        Args:
            file_path: Path to file to validate

        Returns:
            Dict with validation results
        """
        try:
            from improved_gcode_parser import ImprovedGCodeParser

            parser = ImprovedGCodeParser()
            result = parser.parse_file(file_path)

            # Collect errors
            critical_errors = []
            if result.validation_issues:
                critical_errors.extend(result.validation_issues)
            if result.crash_issues:
                critical_errors.extend(result.crash_issues)

            # Collect warnings
            warnings = []
            if result.validation_warnings:
                warnings.extend(result.validation_warnings)
            if result.bore_warnings:
                warnings.extend(result.bore_warnings)
            if result.crash_warnings:
                warnings.extend(result.crash_warnings)

            # Extract line numbers from error/warning messages
            error_lines = self._extract_line_numbers(critical_errors + warnings)

            return {
                'has_critical_errors': len(critical_errors) > 0,
                'critical_errors': critical_errors,
                'warnings': warnings,
                'error_lines': error_lines,
                'result': result
            }
        except Exception as e:
            logger.error(f"Parser error: {e}")
            return {
                'has_critical_errors': True,
                'critical_errors': [f"Parser error: {str(e)}"],
                'warnings': [],
                'error_lines': [],
                'result': None
            }

    def _extract_line_numbers(self, messages: List[str]) -> List[int]:
        """
        Extract line numbers from validation messages.

        Args:
            messages: List of error/warning messages

        Returns:
            List of line numbers
        """
        line_numbers = []
        for msg in messages:
            # Look for "Line X:" pattern
            match = re.search(r'Line (\d+):', msg)
            if match:
                line_num = int(match.group(1))
                if line_num not in line_numbers:
                    line_numbers.append(line_num)
        return sorted(line_numbers)

    def _on_close(self):
        """Handle window close"""
        current_content = self.text_widget.get('1.0', 'end-1c')

        if current_content != self.original_content:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?"
            )

            if response is None:  # Cancel
                return
            elif response:  # Yes - save
                self.save_file()
                # Only close if save was successful
                if not self.modified:
                    self.dialog.destroy()
            else:  # No - don't save
                self.dialog.destroy()
        else:
            self.dialog.destroy()
