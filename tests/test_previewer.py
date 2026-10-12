import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import previewer
from app.services.errors import ClipGifError


def test_preview_command_and_probe_metadata(monkeypatch, tmp_path):
    calls = []
    output = tmp_path / "preview.mp4"

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if "ffmpeg.exe" in command[0]:
            output.write_bytes(b"preview")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"streams": [{"width": 854, "height": 480}], "format": {"duration": "12.5"}}),
            stderr="",
        )

    monkeypatch.setattr(previewer.shutil, "which", lambda name: f"{name}.exe")
    monkeypatch.setattr(previewer.subprocess, "run", run)
    info = previewer.make_preview(tmp_path / "source.mp4", output)
    command = calls[0][0]
    assert isinstance(command, list)
    assert "-movflags" in command and "+faststart" in command
    assert "libx264" in command and "aac" in command
    assert info == {"duration": 12.5, "width": 854, "height": 480}


def test_preview_requires_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(previewer.shutil, "which", lambda _name: None)
    with pytest.raises(ClipGifError, match="ffmpeg"):
        previewer.make_preview(tmp_path / "source.mp4", tmp_path / "preview.mp4")
