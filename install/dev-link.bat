@echo off
REM Cutaway — developer install (link mode).
REM Removes any existing installed copy and creates a directory junction
REM from Fusion's AddIns folder back to the source repo. After this, every
REM Stop/Run cycle in Fusion picks up your latest code with no copy step.
REM
REM Use install.bat for end-user installs (real copy, no source dependency).

setlocal
set "TARGET=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\Cutaway"
set "SOURCE=%~dp0.."
REM Resolve SOURCE to an absolute path without trailing backslash.
for %%I in ("%SOURCE%") do set "SOURCE=%%~fI"

if exist "%TARGET%" (
    echo Removing existing install at:
    echo   %TARGET%
    rmdir /S /Q "%TARGET%" 2>nul
    if exist "%TARGET%" (
        REM Junctions can't be removed by rmdir if they're locked; fall back.
        rmdir "%TARGET%" 2>nul
    )
)

mklink /J "%TARGET%" "%SOURCE%" >nul
if errorlevel 1 (
    echo.
    echo Failed to create junction. Check that:
    echo   - Fusion isn't running (it can lock the folder).
    echo   - You have permission to write to %TARGET%'s parent.
    pause
    exit /b 1
)

echo.
echo Cutaway dev-linked:
echo   %TARGET%  -^>  %SOURCE%
echo.
echo Now every code change is live next time you Stop/Run the add-in in
echo Fusion's Scripts and Add-Ins panel — no install step needed.
echo.
pause
endlocal
