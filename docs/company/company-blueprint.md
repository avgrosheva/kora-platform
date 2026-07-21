# Kora Technologies — Company Blueprint

Internal reference document. Audience: new engineers during onboarding. This document describes how the company works today, not how we'd like it to work eventually. If something here seems inefficient, it probably is — that's usually the point of including it.

---

# 1. Company Overview

## Mission

Kora helps mid-sized and enterprise companies run the operational backbone of their business — subscriptions, customer accounts, billing, and the internal processes that connect them — without stitching together five different vendors that don't talk to each other.

## Vision

Most companies our customers' size run their subscription and customer operations across a patchwork of tools: a billing system, a CRM, a support desk, and a pile of spreadsheets that quietly become load-bearing. We want Kora to be the system of record that replaces that patchwork, not another tool added to it.

## Core Values

These are the things that actually get referenced in day-to-day decisions, not a poster in the office.

- **Boring is a feature.** For infrastructure that customers depend on to run billing and customer data, predictability beats cleverness. We optimize for systems that behave the same way at 3am as they do in a demo.
- **Ship what you can support.** Every team that ships a feature owns its on-call rotation for that feature for at least two quarters. This keeps engineering honest about complexity.
- **Data has one home.** Every business entity has exactly one system of record. When two systems disagree about a customer's status, that's a bug, not a sync delay.
- **Customers don't read changelogs.** If a change affects billing, invoicing, or account status, it goes through a deliberate rollout process, not a deploy.
- **Write it down.** Decisions that aren't documented get re-litigated every six months by someone who wasn't in the room the first time.

## Business Model

Kora is a B2B SaaS company selling subscription and customer operations software directly to mid-market and enterprise companies, primarily through a sales-led motion with an increasing self-serve on-ramp for smaller accounts that later expand into managed accounts.

## Revenue Model

- Tiered annual contracts (Standard, Growth, Enterprise), billed annually or quarterly.
- Usage-based add-on fees for transaction volume above contracted thresholds (relevant mainly to Growth/Enterprise tiers processing high subscriber counts).
- Implementation and onboarding fees for Enterprise contracts, recognized separately from subscription revenue.
- No usage-based pricing for smaller accounts — those are flat annual fees to keep the sales cycle short.

## Target Customers

- Mid-market companies (roughly 150–2,000 employees) running subscription businesses: media, B2B software, membership organizations, education platforms.
- Enterprise accounts (2,000+ employees) with complex billing needs — multiple business units, multi-currency, contract-based custom pricing.
- We do not target consumer subscription businesses or very small businesses (under ~50 employees); our onboarding and support model isn't built for that volume of low-touch accounts.

## Pricing Philosophy

Price around the value of consolidation, not per-seat. Most competitors price per user; we price on account complexity (number of billing entities, transaction volume, integration count) because our buyers are optimizing for fewer systems, not fewer logins. This means Sales needs decent visibility into a prospect's actual operational complexity before quoting — a recurring pain point covered later in this document.

## Growth Stage

Series B, roughly 30 months post-Series A. Revenue is growing primarily through expansion within existing accounts (upsell to higher tiers, additional business units) rather than pure new-logo growth, which is starting to change how Sales and Customer Success are organized.

## Funding Stage

Series B. Board includes two investor seats. The company is not yet profitable but has a defined runway and a board-approved path to default-alive status within the next several quarters.

## Organization Size

Approximately 200 employees.

- Engineering & Product: ~70
- Sales & Marketing: ~45
- Customer Success & Support: ~35
- Operations, Finance, HR, Legal: ~25
- Data & Analytics: ~15
- Executive & Management: ~10

## Engineering Culture

- Small, autonomous teams (4–7 engineers) organized around business domains, not technical layers.
- Roadmap planning happens quarterly; execution happens in two-week cycles.
- Every team has a PM and a designer embedded, not shared across too many teams.
- Postmortems are blameless and mandatory for any incident that touches billing accuracy or customer-facing downtime over 15 minutes.
- Engineers are expected to read support tickets related to their area at least monthly. This is enforced socially, not by tooling, and compliance is inconsistent — noted later as a real problem.

---

# 2. Company Structure

## Departments

**Engineering**
Organized into domain-oriented teams: Billing & Payments, Customer Platform, Integrations, Core Infrastructure, and (newly forming) Internal Tools. Each team owns services end-to-end, including on-call.

**Product**
One VP of Product overseeing product managers assigned per engineering domain. Product owns roadmap prioritization, works directly with Sales and CS to understand account-specific requests, and maintains the public API contract.

**Data & Analytics**
A relatively new, centralized team (formed about a year ago) responsible for the data warehouse, reporting infrastructure, and analytics support for every other department. Currently the most requested and most understaffed team in the company.

**Sales**
Split into New Business (net-new logo acquisition) and Expansion (upsell/cross-sell into existing accounts). Sales Engineering sits alongside both, handling technical scoping for complex Enterprise deals.

**Customer Success & Support**
CS owns the ongoing relationship with paying accounts post-close: onboarding, adoption, renewal risk. Support is a separate function handling reactive ticket resolution, tiered L1/L2/L3.

**Marketing**
Demand generation, content, and product marketing. Smaller team relative to Sales; most pipeline still comes from outbound and existing-customer referral, not inbound.

**Operations & Finance**
Handles billing operations (yes, we sell billing software and also run our own), vendor contracts, and financial reporting to the board. Finance closely tracks revenue recognition given the mix of subscription and usage-based billing.

**People/HR & Legal**
Standard functions; Legal is disproportionately busy given the number of enterprise contracts with custom terms and data processing agreements.

## Responsibilities of Each Department (Summary Table)

| Department | Owns | Does Not Own |
|---|---|---|
| Engineering | System architecture, uptime, code quality | Feature prioritization |
| Product | Roadmap, requirements, API contracts | Implementation details |
| Data & Analytics | Warehouse, reporting, cross-team metrics definitions | Source system data models |
| Sales | Pipeline, quoting, closing | Contract legal terms (Legal owns final language) |
| Customer Success | Adoption, renewal, expansion conversations | Technical support tickets |
| Support | Ticket resolution, incident communication to customers | Product roadmap decisions |
| Marketing | Positioning, campaigns, content | Sales quota-bearing conversations |
| Operations & Finance | Internal billing accuracy, revenue recognition, vendor management | Customer-facing billing product decisions |

## Daily Workflows

- Engineering teams run daily standups within their domain team; cross-team syncs happen weekly.
- Support triages incoming tickets each morning, escalating anything account-at-risk to CS same-day.
- Sales reps update CRM stage and next steps daily; Sales Ops pulls a pipeline snapshot every morning for leadership.
- Data & Analytics runs overnight batch jobs to refresh the warehouse; anyone needing same-day numbers before 9am is usually out of luck, which is a recurring source of friction with Sales leadership wanting live pipeline numbers.

## How Departments Interact

- **Sales → Product**: Deal-specific feature requests get logged in a shared request tracker. In practice, urgent requests from a big deal in the final stage often bypass this and go straight to a PM via Slack, which causes prioritization friction.
- **CS → Product**: Renewal risk and adoption data are supposed to inform roadmap prioritization, but CS's view of "risk" lives in a different system (CRM notes) than Product's view of usage (product analytics), so this connection is manual and inconsistent today.
- **Support → Engineering**: Bug reports flow through a ticketing system with an engineering escalation path. Chronic complaint: Engineering doesn't have visibility into ticket volume/trends without asking Support directly or pulling a manual export.
- **Finance → Sales**: Quote approval for anything outside standard pricing bands requires Finance sign-off, which is a common bottleneck in deal cycles.
- **Data & Analytics → Everyone**: Every department requests custom reporting from Data & Analytics, whose backlog is consistently 4–6 weeks out. This is one of the most cited internal pain points.

## Main Internal Pain Points

1. **No unified view of a customer.** Sales sees CRM data, Support sees ticket history, Product sees usage events, Finance sees billing history. Answering "is this a healthy account?" requires pulling from four systems and often four different people.
2. **Revenue and forecasting data is fragmented and lagging.** Finance's revenue recognition data, Sales' pipeline data, and actual usage-based billing data don't reconcile automatically. Month-end close involves manual reconciliation.
3. **Data & Analytics is a bottleneck.** A 15-person team serving a 200-person company means most requests queue for weeks. Departments have started building their own spreadsheet-based shadow reporting, which then disagrees with the official warehouse numbers.
4. **Engineers lack lightweight internal tools.** There is no internal system for looking up account status, debugging a customer's billing state, or checking feature flag configuration without going through the production database or asking another team. This slows down both support escalations and engineering debugging.
5. **Institutional knowledge lives in people, not systems.** Sales knows why a deal was priced a certain way; Support knows why a customer is annoyed; none of this is centrally searchable.

These five pain points are the direct motivation for the three internal platforms described in Section 6.

---

# 3. Business Processes

## Customer Lifecycle

1. **Lead** — Marketing-sourced or outbound-sourced, enters CRM.
2. **Qualified Opportunity** — Sales Engineering scopes technical fit for mid-market/enterprise deals.
3. **Closed/Won** — Contract signed, handed to Implementation (a function within CS for Enterprise, self-serve for smaller Standard-tier accounts).
4. **Onboarding** — Typically 2–6 weeks depending on tier and integration complexity.
5. **Active/Adoption** — CS monitors usage and health; this is the longest phase.
6. **Renewal or Expansion** — Handled by Expansion Sales in partnership with CS, roughly 60–90 days before contract end.
7. **Churn or Downgrade** — Tracked with a mandatory exit reason logged by CS; these reasons feed (imperfectly, today) into Product prioritization.

## Sales Lifecycle

Lead → Discovery Call → Technical Scoping (Enterprise only) → Proposal/Quote → Negotiation → Legal Review (custom terms) → Closed/Won → Handoff to CS.

Standard-tier deals can skip technical scoping and legal review in most cases, which is why they close in an average of 3 weeks versus 3–4 months for Enterprise.

## Support Lifecycle

Ticket submitted → L1 triage (response SLA depends on tier: 4 hours for Enterprise, 1 business day for Standard) → Resolved at L1, or escalated to L2 (product specialists) → Escalated to L3 (engineering on-call) if it's a bug, not a usage question → Resolution communicated to customer → Ticket closed with a category tag used later for trend analysis (though this tagging is inconsistently applied, which limits how useful the trend data actually is).

## Product Development Lifecycle

1. **Intake** — Requests come from Sales/CS trackers, Support ticket trends, and direct customer interviews run by Product.
2. **Quarterly Planning** — Each domain team's PM prioritizes a quarter's worth of work against roadmap themes set by VP of Product and reviewed with the executive team.
3. **Discovery** — Small technical spikes for anything architecturally uncertain before committing a full cycle.
4. **Build** — Two-week cycles, domain team owns implementation.
5. **Rollout** — Feature-flagged rollout, gradual exposure starting with internal accounts, then Standard tier, then Enterprise (Enterprise customers are more sensitive to unannounced change, so their rollout is manual and communicated in advance).
6. **Post-launch review** — Usage and support ticket impact reviewed 30 days post-launch.

## How Data Flows Through the Company

- Production application databases (per-domain: Billing, Customer/Account, Support) are the systems of record for their respective domains.
- Nightly batch jobs extract from production databases into the central data warehouse.
- Data & Analytics builds and maintains transformed models on top of the warehouse (a fairly standard ELT setup) for reporting.
- CRM (Sales/CS) and the support ticketing tool are third-party SaaS products, not internally built, and are two of the four sources feeding the warehouse.
- Today, there is no real-time or near-real-time data flow between production systems and any cross-functional reporting — everything is nightly batch. This is a known limitation, and it's directly relevant to why the Revenue Intelligence Platform is being built (see Section 6).

## Main Business Entities

- **Account** — A company that is a Kora customer. Has one or more Contracts.
- **Contract** — A specific agreement: tier, pricing, term length, billing frequency.
- **Subscription** — What the Account's own end-customers are subscribed to, managed via Kora's product on the Account's behalf (this is the "customers of our customers" layer — important not to confuse with our own Accounts).
- **User** — An individual person with login access to Kora, belonging to an Account.
- **Invoice** — Generated against a Contract, may include usage-based line items.
- **Ticket** — A support interaction, associated with an Account and optionally a User.
- **Opportunity** — A Sales pipeline entity, becomes a Contract when closed/won.
- **Usage Event** — Raw product usage data, the input to usage-based billing and to product analytics.

## Relationships Between Entities

- An **Account** has one or more **Contracts** over its lifetime (renewals create new Contract records; they aren't edited in place, for audit reasons).
- A **Contract** has many **Invoices**.
- An **Account** has many **Users**.
- An **Account**'s end customers generate many **Subscriptions** and many **Usage Events** — this is the data our own customers manage using Kora, and it's high-volume relative to everything else in the system.
- A **Ticket** belongs to one **Account** and optionally one **User**.
- An **Opportunity** converts into exactly one **Contract** on close/won; it never converts into more than one, which has occasionally caused reporting confusion during multi-year, multi-phase enterprise deals that get modeled as separate Opportunities instead.

---

# 4. Critical KPIs and How Success Is Measured

| KPI | Owner | Why It Matters |
|---|---|---|
| Net Revenue Retention (NRR) | Executive team / CS | Primary growth-stage health metric; expansion revenue matters more than new logos right now |
| Gross churn rate | CS | Distinguishes "we're growing despite churn" from "we have a retention problem" |
| Sales cycle length (by tier) | Sales | Enterprise cycle length directly affects quarterly forecasting accuracy |
| Support SLA compliance | Support | Contractual obligation for Enterprise tier; breach has financial penalty clauses |
| Time-to-value (onboarding to first active usage) | CS / Product | Leading indicator of renewal risk |
| Deployment frequency / change failure rate | Engineering | Standard engineering health metrics, reviewed monthly |
| Data request turnaround time | Data & Analytics | Internal-facing metric, currently the team's worst-performing number and an acknowledged organizational problem |
| Revenue recognized vs. billed | Finance | Reconciliation accuracy, audited quarterly |

Success at the company level is measured primarily by NRR and a defined path to default-alive status, both tracked and reported to the board quarterly. Department-level success measures roll up into these but aren't identical to them — Support being fast doesn't matter if it's not converting into retention, for instance.

---

# 5. Existing Software Stack

## Internally Built

- **Billing & Payments service** — core system of record for contracts, invoicing, usage-based charges.
- **Customer/Account platform** — account and subscription management, the product customers actually use to manage their own subscribers.
- **Public API** — the primary integration surface for customers connecting Kora to their own systems.

## Third-Party (Vendor) Tools

- **CRM** — Salesforce, used by Sales and CS.
- **Support ticketing** — Zendesk.
- **Data warehouse** — Snowflake, with a standard ELT pipeline (Fivetran-style connectors plus custom extraction jobs for internal databases).
- **BI/reporting layer** — Looker, maintained by Data & Analytics.
- **Payments processing** — Stripe, underlying actual payment execution (Kora's billing service handles logic and invoicing; Stripe handles the money movement).
- **Internal communication** — Slack, Google Workspace.
- **Incident management** — PagerDuty.
- **Feature flagging** — LaunchDarkly.

## Third-Party Integrations (Customer-Facing)

Kora's platform integrates with common tools our customers already use: accounting systems (for revenue sync), tax calculation providers, and a handful of CRM/marketing platforms for customer data sync. These integrations are maintained by the Integrations engineering team and are a meaningful source of Enterprise sales objections when a required integration doesn't exist yet.

---

# 6. Current Problems That Require Internal Software

The pain points in Section 2 aren't abstract — they translate into three concrete internal engineering efforts. This section explains why each exists. These are not hypothetical future products; they are the next things Engineering is building, and they are why new engineers are being hired right now.

## Why the Revenue Intelligence Platform Needs to Exist

Finance, Sales leadership, and the executive team currently reconcile revenue, pipeline, and usage-based billing data manually, monthly, across Salesforce, the Billing service, and Snowflake exports. This is slow (multi-day close process), error-prone (numbers regularly disagree between systems until reconciled by hand), and entirely backward-looking (nightly batch, no intra-month visibility into forecast accuracy).

The Revenue Intelligence Platform exists to give Finance, Sales leadership, and the executive team a single, reliable, close-to-real-time view of revenue: recognized revenue, pipeline-to-close forecasting, usage-based billing trends, and NRR/churn broken down by segment — without a human manually stitching together CRM exports and billing exports every month-end. This is an internal analytics and forecasting system, not a customer-facing product.

## Why the Customer Intelligence Platform Needs to Exist

No single person in the company can currently answer "is this account healthy?" without pulling from CRM notes (Sales/CS), ticket history (Zendesk), and usage data (product analytics), each maintained separately with no shared account health concept. CS's renewal risk assessments are subjective and undocumented; Support's ticket trends rarely make it back to Product in a structured way; Product's usage data rarely informs CS's renewal conversations.

The Customer Intelligence Platform exists to unify account-level signals — usage trends, support ticket history and sentiment, contract and billing status, and CS-logged health notes — into a single internal view, used by CS for renewal prep, by Support for context on escalations, and by Product for prioritization input. This is the internal system that finally gives every customer-facing team the same picture of an account.

## Why the Internal AI Workspace Needs to Exist

Institutional knowledge at Kora currently lives in people's heads, old Slack threads, and scattered Notion pages that go stale. Engineers debugging a production issue can't easily look up why a customer's account is configured the way it is; Support agents can't quickly find whether a similar issue was resolved before; new hires spend weeks re-discovering things that were already figured out by someone else six months ago.

The Internal AI Workspace exists as an internal tool — search and assistance over Kora's own internal documentation, past support resolutions, and internal runbooks — to reduce the time employees across Engineering, Support, and CS spend hunting for information that already exists somewhere in the company. It is explicitly an internal productivity tool, not a customer-facing AI feature.

---

# 7. Future Vision

Over the next 18–24 months, the intent is for these three internal platforms to become the connective layer between departments that today only exists through manual exports and tribal knowledge. Longer-term, as the company scales past 200 employees, the goal is that no cross-department question — "is this account at risk," "what's our real-time revenue picture," "has anyone solved this problem before" — requires asking three different people in three different tools to get an answer. Whether these internal platforms eventually get productized as customer-facing offerings is an open question the executive team has discussed but not committed to; for now, they are internal infrastructure, built to make Kora's own 200 employees more effective at running the business.

---

# 8. Engineering Stack

This is the production stack as it exists today, not an aspirational list. Some of these choices predate the current engineering leadership and are kept for continuity reasons rather than because we'd pick them again from scratch — noted where relevant.

| Layer | Technology | Why We Chose It |
|---|---|---|
| Frontend | React + TypeScript (Next.js for the customer-facing app shell) | Largest available hiring pool for a company our size; Next.js gives us server-rendering for the parts of the product that need fast initial load without a separate rendering team. |
| Backend | Python (Django) for the majority of services; Go for the Billing ledger service | Python/Django lets domain teams move quickly and keeps onboarding time low. The Billing ledger (the source of truth for money) is written in Go specifically for its stricter concurrency guarantees and lower operational surprises under load — this was a deliberate exception, not a stack fragmentation accident. |
| API | REST, versioned (`/v1`, `/v2`), documented with OpenAPI | Customers integrate directly with our API; REST plus a stable OpenAPI contract is easier for external engineering teams to consume than GraphQL, and it's what our Enterprise customers' own integration teams expect. |
| Database | PostgreSQL (primary OLTP store, one instance per domain: Billing, Customer/Account, Support) | Strong transactional guarantees matter more than horizontal write scale for our data volumes today; Postgres also gives us mature tooling for the audit and reconciliation requirements that come with billing data. |
| Analytics Warehouse | Snowflake | Already covered in Section 5 — separates analytical workloads from production databases, which protects OLTP performance and lets Data & Analytics run heavy queries without risking customer-facing latency. |
| ORM | Django ORM (Python services), sqlc for the Go billing service | Django ORM is the path of least friction for CRUD-heavy domain services. The Go billing service intentionally avoids a full ORM in favor of sqlc-generated, hand-reviewed SQL — correctness in financial queries is worth the extra verbosity. |
| Authentication | Auth0, with SAML/SSO for Enterprise tier | Building and maintaining SSO/SAML in-house isn't a good use of engineering time at our size; Auth0 covers the compliance and enterprise-IT expectations our larger customers require during procurement. |
| AI | Anthropic Claude (API) | Used both as the model layer for customer-facing product features and, increasingly, as the underlying model for the Internal AI Workspace described below. Chosen for a combination of output quality and a usable API surface for tool use, which the Workspace product depends on directly. |
| Automation | Temporal (billing workflows), Apache Airflow (data pipelines) | Temporal handles long-running, retry-heavy processes like invoice generation and dunning, where "did this actually complete" matters. Airflow orchestrates the nightly ELT jobs feeding the warehouse — separate tools for separate failure modes. |
| Message Queue | Kafka (usage events), Amazon SQS (internal service-to-service jobs) | Usage events arrive at a volume and rate that benefit from Kafka's durability and replay guarantees, since usage data feeds both billing and product analytics and can't be silently dropped. SQS is simpler and sufficient for lower-volume internal task queues. |
| Cache | Redis | Standard choice for session storage, rate limiting, and hot-path lookups (e.g., account status checks during API requests); nothing exotic needed here. |
| Object Storage | Amazon S3 | Stores invoices, exported reports, and uploaded customer files; the default choice given the rest of the infrastructure already sits on AWS. |
| Monitoring | Datadog | Single pane of glass for metrics, APM, and infrastructure monitoring; reduces the number of dashboards an on-call engineer needs to check during an incident. |
| CI/CD | GitHub Actions, ArgoCD (GitOps deploys to Kubernetes) | GitHub Actions keeps CI configuration next to the code it tests; ArgoCD gives us auditable, declarative deploys, which matters given the postmortem and change-management culture described in Section 1. |
| Infrastructure | AWS, provisioned with Terraform | AWS predates the current infrastructure team and switching providers isn't justified at our scale; Terraform gives us reviewable, versioned infrastructure changes rather than manual console changes. |
| Containerization | Docker, orchestrated with Kubernetes (EKS) | Standard for our team size — lets each domain team own its own deployment without needing deep Kubernetes expertise on every team, since a shared Infrastructure function manages the cluster. |
| Logging | Datadog Log Management | Consolidated with monitoring rather than run as a separate ELK stack — one less system to operate and correlate against metrics and traces during incidents. |
| Analytics | Amplitude (product usage analytics), feeding into Snowflake | Amplitude captures product usage events at the interaction level for Product and CS; those events are also piped into the warehouse so Data & Analytics doesn't have to maintain two separate definitions of "usage." |
| Documentation | Notion (general company/process docs), Swagger/OpenAPI UI (API docs) | Notion is already the default company-wide tool (Section 3 references it implicitly through process documentation); API documentation is kept separate and generated directly from the OpenAPI spec so it can't drift from the actual contract. |

---

# 9. Internal Engineering Products

## Revenue Intelligence Platform

**Purpose:** Give Finance, Sales leadership, and the executive team a single, reliable, close-to-real-time view of revenue — recognized revenue, pipeline-to-close forecasting, and usage-based billing trends — without a manual month-end reconciliation across Salesforce, the Billing service, and Snowflake exports.

**Primary Users:** Finance, Sales leadership, executive team, Data & Analytics (as maintainers).

**Business Problems Solved:** Fragmented revenue and pipeline data (Section 2, pain point 2); multi-day manual month-end close; no intra-month forecast visibility; numbers disagreeing across CRM, Billing, and warehouse exports until manually reconciled.

**Product Owner:** VP of Product, in partnership with the Head of Data (the platform's data model and pipeline reliability are owned by Data & Analytics; the product surface and prioritization are owned by Product).

**Current Status:** In active development. Core data model (unifying Contract, Invoice, and Opportunity entities into a single reporting layer) is built; the forecasting module is in discovery.

**Future Direction:** Move from nightly batch to near-real-time ingestion for the metrics Sales leadership checks most often (pipeline-to-close, current-quarter bookings); eventually expose a scoped, read-only view to CS for renewal-adjacent revenue context, at which point it starts to overlap with the Customer Intelligence Platform and the two products will need a defined data-sharing boundary.

## Customer Intelligence Platform

**Purpose:** Unify account-level signals — usage trends, support ticket history, contract and billing status, and CS-logged health notes — into a single internal view of account health.

**Primary Users:** Customer Success (renewal prep), Support (escalation context), Product (prioritization input).

**Business Problems Solved:** No single person can currently answer "is this account healthy?" without pulling from four separate systems (Section 2, pain point 1); CS's renewal risk assessments are subjective and undocumented; Support ticket trends rarely make it back to Product in structured form.

**Product Owner:** VP of Product, with a CS operations lead as the primary internal stakeholder defining what "account health" should actually mean in practice.

**Current Status:** Early build. Account health scoring logic exists as a first draft based on usage trend and ticket volume; CS health notes are not yet integrated because they currently live as unstructured text in Salesforce and need a defined schema before they can feed a scoring model.

**Future Direction:** Structured CS health notes (replacing free-text CRM notes with a defined taxonomy), automated renewal-risk alerts surfaced to CS ahead of the standard 60–90 day renewal window, and a read-only Support-facing view so agents get account context without needing CS to relay it manually.

## Internal AI Workspace

**Purpose:** Provide search and assistance over Kora's own internal documentation, past support resolutions, and internal runbooks, so employees stop losing time re-discovering information that already exists somewhere in the company.

**Primary Users:** Engineering (debugging context, runbooks), Support (prior resolution lookup), new hires across all departments (onboarding).

**Business Problems Solved:** Institutional knowledge living in people's heads and stale Notion pages (Section 2, pain point 5); engineers lacking lightweight tooling to look up account or billing configuration context without production database access; new hires spending weeks re-discovering already-solved problems.

**Product Owner:** Principal Software Architect, with Support operations as the primary early stakeholder since the first use case is ticket-resolution search.

**Current Status:** Prototype stage. Internal documentation and closed-ticket corpus have been indexed; retrieval quality is inconsistent across older, poorly tagged tickets, and there's no engineering-facing tool for account/billing state lookup yet — that's currently listed as a stretch goal for this product rather than a separate one.

**Future Direction:** Expand the indexed corpus to include internal Slack threads (with appropriate access controls) and postmortems; add the account/billing state lookup tool for engineers referenced in Section 2 as a chronic gap; evaluate whether this eventually needs role-based access controls once it indexes anything customer-identifiable, given the Enterprise data processing agreements Legal already manages.

---

# 10. Organization Structure

```
CEO
├── Product (VP of Product)
│   ├── PM — Billing & Payments
│   ├── PM — Customer Platform
│   ├── PM — Integrations
│   └── PM — Internal Tools (Revenue Intelligence, Customer Intelligence, Internal AI Workspace)
├── Engineering (CTO)
│   ├── Billing & Payments team
│   ├── Customer Platform team
│   ├── Integrations team
│   ├── Core Infrastructure team
│   └── Internal Tools team
├── Data & Analytics (Head of Data)
│   ├── Analytics Engineering
│   └── BI / Reporting
├── Sales (VP of Sales)
│   ├── New Business
│   ├── Expansion
│   └── Sales Engineering
├── Marketing (VP of Marketing)
│   ├── Demand Generation
│   └── Product Marketing
├── Customer Success & Support (VP of Customer Success)
│   ├── Customer Success (Onboarding, Adoption, Renewal)
│   └── Support (L1/L2/L3)
├── Operations & Finance (COO / CFO)
│   ├── Billing Operations
│   ├── Financial Reporting
│   └── Vendor Management
└── People/HR & Legal (Head of People)
    ├── HR
    └── Legal
```

Note: the Internal Tools engineering team and its corresponding PM line are recent additions, formed specifically to build and maintain the three platforms described in this document. Before this, internal tooling work was absorbed ad hoc by whichever domain team had spare capacity, which is part of why these problems went unaddressed for as long as they did.

---

# 11. High-Level Data Flow

```
 External Services (Stripe, Salesforce, Zendesk, accounting/tax integrations)
            │
            ▼
 Operational Databases (Billing, Customer/Account, Support — PostgreSQL, per domain)
            │
            ▼
 Analytics Warehouse (Snowflake, nightly ELT via Airflow)
            │
            ├──────────────────────────────┬───────────────────────────────┐
            ▼                              ▼                               ▼
 Revenue Intelligence Platform   Customer Intelligence Platform   Internal AI Workspace
 (revenue, pipeline, usage           (account health, usage,        (internal docs, support
     billing trends)                ticket trends, CS notes)         resolutions, runbooks)
            │                              │                               │
            ▼                              ▼                               ▼
       Executives,                  Customer Success,                Engineering,
      Finance, Sales               Support, Product                 Support, new hires
```

Today, everything below the warehouse layer runs on the same nightly batch cadence — there is no near-real-time path anywhere in this diagram yet. That's the single biggest limitation driving the "future direction" notes for all three platforms in Section 9.

---

# 12. Current Engineering Challenges

| # | Problem | Business Impact | Current Manual Process | Desired Future State | Internal Product Responsible |
|---|---|---|---|---|---|
| 1 | Month-end revenue reconciliation across CRM, Billing, and warehouse exports is manual | Multi-day close process; numbers disagree until manually reconciled; delays board reporting | Finance analyst manually cross-references Salesforce exports, Billing invoicing data, and Snowflake reports in a spreadsheet | Automated, single-source revenue view that reconciles continuously, not once a month | Revenue Intelligence Platform |
| 2 | No intra-month visibility into forecast-vs-actual | Leadership can't tell if the quarter is on track until it's nearly over | Sales Ops pulls a manual pipeline snapshot each morning; no automated comparison against billing actuals | Live pipeline-to-close view cross-referenced against actual usage-based billing trends | Revenue Intelligence Platform |
| 3 | Usage-based billing trends aren't visible until the nightly batch runs | Finance and Sales can be surprised by usage spikes or drop-offs a full day after they happen | Support/CS notice a billing anomaly only after a customer complains or the invoice is generated | Same-day or near-real-time usage trend visibility tied to billing thresholds | Revenue Intelligence Platform |
| 4 | No single person can answer "is this account healthy?" without checking four systems | Slows renewal prep, escalation triage, and roadmap prioritization; inconsistent answers depending on who's asked | CS manually checks CRM notes, Support checks Zendesk history, Product checks usage analytics separately, with no shared definition of "health" | One account health view combining usage, tickets, billing, and CS notes | Customer Intelligence Platform |
| 5 | CS renewal risk assessment is subjective and undocumented | Renewal risk is caught late or missed entirely for accounts without an attentive CS rep | Risk is a judgment call logged (inconsistently) as free text in Salesforce notes | Structured, scored renewal risk model surfaced automatically ahead of the renewal window | Customer Intelligence Platform |
| 6 | Support ticket trends rarely reach Product in structured form | Product roadmap decisions miss recurring pain points that Support already knows about | Product occasionally requests a manual ticket export from Support when preparing quarterly planning | Ticket trend data feeding directly into account health and roadmap prioritization views | Customer Intelligence Platform |
| 7 | Expansion opportunities are only noticed when a CS rep happens to spot them | Missed upsell revenue, inconsistent expansion motion across accounts depending on rep attentiveness | CS manually reviews usage during renewal prep, close to the deadline, not continuously | Usage-based expansion signals surfaced proactively, well before the renewal conversation | Customer Intelligence Platform |
| 8 | Institutional knowledge lives in people's heads, old Slack threads, and stale Notion pages | New hires re-discover already-solved problems; repeated questions burn senior engineers' time | Employees ask in Slack and wait for whoever remembers the answer | Searchable internal knowledge base surfacing documentation, past resolutions, and runbooks | Internal AI Workspace |
| 9 | Support agents can't quickly check whether a similar issue was resolved before | Slower ticket resolution, inconsistent answers to the same recurring question across agents | Agents search Zendesk manually by keyword, with mixed results depending on how the original ticket was tagged | Semantic search across past resolutions surfacing relevant precedent automatically | Internal AI Workspace |
| 10 | Engineers have no lightweight way to inspect an account's billing/config state while debugging | Debugging and support escalations take longer than necessary; engineers fall back to direct production database queries | An engineer queries the production database directly or asks another team for a manual lookup | A scoped internal tool for read-only account/billing state lookup, without direct DB access | Internal AI Workspace (planned extension) |
| 11 | Data & Analytics' request backlog runs 4–6 weeks, causing departments to build shadow spreadsheet reporting | Duplicate, conflicting numbers circulate across departments; trust in the "official" warehouse numbers erodes | Departments build their own ad hoc spreadsheets when official reporting is too slow to wait for | Self-service reporting for the most common cross-functional questions, reducing one-off request volume | Revenue Intelligence Platform / Customer Intelligence Platform (self-service views reduce ad hoc request load on Data & Analytics) |
