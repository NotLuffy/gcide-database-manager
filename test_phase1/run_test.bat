@echo off
REM Phase 1 Test Environment Launcher
REM This script launches the isolated test environment for the file scanner

echo ================================================================================
echo Phase 1 Test Environment - Pre-Import File Scanner
echo ================================================================================
echo.
echo This is an ISOLATED test environment.
echo It does NOT modify your database or main application.
echo.
echo Starting test application...
echo.

cd /d "%~dp0"
python file_scanner_test.py

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Failed to launch test application
    echo ================================================================================
    echo.
    echo Possible issues:
    echo   - Python not installed or not in PATH
    echo   - improved_gcode_parser.py not found in parent directory
    echo   - Missing dependencies
    echo.
    echo Try running manually:
    echo   python file_scanner_test.py
    echo.
    pause
)
