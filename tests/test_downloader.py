from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from app.config import MAX_VIDEO_BYTES
from app.platforms.bilibili import BilibiliAdapter
from app.services import downloader
from app.services.errors import ClipGifError


class FakeYoutubeDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def extract_info(self, _url, download=True):
        assert download
        filename = Path(self.options["outtmpl"].replace("%(ext)s", "mp4"))
        filename.write_bytes(b"video")
        self.options["progress_hooks"][0]({"downloaded_bytes": 5})
        return {"filepath": str(filename), "title": "test"}

    def prepare_filename(self, info):
        return info["filepath"]


def test_download_uses_adapter_limits_and_cleans_cookie(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "WORK_DIR", tmp_path)
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    source, title = downloader.download_video(
        BilibiliAdapter(), "BV1xx411c7mD", "abc123", b"# Netscape HTTP Cookie File\n"
    )
    assert source.read_bytes() == b"video"
    assert title == "test"
    assert list((tmp_path / "abc123").glob(".cookies-*.txt")) == []


def test_download_rejects_invalid_cookie_format(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "WORK_DIR", tmp_path)
    with pytest.raises(ClipGifError, match="Netscape"):
        downloader.download_video(BilibiliAdapter(), "BV1xx411c7mD", "abc", b"secret")


def test_download_stops_oversized_stream(monkeypatch, tmp_path):
    class Oversized(FakeYoutubeDL):
        def extract_info(self, _url, download=True):
            self.options["progress_hooks"][0]({"downloaded_bytes": MAX_VIDEO_BYTES + 1})

    monkeypatch.setattr(downloader, "WORK_DIR", tmp_path)
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=Oversized))
    with pytest.raises(ClipGifError, match="超过 200 MB"):
        downloader.download_video(BilibiliAdapter(), "BV1xx411c7mD", "abc")


def test_login_failure_is_friendly_and_cookie_is_removed(monkeypatch, tmp_path):
    class LoginError(FakeYoutubeDL):
        def extract_info(self, _url, download=True):
            raise RuntimeError("login required")

    monkeypatch.setattr(downloader, "WORK_DIR", tmp_path)
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=LoginError))
    with pytest.raises(ClipGifError, match="需要登录"):
        downloader.download_video(
            BilibiliAdapter(), "BV1xx411c7mD", "abc", b"# Netscape HTTP Cookie File\n"
        )
    assert list((tmp_path / "abc").glob(".cookies-*.txt")) == []


def test_unavailable_formats_have_a_friendly_message(monkeypatch, tmp_path):
    class NoFormats(FakeYoutubeDL):
        def extract_info(self, _url, download=True):
            raise RuntimeError("No video formats found")

    monkeypatch.setattr(downloader, "WORK_DIR", tmp_path)
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=NoFormats))
    with pytest.raises(ClipGifError, match="可下载的视频格式"):
        downloader.download_video(BilibiliAdapter(), "BV1xx411c7mD", "abc")
    assert list((tmp_path / "abc").glob("source.*")) == []
