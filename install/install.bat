@echo off
REM Cutaway — Windows install script.
REM Copies the add-in to Fusion's per-user AddIns folder so Fusion will pick
REM it up the next time Scripts and Add-Ins is opened.

setlocal
set "TARGET=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\Cutaway"

if not exist "%TARGET%" mkdir "%TARGET%"

REM Source = the folder that contains this script's parent.
REM %~dp0 is "...\install\", so .. is the add-in root.
set "SOURCE=%~dp0.."

xcopy /E /I /Y /Q "%SOURCE%\Cutaway.py" "%TARGET%\" >nul
xcopy /E /I /Y /Q "%SOURCE%\Cutaway.manifest" "%TARGET%\" >nul
xcopy /E /I /Y /Q "%SOURCE%\version.json" "%TARGET%\" >nul

REM Clear src/resources before copying (matches install.sh) so files that a
REM newer version renamed or deleted don't linger from the previous install.
if exist "%TARGET%\src" rmdir /S /Q "%TARGET%\src"
if exist "%TARGET%\resources" rmdir /S /Q "%TARGET%\resources"

xcopy /E /I /Y /Q "%SOURCE%\src" "%TARGET%\src\" >nul
xcopy /E /I /Y /Q "%SOURCE%\resources" "%TARGET%\resources\" >nul

REM Also copy the install/uninstall scripts INTO the installed folder, so the
REM user can uninstall later even after deleting the downloaded zip.
if exist "%TARGET%\install" rmdir /S /Q "%TARGET%\install"
xcopy /E /I /Y /Q "%SOURCE%\install" "%TARGET%\install\" >nul

echo.
echo Cutaway installed to:
echo   %TARGET%
echo.
echo Next steps:
echo   1. Open Fusion 360 (or restart if it was running).
echo   2. Open: UTILITIES tab -^> Add-Ins -^> Scripts and Add-Ins -^> Add-Ins tab.
echo   3. Find "Cutaway" in the My Add-Ins list and click Run.
echo   4. Tick "Run on Startup" so it launches automatically next time.
echo.
pause
endlocal
