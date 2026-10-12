import time

from app.platforms.base import PlatformAdapter, PlatformInfo
from app.platforms.registry import detect_platform, list_platforms, platform_registry, register_adapter
from app.services import jobs
from app.services.jobs import JobManager, PreviewJob


def test_bilibili_is_auto_discovered():
    assert platform_registry
    assert detect_platform("BV1xx411c7mD").name == "bilibili"
    assert [item.name for item in list_platforms()] == ["bilibili"]


def test_fake_adapter_can_be_registered_without_pipeline_changes(monkeypatch_platform, tmp_path):
    class FakeAdapter(PlatformAdapter):
        name = "fake"
        display_name = "Fake"

        def match(self, raw_input):
            return raw_input.startswith("fake:")

        def normalize(self, raw_input):
            return raw_input

        def extract_video_id(self, normalized_url):
            return normalized_url.split(":", 1)[1]

        def info(self):
            return PlatformInfo(self.name, self.display_name, ["fake:"], "")

    register_adapter(FakeAdapter())
    adapter = detect_platform("fake:abc123")
    assert adapter is not None
    assert adapter.extract_video_id(adapter.normalize("fake:abc123")) == "abc123"
    assert any(item.name == "fake" for item in list_platforms())

    def fake_download(received_adapter, raw_input, preview_id, _cookies):
        assert received_adapter is adapter
        assert raw_input == "fake:abc123"
        source = tmp_path / "source.mp4"
        source.write_bytes(b"source")
        return source, "fake title"

    def fake_preview(_source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"preview")
        return {"duration": 1.0, "width": 320, "height": 240}

    monkeypatch_platform.setattr(jobs, "download_video", fake_download)
    monkeypatch_platform.setattr(jobs, "make_preview", fake_preview)
    monkeypatch_platform.setattr(jobs, "PREVIEWS_DIR", tmp_path / "previews")
    manager = JobManager()
    job = PreviewJob("a" * 32, "fake", adapter)
    try:
        manager.add_preview(job, "fake:abc123", None)
        for _ in range(100):
            if job.status in {"ready", "failed"}:
                break
            time.sleep(0.01)
        assert job.status == "ready"
        assert job.platform == "fake"
    finally:
        manager.shutdown()


def test_unknown_platform_is_not_detected():
    assert detect_platform("https://example.com/video") is None
