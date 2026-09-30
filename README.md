# CortexFlow — Static Blog (Astro + Cloudflare Pages)

A fast, fully static English blog about AI agents, workflow automation, and chatbots.
Built with [Astro](https://astro.build) (static output, zero client-side JS frameworks),
styled with hand-written CSS, and ready to deploy on **Cloudflare Pages**.

## Quick start

```bash
cd ~/workspace/blog
npm install        # once
npm run dev        # local dev server at http://localhost:4321
npm run build      # static output goes to ./dist/
```

## Change the site name / domain (one file)

Edit **`src/config.ts`** — everything (header, footer, `<title>` suffix,
meta tags, canonical URLs, sitemap, RSS, robots.txt) reads from here:

```ts
export const SITE = {
  name: "CortexFlow",          // <- site name
  url: "https://cortexflow.tech",  // <- CHANGE to your real domain
  ...
};
```

> **Do this before deploying.** Canonical URLs, the sitemap, and RSS all use
> `SITE.url`. Keep the `https://` and no trailing slash.

## Add a new post

1. Copy the template:
   ```bash
   cp src/content/posts/_template.md src/content/posts/my-new-post-slug.md
   ```
2. Edit the frontmatter (all fields explained in the template):
   - `title`, `description` (≤160 chars — used for Google snippet)
   - `date: YYYY-MM-DD`
   - `category:` one of `ai-agents` | `automation` | `chatbots`
   - `tags:` list of strings
   - `draft: false` to publish (drafts are never built, sitemapped, or in RSS)
3. Write Markdown below the frontmatter.
4. `npm run build` and check `./dist/blog/my-new-post-slug/index.html`.

The post URL is `/blog/<filename-without-.md>/`.

## Deploy to Cloudflare Pages

### Option A — Connect a GitHub repo (recommended, auto-deploys on push)

1. Push this folder to a GitHub repo.
2. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
3. Select the repo. Set:
   - **Framework preset:** `Astro`
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Node version:** 20+ (set env var `NODE_VERSION=20` if needed)
4. Deploy. Every push to `main` rebuilds automatically.

### Option B — Direct upload of `dist/` via Wrangler (no Git)

1. Install Wrangler and log in (one time):
   ```bash
   npm install -g wrangler
   wrangler login
   ```
2. Build and deploy:
   ```bash
   npm run build
   wrangler pages deploy dist --project-name=cortexflow
   ```
   The first deploy creates the `cortexflow` Pages project; later deploys update it.
3. In the Pages project settings, add your custom domain (Cloudflare handles DNS + SSL).

## After deploying

1. **Google Search Console** — add the property, submit `https://YOUR-DOMAIN/sitemap-index.xml`.
2. **Bing Webmaster Tools** — same sitemap.
3. **Replace the placeholder OG image** — `public/og-default.svg` works, but a 1200×630 PNG
   (`public/og-default.png` + update `BaseLayout.astro`) looks better on social shares.
4. **Analytics (optional, privacy-friendly):** Cloudflare Web Analytics (one-click in the
   Pages dashboard) or Plausible — no code changes needed for the former.
5. **Contact form:** the form on `/contact/` currently opens the visitor's email client.
   For a real inbox, point it at Formspree/Getform or add a Pages Function (see the
   HTML comment in `src/pages/contact.astro`).

## Project structure

```
src/
  config.ts               # ← SITE NAME + DOMAIN live here
  content.config.ts       # post schema (frontmatter validation)
  content/posts/          # Markdown posts
    how-to-connect-mcp-server-n8n.md   # first published post
    _template.md          # draft template for new posts
  pages/
    index.astro           # homepage: hero + topic cards + latest posts
    blog/[slug].astro     # individual post pages (JSON-LD Article schema)
    blog/[page].astro     # paginated /blog/ index (page 2+ noindexed)
    blog/index.astro      # /blog/ → redirects to /blog/1/
    categories/[category].astro  # ai-agents / automation / chatbots
    tags/[tag].astro      # auto-generated tag pages
    about.astro  contact.astro
    rss.xml.ts            # /rss.xml feed
    robots.txt.ts         # /robots.txt (sitemap URL auto-matches domain)
  components/             # BaseLayout (all SEO head tags), Header, Footer
  lib/posts.ts            # post helpers (sorting, URLs, dates, slugify)
  styles/global.css       # entire design: light theme, responsive, ~8 KB
public/
  favicon.svg  og-default.svg
```

## SEO checklist (all built in)

- Unique `<title>` + `<meta name="description">` per page (from frontmatter)
- Canonical URLs on every page (pagination page 2+ marked `noindex`)
- Open Graph + Twitter Card tags on every page
- `sitemap-index.xml` (auto-generated), `robots.txt`, `/rss.xml`
- JSON-LD `Article` schema on posts (eligible for rich results)
- Semantic HTML5 (`header`/`main`/`article`/`nav`/`footer`), single H1 per page
- Breadcrumb navigation on posts, categories, tags
- Zero client-side JS — homepage is ~8 KB HTML

## Notes

- `node_modules/` and `dist/` are build artifacts; don't commit them to Git
  (add a `.gitignore` with both if you push to GitHub).
- Cloudflare Pages serves `dist/` as-is — everything here is plain static files,
  so there is nothing that can break at runtime.
