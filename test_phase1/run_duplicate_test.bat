@echo off
REM Phase 1.4 Test - Duplicate with Automatic Scan

echo ================================================================================
echo Phase 1.4 Test Environment - Duplicate with Automatic Scan
echo ================================================================================
echo.
echo This test demonstrates duplicating G-code files with automatic scanning,
echo optional auto-fix of warnings, and editor integration.
echo.
echo Starting test application...
echo.

cd /d "%~dp0"
python duplicate_with_scan_test.py

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Failed to launch test application
    echo ================================================================================
    echo.
    pause
)
