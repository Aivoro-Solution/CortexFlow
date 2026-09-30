# CortexFlow redesign — design notes (2026-09-30)

## Concept: "The Workflow Canvas"
Visual language drawn from node-based automation canvases (n8n-style dotted
grid, connector lines, node glyphs) crossed with a precise lab notebook.
Readers build workflows daily — the canvas IS their world, so the design
speaks their vernacular instead of generic SaaS.

## Tokens
- --paper #FAFAF7 (page) / --paper-raised #FFFFFF
- --ink #15151A (text) / --ink-deep #0C0C10 (dark bands, code)
- --muted #5C5C66 / --faint #8B8B95 / --line #E8E8E0
- --signal #FF4D00 (graphic accents only) / --signal-deep #B53A00 (text-safe) / --signal-soft #FFF1E8

## Type
- Display: Space Grotesk (headlines, wordmark, row titles)
- Body: IBM Plex Sans (prose, UI)
- Code: system mono stack (code only — never as decorative labels)

## Layout
- Left-aligned everywhere; generous whitespace. No centered gradient hero.
- Homepage: ink hero band with dotted grid + animated node chain
  (trigger → agent → tools → output); editorial index rows for latest posts;
  three category panels with custom line SVG icons; quiet RSS strip.
- Post: refined measure (740px), ink code blocks, signal-ruled blockquotes.
- Footer: ink band.

## Principles
- One memorable element: the animated node chain. Everything else quiet.
- No card-kit, no gradient washes, no pill CTAs, no ALL-CAPS eyebrows,
  no "A · B · C" meta strings, no arrows appended to links.
- Motion: single load-draw of the chain connectors; prefers-reduced-motion
  respected. No scroll fade-ups.

## Deliberate deviations from the skill's tell-list (all brief-grounded)
- Monospace used for code only (a code-tutorial blog — authentic, not chrome).
- Hairline rules used in the post index (an index, not a newspaper pastiche).
- Dotted grid (direct quote of the n8n canvas, the subject's own medium).
