# ClipGIF P1 Advanced GIF Controls — Design

**Date:** 2026-10-12  
**Status:** Approved design; awaiting the user's review of this document.

## Goal and scope

Extend the existing local ClipGIF workflow with the non-optional P1 GIF controls from `overview.md`, with one user-confirmed terminology and scope change:

- Add a freeform crop feature named **裁切**. It selects the output picture area; it is not advertised as watermark removal and does not promise to remove a watermark.
- Add GIF output dimensions, playback speed, and palette/quality controls.
- Do not add filmstrip timeline thumbnails in this iteration.
- Keep the existing Bilibili download/preview workflow, local processing model, dependencies, 60-second selection cap, and 50 MB GIF cap.

## User workflow

1. Load and preview a video as today.
2. Enable **裁切** to show a crop rectangle over the video. Drag inside the rectangle to move it; drag its handles to resize it. A reset action restores the full frame. The crop rectangle is not enabled by default.
3. Configure output dimensions, speed, FPS, maximum colors, and dithering in the GIF export controls.
4. Generate, preview, and download the GIF through the existing task flow.

The crop affects only the generated GIF. The source video and browser preview remain unchanged.

## User interface and defaults

- Render an interactive crop overlay aligned to the displayed video image, with move and resize handles and an accessible reset control. Keep the existing timeline selection and preview controls.
- Represent the crop as normalized frame-relative coordinates so the same region can be applied to the original, full-quality source even though the displayed preview is smaller.
- Provide output width choices 320, 480, and 640 pixels, plus a custom width; allow an optional custom height. When only width is specified, calculate height from the cropped region's aspect ratio.
- If both output width and height are specified and have a different aspect ratio from the crop, fit the image inside the requested dimensions and pad the remaining area with black. Never stretch the picture.
- Provide speed choices 0.5x, 1x, 1.5x, and 2x.
- Provide FPS choices 5, 10, 15, and 20. Keep the current 12 FPS value as the compatibility default when no FPS is submitted.
- Provide maximum color choices 64, 128, and 256, and dithering choices `bayer` and `sierra2_4a`.
- Preserve current effective defaults when advanced controls are untouched: no crop, maximum output width 480 without upscaling smaller source frames, 12 FPS, 1x speed, 128 colors, and `sierra2_4a` dithering.

## API and validation

Extend `GifRequest` with optional crop coordinates, output width/height, FPS, speed, maximum colors, and dithering. Requests omitting the new properties remain valid and produce the existing default output. Use `extra="forbid"` and validate every supplied property server-side.

- Crop coordinates are finite normalized values in the range [0, 1], describe a non-empty rectangle fully inside the frame, and must cover at least 16 by 16 source pixels at the preview/source aspect ratio.
- Custom output width and height are integers between 64 and 1280 pixels. An omitted height is derived from the crop aspect ratio. The unchanged default width behavior caps output at 480 pixels and does not enlarge smaller source frames.
- FPS is one of 5, 10, 12 (compatibility default), 15, or 20. Explicit user selections are 5, 10, 15, or 20.
- Speed is one of 0.5, 1, 1.5, or 2.
- Maximum colors are 64, 128, or 256. Dithering is `bayer` or `sierra2_4a`.
- Keep the existing clip-duration and output-file size limits.

Invalid values should produce the application's existing Chinese validation errors rather than reaching FFmpeg. Crop validation must also reject rectangles that become empty or fall outside the decoded frame after conversion to pixel coordinates.

## Processing architecture

Extend the current `GifRequest` → `JobManager` → `make_gif` pipeline; do not add a separate crop/transcode intermediate file or a new dependency. The existing source video remains the input so output quality is not limited by the preview transcode.

Build a deterministic video filter chain from validated options: crop (when selected), speed adjustment with `setpts`, FPS conversion, aspect-preserving scale, and optional padding. Use equivalent video filters and palette settings for palette generation and final GIF encoding, so the generated palette matches the actual output frames. Keep subprocess invocation as argument lists, with existing timeouts, error reporting, temporary-palette cleanup, and GIF-size enforcement.

The selected source interval remains unchanged by speed. Faster playback shortens the resulting GIF duration in proportion to the speed factor; slower playback lengthens it. At 1x, timing remains equivalent to the current behavior.

## Testing and acceptance

- Unit-test request defaults, valid choices, bounds, non-finite values, and invalid crop rectangles.
- Test that generated FFmpeg arguments use the requested crop, speed, FPS, scaling/padding, color count, and dithering for both palette and final output; verify no shell execution is introduced.
- Extend API tests for advanced options and validation errors.
- Test crop-overlay mapping, move/resize behavior, reset, and normalized coordinates at different displayed sizes.
- Use locally generated synthetic media to verify crop output bounds and aspect ratio, exact requested dimensions when width and height are supplied, and expected duration changes at 0.5x/1.5x/2x. Confirm GIF output remains readable and the existing default behavior and size limit still work.
- Run the Python test suite and JavaScript syntax/unit tests; manually exercise the browser export controls and crop overlay.

## Documentation

Update `overview.md` to replace the P1 watermark-removal request with the user-approved **裁切** feature and its explicit scope. Update `README.md` and `SKILL.md` with the crop interaction, output dimensions, speed, quality controls, defaults, and limitations. No platform watermark-removal presets are exposed as user-facing functionality.

## Deferred

- Filmstrip/timeline thumbnails.
- AI, inpainting, blur, or mask-based watermark removal.
- Any change to platform support, downloading, preview generation, storage, or deployment dependencies.
