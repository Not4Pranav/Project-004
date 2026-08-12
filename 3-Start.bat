@echo off
setlocal EnableExtensions
title Auto-paste — 3. Start
cd /d "%~dp0"
color 0C
echo.
echo  ============================================================
echo   AUTO-PASTE   step 3 of 3   Send unique lines
echo  ============================================================
echo.
echo  Each unused line is copied, pasted into the window you
echo  click, then Enter is pressed.
echo.
echo  Rate: 4 strings every 5 seconds. Never the same string twice.
echo  A red STOP button stays on top. Click it to halt.
echo.
echo  1. Click START on the control window.
echo  2. Immediately click the text box in Chrome, Discord, Word...
echo  3. Wait for the 3-second countdown.
echo.

call "%~dp0auto_paste.bat" --send
echo.
pause
endlocal
