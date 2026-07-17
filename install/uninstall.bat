@echo off
REM Cutaway — Windows uninstall script.
REM Deletes the add-in from Fusion's per-user AddIns folder. Fusion may need
REM a restart to clear the entry from the Scripts and Add-Ins panel.
REM Works both from the downloaded zip AND from the copy inside the installed
REM folder itself (install.bat puts install\ there) — a script cannot delete
REM the folder it is running from, so that case is handed to a detached
REM helper in %TEMP% that runs after this window closes.

setlocal
set "TARGET=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\Cutaway"

if not exist "%TARGET%" (
    echo Cutaway not found at:
    echo   %TARGET%
    echo Nothing to remove.
    pause
    exit /b 0
)

echo Cutaway will be removed from:
echo   %TARGET%
echo Restart Fusion if it was running.
pause

REM Step out of the folder so an open working directory can't block rmdir.
cd /d "%TEMP%"

REM Running from INSIDE the installed folder? Hand off and exit.
echo %~dp0 | findstr /I /C:"%TARGET%" >nul
if not errorlevel 1 (
    (
        echo @echo off
        echo timeout /t 2 /nobreak ^>nul
        echo rmdir /S /Q "%TARGET%"
        echo del "%%~f0"
    ) > "%TEMP%\cutaway_uninstall_helper.bat"
    start "" /min cmd /c "%TEMP%\cutaway_uninstall_helper.bat"
    echo Removal will finish in the background.
    exit /b 0
)

rmdir /S /Q "%TARGET%"
echo Cutaway removed from:
echo   %TARGET%
pause
endlocal
