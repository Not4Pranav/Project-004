@echo off
setlocal
python -m pip install --upgrade pip pyinstaller
pyinstaller --noconfirm --onefile --windowed --name UniqueStringGenerator unique_string_generator.py
echo.
echo Built EXE (if PyInstaller succeeded): dist\UniqueStringGenerator.exe
pause
