---
title: "RAG Chatbot — Google Drive + Gemini + Pinecone"
description: "Chat with your company docs: Google Drive auto-ingests files into Pinecone, Gemini answers with citations. Import-ready n8n workflow."
date: 2026-10-02
category: "ai-agents"
difficulty: "intermediate"
workflow: "/templates/rag-chatbot-drive-gemini-pinecone.json"
integrations: ["Google Drive", "Google Gemini", "Pinecone"]
---

## How it works

This workflow has two branches that run independently:

**Ingestion branch — documents → vector store:**

1. **Google Drive triggers watch your folder** — one fires when a file is created, the other when a file is updated (both poll every minute).
2. **The file is downloaded** from Google Drive with its original name preserved.
3. **Text is extracted, split, and embedded** — a binary data loader reads the file, a recursive character text splitter chunks it (100-character overlap), and Google's `text-embedding-004` model turns each chunk into a vector.
4. **Chunks are inserted into Pinecone** — your vector index stays in sync with the Drive folder automatically.

**Chat branch — questions → answers:**

1. **Chat trigger receives the message** — use n8n's built-in chat widget or connect any chat frontend.
2. **The AI Agent answers** — it runs on `gemini-2.0-flash-exp` with a system prompt that makes it a helpful HR assistant for company policies.
3. **Retrieval happens through a tool** — the agent calls `company_documents_tool`, which searches Pinecone for relevant chunks and feeds them back as context.
4. **Honest fallback** — if the answer isn't in the documents, the agent replies "I cannot find the answer in the available resources." instead of hallucinating.
5. **Window Buffer Memory** keeps the conversation context so follow-up questions work naturally.

## Set up steps

You'll need:

- A Google Cloud project with the **Vertex AI API** enabled
- A Google AI API key — get one at [Google AI Studio](https://aistudio.google.com) → Get API key
- A Pinecone account — [pinecone.io](https://www.pinecone.io), free tier works; create an index with **768 dimensions** (matches `text-embedding-004`) and cosine metric
- A Google Drive folder containing your company documents (PDF, DOCX, TXT)

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Google Drive** — *Credentials → New → Google Drive OAuth2*, sign in with Google, and save. Select it in *Google Drive File Created*, *Google Drive File Updated*, and *Download File From Google Drive*. Then open both trigger nodes and pick your documents folder in *Folder to Watch*.
4. **Google AI (PaLM API)** — *Credentials → New → Google PaLM API*, paste your Google AI Studio API key, and save. Select it in *Embeddings Google Gemini*, *Google Gemini Chat Model*, and both *(retrieval)* variants.
5. **Pinecone** — *Credentials → New → Pinecone*, paste your Pinecone API key, and save. Select it in *Pinecone Vector Store* and *Pinecone Vector Store (Retrieval)*, then pick your index in both nodes.
6. **Activate** the workflow, drop a document into the Drive folder, wait a minute, then ask a question in the chat.

## Customize it

- **Chunk size and overlap** — open *Recursive Character Text Splitter* and tune `chunkSize` / `chunkOverlap` for long vs. short documents.
- **Different models** — swap `models/text-embedding-004` for another embedding model (match your Pinecone index dimensions!) or `models/gemini-2.0-flash-exp` for a different Gemini chat model.
- **System prompt** — edit the system message in the *AI Agent* node to change its role, tone, or fallback behavior.
- **More triggers** — the ingestion branch also works with a *Schedule Trigger* that sweeps the whole folder nightly, or add a *Google Drive Trigger* on `fileDeleted` plus a Pinecone delete step.
- **Richer answers** — raise the retrieval *Top K* / add a score threshold in the *Vector Store Tool* node to control how many chunks the agent sees.
