import sys

from app.services import deps


def test_ffmpeg_check_requires_both_binaries(monkeypatch):
    found = {"ffmpeg": "ffmpeg.exe", "ffprobe": "ffprobe.exe"}
    monkeypatch.setattr(deps.shutil, "which", lambda name: found.get(name))
    assert deps.check_ffmpeg() == (True, "ffmpeg 和 ffprobe 已就绪。")

    found.pop("ffprobe")
    ok, message = deps.check_ffmpeg()
    assert not ok
    assert "ffprobe" in message


def test_ffmpeg_hint_is_platform_specific(monkeypatch):
    monkeypatch.setattr(deps.shutil, "which", lambda _name: None)
    monkeypatch.setattr(deps.sys, "platform", "win32")
    assert "winget" in deps.check_ffmpeg()[1]
    monkeypatch.setattr(deps.sys, "platform", "darwin")
    assert "brew install ffmpeg" in deps.check_ffmpeg()[1]
    monkeypatch.setattr(deps.sys, "platform", "linux")
    assert "apt install ffmpeg" in deps.check_ffmpeg()[1]


def test_python_version_check(monkeypatch):
    monkeypatch.setattr(deps.sys, "version_info", (3, 11, 0, "final", 0))
    assert deps.check_python_version()[0]
    monkeypatch.setattr(deps.sys, "version_info", (3, 10, 9, "final", 0))
    monkeypatch.setattr(deps.sys, "platform", "win32")
    ok, message = deps.check_python_version()
    assert not ok and "downloads/windows" in message
    monkeypatch.setattr(deps.sys, "platform", "darwin")
    assert "downloads/macos" in deps.check_python_version()[1]
    monkeypatch.setattr(deps.sys, "platform", "linux")
    assert "Linux" in deps.check_python_version()[1]


def test_ytdlp_check_reports_missing_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    ok, message = deps.check_ytdlp()
    assert not ok
    assert "yt-dlp" in message
