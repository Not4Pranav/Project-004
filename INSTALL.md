# Install Auto-paste

Auto-paste does **not** need a package manager. There are no pip or npm
dependencies. Pick one path.

## Windows (recommended)

1. Unzip or clone this folder anywhere.
2. Read `START-HERE.txt`.
3. Double-click **`1-Install.bat`** (same as `install.bat`).
4. Optional: **`2-Edit-list.bat`** / `EDIT-LINKS.bat` to edit `links.txt`.
5. Double-click **`3-Start.bat`**. Copy any text.

`1-Install.bat` only *looks* for an engine, in this order:

| Engine | Used for |
|---|---|
| Python 3 (`py -3` or `python`) | `auto_paste.py` |
| Node.js | `auto-paste.js` |
| Windows PowerShell | `auto_paste.ps1` |

Python is optional. If it is missing, PowerShell still runs the Notepad
watcher. The browser notepad (`OPEN-WEB.bat`) needs no engine at all,
though Python is used to serve `index.html` on `http://127.0.0.1:8765/`
so the Clipboard API is allowed.

### Optional: install Python

<https://www.python.org/downloads/windows/>

Tick **“Add python.exe to PATH”**. Then run `1-Install.bat` again.

### Optional: install Node.js

<https://nodejs.org/> — only if you want `node auto-paste.js`.

## macOS / Linux

```bash
python3 auto_paste.py --doctor
python3 auto_paste.py --watch
```

Clipboard tools:

| System | Package |
|---|---|
| macOS | built-in `pbpaste` |
| Linux X11 | `xclip` or `xsel` (`sudo apt install xclip`) |
| Linux Wayland | `wl-clipboard` (`sudo apt install wl-clipboard`) |

Without those, open `index.html` in a browser (or `python3 -m http.server 8765`).

## Verify

```bash
python3 test_auto_paste.py
python3 auto_paste.py --doctor
```

`--doctor` prints the Python version, whether `links.txt` exists, and
whether the clipboard can be read. It does not change any files.

## What is created at runtime

| File | Where | Purpose |
|---|---|---|
| `links.txt` | this folder | your paste list (you edit it) |
| `.auto-paste-cursor` | this folder | remembers `--next` position |
| `auto-paste-notepad.txt` | system temp | file opened in Notepad |

Nothing is written to Startup, the registry, or Program Files.
