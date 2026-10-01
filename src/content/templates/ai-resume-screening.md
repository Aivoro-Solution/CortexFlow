---
title: "AI Applicant & Resume Screening"
description: "Parse resumes with AI, score candidates against your job description, and rank them in a sheet. Invites stay drafts."
date: 2026-10-01
category: "ai-agents"
difficulty: "intermediate"
workflow: "/templates/ai-resume-screening.json"
integrations: ["Gmail", "OpenAI", "Google Sheets"]
---

## How it works

1. **Gmail Trigger** — watches your inbox and fires on every new application email (you set the filter, e.g. subject contains "application").
2. **Download Resume** — grabs the resume file attached to the email.
3. **Parse Resume with AI** — GPT reads the resume and returns clean structured JSON: name, email, skills, years of experience, and a short summary.
4. **Job Description** — a Set node that holds your job posting. Paste your JD here once; every candidate is scored against it.
5. **Score Candidate** — GPT compares the parsed resume against your job description and returns a 0-100 score plus strengths and risks.
6. **Normalize Result** — tidies the AI output into clean fields: name, email, score, summary, strengths, risks.
7. **Append to Sheet** — adds one ranked row per candidate to your Google Sheet, highest scores on top if you sort by the score column.
8. **High Score?** — an IF node that only continues when the score is 80 or above.
9. **Create Interview Draft** — Gmail creates a DRAFT interview invite. A human reviews and sends every invite — the workflow never emails anyone automatically.

## Set up steps

You'll need:

- n8n (self-hosted or cloud) with Google OAuth access
- A Gmail account — you connect it via OAuth inside n8n, no app passwords needed
- An OpenAI account — get an API key at platform.openai.com → API keys
- A Google account with a spreadsheet — columns: name, email, score, summary, strengths, risks

1. **Download the workflow JSON** using the download button on this page.
2. In n8n, go to *Workflows → ⋯ → Import from file* and select the JSON.
3. **Connect Gmail** — go to *Credentials → New → Gmail OAuth2 API*, sign in with Google, save. Then open *Gmail Trigger* and *Download Resume* and select this credential.
4. **Connect OpenAI** — go to *Credentials → New → OpenAI*, paste your API key, save. Then open *Parse Resume with AI* and *Score Candidate* and select it.
5. **Connect Google Sheets** — go to *Credentials → New → Google Sheets OAuth2 API*, sign in, save. Then open *Append to Sheet*, select the credential, and pick your spreadsheet and tab.
6. **Paste your job description** — open the *Job Description* Set node and replace the placeholder text with your full job posting.
7. **Set the inbox filter** — open *Gmail Trigger* and add a filter (e.g. subject contains "application") so it only fires on application emails.
8. **Activate** the workflow (toggle, top-right), then send yourself a test application email.

## Customize it

- **Change the score threshold** — open *High Score?* and edit the 80 cutoff up or down.
- **Change the model** — open either AI node and swap `gpt-4o-mini` for `gpt-4o` or any other model.
- **Change the invite text** — edit the subject and message in *Create Interview Draft*. It stays a draft until you personally send it.
- **PDF resumes** — add an *Extract from File* node between *Download Resume* and *Parse Resume with AI*, and point the parsing prompt at its extracted text.
- **Score weighting** — edit the system prompt in *Score Candidate* to weigh skills, experience, or education differently.
