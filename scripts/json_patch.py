#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safely patch JSON/JSONC settings for editors (VS Code, Sublime Text).

Why not a plain rewrite:
  * VS Code settings.json and Sublime Preferences are JSONC — they allow comments.
    json.load()+dump() would destroy those comments and reformat the whole file.
  * This script edits TEXTUALLY: it locates the top-level "key": value span and
    replaces only that span, leaving comments, ordering and formatting untouched.

Usage:
  python json_patch.py locate
  python json_patch.py show [--file vscode|sublime] [--path FILE]
  python json_patch.py set --json '{"editor.fontSize": 14}' [--file ...] [--path FILE] [--dry-run]
  python json_patch.py backups [--file ...]
  python json_patch.py restore <backup-file> [--file ...]

Exit codes: 0 ok, 1 environment problem, 2 bad arguments, 3 verify failed.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

TARGETS = {
    "vscode": {
        "name": "VS Code",
        "process": "code.exe",
        "paths": [r"%APPDATA%\Code\User\settings.json"],
    },
    "sublime": {
        "name": "Sublime Text",
        "process": "sublime_text.exe",
        "paths": [
            r"%APPDATA%\Sublime Text\Packages\User\Preferences.sublime-settings",
            r"%APPDATA%\Sublime Text 3\Packages\User\Preferences.sublime-settings",
        ],
    },
}


def find_file(kind):
    for pat in TARGETS[kind]["paths"]:
        p = os.path.expandvars(pat)
        if os.path.isfile(p):
            return p
    return None


def is_running(kind):
    proc = TARGETS[kind]["process"]
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True,
                             errors="ignore").stdout.lower()
        return proc in out
    except Exception:
        return None


def strip_jsonc(t):
    """Remove // and /* */ comments, keeping string literals intact."""
    out, i, n, in_str = [], 0, len(t), False
    while i < n:
        c = t[i]
        if in_str:
            if c == "\\":
                out.append(t[i:i + 2]); i += 2; continue
            if c == '"':
                in_str = False
            out.append(c); i += 1; continue
        if c == '"':
            in_str = True; out.append(c); i += 1; continue
        if c == "/" and i + 1 < n and t[i + 1] == "/":
            j = t.find("\n", i); i = n if j < 0 else j; continue
        if c == "/" and i + 1 < n and t[i + 1] == "*":
            j = t.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        out.append(c); i += 1
    return "".join(out)


def parse_jsonc(t):
    strict = re.sub(r",(\s*[}\]])", r"\1", strip_jsonc(t))
    return json.loads(strict)


def skip_ws(t, i):
    while i < len(t) and t[i] in " \t\r\n":
        i += 1
    return i


def scan_string(t, i):
    i += 1
    while i < len(t):
        if t[i] == "\\":
            i += 2; continue
        if t[i] == '"':
            return i + 1
        i += 1
    raise ValueError("unterminated string")


def scan_value(t, i):
    i = skip_ws(t, i)
    c = t[i]
    if c == '"':
        return scan_string(t, i)
    if c in "[{":
        depth = 0
        while i < len(t):
            c2 = t[i]
            if c2 == '"':
                i = scan_string(t, i); continue
            if c2 in "[{":
                depth += 1
            elif c2 in "]}":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        raise ValueError("unbalanced brackets")
    j = i
    while j < len(t) and t[j] not in ",}\n\r":
        j += 1
    while j > i and t[j - 1] in " \t":
        j -= 1
    return j


def find_key_span(t, key):
    """Return (value_start, value_end) for a TOP-LEVEL key, or None."""
    depth, i, target = 0, 0, '"' + key + '"'
    while i < len(t):
        c = t[i]
        if c == "/" and i + 1 < len(t) and t[i + 1] == "/":
            j = t.find("\n", i); i = len(t) if j < 0 else j + 1; continue
        if c == "/" and i + 1 < len(t) and t[i + 1] == "*":
            j = t.find("*/", i + 2); i = len(t) if j < 0 else j + 2; continue
        if c == '"':
            end = scan_string(t, i)
            if depth == 1 and t[i:end] == target:
                j = skip_ws(t, end)
                if j < len(t) and t[j] == ":":
                    j = skip_ws(t, j + 1)
                    return j, scan_value(t, j)
            i = end; continue
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        i += 1
    return None


def append_key(t, key, literal):
    idx = t.rstrip().rfind("}")
    if idx < 0:
        raise ValueError("no closing brace")
    head = t[:idx].rstrip()          # drop trailing whitespace so we don't add a blank line
    comma = "" if head.endswith("{") or head.endswith(",") else ","
    return head + comma + '\n    "' + key + '": ' + literal + "\n" + t[idx:]


def literal_for(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def cmd_locate():
    for kind, meta in TARGETS.items():
        p = find_file(kind)
        state = is_running(kind)
        print(f"[{kind}] {meta['name']}")
        print("   process:", "RUNNING" if state else ("not running" if state is False else "unknown"))
        print("   config :", p or "not found")
        if p:
            st = os.stat(p)
            print("   mtime  :", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                  "|", st.st_size, "bytes")
        print()
    return 0


def cmd_show(p, keys=None):
    t = open(p, "rb").read().decode("utf-8-sig", errors="replace")
    print("file:", p)
    try:
        obj = parse_jsonc(t)
    except Exception as e:
        print("!! cannot parse (JSONC):", e)
        return 2
    if keys:
        for k in keys:
            span = find_key_span(t, k)
            print(f"  {k} =", t[span[0]:span[1]] if span else "(not set)")
    else:
        for k in sorted(obj):
            if isinstance(obj[k], (str, int, float, bool)) or obj[k] is None:
                print(f"  {k} = {json.dumps(obj[k], ensure_ascii=False)}")
        print("  ... (object/array values omitted; use show \"key\" to inspect)")
    return 0


def unique_path(base):
    """Never let two patches in the same second overwrite each other's backup."""
    if not os.path.exists(base):
        return base
    n = 2
    while os.path.exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def cmd_set(p, kind, pairs, dry):
    if is_running(kind):
        print(f"!! {TARGETS[kind]['name']} is RUNNING. Exit it completely first —")
        print("   settings changed now are overwritten when it quits.")
        return 1

    t = open(p, "rb").read().decode("utf-8-sig", errors="replace")
    before = parse_jsonc(t)

    for key, value in pairs.items():
        lit = literal_for(value)
        span = find_key_span(t, key)
        if span:
            old = t[span[0]:span[1]]
            if old == lit:
                print(f"  {key}: already {lit}")
                continue
            print(f"  {key}: {old}  ->  {lit}")
            t = t[:span[0]] + lit + t[span[1]:]
        else:
            print(f"  {key}: (new)  ->  {lit}")
            t = append_key(t, key, lit)

    try:
        after = parse_jsonc(t)
    except Exception as e:
        print("!! result would be invalid JSON, aborting:", e)
        return 2

    diff = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    unexpected = diff - set(pairs)
    if unexpected:
        print("!! unexpected keys changed:", unexpected, "-> aborting")
        return 2

    if dry:
        print("(--dry-run: nothing written)")
        return 0

    bak = unique_path(p + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(p, bak)
    with open(p, "wb") as f:
        f.write(t.encode("utf-8"))
    print("\nbackup :", os.path.basename(bak))
    print("verify : changed keys =", sorted(diff), "| JSON valid:", True)
    return 0


def cmd_backups(p):
    hits = sorted(glob.glob(p + ".bak-*"))
    for h in hits:
        st = os.stat(h)
        print(f"  {os.path.basename(h)}  {st.st_size} bytes  "
              f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}")
    if not hits:
        print("(no backups)")
    return 0


def cmd_restore(p, name, kind):
    if is_running(kind):
        print("!! editor is running; exit it first.")
        return 1
    cand = [name, os.path.join(os.path.dirname(p), name)]
    src = next((c for c in cand if os.path.isfile(c)), None)
    if not src:
        print("!! backup not found:", name)
        return 1
    shutil.copy2(p, unique_path(p + ".before-restore-" + time.strftime("%Y%m%d-%H%M%S")))
    shutil.copy2(src, p)
    print("restored from", os.path.basename(src))
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    kind = "vscode"
    path = None
    js = None
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--file":
            kind = args[i + 1]; i += 2; continue
        if a == "--path":
            path = args[i + 1]; i += 2; continue
        if a == "--json":
            js = args[i + 1]; i += 2; continue
        rest.append(a); i += 1

    cmd = rest[0] if rest else "locate"
    if cmd == "locate":
        return cmd_locate()
    if kind not in TARGETS:
        print("!! unknown --file:", kind, "(use vscode|sublime)")
        return 2

    p = path or find_file(kind)
    if not p:
        print(f"!! settings file not found for {kind}; run 'locate'.")
        return 1

    if cmd == "show":
        return cmd_show(p, rest[1:] or None)
    if cmd == "set":
        if not js:
            print('usage: set --json \'{"editor.fontSize": 14}\'')
            return 2
        try:
            pairs = json.loads(js)
        except Exception as e:
            print("!! --json is not valid JSON:", e)
            return 2
        if not isinstance(pairs, dict) or not pairs:
            print("!! --json must be a non-empty object")
            return 2
        return cmd_set(p, kind, pairs, dry)
    if cmd == "backups":
        return cmd_backups(p)
    if cmd == "restore":
        if len(rest) < 2:
            print("usage: restore <backup-file>")
            return 2
        return cmd_restore(p, rest[1], kind)

    print("unknown command:", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
