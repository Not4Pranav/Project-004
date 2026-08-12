# Unique String Generator

Desktop utility that creates **unique random strings** and copies them to the **clipboard**.

It does **not**:

- type into other applications
- press Enter
- send messages on WhatsApp, Discord, or anywhere else

## Run from source

Needs Python 3.10+ with Tkinter (included with the official Windows installer).

```bat
python unique_string_generator.py
```

## Build a Windows .exe

On a Windows machine with Python installed:

```bat
build_windows.bat
```

Output: `dist\UniqueStringGenerator.exe`

## Limits

- Each generated string is unique for the current session.
- Clipboard copy is limited to **4 copies every 5 seconds**.
