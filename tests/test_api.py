import time
from fastapi.testclient import TestClient
import pytest

from app import main
from app.models import PreviewStatus
from app.platforms.registry import detect_platform
from app.services import jobs
from app.services.jobs import JobManager, PreviewJob


@pytest.fixture
def client(monkeypatch, tmp_path):
    manager = JobManager()
    monkeypatch.setattr(main.app.state, "jobs", manager)
    monkeypatch.setattr(jobs, "PREVIEWS_DIR", tmp_path / "previews")
    monkeypatch.setattr(jobs, "OUTPUTS_DIR", tmp_path / "outputs")
    with TestClient(main.app) as test_client:
        yield test_client
    manager.shutdown()


def _wait_for_status(client, path, expected):
    for _ in range(100):
        response = client.get(path)
        if response.status_code == 200 and response.json()["status"] in expected:
            return response.json()
        time.sleep(0.01)
    raise AssertionError(f"Job did not reach expected status: {expected}")


def test_health_and_platform_list(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/platforms").json()["platforms"][0]["name"] == "bilibili"


def test_unknown_platform_is_a_chinese_client_error(client):
    response = client.post("/api/previews", data={"url": "https://example.com/clip"})
    assert response.status_code == 400
    assert "暂不支持" in response.json()["detail"]
    assert "B站" in response.json()["detail"]


def test_preview_job_success_includes_platform(monkeypatch, client, tmp_path):
    def fake_download(adapter, raw_input, preview_id, cookies):
        assert adapter.name == "bilibili"
        assert raw_input == "https://www.bilibili.com/video/BV1xx411c7mD"
        assert cookies is None
        source = tmp_path / f"{preview_id}-source.mp4"
        source.write_bytes(b"source")
        return source, "测试视频"

    def fake_preview(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"preview")
        return {"duration": 10.5, "width": 640, "height": 360}

    monkeypatch.setattr(jobs, "download_video", fake_download)
    monkeypatch.setattr(jobs, "make_preview", fake_preview)
    created = client.post("/api/previews", data={"url": "BV1xx411c7mD"}).json()
    result = _wait_for_status(client, f"/api/previews/{created['preview_id']}", {"ready", "failed"})
    assert result["status"] == "ready"
    assert result["platform"] == "bilibili"
    assert result["duration"] == 10.5
    assert result["video_url"].endswith("/video")


def test_gif_job_success_and_download(monkeypatch, client, tmp_path):
    manager = main.app.state.jobs
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    adapter = detect_platform("BV1xx411c7mD")
    preview_id = "a" * 32
    manager.previews[preview_id] = PreviewJob(
        preview_id=preview_id,
        platform="bilibili",
        adapter=adapter,
        status=PreviewStatus.READY,
        source_path=source,
        duration=20,
        width=640,
        height=360,
    )

    def fake_make_gif(_source, target, _request, _frame_width, _frame_height, on_stage):
        on_stage("clipping")
        on_stage("transcoding")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"gif")
        return target

    monkeypatch.setattr(jobs, "make_gif", fake_make_gif)
    response = client.post(
        f"/api/previews/{preview_id}/gif",
        json={"start": 12.5, "end": 15.5},
    )
    assert response.status_code == 200
    task = response.json()
    result = _wait_for_status(client, f"/api/tasks/{task['task_id']}", {"success", "failed"})
    assert result["status"] == "success"
    assert result["platform"] == "bilibili"
    assert client.get(result["gif_url"]).content == b"gif"
    download = client.get(result["download_url"])
    assert download.content == b"gif"
    assert f"clipgif-bilibili-{task['task_id']}.gif" in download.headers["content-disposition"]


def test_gif_job_fails_when_preview_dimensions_are_missing(monkeypatch, client, tmp_path):
    manager = main.app.state.jobs
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    preview_id = "c" * 32
    manager.previews[preview_id] = PreviewJob(
        preview_id=preview_id,
        platform="bilibili",
        adapter=detect_platform("BV1xx411c7mD"),
        status=PreviewStatus.READY,
        source_path=source,
        duration=20,
    )
    called = False

    def fake_make_gif(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(jobs, "make_gif", fake_make_gif)
    task = client.post(
        f"/api/previews/{preview_id}/gif",
        json={"start": 0, "end": 3},
    ).json()
    result = _wait_for_status(client, f"/api/tasks/{task['task_id']}", {"success", "failed"})
    assert result["status"] == "failed"
    assert "尺寸" in result["error"]
    assert called is False


def test_advanced_gif_options_are_forwarded_to_gif_job(monkeypatch, client, tmp_path):
    manager = main.app.state.jobs
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    preview_id = "d" * 32
    manager.previews[preview_id] = PreviewJob(
        preview_id=preview_id,
        platform="bilibili",
        adapter=detect_platform("BV1xx411c7mD"),
        status=PreviewStatus.READY,
        source_path=source,
        duration=20,
        width=640,
        height=360,
    )
    received = []

    def fake_make_gif(_source, target, request, _frame_width, _frame_height, _on_stage):
        received.append(request)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"gif")
        return target

    monkeypatch.setattr(jobs, "make_gif", fake_make_gif)
    response = client.post(
        f"/api/previews/{preview_id}/gif",
        json={
            "start": 0,
            "end": 3,
            "crop": {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
            "width": 640,
            "height": 480,
            "fps": 20,
            "speed": 2,
            "max_colors": 256,
            "dither": "bayer",
        },
    )
    assert response.status_code == 200
    task = response.json()
    result = _wait_for_status(
        client, f"/api/tasks/{task['task_id']}", {"success", "failed"}
    )
    assert result["status"] == "success"
    request = received[0]
    assert request.crop.x == 0.25
    assert request.crop.y == 0.25
    assert request.crop.width == 0.5
    assert request.crop.height == 0.5
    assert request.width == 640
    assert request.height == 480
    assert request.fps == 20
    assert request.speed == 2
    assert request.max_colors == 256
    assert request.dither == "bayer"


def test_gif_request_outside_source_duration_is_rejected(client, tmp_path):
    manager = main.app.state.jobs
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    preview_id = "b" * 32
    manager.previews[preview_id] = PreviewJob(
        preview_id=preview_id,
        platform="bilibili",
        adapter=detect_platform("BV1xx411c7mD"),
        status=PreviewStatus.READY,
        source_path=source,
        duration=3,
    )
    response = client.post(f"/api/previews/{preview_id}/gif", json={"start": 0, "end": 4})
    assert response.status_code == 422
    assert "总时长" in response.json()["detail"]


def test_invalid_gif_parameters_return_chinese_error(client):
    response = client.post(
        "/api/previews/unknown/gif",
        json={"start": -1, "end": 1},
    )
    assert response.status_code == 422
    assert "时间段无效" in response.json()["detail"]


@pytest.mark.parametrize(
    "options",
    [
        {"fps": 8},
        {"width": True},
        {"crop": {"x": 0.8, "y": 0, "width": 0.3, "height": 0.5}},
    ],
)
def test_invalid_advanced_gif_options_return_chinese_error(client, options):
    response = client.post(
        "/api/previews/unknown/gif",
        json={"start": 0, "end": 3, **options},
    )
    assert response.status_code == 422
    assert "参数无效" in response.json()["detail"]
