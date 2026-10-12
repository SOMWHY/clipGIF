from contextlib import asynccontextmanager
from dataclasses import asdict
import logging
from pathlib import Path
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import (
    LOGS_DIR,
    MAX_COOKIE_BYTES,
    PORT,
    PORT,
    PREVIEWS_DIR,
    ensure_directories,
)
from app.models import GifRequest, PreviewResponse, PreviewStatus, TaskResponse, TaskStatus
from app.platforms.registry import detect_platform, list_platforms
from app.services.jobs import GifJob, JobManager, PreviewJob
from app.services.deps import check_ffmpeg, check_python_version, check_ytdlp


ensure_directories()
_log_format = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_log_file = (LOGS_DIR / "app.log").resolve()
if not any(
    isinstance(handler, logging.FileHandler)
    and Path(handler.baseFilename).resolve() == _log_file
    for handler in _root_logger.handlers
):
    file_handler = logging.FileHandler(_log_file, encoding="utf-8")
    file_handler.setFormatter(_log_format)
    _root_logger.addHandler(file_handler)
if not any(
    isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
    for handler in _root_logger.handlers
):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(_log_format)
    _root_logger.addHandler(console_handler)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(application: FastAPI):
    yield
    application.state.jobs.shutdown()


app = FastAPI(title="ClipGIF", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.state.jobs = JobManager()


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path.endswith("/gif"):
        errors = exc.errors()
        is_time_error = any(
            not error["loc"] or error["loc"][-1] in {"start", "end"}
            for error in errors
        )
        if is_time_error:
            detail = "时间段无效：开始时间不能小于 0，结束时间必须大于开始时间，且片段不能超过 60 秒。"
        else:
            detail = "GIF 导出参数无效，请检查裁切区域、尺寸、速度和画质选项。"
    else:
        detail = "请求参数无效，请检查输入内容和文件格式。"
    return JSONResponse(status_code=422, content={"detail": detail})


@app.middleware("http")
async def log_request(request: Request, call_next):
    response = await call_next(request)
    logger.info("%s %s %s", request.method, request.url.path, response.status_code)
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "python": check_python_version()[0],
        "ffmpeg": check_ffmpeg()[0],
        "yt_dlp": check_ytdlp()[0],
    }


@app.get("/api/platforms")
def platforms():
    return {"platforms": [asdict(info) for info in list_platforms()]}


@app.post("/api/previews", response_model=PreviewResponse)
async def create_preview(url: str = Form(...), cookies: UploadFile | None = File(default=None)):
    raw_input = url.strip()
    adapter = detect_platform(raw_input)
    if adapter is None:
        supported = "、".join(info.display_name for info in list_platforms()) or "无"
        raise HTTPException(
            status_code=400,
            detail=f"暂不支持该平台或输入无效，当前支持：{supported}。请检查视频链接或 BV 号。",
        )
    valid, message = adapter.validate(raw_input)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    cookie_bytes = None
    if cookies is not None and cookies.filename:
        if not cookies.filename.lower().endswith(".txt"):
            raise HTTPException(status_code=400, detail="Cookie 文件必须使用 .txt 格式。")
        cookie_bytes = await cookies.read(MAX_COOKIE_BYTES + 1)
        await cookies.close()
        if len(cookie_bytes) > MAX_COOKIE_BYTES:
            raise HTTPException(status_code=413, detail="cookies.txt 文件不能超过 2 MB。")
    preview_id = uuid.uuid4().hex
    job = PreviewJob(preview_id=preview_id, platform=adapter.name, adapter=adapter)
    app.state.jobs.add_preview(job, raw_input, cookie_bytes)
    return PreviewResponse(preview_id=preview_id, platform=adapter.name, status=job.status)


@app.get("/api/previews/{preview_id}", response_model=PreviewResponse)
def get_preview(preview_id: str):
    job = app.state.jobs.previews.get(preview_id)
    if job is None:
        raise HTTPException(status_code=404, detail="找不到该预览任务。")
    return PreviewResponse(
        preview_id=job.preview_id,
        platform=job.platform,
        status=job.status,
        title=job.title,
        duration=job.duration,
        width=job.width,
        height=job.height,
        video_url=f"/api/previews/{preview_id}/video" if job.status == PreviewStatus.READY else None,
        error=job.error,
    )


@app.api_route("/api/previews/{preview_id}/video", methods=["GET", "HEAD"])
def get_preview_video(preview_id: str):
    job = app.state.jobs.previews.get(preview_id)
    if job is None or job.status != PreviewStatus.READY or job.video_path is None:
        raise HTTPException(status_code=404, detail="预览视频尚未准备好。")
    expected_path = PREVIEWS_DIR / f"{preview_id}.mp4"
    if job.video_path.resolve() != expected_path.resolve() or not expected_path.is_file():
        logger.warning("Preview file mapping failed for ID %s.", preview_id)
        raise HTTPException(status_code=404, detail="预览视频文件不存在，请重新加载。")
    return FileResponse(expected_path, media_type="video/mp4")


@app.post("/api/previews/{preview_id}/gif", response_model=TaskResponse)
def create_gif(preview_id: str, request: GifRequest):
    preview = app.state.jobs.previews.get(preview_id)
    if preview is None or preview.status != PreviewStatus.READY:
        raise HTTPException(status_code=404, detail="预览视频尚未准备好。")
    if preview.duration is None or request.end > preview.duration:
        raise HTTPException(status_code=422, detail="结束时间不能超过视频总时长。")
    task_id = uuid.uuid4().hex
    task = GifJob(task_id=task_id, preview_id=preview_id, platform=preview.platform)
    app.state.jobs.add_gif(task, preview, request)
    return TaskResponse(
        task_id=task_id, preview_id=preview_id, platform=preview.platform, status=task.status
    )


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    task = app.state.jobs.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到该 GIF 任务。")
    complete = task.status == TaskStatus.SUCCESS
    return TaskResponse(
        task_id=task.task_id,
        preview_id=task.preview_id,
        platform=task.platform,
        status=task.status,
        gif_url=f"/api/tasks/{task_id}/gif" if complete else None,
        download_url=f"/api/tasks/{task_id}/download" if complete else None,
        error=task.error,
    )


def _get_task_file(task_id: str, download: bool):
    task = app.state.jobs.tasks.get(task_id)
    if task is None or task.status != TaskStatus.SUCCESS or task.gif_path is None:
        raise HTTPException(status_code=404, detail="GIF 文件尚未准备好。")
    expected_path = Path(task.gif_path)
    if expected_path.name != f"{task_id}.gif" or not expected_path.is_file():
        raise HTTPException(status_code=404, detail="GIF 文件不存在，请重新生成。")
    filename = f"clipgif-{task.platform}-{task_id}.gif" if download else None
    return FileResponse(
        expected_path,
        media_type="image/gif",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


@app.get("/api/tasks/{task_id}/gif")
def get_task_gif(task_id: str):
    return _get_task_file(task_id, download=False)


@app.get("/api/tasks/{task_id}/download")
def download_task_gif(task_id: str):
    return _get_task_file(task_id, download=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)
