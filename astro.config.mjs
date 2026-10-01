import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import fs from "node:fs";
import path from "node:path";
import { SITE } from "./src/config";

// Build a slug -> lastmod map from post frontmatter (date / updated).
const postsDir = new URL("./src/content/posts/", import.meta.url).pathname;
const lastmodBySlug = {};
try {
  for (const f of fs.readdirSync(postsDir)) {
    if (!f.endsWith(".md") || f.startsWith("_")) continue;
    const src = fs.readFileSync(path.join(postsDir, f), "utf8");
    const m = src.match(/^---\n([\s\S]*?)\n---/);
    if (!m) continue;
    const fm = m[1];
    const get = (k) => (fm.match(new RegExp(`^${k}:\\s*(.+)$`, "m")) || [])[1];
    const d = (get("updated") || get("date") || "").trim();
    if (d) lastmodBySlug[f.replace(/\.md$/, "")] = new Date(d).toISOString().split("T")[0];
  }
} catch {
  /* sitemap still builds without lastmod */
}

export default defineConfig({
  site: SITE.url,
  output: "static",
  integrations: [
    sitemap({
      // Draft pages are never rendered, so they never reach the sitemap.
      // Tag pages are thin/noindex and pagination duplicates /blog/ — keep both out.
      filter: (page) =>
        !page.includes("draft") &&
        !/\/tags\//.test(page) &&
        !/\/blog\/\d+\/?$/.test(page),
      serialize(item) {
        const m = item.url.match(/\/blog\/([^/]+)\/?$/);
        const lastmod = m && lastmodBySlug[m[1]];
        return lastmod ? { ...item, lastmod } : item;
      },
    }),
  ],
  markdown: {
    shikiConfig: {
      theme: "github-light",
      wrap: true,
    },
  },
});
