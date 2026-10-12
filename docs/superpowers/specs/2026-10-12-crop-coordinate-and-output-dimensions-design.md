# Crop Coordinate and Output Dimension Design

## Problem

The crop overlay currently uses the full CSS bounding box of the `<video>`
element as the video image. With `object-fit: contain`, a portrait or landscape
video can occupy only part of that box, leaving letterboxed space. Pointer
coordinates are normalized against the larger box, while FFmpeg interprets the
resulting fractions against the actual video frame. This makes the exported
crop differ from the visible selection and can produce incorrect derived GIF
dimensions.

## Design

Keep the existing player layout. Explicitly retain centered `object-fit:
contain`, and calculate the rendered image rectangle from the video's intrinsic
`videoWidth` and `videoHeight` and its CSS element rectangle. Position the crop
overlay over the rendered image rectangle; constrain drag, resize, and
normalization to that same rectangle. The crop values sent to the API remain
normalized fractions of the actual video image, so the existing FFmpeg crop
filter continues to consume the same coordinate contract.

When only output width or output height is specified, calculate the other
dimension from the actual cropped frame aspect ratio and let FFmpeg generate
that proportional dimension. Do not silently shrink a user-specified dimension
or add an informational prompt. Explicit width and height inputs remain limited
to 64–1280 pixels. The automatically derived dimension may exceed 1280 pixels,
but must not exceed a 4096-pixel processing safety limit. If it exceeds that
limit, return an explicit error. Default output behavior and the fixed-canvas
behavior when both dimensions are specified remain unchanged.

## Data Flow

1. The browser reads intrinsic dimensions from the loaded preview video.
2. The crop controller calculates the centered `contain` image rectangle
   inside the CSS video element.
3. Crop overlay interaction and fraction normalization use that image rectangle.
4. The API receives fractions of the actual image; the backend applies them to
   the source frame and computes the actual cropped aspect ratio.
5. For a single specified output dimension, FFmpeg scales to that exact
   dimension and derives the other proportionally, subject to the 4096-pixel
   limit.

## Compatibility and Limits

- Preserve the existing player frame, time-selection controls, default GIF
  dimensions, GIF palette workflow, and two-dimension padding behavior.
- Preserve the existing 200 MB source limit, 50 MB GIF limit, and FFmpeg
  timeout.
- Keep crop values normalized to `[0, 1]`; do not change the API schema.
- Do not change or relax the explicitly specified 64–1280 pixel dimension
  validation.

## Validation

- Unit-test contained image rectangle calculations and normalized crop mapping
  for portrait and landscape aspect ratios, including letterboxed space.
- Verify crop movement and resizing remain bounded by the displayed image, not
  the surrounding CSS box.
- Test backend derived dimensions for width-only and height-only requests,
  acceptance above 1280 up to 4096, rejection above 4096, unchanged default
  sizing, and unchanged fixed-canvas behavior.
- In the browser, compare the selection overlay and exported GIF for portrait
  and landscape examples; exercise default, width-only, and height-only
  exports.
