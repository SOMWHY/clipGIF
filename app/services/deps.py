import shutil
import sys


MIN_PYTHON = (3, 11)


def _platform_hint(tool: str) -> str:
    if tool == "ffmpeg":
        if sys.platform == "win32":
            return "Windows：可运行 `winget install --id Gyan.FFmpeg.Shared -e`，或从 https://ffmpeg.org/download.html 下载并将 bin 目录加入 PATH。"
        if sys.platform == "darwin":
            return "macOS（实验性）：运行 `brew install ffmpeg`。"
        return "Linux（实验性）：运行 `sudo apt install ffmpeg`（Debian/Ubuntu）或 `sudo dnf install ffmpeg`（Fedora）。"
    if sys.platform == "win32":
        return "Windows：使用本项目启动脚本安装，或运行 `.venv\\Scripts\\python.exe -m pip install yt-dlp`。"
    if sys.platform == "darwin":
        return "macOS：激活项目虚拟环境后运行 `python3 -m pip install yt-dlp`。"
    return "Linux：激活项目虚拟环境后运行 `python -m pip install yt-dlp`。"


def check_ffmpeg() -> tuple[bool, str]:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return True, "ffmpeg 和 ffprobe 已就绪。"
    return False, f"未找到 ffmpeg 或 ffprobe。{_platform_hint('ffmpeg')}"


def check_ytdlp() -> tuple[bool, str]:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return False, f"未找到 yt-dlp。{_platform_hint('yt-dlp')}"
    return True, "yt-dlp 已就绪。"


def check_python_version() -> tuple[bool, str]:
    if sys.version_info[:2] >= MIN_PYTHON:
        return True, f"Python {sys.version_info[0]}.{sys.version_info[1]} 已就绪。"
    if sys.platform == "win32":
        hint = "Windows 安装指引：https://www.python.org/downloads/windows/"
    elif sys.platform == "darwin":
        hint = "macOS 安装指引：https://www.python.org/downloads/macos/"
    else:
        hint = "Linux 请安装发行版提供的 Python 3.11 或更高版本。"
    return False, (
        f"需要 Python 3.11 或更高版本；当前为 {sys.version_info[0]}.{sys.version_info[1]}。{hint}"
    )
