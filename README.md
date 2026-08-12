# Auto-paste

Copy a string once. It lands in Notepad — you never hit Ctrl+V.

Windows is the first-class path (double-click the numbered `.bat` files).
The same engine runs on macOS and Linux, and there is a browser notepad
that works without installing anything.

## Start here (Windows)

Read **`START-HERE.txt`**, then:

| Step | Double-click | What it does |
|---|---|---|
| 1 | `1-Install.bat` | Finds Python / Node / PowerShell, creates `links.txt` |
| 2 | `2-Edit-list.bat` | Opens `links.txt` in Notepad (optional) |
| 3 | `3-Start.bat` | Watches the clipboard and pastes into Notepad |

Same actions, other names:

- `install.bat` → `1-Install.bat`
- `EDIT-LINKS.bat` → `2-Edit-list.bat`
- `START.bat` → menu (watch, live, list, collect, web)
- `OPEN-WEB.bat` → browser notepad at `http://127.0.0.1:8765/`

## What you get

- **Clipboard watch** — every new copy opens / updates Notepad.
- **Live paste** — send the text into an already-open Notepad window.
- **Paste list** — `links.txt` holds URLs or any snippet, one per line.
- **Collect** — save each new copy into `links.txt` (no duplicates).
- **Web notepad** — `index.html` watches the clipboard in the browser.
- **Four engines** — Python, PowerShell, Node, and plain HTML.

Auto-paste only writes **text**. It never runs what you copy.

## Web notepad

Open `index.html`, or double-click `OPEN-WEB.bat`.

1. Click **Paste clipboard & keep watching** once so the browser may read the clipboard.
2. Copy anything in another window. It appears on the page.
3. Use the **List** drawer to keep snippets, import `links.txt`, or paste the whole list.

Also:

- **Paste now** — pull the current clipboard immediately
- **Auto-paste on/off** — pause the watcher
- **Append** — add the next copy under the current text
- New / Open / Save behave like a small notepad
- Shortcuts: `Ctrl+S` save, `Ctrl+N` new, `Ctrl+Shift+V` paste now, `?` help

## Windows (real Notepad)

```bat
auto_paste.bat
auto_paste.bat --watch
auto_paste.bat --live
auto_paste.bat --list
auto_paste.bat --next
auto_paste.bat --save-clip
auto_paste.bat --collect
auto_paste.bat --doctor
```

`--watch` keeps the script running and pastes again whenever the clipboard changes.
`--live` sends the text into an already-open Notepad window (Ctrl+V).
Without `--live`, the copied string is written to a temp file and opened in Notepad.

PowerShell:

```powershell
.\auto_paste.ps1
.\auto_paste.ps1 -Watch
.\auto_paste.ps1 -Live -Append
.\auto_paste.ps1 -List
.\auto_paste.ps1 -Next
.\auto_paste.ps1 -Collect
```

## Python (Windows, macOS, Linux)

No third-party packages.

```bash
python auto_paste.py
python auto_paste.py --watch
python auto_paste.py --list --list-file links.txt
python auto_paste.py --next
python auto_paste.py --save-clip
python auto_paste.py --collect
python auto_paste.py --doctor
```

On Windows this opens `notepad.exe`. Elsewhere it opens the default text
editor (`xdg-open` / TextEdit).

## Node.js (optional)

```bash
node auto-paste.js --watch
node auto-paste.js --list
node auto-paste.js --doctor
```

## The list file

`links.txt` is a plain-text paste list:

```
# comments and blank lines are ignored
https://example.com
a saved sentence
```

`examples/sample-links.txt` and `examples/snippets.txt` are ready-made lists.
`1-Install.bat` copies the sample into `links.txt` if the file is missing.

## Tests

```bash
python test_auto_paste.py
```

The tests cover list parsing, append / dedupe, the `--next` cursor, the
watch loop, and the CLI. They do not need a real clipboard or Notepad.

## Files

| File | Role |
|---|---|
| `START-HERE.txt` | First thing to read on Windows |
| `1-Install.bat` / `install.bat` | Install check |
| `2-Edit-list.bat` / `EDIT-LINKS.bat` | Edit `links.txt` |
| `3-Start.bat` | Start clipboard watch |
| `START.bat` | Menu |
| `OPEN-WEB.bat` | Serve / open the web notepad |
| `auto_paste.py` | Main engine |
| `auto_paste.bat` | Picks Python, Node, or PowerShell |
| `auto_paste.ps1` | PowerShell engine |
| `auto-paste.js` | Node engine |
| `index.html` | Browser notepad |
| `links.txt` | Your paste list |
| `INSTALL.md` | Longer install notes |
| `examples/` | Sample lists and command sheet |
| `test_auto_paste.py` | Unit tests |

More detail: **[INSTALL.md](INSTALL.md)**.
