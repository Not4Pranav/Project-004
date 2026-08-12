@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Auto-paste
cd /d "%~dp0"
color 0B

:menu
cls
echo.
echo  ============================================================
echo   AUTO-PASTE
echo   Unique line  -^>  copy  -^>  paste  -^>  Enter
echo   4 every 5 seconds   red STOP
echo  ============================================================
echo.
echo    1^) SEND into the app you click   ^(Chrome / Discord / Word^)
echo    2^) Watch clipboard  -^>  Notepad
echo    3^) Live-paste into an already-open Notepad
echo    4^) Dump links.txt into Notepad
echo    5^) Collect copies into links.txt
echo    6^) Open the web notepad
echo    7^) Open the practice app  ^(custom-app.html^)
echo    8^) Edit links.txt
echo    9^) Install / doctor check
echo    Q^) Quit
echo.
set "choice="
set /p "choice=  Choose [1]: "
if "%choice%"=="" set "choice=1"

if /I "%choice%"=="Q" goto :eof
if "%choice%"=="1" goto send
if "%choice%"=="2" goto watch
if "%choice%"=="3" goto live
if "%choice%"=="4" goto dump
if "%choice%"=="5" goto collect
if "%choice%"=="6" goto web
if "%choice%"=="7" goto app
if "%choice%"=="8" goto edit
if "%choice%"=="9" goto install
echo  Unknown choice.
pause
goto menu

:send
echo.
call "%~dp0auto_paste.bat" --send
echo.
pause
goto menu

:watch
echo.
call "%~dp0auto_paste.bat" --watch
echo.
pause
goto menu

:live
echo.
call "%~dp0auto_paste.bat" --live --watch
echo.
pause
goto menu

:dump
echo.
call "%~dp0auto_paste.bat" --list
echo.
pause
goto menu

:collect
echo.
call "%~dp0auto_paste.bat" --collect
echo.
pause
goto menu

:web
call "%~dp0OPEN-WEB.bat"
goto menu

:app
if exist "%~dp0examples\custom-app.html" (
  start "" "%~dp0examples\custom-app.html"
) else (
  echo  examples\custom-app.html is missing.
  pause
)
goto menu

:edit
call "%~dp02-Edit-list.bat"
goto menu

:install
call "%~dp01-Install.bat"
goto menu
