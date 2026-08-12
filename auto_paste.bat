@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (
  py -3 "%~dp0auto_paste.py" %*
  goto :eof
)
where python >nul 2>nul && (
  python "%~dp0auto_paste.py" %*
  goto :eof
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto_paste.ps1" %*
