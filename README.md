# 🎵 Aurora Music · 本地音乐播放器

一款面向 Windows 的本地音乐播放器，采用 **深色 Aurora 风格** 界面（仿网易云布局）。支持全格式音频解码、联网歌词、联网专辑封面、桌面悬浮歌词与完整的播放控制。

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![UI](https://img.shields.io/badge/UI-Tkinter-1FD87A)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)

---

## ✨ 功能特性

- 📂 **本地音乐库**：扫描/拖拽导入文件夹，自动读取 ID3 元数据（标题/歌手/专辑/时长/内嵌封面）
- 🎶 **全格式解码**：内置 PyAV 解码器，mp3 / flac / wav / m4a / aac / ogg / wma / opus / ape 全支持
- 📡 **联网歌词**：网易云 + QQ 双接口自动匹配（「歌手 - 歌名」），LRC 解析、卡拉 OK 高亮
- 🖼️ **联网封面**：无内嵌专辑图时自动按「歌手 - 歌名」联网抓取并缓存复用
- 🪟 **桌面悬浮歌词**：独立透明窗口、置顶显示、右键可改字号/颜色/导入 LRC、鼠标靠近显底色
- 🔁 **播放模式**：列表循环 / 单曲循环 / 随机播放
- ⏮️ **完整控制**：上一曲 / 下一曲 / 播放暂停 / 进度拖动 / 音量（上下滑动面板）
- 🗂️ **播放列表**：收藏（持久化 favorites.json）、播放队列、下一首播放、拖拽排序
- 🎨 **Aurora 深色 UI**：无边框窗口、隐藏式滚动条、高清矢量图标（缩放不失真）

---

## 🚀 快速开始

### 方式一：直接运行 EXE（推荐）

从 [Releases](../../releases) 下载 `本地音乐播放器.exe`，双击即可使用。

### 方式二：源码运行

需要 Python 3.10+：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python 本地音乐播放器.py
```

### 方式三：打包为 EXE

```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --icon icon.ico --name "本地音乐播放器" 本地音乐播放器.py
```

产物在 `dist/` 目录下。

---

## 📖 使用说明

| 操作 | 方法 |
|---|---|
| 添加音乐 | 左侧「添加音乐文件夹」或直接把文件/文件夹拖进窗口 |
| 播放 / 暂停 | 空格键 或 底部 ▶ / ⏸ 按钮 |
| 上一曲 / 下一曲 | `Alt + ← / →` 或底部按钮 |
| 切换播放模式 | 点击循环按钮（列表循环 → 单曲循环 → 随机） |
| 歌词微调 | 桌面歌词窗口右键 → 字号 / 颜色 / 导入 LRC / 整体偏移 |
| 封面来源 | 歌曲右键菜单 →「封面来源」切换内嵌 / 联网 |

> 提示：歌词接口偶尔限流，稍后重试即可；建议文件名使用「歌手 - 歌名.mp3」格式以提高匹配率。

---

## 🧱 技术栈

- **GUI**：Tkinter（无边框自绘窗口）
- **音频**：pygame-ce（播放）+ PyAV（全格式解码转码）
- **图像**：Pillow（封面处理）
- **打包**：PyInstaller

## 📁 目录结构

```
本地音乐播放器/
├── 本地音乐播放器.py   # 主程序（单文件）
├── requirements.txt    # 依赖清单
├── icon.ico            # 应用图标
├── covers_cache/       # 联网封面缓存（自动生成）
└── favorites.json      # 收藏记录（自动生成）
```

## ⚖️ License

[MIT](LICENSE) © 2026 [Bluebee944](https://github.com/Bluebee944)
