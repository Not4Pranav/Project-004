@echo off
setlocal EnableExtensions
title Auto-paste — 3. Start
cd /d "%~dp0"
color 0A
echo.
echo  ============================================================
echo   AUTO-PASTE   step 3 of 3   Watching clipboard
echo  ============================================================
echo.
echo  Copy any text. It will open / update Notepad by itself.
echo  Press Ctrl+C in this window to stop.
echo.

call "%~dp0auto_paste.bat" --watch
echo.
pause
endlocal
