# Revenue Intelligence Platform — Product Requirements Document

**Company:** Kora Technologies
**Document owner:** VP of Product (in partnership with Head of Data)
**Status:** Approved for MVP implementation
**Audience:** Backend engineering, frontend engineering, data engineering, QA, design

This document is the source of truth for the Revenue Intelligence Platform MVP. It assumes familiarity with the Kora Technologies Company Blueprint, in particular Section 2 (Main Internal Pain Points), Section 3 (Business Processes and Business Entities), Section 8 (Engineering Stack), and Section 9 (Internal Engineering Products). Where this document references entities, KPIs, or systems defined in the Blueprint, it uses the same definitions — it does not redefine them.

---

# 1. Overview

The Revenue Intelligence Platform is an internal application that gives executives, sales leadership, and finance a single, reliable view of revenue: recognized revenue, pipeline-to-close forecasting, and usage-based billing trends. It replaces the current month-end process in which Finance manually reconciles exports from Salesforce, the Billing ledger service, and Snowflake before anyone can trust the numbers.

The platform does not generate or store new financial data. It is a read layer on top of existing systems of record (Billing service, Salesforce, Snowflake warehouse). Its job is to make the data those systems already contain visible, trustworthy, and interpretable, without requiring a manual reconciliation step every time someone needs an answer.

The MVP scope defined in this document covers seven capabilities: Authentication, Executive Dashboard, Revenue Analytics, AI Executive Summary, AI Copilot, Reports, and a Data Health Dashboard. Each is specified in full in Section 8.

---

# 2. Product Vision

Within two quarters of launch, no executive, sales leader, or finance stakeholder at Kora should need to ask Data & Analytics for a one-off revenue report. The platform should be the default place people go to answer "how is revenue doing," "is this quarter on track," and "why did this number move" — with enough confidence in the underlying data that its numbers are treated as the numbers, not a second opinion to be checked against a spreadsheet.

Longer-term (beyond this MVP), the platform is expected to narrow the gap between nightly batch reporting and same-day visibility, and to extend read access to Customer Success for renewal-adjacent revenue context — at which point its data boundary with the Customer Intelligence Platform will need to be formally defined. That extension is explicitly out of scope for this document (see Section 15).

---

# 3. Business Goals

1. Eliminate the manual, spreadsheet-based revenue reconciliation process currently performed by Finance at month-end.
2. Reduce the average time from "board or leadership asks a revenue question" to "answer delivered" from days to minutes.
3. Establish a single, agreed-upon definition of revenue and pipeline metrics that Finance, Sales, and the executive team all reference, replacing the current state where each function maintains its own version.
4. Reduce the volume of ad hoc reporting requests to Data & Analytics that relate to revenue, pipeline, or billing trend questions (see Blueprint Section 2, pain point 3).
5. Give Finance and Sales leadership visibility into usage-based billing trends before invoice generation, not after.

---

# 4. Success Metrics

| Metric | Baseline (Pre-Launch) | Target (2 Quarters Post-Launch) |
|---|---|---|
| Month-end close reconciliation time | 3–5 business days (manual) | Under 1 business day |
| Ad hoc revenue/pipeline report requests to Data & Analytics per month | Baseline to be measured in first month post-launch | 50% reduction |
| Time from leadership question to answer (self-reported, via periodic survey) | Days (requires Data & Analytics or Finance to compile) | Under 15 minutes for standard questions |
| Weekly active users among the six target personas | N/A (new product) | 80% of target persona group active at least weekly by end of Q2 post-launch |
| AI Executive Summary usage (opened at least once per week) | N/A | 60% of Executive-role users |
| Data Health Dashboard: unresolved reconciliation discrepancies flagged | Not currently tracked | Discrepancies surfaced within 24 hours of the nightly sync, not discovered manually at month-end |

Success is not measured by platform usage alone. If usage is high but Finance still runs a manual reconciliation in parallel "just to check," the platform has not achieved its core goal, and that is treated as a launch-blocking signal, not a minor gap.

---

# 5. Personas

## CEO
Checks revenue health infrequently but wants a fast, trustworthy answer when they do — typically before board meetings or when a Sales or Finance leader flags a concern. Has no patience for navigating multiple screens to find one number. Primary need: the Executive Dashboard and AI Executive Summary.

## COO
Cares about operational efficiency of the revenue process itself, not just the numbers. Interested in where reconciliation discrepancies come from and whether the underlying data pipeline is healthy — the Data Health Dashboard is disproportionately relevant to this persona compared to the others.

## Head of Sales
Needs pipeline-to-close visibility broken down by segment and rep, and wants to know, without asking Sales Ops, whether the quarter is tracking to forecast. Cares more about Revenue Analytics filtering and drill-down than about the AI features.

## Finance Manager
The primary owner of the reconciliation problem this platform is built to solve. Needs to trust the numbers enough to stop maintaining a parallel spreadsheet. Heaviest user of Reports (CSV/PDF exports feeding board decks and audit documentation) and the Data Health Dashboard.

## Business Analyst
Works across Finance and Sales Ops, building ad hoc analysis on top of the platform's data. Primary user of the AI Copilot's "Ask Data" capability for exploratory questions that don't warrant a full Data & Analytics request.

## Product Analyst
Uses revenue and usage-based billing trends to understand product engagement and pricing tier performance. Lighter user overall than the other five personas, but relies on Revenue Analytics filtering by product tier and usage metrics.

---

# 6. User Stories

**Authentication**
- As any target user, I want to log in using my existing company credentials so that I don't need to manage a separate password.
- As an Admin, I want session tokens to expire after a defined period so that stale sessions don't remain valid indefinitely.

**Executive Dashboard**
- As a CEO, I want to see current-quarter revenue, pipeline-to-close, and churn at a glance so that I don't need to ask Finance or Sales Ops for a status update.
- As a COO, I want to see whether the data behind the dashboard is current and reliable so that I know whether to trust what I'm looking at.

**Revenue Analytics**
- As a Head of Sales, I want to filter pipeline and bookings by segment and rep so that I can identify where the quarter is at risk.
- As a Finance Manager, I want to see recognized revenue versus billed revenue over time so that I can identify recognition timing discrepancies without a manual export.
- As a Product Analyst, I want to filter revenue by product tier and usage-based billing volume so that I can see which tiers are driving growth.

**AI Executive Summary**
- As a CEO, I want a short, plain-language summary of what changed and why, generated automatically, so that I don't have to interpret raw charts myself.
- As a Finance Manager, I want the summary to cite the specific numbers it's referencing so that I can verify it against the underlying data if needed.

**AI Copilot**
- As a Business Analyst, I want to ask a natural-language question about revenue data and get an answer grounded in the platform's actual data, so that I don't need to file a request with Data & Analytics for straightforward questions.
- As any user, I want to know when the Copilot cannot answer a question reliably, rather than receiving a confident but ungrounded answer.

**Reports**
- As a Finance Manager, I want to export a revenue report as PDF for the board deck so that I don't need to manually rebuild charts in a separate tool.
- As a Business Analyst, I want to export the underlying data as CSV so that I can do further analysis outside the platform.

**Data Health Dashboard**
- As a COO, I want to see the last successful data sync time and whether any source system failed to sync so that I know if the numbers I'm looking at are current.
- As a Finance Manager, I want to see whether Billing, Salesforce, and Snowflake numbers are reconciled or in conflict, and by how much, so that I can flag discrepancies before month-end instead of during it.

---

# 7. User Journey

## Primary journey: Finance Manager, month-end close

1. Finance Manager logs in on the first business day after month-end.
2. Lands on the Executive Dashboard, immediately checks the Data Health Dashboard status indicator (visible as a persistent header element, described in Section 9).
3. If Data Health shows all sources reconciled within tolerance, proceeds to Revenue Analytics to review recognized-versus-billed revenue for the closed month.
4. If a discrepancy is flagged, navigates to the Data Health Dashboard to see which source system and which entities are affected, and whether it's a known timing issue (e.g., an invoice generated after the warehouse's nightly sync cutoff) or a genuine data problem requiring escalation to Data & Analytics.
5. Once satisfied, exports a PDF report of the closed month's revenue summary for the Finance leadership review meeting.
6. Historically, this entire process took 3–5 days and involved three separate spreadsheet exports. In the target state, steps 1–5 take under an hour, assuming no genuine data discrepancy is found.

## Secondary journey: CEO, pre-board-meeting check

1. CEO logs in the morning of a board meeting.
2. Lands on Executive Dashboard, reads the AI Executive Summary card first (top of page, described in Section 9).
3. Skims KPI cards for current quarter revenue, NRR, and pipeline-to-close.
4. If a number looks concerning, opens AI Copilot and asks a follow-up question in natural language (e.g., "why did NRR drop this month") rather than digging through Revenue Analytics filters directly.
5. Exits the platform with either confidence in the numbers or a specific question to raise with Finance or Sales leadership directly.

## Secondary journey: Business Analyst, exploratory question

1. Business Analyst receives an informal question from a Sales leader ("how does the Growth tier compare to Enterprise for expansion revenue this quarter") that doesn't warrant a formal Data & Analytics request.
2. Opens AI Copilot, asks the question directly.
3. Copilot returns a grounded answer referencing specific figures, or, if the question requires a comparison the underlying data model doesn't support, tells the user so rather than guessing.
4. If the answer is sufficient, Business Analyst relays it directly. If not, follows up in Revenue Analytics using manual filters, or escalates to Data & Analytics only if genuinely blocked.

---

# 8. Functional Requirements

## 8.1 Authentication

**Purpose:** Ensure only authorized Kora employees can access revenue and financial data, consistent with the access sensitivity of the information the platform surfaces.

**Description:** Users authenticate via the company's existing Auth0-backed SSO (see Blueprint Section 8), which issues a signed JWT on successful login. The platform validates this JWT on every request rather than maintaining its own separate credential store. Session tokens expire after 8 hours of inactivity; refresh tokens are supported to avoid forcing re-login during a normal workday.

**User Flow:**
1. User navigates to the platform URL.
2. Redirected to company SSO login if no valid session exists.
3. On successful SSO authentication, Auth0 issues a JWT containing the user's identity and role claim.
4. Platform validates the JWT signature and expiry on each API request via the backend's auth middleware.
5. If the JWT is expired, the frontend silently attempts a refresh; if refresh fails, the user is redirected to login.

**Business Value:** Avoids building and maintaining a separate credential system for an internal tool; leverages existing enterprise-grade SSO infrastructure and inherits its security posture (see Blueprint Section 8, Authentication).

**Acceptance Criteria:**
- Given a user with no active session, when they navigate to any platform URL, then they are redirected to SSO login before any application content loads.
- Given a valid JWT with an unrecognized role claim, when the user attempts to access the platform, then they receive a permission-denied state rather than default access (see Section 12, Error States).
- Given an expired JWT, when the user makes an API request, then the request is rejected with a 401 and the frontend triggers the refresh flow before retrying.
- Given a refresh token that has also expired, when refresh is attempted, then the user is redirected to a fresh SSO login without an error being surfaced as a bug.
- No endpoint in the platform is accessible without a valid JWT, including read-only data endpoints.

## 8.2 Executive Dashboard

**Purpose:** Give every target persona a single landing screen answering "how is revenue doing right now" without requiring navigation into a specific analytics view.

**Description:** The default screen after login. Displays the AI Executive Summary, a fixed set of KPI cards (defined in Section 10), and a persistent Data Health status indicator. Does not include deep filtering — that's the role of Revenue Analytics. The Executive Dashboard is deliberately narrow in scope to keep it fast and glanceable.

**User Flow:**
1. User lands on the dashboard immediately after login.
2. AI Executive Summary loads asynchronously (does not block KPI cards from rendering — see Section 12 for AI-unavailable handling).
3. KPI cards render with current values and period-over-period change indicators.
4. User can click any KPI card to navigate directly into Revenue Analytics pre-filtered to that metric.

**Business Value:** Directly addresses the goal of reducing time from "leadership asks a question" to "answer delivered" (Section 4). Removes the need to open Revenue Analytics for the majority of quick status checks.

**Acceptance Criteria:**
- Given a user with Executive or Analyst role, when they log in, then the Executive Dashboard is the default landing screen.
- Given the AI Executive Summary is still loading, then the KPI cards must render independently and not be blocked by the summary's load time.
- Given a KPI card is clicked, then the user is navigated to Revenue Analytics with the corresponding filter and date range pre-applied.
- Given the Data Health status is anything other than "healthy," then a visible (not hidden-behind-a-click) indicator must appear in the dashboard header.

## 8.3 Revenue Analytics

**Purpose:** Provide the detailed, filterable view of revenue, pipeline, and usage-based billing data that the Executive Dashboard intentionally does not provide.

**Description:** The primary analytical screen. Includes recognized revenue over time, billed revenue, pipeline-to-close by stage, NRR and churn broken down by segment, and usage-based billing trend charts. Fully filterable by date range, customer segment, product tier, and (where permitted by role) sales rep.

**User Flow:**
1. User navigates from the Executive Dashboard (via KPI card click) or directly via primary navigation.
2. Default view shows current quarter, all segments.
3. User applies filters (date range, segment, tier, rep); charts and tables update accordingly.
4. User can toggle between recognized revenue and billed revenue views for reconciliation purposes.
5. User can export the current filtered view directly to CSV or PDF (see Section 8.6).

**Business Value:** Replaces the manual spreadsheet-based drill-down Finance and Sales Ops currently perform when a KPI card raises a question. Directly serves the Head of Sales and Finance Manager personas, who need more than a glance.

**Acceptance Criteria:**
- Given no filters are applied, then the screen defaults to current quarter, all segments, all tiers.
- Given a date range filter is applied, then all charts and tables on the screen update consistently — no chart may reflect a stale filter state.
- Given a user without permission to view rep-level detail (see Section 11 permissions matrix), then the rep filter is not shown, not shown-but-disabled.
- Given the recognized-versus-billed toggle is switched, then the underlying data source query changes accordingly and the toggle state is reflected in the exported report if an export is triggered from this state.
- Given no data exists for the selected filter combination, then the empty-data state defined in Section 12 is shown rather than an empty chart with no explanation.

## 8.4 AI Executive Summary

**Purpose:** Automatically generate a short, plain-language summary of the current period's revenue performance, so executives don't need to interpret raw charts themselves.

**Description:** A card at the top of the Executive Dashboard, regenerated on a scheduled basis (daily, aligned with the nightly warehouse sync — see Blueprint Section 11) rather than on every page load, to keep the underlying numbers stable and auditable within a given day. Summarizes period-over-period changes in the core KPIs and highlights the most significant driver of change, citing the specific figures involved.

**User Flow:**
1. Summary is generated by a scheduled backend job immediately after the nightly warehouse sync completes.
2. User opens the Executive Dashboard and sees the most recent generated summary, with a visible timestamp of when it was generated.
3. User can click "why" on any statement in the summary to jump into Revenue Analytics filtered to the relevant metric and time period.

**Business Value:** Reduces the interpretive burden on the CEO and COO personas in particular, who check the platform infrequently and need a fast, trustworthy read rather than a dashboard to explore.

**Acceptance Criteria:**
- Given the nightly sync has completed, then a new summary is generated within a defined SLA window (target: within 30 minutes of sync completion) before the start of business hours.
- Given the summary references a specific number (e.g., "NRR declined 3 points"), then that number must match exactly what Revenue Analytics shows for the same period — the summary and the analytics view can never disagree.
- Given the summary generation job fails, then the dashboard displays the most recent successfully generated summary along with its generation date, rather than a blank card (see Section 12).
- Given a user clicks a "why" link within the summary, then they land in Revenue Analytics with the correct metric and period filter already applied.

## 8.5 AI Copilot

**Purpose:** Let users ask natural-language questions about revenue data and receive answers grounded in the platform's actual underlying data, reducing reliance on ad hoc requests to Data & Analytics.

**Description:** A conversational interface, separate from the Executive Summary, that accepts free-text questions and returns answers backed by queries against the platform's data model — not free-form generation disconnected from real numbers. Detailed prompt strategy and grounding approach are specified in Section 11.

**User Flow:**
1. User opens AI Copilot from primary navigation or from a KPI card's "ask about this" shortcut.
2. User types a natural-language question.
3. Backend translates the question into a scoped query against the platform's data layer (not the raw warehouse directly — see Section 11).
4. If the query can be answered with available data and within the user's permission scope, a grounded answer is returned along with the specific figures used.
5. If the question cannot be answered (insufficient data, out-of-scope entity, or outside the user's permission scope), the Copilot states this explicitly rather than producing a plausible-sounding but ungrounded answer.

**Business Value:** Directly targets the reduction in ad hoc reporting requests to Data & Analytics (Section 3, Business Goal 4), while keeping answers grounded to avoid the platform becoming a source of confidently wrong numbers.

**Acceptance Criteria:**
- Given a question the platform's data model can answer, then the response includes the specific underlying figures, not just a qualitative statement.
- Given a question referencing data outside the user's permission scope (e.g., an Analyst asking for rep-level detail they don't have access to), then the Copilot declines and explains why, rather than silently omitting the restricted detail from an otherwise-answered response.
- Given a question the underlying data model genuinely cannot answer (e.g., asking about a metric that doesn't exist), then the Copilot states this rather than fabricating a plausible number.
- Given the AI service is unavailable, then the Copilot interface reflects this clearly (see Section 12) rather than hanging indefinitely or failing silently.
- Every Copilot query and response is logged for audit purposes (see Section 13, Audit).

## 8.6 Reports (CSV / PDF)

**Purpose:** Let users export platform data in formats usable outside the platform — for board decks, audit documentation, and further analysis.

**Description:** Available from Revenue Analytics and from a dedicated Reports screen. CSV exports the underlying tabular data matching the current filter state. PDF exports a formatted report suitable for a board deck or leadership review, including the relevant charts and summary text. Excel export is included as an MVP-adjacent format per the Reports screen requirement (see Section 9, Reports screen) using the same underlying export pipeline as CSV, with formatting applied.

**User Flow:**
1. User applies filters in Revenue Analytics (or selects a saved report template from the Reports screen).
2. User selects export format (CSV, Excel, or PDF).
3. Export is generated server-side (not client-side, to ensure large exports don't block the browser) and delivered as a download once ready; for larger exports, the user is notified when the file is ready rather than waiting on a blocking spinner.
4. Every export is logged with the requesting user, timestamp, and filter parameters used (see Section 13, Audit).

**Business Value:** Directly serves the Finance Manager persona's heaviest workflow — the platform must be at least as convenient as the current manual spreadsheet process, or Finance has no reason to stop using spreadsheets in parallel.

**Acceptance Criteria:**
- Given a filtered Revenue Analytics view, when the user exports to CSV, then the exported file contains exactly the rows and columns reflected in the current filter and view state — no extra columns, no omitted rows.
- Given a PDF export is requested, then the generated PDF includes the relevant chart(s), the applied filter parameters (visibly stated, not just implied), and a generation timestamp.
- Given an export exceeds a defined size threshold, then it is generated asynchronously with a notification on completion rather than blocking the UI.
- Given an export is generated, then a corresponding audit log entry is created recording who requested it, when, and with what parameters.

## 8.7 Data Health Dashboard

**Purpose:** Give users — particularly the COO and Finance Manager personas — visibility into whether the underlying data feeding the platform is current, complete, and reconciled across source systems, so that platform numbers are trusted rather than independently re-verified.

**Description:** A dedicated screen (and a persistent summary indicator visible elsewhere in the platform, per Section 8.2) showing: last successful sync time per source system (Billing, Salesforce, Snowflake), row-count deltas versus the prior sync, and reconciliation status between source systems for the core entities defined in the Blueprint (Contract, Invoice, Opportunity).

**User Flow:**
1. User navigates to Data Health Dashboard directly, or clicks the persistent status indicator from any other screen.
2. Screen shows sync status per source system with last-successful-sync timestamps.
3. Reconciliation section shows any entities where source systems disagree beyond a defined tolerance (e.g., an Opportunity marked closed/won in Salesforce with no corresponding Contract in the Billing system).
4. User can drill into a specific discrepancy to see the affected record IDs, for escalation to Data & Analytics if needed.

**Business Value:** Directly addresses the trust problem described in Blueprint Section 2 (pain point 2) — numbers disagreeing across systems until manually reconciled. Without this screen, the platform risks becoming just another system whose numbers might be wrong, defeating its purpose.

**Acceptance Criteria:**
- Given any source system's last sync exceeds a defined staleness threshold, then this is visibly flagged both on this screen and via the persistent header indicator.
- Given a reconciliation discrepancy exists between two source systems for the same entity, then it is listed with enough detail (entity type, ID, systems involved, values in conflict) to be actionable without further investigation.
- Given all source systems are synced and reconciled within tolerance, then the platform-wide status indicator reflects "healthy," and this state is visually distinct from any degraded state.
- Given a user with Analyst role, then they can view but not dismiss or acknowledge a flagged discrepancy — dismissal is restricted to Admin role (see Section 11).

---

# 9. Screens

## Login

Single-purpose screen. Displays the Kora logo, a brief "Revenue Intelligence Platform" label, and a "Log in with Kora SSO" button. No username/password fields are rendered directly — authentication is fully delegated to Auth0 (Section 8.1). If the user arrives already authenticated (valid session), this screen is skipped entirely and they land directly on the Dashboard.

## Dashboard (Executive Dashboard)

The default landing screen. Layout, top to bottom: persistent header (logo, primary navigation, Data Health status indicator, user menu), AI Executive Summary card, KPI card row, and a secondary section with two supporting charts (revenue trend and pipeline-to-close trend) for at-a-glance context beyond the KPI cards alone. Full KPI card, chart, and interaction specification is in Section 10.

## Revenue Analytics

The detailed analytical screen. Layout: filter bar (date range, segment, product tier, rep — rep visible only per permissions), followed by a tab or section structure separating Revenue (recognized vs. billed), Pipeline (by stage and rep), and Usage-Based Billing Trends. Each section contains its own chart(s) and an underlying data table. Export controls (CSV/Excel/PDF) are available from this screen at all times, scoped to the current filter state.

## Reports

A dedicated screen for report generation and history, separate from ad hoc exports triggered within Revenue Analytics. Contains: a list of report templates (e.g., "Monthly Board Summary," "Quarterly Revenue Recognition Detail"), a history of previously generated reports with re-download links, and a "generate new report" flow that lets the user select a template, date range, and format. Report history is scoped per-user unless the user has Admin role, in which case all report generation history is visible for audit purposes.

## Data Health

Full detail as described in Section 8.7. Layout: per-source-system sync status cards at the top, followed by a reconciliation discrepancy table below. Discrepancy table supports filtering by entity type and by severity (data missing entirely vs. values disagreeing beyond tolerance vs. minor timing lag).

## Settings

Minimal for MVP. Contains: user profile information (read-only, sourced from SSO — not editable within this platform), notification preferences (e.g., whether to receive an email when a flagged Data Health discrepancy is dismissed or a scheduled report completes), and, for Admin role only, a user role management section reflecting the permissions matrix in Section 11.

## AI Copilot

A conversational screen, accessible from primary navigation. Layout: a chat-style input at the bottom, response history above, with each response visually distinguishing narrative text from cited figures (figures are rendered distinctly, e.g., in a bordered inline card, to make clear they are pulled from real data rather than generated prose). Includes a persistent disclaimer describing the Copilot's grounding and limitations (see Section 11, Limitations) visible on first use per session, dismissible thereafter.

---

# 10. Dashboard — Detailed Specification

## KPI Cards

Six KPI cards are shown on the Executive Dashboard, matching the critical KPIs defined in Blueprint Section 4 that are relevant to revenue (Support SLA and deployment metrics are out of scope for this platform).

1. **Current Quarter Revenue (Recognized)** — Total recognized revenue for the current quarter to date, with a period-over-period comparison against the same point in the prior quarter. Clicking navigates to Revenue Analytics, Revenue tab, current quarter.
2. **Net Revenue Retention (NRR)** — Current NRR, trailing twelve months, with trend arrow indicating direction versus prior period. Clicking navigates to Revenue Analytics filtered to NRR view.
3. **Gross Churn Rate** — Current period gross churn, with trend arrow. Clicking navigates to Revenue Analytics, segment breakdown of churn.
4. **Pipeline-to-Close (Current Quarter)** — Total open pipeline value weighted by stage probability, compared against the quarter's booking target. Clicking navigates to Revenue Analytics, Pipeline tab.
5. **Usage-Based Billing (Current Month)** — Total usage-based billing revenue for the current month to date, with a comparison against the prior month's equivalent point. Clicking navigates to Revenue Analytics, Usage-Based Billing Trends tab.
6. **Revenue Recognized vs. Billed (Variance)** — The dollar and percentage variance between recognized and billed revenue for the most recently closed month — the single number Finance cares most about at month-end. Clicking navigates directly to the reconciliation detail in Revenue Analytics.

Each KPI card displays: the current value, a period-over-period delta (absolute and percentage), a trend arrow (up/down/flat, with color meaning dependent on whether up is good or bad for that specific metric — churn going up is shown as a negative-color trend even though the arrow points up), and the as-of timestamp for the underlying data.

## Charts

**Revenue Trend Chart** (Executive Dashboard, supporting section): Line chart, trailing 12 months, recognized revenue by month, with the current month's partial-period value visually distinguished (e.g., dashed line segment) from completed months, so users don't misread an in-progress month as a completed one.

**Pipeline-to-Close Trend Chart** (Executive Dashboard, supporting section): Stacked bar chart, current quarter, pipeline value by stage, updated daily, with the quarter's booking target overlaid as a reference line.

**Recognized vs. Billed Revenue Chart** (Revenue Analytics): Dual-line chart over the selected date range, with the variance between the two lines shaded to make discrepancies visually obvious without requiring the user to read exact values.

**Pipeline by Stage and Rep Chart** (Revenue Analytics, Pipeline tab): Horizontal stacked bar chart, one bar per rep (or per segment, if rep-level detail isn't permitted for the viewing user), segmented by pipeline stage.

**Usage-Based Billing Trend Chart** (Revenue Analytics): Line chart showing usage-based billing revenue by product tier over the selected date range, with the ability to toggle individual tiers on/off in the legend.

## Tables

Every chart in Revenue Analytics has a corresponding data table below it, showing the exact underlying rows used to render the chart, sortable by any column and matching the export output exactly (so a user can visually verify a CSV export against what they see on screen).

## Interactions and Filters

- **Global date range filter** — applies across all Revenue Analytics charts and tables simultaneously (not scoped per-chart); default is current quarter.
- **Segment filter** — filters by customer segment (Standard, Growth, Enterprise tier, consistent with Blueprint Section 1 pricing tiers).
- **Product tier filter** — same tier definitions as segment filter, used specifically for the Usage-Based Billing Trends view where tier is the primary lens rather than a secondary filter.
- **Rep filter** — visible only to users with permission to see rep-level detail (Executive and Admin roles; see Section 11). Not shown at all (not shown-disabled) to Analyst-role users, to avoid implying access that doesn't exist.
- **Recognized vs. Billed toggle** — switches the primary revenue view between the two bases; persists across navigation within a session but resets to "Recognized" as default on new session start.
- **KPI card click-through** — every KPI card is clickable and deep-links into Revenue Analytics with the corresponding filter state pre-applied, as specified per-card above.

---

# 11. AI

## Executive Summary

Generated once daily, immediately following the nightly warehouse sync (Blueprint Section 11). Not generated on-demand per page load, to keep the summary's figures stable and auditable within a given business day — a user checking the dashboard at 9am and again at 4pm should see the identical summary, not two different AI-generated interpretations of the same underlying data. Full behavior and acceptance criteria are specified in Section 8.4.

## Ask Data (AI Copilot's core capability)

The Copilot does not generate answers from unconstrained language model output. A user's natural-language question is first translated into a structured query against the platform's own data access layer (the same layer serving Revenue Analytics and the Executive Dashboard), and the model's role is to interpret the question, select the right structured query, and phrase the grounded result back in natural language — not to reason freely about revenue figures from its own training knowledge. This is the mechanism that makes the acceptance criteria in Section 8.5 (grounded figures, explicit refusal when data isn't available) enforceable rather than aspirational.

## Recommendations

The Copilot may surface a small number of suggested follow-up questions after answering (e.g., after answering an NRR question, suggesting "see churn by segment" as a related question) but does not proactively generate open-ended strategic recommendations ("you should consider raising Enterprise pricing") in the MVP. Prescriptive recommendations are explicitly out of scope for this release (see Section 15) because they require a level of business judgment and downstream accountability that the MVP's grounding mechanism is not built to support responsibly.

## Limitations

The AI Copilot and Executive Summary are subject to the following constraints, which are surfaced to users directly rather than left implicit:

- Answers are limited to what the platform's data access layer can query. Questions requiring data outside Contract, Invoice, Opportunity, and Usage Event entities (Blueprint Section 3) cannot be answered, and the Copilot states this rather than guessing.
- Answers respect the requesting user's permission scope. The Copilot never uses elevated data access to answer a question the user themselves could not see in Revenue Analytics.
- The Executive Summary reflects data as of the most recent nightly sync, not real-time. This is stated with a visible timestamp on every summary.
- Neither feature is designed to answer hypothetical or forward-looking "what if" questions (e.g., "what would revenue be if we raised Enterprise prices 10%") in the MVP — this is a modeling capability, not a data-retrieval one, and is out of scope.

## Prompt Strategy

The system prompt used for both the Executive Summary generation job and the Ask Data Copilot explicitly instructs the model to: only reference figures returned by the structured query layer, never estimate or infer a number it wasn't given, cite the specific metric and time period for every factual claim, and respond with an explicit "I don't have data to answer that" rather than a hedged guess when the query layer returns no result or an out-of-scope request. The prompt also enforces the permission scope by including the requesting user's role and accessible data scope as part of the context provided to the model on every request, rather than relying on the model to infer what it should or shouldn't reveal.

---

# 12. Roles

## Role Definitions

- **Admin** — Data & Analytics team members responsible for maintaining the platform's data pipeline and user access. Can view everything, dismiss Data Health discrepancies, and manage user role assignments.
- **Executive** — CEO, COO, Head of Sales, Finance Manager. Full read access to all revenue data including rep-level detail, full access to Reports and AI features, cannot manage user roles or dismiss Data Health discrepancies.
- **Analyst** — Business Analyst, Product Analyst. Full read access to aggregate revenue, pipeline, and usage data, but not rep-level detail. Full access to Reports and AI Copilot within their permission scope.

## Permissions Matrix

| Capability | Admin | Executive | Analyst |
|---|---|---|---|
| View Executive Dashboard | Yes | Yes | Yes |
| View Revenue Analytics (aggregate) | Yes | Yes | Yes |
| View Revenue Analytics (rep-level detail) | Yes | Yes | No |
| Use AI Executive Summary | Yes | Yes | Yes |
| Use AI Copilot (aggregate questions) | Yes | Yes | Yes |
| Use AI Copilot (rep-level questions) | Yes | Yes | No — Copilot declines per Section 11 |
| Generate CSV / Excel / PDF reports | Yes | Yes | Yes |
| View own report generation history | Yes | Yes | Yes |
| View all users' report generation history | Yes | No | No |
| View Data Health Dashboard | Yes | Yes | Yes |
| Dismiss / acknowledge Data Health discrepancies | Yes | No | No |
| Manage user role assignments (Settings) | Yes | No | No |
| View audit logs | Yes | No | No |

---

# 13. Reports — Format Specifications

## CSV

Contains the exact rows and columns visible in the current filtered view at time of export — no additional columns beyond what's displayed, and no columns silently omitted. Column headers match the on-screen table headers exactly. Encoded UTF-8. Numeric values are exported unformatted (raw numbers, not currency-symbol-prefixed strings) so the file is directly usable in downstream spreadsheet analysis without cleanup.

## Excel

Uses the same underlying export data as CSV, with formatting applied: currency and percentage formatting on relevant columns, a frozen header row, and the applied filter parameters written into a separate metadata sheet within the same workbook (not just in the filename), so a downloaded file remains self-documenting even if renamed or shared outside its original context.

## PDF

A formatted report intended for board or leadership review rather than further data manipulation. Includes: a cover section stating report title, generation timestamp, and applied filters; the relevant chart(s) rendered as static images; the corresponding data table below each chart; and, where the report includes the Executive Summary, the summary text with its own generation timestamp distinct from the report's own generation timestamp (these can differ if a report is generated later than the summary itself was produced).

---

# 14. Error States

| State | Trigger | Behavior |
|---|---|---|
| Empty dashboard | New user or newly provisioned account with no accessible data scope configured yet | Dashboard shell renders (header, navigation) with a clear message explaining that no data scope has been assigned, and a contact point (Admin) to resolve it — not a blank white screen. |
| API unavailable | Backend API is unreachable or returns 5xx | A platform-wide banner indicates the issue, cached last-known KPI values (if available and clearly timestamped as stale) may still render, but no user-facing screen fails silently with no explanation. |
| No data | Valid filter combination that legitimately has no matching data (e.g., a new segment with no historical revenue yet) | Distinguished explicitly from an error state — message states plainly that no data exists for the selected filters, with a suggestion to adjust the date range or filters, rather than implying something is broken. |
| Permission denied | User attempts to access a screen, filter, or Copilot query outside their role's scope | Explicit message naming what is restricted and why (role-based), rather than a generic 403 or a silently empty result. Never silently downgrades to a "safe" empty response that could be mistaken for legitimate data. |
| AI unavailable | Executive Summary generation job fails, or AI Copilot's backing service is unreachable | Executive Summary: most recent successfully generated summary is shown with its original generation timestamp and a visible note that a newer summary could not be generated. AI Copilot: input is disabled with a clear message rather than allowed to submit a question that will silently fail or hang. |

---

# 15. Non-Functional Requirements

## Performance
- Executive Dashboard KPI cards must render within 2 seconds of authentication completing, using cached/pre-aggregated data rather than computing aggregates live on every page load.
- Revenue Analytics filter changes must update charts and tables within 3 seconds under normal load.
- AI Copilot responses should return within 10 seconds for the majority of queries; anything requiring longer must show a visible "thinking" state rather than an unexplained delay.

## Security
- All data in transit is encrypted (TLS). All data at rest in any platform-specific storage is encrypted using standard AWS-managed encryption, consistent with Blueprint Section 8 infrastructure choices.
- No direct production database access is granted to platform users; all data access flows through the platform's own data access layer, which enforces the permissions matrix in Section 12 at the query level, not just in the UI.
- JWT validation occurs on every API request; there is no endpoint that trusts a client-supplied role claim without server-side verification against the identity provider.

## Scalability
- The platform must support the full target persona group (approximately 6 role types across roughly 30–40 named users given current company size) with headroom for growth to twice that number without architectural changes, consistent with the company's current ~200-person scale (Blueprint Section 1).
- Report generation and AI Copilot queries are handled asynchronously where they exceed a defined latency threshold, to prevent one user's heavy query from degrading dashboard performance for others.

## Accessibility
- All screens meet WCAG 2.1 AA standards: sufficient color contrast (including trend-arrow color coding, which must not rely on color alone — icons/shape differences are required alongside color), full keyboard navigability, and screen-reader-compatible labeling for charts and KPI cards (not just visual rendering).

## Logging
- All API requests are logged with requesting user, endpoint, timestamp, and response status, consistent with the company's centralized logging approach (Blueprint Section 8, Datadog Log Management).
- AI Copilot queries and responses are logged in full (question, structured query generated, response returned) to support both audit requirements and future model performance evaluation.

## Audit
- Every report export, every Data Health discrepancy dismissal, and every user role change is recorded in an audit log accessible to Admin role users, including who performed the action and when.
- Audit logs are immutable from the application layer — no user-facing action can delete or modify an existing audit log entry.

## Localization
- MVP is English-only. The data model and UI framework should not hard-code English-only assumptions that would block future localization (e.g., currency formatting should be locale-aware even if only USD is supported at launch), but full localization is out of scope for this release (see Section 16).

## Responsive Design
- The platform must be fully usable on standard laptop and desktop screen widths (1280px and above). Tablet support (768px–1279px) should degrade gracefully (e.g., KPI cards reflow rather than overflow) but is not required to match desktop feature parity exactly. Mobile phone support is explicitly out of scope for this MVP (see Section 16) — this is an internal analytical tool, not expected to be used primarily on a phone.

---

# 16. Out of Scope

The following are explicitly excluded from this MVP and should not be inferred as implied requirements:

- Real-time (sub-nightly-batch) data refresh. The platform inherits the nightly sync cadence described in Blueprint Section 11; closing that gap is a documented future direction for the Revenue Intelligence Platform (Blueprint Section 9) but not part of this MVP.
- Read access for Customer Success or Support roles. This platform's initial roll-out is scoped to the six personas in Section 5; extending access to CS (as referenced in Blueprint Section 9's future direction) requires a defined data-sharing boundary with the Customer Intelligence Platform and is a separate, future initiative.
- Prescriptive AI recommendations (e.g., pricing or strategy suggestions). Covered in Section 11.
- What-if / scenario modeling capability within the AI Copilot.
- Mobile phone-optimized UI.
- Full localization / multi-language support.
- Editing or write-back capability of any kind — this platform is strictly read-only against source systems. No user action within this platform can modify Billing, Salesforce, or Snowflake data.
- Direct integration with tools outside the existing stack described in Blueprint Section 8 (e.g., no new BI tool, no replacement of Looker for non-revenue reporting).
- Automated email/Slack alerting on KPI thresholds. The Data Health status indicator and Executive Summary are the MVP's proactive-communication mechanisms; threshold-based alerting is a candidate for a future iteration, not this release.

---

# 17. MVP Scope Summary

The MVP consists of exactly the seven capabilities specified in Section 8: Authentication, Executive Dashboard, Revenue Analytics, AI Executive Summary, AI Copilot, Reports (CSV/Excel/PDF), and Data Health Dashboard. Every screen in Section 9 supports one or more of these capabilities; there are no additional screens beyond Login, Dashboard, Revenue Analytics, Reports, Data Health, Settings, and AI Copilot in this release. Anything not explicitly described in Sections 8 through 14 of this document should be treated as out of scope by default (Section 16) rather than assumed to be a reasonable implicit extension — if a feature isn't specified here, it isn't in the MVP, and engineering should raise it with Product rather than build it speculatively.

---

# 18. Acceptance Criteria Summary

This section consolidates the acceptance criteria already specified per-feature in Section 8 into a single release checklist. A feature is considered launch-ready only when every criterion below is verifiably true in a staging environment with production-equivalent data volume.

**Authentication:** SSO redirect works for unauthenticated users; JWT validated on every request; expired-token refresh flow works; unrecognized role claims produce permission-denied, not default access.

**Executive Dashboard:** Loads as default landing screen; KPI cards render independently of AI Summary load time; every KPI card deep-links correctly into Revenue Analytics; Data Health degraded state is visibly surfaced in the header.

**Revenue Analytics:** Correct default filter state; all charts/tables update consistently on filter change; rep-level filter hidden entirely (not disabled) for Analyst role; recognized/billed toggle correctly changes underlying query and persists through export; empty-filter-result state handled per Section 14.

**AI Executive Summary:** Generated within SLA after nightly sync; every cited figure matches Revenue Analytics exactly for the same period; stale-summary fallback works when generation fails; "why" links deep-link correctly.

**AI Copilot:** Grounded answers include specific cited figures; permission-scope violations are explicitly declined, not silently filtered; genuinely unanswerable questions produce an explicit "no data" response rather than a fabricated one; AI-unavailable state disables input with a clear message; every query/response pair is logged.

**Reports:** CSV output matches on-screen filtered view exactly; Excel includes formatting and a metadata sheet documenting applied filters; PDF includes charts, tables, filters, and timestamp; large exports run asynchronously with completion notification; every export is audit-logged.

**Data Health Dashboard:** Staleness beyond threshold is flagged both on-screen and in the persistent header indicator; reconciliation discrepancies include enough detail to be actionable; healthy state is visually distinct from degraded states; discrepancy dismissal is restricted to Admin role only.

**Cross-cutting (Non-Functional):** Performance targets met under production-equivalent load; no production database is directly accessible from any platform user action; WCAG 2.1 AA compliance verified; all specified logging and audit trails are present and immutable from the application layer; responsive behavior verified at 1280px and at tablet breakpoints; localization-readiness verified even though only English ships at launch.

---

# 19. KPI Definitions

This is the KPI Dictionary for the platform. Every metric referenced anywhere in this document — KPI cards, Revenue Analytics charts, AI Executive Summary, AI Copilot responses — must use the exact formula defined here. This is the enforcement mechanism behind the acceptance criteria in Section 8.4 that the Executive Summary and Revenue Analytics can never disagree on a number: if both are computed from this dictionary, disagreement becomes a bug by definition, not a matter of interpretation.

Unless otherwise noted, "customer" refers to an Account as defined in Blueprint Section 3, and monetary figures are computed from Contract and Invoice records, not from Opportunity (pipeline) records, which are forecast rather than realized.

| KPI | Formula | Description | Business Purpose |
|---|---|---|---|
| MRR (Monthly Recurring Revenue) | Sum of normalized monthly subscription value across all active Contracts (annual and quarterly contracts are normalized to a monthly-equivalent value) | The recurring subscription revenue base, excluding one-time fees and excluding usage-based charges above committed thresholds | Baseline denominator for NRR, GRR, LTV, and ARPA; the single number Finance and Sales leadership use to track recurring revenue health independent of one-time or usage variance |
| ARR (Annual Recurring Revenue) | MRR × 12 | Annualized view of MRR | Standard board- and investor-facing metric; used in the Revenue Intelligence Platform primarily for period-over-period and year-over-year comparison views |
| NRR (Net Revenue Retention) | (Starting MRR + Expansion MRR − Contraction MRR − Churned MRR) ÷ Starting MRR × 100, computed over the existing customer base only (excludes new-customer MRR) | Percentage of revenue retained and grown from the existing customer base over a period | Primary growth-stage health metric per Blueprint Section 4; the metric most sensitive to whether expansion is outpacing churn |
| GRR (Gross Revenue Retention) | (Starting MRR − Contraction MRR − Churned MRR) ÷ Starting MRR × 100 | Same as NRR but excludes expansion — GRR can never exceed 100% | Isolates retention from expansion; used to distinguish "we're growing because of upsell" from "we'd be shrinking without it" |
| Revenue | Sum of recognized revenue from Invoice records within the reporting period, per standard revenue recognition rules applied by Finance | Gross recognized revenue for the period, before deducting credits, refunds, or discounts | The top-line figure referenced on the Executive Dashboard's "Current Quarter Revenue" KPI card |
| Churn Rate | Generic term; in this platform, always qualified as either Customer Churn or Revenue Churn (defined below) — never used unqualified in any UI label or AI-generated text | Umbrella term for the rate at which customers or revenue are lost | Included here only to make explicit that this platform never displays an unqualified "churn rate" — ambiguity here is exactly the kind of discrepancy the platform exists to eliminate |
| Customer Churn | Number of Accounts churned in period ÷ Number of active Accounts at start of period × 100 | Count-based churn, independent of account size | Useful for the Head of Sales and Finance Manager personas assessing whether churn is concentrated in small accounts or spread evenly |
| Revenue Churn | MRR lost from churned and fully-downgraded Accounts in period ÷ Starting MRR × 100 | Dollar-weighted churn, sensitive to the size of accounts lost | The more financially meaningful churn figure for Finance and the executive team; large-account churn moves this number even if customer count churn looks stable |
| LTV (Customer Lifetime Value) | (ARPA × Gross Margin %) ÷ Revenue Churn Rate | Estimated total gross-margin revenue expected from an average Account over its lifetime | Used alongside CAC to assess unit economics; primarily relevant to the Business Analyst persona and to board reporting |
| CAC (Customer Acquisition Cost) | Total Sales & Marketing expense in period ÷ Number of new Accounts acquired in period | Average cost to acquire one new paying Account | Paired with LTV for unit economics review; sourced from Finance's expense data, not computed from platform-native entities alone |
| ARPA (Average Revenue Per Account) | Total MRR ÷ Number of active Accounts | Average recurring revenue contributed per Account | Used to compare revenue concentration across segments (Standard/Growth/Enterprise) and to feed the LTV calculation |
| Trial Conversion | Number of trial Accounts converting to a paid Contract within the defined trial window ÷ Number of trials started in period × 100 | Percentage of self-serve trials that convert to paying customers | Relevant primarily to Standard-tier self-serve onboarding (Blueprint Section 1); not meaningful for Enterprise, which does not use a trial motion |
| Renewal Rate | Number of Contracts renewed in period ÷ Number of Contracts up for renewal in period × 100 | Count-based renewal rate, distinct from revenue-based NRR/GRR | Used by the Head of Sales and Finance Manager to assess renewal execution independent of account size effects |
| Expansion Revenue | Additional MRR from existing Accounts upgrading tier, adding business units, or exceeding usage-based billing thresholds, within period | The MRR growth attributable specifically to existing customers, not new logos | Directly feeds the NRR formula and is tracked independently on the Usage-Based Billing Trends view, since usage-driven expansion is a distinct signal from tier upgrades |
| Net Revenue | Revenue (as defined above) minus refunds, credits, and discounts issued within the period | Recognized revenue after deductions, as opposed to the gross figure | The figure reconciled against Billing system totals on the Data Health Dashboard (Section 8.7); discrepancies between Revenue and Net Revenue that don't match expected discount/credit activity are a primary reconciliation flag |

---

# 20. Dashboard Layout

The following is the structural wireframe for the Executive Dashboard, extending the screen description in Section 9 and the KPI card specification in Section 10. The Revenue Trend chart and KPI cards below match Section 10 exactly; Revenue Breakdown, Top Customers, and Recent Alerts are the specific components that make up the "secondary supporting section" referenced in Section 9's Dashboard description, and Recent Alerts is the on-dashboard surfacing mechanism for Data Health Dashboard status (Section 8.7) — this wireframe does not introduce new scope beyond what Sections 8–10 already specify, it makes their layout explicit.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                    │
│ Kora Logo   Revenue Intelligence Platform     [Data Health: ● Healthy]   │
│                                              [Notifications] [User Menu] │
├───────────┬────────────────────────────────────────────────────────────┤
│ SIDEBAR   │ GLOBAL FILTERS                                              │
│           │ [Date Range: Current Quarter ▾] [Segment: All ▾]           │
│ Dashboard │ [Product Tier: All ▾]                                       │
│ Revenue   ├────────────────────────────────────────────────────────────┤
│ Analytics │ AI EXECUTIVE SUMMARY                                        │
│ Reports   │ ┌──────────────────────────────────────────────────────┐   │
│ Data      │ │ Generated: Jul 21, 2026, 06:12 AM                     │   │
│ Health    │ │ "NRR declined 3 points this month, driven primarily   │   │
│ AI        │ │  by contraction in the Growth segment [why]..."       │   │
│ Copilot   │ └──────────────────────────────────────────────────────┘   │
│ Settings  ├────────────────────────────────────────────────────────────┤
│           │ KPI CARDS                                                  │
│           │ ┌─────────┬─────────┬─────────┬─────────┬─────────┬──────┐│
│           │ │Current  │ NRR     │ Gross   │Pipeline │ Usage-  │Rec vs││
│           │ │Qtr Rev  │         │ Churn   │to Close │ Based   │Billed││
│           │ │$X.XM ▲  │ XX% ▼   │ X.X% ▲  │$X.XM    │Billing  │Var.  ││
│           │ └─────────┴─────────┴─────────┴─────────┴─────────┴──────┘│
│           ├────────────────────────────────┬───────────────────────────┤
│           │ REVENUE TREND                  │ REVENUE BREAKDOWN         │
│           │ (12-month line chart,          │ (by segment / tier,       │
│           │  current month dashed)         │  stacked bar or donut)    │
│           │                                 │                           │
│           ├────────────────────────────────┼───────────────────────────┤
│           │ TOP CUSTOMERS                  │ RECENT ALERTS             │
│           │ (table: Account, MRR,          │ (Data Health flags,       │
│           │  segment, renewal date,        │  reconciliation           │
│           │  sorted by MRR desc)           │  discrepancies, sync      │
│           │                                 │  staleness warnings)     │
├───────────┴────────────────────────────────┴───────────────────────────┤
│ FOOTER                                                                    │
│ Data as of: nightly sync, Jul 21, 2026, 03:00 AM   |   Version 1.0        │
└──────────────────────────────────────────────────────────────────────────┘
```

**Hierarchy notes:**
- The Data Health status indicator lives in the header, not buried in the layout, consistent with the Section 8.2 acceptance criterion that degraded status must be visible without navigation.
- AI Executive Summary sits above the KPI cards intentionally — for the CEO and COO personas (Section 5), the summary is the primary entry point, and the KPI cards serve as supporting detail for a claim already read, not the first thing scanned.
- Revenue Breakdown, Top Customers, and Recent Alerts are secondary, below-the-fold content. They support drill-down curiosity but are not required reading to answer "how is revenue doing" — that answer is fully contained in the Summary and KPI cards above them.
- Recent Alerts on the dashboard is a summary view only (most recent 3–5 items); the full Data Health Dashboard (Section 9, Section 8.7) remains the authoritative detail screen and is reached via the sidebar or by clicking through an alert.

---

# 21. API Architecture Boundaries

These are binding architectural rules for this platform, not suggestions. Any implementation that violates one of these should be treated as a defect regardless of whether it otherwise passes functional acceptance criteria.

- **Frontend communicates only through the REST API.** The frontend application has no direct connection to Snowflake, the Billing service database, Salesforce, or any other data source. Every screen defined in Section 9 is served exclusively by this platform's own backend API.
- **No direct database access, from any client.** This includes internal tooling and ad hoc scripts — if a Data & Analytics team member needs to inspect platform data outside the API, that need should be raised as a feature request (e.g., an admin export), not worked around with a direct connection string.
- **AI requests go through the backend only.** Neither the Executive Summary generation job nor the AI Copilot calls the Anthropic Claude API directly from the frontend. All model calls are proxied through the backend, which is also where the grounding mechanism described in Section 11 (translating natural-language questions into structured queries against the platform's own data access layer) is enforced. This is also the point at which the requesting user's role and permission scope (Section 12) are attached to every AI request, so permission enforcement cannot be bypassed by a client that simply omits the check.
- **JWT authentication on every request.** As specified in Section 8.1, every API endpoint validates the JWT signature and expiry server-side. There is no internal or "trusted" endpoint exempted from this — including endpoints called only by scheduled backend jobs (e.g., the Executive Summary generation job), which authenticate using their own service-level credentials rather than being left unauthenticated.
- **Role-based authorization is enforced at the API layer, not the UI layer.** The permissions matrix in Section 12 is implemented as server-side authorization checks on every relevant endpoint. The frontend hiding a filter or button (e.g., the rep-level filter for Analyst role, per Section 10) is a UX convenience, not a security control — the corresponding API endpoint must independently reject an unauthorized request even if it somehow reached the backend directly.
- **Every business action is logged.** Consistent with Section 13 (Reports) and Section 15 (Audit), any action that reads sensitive data, exports a report, dismisses a Data Health discrepancy, or changes a user's role produces a log entry with actor, timestamp, and action detail. Read-only navigation between screens is logged at the access-log level (Section 15, Logging); the specific business actions called out in Section 15 (Audit) are logged additionally at the audit level.
- **Every endpoint is versioned.** All endpoints are exposed under a `/v1` prefix, consistent with the API versioning approach described in Blueprint Section 8. Breaking changes to an endpoint's contract require a new version (`/v2`); they are never introduced as an in-place change to `/v1` that could silently break the frontend or any future integration built against it.
- **Errors use a unified response format.** Every error response, regardless of endpoint or failure type, follows the same structure:

```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Rep-level detail is not available for your role.",
    "requestId": "a1b2c3d4-...",
    "timestamp": "2026-07-21T14:32:00Z"
  }
}
```

  The `code` field is a stable, machine-readable identifier (used by the frontend to drive the specific error states defined in Section 14 — e.g., `PERMISSION_DENIED`, `AI_UNAVAILABLE`, `DATA_UNAVAILABLE`, `SYNC_STALE`); the `message` field is human-readable and safe to display directly to the user; `requestId` supports tracing a specific failure through the logging pipeline (Section 15) when a user reports an issue.
