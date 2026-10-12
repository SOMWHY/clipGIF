import logging
from pathlib import Path
import re
import tempfile
from typing import Any

from app.config import MAX_COOKIE_BYTES, MAX_VIDEO_BYTES, WORK_DIR
from app.platforms.base import PlatformAdapter
from app.services.errors import ClipGifError


logger = logging.getLogger(__name__)
_COOKIE_HEADER = re.compile(br"(?im)^# Netscape HTTP Cookie File|^# HTTP Cookie File")


def download_video(
    adapter: PlatformAdapter,
    raw_input: str,
    preview_id: str,
    cookies: bytes | None = None,
) -> tuple[Path, str]:
    import yt_dlp

    work_dir = WORK_DIR / preview_id
    work_dir.mkdir(parents=True, exist_ok=True)
    output_template = work_dir / "source.%(ext)s"
    cookie_path: Path | None = None

    if cookies is not None:
        if len(cookies) > MAX_COOKIE_BYTES:
            raise ClipGifError("cookies.txt 文件不能超过 2 MB。")
        if not _COOKIE_HEADER.search(cookies[:4096]):
            raise ClipGifError("cookies.txt 必须是 Netscape 格式的 Cookie 文件。")
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".cookies-", suffix=".txt", dir=work_dir, delete=False
        ) as cookie_file:
            cookie_file.write(cookies)
            cookie_path = Path(cookie_file.name)

    options: dict[str, Any] = {
        "format": adapter.get_default_format(),
        "outtmpl": str(output_template),
        "noplaylist": True,
        "max_filesize": MAX_VIDEO_BYTES,
        "quiet": True,
        "no_warnings": True,
        "no_progress": True,
        "overwrites": True,
    }
    options.update(adapter.get_ytdlp_options({}))
    if cookie_path is not None:
        options["cookiefile"] = str(cookie_path)

    def enforce_size(progress: dict[str, Any]) -> None:
        downloaded = progress.get("downloaded_bytes", 0) or 0
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate") or 0
        if max(downloaded, total) > MAX_VIDEO_BYTES:
            raise ClipGifError("源视频超过 200 MB，已停止下载。")

    options["progress_hooks"] = [enforce_size]
    completed = False
    try:
        normalized_url = adapter.normalize(raw_input)
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(normalized_url, download=True)
            filename = (
                info.get("filepath")
                or next(
                    (
                        item.get("filepath") or item.get("filename")
                        for item in (info.get("requested_downloads") or [])
                        if item.get("filepath") or item.get("filename")
                    ),
                    None,
                )
                or downloader.prepare_filename(info)
            )
        source_path = Path(filename).resolve()
        if source_path.parent != work_dir.resolve():
            raise ClipGifError("下载器返回了无效的视频文件路径。")
        if not source_path.is_file():
            raise ClipGifError("视频下载未生成源文件，请稍后重试。")
        if source_path.stat().st_size > MAX_VIDEO_BYTES:
            source_path.unlink(missing_ok=True)
            raise ClipGifError("源视频超过 200 MB，无法处理。")
        completed = True
        return source_path, str(info.get("title") or adapter.extract_video_id(normalized_url) or "视频")
    except ClipGifError:
        raise
    except Exception as exc:
        logger.warning("Video download failed for preview %s (%s).", preview_id, type(exc).__name__)
        raise ClipGifError(adapter.format_download_error(exc)) from exc
    finally:
        if cookie_path is not None:
            cookie_path.unlink(missing_ok=True)
        if not completed:
            for partial in work_dir.iterdir():
                if partial.is_file() and partial.name.startswith("source."):
                    partial.unlink(missing_ok=True)
