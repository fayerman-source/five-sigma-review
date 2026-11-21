# Gemini 4 NYC Hackathon — Sat Nov 21, 2026 (The Malin, 220 W 26th St)

You are helping Eli (NYC attorney, ex-Thomson Reuters programmer) build a hackathon project TODAY.
Teammate (likely): Rahul (AI engineer; built a legal citation verifier; likes pre-registered evals, fail-closed verification). Possibly a third person.

## Hard deadlines
- Hacking started 10:45. **Submissions due 5:00 PM** (form: https://cerebralvalley.ai/e/gemini-4-nyc/hackathon/submit).
- Submission needs: PUBLIC GitHub repo, a **1-minute demo video**, all teammates added. Record the video by ~4:30.
- Judging round 1: 5:00–6:45 (3 min live demo + 2 min Q&A). Final (top 6): 7:00–8:00. Winners 8:15.

## Rules (from the participant guide)
- **New work only.** Repo created today; demo shows only what was built today. Do NOT copy any of Eli's existing code (LocalPass, DISCO tool, enron-proto) and NEVER use client or confidential material. Public data only.
- Use **at least two Gemini 4 models** (Argon, Carbon, Neon, Hydrogen), **each with a clear job**.
- Must go beyond a text box: documents / images / audio / video central to how it works.
- Banned: text-only chatbots, demos only on scripted inputs, evals made only of examples the team wrote to pass, basic RAG, Streamlit apps, dashboard as the main feature, image analyzers, medical advice, AI job screeners, sports coaches, etc.
- Teams of 1–4. Registration included a broad Google rights waiver: keep proprietary ideas/code out.

## Track: Problem Statement One — "5 Sigma"
Pick a real task agents struggle with, build a Gemini 4 system that does it reliably, and PROVE it: an evaluation on inputs you didn't prepare for, compared with a simple baseline (single model call / existing tool / how people do it today). Show where it still fails and what you changed.
Their own example: "an agent that fills out messy real-world forms (scanned PDFs, handwritten notes), tested on 50 documents it has never seen, with an accuracy score against a single-model baseline."

## Judging
Live demo on real unrehearsed inputs 35% · Proof it works (baseline, honest failures) 25% · Creativity 20% · Gemini 4 & Decisions API use 20%.
Prizes: $7,500 / $5,000 / $2,500; Best use of Managed Agents $5,000; Shopify $2,500 Shop Cash.

## Project idea (Eli's domain)
First-pass legal document review on messy PUBLIC documents (e.g. Enron emails with attachments, SEC filings, scanned exhibits): responsiveness, issue tags, privilege flags, each call backed by an exact quote that code verifies.
- Model A (e.g. a vision-strong model) reads scanned/PDF/image pages into text + layout.
- Model B makes the coding call with quotes; code checks every quote exists verbatim (fail-closed).
- Optional: Decisions API / Managed Agents for the review loop (ask Google staff what Decisions API does; it counts in judging).
- Baseline: one single Gemini call on the raw document.
- Eval: ~50 held-out public documents labelled by Eli (the attorney) BEFORE seeing model output; accuracy table + failure slide.
- Demo: judges hand in a new document (upload), it codes it live with verified quotes.
Keep scope small. Pitch order: problem → baseline → score → where it fails.

## Access
Gemini 4 hackathon credentials: email "[NYC Hackathon] Gemini 4 Access Credentials" from Thor (Google DeepMind) in fayerman@gmail.com. Sign in at ai.dev in an INCOGNITO window. Never commit keys; use a .env that is gitignored.
Wi-Fi: Hackathon / hackathon. Discord: Cerebral Valley server, Gemini 4 NYC section (#announcements, #questions, #google-deepmind).

## Working style
Eli wants brief answers, all next steps at once, scripts tested end to end before handing them over.
