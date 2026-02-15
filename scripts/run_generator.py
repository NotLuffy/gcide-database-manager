"""
Launcher script for the G-Code Generator GUI.
Double-click this file to launch the generator.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Launch the GUI
from gcode_generator.ui.generator_gui import main
main()
