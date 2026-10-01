---
title: "RAG Chatbot over Company Documents"
description: "Chat with your company docs: retrieval-augmented answers grounded in your knowledge base, with a doc-ingestion flow included."
date: 2026-10-01
category: "chatbots"
difficulty: "advanced"
workflow: "/templates/rag-chatbot-company-documents.json"
integrations: ["OpenAI", "Qdrant"]
---

## How it works

The workflow has two separate chains: one answers questions, the other loads documents into the knowledge base.

Answer chain:

1. **Chat Trigger starts the conversation** — the n8n chat UI sends the user's question into the workflow.
2. **Embed Question creates a vector** — the question is turned into an embedding through the OpenAI embeddings API.
3. **Search Vector DB retrieves chunks** — the vector is searched against your vector database, returning the most relevant document chunks.
4. **Build Context formats the evidence** — the retrieved chunks and the original question are assembled into clean fields for the agent.
5. **Answer from Docs (AI agent) answers** — GPT answers using ONLY the retrieved context. If the answer is not in the context, it says so instead of guessing.

Ingestion chain (unconnected — runs separately):

6. **Ingest Webhook Trigger receives a document** — POST document text (with an ID) to this webhook.
7. **Prepare Document normalizes it** — trims the text and passes the document ID through (auto-generated if missing).
8. **Embed Document creates a vector** — the document text is embedded with the same model used for questions.
9. **Upsert to Vector DB stores it** — the vector plus the original text lands in your `docs` collection, ready for retrieval.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with webhook access
- An OpenAI account — get an API key at platform.openai.com → API keys
- A vector database (Qdrant, Pinecone, or similar) — create a collection named `docs` and get an API key plus your API URL

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Create your OpenAI credentials** — in n8n go to *Credentials → New → OpenAI*, paste your API key, save, and select it in *OpenAI Chat Model*. Then go to *Credentials → New → Header Auth*, add a header named `Authorization` with the value `Bearer YOUR_OPENAI_API_KEY`, save, and select it in *Embed Question* and *Embed Document*.
4. **Connect your vector database** — in n8n go to *Credentials → New → Header Auth*, add your vector DB's auth header, save, and select it in *Search Vector DB* and *Upsert to Vector DB*. Replace both placeholder URLs (`https://your-vector-db.com/...`) with your real endpoints.
5. **Ingest your docs** — POST each document to the *Ingest Webhook Trigger* URL as `{"doc_id": "handbook-1", "doc_text": "..."}`. For one-off pastes, you can replace the trigger with a Manual Trigger.
6. **Activate** the workflow (toggle, top-right), open the chat from the *Chat Trigger* node, and ask a question about your docs.

Note: *Search Vector DB* and *Build Context* expect Qdrant-style results (`results[].payload.text`). If your provider returns a different shape, adjust the expression in *Build Context*.

## Customize it

- **Swap the embedding model** — change `text-embedding-3-small` in *Embed Question* and *Embed Document* (keep both identical).
- **Tune retrieval** — raise `limit` in *Search Vector DB* for more context per answer, or lower it for faster responses.
- **Ground harder** — edit the system prompt in *Answer from Docs* to require citations from specific chunks.
- **Scheduled ingestion** — replace *Ingest Webhook Trigger* with a Schedule Trigger that pulls documents from Google Drive, Notion, or your CMS on a cadence.
- **Chunk long documents** — add a Code node after *Prepare Document* to split long texts into overlapping chunks before embedding.
