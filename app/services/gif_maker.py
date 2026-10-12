import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from collections.abc import Callable

from app.config import MAX_GIF_BYTES, MAX_CLIP_SECONDS
from app.models import CropRegion, GifRequest
from app.services.errors import ClipGifError


def _tool_path() -> str:
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise ClipGifError("未找到 ffmpeg，请安装后重启 ClipGIF。")
    return executable


def _time_value(value: float) -> str:
    if not math.isfinite(value):
        raise ClipGifError("时间必须是有限数字。")
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _fraction(value: float) -> str:
    return f"{value:.12g}"


def _crop_filter(crop: CropRegion, frame_width: int, frame_height: int) -> str:
    if frame_width <= 0 or frame_height <= 0:
        raise ClipGifError("无法读取视频画面尺寸，请重新加载视频。")
    if crop.width * frame_width < 16 or crop.height * frame_height < 16:
        raise ClipGifError("裁切区域太小，请至少保留 16×16 像素的画面。")

    x, y, width, height = map(_fraction, (crop.x, crop.y, crop.width, crop.height))
    return (
        f"crop=trunc(iw*{width}/2)*2:trunc(ih*{height}/2)*2:"
        f"trunc(iw*{x}/2)*2:trunc(ih*{y}/2)*2"
    )


def _scale_and_pad_filters(
    request: GifRequest, frame_width: int, frame_height: int
) -> list[str]:
    if frame_width <= 0 or frame_height <= 0:
        raise ClipGifError("无法读取视频画面尺寸，请重新加载视频。")
    crop = request.crop
    crop_width = frame_width * (crop.width if crop is not None else 1)
    crop_height = frame_height * (crop.height if crop is not None else 1)
    aspect_ratio = crop_width / crop_height

    if request.width is None and request.height is None:
        return [r"scale=w=min(480\,iw):h=-2:flags=lanczos"]

    if request.width is not None and request.height is not None:
        return [
            f"scale=w={request.width}:h={request.height}:"
            "force_original_aspect_ratio=decrease:flags=lanczos",
            f"pad={request.width}:{request.height}:(ow-iw)/2:(oh-ih)/2:color=black",
        ]

    if request.width is not None:
        derived_height = round(request.width / aspect_ratio)
        if derived_height < 1 or derived_height > 1280:
            raise ClipGifError("裁切后的 GIF 高度超出可处理范围（1–1280 像素）。")
        return [f"scale=w={request.width}:h=-2:flags=lanczos"]

    assert request.height is not None
    derived_width = round(request.height * aspect_ratio)
    if derived_width < 1 or derived_width > 1280:
        raise ClipGifError("裁切后的 GIF 宽度超出可处理范围（1–1280 像素）。")
    return [f"scale=w=-2:h={request.height}:flags=lanczos"]


def _build_video_filter(request: GifRequest, frame_width: int, frame_height: int) -> str:
    filters: list[str] = []
    if request.crop is not None:
        filters.append(_crop_filter(request.crop, frame_width, frame_height))
    if request.speed != 1:
        filters.append(f"setpts=PTS/{request.speed:g}")
    filters.append(f"fps={request.fps}")
    filters.extend(_scale_and_pad_filters(request, frame_width, frame_height))
    return ",".join(filters)


def make_gif(
    source_path: Path,
    output_path: Path,
    request: GifRequest,
    frame_width: int,
    frame_height: int,
    on_stage: Callable[[str], None] | None = None,
) -> Path:
    start, end = request.start, request.end
    if not math.isfinite(start) or not math.isfinite(end):
        raise ClipGifError("时间必须是有限数字。")
    if start < 0 or end <= start:
        raise ClipGifError("结束时间必须大于开始时间，且开始时间不能小于 0。")
    if end - start > MAX_CLIP_SECONDS:
        raise ClipGifError(f"片段不能超过 {MAX_CLIP_SECONDS:g} 秒。")
    if not source_path.is_file():
        raise ClipGifError("找不到源视频，请重新加载视频。")
    ffmpeg = _tool_path()
    video_filter = _build_video_filter(request, frame_width, frame_height)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.stem}-", suffix="-palette.png", dir=output_path.parent, delete=False
    ) as palette_file:
        palette_path = Path(palette_file.name)
    palette_path.unlink(missing_ok=True)

    start_value = _time_value(start)
    duration_value = _time_value(end - start)
    palette_filter = f"{video_filter},palettegen=max_colors={request.max_colors}"
    gif_filter = (
        f"[0:v]{video_filter}[video];"
        f"[video][1:v]paletteuse=dither={request.dither}"
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
