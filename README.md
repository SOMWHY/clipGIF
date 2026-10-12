# ClipGIF

ClipGIF 是一个在你自己电脑上运行的本地网页应用：浏览器提供视频预览和时间轴，下载、剪辑与 GIF 转码都由本机上的 Python 服务完成。它不是命令行剪辑工具，也不会把视频上传到 ClipGIF 服务器。

> 请仅处理你有权使用的内容，并遵守 B 站及其他视频平台的服务条款、版权和当地法律。

## 当前支持情况

- 视频平台：完整支持 B 站 BV 号、`bilibili.com` 视频链接和 `b23.tv` 短链。
- 未来计划欢迎贡献 YouTube、Vimeo、X/Twitter 及更多 yt-dlp 支持平台。
- 操作系统：Windows 10/11 完整支持；macOS 和 Linux 脚本目前为实验性占位实现；Docker 尚未实现。
- GIF 导出支持画幅裁切、自定义尺寸、倍速和画质参数；可选的 filmstrip 时间轴缩略图尚未实现。
- 界面采用暖纸白、墨色与苔橄榄绿的编辑式画廊风格，适配窄屏，并支持系统“减少动态效果”偏好。

欢迎贡献其他 yt-dlp 支持平台。参见[新增视频平台指南](docs/adding-a-platform.md)和[操作系统支持矩阵](docs/platform-support.md)。

## Windows 10/11 安装与启动

1. 安装 **Python 3.11 或更高版本**，安装程序中勾选“Add Python to PATH”。
2. 安装 ffmpeg 与 ffprobe。推荐在终端运行：

   ```powershell
   winget install --id Gyan.FFmpeg.Shared -e
   ```

   如果没有 winget，请从 [ffmpeg.org/download.html](https://ffmpeg.org/download.html) 下载 Windows 构建，并将包含 `ffmpeg.exe` 和 `ffprobe.exe` 的 `bin` 文件夹加入 PATH。重新打开终端后运行 `ffmpeg -version` 和 `ffprobe -version` 验证。
3. 下载或解压本项目到一个普通文件夹。
4. 双击项目目录中的 `start.bat`，或双击 `scripts\start_windows.bat`。首次启动会建立 `.venv` 并安装 Python 依赖；启动脚本会检查 ffmpeg/ffprobe 并打开浏览器。
5. 页面地址为 <http://127.0.0.1:8000>。若修改端口，可在启动前设置 `CLIPGIF_PORT` 环境变量。
6. 关闭最小化的“ClipGIF server”窗口即可停止本地服务。

启动期间需要网络来安装 Python 依赖及下载公开视频。ffmpeg 是系统工具，不会由 pip 自动安装。

## macOS（实验性）

当前脚本是占位实现，不能一键启动。贡献者可先安装 Python 3.11+ 和 ffmpeg（例如 `brew install ffmpeg`），再在项目目录中创建虚拟环境并安装依赖：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main
```

浏览器打开 <http://127.0.0.1:8000>。可用 `CLIPGIF_PORT` 环境变量改端口。

## Linux（实验性）

当前脚本是占位实现，不能一键启动。贡献者需安装 Python 3.11+ 和 ffmpeg（Debian/Ubuntu 可运行 `sudo apt install ffmpeg`；Fedora 可运行 `sudo dnf install ffmpeg`），然后按照上面的虚拟环境命令安装依赖并运行 `python -m app.main`。浏览器地址仍为 <http://127.0.0.1:8000>。

## 使用方法

1. 在输入框粘贴 B 站 BV 号、完整链接或 `b23.tv` 短链，点击“加载视频”。
2. 如视频要求登录，可从浏览器导出 **Netscape 格式**的 `cookies.txt` 并在加载时上传。Cookie 只用于该次下载，服务不会自动读取项目根目录中的 cookie 文件，也不会记录 cookie 内容；下载成功或失败后会删除临时文件。
3. 等待预览视频出现。拖动时间轴的两个滑块设置起止时间；起止显示到 0.1 秒，按左右方向键可微调当前聚焦滑块。
4. 点击“预览选区”循环播放所选片段，使用“跳到起点/终点”进行微调。选区必须大于 0 秒且不超过 60 秒。
5. 如需调整画幅，点击“启用裁切”，拖动框内区域移动裁切框，拖动四角调整大小；点击“重置画幅”恢复完整画面。关闭裁切后导出完整画幅。
6. 在“GIF 导出设置”中按需设置宽、高、速度、FPS、颜色数和抖动方式：
   - 宽度可选 320、480、640 px 或自定义；高度留空时自动按比例计算。宽高比例不一致时会等比缩放并补黑边，不会拉伸。
   - 速度可选 0.5×、1×、1.5×、2×；速度越快，生成的 GIF 时长越短，源视频选段不变。
   - FPS 可选 5、10、15、20；颜色数可选 64、128、256；抖动可选 Bayer 或 Sierra 2-4A。
   - 默认行为与原版本一致：不裁切、宽度最多 480 px（较小画面不放大）、12 FPS、1×、128 色、Sierra 2-4A。
7. 点击“生成 GIF”，等待转码完成后预览，并点击“下载 GIF”保存文件。

裁切只改变 GIF 的画幅，不会修复裁切框内的图像内容。自定义宽高限制为 64–1280 px；GIF 大于 50 MB 时请缩短片段、降低宽度、帧率或颜色数。

浏览器视频播放器通过 HTTP Range 支持拖动 seek；预览视频由 ffmpeg 输出为 H.264/AAC MP4，并带有 fast-start 元数据。

## 界面与动效

ClipGIF 使用暖纸白背景、深墨色正文和克制的苔橄榄绿强调色。中文标题使用本机可用的衬线字体回退，表单、标签和操作控件使用无衬线字体；应用不依赖远程字体或前端动效库。页面按“来源 → 视频与选段 → 导出 → 结果”的顺序纵向排列，窄屏会收拢为单列。

首次打开时，标题和来源区域轻柔淡入；首次加载编辑器及每次生成 GIF 时会有短暂淡入，按钮仅有轻微悬停反馈。裁切框和时间轴拖动保持即时。若操作系统或浏览器启用了“减少动态效果”（`prefers-reduced-motion: reduce`），页面入场和结果动画、按钮位移动效及结果平滑滚动都会关闭。

## 导出 cookies.txt

只有视频需要登录时才需要 cookie。使用你信任的浏览器扩展导出当前浏览器会话的 Netscape 格式 `cookies.txt`，确认扩展生成的是文本格式，然后在 ClipGIF 加载视频时选择该文件。Cookie 等同于登录凭据：不要分享或提交到代码仓库。ClipGIF 将上传内容暂存到当前任务目录供 yt-dlp 使用，并在下载流程结束时清理。

## 常见问题

- **提示找不到 ffmpeg/ffprobe**：按上文安装，并确认 `ffmpeg -version` 和 `ffprobe -version` 可在新开的终端中运行，然后重新启动服务。
- **yt-dlp 下载失败**：确认链接有效、网络正常，并升级项目虚拟环境中的 yt-dlp：`.venv\Scripts\python.exe -m pip install --upgrade yt-dlp`。
- **提示需要登录**：上传从浏览器导出的 Netscape 格式 `cookies.txt`。不要将 cookie 内容发给他人。
- **GIF 太大**：输出限制为 50 MB；请缩短片段，或降低输出宽度、FPS、最大颜色数后重试。
- **预览不能拖动进度条**：使用最新版本的启动依赖，并重新加载预览；后端视频响应支持 HTTP Range（部分内容请求返回 206）。
- **检查 Range 响应**：将 `{preview_id}` 替换为页面任务 ID，运行 `curl.exe -H "Range: bytes=0-100" http://127.0.0.1:8000/api/previews/{preview_id}/video -I`，预期返回 `206`。
- **提示平台不支持**：当前仅完整支持 B 站；YouTube、Vimeo、X/Twitter 和本地文件尚未实现。
- **Windows 端口已被占用**：在启动前将 `CLIPGIF_PORT` 设置为其他可用端口。

源视频、预览和 GIF 文件保存在项目的 `work/`、`previews/`、`outputs/` 目录；目前没有自动过期清理。需要释放空间时，请先停止服务，再删除这些目录中的文件。

## 开发与测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
node --test tests\test_timeline.js tests\test_crop.js
```

时间轴单测需要 Node.js 20+；这不是运行 ClipGIF 网页应用的依赖。

界面样式或交互调整后，建议在桌面和窄屏检查来源表单、视频编辑器、导出与结果状态，并验证裁切拖动和系统减少动态效果设置。

平台扩展方式见[新增视频平台指南](docs/adding-a-platform.md)；操作系统贡献方式见[支持矩阵](docs/platform-support.md)。
