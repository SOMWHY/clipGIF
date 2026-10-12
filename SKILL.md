# ClipGIF 项目复用与维护指南

ClipGIF 是 FastAPI 本地网页应用。页面只连接到本机 `127.0.0.1` 服务；yt-dlp 下载源媒体，ffmpeg/ffprobe 生成可 seek 预览并从源视频转码 GIF。处理前请确保有权访问、下载和使用目标媒体，并遵守平台条款及版权要求。

## 一键启动

- **Windows 10/11（完整支持）**：安装 Python 3.11+ 和 ffmpeg/ffprobe，双击 `start.bat` 或 `scripts\start_windows.bat`。脚本建立 `.venv`、安装 requirements、检查系统依赖并打开 `http://127.0.0.1:8000`。关闭最小化的服务窗口停止服务。
- **macOS（实验性占位）**：先安装 Python 3.11+ 和 ffmpeg；当前脚本不启动服务。手动执行 `python3 -m venv .venv`、激活环境、`python -m pip install -r requirements.txt` 和 `python -m app.main`。
- **Linux（实验性占位）**：先安装 Python 3.11+、ffmpeg/ffprobe；当前脚本不启动服务。按 macOS 的虚拟环境步骤安装依赖并运行 `python -m app.main`。

端口可用 `CLIPGIF_PORT` 环境变量覆盖。`scripts/start_macos.sh` 和 `scripts/start_linux.sh` 目前故意报告尚未实现。

## API

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/` | ClipGIF 网页 |
| `GET` | `/health` | Python、ffmpeg/ffprobe、yt-dlp 就绪情况 |
| `GET` | `/api/platforms` | 当前适配平台及 cookie 帮助信息 |
| `POST` | `/api/previews` | multipart 表单创建视频预览，字段 `url`，可选 `cookies` 文件 |
| `GET` | `/api/previews/{preview_id}` | 查询预览任务状态与媒体元信息 |
| `GET`, `HEAD` | `/api/previews/{preview_id}/video` | 预览 MP4，支持 HTTP Range/206 |
| `POST` | `/api/previews/{preview_id}/gif` | JSON `{ "start": 0.0, "end": 3.0 }` 创建 GIF 作业 |
| `GET` | `/api/tasks/{task_id}` | 查询 GIF 作业状态 |
| `GET` | `/api/tasks/{task_id}/gif` | GIF 预览 |
| `GET` | `/api/tasks/{task_id}/download` | 下载 GIF |

作业状态保存在进程内存，服务重启后状态不保留。服务最多同时运行 2 个媒体作业；预览在 `previews/`、源文件在 `work/{preview_id}/`、GIF 在 `outputs/`。

## 常用命令

显示 yt-dlp 支持信息或下载单个公开视频（仅作手动排障；应用本身通过 Python API 调用 yt-dlp）：

```powershell
.\.venv\Scripts\python.exe -m yt_dlp --list-extractors
.\.venv\Scripts\python.exe -m yt_dlp -f "bv*[height<=480]+ba/b[height<=480]" -o "work\manual\source.%(ext)s" "https://www.bilibili.com/video/BV..."
```

检查视频信息和手动生成片段：

```powershell
ffprobe -v error -show_entries format=duration:stream=width,height -of json input.mp4
ffmpeg -ss 0 -t 3 -i input.mp4 -vf "fps=12,scale=w=min(480\,iw):h=-2:flags=lanczos,palettegen=max_colors=128" -frames:v 1 palette.png
ffmpeg -ss 0 -t 3 -i input.mp4 -i palette.png -filter_complex "[0:v]fps=12,scale=w=min(480\,iw):h=-2:flags=lanczos[v];[v][1:v]paletteuse=dither=sierra2_4a" -loop 0 output.gif
```

## 复用项目

1. 安装 Python 3.11+、requirements 和系统 ffmpeg/ffprobe。
2. 将 `app/services/` 中的下载、预览和 GIF 服务复用到自己的 FastAPI 服务；外部命令必须继续使用参数数组，不得拼接 shell 命令。
3. 设置独立的数据目录时，应通过 `app/config.py` 的 `Path` 配置完成，不要硬编码 Windows 路径。
4. 本 MVP 的 cookie 只接受网页上传且只为当前下载短暂落盘。不要持久化、记录或共享 Cookie。

## 故障排查

- `GET /health` 返回 `ffmpeg: false`：确认 PATH 同时包含 `ffmpeg` 和 `ffprobe`。
- 依赖安装失败：确认联网后重新运行 `.venv\Scripts\python.exe -m pip install -r requirements.txt`。
- 需要登录：用户在预览表单上传 Netscape 格式 Cookie；不要打印 Cookie 值。
- Range seek 失败：发起 `Range: bytes=0-100` 请求，预期 `206`、`Content-Range` 及 101 字节。
- 本地媒体暂不自动过期清理；用户停止服务后可删除 `work/`、`previews/`、`outputs/` 中的文件释放空间。
- GIF 生成失败：查看控制台及 `logs/app.log` 的非敏感错误信息，确认源视频可被 ffprobe 读取且选区不超过 60 秒。
- 默认限制：源视频 200 MB、预览 100 MB、GIF 50 MB、Cookie 文件 2 MB；GIF 选区为 0–60 秒。

## 新增视频平台

在 `app/platforms/` 新增继承 `PlatformAdapter` 的模块，并导出 `ADAPTER` 实例。实现 `match`、`validate`、`normalize`、`extract_video_id`，需要时覆盖 yt-dlp 选项和 cookie 帮助。新增测试，检查未知/恶意链接拒绝、识别及 FakeAdapter 能经注册表进入共用流水线。详细步骤参见 `docs/adding-a-platform.md`。

## 新增操作系统支持

更新对应 `scripts/start_*.sh` 启动逻辑和 `app/services/deps.py` 安装提示，为该系统增加 CI job，验证路径使用 `pathlib.Path`，更新 `docs/platform-support.md` 矩阵与 README。当前 macOS/Linux 脚本是占位实现，Docker 尚未提供。
