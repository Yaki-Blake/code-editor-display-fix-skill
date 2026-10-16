# Dev-C++ 实战案例与颜色换算

> Dev-C++ 是本 skill 唯一配套了专用脚本（`scripts/ini_patch.py`）的编辑器，其余编辑器按 `editors.md` 手动处理。

## 一、颜色格式换算（Dev-C++ / Delphi）

`[Editor.Syntax]` 的颜色可以写常量名，也可以写 **TColor 十进制整数**（格式 `$00BBGGRR`，注意是 **BGR** 顺序）：

```
TColor = R + G*256 + B*65536        # 把 #RRGGBB 反着读成 BBGGRR 再当十进制
```

| 想要的颜色 | #RRGGBB | 写进 ini 的十进制 | 用途 |
|---|---|---|---|
| 深灰 | #606060 | `6316128` | **白底注释首选** |
| 深绿 | #007000 | `28672` | 传统注释色 |
| 深蓝 | #0000A0 | `10485760` | |
| 深红 | #800000 | `128` | |
| 中灰 | #808080 | `8421504` | 白底偏浅，慎用 |

常用常量名：`clBlack` `clWhite` `clRed` `clGreen` `clBlue` `clPurple` `clGray` `clNavy` `clMaroon` `clBtnFace`
（`clNone` 表示"用默认背景"，`clHighlight` 表示"跟随系统高亮色"——**白底上常常看不清，别给注释用**）

## 二、[Editor.Syntax] 行格式

```
项=前景色, 背景色, 粗体, 斜体, 下划线
```

白底参考配置：

```ini
[Editor.Syntax]
Character=clBlack, clNone, 0, 0, 0
Comment=6316128, clNone, 0, 1, 0          ; 深灰 + 斜体
Identifier=clBlack, clNone, 0, 0, 0
Number=clPurple, clNone, 0, 0, 0
Preprocessor=clGreen, clNone, 0, 0, 0
ReservedWord=clBlack, clNone, 1, 0, 0     ; 关键字加粗
Space=clBlack, clWhite, 0, 0, 0           ; ← 编辑器底色（clWhite = 白底）
String=clRed, clNone, 0, 0, 0
Selected text=clWhite, clNavy             ; ← 选中时的前景/背景（只有两项）
```

> ⚠ 用 `ini_patch.py` 改这类行时**必须给完整值**（五个字段），否则会把后四个字段抹掉——脚本对这种情况会拒绝执行。

## 三、完整案例复盘（2026-10-16，实测）

### 现象

Dev-C++ 6.3，白色主题。注释里 `// 2^31`、`→`、`*` 等**数字和符号正常显示**，
"记账本""输出""剩下的大质数"等**汉字整片空白**；**用户点选整行后汉字立刻出现**。

### 排查

| 步骤 | 动作 | 结果 |
|---|---|---|
| 1 | 怀疑编码，读源文件字节 | 文件是 **UTF-8**，中文**完好存在**（192 个非 ASCII 字节，GBK 解码报错） → 排除"内容丢失" |
| 2 | 看用户描述的关键线索"选中才显示" | 字符数据正确 → 锁定**绘制阶段**（字体/颜色） |
| 3 | 查 `[Editor.Font]` | `Name="Consolas"` —— **纯拉丁字体，无汉字字形**；`Charset=1` |

### 根因

字体无汉字字形时，系统回退到别的字体代画；Dev-C++ 这条回退路径**丢掉前景色**，
汉字被画成接近白底的颜色 → 隐形。选中整行时前景被强制为 `Selected text` 里的白色 → 汉字显形。

### 修复

```
[Editor.Font]   Name: Consolas -> NSimSun      Charset: 1 -> 134
[Editor]        NewDocEncoding: ANSI -> UTF-8
[Editor.Syntax] Comment: clHighlight -> 6316128   (#606060 深灰)
```

### 踩坑记录（务必记住）

1. **第一次改完没生效**：趁 Dev-C++ 还开着改的，程序退出时用**内存里的旧设置**覆盖回写了文件。
   证据：文件 mtime 变成了程序启动/退出的时刻，`Name`/`NewDocEncoding` 变回原值，
   而 `[Editor.Syntax]` 的改动**被保留**（语法配色是启动时真读的，窗体属性不是）。
   → **必须在程序完全退出后改。**
2. **`devcpp.ini` 是 GBK 编码**且含中文路径（`Default="F:\七彩虹电脑文件"`），
   按 UTF-8 整体重写会永久毁掉它。
3. **注册表不可信**：`InstallLocation` 是垃圾值 `X`，`UninstallString` 指向已不存在的 `D:\软件\...`；
   实际装在 `F:\软件\DEV C++\Dev-Cpp\`。

### 最终配置

```
[Editor.Font]   Name="NSimSun"   Charset=134   Size=12
[Editor]        NewDocEncoding="UTF-8"
[Editor.Syntax] Comment=6316128, clNone, 0, 1, 0
                Space=clBlack, clWhite, 0, 0, 0      ; 白底黑字
[Editor.Gutterfont] Name="Consolas"                  ; 行号只有数字，不必改
```

## 四、常用操作

```bash
# 查看现状（进程状态 + 配置路径 + 字体/配色关键项）
python scripts/ini_patch.py locate

# 空跑
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134" --dry-run

# 实改（自动备份 + 校验）
python scripts/ini_patch.py set "Editor.Font:Name=NSimSun" "Editor.Font:Charset=134"

# 回滚
python scripts/ini_patch.py backups
python scripts/ini_patch.py restore devcpp.ini.bak-20261016-231801
```
