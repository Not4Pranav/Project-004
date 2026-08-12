# Auto-paste into Notepad

Copy a string, and it lands in Notepad without you hitting Ctrl+V.

## Web notepad (works in the browser)

Open `index.html`. Click **Paste clipboard & keep watching** once so the browser can read the clipboard. After that, every new copy is pasted into the page automatically.

- **Paste now** — pull the current clipboard immediately
- **Auto-paste on/off** — watch for new copies
- New / Open / Save behave like a small notepad

## Windows (real Notepad)

Double-click `auto_paste.bat`, or from a terminal:

```bat
auto_paste.bat
auto_paste.bat --watch
auto_paste.bat --live
```

`--watch` keeps the script running and pastes again whenever the clipboard changes.  
`--live` sends the text into an already-open Notepad window (Ctrl+V).  
Without `--live`, the copied string is written to a temp file and opened in Notepad.

PowerShell:

```powershell
.\auto_paste.ps1
.\auto_paste.ps1 -Watch
.\auto_paste.ps1 -Live -Append
```

## Python (Windows, macOS, Linux)

```bash
python auto_paste.py
python auto_paste.py --watch
```

On Windows this opens `notepad.exe`. Elsewhere it opens the default text editor (`xdg-open` / TextEdit).
