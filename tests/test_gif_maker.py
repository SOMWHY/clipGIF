from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models import GifRequest
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
    assert GifRequest(start=12.5, end=18).model_dump() == {"start": 12.5, "end": 18.0}


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
    assert gif_maker.make_gif(source, output, 12.5, 15.5) == output
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
        gif_maker.make_gif(source, output, 0, 1)
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
        gif_maker.make_gif(source, tmp_path / "bad.gif", 0, 1)
