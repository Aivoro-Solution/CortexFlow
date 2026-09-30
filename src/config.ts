// ============================================================
//  SITE CONFIG — change the name / domain / tagline here once
//  and it updates across the whole site.
// ============================================================
export const SITE = {
  name: "CortexFlow",
  tagline: "Practical guides on AI agents, automation, and chatbots",
  description:
    "CortexFlow is a hands-on blog about AI agents, workflow automation, and chatbots. Step-by-step tutorials, honest tool comparisons, and real-world builds — no fluff.",
  // IMPORTANT: set this to your real domain before deploying.
  // Example: "https://agentcraft.io"
  url: "https://cortexflow.tech",
  author: "CortexFlow",
  authorEmail: "hello@cortexflow.tech",
  language: "en",
  postsPerPage: 10,
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
] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];
