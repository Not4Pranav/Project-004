# Auto-paste

Fully automatic on Windows: each **unique** line from `links.txt` is
copied, pasted into the app you clicked (Chrome, Discord, Word, …),
then **Enter** is pressed.

- **4 strings every 5 seconds**
- **Never sends the same string twice**
- Runs until the **red STOP** button (or the list is finished)

The old Notepad watcher and the browser notepad are still here.

## Start here (Windows)

Read **`START-HERE.txt`**, then:

| Step | Double-click | What it does |
|---|---|---|
| 1 | `1-Install.bat` | Finds Python / Node / PowerShell, creates `links.txt` |
| 2 | `2-Edit-list.bat` | One unique string per line |
| 3 | `3-Start.bat` | Red STOP window → click your text box → send |

Then click **START**, immediately click the text box in Chrome / Discord /
Word, and wait 3 seconds.

Same actions, other names:

- `install.bat` → `1-Install.bat`
- `EDIT-LINKS.bat` → `2-Edit-list.bat`
- `START.bat` → menu (send is the default)
- `OPEN-WEB.bat` → browser notepad

Python is optional. If it is missing, PowerShell still runs the sender.

## What happens

1. Unused unique lines are read from `links.txt` (comments and dupes dropped).
2. Each line is **copied** to the clipboard.
3. **Ctrl+V** is sent to the window you clicked, then **Enter**.
4. The line is recorded in `.auto-paste-used` so it is never sent again.
5. The next line waits `5 / 4 = 1.25` seconds (4 every 5 seconds).
6. **STOP** aborts between lines.

Practice without Discord/Word: open `examples/custom-app.html`, click the
composer, then run `3-Start.bat`. The page also has its own START / red STOP
demo.

## Web notepad

`index.html` / `OPEN-WEB.bat`:

- **Paste clipboard & keep watching** — copies land in the page
- **Send list** — unique unused lines, 4 every 5 seconds, **red STOP**
- List drawer can import `links.txt`

Browsers cannot type into other desktop apps. Use `3-Start.bat` for that.

## Commands

```bat
auto_paste.bat --send
auto_paste.bat --send --reset-used
auto_paste.bat --send --dry-run --no-gui
auto_paste.bat --watch
auto_paste.bat --doctor
```

```bash
python auto_paste.py --send
python auto_paste.py --send --no-gui --countdown 3
python test_auto_paste.py
```

```powershell
.\auto_paste.ps1 -Send
```

Focused-app send (Ctrl+V, Enter) is **Windows-only**. On macOS/Linux use the
web notepad or `examples/custom-app.html`.

## Files

| File | Role |
|---|---|
| `START-HERE.txt` | First thing to read |
| `1-Install.bat` / `install.bat` | Install check |
| `2-Edit-list.bat` / `EDIT-LINKS.bat` | Edit `links.txt` |
| `3-Start.bat` | Send + red STOP |
| `START.bat` | Menu |
| `OPEN-WEB.bat` | Web notepad |
| `auto_paste.py` | Main engine |
| `auto_paste.bat` / `.ps1` / `auto-paste.js` | Launchers |
| `index.html` | Browser notepad |
| `examples/custom-app.html` | Practice target |
| `links.txt` | Your unique lines |
| `test_auto_paste.py` | Unit tests |

More detail: **[INSTALL.md](INSTALL.md)**.
