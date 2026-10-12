# ClipGIF P1 GIF Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add validated GIF crop, dimension, speed, FPS, palette-size, and dithering controls to the existing ClipGIF editor and source-based FFmpeg export pipeline.

**Architecture:** Keep the existing FastAPI → `GifRequest` → `JobManager` → `make_gif` path and add no dependencies or intermediate transcode. The browser crop overlay sends a normalized rectangle; the backend applies identical crop/speed/FPS/scale/pad filters to palette generation and GIF encoding, using the original source video.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, FFmpeg/ffprobe, native HTML/CSS/JavaScript, pytest, Node.js built-in test runner.

**Spec:** `docs/superpowers/specs/2026-10-12-clipgif-p1-design.md`

## Global Constraints

- Python 3.11+; retain FastAPI templates and native JavaScript; add no dependencies.
- Source clip duration remains at most 60 seconds and GIF output remains at most 50 MB.
- Crop coordinates are normalized to [0, 1], stay within the frame, and cover at least 16 by 16 source pixels.
- Custom output dimensions are integers from 64 through 1280 pixels; preset widths are 320, 480, and 640 pixels.
- FPS choices are 5, 10, 15, and 20; preserve 12 FPS as the compatibility default when the request omits FPS.
- Playback speeds are 0.5x, 1x, 1.5x, and 2x; color counts are 64, 128, and 256; dithering is `bayer` or `sierra2_4a`.
- Preserve default output behavior: no crop, output width capped at 480 without upscaling smaller inputs, 12 FPS, 1x, 128 colors, `sierra2_4a`.
- Crop is named **裁切** and changes the output picture area only; do not describe it as watermark removal or add AI/masking/blur removal.
- Use the original source video for GIF generation. FFmpeg commands must remain argument arrays, never `shell=True`.
- Keep the existing 50 MB GIF size cap, 60-second clip cap, timeout, and temporary-file cleanup behavior.
- Do not implement optional filmstrip timeline thumbnails in this iteration.

## Review Focus

- A normalized crop near an image edge must remain inside the decoded frame after conversion to chroma-safe pixel coordinates, and resetting to full frame must not shave odd-sized edges; Tasks 2–3 test edge, minimum-size, and full-frame cases.
- Explicit width/height with a mismatched aspect ratio must yield exact requested dimensions without stretching; Task 5 tests the generated file with ffprobe.
- Speed must affect both palette and output frames, while the source interval remains fixed; Task 2 tests filter construction and Task 5 tests output duration.
- Requests omitting every advanced option must preserve the current ≤480-pixel, 12-FPS, 128-color output; Tasks 1 and 2 pin defaults in model and FFmpeg tests.
- Failed or oversized transcodes must not leave a partial GIF or palette image; Task 2 tests failure cleanup and preserves the existing size-limit test.

---

### Task 1: Define and validate the GIF export contract

**Files:**
- Modify: `app/models.py`
- Modify: `app/main.py`
- Test: `tests/test_gif_maker.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces `CropRegion(x: float, y: float, width: float, height: float)` with normalized finite coordinates, positive dimensions, and a rectangle fully inside the frame.
- Produces optional `GifRequest.crop`, `width`, and `height`; `fps=12`, `speed=1.0`, `max_colors=128`, and `dither="sierra2_4a"` defaults.
- Crop JSON shape: `"crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8}`. All crop values are fractions of the full frame.
- Width and height are optional strict integers from 64 through 1280. Width omitted means the existing 480-pixel maximum with no upscaling; explicit dimensions request that output canvas size.
- When exactly one dimension is supplied, calculate the other from the crop aspect ratio; only the explicitly supplied dimension must be at least 64 pixels. A derived dimension may be below 64 but must be positive and no greater than 1280. When both dimensions are supplied, both remain within 64–1280.
- FPS accepts 5, 10, 12, 15, or 20 so omission preserves the current 12-FPS result; explicit UI choices are 5, 10, 15, and 20. Speed accepts 0.5, 1, 1.5, or 2; colors accept 64, 128, or 256; dither accepts `bayer` or `sierra2_4a`.

- [ ] **Step 1: Write failing schema tests** in `tests/test_gif_maker.py`:

```python
def test_gif_request_uses_current_export_defaults():
    request = GifRequest(start=0, end=3)
    assert request.fps == 12
    assert request.speed == 1
    assert request.width is None and request.height is None
    assert request.max_colors == 128
    assert request.dither == "sierra2_4a"
    assert request.crop is None


@pytest.mark.parametrize(
    "crop",
    [
        {"x": -0.1, "y": 0, "width": 0.5, "height": 0.5},
        {"x": 0.8, "y": 0, "width": 0.3, "height": 0.5},
        {"x": 0, "y": 0, "width": 0, "height": 0.5},
        {"x": 0, "y": 0, "width": float("nan"), "height": 0.5},
    ],
)
def test_gif_request_rejects_invalid_crop(crop):
    with pytest.raises(ValidationError):
        GifRequest(start=0, end=3, crop=crop)


@pytest.mark.parametrize(
    "options",
    [
        {"width": 63}, {"width": True}, {"height": 1281}, {"fps": 8}, {"fps": True},
        {"speed": 3}, {"max_colors": 32}, {"dither": "none"},
    ],
)
def test_gif_request_rejects_out_of_range_export_options(options):
    with pytest.raises(ValidationError):
        GifRequest(start=0, end=3, **options)
```

- [ ] **Step 2: Run the focused tests and confirm they fail** because the crop model and advanced request fields do not exist:

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_gif_maker.py -q`

Expected: FAIL on missing `crop`, `fps`, and dimension fields.

- [ ] **Step 3: Add `CropRegion` and `GifRequest` validation** in `app/models.py`:

```python
from typing import Literal


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
```

Add the typed optional fields and allowed-value validators to `GifRequest`; preserve its existing time-range validation. In `app/main.py`, distinguish invalid time fields from invalid export options in the request-validation response so size/speed errors do not misleadingly report a time-range problem.

Define the fields as:

```python
crop: CropRegion | None = None
width: Annotated[int, Field(strict=True, ge=64, le=1280)] | None = None
height: Annotated[int, Field(strict=True, ge=64, le=1280)] | None = None
fps: Annotated[int, Field(strict=True)] = 12
speed: Literal[0.5, 1.0, 1.5, 2.0] = 1.0
max_colors: Literal[64, 128, 256] = 128
dither: Literal["bayer", "sierra2_4a"] = "sierra2_4a"
```

Validate FPS against `{5, 10, 12, 15, 20}` while retaining 12 only as the compatibility default. Do not allow booleans to pass as integer dimensions or FPS.

- [ ] **Step 4: Run schema and API validation tests**. Add an API test posting invalid FPS, boolean dimensions, and out-of-frame crop requests and assert HTTP 422 with Chinese details. The parameterized `GifRequest` test must also instantiate a fully populated valid crop/export request and assert each field survives validation.

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_gif_maker.py tests\test_api.py -q`

Expected: PASS; update `test_gif_request_preserves_decimal_seconds` to compare `start` and `end` individually because the request model now includes defaulted export fields; existing P0 bodies containing only `start` and `end` remain accepted.

- [ ] **Step 5: Commit the contract**:

```powershell
git add app/models.py app/main.py tests/test_gif_maker.py tests/test_api.py
git commit -m "feat: define validated GIF export options"
```

### Task 2: Apply crop and export controls in FFmpeg

**Files:**
- Modify: `app/services/gif_maker.py`
- Modify: `app/services/jobs.py`
- Test: `tests/test_gif_maker.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Change the service entry point to `make_gif(source_path: Path, output_path: Path, request: GifRequest, frame_width: int, frame_height: int, on_stage: Callable[[str], None] | None = None) -> Path`.
- `JobManager._run_gif` passes the validated `GifRequest` and the ready preview's width/height; those preview dimensions retain the source frame's aspect ratio.
- Add pure helper `_build_video_filter(request: GifRequest, frame_width: int, frame_height: int) -> str` in `app/services/gif_maker.py`. It returns the same crop, speed, FPS, scale, and optional pad chain for both palette generation and final encoding.

- [ ] **Step 1: Write failing FFmpeg-option tests** in `tests/test_gif_maker.py`:

```python
def test_build_video_filter_applies_crop_speed_fps_and_exact_canvas():
    request = GifRequest(
        start=0,
        end=3,
        crop={"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
        width=640,
        height=480,
        fps=20,
        speed=2,
        max_colors=256,
        dither="bayer",
    )
    filters = gif_maker._build_video_filter(request, 1280, 720)
    assert "crop=" in filters
    assert "setpts=PTS/2" in filters
    assert "fps=20" in filters
    assert "force_original_aspect_ratio=decrease" in filters
    assert "pad=640:480" in filters


def test_crop_filter_keeps_bottom_right_region_inside_odd_frame():
    crop = CropRegion(x=0.5, y=0.5, width=0.5, height=0.5)
    result = gif_maker._crop_filter(crop, 1279, 719)
    assert result == (
        "crop=trunc(iw*0.5/2)*2:trunc(ih*0.5/2)*2:"
        "trunc(iw*0.5/2)*2:trunc(ih*0.5/2)*2"
    )


def test_crop_filter_rejects_region_smaller_than_minimum():
    crop = CropRegion(x=0, y=0, width=0.01, height=0.01)
    with pytest.raises(ClipGifError, match="裁切区域"):
        gif_maker._crop_filter(crop, 320, 240)


def test_make_gif_uses_identical_video_filters_for_palette_and_output(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"generated")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gif_maker.shutil, "which", lambda _name: "ffmpeg.exe")
    monkeypatch.setattr(gif_maker.subprocess, "run", run)
    request = GifRequest(start=0, end=3, fps=15, max_colors=64, dither="bayer")
    gif_maker.make_gif(source, tmp_path / "result.gif", request, 640, 360)
    palette_filter = calls[0][calls[0].index("-vf") + 1].split(",palettegen=")[0]
    output_graph = calls[1][calls[1].index("-filter_complex") + 1]
    assert palette_filter in output_graph
    assert "palettegen=max_colors=64" in calls[0][calls[0].index("-vf") + 1]
    assert "paletteuse=dither=bayer" in output_graph
```

- [ ] **Step 2: Run the focused tests and confirm they fail** on the absent filter helper and new `make_gif` signature:

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_gif_maker.py -q`

Expected: FAIL because the configurable pipeline has not been implemented.

- [ ] **Step 3: Implement the shared filter builder and pass request data through jobs**:

```python
def _build_video_filter(request: GifRequest, frame_width: int, frame_height: int) -> str:
    filters: list[str] = []
    if request.crop is not None:
        # Convert the validated normalized region to bounded even pixel values.
        filters.append(_crop_filter(request.crop, frame_width, frame_height))
    if request.speed != 1:
        filters.append(f"setpts=PTS/{request.speed:g}")
    filters.append(f"fps={request.fps}")
    filters.extend(_scale_and_pad_filters(request, frame_width, frame_height))
    return ",".join(filters)
```

Define and test these helper signatures in the same module:

```python
def _crop_filter(crop: CropRegion, frame_width: int, frame_height: int) -> str: ...
def _scale_and_pad_filters(
    request: GifRequest, frame_width: int, frame_height: int
) -> list[str]: ...
```

Build crop expressions from normalized fractions and FFmpeg's input dimensions (`iw`/`ih`), truncate crop size and origin to even pixels, and clamp the final rectangle to the frame. Use `frame_width`/`frame_height` to reject rectangles smaller than 16 by 16 pixels at the displayed source aspect ratio; the source file is never smaller than its downscaled preview. Scale/pad rules: when width and height are both omitted, use the current `scale=w=min(480\\,iw):h=-2:flags=lanczos`; when exactly one is supplied, calculate the other dimension from the cropped aspect ratio; when both are supplied, use `force_original_aspect_ratio=decrease` and centered black `pad` to produce the exact canvas without stretching. Validate explicit dimensions in 64–1280 and derived dimensions in 1–1280 before running FFmpeg.

Use the filter helper before `palettegen` in the palette pass and in the video branch of the output filter graph. Use `request.max_colors` and `request.dither`; omit `setpts` at 1x to preserve current timestamps. Keep `-ss` and `-t` based on the original interval, subprocess argument arrays, timeout, callbacks, cleanup, and GIF-size checks. If `PreviewJob.width` or `height` is absent, fail the task with a clear Chinese `ClipGifError` instead of passing invalid dimensions to FFmpeg.

- [ ] **Step 4: Run focused tests and update existing callers**:

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_gif_maker.py tests\test_api.py -q`

Expected: PASS; all fake `make_gif` callables accept `request`, `frame_width`, `frame_height`, and `on_stage`; ready-preview fixtures set width and height (for example, 640×360); default requests still use the ≤480 scale and 12 FPS.

- [ ] **Step 5: Commit the FFmpeg pipeline**:

```powershell
git add app/services/gif_maker.py app/services/jobs.py tests/test_gif_maker.py tests/test_api.py
git commit -m "feat: apply GIF crop and quality settings"
```

### Task 3: Build the interactive crop overlay

**Files:**
- Create: `app/static/crop.js`
- Modify: `app/templates/index.html`
- Modify: `app/static/style.css`
- Modify: `app/services/gif_maker.py`
- Test: `tests/test_crop.js`
- Test: `tests/test_gif_maker.py`

**Interfaces:**
- Expose `window.ClipGifCrop.createCropOverlay({frame, video, toggle, reset})`.
- Return `setEnabled(enabled)`, `reset()`, and `region()`. `region()` returns `null` when crop is disabled, otherwise `{x, y, width, height}` in normalized video-frame coordinates.
- The crop rectangle starts disabled; enabling initializes a full-frame rectangle. The reset control restores the full-frame rectangle and keeps crop enabled.
- Export pure `normalizeRect(rect, bounds)`, `moveRect(rect, dx, dy, bounds)`, and `resizeRect(rect, handle, dx, dy, bounds, minWidth, minHeight)` helpers on `window.ClipGifCrop` so edge behavior is directly testable without a browser.

- [ ] **Step 1: Write failing Node tests** in `tests/test_crop.js` for normalized coordinates, disabling to `null`, restoring the full frame, and clamping moves/resizes at frame edges:

```javascript
test("crop rect stays inside the frame when moved", () => {
  const frame = { left: 10, top: 20, width: 200, height: 100 };
  assert.deepEqual(
    window.ClipGifCrop.moveRect({ left: 150, top: 70, width: 50, height: 20 }, 40, 40, frame),
  { left: 160, top: 100, width: 50, height: 20 },
  );
});

test("crop region is normalized to displayed video bounds", () => {
  assert.deepEqual(
    window.ClipGifCrop.normalizeRect(
      { left: 60, top: 45, width: 100, height: 50 },
      { left: 10, top: 20, width: 200, height: 100 },
    ),
    { x: 0.25, y: 0.25, width: 0.5, height: 0.5 },
  );
});
```

Also assert resize handles cannot cross the opposite edge and that minimum dimensions are honored.

- [ ] **Step 2: Run the crop tests and confirm they fail** because `/static/crop.js` does not exist:

Run: `node --test tests\test_crop.js`

Expected: FAIL with the missing crop module.

- [ ] **Step 3: Implement the crop controller** in `app/static/crop.js`:

```javascript
function normalizedRect(rect, bounds) {
  return {
    x: (rect.left - bounds.left) / bounds.width,
    y: (rect.top - bounds.top) / bounds.height,
    width: rect.width / bounds.width,
    height: rect.height / bounds.height,
  };
}
```

Use pointer capture for dragging the rectangle and its four corner handles; clamp movement and resizing to the displayed video bounds and enforce a 16-source-pixel minimum using `video.videoWidth` and `video.videoHeight`. Recompute the overlay bounds from the video element's current client rectangle on resize. Do not derive coordinates from the outer letterboxed player frame. Update `_build_video_filter` so a normalized full-frame region skips the crop filter; reset-to-full-frame must not discard odd-sized source edge pixels.

- [ ] **Step 4: Add overlay markup and styles**, and run crop tests:

Add `crop.js` before `app.js` in the template. Place an initially hidden overlay and four labeled resize handles over the video element, with separate enable and reset buttons. Add focus-visible styling, `touch-action: none` for pointer handles, and responsive positioning in `style.css`.

Run: `node --test tests\test_crop.js`

Expected: PASS for edge clamping, normalized frame-relative coordinates, reset, and disabled state. Run `.\.venv\Scripts\python.exe -m pytest tests\test_gif_maker.py -q` and confirm a full-frame crop on an odd-sized source adds no crop filter.

- [ ] **Step 5: Commit the crop component**:

```powershell
git add app/static/crop.js app/templates/index.html app/static/style.css tests/test_crop.js
git add app/services/gif_maker.py tests/test_gif_maker.py
git commit -m "feat: add interactive GIF crop frame"
```

### Task 4: Wire export controls into the editor and API

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Test: `tests/test_api.py`
- Test: `tests/test_crop.js`

**Interfaces:**
- `app.js` reads `window.ClipGifCrop.createCropOverlay(...).region()` and submits it as the request's optional `crop` object.
- Form field names map exactly to API keys: `width`, `height`, `fps`, `speed`, `max_colors`, `dither`.
- The initial UI state omits width, height, and FPS (preserving the ≤480 and 12-FPS defaults), and selects 1x, 128 colors, and `sierra2_4a`.

- [ ] **Step 1: Add an API integration test** in `tests/test_api.py` that captures the `GifRequest` passed to `make_gif` and asserts a submitted crop plus width/height/FPS/speed/colors/dither arrive unchanged.

Use the existing `client` fixture and a ready `PreviewJob`; the patched `make_gif` callable has signature `(source, target, request, frame_width, frame_height, on_stage)`, records `request.model_dump()`, writes a small GIF file to `target`, and returns it. POST:

```python
{
    "start": 0,
    "end": 3,
    "crop": {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
    "width": 640,
    "height": 480,
    "fps": 20,
    "speed": 2,
    "max_colors": 256,
    "dither": "bayer",
}
```

Wait for `success` and assert the captured request preserves each supplied value. This API test is a passing integration guard for the preceding contract and FFmpeg tasks; the browser form itself is manually exercised in Task 5.

- [ ] **Step 2: Run the API integration test**:

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_api.py -q -k advanced_gif_options`

Expected: PASS with all explicitly submitted fields preserved through the background job.

- [ ] **Step 3: Add the export form controls** to the editor template: an enable-crop button and reset button, width preset options 320/480/640 plus default and custom values, optional height, speed choices 0.5/1/1.5/2, FPS choices 5/10/15/20, colors 64/128/256, and dithering `bayer`/`sierra2_4a`. Reveal custom numeric inputs only when their option is selected. Keep labels and errors in Chinese, and do not use “去水印” wording.

Use stable ids `cropToggle`, `cropReset`, `outputWidth`, `customWidth`, `outputHeight`, `outputSpeed`, `outputFps`, `outputColors`, and `outputDither`. The default width select value is empty (omit width from JSON); its label says “默认（最大 480，较小画面不放大）”. The FPS select also starts at an empty “默认（12 fps）” option; explicit options are 5, 10, 15, and 20. Custom width input is number/step=1/min=64/max=1280. Height is optional with the same bounds.

- [ ] **Step 4: Wire crop and form values into the POST body** in `app/static/app.js`. Omit empty width/height/FPS fields and omit `crop` when crop is disabled; convert numeric fields to numbers. Keep the existing source interval and task polling flow. Run the focused API and crop tests.

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_api.py -q; node --test tests\test_crop.js`

Expected: PASS; the JSON passed to the task contains the selected options, while untouched controls preserve default values.

- [ ] **Step 5: Commit the editor integration**:

```powershell
git add app/templates/index.html app/static/app.js app/static/style.css tests/test_api.py tests/test_crop.js
git commit -m "feat: expose advanced GIF export controls"
```

### Task 5: Verify real output and update P1 documentation

**Files:**
- Modify: `overview.md`
- Modify: `README.md`
- Modify: `SKILL.md`
- Test: `tests/test_gif_maker.py`
- Test: `tests/test_crop.js`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- The documented API example uses `crop: {x, y, width, height}`, optional `width` and `height`, and the validated quality options.
- The overview's P1 section describes user-approved **裁切**, not watermark removal. Adapter watermark preset methods are not exposed as a GIF removal feature.

- [ ] **Step 1: Add a real synthetic-media test** in `tests/test_gif_maker.py`:

```python
def test_make_gif_crop_speed_and_canvas_with_real_ffmpeg(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    assert ffmpeg is not None and ffprobe is not None, "install ffmpeg and ffprobe to run media tests"
    source = tmp_path / "source.mp4"
    output = tmp_path / "result.gif"
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i",
            "testsrc2=size=160x120:rate=20:duration=2",
            "-pix_fmt", "yuv420p", str(source),
        ],
        check=True, capture_output=True, text=True,
    )
    request = GifRequest(
        start=0, end=2,
        crop={"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
        width=80, height=80, fps=10, speed=2, max_colors=64, dither="bayer",
    )
    make_gif(source, output, request, 160, 120)
    probe = subprocess.run(
        [
            ffprobe, "-v", "error", "-show_entries", "format=duration:stream=width,height",
            "-of", "json", str(output),
        ],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(probe.stdout)
    assert (result["streams"][0]["width"], result["streams"][0]["height"]) == (80, 80)
    assert abs(float(result["format"]["duration"]) - 1.0) <= 0.2
```

Use a temporary output directory and also invoke ffmpeg once with `-v error -i result.gif -f null -` to assert the GIF fully decodes.

- [ ] **Step 2: Install FFmpeg in the CI matrix and run the focused media test**. In `.github/workflows/ci.yml`, add an OS-specific installation step before pytest: Windows `choco install ffmpeg -y`, macOS `brew install ffmpeg`, and Ubuntu `sudo apt-get update && sudo apt-get install -y ffmpeg`. Preserve the existing OS matrix and `continue-on-error` policy, and add `tests/test_crop.js` to the Node test command.

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_gif_maker.py -q`

Expected: PASS with installed ffmpeg/ffprobe; missing executables fail explicitly rather than silently skipping.

- [ ] **Step 3: Update the specifications and user docs**:

In `overview.md`, replace the P1 watermark-removal item with the agreed freeform crop behavior; update its GIF API example and acceptance criteria to describe crop output, custom dimensions, speed, FPS, colors, and dithering. Keep AI/mask-based removal out of scope.

In `README.md`, add concise Chinese steps for enabling/moving/resizing/resetting the crop frame and describe export width/height, speed, FPS, colors, dithering, defaults, and the 50 MB/60-second limits. In `SKILL.md`, document the JSON request fields, allowed values, default behavior, aspect-preserving padding, and that crop is not watermark removal.

- [ ] **Step 4: Run all relevant automated checks**:

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: PASS for the full Python suite.

Run: `node --check app\static\app.js; node --check app\static\crop.js; node --check app\static\timeline.js; node --test tests\test_timeline.js tests\test_crop.js`

Expected: all syntax checks and JavaScript tests pass.

- [ ] **Step 5: Manually validate the browser workflow**: start the app with the existing Windows script, load a user-authorized video, drag/move/resize/reset the crop overlay, generate a short GIF using non-default speed and output settings, and confirm preview/download dimensions and timing. Do not use or request cookie contents as test evidence.

- [ ] **Step 6: Commit the end-to-end verification and docs**:

```powershell
git add overview.md README.md SKILL.md .github/workflows/ci.yml tests/test_gif_maker.py tests/test_crop.js
git commit -m "docs: document ClipGIF P1 controls"
```
