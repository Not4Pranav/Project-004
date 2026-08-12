@echo off
setlocal EnableExtensions
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

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto_paste.ps1" %*
exit /b %ERRORLEVEL%
