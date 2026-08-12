#!/usr/bin/env node
/**
 * Auto-paste — Node.js companion to auto_paste.py
 *
 *   node auto-paste.js
 *   node auto-paste.js --watch
 *   node auto-paste.js --list
 *   node auto-paste.js --next
 *   node auto-paste.js --save-clip
 *   node auto-paste.js --collect
 *   node auto-paste.js --doctor
 *
 * No npm packages. Uses the OS clipboard tools (PowerShell / pbpaste / xclip).
 */

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const HERE = __dirname;
const DEFAULT_LIST = path.join(HERE, "links.txt");
const WATCH_FILE = path.join(os.tmpdir(), "auto-paste-notepad.txt");
const CURSOR_NAME = ".auto-paste-cursor";

function parseArgs(argv) {
  const args = {
    watch: false,
    live: false,
    append: false,
    dumpList: false,
    nextItem: false,
    saveClip: false,
    collect: false,
    doctor: false,
    interval: 0.6,
    listFile: DEFAULT_LIST,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--watch") args.watch = true;
    else if (a === "--live") args.live = true;
    else if (a === "--append") args.append = true;
    else if (a === "--list") args.dumpList = true;
    else if (a === "--next") args.nextItem = true;
    else if (a === "--save-clip") args.saveClip = true;
    else if (a === "--collect") args.collect = true;
    else if (a === "--doctor") args.doctor = true;
    else if (a === "--help" || a === "-h") args.help = true;
    else if (a === "--interval") args.interval = Number(argv[++i]);
    else if (a === "--list-file") args.listFile = argv[++i];
    else throw new Error("Unknown argument: " + a);
  }
  return args;
}

function parseList(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

function loadList(file) {
  if (!fs.existsSync(file)) return [];
  return parseList(fs.readFileSync(file, "utf8"));
}

function appendToList(file, text) {
  const item = String(text || "").replace(/[\r\n]+$/, "");
  if (!item.trim()) return false;
  const existing = loadList(file);
  if (existing.includes(item)) return false;
  let prefix = "";
  if (fs.existsSync(file)) {
    const data = fs.readFileSync(file);
    if (data.length && data[data.length - 1] !== 10) prefix = "\n";
  }
  fs.appendFileSync(file, prefix + item + "\n", "utf8");
  return true;
}

function cursorPath(listFile) {
  return path.join(path.dirname(listFile), CURSOR_NAME);
}

function readCursor(listFile) {
  const p = cursorPath(listFile);
  if (!fs.existsSync(p)) return 0;
  const n = parseInt(fs.readFileSync(p, "utf8").trim(), 10);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

function writeCursor(listFile, index) {
  fs.writeFileSync(cursorPath(listFile), String(index), "utf8");
}

function runCapture(cmd, args) {
  const res = spawnSync(cmd, args, { encoding: "utf8" });
  if (res.error) throw res.error;
  if (res.status !== 0) {
    const err = new Error((res.stderr || "command failed").trim());
    err.status = res.status;
    throw err;
  }
  return res.stdout.replace(/\r?\n$/, "");
}

function getClipboard() {
  if (process.platform === "win32") {
    return runCapture("powershell", [
      "-NoProfile",
      "-Command",
      "Get-Clipboard -Raw",
    ]);
  }
  if (process.platform === "darwin") {
    return runCapture("pbpaste", []);
  }
  const tries = [
    ["wl-paste", ["-n"]],
    ["xclip", ["-selection", "clipboard", "-o"]],
    ["xsel", ["--clipboard", "--output"]],
  ];
  let last = null;
  for (const [cmd, args] of tries) {
    try {
      return runCapture(cmd, args);
    } catch (err) {
      last = err;
    }
  }
  throw last || new Error("Could not read the clipboard");
}

function openEditor(file) {
  if (process.platform === "win32") {
    spawn("notepad.exe", [file], { detached: true, stdio: "ignore" }).unref();
    return;
  }
  if (process.platform === "darwin") {
    spawn("open", ["-t", file], { detached: true, stdio: "ignore" }).unref();
    return;
  }
  spawn("xdg-open", [file], { detached: true, stdio: "ignore" }).unref();
}

function writeAndOpen(text, append) {
  if (append && fs.existsSync(WATCH_FILE)) {
    let existing = fs.readFileSync(WATCH_FILE, "utf8");
    if (existing && !existing.endsWith("\n")) existing += "\n";
    text = existing + text;
  }
  fs.writeFileSync(WATCH_FILE, text, "utf8");
  openEditor(WATCH_FILE);
  return WATCH_FILE;
}

function applyText(text, { live, append }) {
  if (!text) {
    console.error("Clipboard is empty.");
    return;
  }
  if (live && process.platform !== "win32") {
    throw new Error("--live is only supported on Windows Notepad");
  }
  if (live) {
    // Best-effort: put text on the clipboard and let the Python/PS live
    // path handle SendKeys. Node has no SendKeys without extra deps.
    console.error("--live in Node opens Notepad with a file instead (no SendKeys).");
  }
  const dest = writeAndOpen(text, append);
  console.log(`Opened ${dest} (${text.length} characters).`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function watchLoop(getText, apply, interval, applyFirst) {
  let last = "";
  if (applyFirst) {
    last = getText();
    apply(last);
  } else {
    last = getText();
  }
  for (;;) {
    await sleep(interval * 1000);
    const current = getText();
    if (current && current !== last) {
      last = current;
      apply(current);
    }
  }
}

function printHelp() {
  console.log(`Auto-paste — copy once, it lands in Notepad.

Usage:
  node auto-paste.js [options]

Options:
  --watch          Re-paste when the clipboard changes
  --live           Windows live paste (falls back to file open in Node)
  --append         Append instead of replace
  --list           Dump links.txt into Notepad
  --next           Paste the next unused list item
  --save-clip      Append the clipboard to links.txt
  --collect        Watch clipboard and save each new copy
  --list-file P    Path to the paste list
  --interval N     Watch poll interval in seconds (default 0.6)
  --doctor         Check clipboard / list file
  -h, --help       Show this help
`);
}

async function main(argv) {
  const args = parseArgs(argv);
  if (args.help) {
    printHelp();
    return 0;
  }

  if (args.doctor) {
    console.log("Auto-paste doctor (Node)");
    console.log("  Node       " + process.version);
    console.log("  Platform   " + process.platform);
    console.log("  List file  " + args.listFile);
    const items = loadList(args.listFile);
    console.log("  List       " + items.length + " item(s)");
    try {
      const text = getClipboard();
      console.log("  Clipboard  ok (" + text.length + " chars)");
    } catch (err) {
      console.log("  Clipboard  not readable (" + err.message + ")");
    }
    return 0;
  }

  if (args.saveClip) {
    if (appendToList(args.listFile, getClipboard())) {
      console.log("Saved to " + args.listFile);
      return 0;
    }
    console.error("Nothing new to save (empty or already in the list).");
    return 1;
  }

  if (args.dumpList) {
    const items = loadList(args.listFile);
    if (!items.length) {
      console.error("No items in " + args.listFile + ". Edit it with 2-Edit-list.bat.");
      return 1;
    }
    applyText(items.join("\n"), args);
    return 0;
  }

  if (args.nextItem) {
    const items = loadList(args.listFile);
    if (!items.length) {
      console.error("No items in " + args.listFile + ". Edit it with 2-Edit-list.bat.");
      return 1;
    }
    const idx = readCursor(args.listFile) % items.length;
    applyText(items[idx], args);
    writeCursor(args.listFile, (idx + 1) % items.length);
    return 0;
  }

  const apply = (text) => applyText(text, args);

  if (args.collect) {
    console.log("Collecting copies into " + args.listFile + ". Ctrl+C to stop.");
    await watchLoop(
      getClipboard,
      (text) => {
        if (appendToList(args.listFile, text)) {
          console.log("+ " + String(text).split(/\r?\n/)[0].slice(0, 80));
        } else {
          console.log("(skipped empty or duplicate)");
        }
      },
      args.interval,
      true
    );
    return 0;
  }

  apply(getClipboard());
  if (!args.watch) return 0;

  console.log("Watching clipboard — copy something else to auto-paste. Ctrl+C to stop.");
  await watchLoop(getClipboard, apply, args.interval, false);
  return 0;
}

if (require.main === module) {
  main(process.argv.slice(2)).then(
    (code) => process.exit(code),
    (err) => {
      console.error(err.message || err);
      process.exit(1);
    }
  );
}

module.exports = { parseList, parseArgs, appendToList, loadList };
