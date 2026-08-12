@echo off
setlocal EnableExtensions
title Auto-paste — web notepad
cd /d "%~dp0"

set "PORT=8765"
set "URL=http://127.0.0.1:%PORT%/"

where py >nul 2>nul && (
  echo Starting local notepad at %URL%
  echo Close this window to stop the server.
  start "" "%URL%"
  py -3 -m http.server %PORT% --bind 127.0.0.1
  goto :eof
)
where python >nul 2>nul && (
  echo Starting local notepad at %URL%
  echo Close this window to stop the server.
  start "" "%URL%"
  python -m http.server %PORT% --bind 127.0.0.1
  goto :eof
)

echo Python not found — opening index.html directly.
echo If the browser blocks the clipboard, install Python and run this again.
start "" "%~dp0index.html"
endlocal
