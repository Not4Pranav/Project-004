@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Auto-paste

where py >nul 2>nul && (
  py -3 "%~dp0auto_paste.py" %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>nul && (
  python "%~dp0auto_paste.py" %*
  exit /b %ERRORLEVEL%
)
where node >nul 2>nul && (
  node "%~dp0auto-paste.js" %*
  exit /b %ERRORLEVEL%
)

rem Map GNU-style flags so the PowerShell fallback understands 3-Start.bat.
set "PSARGS="
:map
if "%~1"=="" goto runps
if /I "%~1"=="--send" set "PSARGS=!PSARGS! -Send" & shift & goto map
if /I "%~1"=="--watch" set "PSARGS=!PSARGS! -Watch" & shift & goto map
if /I "%~1"=="--live" set "PSARGS=!PSARGS! -Live" & shift & goto map
if /I "%~1"=="--append" set "PSARGS=!PSARGS! -Append" & shift & goto map
if /I "%~1"=="--list" set "PSARGS=!PSARGS! -List" & shift & goto map
if /I "%~1"=="--next" set "PSARGS=!PSARGS! -Next" & shift & goto map
if /I "%~1"=="--save-clip" set "PSARGS=!PSARGS! -SaveClip" & shift & goto map
if /I "%~1"=="--collect" set "PSARGS=!PSARGS! -Collect" & shift & goto map
if /I "%~1"=="--doctor" set "PSARGS=!PSARGS! -Doctor" & shift & goto map
if /I "%~1"=="--reset-used" set "PSARGS=!PSARGS! -ResetUsed" & shift & goto map
if /I "%~1"=="--dry-run" set "PSARGS=!PSARGS! -DryRun" & shift & goto map
if /I "%~1"=="--interval" set "PSARGS=!PSARGS! -Interval %~2" & shift & shift & goto map
if /I "%~1"=="--countdown" set "PSARGS=!PSARGS! -Countdown %~2" & shift & shift & goto map
if /I "%~1"=="--rate-count" set "PSARGS=!PSARGS! -RateCount %~2" & shift & shift & goto map
if /I "%~1"=="--rate-window" set "PSARGS=!PSARGS! -RateWindow %~2" & shift & shift & goto map
if /I "%~1"=="--list-file" set "PSARGS=!PSARGS! -ListFile `"%~2`"" & shift & shift & goto map
set "PSARGS=!PSARGS! %~1"
shift
goto map

:runps
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto_paste.ps1" !PSARGS!
exit /b %ERRORLEVEL%
