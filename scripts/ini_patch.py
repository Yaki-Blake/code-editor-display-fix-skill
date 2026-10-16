#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safely inspect and patch Dev-C++ devcpp.ini (Embarcadero 6.x / Orwell 5.11).

Why not a plain text editor:
  devcpp.ini is ANSI/GBK encoded and contains Chinese paths (e.g. Default="F:\\中文目录").
  Reading/writing it as UTF-8 destroys those fields forever. This script works on raw
  bytes and replaces only the requested key lines, leaving every other byte untouched.

Usage:
  python ini_patch.py locate
  python ini_patch.py show [Section]
  python ini_patch.py set "Section:Key=Value" ["Section:Key=Value" ...] [--dry-run]
  python ini_patch.py backups
  python ini_patch.py restore <backup-file-name>

Exit codes: 0 ok, 1 environment problem (running / not found), 2 bad arguments, 3 verify failed.
"""
import glob
import os
import shutil
import subprocess
import sys
import time

CANDIDATES = [
    r"%APPDATA%\Embarcadero\Dev-Cpp\devcpp.ini",
    r"%APPDATA%\Dev-Cpp\devcpp.ini",
    r"%LOCALAPPDATA%\Embarcadero\Dev-Cpp\devcpp.ini",
]

KEY_ITEMS = ["NewDocEncoding=", "Comment=", "Space=", "Selected text=", "HighColor="]


def find_config():
    for c in CANDIDATES:
        p = os.path.expandvars(c)
        if os.path.isfile(p):
            return p
    base = os.path.expandvars(r"%APPDATA%")
    for pat in ("*/devcpp.ini", "*/*/devcpp.ini"):
        hits = sorted(glob.glob(os.path.join(base, pat)))
        if hits:
            return hits[0]
    return None


def is_running():
    """True / False / None(unknown)."""
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True,
                             errors="ignore").stdout.lower()
        return "devcpp" in out
    except Exception:
        return None


def load(p):
    data = open(p, "rb").read()
    nl = b"\r\n" if b"\r\n" in data else b"\n"
    return data, nl, data.split(nl)


def bounds(lines, section):
    tag = ("[" + section + "]").encode()
    if tag not in lines:
        return None
    s = lines.index(tag) + 1
    e = s
    while e < len(lines) and not lines[e].startswith(b"["):
        e += 1
    return s, e


def refuse_if_running():
    state = is_running()
    if state:
        print("!! Dev-C++ is RUNNING. Ask the user to exit it completely first:")
        print("   changes made now will be overwritten when it quits.")
        return True
    if state is None:
        print("?? could not read the process list; make sure Dev-C++ is closed.")
    return False


def dump_config(p):
    st = os.stat(p)
    print("config :", p)
    print("mtime  :", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)))
    print("bytes  :", st.st_size)
    text = open(p, "rb").read().decode("gbk", errors="replace").replace("\r\n", "\n")
    for section in ("[Editor.Font]", "[Editor.Syntax]"):
        if section in text:
            start = text.index(section)
            nxt = [text.index(s, start + 1) for s in ("[Editor.Gutterfont]", "[Editor.Syntax]",
                                                      "[CodeCompletion]") if s in text[start + 1:]]
            end = min(nxt) if nxt else len(text)
            print("\n---", section, "---")
            print(text[start:end].strip())
    print("\n--- key items ---")
    for line in text.splitlines():
        for k in KEY_ITEMS:
            if line.startswith(k):
                print(" ", line)


def cmd_locate():
    state = is_running()
    print("Dev-C++ process:", "RUNNING (must exit first)" if state else
          ("not running" if state is False else "unknown"))
    p = find_config()
    if not p:
        print("!! devcpp.ini not found. Look for it manually under %APPDATA%.")
        return 1
    dump_config(p)
    return 0


def cmd_show(p, section=None):
    text = open(p, "rb").read().decode("gbk", errors="replace").replace("\r\n", "\n")
    if section:
        b = bounds(text.splitlines(), section)
        if b is None:
            print("!! section not found:", section)
            return 2
        s, e = b
        for line in text.splitlines()[s:e]:
            print(line)
        return 0
    print("[sections]")
    for line in text.splitlines():
        if line.startswith("[") and line.endswith("]"):
            print(" ", line)
    print("\n(hint: python ini_patch.py show Editor.Font)")
    return 0


def unique_path(base):
    """Never let two patches in the same second overwrite each other's backup."""
    if not os.path.exists(base):
        return base
    n = 2
    while os.path.exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def cmd_set(p, specs, dry):
    if refuse_if_running():
        return 1
    data, nl, lines = load(p)
    changes = []
    for spec in specs:
        if "=" not in spec or ":" not in spec.split("=", 1)[0]:
            print('!! bad spec (expect "Section:Key=Value"):', spec)
            return 2
        head, value = spec.split("=", 1)
        section, key = head.split(":", 1)
        b = bounds(lines, section)
        if b is None:
            print("!! section not found:", section)
            return 2
        s, e = b
        for i in range(s, e):
            if lines[i].split(b"=", 1)[0] == key.encode():
                old_line = lines[i]
                # Guard: multi-field rows (e.g. [Editor.Syntax] "前景, 背景, 粗体, 斜体, 下划线")
                # must be given as a COMPLETE value, otherwise the trailing fields get wiped.
                old_val = old_line.split(b"=", 1)[1]
                if b"," in old_val and b"," not in value.encode():
                    print(f"!! [{section}] {key} holds a multi-field value; refuse to wipe it.")
                    print("   old      :", old_line.decode("latin-1"))
                    print("   you gave :", key + "=" + value)
                    print('   fix      : pass the complete value, e.g. '
                          f'"{section}:{key}=28672, clNone, 0, 1, 0"')
                    return 2
                new_val = value.encode()
                # Keep the original quoting style: Dev-C++ stores strings as Name="Consolas",
                # so writing a bare NSimSun would silently change the file's conventions.
                if (old_val.startswith(b'"') and old_val.endswith(b'"')
                        and not (new_val.startswith(b'"') and new_val.endswith(b'"'))):
                    new_val = b'"' + new_val + b'"'
                new = key.encode() + b"=" + new_val
                if old_line != new:
                    changes.append((i, old_line, new))
                    lines[i] = new
                break
        else:
            print("!! key not found:", key, "in", section)
            return 2

    if not changes:
        print("nothing to change (values already match).")
        return 0

    print("planned changes:")
    for i, old, new in changes:
        print(f"  line {i + 1}: {old.decode('latin-1')}  ->  {new.decode('latin-1')}")

    if dry:
        print("(--dry-run: nothing written)")
        return 0

    bak = unique_path(p + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(p, bak)
    with open(p, "wb") as f:
        f.write(nl.join(lines))

    back = list(lines)
    for i, old, _ in changes:
        back[i] = old
    ok = nl.join(back) == open(bak, "rb").read()

    print("\nbackup :", os.path.basename(bak))
    print("written:", len(data), "->", len(nl.join(lines)), "bytes")
    print("verify (revert changes == backup, byte-identical):", ok)
    return 0 if ok else 3


def cmd_backups(p):
    hits = sorted(glob.glob(p + ".bak*"))
    if not hits:
        print("(no backups)")
        return 0
    for h in hits:
        st = os.stat(h)
        print(f"  {os.path.basename(h)}  {st.st_size} bytes  "
              f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}")
    return 0


def cmd_restore(p, name):
    if refuse_if_running():
        return 1
    cand = [name, os.path.join(os.path.dirname(p), name)]
    src = next((c for c in cand if os.path.isfile(c)), None)
    if not src:
        print("!! backup not found:", name, "(see: backups)")
        return 1
    shutil.copy2(p, unique_path(p + ".before-restore-" + time.strftime("%Y%m%d-%H%M%S")))
    shutil.copy2(src, p)
    print("restored from", os.path.basename(src))
    return 0


def resolve_config(explicit=None):
    """explicit: value of --path (any devcpp.ini, e.g. a portable install)."""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    return find_config()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    explicit = None
    if "--path" in args:
        i = args.index("--path")
        if i + 1 >= len(args):
            print("!! --path requires a file path")
            return 2
        explicit = args[i + 1]
        del args[i:i + 2]

    cmd = args[0] if args else "locate"

    if cmd == "locate":
        if explicit:
            if not os.path.isfile(explicit):
                print("!! file not found:", explicit)
                return 1
            state = is_running()
            print("Dev-C++ process:", "RUNNING (must exit first)" if state else
                  ("not running" if state is False else "unknown"))
            dump_config(explicit)
            return 0
        return cmd_locate()

    p = resolve_config(explicit)
    if not p:
        print("!! devcpp.ini not found; run 'locate' for details.")
        return 1

    if cmd == "show":
        return cmd_show(p, args[1] if len(args) > 1 else None)
    if cmd == "set":
        if len(args) < 2:
            print('usage: set "Section:Key=Value" ... [--path FILE] [--dry-run]')
            return 2
        return cmd_set(p, args[1:], dry)
    if cmd == "backups":
        return cmd_backups(p)
    if cmd == "restore":
        if len(args) < 2:
            print("usage: restore <backup-file-name> [--path FILE]")
            return 2
        return cmd_restore(p, args[1])

    print("unknown command:", cmd)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
