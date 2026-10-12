import re
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.platforms.base import PlatformAdapter, PlatformInfo


_BV_PATTERN = re.compile(r"(?i)(?<![0-9a-z])BV[0-9a-z]{10}(?![0-9a-z])")
_ALLOWED_HOSTS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv", "www.b23.tv"}
_SHORT_HOSTS = {"b23.tv", "www.b23.tv"}
_BILIBILI_URL = re.compile(r"^https://www\.bilibili\.com/video/(BV[0-9A-Za-z]{10})(?:/|$)", re.I)


class _SafeRedirectHandler(HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, request, fp, code, message, headers, new_url):
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in _ALLOWED_HOSTS:
            raise URLError("短链跳转目标不是允许的 B 站地址")
        return super().redirect_request(request, fp, code, message, headers, new_url)


class BilibiliAdapter(PlatformAdapter):
    name = "bilibili"
    display_name = "B站"

    def match(self, raw_input: str) -> bool:
        value = raw_input.strip()
        if _BV_PATTERN.fullmatch(value):
            return True
        valid, _ = self.validate(value)
        if not valid:
            return False
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = (parsed.hostname or "").lower()
        return host in _ALLOWED_HOSTS and (
            bool(_BV_PATTERN.search(parsed.path)) or host in _SHORT_HOSTS
        )

    def validate(self, raw_input: str) -> tuple[bool, str]:
        value = raw_input.strip()
        if _BV_PATTERN.fullmatch(value):
            return True, ""
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = (parsed.hostname or "").lower()
        try:
            port = parsed.port
        except ValueError:
            return False, "请输入有效的 B 站 BV 号、视频链接或 b23.tv 短链。"
        if (
            parsed.scheme not in {"http", "https"}
            or host not in _ALLOWED_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 80, 443}
        ):
            return False, "请输入有效的 B 站 BV 号、视频链接或 b23.tv 短链。"
        if not (_BV_PATTERN.search(parsed.path) or host in _SHORT_HOSTS):
            return False, "B 站链接中没有有效的视频 BV 号。"
        return True, ""

    def normalize(self, raw_input: str) -> str:
        is_valid, message = self.validate(raw_input)
        if not is_valid:
            raise ValueError(message)
        value = raw_input.strip()
        match = _BV_PATTERN.fullmatch(value)
        if match:
            return f"https://www.bilibili.com/video/{match.group(0)}"

        parsed = urlparse(value if "://" in value else f"https://{value}")
        if (parsed.hostname or "").lower() in _SHORT_HOSTS:
            value = self._resolve_short_url(
                f"https://{parsed.hostname}{parsed.path}"
                + (f"?{parsed.query}" if parsed.query else "")
            )
            parsed = urlparse(value)
        video_match = _BV_PATTERN.search(parsed.path)
        if not video_match or (parsed.hostname or "").lower() not in _ALLOWED_HOSTS:
            raise ValueError("短链未解析为有效的 B 站视频地址。")
        return f"https://www.bilibili.com/video/{video_match.group(0)}"

    def _resolve_short_url(self, url: str) -> str:
        opener = build_opener(_SafeRedirectHandler())
        request = Request(url, headers={"User-Agent": "ClipGIF/1.0"})
        try:
            with opener.open(request, timeout=10) as response:
                final_url = response.geturl()
        except (OSError, URLError, TimeoutError) as exc:
            raise ValueError("无法解析 b23.tv 短链，请检查网络后重试。") from exc
        final = urlparse(final_url)
        if final.scheme != "https" or (final.hostname or "").lower() not in _ALLOWED_HOSTS:
            raise ValueError("短链跳转目标不是允许的 B 站地址。")
        return final_url

    def extract_video_id(self, normalized_url: str) -> str | None:
        match = _BV_PATTERN.search(urlparse(normalized_url).path)
        return match.group(0) if match else None

    def get_default_format(self) -> str:
        return "bv*[height<=480]+ba/b[height<=480]/bv*+ba/b"

    def get_cookie_help(self) -> str:
        return (
            "如视频需要登录，请使用浏览器扩展导出 Netscape 格式 cookies.txt，"
            "仅在本页面加载视频时上传。文件只用于本次下载，结束后会删除。"
        )

    def format_download_error(self, error: Exception) -> str:
        detail = str(error).lower()
        if any(term in detail for term in ("login", "log in", "cookie", "会员", "登录")):
            return "B站视频需要登录，请导出并上传 Netscape 格式的 cookies.txt。"
        if any(term in detail for term in ("412", "403", "429", "forbidden", "too many requests")):
            return "B站暂时拒绝了下载请求，可能是限流或需要登录；请稍后重试或上传 cookies.txt。"
        if "no video formats found" in detail or "requested format is not available" in detail:
            return "B站当前未提供可下载的视频格式，可能需要登录或该视频暂不可用。"
        if any(term in detail for term in ("timed out", "timeout", "connection", "network")):
            return "连接 B 站失败，请检查网络后重试。"
        if any(term in detail for term in ("404", "not found", "不存在")):
            return "找不到该 B 站视频，请检查 BV 号或视频是否已删除。"
        return "B站视频下载失败，请确认链接有效、网络正常，或稍后重试。"

    def info(self) -> PlatformInfo:
        return PlatformInfo(
            name=self.name,
            display_name=self.display_name,
            url_patterns=["BV 号", "bilibili.com/video/BV…", "b23.tv 短链"],
            cookie_help=self.get_cookie_help(),
        )


ADAPTER = BilibiliAdapter()
