#!/usr/bin/env python3
"""
Video Subtitle Extractor
Downloads video from YouTube/Bilibili, extracts subtitles, and cleans up.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import yt_dlp
except ImportError:
    print("❌ Error: yt-dlp not installed")
    print("Please install: pip install yt-dlp")
    sys.exit(1)

# Check for Whisper (optional)
WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    pass


def run_command(cmd: list, check: bool = True) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check
    )
    return result.returncode, result.stdout, result.stderr


def get_video_info(url: str, cookies_file: str = None, cookies_from_browser: str = None) -> Optional[dict]:
    """
    Extract video info (title, id, etc.) without downloading.
    Works for both YouTube and other URLs.

    Args:
        url: Video URL
        cookies_file: Path to cookies file for authentication
        cookies_from_browser: Browser name to load cookies from
    """
    print(f"🔍 获取视频信息...")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file
    elif cookies_from_browser:
        ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            return {
                'title': info.get('title', 'Unknown'),
                'id': info.get('id', 'unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'description': info.get('description', ''),
            }
    except Exception as e:
        print(f"⚠️ 无法获取视频信息: {e}")
        return None


def download_from_youtube(url: str, output_dir: Path, cookies_file: str = None, cookies_from_browser: str = None) -> Optional[Path]:
    """
    Download video from YouTube using yt-dlp.
    Returns the path to downloaded video or None if failed.

    Args:
        url: YouTube URL
        output_dir: Directory to save video
        cookies_file: Path to cookies file for authentication
        cookies_from_browser: Browser name to load cookies from
    """
    print(f"📥 尝试从 YouTube 下载...")

    output_template = str(output_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        'format': 'best[height<=1080][ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
    }

    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file
    elif cookies_from_browser:
        ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_filename = ydl.prepare_filename(info)
            video_path = Path(video_filename)

            if video_path.exists():
                print(f"✅ YouTube 下载成功: {video_path.name}")
                return video_path

        print(f"❌ YouTube 下载失败")
        return None

    except Exception as e:
        print(f"❌ YouTube 下载失败: {e}")
        return None


def search_bilibili_by_title(title: str, output_dir: Path) -> Optional[Path]:
    """
    Search Bilibili using the video title and download the best match.
    Returns the path to downloaded video or None if failed.
    """
    print(f"🔍 在 Bilibili 搜索: {title}")

    # Skip if title is the default fallback
    if title == "video":
        print(f"⚠️ 搜索词过于通用，跳过 Bilibili 搜索")
        print(f"💡 提示: 请使用 --title 参数指定搜索关键词")
        return None

    # Clean up the title for better search results
    search_query = clean_title_for_search(title)

    # Use Bilibili search URL with URL encoding
    import urllib.parse
    encoded_query = urllib.parse.quote(search_query)
    search_url = f"https://search.bilibili.com/all?keyword={encoded_query}"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # Extract playlist/search results without downloading
        'playlistend': 10,  # Get top 10 results
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_result = ydl.extract_info(search_url, download=False)

            if not search_result:
                print(f"❌ Bilibili 搜索未返回结果")
                return None

            # Bilibili search returns entries directly
            entries = search_result.get('entries', []) if isinstance(search_result, dict) else []
            if not entries and isinstance(search_result, dict) and 'entries' in search_result:
                entries = search_result['entries']

            if not entries:
                print(f"❌ Bilibili 未找到相关视频")
                return None

            # Find best match
            best_match = find_best_bilibili_match(title, entries)
            if not best_match:
                print(f"❌ 未找到匹配的视频")
                return None

            bilibili_url = best_match.get('url') or best_match.get('webpage_url')
            match_title = best_match.get('title', 'Unknown')

            # Verify it's a Bilibili URL
            if not bilibili_url or ('bilibili.com' not in bilibili_url):
                print(f"⚠️ 搜索结果不是 Bilibili 链接")
                return None

            print(f"🎯 找到最佳匹配: {match_title}")
            print(f"🔗 链接: {bilibili_url}")

            # Download the matched video
            return download_from_url(bilibili_url, output_dir)

    except Exception as e:
        print(f"❌ Bilibili 搜索失败: {e}")
        return None


def clean_title_for_search(title: str) -> str:
    """
    Clean title for better search results.
    Remove common prefixes/suffixes that don't help with search.
    """
    # Remove common patterns
    patterns_to_remove = [
        r'\[.*?\]',  # brackets like [中字], [4K]
        r'【.*?】',  # Chinese brackets
        r'\(.*?\)',  # parentheses
        r'（.*?）',  # Chinese parentheses
        r'\d{4}最新版',  # year + 最新版
        r'\d+分钟.*?教会你',  # time based patterns
        r'有手就会',
        r'零成本',
        r'全程干货',
        r'小白也能',
    ]

    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned)

    # Keep the core content (first 50 chars usually contain the main topic)
    cleaned = cleaned.strip()[:50]

    return cleaned if cleaned else title


def find_best_bilibili_match(original_title: str, entries: List[dict]) -> Optional[dict]:
    """
    Find the best matching video from Bilibili search results.
    """
    original_lower = original_title.lower()
    cleaned_original = clean_title_for_search(original_title).lower()

    # Score each entry
    scored_entries = []
    for entry in entries:
        entry_title = entry.get('title', '').lower()
        score = 0

        # Exact match (high score)
        if original_lower in entry_title or entry_title in original_lower:
            score += 100

        # Cleaned title match
        if cleaned_original and cleaned_original in entry_title:
            score += 50

        # Word overlap scoring
        original_words = set(cleaned_original.split())
        entry_words = set(entry_title.split())
        if original_words:
            overlap = len(original_words & entry_words)
            score += overlap * 10

        scored_entries.append((score, entry))

    # Sort by score (highest first)
    scored_entries.sort(key=lambda x: x[0], reverse=True)

    # Return best match if score > 0
    if scored_entries and scored_entries[0][0] > 0:
        return scored_entries[0][1]

    # Fallback to first result
    return entries[0] if entries else None


def download_from_url(url: str, output_dir: Path) -> Optional[Path]:
    """Download video from a specific URL."""
    output_template = str(output_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        'format': 'best[height<=1080][ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_filename = ydl.prepare_filename(info)
            video_path = Path(video_filename)

            if video_path.exists():
                print(f"✅ 下载成功: {video_path.name}")
                return video_path

        return None

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None


def extract_subtitles(video_path: Path, output_dir: Path, url: str = None, use_whisper: bool = True, cookies_file: str = None, cookies_from_browser: str = None) -> Optional[Path]:
    """
    Extract subtitles from video.
    Tries multiple methods in order:
    1. Extract from URL (original subtitles)
    2. Extract embedded subtitles from video file
    3. Transcribe with Whisper (if available and enabled)

    Args:
        video_path: Path to the video file
        output_dir: Directory to save subtitles
        url: Original video URL (for extracting subtitles without downloading)
        use_whisper: Whether to use Whisper as fallback
        cookies_file: Path to cookies file for authentication
        cookies_from_browser: Browser name to load cookies from

    Returns:
        Path to the subtitle text file, or None if all methods failed
    """
    print(f"📝 提取字幕...")

    # Method 1: Try to get subtitles from original URL
    if url:
        subtitle_path = extract_subtitles_from_url(url, output_dir, cookies_file, cookies_from_browser)
        if subtitle_path:
            return subtitle_path
        print("⚠️ 无法从 URL 获取字幕，尝试从视频文件提取...")

    # Method 2: Try extracting embedded subtitles from video file
    subtitle_path = extract_embedded_subtitles(video_path, output_dir)
    if subtitle_path:
        return subtitle_path

    # Method 3: Use Whisper transcription as fallback
    if use_whisper:
        print("⚠️ 无可用字幕，尝试使用 Whisper 转录...")
        subtitle_path = transcribe_with_whisper(video_path, output_dir)
        if subtitle_path:
            return subtitle_path

    return None


def extract_subtitles_from_url(url: str, output_dir: Path, cookies_file: str = None, cookies_from_browser: str = None) -> Optional[Path]:
    """
    Extract subtitles directly from URL using yt-dlp (without downloading video).

    Args:
        url: Video URL
        output_dir: Directory to save subtitles
        cookies_file: Path to cookies file for authentication
        cookies_from_browser: Browser name to load cookies from
    """
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['zh-Hans', 'zh-Hant', 'zh', 'zh-Hans.cn', 'zh-Hant.cn', 'en'],
        'skip_download': True,
        'subtitlesformat': 'vtt',
        'outtmpl': str(output_dir / '%(title)s'),
        'quiet': False,
        'no_warnings': False,
    }

    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file
    elif cookies_from_browser:
        ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Find subtitle file
            title = info.get('title', 'video')
            safe_title = sanitize_filename(title)

            # Look for downloaded subtitle files
            for pattern in ['*.vtt', '*.zh-Hans.vtt', '*.zh.vtt', '*.en.vtt']:
                for sub_file in output_dir.glob(pattern):
                    if sub_file.name.startswith(safe_title) or 'subtitles' in sub_file.name.lower():
                        # Convert VTT to plain text
                        txt_path = output_dir / f"{safe_title}_subtitles.txt"
                        if convert_vtt_to_txt(sub_file, txt_path):
                            return txt_path

            return None

    except Exception as e:
        print(f"⚠️ 从 URL 提取字幕失败: {e}")
        return None


def extract_embedded_subtitles(video_path: Path, output_dir: Path) -> Optional[Path]:
    """
    Extract embedded subtitles from video file using ffmpeg.
    """
    print("📝 尝试从视频文件提取嵌入式字幕...")

    # First, check if there are any subtitle streams
    probe_cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 's',
        '-show_entries', 'stream=index,codec_name:stream_tags=language',
        '-of', 'json',
        str(video_path)
    ]

    try:
        returncode, stdout, stderr = run_command(probe_cmd, check=False)

        if returncode == 0 and stdout:
            streams_info = json.loads(stdout)
            if 'streams' in streams_info and streams_info['streams']:
                # Found subtitle streams, extract the first one
                subtitle_index = streams_info['streams'][0]['index']
                return extract_subtitle_stream(video_path, output_dir, subtitle_index)

    except Exception as e:
        pass

    print(f"⚠️ 未找到嵌入式字幕")
    return None


def extract_subtitle_stream(video_path: Path, output_dir: Path, stream_index: int) -> Optional[Path]:
    """Extract a specific subtitle stream from video."""
    output_path = output_dir / f"{video_path.stem}_subtitles.srt"

    cmd = [
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-map', f'0:s:{stream_index}',
        '-c:s', 'srt',
        str(output_path)
    ]

    returncode, stdout, stderr = run_command(cmd, check=False)

    if returncode == 0 and output_path.exists():
        # Convert SRT to plain text
        txt_path = output_dir / f"{video_path.stem}_subtitles.txt"
        if convert_srt_to_txt(output_path, txt_path):
            output_path.unlink()  # Remove SRT file
            return txt_path

    return None


def convert_vtt_to_txt(vtt_path: Path, txt_path: Path) -> bool:
    """Convert VTT subtitle file to plain text."""
    try:
        with open(vtt_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Remove VTT headers and timestamps
        lines = content.split('\n')
        text_lines = []

        for line in lines:
            line = line.strip()
            # Skip VTT specific lines
            if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                continue
            # Skip timestamp lines (e.g., 00:00:00.000 --> 00:00:05.000)
            if re.match(r'^\d{2}:\d{2}:\d{2}', line) or '-->' in line:
                continue
            # Skip note lines like NOTE
            if line == 'NOTE':
                continue
            # Skip style/configuration lines
            if line.startswith('style:') or line.startswith('region:'):
                continue

            text_lines.append(line)

        # Join and clean up
        text = ' '.join(text_lines)
        # Remove duplicate spaces
        text = re.sub(r'\s+', ' ', text).strip()

        if text:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return True

        return False

    except Exception as e:
        print(f"⚠️ 转换 VTT 失败: {e}")
        return False


def convert_srt_to_txt(srt_path: Path, txt_path: Path) -> bool:
    """Convert SRT subtitle file to plain text."""
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Remove SRT numbering and timestamps
        lines = content.split('\n')
        text_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines and index numbers
            if not line or line.isdigit():
                continue
            # Skip timestamp lines
            if re.match(r'^\d{2}:\d{2}:\d{2}', line):
                continue
            # Skip position tags
            if line.startswith('{') or line.startswith('}'):
                continue

            text_lines.append(line)

        # Join and clean up
        text = ' '.join(text_lines)
        text = re.sub(r'\s+', ' ', text).strip()

        if text:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return True

        return False

    except Exception as e:
        print(f"⚠️ 转换 SRT 失败: {e}")
        return False


def sanitize_filename(name: str) -> str:
    """Remove/replace characters not suitable for filenames."""
    # Remove or replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace('\n', ' ').replace('\r', ' ')
    # Limit length
    if len(name) > 100:
        name = name[:100]
    return name.strip()


def transcribe_with_whisper(video_path: Path, output_dir: Path, model_size: str = "base") -> Optional[Path]:
    """
    Transcribe video using OpenAI Whisper model.
    This is used as a fallback when no subtitles are available.

    Args:
        video_path: Path to the video file
        output_dir: Directory to save the transcription
        model_size: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Path to the transcription text file, or None if failed
    """
    if not WHISPER_AVAILABLE:
        print(f"⚠️ Whisper 未安装")
        print(f"   安装方法: pip install openai-whisper")
        return None

    print(f"🎙️ 使用 Whisper 转录音频...")
    print(f"   模型: {model_size}")

    try:
        import whisper

        # Load model
        print(f"   加载模型中...")
        model = whisper.load_model(model_size)

        # Transcribe
        print(f"   转录中... (这可能需要几分钟)")
        result = model.transcribe(str(video_path), language='zh', fp16=False)

        # Extract text
        transcript = result.get('text', '').strip()

        if not transcript:
            # Try without language specification
            result = model.transcribe(str(video_path), fp16=False)
            transcript = result.get('text', '').strip()

        if transcript:
            # Save to file
            txt_path = output_dir / f"{video_path.stem}_transcript.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(transcript)

            print(f"✅ Whisper 转录完成")
            return txt_path

        print(f"⚠️ Whisper 转录结果为空")
        return None

    except Exception as e:
        print(f"⚠️ Whisper 转录失败: {e}")
        return None


def update_gitignore(subtitles_dir: Path) -> None:
    """Add subtitles directory to .gitignore."""
    gitignore = Path.cwd() / ".gitignore"

    if not gitignore.exists():
        gitignore.write_text("")

    content = gitignore.read_text()
    entry = f"{subtitles_dir.name}/"

    if entry not in content.splitlines():
        with open(gitignore, 'a') as f:
            f.write(f"\n# Video subtitles\n{entry}\n")
        print(f"✅ 已将 {entry} 添加到 .gitignore")


def process_video(url: str, title: str = None, use_whisper: bool = True, whisper_model: str = "base", cookies_file: str = None, cookies_from_browser: str = None) -> bool:
    """
    Main workflow: download video, extract subtitles, cleanup.
    Returns True if successful, False otherwise.

    Args:
        url: Video URL
        title: Optional title for Bilibili search
        use_whisper: Whether to use Whisper transcription as fallback
        whisper_model: Whisper model size (tiny, base, small, medium, large)
        cookies_file: Path to cookies file for authentication
        cookies_from_browser: Browser name to load cookies from
    """
    # Create output directories
    temp_dir = Path.cwd() / ".video_temp"
    subtitles_dir = Path.cwd() / "subtitles"

    temp_dir.mkdir(exist_ok=True)
    subtitles_dir.mkdir(exist_ok=True)

    # Update .gitignore
    update_gitignore(subtitles_dir)

    video_path = None
    video_info = None

    # Step 1: Get video info first (extract title even if download fails)
    print(f"\n{'='*50}")
    print(f"处理视频: {url}")
    print(f"{'='*50}")

    video_info = get_video_info(url, cookies_file, cookies_from_browser)
    if video_info:
        print(f"📌 标题: {video_info['title']}")
        print(f"⏱️ 时长: {video_info['duration']} 秒")

    # Step 2: Try YouTube download first
    if "youtube.com" in url or "youtu.be" in url:
        video_path = download_from_youtube(url, temp_dir, cookies_file, cookies_from_browser)

    # Step 3: If YouTube failed, try Bilibili with the extracted title
    if not video_path:
        # Determine search title
        if video_info and video_info['title'] and video_info['title'] != 'Unknown':
            search_title = video_info['title']
        elif title:
            search_title = title
        else:
            search_title = None

        if search_title:
            print(f"\n🔄 YouTube 下载失败，尝试 Bilibili 搜索...")
            video_path = search_bilibili_by_title(search_title, temp_dir)
        else:
            print(f"\n⚠️ 无法提取视频标题，跳过 Bilibili 搜索")
            print(f"💡 提示: 使用 --title 参数手动指定搜索关键词")
            print(f"   示例: python3 scripts/download_and_extract.py \"{url}\" --title \"视频标题\"")

    if not video_path:
        print(f"\n❌ 视频下载失败")
        return False

    # Step 4: Extract subtitles (with Whisper fallback)
    subtitle_path = extract_subtitles(video_path, subtitles_dir, url, use_whisper, cookies_file, cookies_from_browser)

    if subtitle_path:
        # Delete video file after successful extraction
        video_path.unlink()
        print(f"🗑️ 已删除临时视频文件")
        print(f"\n✅ 字幕已保存: {subtitle_path.name}")
        return True
    else:
        print(f"\n⚠️ 字幕提取失败，视频文件已保留")
        print(f"📁 视频位置: {video_path}")
        return False


def process_batch(urls: List[str], titles: List[str] = None, cookies_file: str = None, cookies_from_browser: str = None) -> None:
    """Process multiple videos."""
    if titles and len(titles) != len(urls):
        print("❌ 标题数量与链接数量不匹配")
        return

    print(f"🎬 开始批量处理 {len(urls)} 个视频")

    success_count = 0
    for i, url in enumerate(urls):
        title = titles[i] if titles else None
        if process_video(url, title, cookies_file=cookies_file, cookies_from_browser=cookies_from_browser):
            success_count += 1

    print(f"\n{'='*50}")
    print(f"✅ 完成: {success_count}/{len(urls)} 个视频处理成功")
    print(f"📁 字幕保存在: {Path.cwd() / 'subtitles'}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description="Download video and extract subtitles from YouTube/Bilibili"
    )
    parser.add_argument("url", nargs="?", help="Video URL")
    parser.add_argument("-t", "--title", help="Video title for Bilibili search")
    parser.add_argument("-b", "--batch", action="store_true", help="Batch mode")
    parser.add_argument("-f", "--file", help="File containing URLs (one per line)")
    parser.add_argument("--no-whisper", action="store_true", help="Disable Whisper transcription fallback")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--cookies", help="Path to cookies file for YouTube authentication")
    parser.add_argument("--cookies-from-browser", choices=["chrome", "firefox", "safari", "edge", "brave", "opera", "vivaldi", "chromium"],
                        help="Load cookies from browser (requires yt-dlp + browser support)")

    args = parser.parse_args()

    use_whisper = not args.no_whisper
    cookies_file = args.cookies
    cookies_from_browser = args.cookies_from_browser

    if args.file:
        with open(args.file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        process_batch(urls, cookies_file=cookies_file, cookies_from_browser=cookies_from_browser)

    elif args.url:
        process_video(args.url, args.title, use_whisper, args.whisper_model, cookies_file, cookies_from_browser)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
