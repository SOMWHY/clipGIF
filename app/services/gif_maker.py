import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from collections.abc import Callable

from app.config import MAX_GIF_BYTES, MAX_CLIP_SECONDS
from app.services.errors import ClipGifError


DEFAULT_FPS = 12
DEFAULT_COLORS = 128


def _tool_path() -> str:
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise ClipGifError("未找到 ffmpeg，请安装后重启 ClipGIF。")
    return executable


def _time_value(value: float) -> str:
    if not math.isfinite(value):
        raise ClipGifError("时间必须是有限数字。")
    return f"{value:.3f}".rstrip("0").rstrip(".")


def make_gif(
    source_path: Path,
    output_path: Path,
    start: float,
    end: float,
    on_stage: Callable[[str], None] | None = None,
) -> Path:
    if not math.isfinite(start) or not math.isfinite(end):
        raise ClipGifError("时间必须是有限数字。")
    if start < 0 or end <= start:
        raise ClipGifError("结束时间必须大于开始时间，且开始时间不能小于 0。")
    if end - start > MAX_CLIP_SECONDS:
        raise ClipGifError(f"片段不能超过 {MAX_CLIP_SECONDS:g} 秒。")
    if not source_path.is_file():
        raise ClipGifError("找不到源视频，请重新加载视频。")
    ffmpeg = _tool_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.stem}-", suffix="-palette.png", dir=output_path.parent, delete=False
    ) as palette_file:
        palette_path = Path(palette_file.name)
    palette_path.unlink(missing_ok=True)

    start_value = _time_value(start)
    duration_value = _time_value(end - start)
    palette_filter = (
        f"fps={DEFAULT_FPS},scale=w=min(480\\,iw):h=-2:flags=lanczos,"
        f"palettegen=max_colors={DEFAULT_COLORS}"
    )
    gif_filter = (
        f"[0:v]fps={DEFAULT_FPS},scale=w=min(480\\,iw):h=-2:flags=lanczos[video];"
        "[video][1:v]paletteuse=dither=sierra2_4a"
    )
    palette_command = [
        ffmpeg, "-y", "-ss", start_value, "-t", duration_value,
        "-i", str(source_path), "-vf", palette_filter, "-frames:v", "1", str(palette_path),
    ]
    gif_command = [
        ffmpeg, "-y", "-ss", start_value, "-t", duration_value,
        "-i", str(source_path), "-i", str(palette_path),
        "-filter_complex", gif_filter, "-loop", "0", "-an", str(output_path),
    ]
    succeeded = False
    try:
        if on_stage is not None:
            on_stage("clipping")
        palette_result = subprocess.run(
            palette_command, capture_output=True, text=True, timeout=600, check=False
        )
        if palette_result.returncode != 0:
            raise ClipGifError("GIF 调色板生成失败，请换一个视频片段重试。")
        if on_stage is not None:
            on_stage("transcoding")
        gif_result = subprocess.run(
            gif_command, capture_output=True, text=True, timeout=600, check=False
        )
        if gif_result.returncode != 0:
            raise ClipGifError("GIF 转码失败，请换一个视频片段重试。")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise ClipGifError("GIF 转码没有生成有效文件。")
        if output_path.stat().st_size > MAX_GIF_BYTES:
            raise ClipGifError("生成的 GIF 超过 50 MB；请缩短片段后重试。")
        succeeded = True
        return output_path
    except subprocess.TimeoutExpired as exc:
        raise ClipGifError("GIF 生成超时，请尝试更短的视频片段。") from exc
    finally:
        palette_path.unlink(missing_ok=True)
        if not succeeded and output_path.exists():
            output_path.unlink(missing_ok=True)
