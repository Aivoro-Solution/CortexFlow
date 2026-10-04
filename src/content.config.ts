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

const templates = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/templates" }),
  schema: z.object({
    title: z.string(),
    description: z.string().max(160, "Keep meta descriptions under 160 chars"),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    category: z.enum(["ai-agents", "automation", "chatbots"]),
    difficulty: z.enum(["beginner", "intermediate", "advanced"]).default("beginner"),
    // Path to the downloadable n8n workflow JSON in /public, e.g. "/templates/telegram-ai-assistant.json"
    workflow: z.string(),
    integrations: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

const comparisons = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/comparisons" }),
  schema: z.object({
    title: z.string(),
    description: z.string().max(160, "Keep meta descriptions under 160 chars"),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    tool_a: z.string(),
    tool_b: z.string(),
    // One-paragraph verdict shown in the callout box
    verdict: z.string(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { posts, templates, comparisons };
