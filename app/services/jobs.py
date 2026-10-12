from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import logging
from pathlib import Path
import threading

from app.config import MAX_CONCURRENT_JOBS, OUTPUTS_DIR, PREVIEWS_DIR
from app.models import GifRequest, PreviewStatus, TaskStatus
from app.platforms.base import PlatformAdapter
from app.services.downloader import download_video
from app.services.errors import ClipGifError
from app.services.gif_maker import make_gif
from app.services.previewer import make_preview


logger = logging.getLogger(__name__)


@dataclass
class PreviewJob:
    preview_id: str
    platform: str
    adapter: PlatformAdapter
    status: str = PreviewStatus.PENDING
    title: str | None = None
    source_path: Path | None = None
    video_path: Path | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    error: str | None = None


@dataclass
class GifJob:
    task_id: str
    preview_id: str
    platform: str
    status: str = TaskStatus.PENDING
    gif_path: Path | None = None
    error: str | None = None


class JobManager:
    def __init__(self) -> None:
        self.previews: dict[str, PreviewJob] = {}
        self.tasks: dict[str, GifJob] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS, thread_name_prefix="clipgif")

    def add_preview(self, job: PreviewJob, raw_input: str, cookies: bytes | None) -> None:
        with self._lock:
            self.previews[job.preview_id] = job
        self._executor.submit(self._run_preview, job, raw_input, cookies)

    def add_gif(self, job: GifJob, preview: PreviewJob, request: GifRequest) -> None:
        with self._lock:
            self.tasks[job.task_id] = job
        self._executor.submit(self._run_gif, job, preview, request)

    def _run_preview(self, job: PreviewJob, raw_input: str, cookies: bytes | None) -> None:
        try:
            job.status = PreviewStatus.RESOLVING
            normalized = job.adapter.normalize(raw_input)
            job.status = PreviewStatus.DOWNLOADING
            source_path, title = download_video(job.adapter, normalized, job.preview_id, cookies)
            job.source_path = source_path
            job.title = title
            job.status = PreviewStatus.PREVIEWING
            video_path = PREVIEWS_DIR / f"{job.preview_id}.mp4"
            metadata = make_preview(source_path, video_path)
            job.video_path = video_path
            job.duration = float(metadata["duration"])
            job.width = int(metadata["width"])
            job.height = int(metadata["height"])
            job.status = PreviewStatus.READY
        except ClipGifError as exc:
            job.error = str(exc)
            job.status = PreviewStatus.FAILED
        except Exception:
            logger.exception("Unexpected preview job failure: %s", job.preview_id)
            job.error = "处理视频时发生错误，请检查日志后重试。"
            job.status = PreviewStatus.FAILED

    def _run_gif(self, job: GifJob, preview: PreviewJob, request: GifRequest) -> None:
        try:
            if preview.source_path is None:
                raise ClipGifError("找不到原始视频，请重新加载。")
            output_path = OUTPUTS_DIR / f"{job.task_id}.gif"

            def set_stage(stage: str) -> None:
                job.status = TaskStatus.CLIPPING if stage == "clipping" else TaskStatus.TRANSCODING

            make_gif(preview.source_path, output_path, request.start, request.end, set_stage)
            job.gif_path = output_path
            job.status = TaskStatus.SUCCESS
        except ClipGifError as exc:
            job.error = str(exc)
            job.status = TaskStatus.FAILED
        except Exception:
            logger.exception("Unexpected GIF job failure: %s", job.task_id)
            job.error = "生成 GIF 时发生错误，请检查日志后重试。"
            job.status = TaskStatus.FAILED

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
