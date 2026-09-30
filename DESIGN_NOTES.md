# CortexFlow redesign — design notes (2026-09-30, REV D)

## Concept: "Schematic"
Visual language drawn from engineering drawings and spec sheets: white
drawing sheets on a fine grid, 2px ink rules, mono annotations, corner
registration ticks, title blocks, FIG. references, and one signal-orange
accent used only where the eye should land. The reader is an engineer —
the site looks like the documents engineers already trust.

User picked concept C from three prepared options (A Editorial Ink,
B Midnight Dispatch, C Schematic) on 2026-09-30.

## Tokens
- --paper #FFFFFF / --wash #F4F5F7 (grid + fills) / --sheet-tint #FAFAF7
- --ink #16181D (text, rules) / --muted #5B6470 / --faint #9AA2AE / --line #DDE1E7
- --orange #FF4D00 (signal accents: hovers, markers, key lines)
- --blue #3E5C82 (annotation blue: category/spec tags)

## Type
- Display: Archivo 500–800 (headlines, wordmark, spec titles)
- Body: Inter 400–600
- Annotations + code: IBM Plex Mono (sheet numbers, meta, tags, captions)

## Signature elements (one bold thing, rest disciplined)
- Homepage hero = engineering title block: corner ticks, DWG NO. CF-HOME-001,
  meta column (Drawn / Checked / Subject / Status), footer strip
  (TOLERANCE: ZERO FLUFF / UNITS: TUTORIALS / DO NOT SCALE DRAWING).
- Article list = spec-sheet rows with part numbers (001…), dashed
  category tags, hover = orange-soft wash.
- Category cards = FIG. 001–004 engineering figures, hover lifts with
  orange offset shadow (only playful moment on the page).
- Article pages: DWG NO. line per post, mono byline, post-hero mounted in
  a 2px "drawing sheet" frame with FIG. caption (Lottie animations and
  webp fallbacks mount inside the same frame, unchanged behavior).
- Footer: white, 2px ink top rule, mono annotations.

## Motion
- Minimal: hover states only (spec-row wash, track-card lift).
- Lottie article heroes unchanged (4s slow loops, reduced-motion → webp).
- prefers-reduced-motion respected globally.

## Identity (unchanged)
- Logo: C · Orbit C (open C ring + orange signal dot).
- Article OG/webp heroes: Workflow Canvas style (paper/ink/orange, no text)
  — blends with the white schematic sheets; kept as-is.
- Favicon + og-default.svg regenerated in schematic style.
