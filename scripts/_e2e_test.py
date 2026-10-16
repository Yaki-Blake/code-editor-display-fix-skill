#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end test for ini_patch.py on a synthetic GBK devcpp.ini.

Builds a fake config that mimics the real one (Chinese path, quoted font name,
Consolas, clHighlight comment color), then drives the whole CLI:
  locate -> set --dry-run -> set -> verify -> multi-field guard -> backups -> restore

Run:  python _e2e_test.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "ini_patch.py")
PY = sys.executable

# A faithful mini version of the real file: GBK bytes, Chinese path, quoted names.
SAMPLE = """[Editor.Font]
Name="Consolas"
Size=12
Charset=1
[Editor.Gutterfont]
Name="Consolas"
Size=10
[Editor.Syntax]
Comment=clHighlight, clNone, 0, 0, 0
Number=clBlack, clWhite, 0, 0, 0
Space=clBlack, clWhite, 0, 0, 0
[Editor]
NewDocEncoding="ANSI"
[Directories]
Default="F:\\软件\\DEV C++\\Dev-Cpp\\"
"""

PASS, FAIL = 0, []


def check(label, cond, extra=""):
    global PASS
    if cond:
        PASS += 1
        print(f"  [ok] {label}")
    else:
        FAIL.append(label)
        print(f"  [FAIL] {label} {extra}")


def run(*args):
    r = subprocess.run([PY, SCRIPT] + list(args), capture_output=True,
                       text=True, errors="replace")
    return r.returncode, r.stdout + r.stderr


def raw(path):
    return open(path, "rb").read()


def main():
    tmp = tempfile.mkdtemp(prefix="devcpp_e2e_")
    cfg = os.path.join(tmp, "devcpp.ini")
    # Real devcpp.ini is CRLF; write it that way so the CRLF path is exercised too.
    with open(cfg, "wb") as f:
        f.write(SAMPLE.replace("\n", "\r\n").encode("gbk"))
    original = raw(cfg)

    print("== 0. fixture ==")
    check("fixture is GBK, not UTF-8",
          True if _try_utf8(original) is False else False,
          "(it decoded as utf-8, fixture unrealistic)")
    check("fixture contains Chinese path",
          "软件".encode("gbk") in original)

    print("\n== 1. locate --path ==")
    rc, out = run("locate", "--path", cfg)
    check("exit 0", rc == 0, f"rc={rc}")
    check("shows the font section", "[Editor.Font]" in out)
    check("no blank line between entries",
          "\n\n\n" not in out.replace("\r\n", "\n"))
    check("no stray CRLF in output", "\r\n" not in out)

    print("\n== 2. set --dry-run (font + comment + encoding) ==")
    rc, out = run("set",
                  'Editor.Font:Name=NSimSun',
                  'Editor.Font:Charset=134',
                  'Editor.Syntax:Comment=6316128, clNone, 0, 1, 0',
                  'Editor:NewDocEncoding="UTF-8"',
                  "--path", cfg, "--dry-run")
    check("exit 0", rc == 0, f"rc={rc}")
    check("dry-run wrote nothing", raw(cfg) == original)
    check("plan shows quoted target", '"NSimSun"' in out)

    print("\n== 3. real set ==")
    rc, out = run("set",
                  'Editor.Font:Name=NSimSun',
                  'Editor.Font:Charset=134',
                  'Editor.Syntax:Comment=6316128, clNone, 0, 1, 0',
                  'Editor:NewDocEncoding="UTF-8"',
                  "--path", cfg)
    check("exit 0", rc == 0, f"rc={rc}")
    check("verify line is True", "verify (revert changes == backup, byte-identical): True" in out)

    txt = raw(cfg).decode("gbk")
    check('font name keeps quotes: Name="NSimSun"', 'Name="NSimSun"' in txt)
    check("charset written", "Charset=134" in txt)
    check("comment row keeps all 5 fields",
          "Comment=6316128, clNone, 0, 1, 0" in txt)
    check("encoding written", 'NewDocEncoding="UTF-8"' in txt)
    check("Chinese path untouched",
          'Default="F:\\软件\\DEV C++\\Dev-Cpp\\"' in txt)
    check("gutter font untouched (still Consolas)",
          'Size=10' in txt and txt.count('Name="Consolas"') == 1)
    check("Space row untouched", "Space=clBlack, clWhite, 0, 0, 0" in txt)

    n_changed = sum(1 for a, b in zip(original.split(b"\r\n"),
                                     raw(cfg).split(b"\r\n")) if a != b)
    check("exactly 4 lines changed", n_changed == 4, f"got {n_changed}")

    print("\n== 4. multi-field guard ==")
    before = raw(cfg)
    rc, out = run("set", "Editor.Syntax:Comment=28672", "--path", cfg)
    check("refuses with exit 2", rc == 2, f"rc={rc}")
    check("file left untouched", raw(cfg) == before)
    check("explains the fix", "pass the complete value" in out)

    print("\n== 5. no-op detection ==")
    rc, out = run("set", "Editor.Font:Name=NSimSun", "--path", cfg)
    check("exit 0", rc == 0, f"rc={rc}")
    check("says nothing to change", "nothing to change" in out)

    print("\n== 6. backups + restore ==")
    rc, out = run("backups", "--path", cfg)
    check("lists at least one backup", ".bak-" in out)
    bak_name = [ln.strip().split()[0] for ln in out.splitlines() if ".bak-" in ln][0]
    rc, out = run("restore", bak_name, "--path", cfg)
    check("restore exit 0", rc == 0, f"rc={rc}")
    check("restored byte-identical to original", raw(cfg) == original)
    check("pre-restore safety copy made",
          any(f.startswith("devcpp.ini.before-restore-") for f in os.listdir(tmp)))

    print("\n== 7. encoding safety ==")
    check("final file still GBK-decodable", _try_gbk(raw(cfg)))
    check("final file is NOT valid UTF-8 (still ANSI/GBK)", _try_utf8(raw(cfg)) is False)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'=' * 46}")
    print(f"PASSED {PASS}   FAILED {len(FAIL)}")
    for f in FAIL:
        print("   x", f)
    return 1 if FAIL else 0


def _try_utf8(b):
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _try_gbk(b):
    try:
        b.decode("gbk")
        return True
    except UnicodeDecodeError:
        return False


if __name__ == "__main__":
    sys.exit(main())
