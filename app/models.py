from enum import StrEnum
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import MAX_CLIP_SECONDS


class PreviewStatus(StrEnum):
    PENDING = "pending"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    PREVIEWING = "previewing"
    READY = "ready"
    FAILED = "failed"


class TaskStatus(StrEnum):
    PENDING = "pending"
    CLIPPING = "clipping"
    TRANSCODING = "transcoding"
    SUCCESS = "success"
    FAILED = "failed"


PositiveTime = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class CropRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    y: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    width: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    height: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def validate_inside_frame(self) -> "CropRegion":
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("裁切框必须位于画面范围内")
        return self


class GifRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: PositiveTime
    end: PositiveTime
    crop: CropRegion | None = None
    width: Annotated[int, Field(strict=True, ge=64, le=1280)] | None = None
    height: Annotated[int, Field(strict=True, ge=64, le=1280)] | None = None
    fps: Annotated[int, Field(strict=True)] = 12
    speed: Literal[0.5, 1.0, 1.5, 2.0] = 1.0
    max_colors: Literal[64, 128, 256] = 128
    dither: Literal["bayer", "sierra2_4a"] = "sierra2_4a"

    @field_validator("fps")
    @classmethod
    def validate_fps(cls, value: int) -> int:
        if value not in {5, 10, 12, 15, 20}:
            raise ValueError("FPS 必须为 5、10、12、15 或 20。")
        return value

    @field_validator("start", "end")
    @classmethod
    def time_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("时间必须是有限数字")
        return round(value, 3)

    @model_validator(mode="after")
    def validate_range(self) -> "GifRequest":
        if self.end <= self.start:
            raise ValueError("结束时间必须大于开始时间")
        if self.end - self.start > MAX_CLIP_SECONDS:
            raise ValueError(f"片段不能超过 {MAX_CLIP_SECONDS:g} 秒")
        return self


class PreviewResponse(BaseModel):
    preview_id: str
    platform: str
    status: str
    title: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    video_url: str | None = None
    error: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    preview_id: str
    platform: str
    status: str
    gif_url: str | None = None
    download_url: str | None = None
    error: str | None = None
