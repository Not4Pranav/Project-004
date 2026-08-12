#!/usr/bin/env python3
"""Auto-paste — copy once, it lands in Notepad.

Examples:
  python auto_paste.py                 # open Notepad with the copied string
  python auto_paste.py --live          # Ctrl+V into an already-open Notepad
  python auto_paste.py --watch         # re-paste whenever the clipboard changes
  python auto_paste.py --append        # add to the end instead of replacing
  python auto_paste.py --list          # dump links.txt into Notepad
  python auto_paste.py --next          # paste the next unused list item
  python auto_paste.py --save-clip     # append the clipboard to links.txt
  python auto_paste.py --collect       # watch clipboard and save each new copy
  python auto_paste.py --doctor        # check clipboard / editor / list file
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_LIST = HERE / "links.txt"
WATCH_FILE = Path(tempfile.gettempdir()) / "auto-paste-notepad.txt"
CURSOR_NAME = ".auto-paste-cursor"


# ---------------------------------------------------------------------------
# List file (links.txt)
# ---------------------------------------------------------------------------

def parse_list(text: str) -> list[str]:
    """Return non-empty, non-comment lines from a paste-list file."""
    items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def load_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = path.read_text(encoding="utf-8-sig")
    return parse_list(data)


def merge_text(existing: str, incoming: str) -> str:
    """Append incoming to existing, inserting a newline if needed."""
    if not existing:
        return incoming
    if not existing.endswith("\n"):
        existing += "\n"
    return existing + incoming


def append_to_list(path: Path, text: str) -> bool:
    """Append a unique item to the list file. Returns True if written."""
    item = text.strip("\r\n")
    if not item.strip():
        return False
    existing = load_list(path)
    if item in existing:
        return False
    prefix = ""
    if path.exists() and path.stat().st_size:
        data = path.read_bytes()
        if not data.endswith(b"\n"):
            prefix = "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + item + "\n")
    return True


def cursor_path(list_path: Path) -> Path:
    return list_path.with_name(CURSOR_NAME)


def read_cursor(list_path: Path) -> int:
    path = cursor_path(list_path)
    if not path.exists():
        return 0
    try:
        value = int(path.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0
    return max(0, value)


def write_cursor(list_path: Path, index: int) -> None:
    cursor_path(list_path).write_text(str(index), encoding="utf-8")


def next_item(items: Sequence[str], index: int) -> tuple[Optional[str], int]:
    """Return (item, next_index). next_index wraps to 0 after the last item."""
    if not items:
        return None, 0
    index = index % len(items)
    return items[index], (index + 1) % len(items)


def format_list(items: Iterable[str]) -> str:
    return "\n".join(items)


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------

def get_clipboard() -> str:
    if sys.platform == "win32":
        return _clipboard_windows()

    env = os.environ
    commands: list[list[str]] = []
    if env.get("WAYLAND_DISPLAY"):
        commands.append(["wl-paste", "-n"])
    if env.get("DISPLAY"):
        commands.extend(
            [
                ["xclip", "-selection", "clipboard", "-o"],
                ["xsel", "--clipboard", "--output"],
            ]
        )
    commands.append(["pbpaste"])  # macOS

    last_err: Optional[BaseException] = None
    for cmd in commands:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return out.decode("utf-8", errors="replace")
        except (FileNotFoundError, subprocess.CalledProcessError) as err:
            last_err = err
    raise RuntimeError(
        "Could not read the clipboard. Install xclip/xsel/wl-clipboard "
        "or use the web notepad (index.html / OPEN-WEB.bat)."
    ) from last_err


def _clipboard_windows() -> str:
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13

    if not user32.OpenClipboard(None):
        raise RuntimeError("OpenClipboard failed")
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        kernel32.GlobalLock.restype = ctypes.c_void_p
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _set_clipboard_windows(text: str) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    data = text.encode("utf-16-le") + b"\x00\x00"
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    ptr = kernel32.GlobalLock(handle)
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    user32.OpenClipboard(None)
    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, handle)
    finally:
        user32.CloseClipboard()


# ---------------------------------------------------------------------------
# Editors / Notepad
# ---------------------------------------------------------------------------

def write_and_open(text: str, append: bool, dest: Optional[Path] = None) -> Path:
    path = dest or WATCH_FILE
    if append and path.exists():
        existing = path.read_text(encoding="utf-8")
        text = merge_text(existing, text)
    path.write_text(text, encoding="utf-8")
    _open_editor(path)
    return path


def _open_editor(path: Path) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["notepad.exe", str(path)], close_fds=True)
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-t", str(path)])
        return
    for cmd in (
        ["xdg-open", str(path)],
        ["gedit", str(path)],
        ["kate", str(path)],
        ["mousepad", str(path)],
        ["nano", str(path)],
    ):
        try:
            subprocess.Popen(cmd)
            return
        except FileNotFoundError:
            continue
    print(f"Saved clipboard to {path}", file=sys.stderr)


def paste_live(text: str, append: bool) -> None:
    if sys.platform != "win32":
        raise RuntimeError("--live is only supported on Windows Notepad")

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowExW.restype = wintypes.HWND

    hwnd = user32.FindWindowW("Notepad", None)
    if not hwnd:
        subprocess.Popen(["notepad.exe"])
        for _ in range(20):
            time.sleep(0.1)
            hwnd = user32.FindWindowW("Notepad", None)
            if hwnd:
                break
    if not hwnd:
        raise RuntimeError("Could not find or start Notepad")

    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.15)

    edit = user32.FindWindowExW(hwnd, None, "Edit", None)
    if not edit:
        edit = user32.FindWindowExW(hwnd, None, "RichEditD2DPT", None)

    WM_SETTEXT = 0x000C
    EM_SETSEL = 0x00B1
    EM_REPLACESEL = 0x00C2

    if edit:
        if append:
            user32.SendMessageW(edit, EM_SETSEL, 0xFFFFFFFF, 0xFFFFFFFF)
            user32.SendMessageW(edit, EM_REPLACESEL, True, text)
        else:
            user32.SendMessageW(edit, WM_SETTEXT, 0, text)
        return

    # Win11 Notepad (no classic Edit child): type via Ctrl+A / Ctrl+V
    _set_clipboard_windows(text)
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL, VK_A, VK_V = 0x11, 0x41, 0x56

    def tap(vk: int) -> None:
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    if not append:
        tap(VK_A)
    tap(VK_V)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


# ---------------------------------------------------------------------------
# Watch loop
# ---------------------------------------------------------------------------

def watch_loop(
    get_text: Callable[[], str],
    apply: Callable[[str], None],
    interval: float,
    *,
    should_continue: Optional[Callable[[], bool]] = None,
    skip_empty: bool = True,
    apply_first: bool = True,
) -> None:
    """Poll get_text and call apply when the value changes.

    should_continue, if set, is checked each tick; return False to stop.
    """
    last = ""
    if apply_first:
        first = get_text()
        if first or not skip_empty:
            apply(first)
        last = first

    while True:
        if should_continue is not None and not should_continue():
            return
        time.sleep(interval)
        current = get_text()
        if current == last:
            continue
        if skip_empty and not current:
            last = current
            continue
        last = current
        apply(current)


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------

def run_doctor(list_file: Path) -> int:
    print("Auto-paste doctor")
    print(f"  Python     {sys.version.split()[0]}  ({sys.executable})")
    print(f"  Platform   {sys.platform}")
    print(f"  Script     {Path(__file__).resolve()}")
    print(f"  List file  {list_file}")

    items = load_list(list_file) if list_file.exists() else None
    if items is None:
        print("  List       missing (2-Edit-list.bat will create it)")
    else:
        print(f"  List       {len(items)} item(s)")

    clip_ok = False
    clip_err = ""
    try:
        text = get_clipboard()
        clip_ok = True
        preview = text.replace("\n", "\\n")
        if len(preview) > 60:
            preview = preview[:57] + "..."
        print(f"  Clipboard  ok ({len(text)} chars) {preview!r}")
    except Exception as err:  # noqa: BLE001 — doctor must never crash
        clip_err = str(err)
        print(f"  Clipboard  not readable ({clip_err})")

    if sys.platform == "win32":
        print("  Editor     notepad.exe")
    elif sys.platform == "darwin":
        print("  Editor     TextEdit (open -t)")
    else:
        print("  Editor     xdg-open / gedit / kate / mousepad")

    print()
    if clip_ok:
        print("Ready. Run 3-Start.bat (or python auto_paste.py --watch).")
        return 0
    print("Clipboard backend missing. Use OPEN-WEB.bat for the browser notepad,")
    print("or install xclip / xsel / wl-clipboard on Linux.")
    return 0 if items is not None else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto-paste the clipboard (or links.txt) into Notepad"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Paste into an open Notepad window (Windows)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep pasting when the clipboard changes",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append instead of replace",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.6,
        help="Watch poll interval in seconds",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="dump_list",
        help="Paste every item in the list file into Notepad",
    )
    parser.add_argument(
        "--next",
        action="store_true",
        dest="next_item",
        help="Paste the next unused item from the list file",
    )
    parser.add_argument(
        "--save-clip",
        action="store_true",
        help="Append the current clipboard to the list file",
    )
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Watch the clipboard and append each new copy to the list",
    )
    parser.add_argument(
        "--list-file",
        type=Path,
        default=DEFAULT_LIST,
        help="Path to the paste list (default: links.txt next to this script)",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check clipboard, editor, and list file, then exit",
    )
    return parser


def apply_text(text: str, *, live: bool, append: bool) -> None:
    if not text:
        print("Clipboard is empty.", file=sys.stderr)
        return
    if live:
        paste_live(text, append=append)
        print(f"Pasted {len(text)} characters into Notepad.")
    else:
        path = write_and_open(text, append=append)
        print(f"Opened {path} ({len(text)} characters).")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    list_file = Path(args.list_file)

    if args.doctor:
        return run_doctor(list_file)

    if args.save_clip:
        text = get_clipboard()
        if append_to_list(list_file, text):
            print(f"Saved to {list_file}")
            return 0
        print("Nothing new to save (empty or already in the list).", file=sys.stderr)
        return 1

    if args.dump_list:
        items = load_list(list_file)
        if not items:
            print(f"No items in {list_file}. Edit it with 2-Edit-list.bat.", file=sys.stderr)
            return 1
        apply_text(format_list(items), live=args.live, append=args.append)
        return 0

    if args.next_item:
        items = load_list(list_file)
        if not items:
            print(f"No items in {list_file}. Edit it with 2-Edit-list.bat.", file=sys.stderr)
            return 1
        item, nxt = next_item(items, read_cursor(list_file))
        assert item is not None
        apply_text(item, live=args.live, append=args.append)
        write_cursor(list_file, nxt)
        print(f"Next up: item {nxt + 1} of {len(items)}" if items else "")
        return 0

    if args.collect:
        print(f"Collecting copies into {list_file}. Ctrl+C to stop.")

        def collect(text: str) -> None:
            if append_to_list(list_file, text):
                print(f"+ {text.splitlines()[0][:80]}")
            else:
                print("(skipped empty or duplicate)")

        try:
            watch_loop(get_clipboard, collect, args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    def apply(text: str) -> None:
        apply_text(text, live=args.live, append=args.append)

    text = get_clipboard()
    apply(text)

    if not args.watch:
        return 0

    print("Watching clipboard — copy something else to auto-paste. Ctrl+C to stop.")
    try:
        watch_loop(
            get_clipboard,
            apply,
            args.interval,
            apply_first=False,
        )
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
