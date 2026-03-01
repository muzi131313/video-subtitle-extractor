---
name: video-subtitle-extractor
description: YouTube/Bilibili 视频字幕提取工具。从视频链接下载视频，自动提取字幕保存为 txt 文件，完成后清理视频文件。支持 YouTube 优先下载（支持 Cookie 认证绕过限制），失败时自动从 Bilibili 搜索下载；支持 Whisper AI 转录作为备选方案；支持单个视频和批量处理。使用场景：用户要求从 YouTube/Bilibili 下载视频字幕、提取视频字幕、保存视频文案为文本时触发。
---

# Video Subtitle Extractor

从 YouTube 或 Bilibili 视频链接下载视频并提取字幕，自动清理临时文件。

## 快速开始

### 单个视频

```bash
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxx"
```

### 使用 Whisper 转录（无字幕时）

```bash
# 自动使用 Whisper 作为备选
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxx"

# 指定 Whisper 模型大小
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxx" --whisper-model small

# 禁用 Whisper 转录
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxx" --no-whisper
```

### 批量处理

```bash
# 从文件读取 URL 列表（每行一个）
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py -f urls.txt
```

### Cookie 认证（绕过 YouTube 限制）

当 YouTube 触发机器人验证时，使用 cookie 进行身份验证：

```bash
# 方式 1: 使用 cookie 文件
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py "URL" --cookies /path/to/cookies.txt

# 方式 2: 从浏览器加载 cookie
python3 ~/.claude/skills/video-subtitle-extractor/scripts/download_and_extract.py "URL" --cookies-from-browser chrome
```

**导出 Cookie 的方法**：

1. **使用浏览器插件**（推荐）
   - 安装 "Get cookies.txt LOCALLY" 扩展
   - 访问 YouTube 并登录
   - 点击插件，导出 cookies.txt

2. **使用 yt-dlp 内置功能**
   ```bash
   # 从 Chrome 导出
   yt-dlp --cookies-from-browser chrome https://www.youtube.com/watch?v=xxx
   ```

**支持的浏览器**：
- Chrome
- Firefox
- Safari
- Edge
- Brave
- Opera
- Vivaldi
- Chromium

## 工作流程

```
输入 URL → 提取视频信息（标题）
   ↓
尝试 YouTube 下载 → 失败? → Bilibili 搜索下载（使用提取的标题）
   ↓
提取字幕（三级备选）
   ├─ 1. URL 字幕（最快）
   ├─ 2. 嵌入式字幕
   └─ 3. Whisper AI 转录（无字幕时）
   ↓
成功? → 删除视频文件 → 保存 txt 到 /subtitles
   ↓
更新 .gitignore
```

## Whisper AI 转录

当视频没有字幕时，自动使用 OpenAI Whisper 模型进行语音识别转录。

### 安装 Whisper

```bash
pip install openai-whisper
```

### 模型选择

| 模型 | 大小 | 速度 | 精度 | 适用场景 |
|------|------|------|------|----------|
| tiny | ~39MB | 最快 | 较低 | 快速测试 |
| base | ~74MB | 快 | 中等 | **默认推荐** |
| small | ~244MB | 中等 | 较高 | 日常使用 |
| medium | ~769MB | 慢 | 高 | 专业转录 |
| large | ~1550MB | 最慢 | 最高 | 最佳质量 |

### 转录语言

- 优先尝试中文转录 (`language='zh'`)
- 失败则自动检测语言

## 改进点

### 1. 先提取标题
即使 YouTube 下载失败，也会先提取视频标题，用于 Bilibili 搜索。

### 2. 智能 Bilibili 搜索
- 清理标题中的无关内容（如 "【2026最新版】"、"有手就会" 等）
- 使用标题匹配算法自动选择最佳结果
- 支持中文视频的精确匹配

### 3. 多源字幕提取
- 优先从 URL 直接提取字幕（无需下载完整视频）
- 备选方案：提取视频中的嵌入式字幕
- 最终备选：Whisper AI 转录

## 目录结构

```
project/
├── subtitles/              # 字幕输出目录 (自动添加到 .gitignore)
│   └── video_name_transcript.txt  # Whisper 转录文件
├── .video_temp/            # 临时下载目录
│   └── DtBktXq9kOs.mp4
└── .gitignore             # 自动更新
```

## 依赖

```bash
# 必需
pip install yt-dlp
brew install ffmpeg  # macOS

# 可选（用于 AI 转录）
pip install openai-whisper
```

## Claude 使用指南

当用户请求以下操作时使用此 skill：

- "从这个 YouTube 链接下载字幕"
- "帮我提取这个视频的字幕"
- "批量下载这些视频的字幕"
- "把视频文案保存成 txt"
- "解析字幕 <URL>"
- "使用 Whisper 转录视频"

### 处理步骤

1. 执行脚本下载并提取字幕
2. 显示视频信息（标题、时长）
3. 检查字幕提取结果
4. 报告处理状态

### 输出示例（含 Whisper）

```
==================================================
处理视频: https://www.youtube.com/watch?v=xxx
==================================================
🔍 获取视频信息...
📌 标题: 【2026最新版】10分钟教会你用Qwen3+RAGFlow...
⏱️ 时长: 1528 秒
📥 尝试从 YouTube 下载...
✅ YouTube 下载成功: DtBktXq9kOs.mp4
📝 提取字幕...
⚠️ 无法从 URL 获取字幕，尝试从视频文件提取...
⚠️ 未找到嵌入式字幕
⚠️ 无可用字幕，尝试使用 Whisper 转录...
🎙️ 使用 Whisper 转录音频...
   模型: base
   加载模型中...
   转录中... (这可能需要几分钟)
✅ Whisper 转录完成
🗑️ 已删除临时视频文件

✅ 字幕已保存: DtBktXq9kOs_transcript.txt
```

### 无字幕处理

如果视频没有字幕且 Whisper 不可用：
- 输出提示信息
- **保留视频文件**供用户检查
- 显示视频文件位置
- 提示安装 Whisper

## 错误处理

### YouTube 机器人验证

当遇到以下错误时：
```
ERROR: Sign in to confirm you're not a bot.
```

**解决方案**：

1. **使用 Cookie 文件**
   - 安装浏览器扩展 "Get cookies.txt LOCALLY"
   - 登录 YouTube 后导出 cookies
   - 使用 `--cookies /path/to/cookies.txt` 参数

2. **从浏览器加载 Cookie**
   - 使用 `--cookies-from-browser chrome` 等参数
   - 需要浏览器支持（Chrome/Firefox/Safari/Edge 等）

3. **稍后重试** - YouTube 的限制通常是临时的

### 常见问题

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| Sign in to confirm bot | YouTube 频繁访问限制 | 使用 cookies 认证 |
| No subtitles found | 视频无字幕 | 使用 Whisper 转录 |
| FFmpeg not found | 未安装 ffmpeg | `brew install ffmpeg` |
| Whisper not available | 未安装 openai-whisper | `pip install openai-whisper` |

## 资源

### scripts/download_and_extract.py

主脚本，包含完整工作流程：

**核心函数：**
- `get_video_info()` - 提取视频信息（标题、时长等）
- `download_from_youtube()` - YouTube 下载
- `search_bilibili_by_title()` - Bilibili 搜索下载
- `extract_subtitles_from_url()` - 从 URL 提取字幕
- `extract_embedded_subtitles()` - 提取嵌入式字幕
- `transcribe_with_whisper()` - Whisper AI 转录
- `convert_vtt_to_txt()` / `convert_srt_to_txt()` - 字幕格式转换
- `process_video()` - 单个视频处理主流程
- `process_batch()` - 批量处理
