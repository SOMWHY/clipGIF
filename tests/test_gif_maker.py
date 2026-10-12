from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models import CropRegion, GifRequest
from app.services import gif_maker
from app.services.errors import ClipGifError


@pytest.mark.parametrize(
    ("start", "end"),
    [(-1, 2), (2, 2), (5, 4), (0, 60.1), (float("nan"), 1), (0, float("inf"))],
)
def test_gif_request_rejects_invalid_range(start, end):
    with pytest.raises(ValidationError):
        GifRequest(start=start, end=end)


def test_gif_request_preserves_decimal_seconds():
    request = GifRequest(start=12.5, end=18)
    assert request.start == 12.5
    assert request.end == 18.0


def test_gif_request_uses_current_export_defaults():
    request = GifRequest(start=0, end=3)
    assert request.fps == 12
    assert request.speed == 1
    assert request.width is None
    assert request.height is None
    assert request.max_colors == 128
    assert request.dither == "sierra2_4a"
    assert request.crop is None


def test_gif_request_accepts_advanced_export_options():
    request = GifRequest(
        start=0,
        end=3,
        crop={"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6},
        width=640,
        height=480,
        fps=20,
        speed=2,
        max_colors=256,
        dither="bayer",
    )
    assert request.crop.x == 0.1
    assert request.width == 640
    assert request.height == 480
    assert request.fps == 20
    assert request.speed == 2
    assert request.max_colors == 256
    assert request.dither == "bayer"


@pytest.mark.parametrize(
    "crop",
    [
        {"x": -0.1, "y": 0, "width": 0.5, "height": 0.5},
        {"x": 0.8, "y": 0, "width": 0.3, "height": 0.5},
        {"x": 0, "y": 0, "width": 0, "height": 0.5},
        {"x": 0, "y": 0, "width": float("nan"), "height": 0.5},
    ],
)
def test_gif_request_rejects_invalid_crop(crop):
    with pytest.raises(ValidationError):
        GifRequest(start=0, end=3, crop=crop)


@pytest.mark.parametrize(
    "options",
    [
        {"width": 63},
        {"width": True},
        {"height": 1281},
        {"fps": 8},
        {"fps": True},
        {"speed": 3},
        {"max_colors": 32},
        {"dither": "none"},
    ],
)
def test_gif_request_rejects_out_of_range_export_options(options):
    with pytest.raises(ValidationError):
        GifRequest(start=0, end=3, **options)


def test_make_gif_uses_two_palette_passes_and_source(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "result.gif"
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        target = Path(command[-1])
        target.write_bytes(b"generated")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gif_maker.shutil, "which", lambda _name: "ffmpeg.exe")
    monkeypatch.setattr(gif_maker.subprocess, "run", run)
    assert gif_maker.make_gif(
        source,
        output,
        GifRequest(start=12.5, end=15.5),
        640,
        360,
    ) == output
    assert len(calls) == 2
    assert all("-ss" in command and "12.5" in command for command in calls)
    assert str(source) in calls[0] and str(source) in calls[1]
    assert "palettegen=max_colors=128" in calls[0][calls[0].index("-vf") + 1]
    assert "paletteuse=dither=sierra2_4a" in calls[1][calls[1].index("-filter_complex") + 1]
    assert list(tmp_path.glob(".*palette.png")) == []


def test_make_gif_rejects_file_over_limit(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "large.gif"

    def run(command, **_kwargs):
        if str(output) == command[-1]:
            output.write_bytes(b"12345")
        else:
            Path(command[-1]).write_bytes(b"palette")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gif_maker, "MAX_GIF_BYTES", 4)
    monkeypatch.setattr(gif_maker.shutil, "which", lambda _name: "ffmpeg.exe")
    monkeypatch.setattr(gif_maker.subprocess, "run", run)
    with pytest.raises(ClipGifError, match="50 MB"):
        gif_maker.make_gif(source, output, GifRequest(start=0, end=1), 640, 360)
    assert not output.exists()


def test_make_gif_fails_on_ffmpeg_error(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    monkeypatch.setattr(gif_maker.shutil, "which", lambda _name: "ffmpeg.exe")
    monkeypatch.setattr(
        gif_maker.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="failed"),
    )
    with pytest.raises(ClipGifError, match="调色板"):
        gif_maker.make_gif(
            source,
            tmp_path / "bad.gif",
            GifRequest(start=0, end=1),
            640,
            360,
        )


def test_build_video_filter_applies_crop_speed_fps_and_exact_canvas():
    request = GifRequest(
        start=0,
        end=3,
        crop={"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
        width=640,
        height=480,
        fps=20,
        speed=2,
        max_colors=256,
        dither="bayer",
    )
    filters = gif_maker._build_video_filter(request, 1280, 720)
    assert "crop=" in filters
    assert "setpts=PTS/2" in filters
    assert "fps=20" in filters
    assert "force_original_aspect_ratio=decrease" in filters
    assert "pad=640:480" in filters


def test_crop_filter_keeps_bottom_right_region_inside_odd_frame():
    crop = CropRegion(x=0.5, y=0.5, width=0.5, height=0.5)
    result = gif_maker._crop_filter(crop, 1279, 719)
    assert result == (
        "crop=trunc(iw*0.5/2)*2:trunc(ih*0.5/2)*2:"
        "trunc(iw*0.5/2)*2:trunc(ih*0.5/2)*2"
    )


def test_crop_filter_rejects_region_smaller_than_minimum():
    crop = CropRegion(x=0, y=0, width=0.01, height=0.01)
    with pytest.raises(ClipGifError, match="裁切区域"):
        gif_maker._crop_filter(crop, 320, 240)


def test_full_frame_crop_preserves_the_original_odd_frame():
    request = GifRequest(start=0, end=3, crop={"x": 0, "y": 0, "width": 1, "height": 1})
    assert not gif_maker._build_video_filter(request, 1279, 719).startswith("crop=")


def test_make_gif_uses_identical_video_filters_for_palette_and_output(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"generated")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gif_maker.shutil, "which", lambda _name: "ffmpeg.exe")
    monkeypatch.setattr(gif_maker.subprocess, "run", run)
    request = GifRequest(start=0, end=3, fps=15, max_colors=64, dither="bayer")
    gif_maker.make_gif(source, tmp_path / "result.gif", request, 640, 360)
    palette_filter = calls[0][calls[0].index("-vf") + 1].split(",palettegen=")[0]
    output_graph = calls[1][calls[1].index("-filter_complex") + 1]
    assert palette_filter in output_graph
    assert "palettegen=max_colors=64" in calls[0][calls[0].index("-vf") + 1]
    assert "paletteuse=dither=bayer" in output_graph
