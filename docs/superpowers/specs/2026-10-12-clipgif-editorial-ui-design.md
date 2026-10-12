# ClipGIF Meridian Editorial UI Redesign

**Date:** 2026-10-12  
**Status:** Implemented and browser-verified on 2026-10-12.

## Goal

Replace ClipGIF's dark, gradient-heavy interface with a quieter editorial gallery aesthetic inspired by the visual language of Atelier Meridian. Preserve the established local-first video-to-GIF workflow and all P1 functionality.

## Confirmed direction

- **Visual reference:** Atelier Meridian, interpreted as a design reference rather than a page to copy.
- **Palette:** warm paper/off-white background, deep ink text, muted moss/olive green for selected states and primary actions, and restrained sand/stone neutrals.
- **Typography:** Chinese editorial serif treatment for the large hero title, using locally available/system font fallbacks; clean sans-serif for labels, forms, controls, and body copy. Do not add a remote font dependency.
- **Language:** Chinese remains the primary user-facing language. English is limited to small eyebrow labels and restrained step/edition details; it must not carry required instructions.
- **Layout:** vertical editorial long-form composition. Introduce the tool with the title and source form, then reveal the video preview as the primary visual. Keep timeline/crop interactions immediately adjacent to the video, with export settings and result following in clear sequence. The page becomes a single column on narrow screens.
- **Surface treatment:** replace dark glassy/gradient cards, glow, heavy shadows, and oversized rounded panels with generous whitespace, thin rules, light borders, restrained corners, and quiet paper-like surfaces. Maintain clear contrast and visible keyboard focus.
- **Motion:** restrained gallery-style entrance. On initial page load, the hero and source/workspace sections fade in with a small upward offset. Reveal the generated result with a brief fade. Buttons may lift subtly on hover. Timeline dragging and crop pointer interactions must remain immediate, without animation lag. No looping decorative animation, autoplay, or motion that delays controls. Respect `prefers-reduced-motion` by suppressing nonessential transitions and entrance effects.

## User workflow and functionality

The redesign is presentation-only: do not alter API contracts, GIF encoding parameters, validation, Bilibili download/preview logic, task lifecycle, or filesystem behavior.

Retain and restyle all existing UI elements:

1. Bilibili URL/BV input, optional cookies upload, load action, platform badge, and feedback/error notice.
2. Video preview and native controls.
3. Crop enable/reset controls and draggable/resizable crop region.
4. Start/end range controls, selected time display, preview-selection loop, and jump-to-boundary controls.
5. Width/height, speed, FPS, color-count, and dithering controls.
6. GIF generation progress, result preview, and download action.

The input flow remains clear before a video is loaded. Once loaded, the editor follows the source in a vertical sequence. All essential controls remain visible and usable without relying on hover.

## Motion and accessibility details

- Use short, single-run entrances; do not continuously animate the page.
- Motion must not move or resize controls while the user is dragging the crop frame or timeline.
- `prefers-reduced-motion: reduce` disables entrance movement and nonessential transitions while leaving state changes understandable.
- Preserve semantic headings and labels, keyboard operation, visible focus indicators, and adequate foreground/background contrast.
- Keep crop move/resize pointer handling synchronous and unanimated during active pointer capture.

## Responsive behavior

- Wide screens use a readable centered column with the video given the largest visual weight.
- Medium and narrow screens retain the same content order and collapse parameter grids into fewer columns, then one column as needed.
- Do not introduce a persistent sidebar or a fixed two-column editing mode; those options were reviewed and not selected.
- Prevent horizontal overflow for long URLs, buttons, crop controls, and export inputs.

## Implementation scope

- Restyle the existing HTML/CSS and adjust small template copy only where necessary to support the confirmed language and hierarchy.
- Add minimal entrance-state classes/markup only if needed; prefer CSS animations and the existing application event flow.
- Do not add a front-end framework, animation library, external font service, stock photography, decorative media, or new product functionality.
- Preserve the existing crop and timeline JavaScript semantics.

## Verification

- Check changed templates and styles for valid structure and responsive rules.
- Run existing crop/timeline JavaScript tests and Python/API tests to guard against behavior changes.
- Use the local browser to inspect the initial state and a loaded-video/editor state at desktop and narrow viewport widths.
- Verify crop dragging remains responsive; verify result/error visibility states remain legible.
- Check the reduced-motion mode and confirm no nonessential entrance motion is applied.

## Out of scope

- Reproducing Atelier Meridian's exact page, branding, artwork, or copy.
- Rewriting product copy wholesale or translating the application into English.
- Adding filmstrip generation, new video platforms, or new GIF-export behavior.
- Altering the already-implemented P1 crop/export feature semantics.
