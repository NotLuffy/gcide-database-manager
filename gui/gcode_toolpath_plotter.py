"""
G-Code Toolpath Plotter
Visualizes 2D lathe toolpaths using matplotlib.

Features:
- Parses G00/G01 moves and extracts X,Z coordinates
- Shows rapid moves (dashed green) vs feed moves (solid blue)
- Displays tool change positions (orange markers)
- Zoom/pan controls via matplotlib toolbar
- Export to PNG functionality
"""

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from tkinter import messagebox, filedialog
import re
from typing import List, Tuple, Dict
import os
import logging

logger = logging.getLogger(__name__)


class GCodeToolpathParser:
    """Parse G-code file and extract toolpath coordinates"""

    def __init__(self, file_path: str):
        """
        Initialize parser.

        Args:
            file_path: Path to G-code file
        """
        self.file_path = file_path

    def parse(self) -> Dict:
        """
        Parse G-code and extract toolpath data.

        Returns:
            {
                'rapid_moves': [(x1, z1, x2, z2), ...],  # G00 moves
                'feed_moves': [(x1, z1, x2, z2), ...],   # G01 moves
                'tool_changes': [(x, z, tool), ...],     # Tool positions
                'bounds': {'x_min': ..., 'x_max': ..., 'z_min': ..., 'z_max': ...},
                'line_coordinates': {line_num: (x, z), ...},  # Line number to coordinate mapping
                'gcode_lines': [...],  # Original G-code lines for display
                'flip_line': None,  # Line number where flip comment occurs
                'side1_deepest_z': None  # Deepest (most negative) Z from Side 1
            }
        """
        rapid_moves = []
        feed_moves = []
        tool_changes = []
        line_coordinates = {}  # Map line number to ending coordinate
        flip_line = None
        side1_deepest_z = 0.0

        # Load file
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                gcode_lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            return self._empty_result()

        # Track current position (modal G-code)
        current_x = 0.0
        current_z = 0.0
        current_tool = None
        current_mode = 'G00'  # Default to rapid

        for line_num, original_line in enumerate(gcode_lines, 1):
            line = original_line.strip().upper()

            # Check for flip comment (before stripping comments)
            if flip_line is None and '(' in original_line:
                comment = original_line[original_line.index('('):].upper()
                if 'FLIP' in comment:
                    flip_line = line_num

            # Skip comments and empty lines
            if not line or line.startswith('%'):
                continue

            # Remove inline comments
            if '(' in line:
                comment_start = line.index('(')
                line = line[:comment_start].strip()

            if not line:
                continue

            # Tool change (T followed by digits)
            tool_match = re.match(r'T(\d+)', line)
            if tool_match:
                current_tool = tool_match.group(1)
                tool_changes.append((current_x, current_z, current_tool))
                line_coordinates[line_num] = (current_x, current_z)
                continue

            # Detect G-code mode
            if 'G00' in line or 'G0 ' in line or line == 'G0':
                current_mode = 'G00'
            elif 'G01' in line or 'G1 ' in line or line == 'G1':
                current_mode = 'G01'

            # Extract coordinates (X and Z)
            new_x, new_z = self._extract_coordinates(line, current_x, current_z)

            # If position changed, add move
            if new_x != current_x or new_z != current_z:
                move = (current_x, current_z, new_x, new_z)

                if current_mode == 'G00':
                    rapid_moves.append(move)
                else:
                    feed_moves.append(move)

                # Map this line number to the destination coordinate
                line_coordinates[line_num] = (new_x, new_z)

                # Track deepest Z from T1xx drilling operations before flip (ignore G53)
                if flip_line is None or line_num < flip_line:
                    # Only track drilling tools (T1xx) and not G53 lines
                    if current_tool and current_tool.startswith('1') and 'G53' not in line:
                        if new_z < side1_deepest_z:
                            side1_deepest_z = new_z

                # Update current position
                current_x, current_z = new_x, new_z

        # Calculate bounds
        all_x = []
        all_z = []
        for x1, z1, x2, z2 in rapid_moves + feed_moves:
            all_x.extend([x1, x2])
            all_z.extend([z1, z2])

        if not all_x:
            return self._empty_result()

        bounds = {
            'x_min': min(all_x),
            'x_max': max(all_x),
            'z_min': min(all_z),
            'z_max': max(all_z)
        }

        return {
            'rapid_moves': rapid_moves,
            'feed_moves': feed_moves,
            'tool_changes': tool_changes,
            'bounds': bounds,
            'line_coordinates': line_coordinates,
            'gcode_lines': gcode_lines,
            'flip_line': flip_line,
            'side1_deepest_z': side1_deepest_z
        }

    def _extract_coordinates(self, line: str, current_x: float, current_z: float) -> Tuple[float, float]:
        """
        Extract X and Z coordinates from G-code line.

        Args:
            line: G-code line (uppercase)
            current_x: Current X position
            current_z: Current Z position

        Returns:
            (new_x, new_z) tuple
        """
        new_x = current_x
        new_z = current_z

        # Check if this is a G53 (machine coordinate) line
        is_g53 = 'G53' in line

        # X coordinate (radius for lathe)
        x_match = re.search(r'X\s*(-?\d+\.?\d*)', line)
        if x_match:
            new_x = float(x_match.group(1))
            # G53 uses different offset - use absolute value for visualization
            if is_g53:
                new_x = abs(new_x)

        # Z coordinate (length for lathe)
        z_match = re.search(r'Z\s*(-?\d+\.?\d*)', line)
        if z_match:
            new_z = float(z_match.group(1))
            # G53 uses different offset - use absolute value for visualization
            if is_g53:
                new_z = abs(new_z)

        return new_x, new_z

    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'rapid_moves': [],
            'feed_moves': [],
            'tool_changes': [],
            'bounds': {'x_min': 0, 'x_max': 0, 'z_min': 0, 'z_max': 0},
            'line_coordinates': {},
            'gcode_lines': [],
            'flip_line': None,
            'side1_deepest_z': None
        }


class ToolpathPlotter:
    """Modal window showing 2D toolpath visualization"""

    def __init__(self, parent, file_path: str, program_number: str,
                 bg_color: str = '#1e1e1e', fg_color: str = '#d4d4d4'):
        """
        Initialize toolpath plotter.

        Args:
            parent: Parent window
            file_path: Path to G-code file
            program_number: Program number for display
            bg_color: Background color
            fg_color: Foreground color
        """
        self.file_path = file_path
        self.program_number = program_number
        self.bg_color = bg_color
        self.fg_color = fg_color

        # Parse toolpath
        parser = GCodeToolpathParser(file_path)
        self.toolpath_data = parser.parse()

        # Check if we have any toolpath data
        if not self.toolpath_data['rapid_moves'] and not self.toolpath_data['feed_moves']:
            messagebox.showwarning(
                "No Toolpath Data",
                f"No toolpath movements found in {program_number}\n\n"
                "The file may contain only setup commands or comments."
            )
            return

        # Highlight marker reference (for removing previous highlights)
        self.highlight_marker = None

        # Filter state
        self.current_filter = 'whole'  # 'whole', 'side1', 'side2'
        self.flip_visualization = False  # Whether to flip Side 2 coordinates
        self.displayed_line_to_original = {}  # Map displayed line numbers to original line numbers
        self.segment_to_line = {}  # Map plot segment index to G-code line number
        self.current_playback_line = 1  # Current line for animation/playback

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Toolpath Visualization: {program_number}")
        self.window.geometry("1600x900")  # Wider for side-by-side layout
        # Don't use transient() - it prevents maximize button on Windows
        self.window.configure(bg=bg_color)

        # Enable maximize button and resizing
        self.window.resizable(True, True)
        self.window.state('normal')  # Can be 'normal', 'zoomed' (maximized), 'iconic', 'withdrawn'

        # Create UI
        self._create_ui()

    def _create_ui(self):
        """Build plotter window"""
        # Title bar
        header = tk.Frame(self.window, bg='#2d2d30', pady=10)
        header.pack(fill=tk.X)

        # Title
        tk.Label(header,
                text=f"Toolpath Visualization: {self.program_number}",
                bg='#2d2d30', fg='#ffffff',
                font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT, padx=10)

        # Filter controls (if flip comment found)
        if self.toolpath_data['flip_line']:
            filter_frame = tk.Frame(header, bg='#2d2d30')
            filter_frame.pack(side=tk.LEFT, padx=20)

            tk.Label(filter_frame, text="View:",
                    bg='#2d2d30', fg='#d4d4d4',
                    font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)

            # Store button references for updating colors
            self.filter_buttons = {}

            self.filter_buttons['whole'] = tk.Button(
                filter_frame, text="Whole Code",
                command=lambda: self._apply_filter('whole'),
                bg='#007acc', fg='white', font=('Segoe UI', 9),
                padx=10, pady=2)
            self.filter_buttons['whole'].pack(side=tk.LEFT, padx=2)

            self.filter_buttons['side1'] = tk.Button(
                filter_frame, text="Side 1",
                command=lambda: self._apply_filter('side1'),
                bg='#3c3c3c', fg='white', font=('Segoe UI', 9),
                padx=10, pady=2)
            self.filter_buttons['side1'].pack(side=tk.LEFT, padx=2)

            self.filter_buttons['side2'] = tk.Button(
                filter_frame, text="Side 2",
                command=lambda: self._apply_filter('side2'),
                bg='#3c3c3c', fg='white', font=('Segoe UI', 9),
                padx=10, pady=2)
            self.filter_buttons['side2'].pack(side=tk.LEFT, padx=2)

            # Flip visualization toggle (enabled for Whole Code view by default)
            self.flip_viz_btn = tk.Button(filter_frame, text="🔄 Flip View",
                                          command=self._toggle_flip_visualization,
                                          bg='#3c3c3c', fg='white',
                                          font=('Segoe UI', 9),
                                          padx=10, pady=2,
                                          state=tk.NORMAL)  # Enabled by default in Whole Code view
            self.flip_viz_btn.pack(side=tk.LEFT, padx=5)

        # Info panel
        info_frame = tk.Frame(header, bg='#2d2d30')
        info_frame.pack(side=tk.RIGHT, padx=10)

        bounds = self.toolpath_data['bounds']
        rapid_count = len(self.toolpath_data['rapid_moves'])
        feed_count = len(self.toolpath_data['feed_moves'])
        tool_count = len(self.toolpath_data['tool_changes'])

        stats_text = (f"X: {bounds['x_min']:.3f} to {bounds['x_max']:.3f} | "
                     f"Z: {bounds['z_min']:.3f} to {bounds['z_max']:.3f} | "
                     f"Moves: {rapid_count + feed_count} | Tools: {tool_count}")

        tk.Label(info_frame, text=stats_text,
                bg='#2d2d30', fg='#d4d4d4',
                font=('Consolas', 9)).pack()

        # Main content area - split between plot and G-code
        content_frame = tk.Frame(self.window, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # LEFT SIDE: Plot and toolbar
        plot_container = tk.Frame(content_frame, bg=self.bg_color)
        plot_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Plot frame
        plot_frame = tk.Frame(plot_container, bg=self.bg_color)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        # Create and embed matplotlib figure
        self._create_plot()
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Connect click events for plot-to-gcode highlighting
        self.canvas.mpl_connect('pick_event', self._on_plot_click)
        self.canvas.mpl_connect('button_press_event', self._on_plot_button_press)

        # Connect zoom and pan events
        self.canvas.mpl_connect('scroll_event', self._on_scroll_zoom)
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

        # Pan state
        self.panning = False
        self.pan_start = None

        # Navigation toolbar (zoom, pan, home, save)
        toolbar_frame = tk.Frame(plot_container, bg='#2d2d30')
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Style toolbar
        try:
            self.toolbar.config(bg='#2d2d30')
            for child in self.toolbar.winfo_children():
                try:
                    child.config(bg='#2d2d30')
                except:
                    pass
        except:
            pass

        # RIGHT SIDE: G-code viewer
        gcode_container = tk.Frame(content_frame, bg=self.bg_color, width=500)
        gcode_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))
        gcode_container.pack_propagate(False)  # Maintain fixed width

        # G-code header
        gcode_header = tk.Frame(gcode_container, bg='#2d2d30', pady=5)
        gcode_header.pack(fill=tk.X)
        tk.Label(gcode_header, text="G-Code (Click to highlight)",
                bg='#2d2d30', fg='#ffffff',
                font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        # G-code text widget with scrollbar
        text_frame = tk.Frame(gcode_container, bg=self.bg_color)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = tk.Scrollbar(text_frame, bg='#2d2d30')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.gcode_text = tk.Text(text_frame,
                                  bg='#1e1e1e', fg='#d4d4d4',
                                  font=('Consolas', 9),
                                  wrap=tk.NONE,
                                  yscrollcommand=scrollbar.set,
                                  cursor='hand2')
        self.gcode_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.gcode_text.yview)

        # Insert G-code lines
        for line in self.toolpath_data['gcode_lines']:
            self.gcode_text.insert(tk.END, line)

        self.gcode_text.config(state=tk.DISABLED)  # Read-only

        # Bind click event
        self.gcode_text.bind('<Button-1>', self._on_gcode_click)

        # Configure text tags for highlighting
        self.gcode_text.tag_config('highlight', background='#264f78', foreground='#ffffff')
        self.gcode_text.tag_config('playback', background='#4a90e2', foreground='#ffffff')

        # Bottom buttons
        button_frame = tk.Frame(self.window, bg='#2d2d30', pady=10)
        button_frame.pack(fill=tk.X)

        # Left side buttons
        tk.Button(button_frame, text="💾 Export PNG",
                 command=self._export_plot,
                 bg='#4a90e2', fg='white',
                 font=('Segoe UI', 10), padx=15, pady=5).pack(side=tk.LEFT, padx=10)

        # Center - Playback controls
        playback_frame = tk.Frame(button_frame, bg='#2d2d30')
        playback_frame.pack(side=tk.LEFT, padx=30)

        tk.Label(playback_frame, text="Animation:",
                bg='#2d2d30', fg='#d4d4d4',
                font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        tk.Button(playback_frame, text="⏮ First",
                 command=self.goto_first_line,
                 bg='#6c757d', fg='white',
                 font=('Segoe UI', 9), padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(playback_frame, text="◀ Prev",
                 command=self.goto_prev_line,
                 bg='#6c757d', fg='white',
                 font=('Segoe UI', 9), padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(playback_frame, text="▶ Next",
                 command=self.goto_next_line,
                 bg='#6c757d', fg='white',
                 font=('Segoe UI', 9), padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        tk.Button(playback_frame, text="⏭ Last",
                 command=self.goto_last_line,
                 bg='#6c757d', fg='white',
                 font=('Segoe UI', 9), padx=10, pady=3).pack(side=tk.LEFT, padx=2)

        # Line position label
        self.playback_label = tk.Label(playback_frame, text="Line 1/1",
                                       bg='#2d2d30', fg='#4a90e2',
                                       font=('Consolas', 9))
        self.playback_label.pack(side=tk.LEFT, padx=10)

        # Right side button
        tk.Button(button_frame, text="Close",
                 command=self.window.destroy,
                 bg='#6c757d', fg='white',
                 font=('Segoe UI', 10), padx=15, pady=5).pack(side=tk.RIGHT, padx=10)

    def _create_plot(self):
        """Create matplotlib figure with toolpath"""
        # Create figure with dark theme
        self.fig, self.ax = plt.subplots(figsize=(14, 9), facecolor=self.bg_color)
        self.ax.set_facecolor('#252526')

        # Plot rapid moves (dashed green)
        rapid_plotted = False
        for x1, z1, x2, z2 in self.toolpath_data['rapid_moves']:
            label = 'Rapid (G00)' if not rapid_plotted else ''
            self.ax.plot([z1, z2], [x1, x2],
                        color='#4EC9B0', linestyle='--', linewidth=1.5,
                        alpha=0.7, label=label)
            rapid_plotted = True

        # Plot feed moves (solid blue)
        feed_plotted = False
        for x1, z1, x2, z2 in self.toolpath_data['feed_moves']:
            label = 'Feed (G01)' if not feed_plotted else ''
            self.ax.plot([z1, z2], [x1, x2],
                        color='#569CD6', linestyle='-', linewidth=2.0,
                        label=label)
            feed_plotted = True

        # Plot tool change positions (orange markers)
        tool_plotted = set()
        for x, z, tool in self.toolpath_data['tool_changes']:
            label = f'T{tool}' if tool not in tool_plotted else ''
            self.ax.plot(z, x, 'o', color='#CE9178', markersize=8,
                        label=label, zorder=5)
            # Annotate tool number
            self.ax.annotate(f'T{tool}', (z, x),
                           xytext=(5, 5), textcoords='offset points',
                           color='#CE9178', fontsize=9, fontweight='bold')
            tool_plotted.add(tool)

        # Configure axes
        self.ax.set_xlabel('Z - Length (inches)', color=self.fg_color, fontsize=12)
        self.ax.set_ylabel('X - Radius (inches)', color=self.fg_color, fontsize=12)
        self.ax.set_title(f'Toolpath: {self.program_number}',
                         color=self.fg_color, fontsize=14, fontweight='bold', pad=20)

        # Grid
        self.ax.grid(True, color='#3e3e42', linestyle=':', alpha=0.5, linewidth=0.8)

        # Tick colors
        self.ax.tick_params(colors=self.fg_color, labelsize=10)

        # Spine colors
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#3e3e42')

        # Legend
        if self.ax.get_legend_handles_labels()[0]:  # Only if we have labels
            legend = self.ax.legend(loc='upper right',
                                  facecolor='#2d2d30',
                                  edgecolor='#3e3e42',
                                  labelcolor=self.fg_color,
                                  fontsize=10)
            legend.get_frame().set_alpha(0.9)

        # Equal aspect ratio for accurate visualization
        self.ax.set_aspect('equal', adjustable='datalim')

        # Add some padding to bounds
        bounds = self.toolpath_data['bounds']
        x_range = bounds['x_max'] - bounds['x_min']
        z_range = bounds['z_max'] - bounds['z_min']

        padding = 0.1  # 10% padding
        self.ax.set_xlim(bounds['z_min'] - z_range * padding,
                        bounds['z_max'] + z_range * padding)
        self.ax.set_ylim(bounds['x_min'] - x_range * padding,
                        bounds['x_max'] + x_range * padding)

        plt.tight_layout()

    def _on_plot_click(self, event):
        """Handle click on plot to highlight corresponding G-code line"""
        if not hasattr(event, 'artist'):
            return

        # Get the clicked line artist
        artist = event.artist

        # Get the line number stored in gid
        line_gid = artist.get_gid()
        if not line_gid:
            return

        try:
            original_line_num = int(line_gid)
        except (ValueError, TypeError):
            return

        # Find the displayed line number from original line number
        displayed_line_num = None
        for disp_line, orig_line in self.displayed_line_to_original.items():
            if orig_line == original_line_num:
                displayed_line_num = disp_line
                break

        if not displayed_line_num:
            return

        # Remove previous text highlight
        self.gcode_text.tag_remove('highlight', '1.0', tk.END)
        self.gcode_text.tag_remove('playback', '1.0', tk.END)

        # Highlight the line in G-code viewer
        self.gcode_text.tag_add('highlight', f"{displayed_line_num}.0", f"{displayed_line_num}.end")

        # Scroll to make the line visible
        self.gcode_text.see(f"{displayed_line_num}.0")

        # Update playback line
        self.current_playback_line = original_line_num

        # Get coordinates for plot marker
        if original_line_num in self.toolpath_data['line_coordinates']:
            x, z = self.toolpath_data['line_coordinates'][original_line_num]

            # Apply flip transformation if needed
            flip_line = self.toolpath_data['flip_line']
            if self.flip_visualization and flip_line and original_line_num >= flip_line:
                z_ref = self.toolpath_data['side1_deepest_z'] or 0
                x, z = self._flip_coordinate(x, z, z_ref)

            self._highlight_position(x, z, original_line_num)

        # Update playback label
        total_lines = max(self.toolpath_data['line_coordinates'].keys()) if self.toolpath_data['line_coordinates'] else 1
        self.playback_label.config(text=f"Line {original_line_num}/{total_lines}")

    def _on_gcode_click(self, event):
        """Handle click on G-code text widget"""
        # Get the displayed line number that was clicked
        index = self.gcode_text.index(f"@{event.x},{event.y}")
        displayed_line_num = int(index.split('.')[0])

        # Map to original line number
        original_line_num = self.displayed_line_to_original.get(displayed_line_num)
        if not original_line_num:
            return

        # Remove previous text highlight
        self.gcode_text.tag_remove('highlight', '1.0', tk.END)

        # Highlight the clicked line
        self.gcode_text.tag_add('highlight', f"{displayed_line_num}.0", f"{displayed_line_num}.end")

        # Check if this line has a coordinate mapping
        if original_line_num in self.toolpath_data['line_coordinates']:
            x, z = self.toolpath_data['line_coordinates'][original_line_num]

            # Apply flip transformation if needed for Side 2 coordinates
            flip_line = self.toolpath_data['flip_line']
            if self.flip_visualization and flip_line and original_line_num >= flip_line:
                z_ref = self.toolpath_data['side1_deepest_z'] or 0
                x, z = self._flip_coordinate(x, z, z_ref)

            self._highlight_position(x, z, original_line_num)
        else:
            # No coordinate for this line, just remove any existing highlight marker
            if self.highlight_marker:
                self.highlight_marker.remove()
                self.highlight_marker = None
                self.canvas.draw()

    def _highlight_position(self, x: float, z: float, line_num: int):
        """
        Highlight a position on the plot with a red marker.

        Args:
            x: X coordinate
            z: Z coordinate
            line_num: Line number for label
        """
        # Remove previous highlight marker
        if self.highlight_marker:
            self.highlight_marker.remove()

        # Add new highlight marker (red dot)
        self.highlight_marker = self.ax.plot(z, x, 'o',
                                            color='#ff0000',
                                            markersize=12,
                                            markeredgewidth=2,
                                            markeredgecolor='#ffffff',
                                            zorder=10,
                                            label=f'Line {line_num}')[0]

        # Update legend to include the highlighted line
        if self.ax.get_legend():
            self.ax.legend(loc='upper right',
                          facecolor='#2d2d30',
                          edgecolor='#3e3e42',
                          labelcolor=self.fg_color,
                          fontsize=10).get_frame().set_alpha(0.9)

        # Redraw canvas
        self.canvas.draw()

    def _apply_filter(self, filter_type: str):
        """
        Apply side filter and update display.

        Args:
            filter_type: 'whole', 'side1', or 'side2'
        """
        self.current_filter = filter_type

        # Update filter button colors
        if hasattr(self, 'filter_buttons'):
            for key, btn in self.filter_buttons.items():
                if key == filter_type:
                    btn.config(bg='#007acc')
                else:
                    btn.config(bg='#3c3c3c')

        # Enable flip visualization button for Whole Code and Side 2
        if hasattr(self, 'flip_viz_btn'):
            if filter_type in ('whole', 'side2'):
                self.flip_viz_btn.config(state=tk.NORMAL)
            else:
                self.flip_viz_btn.config(state=tk.DISABLED)
                self.flip_visualization = False
                self.flip_viz_btn.config(bg='#3c3c3c', text="🔄 Flip View")

        # Update G-code text display
        self._update_gcode_display()

        # Replot with filtered data
        self._replot()

    def _toggle_flip_visualization(self):
        """Toggle flip visualization for Side 2"""
        self.flip_visualization = not self.flip_visualization

        # Update button appearance
        if self.flip_visualization:
            self.flip_viz_btn.config(bg='#007acc', text="🔄 Flip View (ON)")
        else:
            self.flip_viz_btn.config(bg='#3c3c3c', text="🔄 Flip View")

        # Replot
        self._replot()

    def _update_gcode_display(self):
        """Update G-code text widget based on current filter"""
        self.gcode_text.config(state=tk.NORMAL)
        self.gcode_text.delete('1.0', tk.END)

        flip_line = self.toolpath_data['flip_line']
        self.displayed_line_to_original = {}  # Reset mapping
        displayed_line_num = 1

        if self.current_filter == 'whole':
            # Show all lines
            for original_line_num, line in enumerate(self.toolpath_data['gcode_lines'], 1):
                self.gcode_text.insert(tk.END, line)
                self.displayed_line_to_original[displayed_line_num] = original_line_num
                displayed_line_num += 1
        elif self.current_filter == 'side1':
            # Show only lines before flip
            for original_line_num, line in enumerate(self.toolpath_data['gcode_lines'], 1):
                if flip_line and original_line_num >= flip_line:
                    break
                self.gcode_text.insert(tk.END, line)
                self.displayed_line_to_original[displayed_line_num] = original_line_num
                displayed_line_num += 1
        elif self.current_filter == 'side2':
            # Show only lines after flip
            for original_line_num, line in enumerate(self.toolpath_data['gcode_lines'], 1):
                if flip_line and original_line_num >= flip_line:
                    self.gcode_text.insert(tk.END, line)
                    self.displayed_line_to_original[displayed_line_num] = original_line_num
                    displayed_line_num += 1

        self.gcode_text.config(state=tk.DISABLED)

    def _replot(self):
        """Redraw the plot with current filter settings"""
        # Clear previous plot
        self.ax.clear()
        self.segment_to_line = {}  # Reset segment mapping

        # Get filtered data
        filtered_data = self._get_filtered_toolpath()

        # Plot rapid moves (bright orange, thinner, more transparent)
        rapid_plotted = False
        for i, (x1, z1, x2, z2) in enumerate(filtered_data['rapid_moves']):
            label = 'Rapid (G00)' if not rapid_plotted else ''
            line, = self.ax.plot([z1, z2], [x1, x2],
                        color='#FF8C00', linestyle='-', linewidth=1.0,
                        alpha=0.5, label=label, picker=5, pickradius=5)

            # Store line number in the line's gid for click detection
            line_num = None
            if i < len(filtered_data['rapid_lines']):
                line_num, _ = filtered_data['rapid_lines'][i]
                line.set_gid(str(line_num))  # Store line number as gid

            # Add clickable endpoint dots (half the thickness of feed lines: 2.0/2 = 1.0)
            if line_num:
                # Add dot at end point only (where the move ends)
                dot, = self.ax.plot(z2, x2, 'o', color='black', markersize=1.0,
                           picker=True, pickradius=2, zorder=3)
                dot.set_gid(str(line_num))  # Same line number for clicking

            rapid_plotted = True

        # Plot feed moves (blue for Side 1, neon green for Side 2 when flipped)
        feed_side1_plotted = False
        feed_side2_plotted = False
        for i, (x1, z1, x2, z2) in enumerate(filtered_data['feed_moves']):
            # Get line number and side info from tracked data
            is_side2 = False
            line_num_for_segment = None
            if i < len(filtered_data['feed_lines']):
                line_num_for_segment, is_side2 = filtered_data['feed_lines'][i]

            # Determine color based on side and flip visualization
            if is_side2 and self.flip_visualization:
                # Side 2 with flip: neon green
                label = 'Feed Side 2 (G01)' if not feed_side2_plotted else ''
                color = '#7FFF00'  # Chartreuse (neon green)
                feed_side2_plotted = True
            else:
                # Side 1 or normal: blue
                label = 'Feed (G01)' if not feed_side1_plotted else ''
                color = '#569CD6'
                feed_side1_plotted = True

            line, = self.ax.plot([z1, z2], [x1, x2],
                        color=color, linestyle='-', linewidth=2.0,
                        label=label, picker=5, pickradius=5)

            # Store line number in the line's gid for click detection
            if line_num_for_segment:
                line.set_gid(str(line_num_for_segment))

                # Add clickable endpoint dot (half the thickness of feed lines: 2.0/2 = 1.0)
                # Add dot at end point only (where the move ends)
                dot, = self.ax.plot(z2, x2, 'o', color='black', markersize=1.0,
                           picker=True, pickradius=2, zorder=3)
                dot.set_gid(str(line_num_for_segment))  # Same line number for clicking

        # Plot tool changes
        tool_plotted = set()
        for x, z, tool in filtered_data['tool_changes']:
            label = f'T{tool}' if tool not in tool_plotted else ''
            self.ax.plot(z, x, 'o', color='#CE9178', markersize=8,
                        label=label, zorder=5)
            self.ax.annotate(f'T{tool}', (z, x),
                           xytext=(5, 5), textcoords='offset points',
                           color='#CE9178', fontsize=9, fontweight='bold')
            tool_plotted.add(tool)

        # Reconfigure axes
        self.ax.set_xlabel('Z - Length (inches)', color=self.fg_color, fontsize=12)
        self.ax.set_ylabel('X - Radius (inches)', color=self.fg_color, fontsize=12)

        title = f'Toolpath: {self.program_number}'
        if self.current_filter == 'side1':
            title += ' (Side 1 Only)'
        elif self.current_filter == 'side2':
            title += ' (Side 2 Only'
            if self.flip_visualization:
                title += ' - Flipped'
            title += ')'
        elif self.current_filter == 'whole' and self.flip_visualization:
            title += ' (Side 1 Normal + Side 2 Flipped)'

        self.ax.set_title(title, color=self.fg_color, fontsize=14, fontweight='bold', pad=20)
        self.ax.grid(True, color='#3e3e42', linestyle=':', alpha=0.5, linewidth=0.8)
        self.ax.tick_params(colors=self.fg_color, labelsize=10)

        for spine in self.ax.spines.values():
            spine.set_edgecolor('#3e3e42')

        if self.ax.get_legend_handles_labels()[0]:
            legend = self.ax.legend(loc='upper right',
                                  facecolor='#2d2d30',
                                  edgecolor='#3e3e42',
                                  labelcolor=self.fg_color,
                                  fontsize=10)
            legend.get_frame().set_alpha(0.9)

        self.ax.set_aspect('equal', adjustable='datalim')

        # Auto-scale to bounds
        if filtered_data['rapid_moves'] or filtered_data['feed_moves']:
            bounds = filtered_data['bounds']
            x_range = bounds['x_max'] - bounds['x_min']
            z_range = bounds['z_max'] - bounds['z_min']
            padding = 0.1
            self.ax.set_xlim(bounds['z_min'] - z_range * padding,
                            bounds['z_max'] + z_range * padding)
            self.ax.set_ylim(bounds['x_min'] - x_range * padding,
                            bounds['x_max'] + x_range * padding)

        # Clear highlight marker
        self.highlight_marker = None

        plt.tight_layout()
        self.canvas.draw()

    def _get_filtered_toolpath(self) -> Dict:
        """Get filtered toolpath data based on current filter settings"""
        flip_line = self.toolpath_data['flip_line']
        line_coords = self.toolpath_data['line_coordinates']

        # Build filtered moves with line number tracking
        filtered_rapid = []
        filtered_rapid_lines = []  # Line numbers for each rapid move
        filtered_feed = []
        filtered_feed_lines = []  # Line numbers for each feed move
        filtered_tools = []

        # Process each line's coordinates
        for line_num, (x, z) in line_coords.items():
            # Determine which side this line belongs to
            is_side2 = flip_line and line_num >= flip_line

            # Apply filter rules
            if self.current_filter == 'side1' and is_side2:
                continue
            if self.current_filter == 'side2' and not is_side2:
                continue

            # Find moves that end at this coordinate
            for move in self.toolpath_data['rapid_moves']:
                if abs(move[2] - x) < 0.001 and abs(move[3] - z) < 0.001:
                    # Apply flip transformation for Side 2 if flip visualization is enabled
                    if self.flip_visualization and is_side2:
                        z_ref = self.toolpath_data['side1_deepest_z'] or 0
                        move = self._flip_move(move, z_ref)
                    if move not in filtered_rapid:
                        filtered_rapid.append(move)
                        filtered_rapid_lines.append((line_num, is_side2))

            for move in self.toolpath_data['feed_moves']:
                if abs(move[2] - x) < 0.001 and abs(move[3] - z) < 0.001:
                    # Apply flip transformation for Side 2 if flip visualization is enabled
                    if self.flip_visualization and is_side2:
                        z_ref = self.toolpath_data['side1_deepest_z'] or 0
                        move = self._flip_move(move, z_ref)
                    if move not in filtered_feed:
                        filtered_feed.append(move)
                        filtered_feed_lines.append((line_num, is_side2))

        # Process tool changes
        for x, z, tool in self.toolpath_data['tool_changes']:
            for line_num, (coord_x, coord_z) in line_coords.items():
                if abs(coord_x - x) < 0.001 and abs(coord_z - z) < 0.001:
                    is_side2 = flip_line and line_num >= flip_line

                    # Apply filter rules
                    if self.current_filter == 'side1' and is_side2:
                        continue
                    if self.current_filter == 'side2' and not is_side2:
                        continue

                    # Apply flip transformation for Side 2 if flip visualization is enabled
                    if self.flip_visualization and is_side2:
                        z_ref = self.toolpath_data['side1_deepest_z'] or 0
                        x_flip, z_flip = self._flip_coordinate(x, z, z_ref)
                        filtered_tools.append((x_flip, z_flip, tool))
                    else:
                        filtered_tools.append((x, z, tool))
                    break

        # Calculate new bounds
        all_x = []
        all_z = []
        for x1, z1, x2, z2 in filtered_rapid + filtered_feed:
            all_x.extend([x1, x2])
            all_z.extend([z1, z2])

        if all_x:
            bounds = {
                'x_min': min(all_x),
                'x_max': max(all_x),
                'z_min': min(all_z),
                'z_max': max(all_z)
            }
        else:
            bounds = {'x_min': 0, 'x_max': 0, 'z_min': 0, 'z_max': 0}

        return {
            'rapid_moves': filtered_rapid,
            'rapid_lines': filtered_rapid_lines,
            'feed_moves': filtered_feed,
            'feed_lines': filtered_feed_lines,
            'tool_changes': filtered_tools,
            'bounds': bounds
        }

    def _flip_move(self, move: Tuple[float, float, float, float], z_ref: float) -> Tuple[float, float, float, float]:
        """
        Flip a move's Z coordinates for Side 2 visualization.

        Args:
            move: (x1, z1, x2, z2) tuple
            z_ref: Reference Z (deepest Z from Side 1)

        Returns:
            Flipped move tuple
        """
        x1, z1, x2, z2 = move
        # Z0 is at z_ref, negative Z goes toward positive
        z1_flip = -(z1 - z_ref)
        z2_flip = -(z2 - z_ref)
        return (x1, z1_flip, x2, z2_flip)

    def _flip_coordinate(self, x: float, z: float, z_ref: float) -> Tuple[float, float]:
        """Flip a single coordinate"""
        z_flip = -(z - z_ref)
        return (x, z_flip)

    def _on_plot_button_press(self, event):
        """Handle button press on plot for debugging"""
        if event.inaxes != self.ax:
            return

        # Print debug info to help troubleshoot clicking
        logger.debug(f"Plot clicked at Z={event.xdata:.3f}, X={event.ydata:.3f}")
        logger.debug(f"segment_to_line has {len(self.segment_to_line)} entries")

    def _on_scroll_zoom(self, event):
        """Handle scroll wheel zoom"""
        if event.inaxes != self.ax:
            return

        # Get current axis limits
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        # Get mouse position
        xdata = event.xdata
        ydata = event.ydata

        # Zoom factor (scroll up = zoom in, scroll down = zoom out)
        zoom_factor = 0.8 if event.button == 'up' else 1.2

        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * zoom_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * zoom_factor

        # Calculate relative position of mouse
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        # Set new limits centered on mouse position
        self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        self.ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])

        self.canvas.draw()

    def _on_mouse_press(self, event):
        """Handle mouse button press for panning"""
        if event.button == 3 and event.inaxes == self.ax:  # Right mouse button
            self.panning = True
            self.pan_start = (event.xdata, event.ydata)

    def _on_mouse_release(self, event):
        """Handle mouse button release"""
        if event.button == 3:  # Right mouse button
            self.panning = False
            self.pan_start = None

    def _on_mouse_move(self, event):
        """Handle mouse movement for panning"""
        if self.panning and event.inaxes == self.ax and self.pan_start:
            # Calculate pan offset
            dx = self.pan_start[0] - event.xdata
            dy = self.pan_start[1] - event.ydata

            # Get current limits
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()

            # Apply pan
            self.ax.set_xlim([cur_xlim[0] + dx, cur_xlim[1] + dx])
            self.ax.set_ylim([cur_ylim[0] + dy, cur_ylim[1] + dy])

            self.canvas.draw()

    def goto_first_line(self):
        """Jump to first line with coordinates"""
        if not self.toolpath_data['line_coordinates']:
            return

        # Get first line number that has coordinates
        first_line = min(self.toolpath_data['line_coordinates'].keys())
        self.current_playback_line = first_line
        self._highlight_playback_line()

    def goto_last_line(self):
        """Jump to last line with coordinates"""
        if not self.toolpath_data['line_coordinates']:
            return

        # Get last line number that has coordinates
        last_line = max(self.toolpath_data['line_coordinates'].keys())
        self.current_playback_line = last_line
        self._highlight_playback_line()

    def goto_next_line(self):
        """Move to next line with coordinates"""
        if not self.toolpath_data['line_coordinates']:
            return

        # Get sorted list of line numbers
        line_numbers = sorted(self.toolpath_data['line_coordinates'].keys())

        # Find next line after current
        for line_num in line_numbers:
            if line_num > self.current_playback_line:
                self.current_playback_line = line_num
                self._highlight_playback_line()
                return

        # Already at last line, wrap to first
        self.current_playback_line = line_numbers[0]
        self._highlight_playback_line()

    def goto_prev_line(self):
        """Move to previous line with coordinates"""
        if not self.toolpath_data['line_coordinates']:
            return

        # Get sorted list of line numbers
        line_numbers = sorted(self.toolpath_data['line_coordinates'].keys())

        # Find previous line before current
        for line_num in reversed(line_numbers):
            if line_num < self.current_playback_line:
                self.current_playback_line = line_num
                self._highlight_playback_line()
                return

        # Already at first line, wrap to last
        self.current_playback_line = line_numbers[-1]
        self._highlight_playback_line()

    def _highlight_playback_line(self):
        """Highlight current playback line in G-code viewer and plot"""
        # Find displayed line number from original line number
        displayed_line_num = None
        for disp_line, orig_line in self.displayed_line_to_original.items():
            if orig_line == self.current_playback_line:
                displayed_line_num = disp_line
                break

        if not displayed_line_num:
            return

        # Remove previous playback highlight
        self.gcode_text.tag_remove('playback', '1.0', tk.END)

        # Highlight the line in G-code viewer
        self.gcode_text.tag_add('playback', f"{displayed_line_num}.0", f"{displayed_line_num}.end")

        # Scroll to make the line visible
        self.gcode_text.see(f"{displayed_line_num}.0")

        # Get coordinates for plot marker
        if self.current_playback_line in self.toolpath_data['line_coordinates']:
            x, z = self.toolpath_data['line_coordinates'][self.current_playback_line]

            # Apply flip transformation if needed
            flip_line = self.toolpath_data['flip_line']
            if self.flip_visualization and flip_line and self.current_playback_line >= flip_line:
                z_ref = self.toolpath_data['side1_deepest_z'] or 0
                x, z = self._flip_coordinate(x, z, z_ref)

            self._highlight_position(x, z, self.current_playback_line)

        # Update playback label
        total_lines = len(self.toolpath_data['line_coordinates'])
        self.playback_label.config(text=f"Line {self.current_playback_line}/{max(self.toolpath_data['line_coordinates'].keys())}")

    def _export_plot(self):
        """Export plot to PNG file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            initialfile=f"{self.program_number}_toolpath.png",
            title="Export Toolpath as PNG"
        )

        if filename:
            try:
                self.fig.savefig(filename, dpi=300, facecolor=self.bg_color,
                               edgecolor='none', bbox_inches='tight')
                messagebox.showinfo("Export Complete",
                                  f"Toolpath saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error",
                                   f"Failed to export:\n{str(e)}")
