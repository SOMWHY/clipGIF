# 任务：在本地实现一个“多平台视频时间段转 GIF”的本地网页应用（带可视化时间轴）

你是一个拥有 shell 权限的 agent。请直接操作完成，不要只给建议。假设最终用户是不了解技术的小白，部署和使用必须尽可能简单。项目完成后，必须写一份 `SKILL.md`，方便以后复用。

## 1. 这是个什么项目

项目名：**ClipGIF / 多平台视频转GIF本地网页应用**

**产品形态**：本地网页应用。
- 用户双击启动脚本 → 本地服务在 `127.0.0.1:8000` 起来 → 浏览器访问网页使用。
- 网页只是界面，真正干活的是本地服务（FastAPI + yt-dlp + ffmpeg）。
- 浏览器本身不能调用 yt-dlp 下载视频、不能调用 ffmpeg 剪辑，所以必须有一个跑在用户电脑上的后端进程。启动脚本就是让这个后端跑起来的开关，不是命令行工具。

**目标流程**：用户打开本地网页，粘贴视频链接 / BV 号 / 短链，点击“加载视频”。页面加载出可播放的视频预览和时间轴。用户像剪辑软件一样，在时间轴上拖动起止点选择要截取的片段，实时看到起止时间，然后点击“生成 GIF”。后端用 ffmpeg 剪辑并转成 GIF，网页中预览并一键下载。

**关键体验要求**：
- 用户不需要跑到视频平台看“几分几秒”，再回到本网站手动输入。
- 用户直接在网页的视频预览上拖动选择起止点。
- 支持选中后循环预览选区，确认无误再生成。

**当前 MVP 优先支持**：
- B站：BV 号、完整链接、b23.tv 短链

**未来逐步适配其他视频平台**（这是贡献者的主要任务）：
- YouTube
- Vimeo
- X/Twitter
- 其他 yt-dlp 支持的平台
- 本地文件上传（作为特殊平台适配器）

**合规说明**：仅用于个人学习、授权内容或平台允许的场景。README 中注明遵守各平台条款和版权要求。

## 2. 技术栈要求

目标是“单服务、少依赖、一键启动”：

- 后端：Python 3.11+、FastAPI、Uvicorn、Pydantic
- 前端：FastAPI 模板 + 原生 HTML/CSS/JS。时间轴 UI 用原生 JS 实现，不引入重型前端框架。
- 视频下载：yt-dlp，优先用 Python 包调用，或安全调用 CLI
- 视频处理：ffmpeg / ffprobe，系统安装
- 任务状态：内存字典 + SQLite 均可，简单可靠优先
- 依赖管理：`requirements.txt`
- 端口：默认 `8000`，可通过环境变量修改
- 临时目录：`work/{task_id}/`
- 预览视频目录：`previews/{preview_id}.mp4`
- 输出目录：`outputs/{task_id}.gif`

**启动方式**：
- Windows：`start.bat`（MVP 必须可用，双击即可）
- macOS：`start.sh`（MVP 提供占位脚本，标注“实验性，欢迎贡献者完善”）
- Linux：`start.sh`（同上）
- Docker（可选，非 MVP）：`Dockerfile` + `docker-compose.yml`，供 NAS / 服务器部署，MVP 可只放占位或跳过

**启动脚本要做的事**：创建虚拟环境、安装依赖、检测 ffmpeg / yt-dlp、启动 uvicorn、打印访问地址。小白不需要手敲命令。

最终必须满足：一条命令启动、浏览器访问、可预览视频、可拖拽选时间段、可生成并下载 GIF、小白能照着 README 跑起来。

## 3. 操作系统支持策略（与视频平台区分）

本项目有两类“平台”，必须区分，不要混淆：
- **视频平台**（B站、YouTube 等）：由 `PlatformAdapter` 扩展，见后文“多平台架构要求”。
- **操作系统平台**（Windows、macOS、Linux）：由启动脚本、路径处理、依赖检测扩展，即本节。

### MVP 策略
- MVP 只保证 Windows 10/11 能完整跑通。
- macOS / Linux 提供占位脚本和实验性说明，允许不可用，但必须留好接口和文档入口，方便贡献者接手。
- Docker 为可选部署方式，MVP 可只留 `Dockerfile` 占位和 README 说明。

### 代码硬性要求（保证跨平台可迁移）
- 路径一律使用 `pathlib.Path`，禁止硬编码 `\`、`C:\`、`/Users/`。
- 所有 subprocess 调用使用参数列表，禁止 `shell=True`。
- 所有命令行工具调用通过 `shutil.which()` 检测可用性。
- 不要把 Windows 专属逻辑写进核心流程，集中到 `app/services/deps.py` 和启动脚本中。

### 依赖检测与提示
实现 `app/services/deps.py`，至少提供：
- `check_ffmpeg() -> (ok, message)`
- `check_ytdlp() -> (ok, message)`
- `check_python_version() -> (ok, message)`

每个函数在检测失败时，根据 `sys.platform` 给出对应系统的安装提示：
- Windows：给出 winget / 官网下载指引（MVP 必须准确）
- macOS：给出 `brew install ffmpeg` 提示（实验性，欢迎贡献者完善）
- Linux：给出 `apt install ffmpeg` / `dnf install ffmpeg` 提示（实验性）

### 目录与文件预留
```text
scripts/
  start_windows.bat     # MVP 必须可用
  start_macos.sh        # 占位，实验性
  start_linux.sh        # 占位，实验性
  install_windows.ps1   # 可选
  install_macos.sh      # 占位
```

### 文档预留
- `README.md` 中分三节写安装：Windows（完整）、macOS（实验性）、Linux（实验性）。
- 新增 `docs/platform-support.md`，内容为支持矩阵：

```markdown
| 系统 | 状态 | 负责人 | 说明 |
|---|---|---|---|
| Windows 10/11 | ✅ MVP 完整支持 | - | 双击 start_windows.bat |
| macOS | 🚧 实验性 | 待认领 | 欢迎贡献 |
| Linux | 🚧 实验性 | 待认领 | 欢迎贡献 |
| Docker | 🚧 可选 | 待认领 | 欢迎贡献 |

## 如何贡献某系统支持
1. 修改对应 scripts/start_xxx 脚本
2. 更新 app/services/deps.py 中该系统的安装提示
3. 在 CI 中启用该系统的测试 job
4. 更新本文件的支持矩阵
```

### CI 预留
`.github/workflows/ci.yml` 中：
- `windows-latest`：必须通过，MVP 阻塞项。
- `macos-latest`：`continue-on-error: true`，允许红。
- `ubuntu-latest`：`continue-on-error: true`，允许红。

贡献者把 macOS/Linux 的 job 修绿，即可在 PR 中把 `continue-on-error` 去掉，作为阶段性成果。

## 4. 两阶段工作流（重点）

整个流程分成两个阶段，前端和 API 都要体现。

### 阶段一：准备预览
1. 用户输入链接 / BV / 短链，点击“加载视频”。
2. 后端识别平台，用 yt-dlp 下载视频到 `work/{preview_id}/source.*`。
3. 用 ffmpeg 转成浏览器可播放的预览 mp4：
   - H.264 + AAC，`-movflags +faststart`
   - 缩放到高度 <= 480，降低码率（例如 CRF 28）
   - 输出到 `previews/{preview_id}.mp4`
4. 用 ffprobe 读取时长、宽高，返回给前端。
5. 前端用 `<video>` 加载 `/api/previews/{preview_id}/video`，并提供时间轴。

### 阶段二：选择时间段并生成 GIF
1. 用户在时间轴上拖动起止点，前端实时显示 `start`、`end`。
2. 用户可点击“预览选区”，video 元素循环播放选中的片段。
3. 用户点击“生成 GIF”，前端提交 `preview_id` + `start` + `end` + 高级选项。
4. 后端基于已下载的源视频用 ffmpeg 剪辑并转 GIF。
5. 前端轮询任务状态，完成后预览并下载。

### 关于预览视频的 Range 请求
浏览器 `<video>` 拖动进度条时需要 HTTP Range 支持，否则无法 seek。
- 优先使用 Starlette/FastAPI 的 `FileResponse`，它支持 Range。
- 如果当前版本不支持，请实现一个简单的 Range 中间件或自定义响应，确保 `curl -H "Range: bytes=0-100" .../video` 返回 206。
- 这是硬性验收项。

## 5. 多平台（视频平台）架构要求

### 5.1 平台适配器接口

定义统一接口，例如 `app/platforms/base.py`：

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class PlatformInfo:
    name: str                 # 例如 "bilibili"
    display_name: str         # 例如 "B站"
    url_patterns: list[str]   # 用于文档和前端提示
    cookie_help: str          # 如何获取 cookies.txt

class PlatformAdapter(ABC):
    name: str
    display_name: str

    @abstractmethod
    def match(self, raw_input: str) -> bool:
        """判断用户输入是否属于该平台。"""

    @abstractmethod
    def normalize(self, raw_input: str) -> str:
        """把 BV 号、短链等转成标准 URL，供 yt-dlp 使用。"""

    @abstractmethod
    def extract_video_id(self, normalized_url: str) -> str | None:
        """提取平台视频 ID，便于日志和缓存。"""

    def get_ytdlp_options(self, user_options: dict[str, Any]) -> dict[str, Any]:
        """返回平台专属 yt-dlp 参数，例如 cookie、referer、format。"""
        return {}

    def get_default_format(self) -> str:
        """默认下载格式，优先 480p 或更低。"""
        return "bv*[height<=480]+ba/b[height<=480]"

    def validate(self, raw_input: str) -> tuple[bool, str]:
        """平台级校验，返回 (是否合法, 错误信息)。"""
        return True, ""

    def get_cookie_help(self) -> str:
        """返回该平台如何导出 cookies.txt 的说明。"""
        return ""
```

### 5.2 平台注册表

实现 `app/platforms/registry.py`：

- 自动发现并注册所有适配器。
- 提供 `detect_platform(raw_input) -> PlatformAdapter | None`。
- 提供 `list_platforms() -> list[PlatformInfo]`。
- 如果无法识别平台，返回支持列表。
- 未来新增平台只需添加一个适配器文件，不需要改核心任务流水线。

目录建议：

```text
app/
  platforms/
    __init__.py
    base.py
    registry.py
    bilibili.py
    youtube.py.example
    local_file.py.example
```

### 5.3 核心流水线不绑定平台

核心流程：

1. 接收 `url`
2. `detect_platform(url)` 识别平台
3. `adapter.normalize(url)` 得到标准 URL
4. `adapter.get_ytdlp_options()` 合并通用 yt-dlp 参数
5. 下载源视频
6. 生成浏览器预览 mp4（ffmpeg）
7. 前端选择时间段
8. 基于源视频剪辑并转 GIF
9. 返回结果，API 中带上 `platform` 字段

禁止在核心下载器、GIF 生成器里写大量 `if "bilibili" in url`。平台差异必须收敛到适配器。

### 5.4 当前必须实现的适配器

只要求完整实现 **BilibiliAdapter**：

- 支持 BV 号
- 支持完整 B站链接
- 支持 b23.tv 短链，需跟随重定向解析出 BV
- 提供 B站 cookie 获取说明
- 提供 B站常见水印位置预设，例如右上角、右下角
- 默认下载 480p 或更低
- 对需要登录的视频给出友好错误提示

其他平台适配器只需留空文件或 `example`，不要求现在可用。但测试中必须验证“新增一个假平台适配器，核心流程无需修改即可识别并调用”。

## 6. 功能需求

### P0 必须实现

1. **输入识别**
   - B站：BV 号、完整链接、b23.tv 短链
   - 未来平台：通过适配器自动识别，无法识别时提示支持列表

2. **下载源视频**
   - 使用 yt-dlp 下载到 `work/{preview_id}/source.*`
   - 默认优先 480p 或更低，格式由适配器提供
   - 无 cookie 失败时，前端提示可上传 `cookies.txt`，或把 `cookies.txt` 放到项目根目录自动使用
   - README 用小白语言说明如何导出 Netscape 格式 cookies.txt

3. **生成预览视频**
   - 用 ffmpeg 转码为浏览器可播放 mp4
   - `-movflags +faststart`，H.264 + AAC，高度 <= 480
   - 输出 `previews/{preview_id}.mp4`
   - 记录时长、宽高，返回给前端

4. **可视化时间轴（重点）**
   - 网页内嵌 `<video>` 播放预览
   - 自定义时间轴：
     - 显示总时长
     - 双滑块（起始、结束）选择区间
     - 拖动时实时显示起止时间，如 `00:12.5 - 00:18.0`
     - 不允许结束 <= 起始
     - 片段最长默认 60 秒，超出时前端提示并阻止提交
   - “预览选区”按钮：循环播放选中片段
   - “跳到起点”“跳到终点”按钮：便于微调
   - 支持键盘微调：左右方向键移动当前聚焦的滑块 ±0.1s（体验加分项）

5. **生成 GIF**
   - 用户点击“生成 GIF”，创建任务
   - 使用 ffmpeg 先生成调色板，再生成 GIF
   - 输出 `outputs/{task_id}.gif`，循环播放
   - 基于源视频剪辑，不基于预览视频，保证质量

6. **网页交互与状态**
   - 表单字段：视频链接/BV、加载按钮、时间轴、高级选项、生成按钮
   - 显示识别到的平台，例如“已识别：B站”
   - 显示阶段：解析中、下载中、生成预览中、等待选择、剪辑中、转码中、完成
   - 成功后显示 GIF 预览和“下载 GIF”按钮
   - 失败时显示中文错误原因，不要只报 500

7. **视觉呈现与无障碍**
   - 采用暖纸白、深墨色和克制的苔橄榄绿，使用留白、细分隔线和轻边框，避免深色渐变、光晕和厚重卡片。
   - 中文编辑式衬线标题与无衬线正文/控件均使用本机字体回退；不加载远程字体或动效库。
   - 页面纵向排列来源、视频/选段、导出和结果；中小屏幕保持内容顺序并收拢为单列，不得产生横向溢出。
   - 首屏和编辑器仅轻柔入场，每次生成结果短暂淡入；按钮悬停反馈克制。裁切框和时间轴拖动不得受动画影响。
   - 支持 `prefers-reduced-motion: reduce`：关闭入场、结果和悬停位移动效，并避免结果平滑滚动；保留可见焦点和键盘操作。

8. **下载导出**
   - `GET /api/tasks/{task_id}/gif` 返回 GIF 预览
   - `GET /api/tasks/{task_id}/download` 下载文件，文件名如 `clipgif-{platform}-{task_id}.gif`

9. **错误处理**
   - 非法输入、无效链接、时间段错误、视频不存在、需要登录、ffmpeg 失败、超时，都要有友好提示
   - 区分平台错误：例如“B站视频需要登录，请提供 cookies.txt”
   - 后端不能因为单个任务崩溃

### P1 尽量实现的高级功能

1. **裁剪 GIF 尺寸**
   - 支持输出宽度，如 320、480、640；高度按比例自动
   - 也支持指定宽高，但要做边界校验

2. **自由裁切 GIF 画幅**
   - 在视频画面上显示可拖动、可调整大小的自由裁切框，并可重置为完整画幅
   - 裁切框默认关闭；启用后只影响 GIF 输出，不改变源视频或预览
   - 后端接收相对于原始画幅的归一化 x/y/width/height，使用源视频裁切
   - 裁切区域须在画面内且不小于 16×16 像素；裁切只改变输出画幅，不修改保留区域的图像内容

3. **倍速调整**
   - 支持 0.5x、1x、1.5x、2x
   - 使用 ffmpeg setpts 调整视频速度，并同步调整帧率

4. **画质压缩**
   - 支持 fps：5/10/15/20
   - 支持最大颜色数：64/128/256
   - 支持 dither：bayer、sierra2_4a 等
   - 默认参数要保证 GIF 可播放、体积不过大

5. **时间轴缩略图（体验加分项）**
   - 可选：用 ffmpeg 定期抽帧生成 filmstrip，铺在时间轴背景
   - 如果不做，时间轴至少显示进度刻度和当前时间

## 7. API 建议

### 阶段一：准备预览

- `POST /api/previews` 创建预览任务
  请求体：
  ```json
  { "url": "BV1xx411c7mD" }
  ```
  返回：
  ```json
  {
    "preview_id": "...",
    "platform": "bilibili",
    "status": "pending"
  }
  ```

- `GET /api/previews/{preview_id}` 查询状态
  成功后返回：
  ```json
  {
    "preview_id": "...",
    "platform": "bilibili",
    "status": "ready",
    "title": "视频标题",
    "duration": 360.5,
    "width": 854,
    "height": 480,
    "video_url": "/api/previews/{preview_id}/video"
  }
  ```

- `GET /api/previews/{preview_id}/video` 返回预览 mp4
  - 必须支持 HTTP Range，返回 206

### 阶段二：生成 GIF

- `POST /api/previews/{preview_id}/gif` 创建 GIF 任务
  请求体：
  ```json
  {
    "start": 12.5,
    "end": 18.0,
    "crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8},
    "width": 480,
    "height": null,
    "fps": 10,
    "speed": 1.0,
    "max_colors": 128,
    "dither": "sierra2_4a"
  }
  ```
  返回：
  ```json
  { "task_id": "...", "status": "pending" }
  ```

- `GET /api/tasks/{task_id}` 查询状态和结果，返回中包含：
  ```json
  {
    "task_id": "...",
    "preview_id": "...",
    "platform": "bilibili",
    "status": "success",
    "gif_url": "/api/tasks/.../gif",
    "download_url": "/api/tasks/.../download"
  }
  ```

### 其他

- `GET /api/platforms` 返回支持平台列表
- `GET /api/tasks/{task_id}/gif` 预览 GIF
- `GET /api/tasks/{task_id}/download` 下载 GIF
- `GET /health` 健康检查

## 8. 实现与安全要求

- 所有 subprocess 调用必须使用参数列表，禁止 `shell=True`，防止命令注入。
- 对 URL、BV、时间、宽高、fps、速度、颜色数做白名单/范围校验。
- 平台适配器不能执行任意用户输入拼接的命令。
- 限制并发任务数，例如同时最多 2 个。
- 限制下载视频大小和输出 GIF 大小，例如视频不超过 200MB，GIF 不超过 50MB。
- 限制预览视频大小，生成后如果过大要报错或降码率重试。
- 任务完成后可删除 `work/{preview_id}/` 中的大视频文件，保留预览和 GIF 一段时间。
- 日志写入控制台和 `logs/app.log`。
- 不要硬编码 cookie、SESSDATA 或任何隐私信息。
- 预览视频路径要用 preview_id 映射，禁止把用户输入直接拼进文件路径，防止路径穿越。

## 9. 部署与文档要求

你必须直接完成：
1. 创建项目目录和全部代码。
2. 安装 Python 依赖和系统依赖；如果无法安装 ffmpeg，要在 README 中给出各系统安装命令。
3. 运行服务并做端到端测试。
4. 写 `README.md`，面向小白，包含：
   - 项目是什么（本地网页应用，不是命令行工具）
   - Windows 安装与启动（完整步骤，双击 start_windows.bat）
   - macOS 安装与启动（实验性，欢迎贡献）
   - Linux 安装与启动（实验性，欢迎贡献）
   - 如何打开网页
   - 如何粘贴链接并加载预览
   - 如何在时间轴上选择片段
   - 如何生成并下载 GIF
   - 如何导出 cookies.txt
   - 常见问题：ffmpeg 未安装、yt-dlp 失败、需要登录、GIF 太大、预览无法拖动进度条
   - 当前支持视频平台列表，以及“未来会支持更多平台”
5. 写 `SKILL.md`，包含：
   - 如何一键启动（Windows/macOS/Linux 各写一遍）
   - API 说明
   - 常用 ffmpeg/yt-dlp 命令
   - 如何复用这个项目
   - 故障排查
   - 如何新增视频平台适配器
   - 如何新增操作系统支持
6. 写 `docs/adding-a-platform.md`，面向贡献者（视频平台）：
   - 新建 `app/platforms/xxx.py`
   - 继承 `PlatformAdapter`
   - 实现 `match`、`normalize`、`extract_video_id`
   - 可选覆盖 `get_ytdlp_options`
   - 如何加测试
   - 如何更新 README 支持列表
7. 写 `docs/platform-support.md`，面向贡献者（操作系统平台），内容按第 3 节的支持矩阵。
8. 可选但推荐：提供 `Dockerfile` 和 `docker-compose.yml`。

**期望项目结构**：
```text
clipgif/
  app/
    main.py
    models.py
    services/
      downloader.py
      previewer.py
      gif_maker.py
      deps.py
    platforms/
      __init__.py
      base.py
      registry.py
      bilibili.py
      youtube.py.example
      local_file.py.example
    templates/
      index.html
    static/
      app.js
      timeline.js
      style.css
  scripts/
    start_windows.bat
    start_macos.sh
    start_linux.sh
    install_windows.ps1
    install_macos.sh
  docs/
    adding-a-platform.md
    platform-support.md
  tests/
    test_platform_registry.py
    test_bilibili_adapter.py
    test_api.py
    test_range_support.py
  .github/
    workflows/
      ci.yml
    ISSUE_TEMPLATE/
      platform-support.yml
  previews/
  outputs/
  work/
  logs/
  requirements.txt
  start.bat              # 兼容入口，内部调用 scripts/start_windows.bat
  start.sh               # 兼容入口，内部调用 scripts/start_macos.sh / start_linux.sh
  README.md
  SKILL.md
  Dockerfile
  docker-compose.yml
```

## 10. 验收标准

完成后必须逐条验证，并在最终回复中报告结果。

### 核心流程
1. Windows 下双击 `start_windows.bat` 后，服务能在 `http://127.0.0.1:8000` 打开。
2. 输入公开 B站视频 BV 号，点击“加载视频”，页面出现可播放的视频预览。
3. 视频预览可以拖动进度条 seek，浏览器不报错。
4. `curl -H "Range: bytes=0-100" http://127.0.0.1:8000/api/previews/{id}/video -I` 返回 206。
5. 时间轴显示总时长，双滑块可拖动，起止时间实时更新。
6. 点击“预览选区”，视频循环播放选中片段。
7. 选择 0-3s，默认参数，点击“生成 GIF”，能生成 GIF。
8. 网页能预览 GIF，点击下载能得到 `.gif` 文件。
9. 下载的 GIF 文件大小 > 0，能被浏览器打开，能被 ffmpeg/ffprobe 识别。
10. 输入 b23.tv 短链，能解析、生成预览、生成 GIF。
11. 时间轴支持 `12.5` 这种小数秒，起止时间精确。
12. 非法输入：错误 BV、结束时间小于等于开始、超过 60 秒，网页显示中文错误，后端不崩溃。
13. 开启“倍速 2x”后，输出 GIF 时长约为原选区的 1/2。
14. 开启“宽度 320、fps 10、颜色数 128”后，GIF 尺寸和体积明显变化。
15. 启用“裁切”并调整裁切框后，GIF 只保留所选画幅；重置后恢复完整画面，不承诺修复框内图像内容。
16. 所有 subprocess 无 `shell=True`，命令注入测试无效。
17. `README.md` 和 `SKILL.md` 存在，且小白能按步骤启动。
18. 首页使用暖纸白/深墨色/苔橄榄绿的编辑式视觉风格，且没有横向溢出。
19. 在 `prefers-reduced-motion: reduce` 下，首屏、编辑器、结果、按钮和结果滚动均无非必要动效。
20. 启用动效时，裁切框缩放/移动与时间轴滑块拖动仍即时响应。

### 多平台（视频平台）预留验收
21. 存在 `PlatformAdapter` 抽象接口和 `platform_registry`。
22. 核心下载、预览、转 GIF 流程中没有散落的 B站硬编码判断。
23. `GET /api/platforms` 返回当前支持平台列表。
24. 预览和任务状态中包含 `platform` 字段。
25. 编写一个测试用的假平台适配器，例如 `FakeAdapter`，验证注册表自动发现、`detect_platform` 识别、核心流程无需改核心代码即可调用。
26. `docs/adding-a-platform.md` 存在，贡献者按文档能新增视频平台适配器。
27. README 中明确说明：当前完整支持 B站，未来欢迎贡献其他平台适配器。
28. 未实现平台输入时，网页提示“暂不支持该平台，当前支持：B站”，而不是 500。

### 操作系统平台预留验收
29. Windows 下双击 `start_windows.bat` 能启动服务并打开网页。
30. 核心代码中不出现硬编码 Windows 路径。
31. `app/services/deps.py` 存在，缺 ffmpeg 时给出分平台安装提示。
32. `docs/platform-support.md` 存在，含支持矩阵和贡献指引。
33. CI 中 Windows job 必须通过，macOS/Linux job 存在且 `continue-on-error: true`。
34. `scripts/start_macos.sh` 和 `scripts/start_linux.sh` 存在（可占位），README 标注为实验性。

### 最终回复必须包含
- 项目实际路径
- 启动命令（Windows 为主，macOS/Linux 说明实验性）
- 浏览器访问地址
- 已执行的测试命令和结果
- 当前支持的视频平台列表
- 当前支持的操作系统列表
- 如何新增视频平台适配器的简要说明
- 如何贡献操作系统支持的简要说明
- 时间轴交互的实现说明（Range 支持怎么做的）
- 已知限制
- 如果某些高级功能未完成，说明原因和替代方案

现在开始：先检查当前系统环境，再选择最优实现路径。能直接安装就安装，能直接运行就运行。完成后把项目留在本地，并告诉我如何打开使用。