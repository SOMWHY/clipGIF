import json
import math
from pathlib import Path
import shutil
import subprocess

from app.config import MAX_PREVIEW_BYTES
from app.services.errors import ClipGifError


def _tool_path(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise ClipGifError(f"未找到 {name}，请安装 ffmpeg 后重启 ClipGIF。")
    return executable


def make_preview(source_path: Path, output_path: Path) -> dict[str, float | int]:
    ffmpeg = _tool_path("ffmpeg")
    ffprobe = _tool_path("ffprobe")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg, "-y", "-i", str(source_path),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", r"scale=-2:min(480\,ih)",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", str(output_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise ClipGifError("生成预览超时，请尝试更短或更小的视频。") from exc
    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise ClipGifError("无法生成视频预览，请检查源视频格式或重新加载。")
    if not output_path.is_file():
        raise ClipGifError("预览视频转码未生成文件。")
    if output_path.stat().st_size > MAX_PREVIEW_BYTES:
        output_path.unlink(missing_ok=True)
        raise ClipGifError("预览视频超过 100 MB，暂时无法提供预览。")

    try:
        probe = subprocess.run(
            [
                ffprobe, "-v", "error", "-select_streams", "v:0",
                "-show_entries", "format=duration:stream=width,height",
                "-of", "json", str(output_path),
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise ClipGifError("读取预览视频信息超时，请重新加载视频。") from exc
    if probe.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise ClipGifError("无法读取预览视频信息，请重新加载视频。")
    try:
        data = json.loads(probe.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        width, height = int(stream["width"]), int(stream["height"])
        if not math.isfinite(duration) or duration <= 0 or width <= 0 or height <= 0:
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        output_path.unlink(missing_ok=True)
        raise ClipGifError("预览视频缺少有效的时长或尺寸信息。") from exc
    return {"duration": duration, "width": width, "height": height}
