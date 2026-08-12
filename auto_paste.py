#!/usr/bin/env python3
"""Paste the current clipboard into Notepad (Windows) or a text editor.

Examples:
  python auto_paste.py              # open Notepad with the copied string
  python auto_paste.py --live       # Ctrl+V into an already-open Notepad
  python auto_paste.py --watch      # re-paste whenever the clipboard changes
  python auto_paste.py --append     # add to the end instead of replacing
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WATCH_FILE = Path(tempfile.gettempdir()) / "auto-paste-notepad.txt"


def get_clipboard() -> str:
    if sys.platform == "win32":
        return _clipboard_windows()

    env = os.environ
    commands = []
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

    last_err = None
    for cmd in commands:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return out.decode("utf-8", errors="replace")
        except (FileNotFoundError, subprocess.CalledProcessError) as err:
            last_err = err
    raise RuntimeError(
        "Could not read the clipboard. Install xclip/xsel/wl-clipboard "
        "or use the web notepad (index.html)."
    ) from last_err


def _clipboard_windows() -> str:
    import ctypes
    from ctypes import wintypes

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


def write_and_open(text: str, append: bool) -> Path:
    if append and WATCH_FILE.exists():
        existing = WATCH_FILE.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
        text = existing + text
    WATCH_FILE.write_text(text, encoding="utf-8")
    _open_editor(WATCH_FILE)
    return WATCH_FILE


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


def _set_clipboard_windows(text: str) -> None:
    import ctypes
    from ctypes import wintypes

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-paste the clipboard into Notepad")
    parser.add_argument("--live", action="store_true", help="Paste into an open Notepad window")
    parser.add_argument("--watch", action="store_true", help="Keep pasting when the clipboard changes")
    parser.add_argument("--append", action="store_true", help="Append instead of replace")
    parser.add_argument("--interval", type=float, default=0.6, help="Watch poll interval in seconds")
    args = parser.parse_args()

    def apply(text: str) -> None:
        if not text:
            print("Clipboard is empty.", file=sys.stderr)
            return
        if args.live:
            paste_live(text, append=args.append)
            print(f"Pasted {len(text)} characters into Notepad.")
        else:
            path = write_and_open(text, append=args.append)
            print(f"Opened {path} ({len(text)} characters).")

    text = get_clipboard()
    apply(text)
    last = text

    if not args.watch:
        return 0

    print("Watching clipboard — copy something else to auto-paste. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(args.interval)
            current = get_clipboard()
            if current and current != last:
                last = current
                apply(current)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
