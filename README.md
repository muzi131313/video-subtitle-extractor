# Video Subtitle Extractor

YouTube/Bilibili 视频字幕提取工具 - 自动下载视频、提取字幕并清理临时文件。

## 功能特性

- **多平台支持**: YouTube (优先) 和 Bilibili
- **智能降级**: YouTube 下载失败时自动搜索 Bilibili
- **字幕提取**: 支持自动字幕、手动字幕、嵌入式字幕
- **AI 转录**: 集成 Whisper AI 语音识别（无字幕时自动转录）
- **Cookie 认证**: 支持浏览器 Cookie 绕过 YouTube 限制
- **批量处理**: 支持批量处理多个视频
- **自动清理**: 提取字幕后自动删除视频文件

## 安装

### 依赖安装

```bash
# 必需依赖
pip install yt-dlp
brew install ffmpeg  # macOS

# 可选依赖（用于 AI 转录）
pip install openai-whisper
```

### Claude Skill 安装

将此 skill 目录放置在 `~/.claude/skills/video-subtitle-extractor/`

## 使用方法

### 单个视频

```bash
python3 scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxx"
```

### 使用 Cookie 认证（绕过 YouTube 限制）

```bash
# 方式 1: 从浏览器加载 Cookie
python3 scripts/download_and_extract.py "URL" --cookies-from-browser chrome

# 方式 2: 使用 Cookie 文件
python3 scripts/download_and_extract.py "URL" --cookies /path/to/cookies.txt
```

**支持的浏览器**: chrome, firefox, safari, edge, brave, opera, vivaldi, chromium

### 批量处理

```bash
# 从文件读取 URL 列表（每行一个）
python3 scripts/download_and_extract.py -f urls.txt
```

### Whisper 转录选项

```bash
# 指定 Whisper 模型大小
python3 scripts/download_and_extract.py "URL" --whisper-model small

# 禁用 Whisper 转录
python3 scripts/download_and_extract.py "URL" --no-whisper
```

## Whisper 模型选择

| 模型 | 大小 | 速度 | 精度 | 适用场景 |
|------|------|------|------|----------|
| tiny | ~39MB | 最快 | 较低 | 快速测试 |
| base | ~74MB | 快 | 中等 | **默认推荐** |
| small | ~244MB | 中等 | 较高 | 日常使用 |
| medium | ~769MB | 慢 | 高 | 专业转录 |
| large | ~1550MB | 最慢 | 最高 | 最佳质量 |

## 工作流程

```
输入 URL → 提取视频信息（标题）
   ↓
尝试 YouTube 下载 → 失败? → Bilibili 搜索下载
   ↓
提取字幕（三级备选）
   ├─ 1. URL 字幕（最快）
   ├─ 2. 嵌入式字幕
   └─ 3. Whisper AI 转录
   ↓
成功? → 删除视频 → 保存 txt 到 /subtitles
```

## 目录结构

```
project/
├── subtitles/              # 字幕输出目录 (自动添加到 .gitignore)
│   └── video_name_transcript.txt
├── .video_temp/            # 临时下载目录
└── .gitignore              # 自动更新
```

## 常见问题

### YouTube 机器人验证

**错误**: `Sign in to confirm you're not a bot`

**解决方案**:
1. 使用 `--cookies-from-browser chrome` 从浏览器加载 Cookie
2. 安装 "Get cookies.txt LOCALLY" 浏览器扩展导出 Cookie 文件
3. 使用 `--cookies /path/to/cookies.txt` 指定 Cookie 文件

### 无字幕处理

如果视频没有字幕且 Whisper 不可用：
- 输出提示信息
- 保留视频文件供检查
- 提示安装 Whisper: `pip install openai-whisper`

### Cookie 导出方法

1. **使用浏览器插件**（推荐）
   - 安装 "Get cookies.txt LOCALLY" 扩展
   - 访问 YouTube 并登录
   - 点击插件导出 cookies.txt

2. **使用 yt-dlp 内置功能**
   ```bash
   yt-dlp --cookies-from-browser chrome https://www.youtube.com/watch?v=xxx
   ```

## CLI 参数

```
positional arguments:
  url                   视频 URL

optional arguments:
  -h, --help            显示帮助信息
  -t, --title TITLE     Bilibili 搜索用的标题
  -b, --batch           批量模式
  -f, --file FILE       包含 URL 列表的文件
  --no-whisper          禁用 Whisper 转录
  --whisper-model       Whisper 模型大小 (tiny/base/small/medium/large)
  --cookies COOKIES     Cookie 文件路径
  --cookies-from-browser BROWSER
                        从浏览器加载 Cookie
```

## 示例

```bash
# 基础使用
python3 scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxxxx"

# 使用 Chrome Cookie
python3 scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxxxx" --cookies-from-browser chrome

# 批量处理
cat urls.txt | python3 scripts/download_and_extract.py -f -

# 使用大模型转录
python3 scripts/download_and_extract.py "https://www.youtube.com/watch?v=xxxxx" --whisper-model large
```

## License

MIT License
