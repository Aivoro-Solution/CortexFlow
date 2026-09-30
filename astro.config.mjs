import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import { SITE } from "./src/config";

export default defineConfig({
  site: SITE.url,
  output: "static",
  integrations: [
    sitemap({
      // Draft pages are never rendered, so they never reach the sitemap.
      filter: (page) => !page.includes("draft"),
    }),
  ],
  markdown: {
    shikiConfig: {
      theme: "github-light",
      wrap: true,
    },
  },
});
