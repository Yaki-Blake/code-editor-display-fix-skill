# 各编辑器配置文件适配表

> **万能定位法**：不确定某个设置存在哪？**先在图形界面里改一次，再对比配置文件改前改后的差异**（`diff` 或文件时间戳排序），立刻知道该动哪个键。所有编辑器都适用。
>
> **通用顺序**：关闭程序 → 备份 → 改 → 校验 → 打开程序。

---

## 1. Dev-C++（Embarcadero 6.x / Orwell 5.11）

- **配置**：`%APPDATA%\Embarcadero\Dev-Cpp\devcpp.ini`（6.x）／`%APPDATA%\Dev-Cpp\devcpp.ini`（5.11）；便携版在安装目录。**GBK 编码**，含中文路径。
- **字体**：`[Editor.Font]` 的 `Name` / `Charset` / `Size`
  ```ini
  [Editor.Font]
  Name="NSimSun"     ; 中文等宽首选；Microsoft YaHei 更好看但非等宽
  Charset=134        ; 134 = GB2312；改中文字体时一并设置
  Size=12
  ```
  行号区单独在 `[Editor.Gutterfont]`（只有数字，一般不用改）。
- **配色**：`[Editor.Syntax]`，每行 `项=前景, 背景, 粗体, 斜体, 下划线`；背景由 `Space` 决定（`clBlack, clWhite` = 白底黑字）。
  ```ini
  Comment=6316128, clNone, 0, 1, 0     ; #606060 深灰 + 斜体
  ```
  颜色用 **Delphi TColor 十进制**（`0x00BBGGRR`）或常量名（`clGreen`…）。换算见 `devcpp-case.md`。
- **编码**：`[Editor] NewDocEncoding`（`"ANSI"` / `"UTF-8"`）。注意它只管**新建/保存**；打开已有文件时 Dev-C++ 会自行探测编码。
- **坑**：`clHighlight`（跟随系统高亮色）在白底上常看不清，注释别用它；改字体必须程序**完全退出**（实测退出时会覆盖回写）。

## 2. 小熊猫 C++（Red Panda Dev-C++）

- **配置**：`%APPDATA%\RedPanda-CPP\`（新版）；旧版或便携版可能在安装目录的 `config` 子目录。
- **做法**：目录里是 ini 系配置，**先用万能定位法**（在 UI 改一次字体，看哪个文件被写入、哪个值变了）确定确切文件名与键名——不同版本差异较大。
- **字体**：设置 → 编辑器 → 字体；UI 改完会写入 ini，键名通常是 `font=<字体名>,<字号>,…`
- **与 Dev-C++ 的关系**：小熊猫是完全重写版（Qt），**devcpp.ini 的键名不通用**，不要照搬。
- 编码：默认 UTF-8，一般无需处理；乱码时检查"文件 → 编码"。

## 3. Code::Blocks

- **配置**：`%APPDATA%\CodeBlocks\default.conf`，**XML 格式**（wxWidgets 配置）。
- **字体**：`<editor>` 节点下的 `font` 子节点
  ```xml
  <editor>
      <font>
          <str>Consolas</str>     <!-- 字体名 -->
          <int>12</int>           <!-- 字号 -->
      </font>
  ```
- **配色**：同文件 `<editor><colour_sets>` 下的配色方案（`ACTIVE_COLOUR_SET` 决定当前用哪套）。颜色是**RGB 分量**：
  ```xml
  <style5><FORE><colour r="128" g="128" b="128" /></FORE>
          <NAME><str><![CDATA[Comment (normal)]]></str></NAME></style5>
  ```
  常用 style 编号：`0/1`=Default（背景也在这里）、`5-8`=Comment、`9-10`=Comment line、`19`=Number、`21`=Keyword、`27/28`=String、`34`=Preprocessor、`36`=Operator、`38`=Selection、`39`=Active line。
- **坑**：改完 `default.conf` 后若 GUI 里字体又变回去，是"Syntax highlighting → Fonts & colours"里的按元素字体覆盖了全局字体——去那里改。
- 官方配色主题可整段替换 `<colour_sets>` 内容（Code::Blocks wiki 有现成主题）。

## 4. VS Code

- **配置**：`%APPDATA%\Code\User\settings.json`（**JSONC，含注释**）；工作区级在项目 `.vscode/settings.json`，**工作区优先**。
- **字体**：
  ```jsonc
  "editor.fontFamily": "'Microsoft YaHei', Consolas, monospace",
  "editor.fontSize": 14,
  "editor.fontLigatures": true
  ```
- **配色**：
  ```jsonc
  "workbench.colorTheme": "Default Light Modern",
  "editor.tokenColorCustomizations": {
      "comments": "#6A737D"        // 注释颜色
  },
  "workbench.colorCustomizations": {
      "editor.background": "#FFFFFF"
  }
  ```
- **编码（中文乱码首选）**：
  ```jsonc
  "files.encoding": "utf8",
  "files.autoGuessEncoding": true     // 打开 GBK 文件时自动猜编码，强烈建议开
  ```
- **坑**：VS Code 是 Electron，字体回退良好，一般**不会**出现"汉字隐形"；若用户自定义了 `fontFamily` 成纯拉丁字体才可能。中文乱码几乎都是编码问题，`files.autoGuessEncoding` 基本能解决。

## 5. Visual Studio

- **字体颜色**：`工具 → 选项 → 环境 → 字体和颜色`；配置存在注册表 `HKCU\Software\Microsoft\VisualStudio\<版本>_Config\FontsAndColors`。可导出 `.vssettings`（XML）再用"导入设置"分发。
- **编码（中文乱码）**：VS 默认保存为 UTF-8 with BOM；打开老 GBK 文件乱码时用 `文件 → 高级保存选项` 指定 `简体中文 (GB2312) - 代码页 936` 或转 UTF-8 后保存。
- **坑**：改注册表前先导出 `.vssettings` 备份；VS 运行时改注册表不生效，必须关闭。

## 6. CLion（及其他 JetBrains IDE）

- **配置目录**：`%APPDATA%\JetBrains\CLion<版本>\`（2020.1 之后；更早为 `%APPDATA%\JetBrains\CLion<版本>` 或 `~/.CLion<版本>`）。
  - `options\editor.xml` —— 编辑器字体等
  - `colors\*.icls` —— 配色方案（IntelliJ XML 格式，可导入导出）
  - `options\fileEncodings.xml` —— 文件编码
- **字体**：`options\editor.xml` 里找 `FONT_FACE` / `FONT_SIZE`；若没有，说明当前用的是配色方案自带字体（改 `colors\*.icls` 里的 `EDITOR_FONT_NAME`）。
  ```xml
  <component name="EditorSettings">
    <option name="FONT_FACE" value="Microsoft YaHei" />
    <option name="FONT_SIZE" value="14" />
  </component>
  ```
- **中文缺字的专用解法**：JetBrains 有**字体回退**设置 —— `设置 → 编辑器 → 字体 → 回退字体（Fallback font）` 选 `Microsoft YaHei`，比换主字体更优雅。
- **编码**：`设置 → 编辑器 → 文件编码`，把项目编码设为 UTF-8；乱码时检查 `fileEncodings.xml`。
- **坑**：IDE 运行时改 `options\` 下的文件会被覆盖（和 Dev-C++ 同理），必须退出后改。

## 7. Sublime Text

- **配置**：`%APPDATA%\Sublime Text\Packages\User\Preferences.sublime-settings`（**JSON 但允许注释**）。
- **字体 / 配色**：
  ```jsonc
  {
    "font_face": "Microsoft YaHei",     // 或 "Consolas, Microsoft YaHei"
    "font_size": 12,
    "color_scheme": "Packages/Color Scheme - Default/Monokai.sublime-color-scheme",
    "font_options": ["no_italic"]
  }
  ```
- **坑**：文件允许 `//` 注释，**用 JSON 解析器直接读会失败**；改的时候要用文本级替换保留注释（`scripts/json_patch.py` 已处理）。

## 8. Notepad++

- **配置**：`%APPDATA%\Notepad++\config.xml`（字体等）、`stylers.xml`（配色，各语言 lexer 的样式）。
- **字体**：`config.xml` 里的 `<FontName>` / `<FontSize>`。
- **配色**：`stylers.xml` 的 `<GlobalStyles>`（Default Style 的背景/前景）与各 lexer 段（`<LexerType name="cpp">` 里的 `Comment`、`CommentLine`、`Keyword`、`Number`、`String`…）。
  ```xml
  <Style name="Comment" fore="#606060" back="#FFFFFF" fontStyle="2"/>   <!-- 2 = 斜体 -->
  ```
  颜色是 `#RRGGBB`；`fontStyle` 位掩码：1=粗体、2=斜体、4=下划线。
- **编码**：`设置 → 首选项 → 新建文档 → 编码`；已有文件用 `编码` 菜单转换。

## 9. Vim / Neovim（Windows）

- **配置**：`%USERPROFILE%\_vimrc`（Vim）、`%LOCALAPPDATA%\nvim\init.lua` 或 `_vimrc`（Neovim）。
- **字体（仅 gVim 生效，终端里的字体由终端程序决定）**：
  ```vim
  set guifont=Consolas:h12           " Windows
  " 中文等宽：set guifont=NSimSun:h12
  ```
- **配色**：`colorscheme desert`；自定义方案放 `$HOME/vimfiles/colors/*.vim`，前景/背景用 `guifg=#RRGGBB guibg=#RRGGBB`。
- **编码**：
  ```vim
  set encoding=utf-8
  set fileencodings=ucs-bom,utf-8,gbk,gb18030,latin1
  ```
  最后一行能让 Vim 自动识别 GBK 中文文件，是 Windows 下乱码的常用解法。
- **坑**：终端（Windows Terminal 等）里的中文显示取决于**终端的字体设置**，改 vimrc 没用。

---

## 附：中文等宽字体速查

| 字体名（配置里写） | 等宽 | 含汉字 | 备注 |
|---|---|---|---|
| `NSimSun` | ✔ | ✔ | 首选，对齐完美 |
| `SimSun` | ✔ | ✔ | 字形更老 |
| `Microsoft YaHei` | ✘ | ✔ | 好看清晰，缩进略松 |
| `Consolas` | ✔ | ✘ | 拉丁最佳，**汉字靠回退，可能隐形** |
| `JetBrains Mono` | ✔ | ✘ | 同上，JetBrains 系可配 Fallback font 补救 |
| `Courier New` | ✔ | ✘ | 老牌，汉字同样靠回退 |
