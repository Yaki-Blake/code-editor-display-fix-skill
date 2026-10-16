# code-editor-display-fix

> 可以修复部分因为编译器自身问题导致的注释无法显示。

Fix display problems in code editors — **invisible Chinese characters, unreadable comment colors, garbled text, and settings that silently revert.**

---

## English

### What it solves

| Symptom | Root cause |
|---|---|
| Chinese characters invisible, ASCII/digits fine | the editor font has no CJK glyphs; the fallback path loses the foreground colour |
| Comment or keyword too faint | foreground too close to the background colour |
| Chinese shows as `锟斤拷` / `璁颁簨` | file encoding does not match the editor's encoding setting |
| Config edited but nothing changed | the editor was still running and overwrote it on exit |

**Strongest clue:** if selecting the line makes the text appear, the character data is fine — it is a *rendering* (font / colour) problem, **not** an encoding one. Stop chasing encoding.

### Supported editors

Dev-C++ 6.x · Red Panda C++ · Code::Blocks · VS Code · Visual Studio · CLion · Sublime Text · Notepad++ · Vim / Neovim

### Quick start

```bash
python scripts/locate_editors.py      # which editors are installed, where their configs live

# ini-based (Dev-C++ / Red Panda)
python scripts/ini_patch.py locate
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134" --dry-run
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134"

# JSON-based (VS Code / Sublime)
python scripts/json_patch.py locate
python scripts/json_patch.py set --json '{"editor.fontFamily": "Microsoft YaHei, Consolas, monospace"}' --file vscode
```

### Three rules (break any of them and it will bite)

1. **Fully exit the editor first.** Editing a config while the editor runs gets ignored, then overwritten on quit.
2. **Preserve the original encoding.** Many configs are ANSI/GBK and contain non-ASCII paths; a UTF-8 rewrite destroys them.
3. **Back up, verify, roll back.** Every script timestamps a backup and checks the result — non-target entries must stay byte-identical.

### Verified

| Command | Assertions | Result |
|---|---|---|
| `python scripts/_e2e_test.py` | 30 | all pass |
| `python scripts/_e2e_test_json.py` | 23 | all pass |

Re-run both after changing any script.

### Honest limit

Only **Dev-C++** and **VS Code** were tested on a real machine. The other editors' paths and setting keys come from official documentation and have **not** been empirically verified. See `references/editors.md`.

---

## 中文

### 解决什么问题

| 症状 | 根因 |
|---|---|
| 汉字看不见，数字和符号正常 | 编辑器字体没有汉字字形，系统回退绘制时**丢了前景色** |
| 注释 / 关键字颜色太淡 | 前景色与背景色太接近 |
| 中文变成 `锟斤拷` / `璁颁簨` | 文件编码与编辑器编码设置不匹配 |
| 改了配置却没生效 | 编辑器没退出，退出时用内存里的设置覆盖回写 |

**最强判据**：如果**选中那一行文字就出现了**，说明字符数据完全正确，问题在**绘制层**（字体 / 颜色），**不是编码问题**——别再折腾编码了。

### 支持的编辑器

Dev-C++ 6.x · 小熊猫 C++ · Code::Blocks · VS Code · Visual Studio · CLion · Sublime Text · Notepad++ · Vim / Neovim

### 快速开始

```bash
python scripts/locate_editors.py      # 本机装了哪些编辑器、配置在哪

# ini 系（Dev-C++ / 小熊猫）
python scripts/ini_patch.py locate
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134" --dry-run
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134"

# JSON 系（VS Code / Sublime）
python scripts/json_patch.py locate
python scripts/json_patch.py set --json '{"editor.fontFamily": "Microsoft YaHei, Consolas, monospace"}' --file vscode
```

### 三条铁律（违反任一条必翻车）

1. **必须让编辑器完全退出。** 程序运行时改配置会被无视，**退出时用内存里的旧设置覆盖回写**。
2. **原样保留文件编码。** 很多配置是 ANSI/GBK 且含中文路径，按 UTF-8 重写会毁掉它们。
3. **改前备份、改后校验、支持回滚。** 所有脚本都会打时间戳备份并校验结果——非目标项必须保持字节完全一致。

### 已验证

| 命令 | 断言数 | 结果 |
|---|---|---|
| `python scripts/_e2e_test.py` | 30 | 全部通过 |
| `python scripts/_e2e_test_json.py` | 23 | 全部通过 |

改完任何脚本后请重跑这两套测试。

### 诚实的边界

只有 **Dev-C++** 和 **VS Code** 做过真机实测。其余编辑器的路径与设置键名来自官方文档，**未经实测**。详见 `references/editors.md`。

---

## Layout / 目录结构

```
SKILL.md                      methodology + decision tables / 方法论与判据表
references/troubleshooting.md triage flow + anti-disaster checklist / 排查流程与防翻车清单
references/editors.md         per-editor paths and setting keys / 各编辑器路径与设置项
references/devcpp-case.md     Dev-C++ case study + TColor table / 实战复盘与颜色换算
scripts/locate_editors.py     read-only scanner / 只读扫描器
scripts/ini_patch.py          safe ini patcher / ini 安全改写
scripts/json_patch.py         safe JSONC patcher / JSON 安全改写
scripts/_e2e_test*.py         self-tests / 自测
```

## License / 许可

Mozilla Public License 2.0 (MPL-2.0) — see [LICENSE](LICENSE).
