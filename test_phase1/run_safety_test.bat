@echo off
REM Phase 1.3 Test - Safety Warnings Before Writes

echo ================================================================================
echo Phase 1.3 Test Environment - Safety Warnings Before Writes
echo ================================================================================
echo.
echo This test demonstrates safety features that prevent data conflicts.
echo It includes conflict detection, auto-backup, and warning dialogs.
echo.
echo Starting test application...
echo.

cd /d "%~dp0"
python safety_warnings_test.py

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Failed to launch test application
    echo ================================================================================
    echo.
    pause
)
