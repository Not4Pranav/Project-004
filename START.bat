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
echo   Copy once. It lands in Notepad.
echo  ============================================================
echo.
echo    1^) Watch clipboard  -^>  Notepad
echo    2^) Live-paste into an already-open Notepad
echo    3^) Paste everything in links.txt
echo    4^) Paste the next item from links.txt
echo    5^) Collect copies into links.txt
echo    6^) Open the web notepad
echo    7^) Edit links.txt
echo    8^) Install / doctor check
echo    Q^) Quit
echo.
set "choice="
set /p "choice=  Choose [1]: "
if "%choice%"=="" set "choice=1"

if /I "%choice%"=="Q" goto :eof
if "%choice%"=="1" goto watch
if "%choice%"=="2" goto live
if "%choice%"=="3" goto dump
if "%choice%"=="4" goto next
if "%choice%"=="5" goto collect
if "%choice%"=="6" goto web
if "%choice%"=="7" goto edit
if "%choice%"=="8" goto install
echo  Unknown choice.
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

:next
echo.
call "%~dp0auto_paste.bat" --next
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

:edit
call "%~dp02-Edit-list.bat"
goto menu

:install
call "%~dp01-Install.bat"
goto menu
