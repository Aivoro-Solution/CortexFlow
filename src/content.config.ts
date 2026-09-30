import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const posts = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/posts" }),
  schema: z.object({
    title: z.string(),
    description: z.string().max(160, "Keep meta descriptions under 160 chars"),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    category: z.enum(["ai-agents", "automation", "chatbots", "news"]),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
    featured: z.boolean().default(false),
    author: z.string().default("CortexFlow"),
    // Optional path to an OG/social image in /public, e.g. "/og/mcp-n8n.png"
    image: z.string().optional(),
  }),
});

export const collections = { posts };
