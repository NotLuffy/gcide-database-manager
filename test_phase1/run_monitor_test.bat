@echo off
REM Phase 1.2 Test - Database File Monitor

echo ================================================================================
echo Phase 1.2 Test Environment - Database File Monitor
echo ================================================================================
echo.
echo This test monitors the database file for external changes.
echo It does NOT modify your database - it only watches for changes.
echo.
echo Starting test application...
echo.

cd /d "%~dp0"
python database_monitor_test.py

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Failed to launch test application
    echo ================================================================================
    echo.
    echo Possible issues:
    echo   - Python not installed or not in PATH
    echo   - watchdog library not installed (pip install watchdog)
    echo.
    pause
)
