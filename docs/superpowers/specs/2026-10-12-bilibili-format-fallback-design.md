# Bilibili Format Fallback Design

## Problem

The Bilibili adapter only selects video formats at 480p or below. Public probing
showed that `BV1cgpg6dEsB` exposes 640p and 854p formats but no format at or below
480p, while `BV1ovpE66Es8` exposes a 480p format. The first video therefore fails
format selection before download; this does not establish a Cookie-authentication
problem.

## Design

Keep the current preference for a 480p-or-lower source when available. Add an
ordered yt-dlp fallback to the best available video/audio combination or merged
format when no such low-resolution format exists. Apply this change only to the
Bilibili adapter; leave other platform defaults unchanged.

The existing 200 MB source-download limit remains in force. Existing preview and
GIF processing continue to scale output to at most 480 pixels high/wide according
to their current behavior, so the fallback affects source selection, not the
output-size policy.

## Validation

- Unit-test that the Bilibili selector keeps the low-resolution preference and
  includes an unrestricted fallback.
- Use yt-dlp metadata-only extraction against the two public reproductions to
  verify the previously failing video selects an available format and the
  previously working video still selects a format at or below 480p.
- Run the focused downloader/platform tests.

## Out of Scope

- Changing Cookie handling, prompting for Cookie contents, or logging Cookie data.
- Changing the 200 MB source limit, preview scaling, or GIF dimensions.
- Altering selectors for non-Bilibili platforms.
