#!/usr/bin/env python3
"""
Unique String Generator
Generates unique random strings and copies them to the clipboard.
Does not inject keystrokes or send messages to any application.
"""

from __future__ import annotations

import secrets
import string
import time
import tkinter as tk
from tkinter import ttk, messagebox


ALPHABET = string.ascii_letters + string.digits
MAX_COPIES_PER_WINDOW = 4
WINDOW_SECONDS = 5.0


class UniqueStringApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Unique String Generator")
        self.minsize(480, 420)
        self.geometry("560x480")
        self.configure(bg="#111318")

        self.used: set[str] = set()
        self.copy_times: list[float] = []

        self.length_var = tk.IntVar(value=16)
        self.count_var = tk.StringVar(value="Generated: 0  |  Unique in session: 0")
        self.status_var = tk.StringVar(value="Ready. Generate, then copy. Paste yourself.")
        self.preview_var = tk.StringVar(value="")
        self.auto_copy_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 8}

        header = tk.Label(
            self,
            text="Unique String Generator",
            font=("Segoe UI", 18, "bold"),
            fg="#f4f4f5",
            bg="#111318",
        )
        header.pack(anchor="w", padx=16, pady=(16, 4))

        sub = tk.Label(
            self,
            text="Creates unused random strings and copies them to the clipboard only.\n"
            "This app never types into other windows and never presses Enter.",
            font=("Segoe UI", 10),
            fg="#a1a1aa",
            bg="#111318",
            justify="left",
        )
        sub.pack(anchor="w", padx=16, pady=(0, 8))

        card = tk.Frame(self, bg="#1b1e27")
        card.pack(fill="x", padx=16, pady=8)

        tk.Label(
            card, text="Length", fg="#e4e4e7", bg="#1b1e27", font=("Segoe UI", 10)
        ).grid(row=0, column=0, sticky="w", padx=12, pady=12)

        length = tk.Scale(
            card,
            from_=8,
            to=64,
            orient="horizontal",
            variable=self.length_var,
            bg="#1b1e27",
            fg="#e4e4e7",
            highlightthickness=0,
            troughcolor="#2a2e3a",
            length=280,
        )
        length.grid(row=0, column=1, sticky="ew", padx=12, pady=12)
        card.columnconfigure(1, weight=1)

        preview_box = tk.Entry(
            self,
            textvariable=self.preview_var,
            font=("Consolas", 14),
            bg="#0d0f14",
            fg="#e4e4e7",
            insertbackground="#e4e4e7",
            relief="flat",
        )
        preview_box.pack(fill="x", padx=16, pady=8)
        preview_box.configure(state="readonly")

        btns = tk.Frame(self, bg="#111318")
        btns.pack(fill="x", padx=16, pady=8)

        style_kwargs = {
            "font": ("Segoe UI", 11, "bold"),
            "relief": "flat",
            "bd": 0,
            "padx": 14,
            "pady": 10,
            "cursor": "hand2",
        }

        tk.Button(
            btns,
            text="Generate unique string",
            command=self.generate,
            bg="#3b82f6",
            fg="white",
            activebackground="#2563eb",
            **style_kwargs,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btns,
            text="Copy to clipboard",
            command=self.copy_current,
            bg="#27272a",
            fg="white",
            activebackground="#3f3f46",
            **style_kwargs,
        ).pack(side="left", padx=8)

        tk.Button(
            btns,
            text="Generate + copy",
            command=self.generate_and_copy,
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            **style_kwargs,
        ).pack(side="left", padx=8)

        tk.Label(
            self,
            textvariable=self.count_var,
            font=("Segoe UI", 10),
            fg="#d4d4d8",
            bg="#111318",
        ).pack(anchor="w", **pad)

        tk.Label(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#111318",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 16))

        note = tk.Label(
            self,
            text="Copy rate is limited to 4 clipboard copies every 5 seconds so you cannot burst-paste.",
            font=("Segoe UI", 8),
            fg="#71717a",
            bg="#111318",
        )
        note.pack(anchor="w", padx=16, pady=(0, 12))

    def _new_unique(self) -> str:
        length = int(self.length_var.get())
        for _ in range(2000):
            value = "".join(secrets.choice(ALPHABET) for _ in range(length))
            if value not in self.used:
                self.used.add(value)
                return value
        raise RuntimeError("Could not find an unused string. Increase length.")

    def generate(self) -> str:
        try:
            value = self._new_unique()
        except RuntimeError as exc:
            messagebox.showerror("Generator", str(exc))
            return ""
        self.preview_var.set(value)
        self.preview_box.selection_range(0, tk.END)
        self.preview_box.focus_set()
        self.count_var.set(
            f"Generated: {len(self.used)}  |  Unique in session: {len(self.used)}"
        )
        self.status_var.set("New unique string ready. Copy it, then paste yourself.")
        if self.auto_copy_var.get():
            self.copy_current()
        return value

    def _allow_copy(self) -> bool:
        now = time.monotonic()
        self.copy_times = [t for t in self.copy_times if now - t < WINDOW_SECONDS]
        if len(self.copy_times) >= MAX_COPIES_PER_WINDOW:
            wait = WINDOW_SECONDS - (now - self.copy_times[0])
            self.status_var.set(
                f"Copy limit: at most {MAX_COPIES_PER_WINDOW} copies / {int(WINDOW_SECONDS)}s. "
                f"Wait {wait:.1f}s."
            )
            return False
        self.copy_times.append(now)
        return True

    def copy_current(self) -> None:
        value = self.preview_var.get().strip()
        if not value:
            self.status_var.set("Generate a string first.")
            return
        if not self._allow_copy():
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        self.status_var.set("Copied to clipboard. Paste it yourself where you need it.")

    def generate_and_copy(self) -> None:
        value = self.generate()
        if value:
            self.copy_current()


if __name__ == "__main__":
    app = UniqueStringApp()
    app.mainloop()
