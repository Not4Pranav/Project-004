#!/usr/bin/env python3
"""Auto-paste — unique lines, copied, pasted, Enter.

Default send mode (3-Start.bat):
  each unused line → clipboard → Ctrl+V into the window you clicked → Enter
  4 strings every 5 seconds, never the same string twice
  red STOP button (or Ctrl+C)

Also:
  python auto_paste.py --watch       # clipboard → Notepad
  python auto_paste.py --live        # Ctrl+V into an open Notepad
  python auto_paste.py --list        # dump links.txt into Notepad
  python auto_paste.py --doctor
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_LIST = HERE / "links.txt"
WATCH_FILE = Path(tempfile.gettempdir()) / "auto-paste-notepad.txt"
CURSOR_NAME = ".auto-paste-cursor"
USED_NAME = ".auto-paste-used"
RATE_COUNT = 4
RATE_WINDOW = 5.0
DEFAULT_COUNTDOWN = 3.0


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


def unique_lines(items: Sequence[str]) -> list[str]:
    """Preserve order, drop exact duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def unused_lines(items: Sequence[str], used: Iterable[str]) -> list[str]:
    used_set = set(used)
    return [item for item in unique_lines(items) if item not in used_set]


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


def used_path(list_path: Path) -> Path:
    return list_path.with_name(USED_NAME)


def load_used(list_path: Path) -> set[str]:
    path = used_path(list_path)
    if not path.exists():
        return set()
    return set(parse_list(path.read_text(encoding="utf-8-sig")))


def append_used(list_path: Path, item: str) -> None:
    path = used_path(list_path)
    prefix = ""
    if path.exists() and path.stat().st_size:
        data = path.read_bytes()
        if not data.endswith(b"\n"):
            prefix = "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + item.replace("\r", " ").replace("\n", " ") + "\n")


def clear_used(list_path: Path) -> None:
    path = used_path(list_path)
    if path.exists():
        path.unlink()


def send_interval(rate_count: int = RATE_COUNT, rate_window: float = RATE_WINDOW) -> float:
    count = max(1, int(rate_count))
    window = max(0.05, float(rate_window))
    return window / count


def next_allowed_at(
    sent_times: Sequence[float],
    now: float,
    rate_count: int = RATE_COUNT,
    rate_window: float = RATE_WINDOW,
) -> float:
    """Earliest timestamp we may send another string (max N per window)."""
    recent = [t for t in sent_times if now - t < rate_window]
    if len(recent) < rate_count:
        return now
    return min(recent) + rate_window


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


def set_clipboard(text: str) -> None:
    if sys.platform == "win32":
        _set_clipboard_windows(text)
        return
    payload = text.encode("utf-8")
    env = os.environ
    commands: list[list[str]] = []
    if env.get("WAYLAND_DISPLAY"):
        commands.append(["wl-copy"])
    if env.get("DISPLAY"):
        commands.extend(
            [
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ]
        )
    commands.append(["pbcopy"])
    last_err: Optional[BaseException] = None
    for cmd in commands:
        try:
            subprocess.run(cmd, input=payload, check=True, stderr=subprocess.DEVNULL)
            return
        except (FileNotFoundError, subprocess.CalledProcessError) as err:
            last_err = err
    raise RuntimeError("Could not write the clipboard.") from last_err


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
    if not user32.OpenClipboard(None):
        raise RuntimeError("OpenClipboard failed")
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

    _set_clipboard_windows(text)
    _tap_hotkey(select_all=not append, paste=True, enter=False)


# ---------------------------------------------------------------------------
# Focused-app send (Chrome, Discord, Word, …)
# ---------------------------------------------------------------------------

def get_foreground_hwnd() -> int:
    if sys.platform != "win32":
        return 0
    import ctypes

    return int(ctypes.windll.user32.GetForegroundWindow() or 0)


def focus_hwnd(hwnd: int) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    import ctypes

    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)


def send_paste_enter(hwnd: Optional[int] = None) -> None:
    """Paste (Ctrl+V) then Enter into the target window."""
    if sys.platform != "win32":
        raise RuntimeError(
            "Focused-app send (Ctrl+V, Enter) is Windows-only. "
            "Use index.html or examples/custom-app.html on this computer."
        )
    if hwnd:
        focus_hwnd(hwnd)
        time.sleep(0.08)
    _tap_hotkey(select_all=False, paste=True, enter=True)


def _tap_hotkey(*, select_all: bool, paste: bool, enter: bool) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL, VK_A, VK_V, VK_RETURN = 0x11, 0x41, 0x56, 0x0D

    def tap(vk: int) -> None:
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    if select_all or paste:
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        if select_all:
            tap(VK_A)
        if paste:
            tap(VK_V)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    if enter:
        time.sleep(0.04)
        tap(VK_RETURN)


def run_send_session(
    items: Sequence[str],
    *,
    used: Optional[set[str]] = None,
    mark_used: Optional[Callable[[str], None]] = None,
    copy_text: Optional[Callable[[str], None]] = None,
    paste_enter: Optional[Callable[[], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
    sleep: Callable[[float], None] = time.sleep,
    on_status: Optional[Callable[[str], None]] = None,
    on_item: Optional[Callable[[str, int, int], None]] = None,
    countdown: float = 0.0,
    rate_count: int = RATE_COUNT,
    rate_window: float = RATE_WINDOW,
    dry_run: bool = False,
) -> dict:
    """Copy each unused unique line, paste, press Enter. Rate-limited.

    Returns {sent, skipped, stopped, remaining}.
    """
    if copy_text is None:
        copy_text = set_clipboard
    if paste_enter is None:
        paste_enter = lambda: send_paste_enter()
    used_set = set(used or [])
    queue = unused_lines(items, used_set)
    skipped = len(unique_lines(items)) - len(queue)
    sent = 0
    interval = send_interval(rate_count, rate_window)

    def stopped() -> bool:
        return bool(should_stop and should_stop())

    def say(msg: str) -> None:
        if on_status:
            on_status(msg)

    remaining_cd = max(0.0, float(countdown))
    while remaining_cd > 0:
        if stopped():
            return {"sent": 0, "skipped": skipped, "stopped": True, "remaining": len(queue)}
        say(f"Click the text box now — sending in {int(remaining_cd + 0.999)}…")
        step = min(0.2, remaining_cd)
        sleep(step)
        remaining_cd -= step

    total = len(queue)
    for index, item in enumerate(queue):
        if stopped():
            return {
                "sent": sent,
                "skipped": skipped,
                "stopped": True,
                "remaining": total - sent,
            }
        if on_item:
            on_item(item, index + 1, total)
        say(f"Sending {index + 1}/{total}: {item[:60]}")
        try:
            copy_text(item)
        except Exception as err:
            if not dry_run:
                raise
            say(f"(clipboard write skipped: {err})")
        if not dry_run:
            paste_enter()
        used_set.add(item)
        if mark_used:
            mark_used(item)
        sent += 1
        if index < total - 1:
            waited = 0.0
            while waited < interval:
                if stopped():
                    return {
                        "sent": sent,
                        "skipped": skipped,
                        "stopped": True,
                        "remaining": total - sent,
                    }
                step = min(0.1, interval - waited)
                sleep(step)
                waited += step

    say("Done — every unique unused line was sent.")
    return {"sent": sent, "skipped": skipped, "stopped": False, "remaining": 0}


def run_send_console(
    list_file: Path,
    *,
    countdown: float,
    rate_count: int,
    rate_window: float,
    dry_run: bool,
    reset_used: bool,
) -> int:
    if reset_used:
        clear_used(list_file)
    items = load_list(list_file)
    queue = unused_lines(items, load_used(list_file))
    if not queue:
        print(f"Nothing left to send in {list_file}. Add lines or use --reset-used.", file=sys.stderr)
        return 1
    print(f"{len(queue)} unique unused line(s). {rate_count} every {rate_window:g}s.")
    print("Click the text box in Chrome, Discord, Word, … then wait for the countdown.")
    print("Ctrl+C = STOP.")
    stop = {"flag": False}

    def handle_status(msg: str) -> None:
        print(msg)

    try:
        result = run_send_session(
            items,
            used=load_used(list_file),
            mark_used=lambda item: append_used(list_file, item),
            should_stop=lambda: stop["flag"],
            on_status=handle_status,
            countdown=countdown,
            rate_count=rate_count,
            rate_window=rate_window,
            dry_run=dry_run,
        )
    except KeyboardInterrupt:
        print("\nSTOP")
        return 0
    print(
        f"Sent {result['sent']}, skipped {result['skipped']} already-used, "
        f"remaining {result['remaining']}."
    )
    return 0


def run_send_gui(
    list_file: Path,
    *,
    countdown: float,
    rate_count: int,
    rate_window: float,
    dry_run: bool,
    reset_used: bool,
) -> int:
    try:
        import tkinter as tk
    except ImportError:
        print("tkinter not available — using console STOP (Ctrl+C).", file=sys.stderr)
        return run_send_console(
            list_file,
            countdown=countdown,
            rate_count=rate_count,
            rate_window=rate_window,
            dry_run=dry_run,
            reset_used=reset_used,
        )

    if reset_used:
        clear_used(list_file)

    root = tk.Tk()
    root.title("Auto-paste — STOP")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(bg="#1c1d21")

    stop_event = threading.Event()
    started = {"on": False}
    our_hwnd = {"id": 0}
    target_hwnd = {"id": 0}
    status_var = tk.StringVar(
        value="Click START, then click the text box (Chrome, Discord, Word…)."
    )
    preview_var = tk.StringVar(value=_preview_line(list_file))
    count_var = tk.StringVar(value=_count_label(list_file))

    frame = tk.Frame(root, bg="#1c1d21", padx=16, pady=14)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text="AUTO-PASTE",
        fg="#ffffff",
        bg="#1c1d21",
        font=("Segoe UI", 14, "bold"),
    ).pack(anchor="w")
    tk.Label(
        frame,
        text=f"{rate_count} unique strings every {rate_window:g}s  ·  never repeats  ·  copy → paste → Enter",
        fg="#9aa1b2",
        bg="#1c1d21",
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(0, 8))
    tk.Label(
        frame,
        textvariable=count_var,
        fg="#d5d8e0",
        bg="#1c1d21",
        font=("Segoe UI", 10),
    ).pack(anchor="w")
    tk.Label(
        frame,
        textvariable=preview_var,
        fg="#8eb0ff",
        bg="#1c1d21",
        font=("Consolas", 10),
        wraplength=420,
        justify="left",
    ).pack(anchor="w", pady=(2, 8))
    tk.Label(
        frame,
        textvariable=status_var,
        fg="#ffe08a",
        bg="#1c1d21",
        font=("Segoe UI", 10),
        wraplength=420,
        justify="left",
    ).pack(anchor="w", pady=(0, 10))

    btn_row = tk.Frame(frame, bg="#1c1d21")
    btn_row.pack(fill="x")

    def set_status(msg: str) -> None:
        root.after(0, status_var.set, msg)

    def refresh_labels() -> None:
        count_var.set(_count_label(list_file))
        preview_var.set(_preview_line(list_file))

    def capture_target() -> None:
        hwnd = get_foreground_hwnd()
        if hwnd and hwnd != our_hwnd["id"]:
            target_hwnd["id"] = hwnd

    def do_paste_enter() -> None:
        capture_target()
        send_paste_enter(target_hwnd["id"] or None)

    def worker() -> None:
        try:
            result = run_send_session(
                load_list(list_file),
                used=load_used(list_file),
                mark_used=lambda item: append_used(list_file, item),
                paste_enter=do_paste_enter if not dry_run else (lambda: None),
                should_stop=stop_event.is_set,
                on_status=set_status,
                on_item=lambda item, i, n: root.after(
                    0,
                    lambda it=item, ii=i, nn=n: preview_var.set(f"{ii}/{nn}  {it}"),
                ),
                countdown=countdown,
                rate_count=rate_count,
                rate_window=rate_window,
                dry_run=dry_run,
            )
            root.after(0, refresh_labels)
            if result["stopped"]:
                set_status(f"STOP — sent {result['sent']}, {result['remaining']} left.")
            else:
                set_status(f"Done. Sent {result['sent']} unique line(s).")
        except Exception as err:  # noqa: BLE001
            set_status(f"Error: {err}")

    def start() -> None:
        if started["on"]:
            return
        queue = unused_lines(load_list(list_file), load_used(list_file))
        if not queue:
            status_var.set("Nothing left to send. Edit the list or Reset used.")
            return
        started["on"] = True
        stop_event.clear()
        start_btn.configure(state="disabled")
        our_hwnd["id"] = get_foreground_hwnd()
        threading.Thread(target=worker, daemon=True).start()

    def stop() -> None:
        stop_event.set()
        status_var.set("STOP — finishing current keystroke…")

    def reset() -> None:
        stop_event.set()
        clear_used(list_file)
        started["on"] = False
        start_btn.configure(state="normal")
        refresh_labels()
        status_var.set("Used list cleared. Click START when ready.")

    start_btn = tk.Button(
        btn_row,
        text="START",
        command=start,
        bg="#2b5dff",
        fg="#ffffff",
        activebackground="#1d3db8",
        activeforeground="#ffffff",
        relief="flat",
        font=("Segoe UI", 12, "bold"),
        width=10,
        height=2,
        cursor="hand2",
    )
    start_btn.pack(side="left", padx=(0, 8))

    stop_btn = tk.Button(
        btn_row,
        text="STOP",
        command=stop,
        bg="#d0122d",
        fg="#ffffff",
        activebackground="#9a0c20",
        activeforeground="#ffffff",
        relief="flat",
        font=("Segoe UI", 16, "bold"),
        width=16,
        height=2,
        cursor="hand2",
    )
    stop_btn.pack(side="left", padx=(0, 8))

    tk.Button(
        btn_row,
        text="Reset used",
        command=reset,
        bg="#3a3d46",
        fg="#ffffff",
        activebackground="#2a2d34",
        activeforeground="#ffffff",
        relief="flat",
        font=("Segoe UI", 9),
        cursor="hand2",
    ).pack(side="left")

    root.protocol("WM_DELETE_WINDOW", lambda: (stop_event.set(), root.destroy()))
    root.after(80, lambda: (root.lift(), root.focus_force()))
    root.mainloop()
    return 0


def _count_label(list_file: Path) -> str:
    items = unique_lines(load_list(list_file))
    used = load_used(list_file)
    left = unused_lines(items, used)
    return f"{len(left)} left  ·  {len(used)} already sent  ·  {len(items)} unique in list"


def _preview_line(list_file: Path) -> str:
    queue = unused_lines(load_list(list_file), load_used(list_file))
    if not queue:
        return "Next: (none)"
    return "Next: " + queue[0]


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
        uniq = unique_lines(items)
        used = load_used(list_file)
        left = unused_lines(uniq, used)
        print(f"  List       {len(items)} line(s), {len(uniq)} unique, {len(left)} unused")

    try:
        text = get_clipboard()
        preview = text.replace("\n", "\\n")
        if len(preview) > 60:
            preview = preview[:57] + "..."
        print(f"  Clipboard  ok ({len(text)} chars) {preview!r}")
        clip_ok = True
    except Exception as err:  # noqa: BLE001 — doctor must never crash
        print(f"  Clipboard  not readable ({err})")
        clip_ok = False

    if sys.platform == "win32":
        print("  Send       Ctrl+V then Enter into the focused app (Chrome, Discord, Word…)")
        print("  Editor     notepad.exe (watch / list modes)")
    else:
        print("  Send       Windows-only — use examples/custom-app.html here")
        print("  Editor     default text editor (watch / list modes)")

    print()
    print("Ready. Run 3-Start.bat (copy → paste → Enter, red STOP).")
    if not clip_ok and sys.platform != "win32":
        print("Clipboard backend missing on this OS; the Windows send path still works.")
    return 0 if items is not None else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Auto-paste: unique lines → copy → paste into the app you clicked → Enter. "
            "4 every 5 seconds. Red STOP."
        )
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send unused unique lines into the focused app (default for 3-Start.bat)",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Console send mode (Ctrl+C = STOP) instead of the red STOP window",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Copy each line to the clipboard but do not press keys",
    )
    parser.add_argument(
        "--reset-used",
        action="store_true",
        help="Forget already-sent lines before starting",
    )
    parser.add_argument(
        "--countdown",
        type=float,
        default=DEFAULT_COUNTDOWN,
        help="Seconds to click the target text box after START (default 3)",
    )
    parser.add_argument(
        "--rate-count",
        type=int,
        default=RATE_COUNT,
        help="How many strings per rate window (default 4)",
    )
    parser.add_argument(
        "--rate-window",
        type=float,
        default=RATE_WINDOW,
        help="Rate window in seconds (default 5)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Paste into an open Notepad window (Windows)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep pasting when the clipboard changes (Notepad / editor)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append instead of replace (watch / list modes)",
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
        help="Paste the next unused item from the list file into Notepad",
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

    if args.send:
        runner = run_send_console if args.no_gui else run_send_gui
        return runner(
            list_file,
            countdown=args.countdown,
            rate_count=args.rate_count,
            rate_window=args.rate_window,
            dry_run=args.dry_run,
            reset_used=args.reset_used,
        )

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
