@echo off
setlocal EnableExtensions
title Auto-paste — 2. Edit list
cd /d "%~dp0"

if not exist "%~dp0links.txt" (
  if exist "%~dp0examples\sample-links.txt" (
    copy /y "%~dp0examples\sample-links.txt" "%~dp0links.txt" >nul
  ) else (
    (
      echo # Auto-paste list — one string or URL per line
      echo # Lines starting with # are ignored
      echo https://example.com
    ) > "%~dp0links.txt"
  )
)

echo Opening links.txt in Notepad.
echo One string or URL per line. Lines starting with # are ignored.
echo Close Notepad when you are done, then run 3-Start.bat.
start "" notepad.exe "%~dp0links.txt"
endlocal
