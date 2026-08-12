@echo off
setlocal EnableExtensions
title Auto-paste — 1. Install
cd /d "%~dp0"
color 0B
echo.
echo  ============================================================
echo   AUTO-PASTE   step 1 of 3   Install check
echo  ============================================================
echo.
echo  Nothing is downloaded. This just finds Python / Node /
echo  PowerShell and makes sure links.txt exists.
echo.

if not exist "%~dp0links.txt" (
  if exist "%~dp0examples\sample-links.txt" (
    copy /y "%~dp0examples\sample-links.txt" "%~dp0links.txt" >nul
    echo  Created links.txt from examples\sample-links.txt
  ) else (
    (
      echo # Auto-paste list — one string or URL per line
      echo # Lines starting with # are ignored
      echo https://example.com
    ) > "%~dp0links.txt"
    echo  Created a starter links.txt
  )
) else (
  echo  links.txt already present
)

set "ENGINE="
where py >nul 2>nul && set "ENGINE=py -3"
if not defined ENGINE (
  where python >nul 2>nul && set "ENGINE=python"
)

if defined ENGINE (
  echo  Python     found  ^(%ENGINE%^)
  %ENGINE% "%~dp0auto_paste.py" --doctor --list-file "%~dp0links.txt"
) else (
  echo  Python     not on PATH
  where node >nul 2>nul && (
    echo  Node       found
    node "%~dp0auto-paste.js" --doctor --list-file "%~dp0links.txt"
  ) || (
    echo  Node       not on PATH
    echo  PowerShell will be used as the fallback engine.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto_paste.ps1" -Doctor -ListFile "%~dp0links.txt"
  )
)

echo.
echo  Next:
echo    2. Double-click  2-Edit-list.bat   ^(optional^)
echo    3. Double-click  3-Start.bat
echo    Or skip install entirely:  OPEN-WEB.bat
echo.
pause
endlocal
