from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlatformInfo:
    name: str
    display_name: str
    url_patterns: list[str]
    cookie_help: str


class PlatformAdapter(ABC):
    name: str
    display_name: str

    @abstractmethod
    def match(self, raw_input: str) -> bool:
        """Return whether this adapter accepts the supplied input."""

    @abstractmethod
    def normalize(self, raw_input: str) -> str:
        """Return a canonical URL for the downloader."""

    @abstractmethod
    def extract_video_id(self, normalized_url: str) -> str | None:
        """Extract the platform-specific identifier."""

    def get_ytdlp_options(self, user_options: dict[str, Any]) -> dict[str, Any]:
        return {}

    def get_default_format(self) -> str:
        return "bv*[height<=480]+ba/b[height<=480]"

    def validate(self, raw_input: str) -> tuple[bool, str]:
        return True, ""

    def get_cookie_help(self) -> str:
        return ""

    def format_download_error(self, error: Exception) -> str:
        detail = str(error).lower()
        if any(term in detail for term in ("login", "log in", "cookie", "member")):
            return "该视频可能需要登录，请通过页面上传此平台支持的 cookies.txt。"
        if any(term in detail for term in ("timed out", "timeout", "connection", "network")):
            return "连接视频平台失败，请检查网络后重试。"
        if any(term in detail for term in ("404", "not found")):
            return "找不到该视频，请检查链接或视频是否已删除。"
        return "视频下载失败，请确认链接有效、网络正常，或稍后重试。"

    def info(self) -> PlatformInfo:
        return PlatformInfo(
            name=self.name,
            display_name=self.display_name,
            url_patterns=[],
            cookie_help=self.get_cookie_help(),
        )
