# GitHub Header Link Design

## Goal

Give users a direct path from the ClipGIF interface to its GitHub repository.

## Design

Replace the top-right “仅在本机处理” badge with a GitHub icon-only link to `https://github.com/SOMWHY/clipGIF/tree/main`. Use an inline SVG so no icon package or remote asset is needed. Keep the control compact and consistent with the existing ink, fine-border, and olive hover palette. Open the external repository in a new tab with `rel="noopener noreferrer"`, and provide an accessible name and visible keyboard-focus treatment.

## Scope and validation

Change only the top navigation in `app/templates/index.html` and its styles in `app/static/style.css`. Preserve unrelated existing edits. Verify the rendered link destination, accessible name, focus/hover styling, and fit at desktop and narrow viewport widths.
