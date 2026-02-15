@echo off
REM ========================================================================
REM Google Drive Letter Fix - Makes Google Drive Always Use Drive G:
REM ========================================================================
REM
REM This script maps your Google Drive to a consistent drive letter (G:)
REM so that all your file paths stay the same across different computers.
REM
REM Run this script AS ADMINISTRATOR on each computer you use.
REM ========================================================================

echo.
echo ========================================================================
echo     GOOGLE DRIVE LETTER FIX - Map to G: Drive
echo ========================================================================
echo.
echo This script will:
echo   1. Find where Google Drive is currently mounted
echo   2. Create a virtual G: drive that points to it
echo   3. Make it persistent (survives reboots)
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run AS ADMINISTRATOR
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Running as administrator... OK
echo.

REM Find Google Drive location
echo Searching for Google Drive...
set GDRIVE_PATH=

REM Common Google Drive locations
if exist "%USERPROFILE%\Google Drive\" (
    set GDRIVE_PATH=%USERPROFILE%\Google Drive
    echo Found at: %USERPROFILE%\Google Drive
)

if exist "C:\Users\%USERNAME%\Google Drive\" (
    set GDRIVE_PATH=C:\Users\%USERNAME%\Google Drive
    echo Found at: C:\Users\%USERNAME%\Google Drive
)

REM Check current drive letters (L:, M:, N:, etc.)
for %%D in (L M N O P Q R S T) do (
    if exist "%%D:\My Drive\" (
        set GDRIVE_PATH=%%D:\My Drive
        echo Found at: %%D:\My Drive
        goto :found
    )
)

:found
if "%GDRIVE_PATH%"=="" (
    echo.
    echo ERROR: Could not find Google Drive automatically.
    echo.
    echo Please enter the full path to your Google Drive folder:
    echo Example: L:\My Drive
    echo.
    set /p GDRIVE_PATH="Google Drive Path: "
)

if not exist "%GDRIVE_PATH%\" (
    echo.
    echo ERROR: Path does not exist: %GDRIVE_PATH%
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo Will map G: drive to: %GDRIVE_PATH%
echo ========================================================================
echo.
echo After this, you should:
echo   1. Update your G-Code Database settings to use G:\Home\File organizer
echo   2. Click "Fix Drive Letter" button in Maintenance tab
echo   3. All file paths will use G:\ from now on
echo.
echo Press any key to continue, or Ctrl+C to cancel...
pause >nul

REM Remove existing G: mapping if present
if exist "G:\" (
    echo.
    echo Removing existing G: drive mapping...
    subst G: /D >nul 2>&1
)

REM Create the G: drive mapping
echo.
echo Creating G: drive mapping...
subst G: "%GDRIVE_PATH%"

if %errorLevel% equ 0 (
    echo SUCCESS: G: drive created
    echo.
    echo Testing G: drive...
    dir G:\ >nul 2>&1
    if %errorLevel% equ 0 (
        echo G: drive is working!
    ) else (
        echo WARNING: G: drive created but cannot access it
    )
) else (
    echo ERROR: Failed to create G: drive
    pause
    exit /b 1
)

REM Make it persistent across reboots
echo.
echo Making G: drive persistent (survives reboots)...
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\DOS Devices" /v G: /t REG_SZ /d "\??\%GDRIVE_PATH%" /f >nul 2>&1

if %errorLevel% equ 0 (
    echo SUCCESS: G: drive will persist across reboots
) else (
    echo WARNING: Could not make G: drive persistent
    echo You may need to run this script after each reboot
)

echo.
echo ========================================================================
echo COMPLETE!
echo ========================================================================
echo.
echo G: drive is now mapped to: %GDRIVE_PATH%
echo.
echo NEXT STEPS:
echo   1. Open G-Code Database Manager
echo   2. Go to Maintenance tab
echo   3. Click "Fix Drive Letter" button
echo   4. All paths will be updated to use G:\
echo.
echo On other computers:
echo   1. Run this script AS ADMINISTRATOR on each computer
echo   2. It will map G: to wherever Google Drive is on that computer
echo   3. All paths will work because they all use G:\
echo.
pause
