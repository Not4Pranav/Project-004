# Install Auto-paste

No package manager. No pip or npm packages. Windows first.

## Windows

1. Unzip or clone this folder.
2. Read `START-HERE.txt`.
3. Double-click **`1-Install.bat`** (same as `install.bat`).
4. **`2-Edit-list.bat`** — one unique string per line in `links.txt`.
5. **`3-Start.bat`** — red STOP window.
6. Click **START**, then click the text box in Chrome, Discord, Word, or
   `examples/custom-app.html`.

`1-Install.bat` only *looks* for an engine:

| Engine | Used for |
|---|---|
| Python 3 (`py -3` or `python`) | `auto_paste.py` (STOP window via tkinter) |
| Node.js | `auto-paste.js` |
| Windows PowerShell | `auto_paste.ps1` (WinForms STOP) |

Python is optional. PowerShell can send Ctrl+V and Enter by itself.

### Optional: install Python

<https://www.python.org/downloads/windows/>

Tick **“Add python.exe to PATH”**. Then run `1-Install.bat` again.

## macOS / Linux

Focused-app send is Windows-only. Use the browser:

```bash
python3 -m http.server 8765
# open http://127.0.0.1:8765/ and http://127.0.0.1:8765/examples/custom-app.html
python3 auto_paste.py --doctor
python3 test_auto_paste.py
```

## Verify

```bash
python3 test_auto_paste.py
python3 auto_paste.py --doctor
python3 auto_paste.py --send --no-gui --dry-run --countdown 0
```

`--dry-run` copies each unused line to the clipboard but does not press keys.

## Runtime files

| File | Where | Purpose |
|---|---|---|
| `links.txt` | this folder | lines to send |
| `.auto-paste-used` | this folder | already-sent lines (never repeat) |
| `.auto-paste-cursor` | this folder | `--next` position (Notepad mode) |

Nothing is written to Startup, the registry, or Program Files.

## Safety

Only text is copied and pasted. The keystrokes go to the window you
clicked after START. Hit the red **STOP** before leaving the computer.
