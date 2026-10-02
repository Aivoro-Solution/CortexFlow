// ============================================================
//  SITE CONFIG — change the name / domain / tagline here once
//  and it updates across the whole site.
// ============================================================
export const SITE = {
  name: "CortexFlow",
  tagline: "Free n8n workflow templates, plus practical guides on AI agents and automation",
  description:
    "Free ready-to-import n8n workflow templates — AI agents, chatbots, and automations — plus hands-on tutorials, no fluff.",
  // IMPORTANT: set this to your real domain before deploying.
  // Example: "https://agentcraft.io"
  url: "https://cortexflow.tech",
  author: "CortexFlow",
  authorEmail: "hello@cortexflow.tech",
  language: "en",
  postsPerPage: 10,
  // Google Analytics 4 measurement ID (e.g. "G-XXXXXXXXXX").
  // Empty = analytics disabled.
  gaMeasurementId: "G-1G1441RQKF",
  social: {
    twitter: "@cortexflow",
  },
} as const;

export const CATEGORIES = [
  {
    slug: "ai-agents",
    name: "AI Agents",
    description:
      "Build autonomous AI agents: frameworks, memory, tools, and real projects.",
  },
  {
    slug: "automation",
    name: "Automation",
    description:
      "Workflow automation with n8n, Make, and Zapier — from first workflow to production.",
  },
  {
    slug: "chatbots",
    name: "Chatbots",
    description:
      "Chatbots and RAG: WhatsApp bots, website assistants, and conversational AI.",
  },
  {
    slug: "news",
    name: "News",
    description:
      "AI and automation news: launches, shutdowns, and industry moves that matter.",
  },
] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];
