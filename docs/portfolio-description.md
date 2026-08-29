# Kora — Portfolio Description

## CV version

- **Kora — AI due-diligence copilot for investment analysts.** Designed and built an end-to-end product (FastAPI + PostgreSQL/pgvector backend, Next.js 15 frontend) that turns uploaded pitch decks and financial documents into cited, structured due-diligence profiles: AI extraction with source citations, a separate deterministic validation engine (200+ unit tests), coverage-gated investment scoring, and retrieval-augmented chat with citations.
- Architected the data model and pipeline around traceability and honest uncertainty — every AI-extracted fact carries a source citation, findings distinguish document-stated facts from AI inferences from deterministic checks, and the investment score is withheld (not fabricated) when evidence is insufficient.
- Owned the full stack solo: schema design and migrations, the FastAPI service layer, LLM integration (OpenRouter) for extraction/embeddings/chat, and a custom React/Tailwind design system for the frontend.

## Portfolio version

Kora is an AI-powered due-diligence copilot that turns a company's pitch deck or financial documents into a structured, evidence-backed profile — extracting financial and qualitative facts with source citations, running deterministic checks for internal inconsistencies, scoring how complete the evidence is, and computing an investment score it deliberately withholds when that evidence is too thin. Analysts can then ask follow-up questions in a citation-grounded AI chat and export the whole analysis as a due-diligence report. It's a full-stack, independently built product — FastAPI/PostgreSQL/pgvector backend, an LLM pipeline routed through OpenRouter, and a Next.js frontend with a custom design system — built to explore how to make an AI product's output genuinely trustworthy, not just fluent.

## Interview version

*(~60 seconds, written to be spoken)*

"Kora is a due-diligence tool I built for early-stage investment analysts — the people who have to read through a stack of pitch decks and financial documents and figure out which ones are actually worth digging into.

The core idea is: an analyst uploads a document, and Kora extracts the financial and qualitative facts using an LLM — but every single fact is tied back to a citation, the actual passage it came from, so nothing is a black-box number. Then, separately, I built a deterministic validation engine — plain rule-based checks, no LLM involved — that catches internal inconsistencies, like a stated LTV-to-CAC ratio that doesn't actually match the underlying numbers, or a runway claim with no cash or burn rate to back it up. I kept that step deterministic on purpose, because I didn't want the model grading its own homework.

From there, Kora scores how complete the evidence actually is against a due-diligence checklist, and computes an investment score — but if the coverage is too thin, it shows no score at all instead of a misleading one. That was a deliberate product decision: false precision is worse than an honest 'I don't have enough information yet.'

On top of that, there's a retrieval-augmented chat where the analyst can ask follow-up questions and get answers grounded in the actual document, with citations — plus a version that can query the extracted data directly instead of just paraphrasing text.

I built the whole thing solo — the data model, the FastAPI backend, the AI pipeline, and a Next.js frontend with a custom design system. The part I'm proudest of isn't any single feature, it's the overall stance: the product is honest about what it doesn't know, and everything it does claim to know, you can trace back to where it came from."
