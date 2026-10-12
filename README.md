# ClipGIF

ClipGIF 是本地网页视频剪辑器。浏览器负责预览和编辑，本机 Python 服务负责下载、剪辑和 GIF 转码；视频不会上传到 ClipGIF 服务器。

> 请仅处理你有权使用的内容，并遵守 B 站及其他视频平台的服务条款、版权和当地法律。

## 当前支持情况

- **视频平台：**支持 B 站 BV 号、`bilibili.com` 链接和 `b23.tv` 短链。欢迎贡献 YouTube、Vimeo、X/Twitter 等平台。
- **操作系统：**Windows 10/11 完整支持；macOS 和 Linux 仅提供实验性占位脚本；暂不支持 Docker。
- **GIF：**支持裁切、自定义尺寸、倍速和画质设置；尚无 filmstrip 时间轴缩略图。
- **界面：**适配窄屏，并支持系统“减少动态效果”设置。

欢迎贡献其他 yt-dlp 支持平台。参见[新增视频平台指南](docs/adding-a-platform.md)和[操作系统支持矩阵](docs/platform-support.md)。

## Windows 10/11 安装与启动

1. 下载或解压项目。
2. 双击 `start.bat`（或 `scripts\start_windows.bat`）。脚本检查 Python 3.11+、`ffmpeg` 和 `ffprobe`；如缺少，会分别询问是否用 `winget` 安装 Python 3.13（`Python.Python.3.13`）或 FFmpeg（`Gyan.FFmpeg.Shared`）。
3. 首次启动会创建 `.venv` 并安装 Python 依赖，然后打开 <http://127.0.0.1:8000>。关闭最小化的“ClipGIF server”窗口即可停止服务。

只有在你确认后脚本才会安装。若没有 `winget`、你拒绝安装或安装失败，启动会停止并提示手动处理：安装 [Python 3.11+](https://www.python.org/downloads/windows/)，确保 `py` 或 `python` 命令可用；再下载 [FFmpeg Windows 版](https://ffmpeg.org/download.html)，并将同时包含 `ffmpeg.exe` 和 `ffprobe.exe` 的 `bin` 文件夹加入 PATH。也可用以下命令安装 FFmpeg：

```powershell
winget install --id Gyan.FFmpeg.Shared -e
```

安装后若工具仍无法识别，请重新运行 `start.bat` 或打开新终端再试。若已有 `.venv` 使用旧版 Python，先手动重命名或删除它，再重新启动。

启动需要网络来安装依赖或下载公开视频。Python 包安装在项目 `.venv` 中；FFmpeg 是系统工具，不由 pip 安装。修改端口时，启动前设置 `CLIPGIF_PORT`。

## macOS（实验性）

macOS 启动脚本尚未实现。贡献者需先安装 Python 3.11+ 和 FFmpeg（例如 `brew install ffmpeg`），再运行：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main
```

浏览器打开 <http://127.0.0.1:8000>；可用 `CLIPGIF_PORT` 更改端口。

## Linux（实验性）

Linux 启动脚本尚未实现。贡献者需先安装 Python 3.11+ 和 FFmpeg（Debian/Ubuntu：`sudo apt install ffmpeg`；Fedora：`sudo dnf install ffmpeg`），再按 macOS 的步骤创建环境、安装依赖并运行应用。

## 使用方法

1. 粘贴 B 站 BV 号、链接或 `b23.tv` 短链，点击“加载视频”。
2. 等待预览出现，拖动时间轴滑块设定选段（大于 0 秒且不超过 60 秒）。时间显示精确到 0.1 秒；键盘左右键可微调聚焦的滑块。使用“预览选区”和“跳到起点/终点”检查、微调片段。
3. 可选：点击“启用裁切”，拖动裁切框或四角调整画幅；“重置画幅”恢复全画面。关闭裁切则导出完整画面。
4. 设置 GIF 宽、高、速度、FPS、颜色数和抖动方式：
   - 宽度：320、480、640 px 或自定义；高度留空则按比例计算。宽高比不同时等比缩放并补黑边，不会拉伸。
   - 速度：0.5×、1×、1.5×、2×。只改变 GIF 播放时长，不改变视频选段。
   - FPS：5、10、15、20；颜色数：64、128、256；抖动：Bayer 或 Sierra 2-4A。
   - 默认：不裁切、宽度最多 480 px（不放大小画面）、12 FPS、1×、128 色、Sierra 2-4A。
5. 点击“生成 GIF”预览结果，再点击“下载 GIF”保存。

自定义宽高范围为 64–1280 px。裁切只改变画幅，不会修复图像内容。GIF 上限为 50 MB；超限时缩短片段或降低宽度、FPS、颜色数。

预览视频为带 fast-start 元数据的 H.264/AAC MP4，播放器支持 HTTP Range seek。

## 界面与动效

界面采用暖纸白、深墨色和苔橄榄绿；标题使用本机衬线字体回退，控件使用无衬线字体。页面按“来源 → 选段 → 导出 → 结果”排列，窄屏为单列；不依赖远程字体或前端动效库。

页面入场和 GIF 结果轻柔淡入，按钮仅有轻微悬停反馈；裁切和时间轴拖动保持即时。启用系统“减少动态效果”（`prefers-reduced-motion: reduce`）后，会关闭入场、结果、按钮位移和平滑滚动动画。

## 导出 cookies.txt

仅登录视频需要 cookie。用可信的浏览器扩展导出当前会话的 Netscape 格式 `cookies.txt`（文本文件），加载视频时选择它。Cookie 等同于登录凭据：不要分享或提交到仓库。ClipGIF 不会自动读取项目中的 cookie 文件，也不记录 cookie 内容；上传文件只暂存供 yt-dlp 使用，下载结束后删除。

## 常见问题

- **找不到 Python 或 FFmpeg：**重跑 `start.bat` 或开新终端。也可检查 `py -3 --version`（或 `python --version`）、`ffmpeg -version` 和 `ffprobe -version`；仍不可用时按上文手动安装。
- **下载失败：**检查链接和网络；也可更新 yt-dlp：`.venv\Scripts\python.exe -m pip install --upgrade yt-dlp`。
- **视频需要登录：**按[导出 cookies.txt](#导出-cookiestxt)操作，不要分享 cookie。
- **GIF 过大：**上限 50 MB；缩短片段或降低宽度、FPS、颜色数。
- **预览无法拖动：**后端支持 HTTP Range，重新加载预览。可运行以下命令验证，预期返回 `206`：
  ```powershell
  curl.exe -H "Range: bytes=0-100" http://127.0.0.1:8000/api/previews/{preview_id}/video -I
  ```
  将 `{preview_id}` 换成页面中的任务 ID。
- **平台不支持：**目前仅完整支持 B 站；YouTube、Vimeo、X/Twitter 和本地文件尚未实现。
- **Windows 端口占用：**换一个 `CLIPGIF_PORT` 后重启。

源视频、预览和 GIF 分别保存在 `work/`、`previews/` 和 `outputs/`；不会自动清理。释放空间前先停止服务，再删除这些目录中的文件。

## 开发与测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
node --test tests\test_timeline.js tests\test_crop.js
```

时间轴测试需 Node.js 20+，运行 ClipGIF 不需要 Node.js。

调整界面后，请检查桌面和窄屏布局、裁切拖动及“减少动态效果”设置。

平台扩展方式见[新增视频平台指南](docs/adding-a-platform.md)；操作系统贡献方式见[支持矩阵](docs/platform-support.md)。
