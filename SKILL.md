---
name: code-editor-display-fix
description: 修复代码编辑器 / IDE 的显示类问题——汉字或注释看不见、配色太浅看不清、字体怪异、中文乱码、改了设置不生效。覆盖 Dev-C++ / 小熊猫 C++ / Code::Blocks / VS Code / Visual Studio / CLion / Sublime Text / Notepad++ / Vim-Neovim。当用户说「XX 里看不见汉字」「注释看不见 / 太浅 / 颜色不对」「点到那行才显示」「中文显示空白 / 乱码」「字体太丑想换」「改了配置没生效」，或任何编辑器出现「某类字符不显示」时使用。做法：先判定根因（字形 / 编码 / 配色 / 配置未生效），再定位该编辑器的配置文件，在程序完全退出后用安全脚本精准改写，改前备份、改后校验、可一键回滚。
agent_created: true
---

# 代码编辑器显示问题修复

## 何时使用

Dev-C++、小熊猫 C++、Code::Blocks、VS Code、Visual Studio、CLion、Sublime Text、Notepad++、Vim/Neovim 等**任何编辑器/IDE** 出现：

- 某类字符不显示（典型：**汉字空白、数字符号正常**）
- 注释/关键字颜色太浅、和背景撞色
- 字体想换（换成等宽中文、更好看的字体）
- 中文变乱码（`锟斤拷`、`璁颁簨`）
- **改了配置文件却不生效 / 又被改回去**

配套资产：
- `references/troubleshooting.md` —— 通用三步排查法、判据表、防翻车清单
- `references/editors.md` —— **各编辑器配置文件位置 + 字体/配色/编码的设置项**（动手前必查）
- `references/devcpp-case.md` —— Dev-C++ 完整实战案例 + 颜色格式换算表
- `scripts/locate_editors.py` —— 扫描本机装了哪些编辑器、配置在哪
- `scripts/ini_patch.py` —— 安全改写 ini（Dev-C++ / 小熊猫 C++ 系）
- `scripts/json_patch.py` —— 安全改写 JSON 配置（VS Code / Sublime）
- `scripts/_e2e_test.py`、`scripts/_e2e_test_json.py` —— 端到端自测（改完脚本重跑一遍）

## 三条铁律（跨编辑器通用，违反必翻车）

1. **程序必须完全退出才能改配置文件。** 编辑器运行时改文件会被无视，**退出时用内存里的设置覆盖回写**（已实测：Dev-C++、Code::Blocks、JetBrains 全家）。正确顺序永远是：**关闭程序 → 改文件 → 打开程序**。改动生效前先确认进程没了。
2. **原样保留文件编码与格式，只替换目标项。** 很多配置是 **ANSI/GBK/UTF-8 with BOM** 且有中文路径；整体按 UTF-8 重写会毁掉它们。**ini/XML 走二进制或原文替换，JSON 走结构化解析**。
3. **改前备份、改后校验、支持回滚。** 只改用户点名的那几项。校验方式：把本次改动反向还原后，应与备份**字节完全一致**（JSON 文件则可比对除目标键外的其余键）。

## 第一步：确认编辑器与配置文件位置

```bash
# 装了哪些编辑器、配置在哪（只读扫描）
python scripts/locate_editors.py

# 或按 references/editors.md 的表格逐个确认路径
```

各编辑器的配置位置速览（详细见 `references/editors.md`）：

| 编辑器 | 配置位置（Windows） |
|---|---|
| Dev-C++ 6.x | `%APPDATA%\Embarcadero\Dev-Cpp\devcpp.ini` |
| Dev-C++ 5.11 | `%APPDATA%\Dev-Cpp\devcpp.ini` |
| 小熊猫 C++ | `%APPDATA%\RedPanda-CPP\` 下的 ini |
| Code::Blocks | `%APPDATA%\CodeBlocks\default.conf`（XML） |
| VS Code | `%APPDATA%\Code\User\settings.json` |
| Visual Studio | 注册表 `HKCU\Software\Microsoft\VisualStudio\*_Config\FontsAndColors` |
| CLion | `%APPDATA%\JetBrains\CLion<版本>\options\`、`colors\*.icls` |
| Sublime Text | `%APPDATA%\Sublime Text\Packages\User\Preferences.sublime-settings` |
| Notepad++ | `%APPDATA%\Notepad++\config.xml`、`stylers.xml` |
| Vim / Neovim | `%USERPROFILE%\_vimrc`、`%LOCALAPPDATA%\nvim\init.lua` |

**别相信注册表里的安装路径**：`Uninstall\*` 的 `InstallLocation` 常是垃圾值，`UninstallString` 可能指向已废弃的旧盘符；按盘符枚举或直接搜可执行文件更可靠。

## 第二步：判断根因（四种，先定性再动手）

| 判据 | 根因 | 修哪里 |
|---|---|---|
| **只有部分字符不显示**（汉字不行、ASCII/符号正常） | 字体缺字形（回退绘制丢颜色） | 字体 |
| 复制出来是乱码 / 文件字节可疑 | 编码不匹配 | 编码 |
| 字符都在，就是颜色淡、像背景色 | 配色对比度不足 | 配色 |
| 改了配置没生效 / 又变回去 | 程序没退出，或设置层级覆盖 | 流程 + 层级 |

**最强判据——「选中才显示」**：用户说"点到那一行文字就出现了" → **字符数据完全正确**，问题在绘制阶段（字体/颜色），**不要再去折腾编码**。

**为什么字体缺字形会让汉字隐形**：字体没有汉字字形时，系统回退到别的字体代画；部分编辑器的回退路径会**丢掉前景色**，汉字被画成接近背景的颜色而隐形；整行被选中时前景被强制为选中色，汉字立刻显形。

**VS Code / Sublime 一般不会出汉字隐形问题**（它们的字体回退链处理良好），若出现先怀疑用户自定义了 `fontFamily`。

## 第三步：取该编辑器的正确设置项

按 `references/editors.md` 找到对应编辑器，注意各家格式完全不同：

- **Dev-C++ 系（ini）**：`[Editor.Font] Name/Charset`、`[Editor.Syntax] Comment`（Delphi TColor 十进制）
- **Code::Blocks（XML）**：`<editor><font><str>Consolas</str>`、`<colour r="128" g="128" b="128"/>`（**RGB 分量**）
- **VS Code（JSON）**：`editor.fontFamily`、`editor.fontSize`、`editor.tokenColorCustomizations`、`workbench.colorCustomizations`、`files.encoding`、`files.autoGuessEncoding`
- **CLion**：`options\editor.xml` 的 `FONT_FACE`/`FONT_SIZE`、`colors\*.icls`（IntelliJ 格式）
- **Notepad++**：`config.xml` 的字体、`stylers.xml` 的 GlobalStyles 颜色

**颜色格式别搞混**：`#RRGGBB`（VS Code/Code::Blocks/Notepad++）、`0x00BBGGRR` 十进制（Delphi/Dev-C++）。换算表见 `references/devcpp-case.md`。

## 第四步：改（选对工具）

```bash
# ini（Dev-C++ / 小熊猫）：自带备份+校验+回滚，多字段行会被保护
python scripts/ini_patch.py locate
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134" --dry-run
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134"

# JSON（VS Code / Sublime）：自动备份 + 只改指定键 + 校验其余键未变
# 注意：值必须是合法 JSON（字符串要带双引号），整体以 --json 传入
python scripts/json_patch.py locate
python scripts/json_patch.py set --json '{"editor.fontFamily": "Microsoft YaHei, Consolas, monospace"}' --file vscode --dry-run
python scripts/json_patch.py set --json '{"editor.fontFamily": "Microsoft YaHei, Consolas, monospace"}' --file vscode

# XML（Code::Blocks / CLion）与注册表（Visual Studio）：按 references/editors.md 的步骤改，
# 同样遵守"先备份、后改、再校验"，改完立刻用备份做字节比对。
```

脚本都会：检查进程 → 时间戳备份 → 精准替换 → 校验 → 报告；异常即中止且不写盘。

## 第五步：验证与交付

1. 让用户**启动编辑器，打开一个带中文注释的源文件**
2. 确认：汉字显示正常 / 注释颜色可辨 / 背景符合预期（白底或深色）/ 其他设置没被顺手改掉
3. 若仍不满意：**先请用户关闭程序**，再重复第四步换值
4. 交付时说明：改了哪个文件、备份在哪、怎么回滚

## 通用经验（写给下一次）

- 用户说"**只有注释看不清**"→ 优先怀疑配色；说"**只有汉字看不见**"→ 优先怀疑字体
- 用户说"**改完没反应**"→ 90% 是程序没关，或改错了配置文件（多用户/便携版路径不同）
- 白底主题：前景一律选**深色**；深色主题：前景选**浅色**——同色系撞车是最常见事故
- 中文等宽字体首选 `NSimSun`；非等宽但更好看用 `Microsoft YaHei`；`Consolas` 拉丁最佳但**不含汉字字形**
- **一次会话里连续改多次**：备份名必须去重（同一秒内两次修改会互相覆盖，把最早的原始版本冲掉）。脚本已用 `unique_path()` 处理
- **别信"改完了"**：必须让用户重启编辑器看一眼才算完成；改配置的全部风险都在"以为生效了"上

## 已验证（不要凭感觉信，看断言）

`scripts/` 下带两套可重跑的端到端测试，在合成配置上模拟真实文件（GBK + 中文路径 + 引号 + CRLF）：

| 命令 | 覆盖 | 结果 |
|---|---|---|
| `python scripts/_e2e_test.py` | ini：定位 → 试运行 → 真写 → 多字段保护 → 空操作 → 备份回滚 → 编码不变 | **30/30 通过** |
| `python scripts/_e2e_test_json.py` | JSONC：注释/尾逗号保留 → 改键 → 新增键 → 试运行 → 中文值 → 备份不互相覆盖 → 回滚字节一致 | **23/23 通过** |

这两个测试在写完之后**真的抓出过 5 个 bug**（引号被吞、输出多空行、备份互相覆盖、文档里的 CLI 写法和脚本不符、`--path` 缺失），说明"写完没测"和"测过"完全是两回事。改脚本后**务必重跑**。
