#!/usr/bin/env python3
"""Tests for auto_paste.py — no live clipboard or Notepad required."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import auto_paste as ap


SAMPLE_LIST = """# Auto-paste list
# comments and blanks are ignored

https://example.com
https://example.org/docs

a saved snippet
"""


class ParseListTests(unittest.TestCase):
    def test_skips_comments_and_blanks(self) -> None:
        self.assertEqual(
            ap.parse_list(SAMPLE_LIST),
            [
                "https://example.com",
                "https://example.org/docs",
                "a saved snippet",
            ],
        )

    def test_empty(self) -> None:
        self.assertEqual(ap.parse_list(""), [])
        self.assertEqual(ap.parse_list("   \n# only a comment\n"), [])

    def test_strips_whitespace(self) -> None:
        self.assertEqual(ap.parse_list("  hello  \n"), ["hello"])

    def test_keeps_internal_spaces(self) -> None:
        self.assertEqual(ap.parse_list("hello world"), ["hello world"])


class MergeTextTests(unittest.TestCase):
    def test_empty_existing(self) -> None:
        self.assertEqual(ap.merge_text("", "new"), "new")

    def test_adds_newline(self) -> None:
        self.assertEqual(ap.merge_text("old", "new"), "old\nnew")

    def test_keeps_existing_newline(self) -> None:
        self.assertEqual(ap.merge_text("old\n", "new"), "old\nnew")


class ListFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "links.txt"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_missing_is_empty(self) -> None:
        self.assertEqual(ap.load_list(self.path), [])

    def test_load_utf8_bom(self) -> None:
        self.path.write_bytes(b"\xef\xbb\xbfhello\n")
        self.assertEqual(ap.load_list(self.path), ["hello"])

    def test_append_creates_and_dedupes(self) -> None:
        self.assertTrue(ap.append_to_list(self.path, "one"))
        self.assertTrue(ap.append_to_list(self.path, "two"))
        self.assertFalse(ap.append_to_list(self.path, "one"))
        self.assertFalse(ap.append_to_list(self.path, "   "))
        self.assertEqual(ap.load_list(self.path), ["one", "two"])

    def test_append_adds_missing_newline(self) -> None:
        self.path.write_text("one", encoding="utf-8")
        self.assertTrue(ap.append_to_list(self.path, "two"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "one\ntwo\n")

    def test_cursor_roundtrip(self) -> None:
        self.assertEqual(ap.read_cursor(self.path), 0)
        ap.write_cursor(self.path, 3)
        self.assertEqual(ap.read_cursor(self.path), 3)

    def test_cursor_corrupt_file(self) -> None:
        ap.cursor_path(self.path).write_text("nope", encoding="utf-8")
        self.assertEqual(ap.read_cursor(self.path), 0)


class NextItemTests(unittest.TestCase):
    def test_walks_and_wraps(self) -> None:
        items = ["a", "b", "c"]
        item, nxt = ap.next_item(items, 0)
        self.assertEqual((item, nxt), ("a", 1))
        item, nxt = ap.next_item(items, nxt)
        self.assertEqual((item, nxt), ("b", 2))
        item, nxt = ap.next_item(items, nxt)
        self.assertEqual((item, nxt), ("c", 0))
        item, nxt = ap.next_item(items, nxt)
        self.assertEqual((item, nxt), ("a", 1))

    def test_empty(self) -> None:
        self.assertEqual(ap.next_item([], 4), (None, 0))

    def test_format_list(self) -> None:
        self.assertEqual(ap.format_list(["a", "b"]), "a\nb")


class WatchLoopTests(unittest.TestCase):
    def test_applies_changes_then_stops(self) -> None:
        values = iter(["first", "first", "second", "second", "third"])
        seen: list[str] = []

        def get_text() -> str:
            try:
                return next(values)
            except StopIteration:
                return "third"

        ticks = {"n": 0}

        def should_continue() -> bool:
            ticks["n"] += 1
            return ticks["n"] < 5

        ap.watch_loop(
            get_text,
            seen.append,
            interval=0.0,
            should_continue=should_continue,
        )
        self.assertEqual(seen[0], "first")
        self.assertIn("second", seen)
        self.assertIn("third", seen)
        # unchanged polls must not re-apply
        self.assertEqual(seen, ["first", "second", "third"])

    def test_skips_empty_changes(self) -> None:
        seq = iter(["a", "", "b"])
        seen: list[str] = []
        ticks = {"n": 0}

        def get_text() -> str:
            try:
                return next(seq)
            except StopIteration:
                return "b"

        def should_continue() -> bool:
            ticks["n"] += 1
            return ticks["n"] < 4

        ap.watch_loop(get_text, seen.append, 0.0, should_continue=should_continue)
        self.assertEqual(seen, ["a", "b"])


class WriteAndOpenTests(unittest.TestCase):
    def test_write_and_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.txt"
            with patch.object(ap, "_open_editor"):
                ap.write_and_open("hello", append=False, dest=dest)
                ap.write_and_open("world", append=True, dest=dest)
            self.assertEqual(dest.read_text(encoding="utf-8"), "hello\nworld")


class CliTests(unittest.TestCase):
    def test_help(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            with self.assertRaises(SystemExit) as ctx:
                ap.build_parser().parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Auto-paste", buf.getvalue())

    def test_doctor_missing_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.txt"
            with patch.object(ap, "get_clipboard", side_effect=RuntimeError("no clip")):
                code = ap.run_doctor(missing)
            self.assertEqual(code, 1)

    def test_doctor_with_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.txt"
            path.write_text("https://example.com\n", encoding="utf-8")
            with patch.object(ap, "get_clipboard", return_value="hi"):
                code = ap.run_doctor(path)
            self.assertEqual(code, 0)

    def test_list_mode_opens_joined_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.txt"
            path.write_text("# c\nhttps://a.example\nhttps://b.example\n", encoding="utf-8")
            opened: list[str] = []

            def fake_apply(text: str, *, live: bool, append: bool) -> None:
                opened.append(text)
                self.assertFalse(live)
                self.assertFalse(append)

            with patch.object(ap, "apply_text", side_effect=fake_apply):
                code = ap.main(["--list", "--list-file", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(opened, ["https://a.example\nhttps://b.example"])

    def test_list_mode_empty_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.txt"
            path.write_text("# nothing\n", encoding="utf-8")
            code = ap.main(["--list", "--list-file", str(path)])
            self.assertEqual(code, 1)

    def test_next_advances_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.txt"
            path.write_text("one\ntwo\n", encoding="utf-8")
            seen: list[str] = []
            with patch.object(ap, "apply_text", side_effect=lambda t, **_: seen.append(t)):
                self.assertEqual(ap.main(["--next", "--list-file", str(path)]), 0)
                self.assertEqual(ap.main(["--next", "--list-file", str(path)]), 0)
            self.assertEqual(seen, ["one", "two"])
            self.assertEqual(ap.read_cursor(path), 0)

    def test_save_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.txt"
            with patch.object(ap, "get_clipboard", return_value="https://saved.example"):
                self.assertEqual(ap.main(["--save-clip", "--list-file", str(path)]), 0)
                self.assertEqual(ap.main(["--save-clip", "--list-file", str(path)]), 1)
            self.assertEqual(ap.load_list(path), ["https://saved.example"])

    def test_once_mode_uses_clipboard(self) -> None:
        opened: list[str] = []
        with patch.object(ap, "get_clipboard", return_value="copied"):
            with patch.object(ap, "write_and_open", side_effect=lambda t, append: opened.append(t) or Path("x")):
                code = ap.main([])
        self.assertEqual(code, 0)
        self.assertEqual(opened, ["copied"])


class UniqueAndUsedTests(unittest.TestCase):
    def test_unique_preserves_order(self) -> None:
        self.assertEqual(ap.unique_lines(["a", "b", "a", "c", "b"]), ["a", "b", "c"])

    def test_unused_filters_used_and_dupes(self) -> None:
        self.assertEqual(
            ap.unused_lines(["a", "b", "a", "c"], {"b"}),
            ["a", "c"],
        )

    def test_used_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.txt"
            self.assertEqual(ap.load_used(path), set())
            ap.append_used(path, "one")
            ap.append_used(path, "two")
            self.assertEqual(ap.load_used(path), {"one", "two"})
            ap.clear_used(path)
            self.assertEqual(ap.load_used(path), set())

    def test_interval_is_four_per_five(self) -> None:
        self.assertAlmostEqual(ap.send_interval(4, 5), 1.25)

    def test_next_allowed_at_caps_rate(self) -> None:
        times = [0.0, 1.0, 2.0, 3.0]
        self.assertEqual(ap.next_allowed_at(times, now=3.0, rate_count=4, rate_window=5.0), 5.0)
        self.assertEqual(ap.next_allowed_at(times, now=5.1, rate_count=4, rate_window=5.0), 5.1)


class SendSessionTests(unittest.TestCase):
    def test_copies_pastes_enters_marks_used(self) -> None:
        copied: list[str] = []
        pastes = {"n": 0}
        used: list[str] = []
        result = ap.run_send_session(
            ["one", "one", "two", "three"],
            used={"three"},
            mark_used=used.append,
            copy_text=copied.append,
            paste_enter=lambda: pastes.__setitem__("n", pastes["n"] + 1),
            sleep=lambda _dt: None,
            countdown=0,
            rate_count=4,
            rate_window=5,
        )
        self.assertEqual(copied, ["one", "two"])
        self.assertEqual(pastes["n"], 2)
        self.assertEqual(used, ["one", "two"])
        self.assertEqual(result["sent"], 2)
        self.assertEqual(result["skipped"], 1)
        self.assertFalse(result["stopped"])

    def test_stop_midway(self) -> None:
        copied: list[str] = []
        calls = {"n": 0}

        def should_stop() -> bool:
            return len(copied) >= 2

        def sleeper(_dt: float) -> None:
            calls["n"] += 1

        result = ap.run_send_session(
            ["a", "b", "c", "d"],
            copy_text=copied.append,
            paste_enter=lambda: None,
            should_stop=should_stop,
            sleep=sleeper,
            countdown=0,
        )
        self.assertEqual(copied, ["a", "b"])
        self.assertTrue(result["stopped"])
        self.assertEqual(result["sent"], 2)
        self.assertEqual(result["remaining"], 2)

    def test_countdown_can_be_stopped(self) -> None:
        result = ap.run_send_session(
            ["a"],
            copy_text=lambda _t: None,
            paste_enter=lambda: None,
            should_stop=lambda: True,
            sleep=lambda _dt: None,
            countdown=3,
        )
        self.assertTrue(result["stopped"])
        self.assertEqual(result["sent"], 0)

    def test_dry_run_does_not_press_keys(self) -> None:
        pastes = {"n": 0}
        copied: list[str] = []
        ap.run_send_session(
            ["x"],
            copy_text=copied.append,
            paste_enter=lambda: pastes.__setitem__("n", pastes["n"] + 1),
            sleep=lambda _dt: None,
            dry_run=True,
            countdown=0,
        )
        self.assertEqual(copied, ["x"])
        self.assertEqual(pastes["n"], 0)

    def test_send_cli_no_gui_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.txt"
            path.write_text("# none\n", encoding="utf-8")
            code = ap.main(["--send", "--no-gui", "--list-file", str(path)])
            self.assertEqual(code, 1)

    def test_send_cli_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.txt"
            path.write_text("alpha\nbeta\nalpha\n", encoding="utf-8")
            copied: list[str] = []
            with patch.object(ap, "set_clipboard", side_effect=copied.append):
                with patch.object(ap, "send_paste_enter"):
                    code = ap.main(
                        [
                            "--send",
                            "--no-gui",
                            "--dry-run",
                            "--countdown",
                            "0",
                            "--rate-window",
                            "0.01",
                            "--list-file",
                            str(path),
                        ]
                    )
            self.assertEqual(code, 0)
            self.assertEqual(copied, ["alpha", "beta"])
            self.assertEqual(ap.load_used(path), {"alpha", "beta"})


if __name__ == "__main__":
    raise SystemExit(unittest.main(verbosity=2))
