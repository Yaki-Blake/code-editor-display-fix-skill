#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end test for json_patch.py on a synthetic VS Code settings.json.

The point is JSONC safety: comments, blank lines, key order and unrelated
values must survive a patch byte-for-byte. We import the module and stub out
the "is the editor running?" probe so the test is deterministic on any machine.

Run:  python _e2e_test_json.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# A realistic settings.json with a comment, a trailing comma and odd spacing.
SAMPLE = """{
    // my C++ settings
    "editor.fontSize": 14,
    "editor.fontFamily": "Consolas, 'Courier New', monospace",
    "editor.tabSize": 4,
    "files.encoding": "utf8",
    "workbench.colorTheme": "Default Light+",
    /* comment blocks are allowed too */
    "editor.suggest.snippetsPreventQuickSuggestions": false,
}
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


def load_mod():
    spec = importlib.util.spec_from_file_location(
        "json_patch", os.path.join(HERE, "json_patch.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    jp = load_mod()
    jp.is_running = lambda kind: False          # deterministic: pretend nothing runs

    tmp = tempfile.mkdtemp(prefix="vscode_e2e_")
    cfg = os.path.join(tmp, "settings.json")
    with open(cfg, "wb") as f:
        f.write(SAMPLE.encode("utf-8"))
    original = open(cfg, "rb").read()

    print("== 1. parse the JSONC ==")
    obj = jp.parse_jsonc(original.decode("utf-8"))
    check("parses despite // and /* */", obj["editor.fontSize"] == 14)
    check("trailing comma tolerated", obj["editor.tabSize"] == 4)

    print("\n== 2. replace an existing key ==")
    rc = jp.cmd_set(cfg, "vscode", {"editor.fontSize": 16}, dry=False)
    check("exit 0", rc == 0, f"rc={rc}")
    txt = open(cfg, "rb").read().decode("utf-8")
    check("value updated", '"editor.fontSize": 16' in txt)
    check("// comment preserved", "// my C++ settings" in txt)
    check("/* */ comment preserved", "/* comment blocks are allowed too */" in txt)
    check("other keys untouched",
          '"editor.fontFamily": "Consolas, \'Courier New\', monospace"' in txt)
    check("trailing comma still there", "false,\n}" in txt)

    print("\n== 3. append a brand-new key ==")
    rc = jp.cmd_set(cfg, "vscode", {"editor.fontLigatures": True}, dry=False)
    check("exit 0", rc == 0, f"rc={rc}")
    txt = open(cfg, "rb").read().decode("utf-8")
    check("new key present", '"editor.fontLigatures": true' in txt)
    check("no blank line injected", "},\n\n}" not in txt and "\n\n\n" not in txt)
    check("still valid JSON after append",
          jp.parse_jsonc(txt)["editor.fontLigatures"] is True)
    check("no duplicate key", txt.count('"editor.fontLigatures"') == 1)

    print("\n== 4. dry-run changes nothing ==")
    snap = open(cfg, "rb").read()
    rc = jp.cmd_set(cfg, "vscode", {"editor.tabSize": 8}, dry=True)
    check("exit 0", rc == 0, f"rc={rc}")
    check("file untouched", open(cfg, "rb").read() == snap)

    print("\n== 5. Chinese value round-trips ==")
    rc = jp.cmd_set(cfg, "vscode", {"workbench.colorCustomizations.标题颜色": "深蓝"}, dry=False)
    check("exit 0", rc == 0, f"rc={rc}")
    txt = open(cfg, "rb").read().decode("utf-8")
    check("Chinese key written verbatim", '"workbench.colorCustomizations.标题颜色"' in txt)
    check("Chinese value written verbatim (no \\u escapes)", '"深蓝"' in txt)

    print("\n== 6. backups + restore ==")
    baks = sorted(f for f in os.listdir(tmp) if ".bak-" in f)
    check("every patch kept its own backup (no clobbering)", len(baks) == 3,
          f"got {len(baks)}: {baks}")
    check("oldest backup == original file",
          open(os.path.join(tmp, baks[0]), "rb").read() == original)
    rc = jp.cmd_restore(cfg, baks[0], "vscode")
    check("restore exit 0", rc == 0, f"rc={rc}")
    check("restored file == original bytes", open(cfg, "rb").read() == original)
    check("pre-restore safety copy made",
          any(f.startswith("settings.json.before-restore-") for f in os.listdir(tmp)))

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'=' * 46}")
    print(f"PASSED {PASS}   FAILED {len(FAIL)}")
    for f in FAIL:
        print("   x", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
