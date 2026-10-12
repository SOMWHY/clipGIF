import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT_DIR / "work"
PREVIEWS_DIR = ROOT_DIR / "previews"
OUTPUTS_DIR = ROOT_DIR / "outputs"
LOGS_DIR = ROOT_DIR / "logs"
PORT = int(os.environ.get("CLIPGIF_PORT", "8000"))
MAX_VIDEO_BYTES = 200 * 1024 * 1024
MAX_PREVIEW_BYTES = 100 * 1024 * 1024
MAX_GIF_BYTES = 50 * 1024 * 1024
MAX_COOKIE_BYTES = 2 * 1024 * 1024
MAX_CONCURRENT_JOBS = 2
MAX_CLIP_SECONDS = 60.0


def ensure_directories() -> None:
    for directory in (WORK_DIR, PREVIEWS_DIR, OUTPUTS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
