from enum import StrEnum
import math
from typing import Annotated

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


class GifRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: PositiveTime
    end: PositiveTime

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
