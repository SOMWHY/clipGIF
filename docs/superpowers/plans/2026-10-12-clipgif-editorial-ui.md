# ClipGIF Meridian Editorial UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle ClipGIF as a warm, editorial gallery-inspired video-to-GIF workspace while preserving every existing workflow and P1 control.

**Architecture:** Keep the existing single-page HTML and vanilla CSS/JavaScript architecture. Rework visual tokens, component styles, and small semantic template details in place; add only minimal state classes for one-shot entrance/result motion. Preserve all current element IDs, crop/timeline event semantics, API contracts, and loading/error flows.

**Tech Stack:** FastAPI/Jinja templates, HTML, CSS, vanilla JavaScript, pytest, Node built-in test runner, integrated browser.

**Spec:** `docs/superpowers/specs/2026-10-12-clipgif-editorial-ui-design.md`

## Global Constraints

- Use warm paper/off-white, deep ink, muted moss/olive, and restrained sand/stone neutrals.
- Use an editorial serif treatment for the Chinese hero title, with locally available/system fallbacks; use sans-serif for controls and body; add no remote font dependency.
- Keep Chinese as the primary language; English may appear only as small eyebrow/step decoration and must not carry required instructions.
- Keep the page in a vertical editorial flow, with the video as the primary visual; collapse to one column on narrow screens.
- Replace glassy gradients, glow, heavy shadows, and oversized rounded panels with whitespace, thin rules, light borders, and restrained corners.
- Use only short, single-run entrance/result motion and subtle hover feedback; crop/timeline pointer interactions must remain immediate.
- Honor `prefers-reduced-motion: reduce`; do not add looping animation, autoplay, a UI framework, an animation library, or external fonts.
- Preserve all existing UI IDs, crop/timeline behavior, backend/API behavior, export defaults, and task flows.

## Review Focus

- **Long Bilibili URLs and narrow viewports:** input, upload help, buttons, and parameter fields must not cause horizontal overflow; verify at 320 px and 390 px widths.
- **Crop overlay stacking and pointer interaction on warm surfaces:** video/crop contrast must remain clear, and crop move/resize must remain responsive with no animated transforms on the active overlay; browser-check actual pointer drags.
- **Native video controls and timeline range thumbs:** controls must retain contrast and remain reachable/usable on the light theme; verify keyboard focus and range-thumb visibility.
- **Loading, success, and error feedback:** all status text must remain readable and distinguishable without color alone; inspect ready, error, and result states in browser.
- **Reduced motion and dynamic editor/result visibility:** entrance animation must not replay unexpectedly when editor visibility changes, and reduce-motion must suppress all nonessential movement; verify both media modes.

---

### Task 1: Establish editorial page structure and copy hierarchy

**Files:**
- Modify: `app/templates/index.html`
- Test: existing UI behavior through `tests/test_api.py`, `tests/test_crop.js`, and browser checks

**Interfaces:**
- Consumes: current Jinja page, all existing DOM IDs consumed by `app/static/app.js` and `app/static/crop.js`.
- Produces: same functional controls in a semantic, vertical source → video/edit → export/result flow; any new classes are presentation-only and do not replace IDs.

- [x] **Step 1: Record and protect functional selectors**

  Before editing markup, capture the IDs used by the browser scripts:

  ```powershell
  Set-Location D:\web_dev_projects\clipGIF
  rg -o '#[A-Za-z][A-Za-z0-9_-]*' app\static\app.js app\static\crop.js app\static\timeline.js
  ```

  Preserve every template element whose ID is consumed by those scripts.

- [x] **Step 2: Refine only the visible editorial hierarchy**

  In `index.html`, keep all source, cookie, crop, range, export, result, and notice controls. Adjust the hero/supporting copy to concise Chinese-first editorial wording with only a small English eyebrow. Keep existing Chinese labels as the instructions. Set `meta[name="theme-color"]` to the warm paper page color and add version queries to the changed stylesheet and application script URLs so a browser reuses the new visual system and reduced-motion behavior rather than cached assets. Add semantic class hooks for hero/source/editor/result entrance states only if needed; do not add inline behavior.

- [x] **Step 3: Check structure and selector continuity**

  Run:

  ```powershell
  & .\.venv\Scripts\python.exe -m pytest tests\test_api.py -q
  node --test tests\test_crop.js tests\test_timeline.js
  ```

  Expected: existing API and interaction tests pass; page still renders with all controls.

- [x] **Step 4: Inspect initial and loaded-editor markup**

  Use the local browser at desktop width to inspect the unloaded page, then load a video and confirm the editor appears in source/video/timeline/export order. Confirm crop and export IDs remain present and existing controls are not hidden or reordered out of the intended workflow.

### Task 2: Replace the dark visual system with the Meridian editorial theme

**Files:**
- Modify: `app/static/style.css`

**Interfaces:**
- Consumes: existing semantic classes and crop/timeline DOM hooks from `index.html`.
- Produces: responsive warm-paper editorial styling for the full application while keeping functional layout and crop-overlay geometry intact.

- [x] **Step 1: Replace dark tokens and page chrome**

  Define CSS variables for paper/off-white surfaces, ink text, olive accent, sand/stone border, and muted secondary text. Apply the warm background without radial gradients. Restyle topbar, wordmark, local-processing badge, hero, and section headings using generous whitespace and thin rules. Use a Chinese serif-capable local fallback stack for `.intro h1`; retain a readable sans-serif stack for controls and body text.

- [x] **Step 2: Restyle source and editor surfaces**

  Replace gradient panels, glow, heavy shadows, and large radii with transparent/editorial sections, pale inset input fields, subtle borders, and compact restrained corners. Restyle crop controls, timeline track/thumbs, native video frame, badges, export grid, notices, result frame, and download button against the light palette. Ensure crop overlay stays positioned above the video and its dimming mask remains visible against both light and dark video frames.

- [x] **Step 3: Add responsive layout rules**

  Keep the centered vertical flow on wide screens. Collapse `.export-options` from three columns to two and then one at appropriate breakpoints; stack source input/button when needed; allow crop instructions, timeline actions, result header, and footer to wrap. Explicitly use `min-width: 0`, `overflow-wrap: anywhere` where appropriate, and bounded media widths to prevent long-URL overflow.

- [x] **Step 4: Verify selectors and responsive CSS**

  Run:

  ```powershell
  node --test tests\test_crop.js tests\test_timeline.js
  & .\.venv\Scripts\python.exe -m pytest tests\test_api.py -q
  ```

  In browser, inspect 1280 px, 768 px, 390 px, and 320 px widths. Expected: no horizontal page overflow; labels and controls remain legible and reachable; crop handles remain visible and aligned to the video.

### Task 3: Add restrained entrance and result motion with accessibility support

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/style.css`
- Modify: `app/static/app.js` to apply one-time editor entrance state, retrigger result reveal, and respect reduced motion when scrolling to a result
- Test: `tests/test_crop.js`, `tests/test_timeline.js`, API regression tests, and browser reduced-motion checks

**Interfaces:**
- Consumes: semantic entrance hooks from Task 1 and the existing result lifecycle (`resultPanel.hidden` becomes false after successful GIF task completion).
- Produces: one-shot hero/source/editor entrance, brief result reveal on every generated GIF, and subtle button hover; no changes to crop/timeline geometry or API state.

- [x] **Step 1: Define the initial entrance and a non-motion baseline**

  Ensure all content is fully visible and controls are usable without animation. Add CSS keyframes for a short opacity/translate entrance (maximum vertical offset 8 px, duration at most 650 ms) on the initially visible hero and source section. Add an `.editor-entering` hook for the first successfully revealed editor only, and a shorter result fade. Never animate `.crop-box`, `.crop-overlay`, range inputs, or video geometry.

- [x] **Step 2: Wire one-time editor entry and repeatable result reveal**

  In `app.js`, add `.editor-entering` only on the first successful transition to `editor.hidden = false`; remove it on `animationend` and do not add it on later source loads. On each successful GIF result, unhide `resultPanel` immediately, then add `.result-entering` on the next animation frame so a new export retriggers the reveal; remove the class on `animationend`. Do not delay result visibility or change task polling. When scrolling to the result, use `behavior: "auto"` if `matchMedia("(prefers-reduced-motion: reduce)").matches`, otherwise preserve the existing smooth scroll.

- [x] **Step 3: Add hover/focus and reduced-motion rules**

  Limit enabled-button hover lift to 1–2 px with a short transition. Add explicit `:focus-visible` treatment for buttons, links, selects, and inputs. Under `@media (prefers-reduced-motion: reduce)`, disable entrance/result animations and nonessential transitions; do not add the editor/result entry classes while reduced motion is enabled, and preserve immediate visual state changes.

- [x] **Step 4: Verify motion and interaction**

  Run:

  ```powershell
  node --test tests\test_crop.js tests\test_timeline.js
  & .\.venv\Scripts\python.exe -m pytest tests\test_api.py -q
  ```

  In browser, observe first page load, first and subsequent editor reveals, and first and subsequent result reveals. Enable reduced motion through browser emulation and reload; verify there is no entrance or smooth-scroll motion. Drag/resize the crop box and timeline thumbs. Expected: no repeated editor entrance on source changes, each new GIF receives one short reveal when motion is allowed, and no drag lag.

### Task 4: Full regression and visual acceptance

**Files:**
- Modify if needed: `app/templates/index.html`, `app/static/style.css`, `app/static/app.js`
- Test: all existing Python tests, both JavaScript test files, and browser acceptance

**Interfaces:**
- Consumes: completed design system and motion rules from Tasks 1–3.
- Produces: verified redesigned UI with existing local video-to-GIF behavior intact.

- [x] **Step 1: Run all automated regression suites**

  ```powershell
  Set-Location D:\web_dev_projects\clipGIF
  & .\.venv\Scripts\python.exe -m pytest -q
  node --test tests\test_crop.js tests\test_timeline.js
  node --check app\static\app.js
  node --check app\static\crop.js
  ```

  Expected: all Python and JavaScript tests pass and both browser scripts parse successfully.

- [x] **Step 2: Verify user-facing states in the local browser**

  Check unloaded state, loaded-video editor, active crop overlay, export settings, a successful GIF result, and a visible error notice. Verify the same workflow remains understandable at desktop and 320–390 px widths.

- [x] **Step 3: Verify design/accessibility acceptance**

  Confirm warm paper/ink/olive palette, serif hero with sans-serif controls, Chinese-first copy, vertical flow, thin rules/quiet surfaces, visible focus, no horizontal overflow, reduced-motion behavior, and immediate crop/timeline pointer interaction.

- [x] **Step 4: Review final diff**

  ```powershell
  git diff --check
  git status --short
  ```

  Confirm only the template, style, and any justified presentation-only JavaScript change are in scope; no dependency, API, download, or encoding behavior changed.
