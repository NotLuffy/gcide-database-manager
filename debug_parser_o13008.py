import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from improved_gcode_parser import ImprovedGCodeParser

file_path = r"I:/My Drive/Home/Test Export of Repository/mc file export/13.0/o13008.nc"

# Patch the parser to add debug output
original_parse = ImprovedGCodeParser.parse_file

def debug_parse(self, filepath):
    result = original_parse(filepath)

    # Add debug after parsing
    print('='*80)
    print('PARSER RESULT')
    print('='*80)
    print(f'Spacer type: {result.spacer_type}')
    print(f'CB from gcode: {result.cb_from_gcode}mm')
    print(f'OB from gcode: {result.ob_from_gcode}')
    print(f'Title CB: {result.center_bore}mm')
    print(f'Title OB: {result.hub_diameter}mm')

    return result

ImprovedGCodeParser.parse_file = debug_parse

parser = ImprovedGCodeParser()
result = parser.parse_file(file_path)

# Check if OB was detected
if result.ob_from_gcode is None:
    print()
    print('[ERROR] OB not detected!')
    print()
    print('Expected: X8.661 = 220.0mm (close to title 225mm)')
else:
    print()
    print(f'[OK] OB detected: {result.ob_from_gcode:.1f}mm')
