@echo off
REM Cutaway — Windows uninstall script.
REM Deletes the add-in from Fusion's per-user AddIns folder. Fusion may need
REM a restart to clear the entry from the Scripts and Add-Ins panel.

setlocal
set "TARGET=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\Cutaway"

if not exist "%TARGET%" (
    echo Cutaway not found at:
    echo   %TARGET%
    echo Nothing to remove.
    pause
    exit /b 0
)

rmdir /S /Q "%TARGET%"
echo Cutaway removed from:
echo   %TARGET%
echo Restart Fusion if it was running.
pause
endlocal
