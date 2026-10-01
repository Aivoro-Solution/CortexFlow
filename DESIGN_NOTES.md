# CortexFlow redesign — design notes (2026-10-01, BRUTAL)

## Concept: "D · Brutal" (neo-brutalism)
Lalit rejected the Schematic/REV D engineering look on 2026-10-01 ("mujhe
website ka user interface pasand nahi aa raha") and picked **D · Brutal**
from six prepared concepts (A Terminal, B Studio, C Bento, D Brutal,
E Mono, F Ember). Concept reference: `tools/redesign-concepts-v2/concepts.html`
(`#concept-d`).

Visual language: loud, raw, confident. Cream paper, everything boxed in
3px ink borders with hard offset shadows, giant Archivo Black headlines,
rotated sticker badges, primary accents (orange/yellow/blue) doing the
heavy lifting. No gradients, no glassmorphism, no soft shadows, radius
0–2px everywhere.

## Tokens
- --cream #FFFDF5 (page bg) / --paper #FFFFFF (cards) / --wash #F4F1E6
- --ink #111111 (text, borders, shadows)
- --orange #FF4D00 (primary CTAs, starburst) / --yellow #FFD02F (highlights, stickers, step 1) / --blue #2F6BFF (stickers, step 3, blog strip)
- --muted #4A4A44 / --faint #8A8778 (secondary text only)

## Type
- Display: Archivo Black (headlines, wordmark, buttons, stickers) — always
  uppercase for hero/section titles
- Body: Archivo (headlines fallback) / Inter 400–600
- Labels: IBM Plex Mono (kickers, meta, tags, captions, breadcrumbs)

## Signature elements
- Header: sticky, logo as yellow sticker box (Orbit C mark kept), nav
  links as bordered buttons, active = orange.
- Homepage hero: giant Archivo Black headline with `.hl-y` (yellow) and
  `.hl-o` (orange) rotated highlight boxes; rotated stickers "100% FREE!"
  and "★ New drop" (hidden on mobile); chunky CTA buttons with press-down
  `:active` (translate 4px, shadow to 0).
- Template cards: 2-col `.tpl-grid` panels, LIVE starburst (CSS clip-path)
  on featured template, `tpl-tag` chips (yellow LIVE / blue difficulty /
  dashed ghost), orange `↓ JSON` download button.
- How-it-works: 3 `.step` panels — yellow / white / blue.
- Blog strip: blue `.rss-strip` panel with white text, yellow kicker.
- Blog home: category `.track` cards cycle yellow/white/blue/orange;
  post rows = `.spec` panels with yellow number cell.
- Article pages: kicker chip (yellow sticker), brutalist title, 3px framed
  post-hero (animated SVG / Lottie / webp logic untouched, selectors
  unchanged), orange-square h2 markers, yellow blockquotes, 3px table/code
  frames, black footer.
- Footer: solid black (`--ink`) with cream text, yellow highlights, yellow
  newsletter strip on top.

## Motion
- Minimal: hover lifts (translate -2px, shadow grows), button press
  effect. prefers-reduced-motion respected globally.

## Preserved (untouched by redesign)
- All URLs/slugs/routing, JSON-LD, canonical tags, meta descriptions,
  sitemap/RSS generation, GA + AdSense snippets, newsletter JS + KV flow,
  article hero system (animated SVG SMIL / Lottie / webp), hello@cortexflow.tech.
