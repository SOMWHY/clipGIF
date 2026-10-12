# 新增视频平台适配器

当前应用完整支持 B 站。未来平台集成应添加适配器，不要在下载器、预览器或 GIF 服务中添加平台专属 `if` 分支。

## 适配器接口

1. 在 `app/platforms/` 中新增 `xxx.py`。
2. 继承 `app.platforms.base.PlatformAdapter`，并导出模块级 `ADAPTER` 实例。注册表会发现 `app/platforms/` 下含有 `ADAPTER` 实例的 Python 模块。
3. 实现：
   - `match(raw_input: str) -> bool`：只接受你负责的平台域名或 ID 格式。
   - `validate(raw_input: str) -> tuple[bool, str]`：用中文说明无法安全处理的输入。
   - `normalize(raw_input: str) -> str`：转换为 yt-dlp 可处理的规范 URL；短链解析必须限制协议、目标主机、重定向次数和超时。
   - `extract_video_id(normalized_url: str) -> str | None`：提取平台视频 ID。
4. 根据需要覆盖 `get_ytdlp_options(user_options)`、`get_default_format()`、`get_watermark_presets()`、`get_cookie_help()` 和 `format_download_error(error)`。平台特有登录、限流和缺失视频提示应留在适配器中。不得把用户输入拼接进 shell 命令，也不得在代码中硬编码凭据。
5. 返回准确的 `PlatformInfo`：平台名、中文显示名、URL 提示和 Cookie 获取说明。

## 测试与文档

- 在 `tests/test_xxx_adapter.py` 中验证有效 ID、完整链接、短链、无效域名、跳转异常和 cookie 提示。
- 在 `tests/test_platform_registry.py` 中通过 FakeAdapter 验证注册、检测和共用流水线调用不要求修改核心代码。
- 运行 `python -m pytest tests/test_xxx_adapter.py tests/test_platform_registry.py -q`。
- 更新 README 的“当前支持情况”只有在平台实际可用并通过端到端验证后才列入完整支持清单。
- 如果平台需要登录，Cookie 只允许作为用户主动上传的文件用于本次下载；不得自动读取根目录凭证、日志记录或长期保留。
