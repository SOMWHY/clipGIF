from fastapi.testclient import TestClient

from app import main
from app.models import PreviewStatus
from app.platforms.registry import detect_platform
from app.services.jobs import JobManager, PreviewJob


def test_video_response_supports_range_get_and_head(monkeypatch, tmp_path):
    preview_dir = tmp_path / "previews"
    preview_dir.mkdir()
    preview_id = "f" * 32
    video = preview_dir / f"{preview_id}.mp4"
    video.write_bytes(bytes(range(256)) * 4)
    manager = JobManager()
    monkeypatch.setattr(main.app.state, "jobs", manager)
    monkeypatch.setattr(main, "PREVIEWS_DIR", preview_dir)
    manager.previews[preview_id] = PreviewJob(
        preview_id=preview_id,
        platform="bilibili",
        adapter=detect_platform("BV1xx411c7mD"),
        status=PreviewStatus.READY,
        video_path=video,
    )
    try:
        with TestClient(main.app) as client:
            response = client.get(
                f"/api/previews/{preview_id}/video",
                headers={"Range": "bytes=0-100"},
            )
            assert response.status_code == 206
            assert response.headers["content-range"] == "bytes 0-100/1024"
            assert response.headers["accept-ranges"] == "bytes"
            assert response.content == bytes(range(101))
            head = client.head(
                f"/api/previews/{preview_id}/video",
                headers={"Range": "bytes=0-100"},
            )
            assert head.status_code == 206
            assert head.headers["content-range"] == "bytes 0-100/1024"
            unsatisfiable = client.get(
                f"/api/previews/{preview_id}/video",
                headers={"Range": "bytes=2048-"},
            )
            assert unsatisfiable.status_code == 416
            malformed = client.get(
                f"/api/previews/{preview_id}/video",
                headers={"Range": "not-a-range"},
            )
            assert malformed.status_code == 400
            full = client.get(f"/api/previews/{preview_id}/video")
            assert full.status_code == 200
            assert full.content == video.read_bytes()
    finally:
        manager.shutdown()
