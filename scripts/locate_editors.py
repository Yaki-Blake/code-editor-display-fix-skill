#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate installed code editors on Windows and show where each keeps its config.

Read-only. Run this first when a user reports a display problem: it answers
"which editor is actually installed, and which file do I have to open?".

Usage:
  python locate_editors.py            # scan and report
  python locate_editors.py --json     # machine-readable output
"""
import glob
import json
import os
import subprocess
import sys
import time

# kind: ini  -> read key lines (gbk-safe)
#       json -> read key names
#       reg  -> registry-based (Visual Studio)
EDITORS = [
    {
        "id": "devcpp6",
        "name": "Dev-C++ 6.x (Embarcadero)",
        "process": "devcpp.exe",
        "configs": [r"%APPDATA%\Embarcadero\Dev-Cpp\devcpp.ini"],
        "kind": "ini",
        "watch": [("Editor.Font", "Name="), ("Editor.Font", "Charset="),
                  ("Editor.Font", "Size="), ("Editor.Syntax", "Comment="),
                  ("Editor.Syntax", "Space="), ("Editor", "NewDocEncoding=")],
    },
    {
        "id": "devcpp511",
        "name": "Dev-C++ 5.11 (Orwell)",
        "process": "devcpp.exe",
        "configs": [r"%APPDATA%\Dev-Cpp\devcpp.ini"],
        "kind": "ini",
        "watch": [("Editor.Font", "Name="), ("Editor.Syntax", "Comment=")],
    },
    {
        "id": "redpanda",
        "name": "Red Panda C++ (小熊猫 C++)",
        "process": "RedPandaIDE.exe",
        "configs": [r"%APPDATA%\RedPanda-CPP\*.ini", r"%APPDATA%\RedPanda-CPP\*.json"],
        "kind": "generic",
        "watch": [],
    },
    {
        "id": "codeblocks",
        "name": "Code::Blocks",
        "process": "codeblocks.exe",
        "configs": [r"%APPDATA%\CodeBlocks\default.conf"],
        "kind": "xml",
        "watch": [],
    },
    {
        "id": "vscode",
        "name": "VS Code",
        "process": "code.exe",
        "configs": [r"%APPDATA%\Code\User\settings.json"],
        "kind": "json",
        "watch": ["editor.fontFamily", "editor.fontSize", "editor.tokenColorCustomizations",
                  "workbench.colorTheme", "files.encoding", "files.autoGuessEncoding"],
    },
    {
        "id": "sublime",
        "name": "Sublime Text",
        "process": "sublime_text.exe",
        "configs": [r"%APPDATA%\Sublime Text\Packages\User\Preferences.sublime-settings",
                    r"%APPDATA%\Sublime Text 3\Packages\User\Preferences.sublime-settings"],
        "kind": "json",
        "watch": ["font_face", "font_size", "color_scheme"],
    },
    {
        "id": "notepadpp",
        "name": "Notepad++",
        "process": "notepad++.exe",
        "configs": [r"%APPDATA%\Notepad++\config.xml"],
        "kind": "xml",
        "watch": [],
    },
    {
        "id": "jetbrains",
        "name": "JetBrains IDE (CLion / IDEA …)",
        "process": "clion64.exe",
        "configs": [r"%APPDATA%\JetBrains\*\options\editor.xml",
                    r"%APPDATA%\JetBrains\*\colors\*.icls",
                    r"%APPDATA%\JetBrains\*\options\fileEncodings.xml"],
        "kind": "generic",
        "watch": [],
    },
    {
        "id": "vim",
        "name": "Vim",
        "process": "vim.exe",
        "configs": [r"%USERPROFILE%\_vimrc", r"%USERPROFILE%\.vimrc"],
        "kind": "generic",
        "watch": [],
    },
    {
        "id": "neovim",
        "name": "Neovim",
        "process": "nvim.exe",
        "configs": [r"%LOCALAPPDATA%\nvim\init.lua", r"%LOCALAPPDATA%\nvim\init.vim",
                    r"%USERPROFILE%\AppData\Local\nvim\init.lua"],
        "kind": "generic",
        "watch": [],
    },
]


def running_processes():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True,
                             errors="ignore").stdout.lower()
        return out
    except Exception:
        return ""


def expand(p):
    return os.path.expandvars(p)


def resolve(pattern):
    if "*" in pattern:
        return sorted(glob.glob(expand(pattern)))
    p = expand(pattern)
    return [p] if os.path.isfile(p) else []


def read_ini_keys(path, watch):
    lines = open(path, "rb").read().decode("gbk", errors="replace").splitlines()
    cur, out = None, []
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]
            continue
        for section, prefix in watch:
            if cur == section and line.startswith(prefix):
                out.append(f"[{section}] {line}")
    return out


def read_json_keys(path, watch):
    text = open(path, "rb").read().decode("utf-8-sig", errors="replace")
    out = []
    for key in watch:
        marker = '"' + key + '"'
        idx = text.find(marker)
        if idx < 0:
            out.append(f"{key} = (not set)")
            continue
        end = text.find("\n", idx)
        out.append(text[idx:end if end > 0 else len(text)].strip().rstrip(","))
    return out


def scan():
    procs = running_processes()
    found = []
    for ed in EDITORS:
        paths = []
        for pat in ed["configs"]:
            paths.extend(resolve(pat))
        if not paths:
            continue
        entry = {
            "id": ed["id"], "name": ed["name"],
            "running": ed["process"].lower() in procs,
            "files": [],
        }
        for p in paths[:6]:
            st = os.stat(p)
            item = {"path": p, "size": st.st_size,
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}
            try:
                if ed["kind"] == "ini":
                    item["keys"] = read_ini_keys(p, ed["watch"])
                elif ed["kind"] == "json":
                    item["keys"] = read_json_keys(p, ed["watch"])
            except Exception as e:
                item["keys"] = [f"(read failed: {e})"]
            entry["files"].append(item)
        found.append(entry)
    return found


def main():
    as_json = "--json" in sys.argv
    found = scan()
    if as_json:
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return 0

    if not found:
        print("No known editor configs found. Ask the user which editor they use,")
        print("then check references/editors.md for its config path.")
        return 1

    print(f"Found {len(found)} editor(s) with config files:\n")
    for i, ed in enumerate(found, 1):
        print(f"[{i}] {ed['name']}")
        print("    running:", "YES (must be closed before editing)" if ed["running"] else "no")
        for f in ed["files"]:
            print(f"    config : {f['path']}")
            print(f"             {f['size']} bytes | mtime {f['mtime']}")
            for k in f.get("keys", []):
                print("             ", k)
        print()
    print("Next: close the editor, back up the config, then change only the needed keys.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
