# Kora — Product Case Study

## Problem

Early-stage due diligence is still largely a manual, ad-hoc process. An analyst receives a pitch deck or a data-room export, reads it, re-types the key numbers into a spreadsheet, and tries to hold the whole document's internal consistency in their head — does the stated LTV:CAC ratio actually match what the underlying revenue and cost numbers compute to? Does a "12-month runway" claim square with the stated cash and burn rate? Separately, the analyst keeps a running mental list of what the founder hasn't disclosed yet (a cap table? churn data? a real TAM source?), because a due-diligence checklist rarely exists as a first-class artifact — it lives in someone's head or a half-updated spreadsheet.

This is slow, inconsistent between analysts, and genuinely easy to get wrong: a well-designed pitch deck is optimized to read as compelling, not to be internally consistent, and a document that *looks* thorough is not the same thing as one that actually covers what a rigorous due-diligence pass requires.

## Users

Kora is built for the analyst side of early-stage investing and corporate development — the people who do the first pass on a deal, not the people making the final decision. Concretely: VC and angel-fund analysts, individual investors evaluating deals on their own, and small corporate-development or M&A teams who need to triage a stack of documents and decide which ones deserve deeper attention, without a large associate bench to do that triage for them.

## Solution

Kora automates the mechanical part of due diligence — extraction, consistency checking, and gap identification — while keeping every claim traceable back to the document it came from, so the analyst is reviewing evidence, not trusting a black box.

Concretely, Kora:

- Extracts structured financial and qualitative facts from an uploaded document via an LLM, with each fact tied to a source citation (the passage it was extracted from).
- Runs a **separate, deterministic** validation pass over those extracted facts — checking for internal inconsistencies (a reported ratio that doesn't match the numbers it's supposedly derived from, a growth claim with no supporting data point, a "profitable" claim contradicted by the reported net income, and several other checks) — without relying on the LLM to catch its own document's contradictions.
- Assesses how much of a due-diligence checklist the document actually covers (company overview, financials, market, team) and shows exactly what's missing and why it matters, rather than presenting whatever happened to be extracted as if it were complete.
- Computes a category-weighted investment score from verified facts, but withholds it — no number at all — when evidence coverage is too thin, rather than guessing.
- Lets the analyst ask follow-up questions in a retrieval-augmented chat, grounded in the indexed source documents, with citations back to the passages the answer relied on.
- Rolls every analyzed document up into an organization-wide portfolio view, and lets the analyst export the full analysis as a due-diligence report.

## Product Workflow

```
Document → Extract → Validate → Analyze → Ask → Report
```

1. **Document** — upload a pitch deck / financial document into an organization workspace.
2. **Extract** — an LLM pulls structured financial facts (ARR, MRR, burn rate, runway, CAC, LTV, etc.) and qualitative facts (business model, market, risks, team), each with a citation back to the source passage.
3. **Validate** — a deterministic rules engine cross-checks the extracted facts against each other and flags contradictions, independent of the LLM.
4. **Analyze** — Kora scores due-diligence coverage against a fixed checklist and computes an investment score from verified facts (or explicitly withholds it).
5. **Ask** — the analyst asks the AI chat questions grounded in the indexed document text, with cited sources in every answer.
6. **Report** — the full analysis exports as a due-diligence report, and rolls up into the organization's portfolio view alongside every other analyzed company.

## Key Product Decisions

**1. Structured extraction with source citations, not bare numbers.** Every extracted financial and qualitative fact carries a citation back to the page/passage it came from (`source_citations`, `financial_facts` tables). A due-diligence tool that hands an analyst a number with no way to verify where it came from isn't actually saving them work — it's just moving the trust problem somewhere less visible. Citations make every extracted claim auditable in one click.

**2. Validation is a separate, deterministic step — not left to the LLM.** `validation_service.py` is plain Python business logic (LTV:CAC reported-vs-calculated mismatch, growth claims without a supporting time series, unsupported "profitable" claims, runway claims without the cash/burn inputs to back them, funding or valuation figures mislabeled as revenue, forecasts presented as actuals) with 200+ unit tests behind it. An LLM asked "does this document contradict itself?" can miss its own contradictions or hallucinate ones that aren't there; a rule that checks whether `cash / burn_rate` actually equals the stated runway cannot.

**3. Missing information is surfaced explicitly, not silently ignored.** Coverage is scored against a fixed checklist (company, financial, market, team) and gaps are shown with a plain-language explanation of what to request and why it matters — not just a bare list of unfilled field names. A tool that only shows what an LLM happened to extract will always look more complete than the underlying document actually is; Kora is designed to show the gap instead of hiding it.

**4. The investment score can be null instead of a fabricated number.** When coverage falls below a threshold or critical fields (like a cap table or debt figures) are missing, the Score tab shows no number and says so plainly, rather than computing a score from partial evidence and presenting it with the same confidence as a well-evidenced one. False precision is worse than an honest gap in a diligence context — a wrong-but-confident-looking score is more dangerous than an admitted unknown.

**5. Findings distinguish document-stated facts from Kora's own inferences.** Every finding is tagged as either directly stated in the document, an LLM inference from what's in the document, or the result of an automated deterministic check — and the UI never blurs those together. An analyst deciding how much to trust a claim needs to know whether it's a direct quote, an educated guess, or a computed fact; collapsing that distinction would make the tool's output harder to act on, not easier.

**6. RAG chat answers include citations, and can go beyond text retrieval.** Chat runs in two modes: a standard retrieval-augmented mode that grounds answers in indexed document chunks (with citations), and an "analytical" tool-calling mode that can query the actual extracted financial data and missing-information state rather than only paraphrasing embedded text. A due-diligence copilot that can't show its work isn't trustworthy enough to act on.

**7. AI is an assistive layer, not the entire product.** The parts of Kora that matter most for trust — is this data internally consistent, is there enough evidence to score, what's missing — are ordinary, deterministic, unit-tested backend logic, not LLM calls. The LLM is used specifically where language understanding is genuinely required (extraction from unstructured text, qualitative summarization, conversational Q&A), and nowhere else. This keeps the system's safety-critical judgments outside the LLM's hands, and testable in the same way as any other backend service.

## Trade-offs and Limitations

Being direct about what Kora does not yet solve:

- **One document maps to one company profile.** There's no multi-document aggregation yet — if an analyst has a pitch deck *and* a separate financial model for the same company, Kora currently analyzes them as two independent documents rather than merging them into one company view.
- **No cross-document conflict detection.** Validation checks a single document's internal consistency; it does not yet compare two documents from the same company against each other to catch contradictions between them.
- **Organization invitations are manual link-sharing, not email delivery.** Inviting a teammate generates a link the inviter has to send themselves — there's no transactional email integration yet.
- **The extraction/scoring model is tuned around SaaS/subscription businesses.** ARR/MRR-centric metrics and the investment-score weighting reflect a subscription-revenue mental model; the period-convention handling (how MRR and ARR reconcile against each other) hasn't been stress-tested against unusual real-world edge cases outside that shape, and non-SaaS business models are not a first-class case yet.
- **Built for the investor/analyst side only.** Kora currently assumes the user is evaluating *someone else's* company. Adapting it for a business to analyze itself (e.g., a founder self-checking before a raise) or its own vendors/partners would need distinct product decisions — different onboarding, likely a different metric set — that haven't been made.
- **No light theme, no localization.** The UI is a single dark theme, English only.
- **A few UX rough edges remain.** No password-visibility toggle on login/signup, and some client-side navigations show a brief flash before content settles (no route-level loading/Suspense boundaries yet).
- **Single-instance deployment.** No read replicas, no background job queue — document processing and report generation run synchronously within the request rather than being offloaded to a worker, which is a reasonable choice at today's usage but a real constraint if usage or document size grows.
- **Basic auth only.** Email/password with JWT sessions; no SSO/OAuth, no multi-factor authentication.
- **Extraction quality is bounded by the underlying LLM and the source document's own clarity.** Kora surfaces uncertainty honestly (missing-information tracking, coverage thresholds, a withheld score) rather than hiding it, but it cannot fully eliminate LLM extraction mistakes — a genuinely ambiguous or poorly-scanned document will still produce a lower-confidence result, by design, rather than a falsely confident one.
