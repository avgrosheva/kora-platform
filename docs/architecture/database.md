# Revenue Intelligence Platform — Database Design Document

**Company:** Kora Technologies
**Database:** PostgreSQL (production)
**Document owner:** Principal Data Engineer / Database Architect, in partnership with Staff Backend Engineering
**Audience:** Backend engineering, data engineering, QA

This document is the schema-level source of truth for the Revenue Intelligence Platform's own database. It is consistent with the Company Blueprint (business entities: Account, Contract, Invoice, Subscription, Usage Event, Opportunity) and the PRD (KPI Dictionary, roles and permissions, Reports, AI Copilot, Data Health Dashboard). No new business concepts are introduced beyond what those two documents already establish — this document only makes them concrete at the schema level.

No SQL or ORM code is included here. This document describes structure and rationale; DDL is an implementation detail derived from it, not specified by it.

---

# 1. Database Overview

## Philosophy

This database is a **read-optimized, reconciliation-aware store**, not a system of record. The actual sources of truth remain the Billing service, Salesforce, and the Snowflake warehouse, as established in the Blueprint. This database exists to hold a normalized, query-efficient copy of the subset of that data the Revenue Intelligence Platform needs, plus the platform's own native data (AI conversations, generated reports, alerts, audit logs) that has no other home.

Three design principles follow from this:

1. **Ingested data is versioned, not overwritten silently.** Because this platform's core job is catching disagreement between source systems (Data Health Dashboard), the schema must be able to represent "what we last saw from source X" independently of "what we last saw from source Y" for the same real-world entity, rather than collapsing them into one mutable row the moment a sync runs.
2. **Everything financially meaningful is immutable once recorded.** Revenue records, invoices, and payments are never updated in place after initial ingestion; corrections are represented as new rows with a reference to what they correct. This matches how Finance already thinks about revenue recognition (Blueprint Section 3) and makes audit and reconciliation tractable.
3. **Native platform entities (AI conversations, reports, alerts) follow normal mutable-row conventions**, since they don't carry the same reconciliation and audit weight as financial data, but they are still fully audit-logged per Section 8.

## Engine and Baseline Choices

PostgreSQL is used consistent with Blueprint Section 8 (Database: PostgreSQL, one instance per domain). This platform's database is its own domain instance — it does not share a database with the Billing service, Customer/Account platform, or Support system. All primary keys are UUIDs (not auto-incrementing integers) to avoid leaking sequential business volume information across API responses and to allow safe merging of records synced from multiple source systems without key collision.

---

# 2. Entity Relationship Diagram

```
 countries ──┐
             │
 regions ────┼──────────────┐
             │              │
             ▼              ▼
        organizations ──────────────┐
             │                      │
             │ 1:N                  │ 1:N
             ▼                      ▼
         customers              sales_representatives
             │  │                   │
             │  │ 1:N                │ N:1 (assigned to)
             │  ▼                   │
             │ support_tickets ◄────┘ (assigned_rep_id, optional)
             │
             │ 1:N
             ▼
       subscriptions ───────────► subscription_plans ───────► products
             │        N:1                    N:1
             │
     ┌───────┼────────────┬─────────────┬──────────────┐
     │ 1:N   │ 1:N         │ 1:N          │ 1:N           │ 1:N
     ▼       ▼             ▼              ▼               ▼
 invoices  payments   revenue_records  renewals      feature_usage
     │
     │ 1:N
     ▼
 (invoice_line_items — see Section 3.10 note)

 currencies ◄──── referenced by: customers, subscriptions, invoices,
                   payments, revenue_records (currency_id, N:1 each)

 users ──── N:1 ──── roles
   │
   │ 1:N                         1:N
   ▼                              ▼
 ai_conversations ──1:N──► ai_messages
   │
   │ (also referenced by)
   ▼
 generated_reports (requested_by_user_id → users)
 alerts (acknowledged_by_user_id → users, nullable)
 audit_logs (actor_user_id → users, nullable for system-generated events)

 alerts ────► organizations / customers / subscriptions (polymorphic reference,
              see Section 3.19 — entity_type + entity_id, not a hard FK)
```

Notes on reading this diagram: `organizations` is the top-level company record — Kora's paying customer, matching the Blueprint's "Account" entity. `customers` represents individual billing entities or business units under an organization (Blueprint Section 1 notes Enterprise accounts often have "multiple business units, multi-currency, contract-based custom pricing" — this is modeled as one `organizations` row with multiple `customers` rows beneath it, each carrying its own currency and region). Everything below `customers` (subscriptions, invoices, payments, revenue_records, renewals, feature_usage) is scoped to a specific billing entity, not the organization as a whole, since that's the level at which actual billing occurs.

---

# 3. Tables

## 3.1 organizations

**Purpose:** The top-level company record — Kora's paying customer at the account level (Blueprint "Account"). One organization may contain multiple billing entities (`customers`) beneath it.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| name | VARCHAR(255) | No | — |
| legal_name | VARCHAR(255) | Yes | NULL |
| segment | VARCHAR(50) | No | — |
| region_id | UUID | No | — |
| country_id | UUID | No | — |
| domain | VARCHAR(255) | Yes | NULL |
| source_system | VARCHAR(50) | No | 'salesforce' |
| source_record_id | VARCHAR(100) | No | — |
| status | VARCHAR(30) | No | 'active' |
| created_at | TIMESTAMPTZ | No | now() |
| updated_at | TIMESTAMPTZ | No | now() |
| deleted_at | TIMESTAMPTZ | Yes | NULL |

**Primary Key:** id
**Foreign Keys:** region_id → regions.id; country_id → countries.id
**Unique Constraints:** (source_system, source_record_id) — prevents duplicate ingestion of the same source record
**Indexes:** btree on segment (dashboard filtering); btree on status; btree on region_id
**Relationships:** One organization has many customers (1:N). One organization has many sales_representatives assigned through the customers or directly (see 3.11).

**Example Record:**
```
id: 6f2a1e4c-...
name: "Northline Media Group"
segment: "Enterprise"
region_id: <North America region>
country_id: <United States>
source_system: "salesforce"
source_record_id: "0011x00000ABCDE"
status: "active"
```

## 3.2 customers

**Purpose:** A billing entity / business unit beneath an organization — the level at which subscriptions, invoices, and revenue are actually recorded. For most Standard-tier organizations there is exactly one customer row per organization; Enterprise organizations may have several.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| organization_id | UUID | No | — |
| name | VARCHAR(255) | No | — |
| currency_id | UUID | No | — |
| region_id | UUID | No | — |
| country_id | UUID | No | — |
| billing_email | VARCHAR(255) | Yes | NULL |
| source_system | VARCHAR(50) | No | 'billing_service' |
| source_record_id | VARCHAR(100) | No | — |
| status | VARCHAR(30) | No | 'active' |
| created_at | TIMESTAMPTZ | No | now() |
| updated_at | TIMESTAMPTZ | No | now() |
| deleted_at | TIMESTAMPTZ | Yes | NULL |

**Primary Key:** id
**Foreign Keys:** organization_id → organizations.id (ON DELETE RESTRICT — see Section 4); currency_id → currencies.id; region_id → regions.id; country_id → countries.id
**Unique Constraints:** (source_system, source_record_id)
**Indexes:** btree on organization_id; btree on currency_id; btree on status
**Relationships:** Many customers to one organization. One customer has many subscriptions, invoices, payments, revenue_records, renewals, feature_usage rows, and support_tickets.

**Example Record:**
```
id: 9d3f7b21-...
organization_id: 6f2a1e4c-...
name: "Northline Media Group — EU Entity"
currency_id: <EUR>
status: "active"
```

## 3.3 roles

**Purpose:** Defines the three platform roles specified in PRD Section 12 (Admin, Executive, Analyst) and their associated permission scope flags.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| name | VARCHAR(50) | No | — |
| can_view_rep_level_detail | BOOLEAN | No | false |
| can_dismiss_alerts | BOOLEAN | No | false |
| can_manage_users | BOOLEAN | No | false |
| can_view_audit_logs | BOOLEAN | No | false |
| created_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Unique Constraints:** name
**Indexes:** none beyond primary key (small, fully-cached lookup table)
**Relationships:** One role has many users (1:N).

**Example Record:**
```
id: 3b1c...
name: "analyst"
can_view_rep_level_detail: false
can_dismiss_alerts: false
can_manage_users: false
can_view_audit_logs: false
```

## 3.4 users

**Purpose:** Platform users — the six personas from PRD Section 5, resolved to one of the three roles in 3.3. Identity itself is owned by Auth0/company SSO (PRD Section 8.1); this table stores the platform-local profile and role assignment, keyed to the SSO identity.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| sso_subject_id | VARCHAR(255) | No | — |
| email | VARCHAR(255) | No | — |
| full_name | VARCHAR(255) | No | — |
| role_id | UUID | No | — |
| is_active | BOOLEAN | No | true |
| last_login_at | TIMESTAMPTZ | Yes | NULL |
| created_at | TIMESTAMPTZ | No | now() |
| updated_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** role_id → roles.id (ON DELETE RESTRICT — a role in use cannot be deleted)
**Unique Constraints:** sso_subject_id; email
**Indexes:** btree on role_id; btree on is_active
**Relationships:** Many users to one role. One user has many ai_conversations, generated_reports (as requester), audit_logs (as actor), and may acknowledge many alerts.

**Example Record:**
```
id: 71ae...
sso_subject_id: "auth0|64f..."
email: "finance.manager@korasoft.example"
full_name: "Finance Manager"
role_id: <executive role>
is_active: true
```

## 3.5 subscription_plans

**Purpose:** The pricing tier definitions referenced throughout the PRD (Standard, Growth, Enterprise), consistent with Blueprint Section 1 pricing philosophy. This is a lookup/reference table, not billing-transactional data.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| name | VARCHAR(50) | No | — |
| tier_level | SMALLINT | No | — |
| billing_frequency | VARCHAR(20) | No | 'annual' |
| is_usage_based | BOOLEAN | No | false |
| created_at | TIMESTAMPTZ | No | now() |
| updated_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Unique Constraints:** name
**Indexes:** none beyond primary key
**Relationships:** One subscription_plan has many subscriptions.

**Example Record:**
```
id: 5c2a...
name: "Growth"
tier_level: 2
billing_frequency: "annual"
is_usage_based: true
```

## 3.6 products

**Purpose:** Kora's own product/module catalog (e.g., core platform, specific add-on modules). Referenced by subscription_plans and by revenue_records to attribute revenue to a product line, which the PRD's Usage-Based Billing Trends view filters by (PRD Section 10).

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| name | VARCHAR(100) | No | — |
| product_code | VARCHAR(30) | No | — |
| is_active | BOOLEAN | No | true |
| created_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Unique Constraints:** product_code
**Indexes:** none beyond primary key
**Relationships:** One product has many subscriptions and many revenue_records.

**Example Record:**
```
id: 4a11...
name: "Core Billing Platform"
product_code: "CORE"
is_active: true
```

## 3.7 subscriptions

**Purpose:** The Contract entity from the Blueprint's business entity model, scoped to a customer (billing entity). This is the central table most other financial tables hang off of.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| customer_id | UUID | No | — |
| subscription_plan_id | UUID | No | — |
| product_id | UUID | No | — |
| sales_representative_id | UUID | Yes | NULL |
| start_date | DATE | No | — |
| end_date | DATE | Yes | NULL |
| status | VARCHAR(30) | No | 'active' |
| mrr_amount | NUMERIC(18,2) | No | — |
| currency_id | UUID | No | — |
| source_system | VARCHAR(50) | No | 'billing_service' |
| source_record_id | VARCHAR(100) | No | — |
| created_at | TIMESTAMPTZ | No | now() |
| updated_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** customer_id → customers.id (ON DELETE RESTRICT); subscription_plan_id → subscription_plans.id; product_id → products.id; sales_representative_id → sales_representatives.id (nullable — not every subscription has a named rep, e.g., self-serve Standard tier); currency_id → currencies.id
**Unique Constraints:** (source_system, source_record_id)
**Check Constraints:** end_date IS NULL OR end_date > start_date; mrr_amount >= 0
**Indexes:** btree on customer_id; btree on status; btree on (start_date, end_date) for renewal-window queries; btree on sales_representative_id
**Relationships:** Many subscriptions to one customer. One subscription has many invoices, payments, revenue_records, renewals, and feature_usage rows.

**Example Record:**
```
id: 88bd...
customer_id: 9d3f7b21-...
subscription_plan_id: <Growth>
product_id: <Core Billing Platform>
start_date: 2025-03-01
end_date: 2026-02-28
status: "active"
mrr_amount: 4200.00
currency_id: <EUR>
```

## 3.8 revenue_records

**Purpose:** Recognized revenue entries, matching the Blueprint's revenue recognition process (Finance-owned) and feeding directly into the KPI Dictionary's Revenue, Net Revenue, MRR, and NRR/GRR calculations (PRD Section 19). Immutable once written; corrections are new rows, never edits.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| subscription_id | UUID | No | — |
| product_id | UUID | No | — |
| recognized_period_start | DATE | No | — |
| recognized_period_end | DATE | No | — |
| gross_amount | NUMERIC(18,2) | No | — |
| discount_amount | NUMERIC(18,2) | No | 0 |
| credit_amount | NUMERIC(18,2) | No | 0 |
| net_amount | NUMERIC(18,2) | No | — |
| currency_id | UUID | No | — |
| revenue_type | VARCHAR(30) | No | — |
| corrects_revenue_record_id | UUID | Yes | NULL |
| source_system | VARCHAR(50) | No | 'billing_service' |
| source_record_id | VARCHAR(100) | No | — |
| ingested_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** subscription_id → subscriptions.id; product_id → products.id; currency_id → currencies.id; corrects_revenue_record_id → revenue_records.id (self-referencing, nullable)
**Unique Constraints:** (source_system, source_record_id)
**Check Constraints:** net_amount = gross_amount − discount_amount − credit_amount; recognized_period_end > recognized_period_start; revenue_type IN ('recurring','usage_based','one_time')
**Indexes:** btree on subscription_id; btree on (recognized_period_start, recognized_period_end) — this is the primary query pattern for every date-range filter in Revenue Analytics; btree on revenue_type
**Relationships:** Many revenue_records to one subscription. Self-referencing correction chain (a record may reference the record it corrects).

**Example Record:**
```
id: c710...
subscription_id: 88bd...
product_id: <Core Billing Platform>
recognized_period_start: 2026-06-01
recognized_period_end: 2026-06-30
gross_amount: 4200.00
discount_amount: 0.00
credit_amount: 0.00
net_amount: 4200.00
currency_id: <EUR>
revenue_type: "recurring"
```

## 3.9 invoices

**Purpose:** Invoice header data synced from the Billing service, used both for the Recognized-vs-Billed reconciliation view (PRD Section 8.7) and Reports exports.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| customer_id | UUID | No | — |
| subscription_id | UUID | No | — |
| invoice_number | VARCHAR(50) | No | — |
| issue_date | DATE | No | — |
| due_date | DATE | No | — |
| total_amount | NUMERIC(18,2) | No | — |
| currency_id | UUID | No | — |
| status | VARCHAR(30) | No | 'issued' |
| source_system | VARCHAR(50) | No | 'billing_service' |
| source_record_id | VARCHAR(100) | No | — |
| ingested_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** customer_id → customers.id; subscription_id → subscriptions.id; currency_id → currencies.id
**Unique Constraints:** invoice_number; (source_system, source_record_id)
**Check Constraints:** due_date >= issue_date; status IN ('issued','paid','overdue','void'); total_amount >= 0
**Indexes:** btree on customer_id; btree on subscription_id; btree on issue_date; btree on status
**Relationships:** Many invoices to one customer and one subscription. One invoice has many payments.

**Example Record:**
```
id: 2f9a...
customer_id: 9d3f7b21-...
subscription_id: 88bd...
invoice_number: "INV-2026-04412"
issue_date: 2026-06-01
due_date: 2026-06-15
total_amount: 4200.00
status: "paid"
```

## 3.10 payments

**Purpose:** Payment execution records synced from Stripe (via the Billing service, per Blueprint Section 5), linked to invoices.

Note: an `invoice_line_items` table exists conceptually (an invoice may bill more than one subscription period or include usage-based line items) but is intentionally omitted from this document's required table list; where line-item detail is needed for exports, it is synced as part of ingestion but treated as an implementation detail of the invoices/revenue_records relationship rather than a distinct business entity the platform reports on independently.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| invoice_id | UUID | No | — |
| amount | NUMERIC(18,2) | No | — |
| currency_id | UUID | No | — |
| payment_method | VARCHAR(30) | Yes | NULL |
| status | VARCHAR(30) | No | 'succeeded' |
| paid_at | TIMESTAMPTZ | Yes | NULL |
| source_system | VARCHAR(50) | No | 'stripe' |
| source_record_id | VARCHAR(100) | No | — |
| ingested_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** invoice_id → invoices.id; currency_id → currencies.id
**Unique Constraints:** (source_system, source_record_id)
**Check Constraints:** status IN ('succeeded','failed','refunded','pending'); amount >= 0
**Indexes:** btree on invoice_id; btree on status; btree on paid_at
**Relationships:** Many payments to one invoice (an invoice may be paid in installments, or a failed attempt followed by a successful one).

**Example Record:**
```
id: 77dc...
invoice_id: 2f9a...
amount: 4200.00
status: "succeeded"
paid_at: 2026-06-10T14:22:00Z
```

## 3.11 sales_representatives

**Purpose:** Kora's own Sales team members, referenced for rep-level pipeline and bookings detail (PRD Section 10, rep filter — Executive/Admin role only).

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| full_name | VARCHAR(255) | No | — |
| email | VARCHAR(255) | No | — |
| team | VARCHAR(30) | No | — |
| is_active | BOOLEAN | No | true |
| source_system | VARCHAR(50) | No | 'salesforce' |
| source_record_id | VARCHAR(100) | No | — |
| created_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Unique Constraints:** email; (source_system, source_record_id)
**Check Constraints:** team IN ('new_business','expansion')
**Indexes:** btree on team; btree on is_active
**Relationships:** One sales_representative has many subscriptions (as the closing/owning rep).

**Example Record:**
```
id: 1a2b...
full_name: "Sales Rep, Expansion Team"
team: "expansion"
is_active: true
```

## 3.12 regions

**Purpose:** Geographic region lookup, used for organization/customer segmentation and dashboard filtering.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| name | VARCHAR(100) | No | — |
| code | VARCHAR(10) | No | — |

**Primary Key:** id
**Unique Constraints:** code
**Indexes:** none beyond primary key
**Relationships:** One region has many countries, organizations, and customers.

**Example Record:**
```
id: 9a1c...
name: "North America"
code: "NA"
```

## 3.13 countries

**Purpose:** Country lookup, subordinate to region, used for tax/currency defaulting logic and dashboard filtering.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| region_id | UUID | No | — |
| name | VARCHAR(100) | No | — |
| iso_code | VARCHAR(2) | No | — |
| default_currency_id | UUID | Yes | NULL |

**Primary Key:** id
**Foreign Keys:** region_id → regions.id; default_currency_id → currencies.id
**Unique Constraints:** iso_code
**Indexes:** btree on region_id
**Relationships:** Many countries to one region. One country has many organizations and customers.

**Example Record:**
```
id: 4d5e...
region_id: 9a1c...
name: "United States"
iso_code: "US"
default_currency_id: <USD>
```

## 3.14 currencies

**Purpose:** Currency lookup with formatting metadata, referenced by every monetary table given the multi-currency requirement for Enterprise accounts (Blueprint Section 1).

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| iso_code | VARCHAR(3) | No | — |
| symbol | VARCHAR(5) | No | — |
| decimal_places | SMALLINT | No | 2 |

**Primary Key:** id
**Unique Constraints:** iso_code
**Indexes:** none beyond primary key
**Relationships:** Referenced (N:1) by customers, subscriptions, invoices, payments, and revenue_records.

**Example Record:**
```
id: 8e2f...
iso_code: "EUR"
symbol: "€"
decimal_places: 2
```

## 3.15 renewals

**Purpose:** Tracks the renewal lifecycle for a subscription, feeding the Renewal Rate KPI (PRD Section 19) and the 60–90 day renewal window referenced in Blueprint Section 3.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| subscription_id | UUID | No | — |
| renewal_due_date | DATE | No | — |
| outcome | VARCHAR(30) | No | 'pending' |
| resulting_subscription_id | UUID | Yes | NULL |
| decided_at | TIMESTAMPTZ | Yes | NULL |
| source_system | VARCHAR(50) | No | 'salesforce' |
| source_record_id | VARCHAR(100) | No | — |
| created_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** subscription_id → subscriptions.id; resulting_subscription_id → subscriptions.id (nullable — populated only once the renewal produces a new Contract record, consistent with Blueprint Section 3's note that renewals create new Contract records rather than editing in place)
**Unique Constraints:** (source_system, source_record_id)
**Check Constraints:** outcome IN ('pending','renewed','churned','downgraded')
**Indexes:** btree on subscription_id; btree on renewal_due_date (primary query pattern for renewal-window reporting); btree on outcome
**Relationships:** Many renewals to one subscription (a subscription typically has one renewal event per term, but the table allows history). One renewal optionally produces one resulting subscription.

**Example Record:**
```
id: 6b7c...
subscription_id: 88bd...
renewal_due_date: 2026-02-28
outcome: "pending"
```

## 3.16 support_tickets

**Purpose:** A lightweight, read-only reference copy of Support ticket metadata (synced from Zendesk per Blueprint Section 5), included in this schema so the Revenue Intelligence Platform's Data Health and account-context views can reference ticket volume without a live Zendesk query, and so this schema is directly reusable by the future Customer Intelligence Platform (Section 10).

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| customer_id | UUID | No | — |
| ticket_number | VARCHAR(30) | No | — |
| category | VARCHAR(50) | Yes | NULL |
| priority | VARCHAR(20) | No | 'normal' |
| status | VARCHAR(30) | No | 'open' |
| opened_at | TIMESTAMPTZ | No | — |
| closed_at | TIMESTAMPTZ | Yes | NULL |
| source_system | VARCHAR(50) | No | 'zendesk' |
| source_record_id | VARCHAR(100) | No | — |
| ingested_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** customer_id → customers.id
**Unique Constraints:** (source_system, source_record_id)
**Check Constraints:** priority IN ('low','normal','high','urgent'); status IN ('open','pending','resolved','closed')
**Indexes:** btree on customer_id; btree on status; btree on opened_at
**Relationships:** Many support_tickets to one customer. This platform does not have a screen dedicated to ticket detail (out of scope per PRD Section 16) — this table exists as reference data, not as a feature surface.

**Example Record:**
```
id: 5f4a...
customer_id: 9d3f7b21-...
ticket_number: "ZD-88213"
category: "billing_question"
priority: "normal"
status: "resolved"
```

## 3.17 feature_usage

**Purpose:** Usage events feeding usage-based billing, matching the Blueprint's Usage Event entity. This is the highest-volume table in the schema by row count, given the Blueprint's note that end-customer usage data is high-volume relative to everything else in the system.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| subscription_id | UUID | No | — |
| product_id | UUID | No | — |
| event_type | VARCHAR(50) | No | — |
| quantity | NUMERIC(18,4) | No | — |
| event_timestamp | TIMESTAMPTZ | No | — |
| billing_period_start | DATE | No | — |
| billing_period_end | DATE | No | — |
| source_system | VARCHAR(50) | No | 'kafka_usage_stream' |
| source_record_id | VARCHAR(100) | No | — |
| ingested_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** subscription_id → subscriptions.id; product_id → products.id
**Unique Constraints:** (source_system, source_record_id)
**Check Constraints:** quantity >= 0; billing_period_end > billing_period_start
**Indexes:** btree on (subscription_id, billing_period_start, billing_period_end) — this composite index is the primary access path for the Usage-Based Billing Trends view; consider partitioning this table by billing_period_start (monthly range partitions) once row counts justify it, per Section 6
**Relationships:** Many feature_usage rows to one subscription. This table is aggregated, not queried row-by-row, for any dashboard or chart — see Section 6 for the materialized aggregation strategy.

**Example Record:**
```
id: 3c9d...
subscription_id: 88bd...
product_id: <Core Billing Platform>
event_type: "transaction_processed"
quantity: 1
event_timestamp: 2026-06-14T09:12:33Z
billing_period_start: 2026-06-01
billing_period_end: 2026-06-30
```

## 3.18 generated_reports

**Purpose:** History of Reports (CSV/Excel/PDF) generated through the platform, per PRD Section 8.6 and Section 13, supporting both the Reports screen's history view and the audit requirement that every export is logged.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| requested_by_user_id | UUID | No | — |
| report_type | VARCHAR(50) | No | — |
| format | VARCHAR(10) | No | — |
| filter_parameters | JSONB | No | '{}' |
| status | VARCHAR(30) | No | 'pending' |
| file_storage_path | VARCHAR(500) | Yes | NULL |
| requested_at | TIMESTAMPTZ | No | now() |
| completed_at | TIMESTAMPTZ | Yes | NULL |

**Primary Key:** id
**Foreign Keys:** requested_by_user_id → users.id
**Unique Constraints:** none beyond primary key
**Check Constraints:** format IN ('csv','excel','pdf'); status IN ('pending','processing','completed','failed')
**Indexes:** btree on requested_by_user_id; btree on requested_at; GIN index on filter_parameters for any future filter-based search over report history
**Relationships:** Many generated_reports to one user. file_storage_path points to the object storage location (S3, per Blueprint Section 8) — the file itself is not stored in the database.

**Example Record:**
```
id: 9f1a...
requested_by_user_id: 71ae...
report_type: "monthly_board_summary"
format: "pdf"
filter_parameters: {"date_range": "2026-06", "segment": "all"}
status: "completed"
```

## 3.19 alerts

**Purpose:** Data Health Dashboard entries — sync staleness warnings and reconciliation discrepancies (PRD Section 8.7), plus the "Recent Alerts" dashboard widget (PRD Section 20). Uses a polymorphic reference (entity_type + entity_id) rather than a hard foreign key, since an alert may reference any of several entity types (a customer, a subscription, an invoice) depending on where the discrepancy was detected.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| alert_type | VARCHAR(50) | No | — |
| severity | VARCHAR(20) | No | 'warning' |
| entity_type | VARCHAR(50) | No | — |
| entity_id | UUID | No | — |
| description | TEXT | No | — |
| detected_at | TIMESTAMPTZ | No | now() |
| acknowledged_by_user_id | UUID | Yes | NULL |
| acknowledged_at | TIMESTAMPTZ | Yes | NULL |

**Primary Key:** id
**Foreign Keys:** acknowledged_by_user_id → users.id (nullable)
**Unique Constraints:** none beyond primary key
**Check Constraints:** severity IN ('info','warning','critical'); alert_type IN ('sync_stale','reconciliation_discrepancy','data_missing'); acknowledged_at is only non-null when acknowledged_by_user_id is non-null (enforced at application layer given the polymorphic reference makes a single declarative constraint impractical — flagged explicitly here as an application-layer responsibility)
**Indexes:** btree on (entity_type, entity_id); btree on detected_at; btree on severity, filtered to acknowledged_at IS NULL (partial index — this is the query the header status indicator runs on every page load, so it should stay small and fast regardless of total alert history size)
**Relationships:** Polymorphic — logically related to organizations, customers, subscriptions, or invoices depending on entity_type, but not enforced via a database-level foreign key given the multiple possible target tables. Optionally acknowledged by one user (per PRD Section 12, Admin role only can dismiss).

**Example Record:**
```
id: 2d3e...
alert_type: "reconciliation_discrepancy"
severity: "warning"
entity_type: "invoice"
entity_id: 2f9a...
description: "Invoice total does not match corresponding revenue_records net_amount for the same billing period."
detected_at: 2026-07-21T03:14:00Z
```

## 3.20 ai_conversations

**Purpose:** AI Copilot session container (PRD Section 8.5), grouping a sequence of ai_messages for a given user.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| user_id | UUID | No | — |
| title | VARCHAR(255) | Yes | NULL |
| started_at | TIMESTAMPTZ | No | now() |
| last_message_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** user_id → users.id
**Unique Constraints:** none beyond primary key
**Indexes:** btree on user_id; btree on last_message_at
**Relationships:** Many ai_conversations to one user. One ai_conversation has many ai_messages.

**Example Record:**
```
id: 7a2b...
user_id: 71ae...
title: "Growth tier expansion revenue Q2"
started_at: 2026-07-20T10:03:00Z
```

## 3.21 ai_messages

**Purpose:** Individual question/answer turns within an ai_conversation, logged in full per PRD Section 15 (Logging) for audit and future model performance evaluation.

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| ai_conversation_id | UUID | No | — |
| role | VARCHAR(20) | No | — |
| content | TEXT | No | — |
| structured_query_executed | JSONB | Yes | NULL |
| grounded | BOOLEAN | Yes | NULL |
| created_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** ai_conversation_id → ai_conversations.id
**Unique Constraints:** none beyond primary key
**Check Constraints:** role IN ('user','assistant'); grounded is NULL for role='user' (only assistant messages carry a groundedness flag)
**Indexes:** btree on ai_conversation_id
**Relationships:** Many ai_messages to one ai_conversation. structured_query_executed stores the actual query the backend ran against the platform's data access layer to answer the question — this is the field that makes PRD Section 11's grounding requirement auditable rather than just asserted.

**Example Record:**
```
id: 4b1c...
ai_conversation_id: 7a2b...
role: "assistant"
content: "Growth tier expansion revenue was $184K in Q2, up from $151K in Q1."
structured_query_executed: {"metric": "expansion_revenue", "segment": "growth", "period": "2026-Q2"}
grounded: true
```

## 3.22 audit_logs

**Purpose:** Platform-wide audit trail, per PRD Section 15 (Audit) — every report export, alert dismissal, and role change, plus any other action the application layer designates as audit-worthy. Immutable from the application layer (no update or delete path is exposed to any user-facing feature).

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | UUID | No | generated |
| actor_user_id | UUID | Yes | NULL |
| action | VARCHAR(100) | No | — |
| entity_type | VARCHAR(50) | Yes | NULL |
| entity_id | UUID | Yes | NULL |
| metadata | JSONB | No | '{}' |
| request_id | UUID | Yes | NULL |
| occurred_at | TIMESTAMPTZ | No | now() |

**Primary Key:** id
**Foreign Keys:** actor_user_id → users.id (nullable — a small number of audit-worthy events, like a scheduled job's own actions, have no human actor)
**Unique Constraints:** none beyond primary key
**Indexes:** btree on actor_user_id; btree on occurred_at; btree on (entity_type, entity_id); GIN index on metadata for ad hoc audit investigation queries
**Relationships:** Optionally references a user as actor. entity_type/entity_id is polymorphic, same rationale as alerts (3.19). request_id ties back to the API error/response format defined in PRD Section 21 for tracing a specific request through to its audit trail.

**Example Record:**
```
id: 8c4d...
actor_user_id: 71ae...
action: "alert_dismissed"
entity_type: "alert"
entity_id: 2d3e...
metadata: {"reason": "known timing lag, invoice generated after sync cutoff"}
occurred_at: 2026-07-21T09:41:00Z
```

---

# 4. Relationship Rules

## One-to-Many

The overwhelming majority of relationships in this schema are one-to-many: one organization to many customers; one customer to many subscriptions; one subscription to many invoices, payments, revenue_records, renewals, and feature_usage rows; one role to many users; one user to many ai_conversations and generated_reports; one ai_conversation to many ai_messages. These are enforced with standard foreign keys and are the backbone of the schema — this platform's data model is fundamentally hierarchical (organization → customer → subscription → transactional detail), matching how the business itself is structured.

## Many-to-Many

There is no true many-to-many relationship in this schema. This is a deliberate simplification decision grounded in the actual business rules, not an oversight: a subscription belongs to exactly one customer and one subscription_plan; an invoice belongs to exactly one subscription. Where a many-to-many relationship might seem plausible (e.g., "could a sales_representative be associated with a customer directly, independent of any specific subscription"), the PRD and Blueprint do not require that level of modeling — rep attribution lives at the subscription level, which is where Sales actually attributes bookings credit. If a future requirement introduces a genuine many-to-many need (for example, a subscription spanning multiple products with independent revenue attribution per product), that would be modeled as a join table (e.g., `subscription_products`) at that time — not speculatively added now.

## Optional (Nullable) Relationships

- `subscriptions.sales_representative_id` is nullable: not every subscription has an attributed rep (e.g., self-serve Standard tier signups, per Blueprint Section 1).
- `renewals.resulting_subscription_id` is nullable until the renewal outcome is decided.
- `revenue_records.corrects_revenue_record_id` is nullable; most revenue_records are original, not corrections.
- `alerts.acknowledged_by_user_id` / `acknowledged_at` are nullable until an Admin dismisses the alert.
- `audit_logs.actor_user_id` is nullable for system-initiated actions.

## Cascade Rules

- **ON DELETE RESTRICT** is used for organizations → customers, customers → subscriptions, and roles → users. Financial and identity data should never disappear as a side effect of deleting a parent row; a genuine deletion requirement (e.g., GDPR-driven data removal) is handled as an explicit, audited data-deletion process, not an implicit cascade.
- **ON DELETE CASCADE** is used narrowly, only for platform-native, non-financial child data with no independent business meaning of its own: ai_messages cascade from ai_conversations (a message has no meaning outside its conversation). No other cascade deletes exist in this schema.
- Everything else that might look like a candidate for cascade (invoices, payments, revenue_records, renewals, feature_usage, support_tickets under a customer) instead relies on the soft-delete strategy in Section 7 — a customer being deactivated does not delete its financial history, which must remain queryable for historical reporting and audit.

---

# 5. Data Integrity

## Unique Constraints

Every table synced from an external source system (organizations, customers, subscriptions, invoices, payments, renewals, support_tickets, feature_usage) carries a `(source_system, source_record_id)` unique constraint. This is the primary defense against duplicate ingestion during sync retries or re-runs — the ingestion pipeline should always use an upsert keyed to this constraint, never a blind insert.

## Check Constraints

Check constraints are used throughout to encode business rules directly in the schema rather than relying solely on application-layer validation, since this database is fed by an automated ingestion pipeline as well as the application backend, and a check constraint protects against both paths making the same mistake:

- Date-range sanity (`end_date > start_date`, `due_date >= issue_date`, `billing_period_end > billing_period_start`) across subscriptions, invoices, and feature_usage.
- Non-negative monetary and quantity values across all financial tables.
- Enumerated status/type fields (e.g., `invoices.status`, `renewals.outcome`, `alerts.severity`) constrained to a fixed set of values, so an ingestion or application bug can't silently introduce an unrecognized status that the frontend then fails to render correctly.
- The `revenue_records.net_amount = gross_amount − discount_amount − credit_amount` constraint is the schema-level guarantee behind the Net Revenue KPI definition in PRD Section 19 — this can never silently drift from its formula.

## Foreign Keys

All foreign keys are declared and enforced at the database level, not left to application-layer discipline alone. This matters specifically because this platform has multiple write paths into the same tables (the nightly ingestion pipeline and, for platform-native tables, the application backend directly) — a database-level constraint is the only guarantee that holds regardless of which path writes the data.

## Validation Rules (Application-Layer, Beyond What the Database Enforces)

- Currency consistency: a subscription's currency_id should match its customer's currency_id under normal operation; this is validated at ingestion time and any mismatch is surfaced as a Data Health alert (3.19) rather than silently allowed, since the database itself does not enforce cross-table currency consistency via a declarative constraint.
- Role permission checks (PRD Section 12 matrix) are enforced at the API authorization layer, not the database layer, consistent with the architectural boundary established in PRD Section 21 ("role-based authorization is enforced at the API layer, not the UI layer") — the database schema supports this by making role a clean, queryable attribute of users, but does not itself gate query results by role.

---

# 6. Performance

| Index | Table | Rationale |
|---|---|---|
| (recognized_period_start, recognized_period_end) | revenue_records | This is the single most frequent query pattern in the entire platform — every Revenue Analytics date-range filter and every KPI card computation hits this range |
| (subscription_id, billing_period_start, billing_period_end) | feature_usage | Primary access path for Usage-Based Billing Trends; without this composite index, usage aggregation queries would require a full scan of the platform's highest-volume table |
| (entity_type, entity_id) | alerts, audit_logs | Supports the polymorphic reference lookups used when drilling from an alert or audit entry back to the record it concerns |
| Partial index on alerts where acknowledged_at IS NULL | alerts | The header Data Health status indicator (PRD Section 8.2, Section 20) queries this on every page load across the platform; keeping this index small and independent of total historical alert volume keeps that query fast regardless of how much alert history accumulates over time |
| (customer_id) | subscriptions, invoices, support_tickets | Standard parent-lookup index supporting the account-level rollups used throughout Revenue Analytics and any future Customer Intelligence Platform reuse of this schema |
| (renewal_due_date) | renewals | Supports the renewal-window reporting pattern (Blueprint's 60–90 day renewal window) directly |
| GIN index on filter_parameters | generated_reports | Supports future filter-based search over report history without requiring a schema change if that need arises |
| GIN index on metadata | audit_logs | Supports ad hoc audit investigation queries against semi-structured event detail without requiring a rigid, ever-growing set of dedicated columns |

**Partitioning consideration:** `feature_usage` and `revenue_records` are the two tables most likely to require range partitioning (by month, on their respective date columns) once historical volume grows significantly, given the Blueprint's note that end-customer usage data is high-volume relative to the rest of the system. This is not required for MVP launch given current data volume, but the schema's use of a date-range-based primary access pattern on both tables is deliberately chosen to make that partitioning migration straightforward later, rather than requiring a schema redesign.

**Materialized aggregation:** Dashboard KPI cards and Revenue Analytics charts should not compute aggregates (SUM, period-over-period deltas) live against revenue_records and feature_usage on every request. A materialized aggregation layer (either PostgreSQL materialized views refreshed after each nightly ingestion, or precomputed summary tables written by the ingestion pipeline itself) sits between these raw tables and the API layer, consistent with the PRD's performance requirement that KPI cards render within 2 seconds using pre-aggregated data rather than live computation (PRD Section 15).

---

# 7. Soft Delete Strategy

Soft delete (a nullable `deleted_at` timestamp column) is used specifically on **organizations** and **customers**, and nowhere else in this schema.

**Rationale:** An organization or customer being deactivated (e.g., a churned account) must not cause its historical financial data — subscriptions, invoices, payments, revenue_records — to disappear from historical reporting. Because those child tables use `ON DELETE RESTRICT` (Section 4), a hard delete of an organization or customer is already blocked while any financial history exists; soft delete provides the actual mechanism for representing "this account is no longer active" without deleting anything.

Soft delete is deliberately **not** used on transactional/financial tables (subscriptions, invoices, payments, revenue_records, renewals, feature_usage). Those tables represent immutable historical fact once written (Section 1, philosophy) — the correct way to represent a correction or reversal is a new row referencing what it corrects (as revenue_records already does via `corrects_revenue_record_id`), not a soft-deleted row. A "deleted" invoice is a contradiction of the platform's own reconciliation purpose: if an invoice needs to be voided, it transitions to `status = 'void'`, it is not removed from the queryable record.

Soft delete is also **not** used on lookup/reference tables (regions, countries, currencies, subscription_plans, products, roles) — these are expected to be long-lived and rarely deactivated; where deactivation is needed (e.g., a discontinued product), an `is_active` flag serves that purpose more clearly than `deleted_at`, since these rows are referenced by foreign keys from historical data that must continue to resolve correctly regardless of whether the referenced plan or product is still sold today.

All queries against organizations and customers in the application layer must filter `WHERE deleted_at IS NULL` by default; historical reporting views that need to include deactivated accounts (e.g., a churn analysis) explicitly opt into including soft-deleted rows rather than this being the default behavior.

---

# 8. Audit Strategy

Two distinct logging mechanisms exist in this schema, matching the distinction already drawn in PRD Section 15 between general Logging and Audit:

**Audit-level logging (the `audit_logs` table)** captures specifically the actions the PRD designates as audit-worthy: every report export (also recorded redundantly in generated_reports for the Reports screen's own history view, but audit_logs is the canonical cross-cutting log), every Data Health alert dismissal, and every user role change. Each entry captures actor, action, the affected entity (polymorphically), a metadata payload for action-specific detail, and a request_id for tracing back to the originating API request per the unified error/response format in PRD Section 21.

**Access-level logging** (general API request logging — who accessed what, when) is handled outside this database, via the platform's centralized logging pipeline (Datadog Log Management, per Blueprint Section 8), not stored as rows in this schema. Storing every read request as a database row would create an unbounded, high-volume table with no query pattern the application itself needs to serve — that data belongs in the observability stack, not the transactional database.

**What is never logged in audit_logs:** routine read/navigation activity, AI Copilot conversations (which have their own dedicated, richer log in ai_conversations/ai_messages, including the structured query executed — a stronger audit trail than a generic audit_logs entry would provide for that specific feature), and ingestion pipeline sync runs (which have their own operational logging, separate from user-facing audit trail, since they're not actions taken by a platform user).

`audit_logs` rows are never updated or deleted through any application code path. If a correction to an audit entry is ever genuinely required (extremely rare, and itself a security-relevant event), it is handled as a new row referencing the original, following the same immutability-with-correction-reference pattern used for revenue_records — never an in-place edit.

---

# 9. Naming Convention

**Table names:** Plural, snake_case, lowercase (e.g., `subscriptions`, `revenue_records`, `sales_representatives`). No prefixes (no `tbl_` or `rip_` prefix) since this database is dedicated to a single application and namespacing at the table-name level is unnecessary.

**Column names:** snake_case, lowercase. Foreign key columns are named `<singular_referenced_table>_id` (e.g., `customer_id`, `subscription_plan_id`, `sales_representative_id`) so the referenced table is always unambiguous from the column name alone, without needing to consult the schema. Boolean columns are prefixed `is_` or `can_` (`is_active`, `can_view_rep_level_detail`) so their type is inferable from the name. Monetary columns are suffixed `_amount`, never bare (`gross_amount`, not `gross`), to avoid ambiguity with non-monetary numeric columns.

**Primary keys:** Always named `id`, always UUID type, consistent across every table (Section 1). This uniformity means application and ORM-adjacent code (even though this document specifies no ORM per its own scope) never needs table-specific primary key logic.

**Foreign keys:** Always named `<referenced_entity>_id`, matching the primary key name of the table they reference (i.e., every foreign key column name ends in `_id`, matching every primary key column name). Self-referencing foreign keys (e.g., `revenue_records.corrects_revenue_record_id`, `renewals.resulting_subscription_id`) are named to describe the relationship's meaning, not just the target table, since a bare `_id` suffix referencing the same table would be ambiguous about direction and purpose.

**Timestamp columns:** All timestamps are `TIMESTAMPTZ` (timezone-aware), never bare `TIMESTAMP`, given Kora's Enterprise customers span multiple regions and time zones. Standard lifecycle columns are named `created_at`, `updated_at`, and (where applicable) `deleted_at`. Domain-specific timestamps use a descriptive name rather than a generic one (`occurred_at` for audit_logs, `detected_at` for alerts, `ingested_at` for source-synced tables, `paid_at` for payments) so that a table's specific temporal meaning is clear without needing to read column comments.

---

# 10. Future Expansion

This schema is deliberately designed to be reused, not rebuilt, by the two future internal products described in the Blueprint (Section 9).

## Customer Intelligence Platform

The Customer Intelligence Platform's stated purpose (Blueprint Section 9) is to unify usage trends, support ticket history, contract/billing status, and CS health notes into a single account health view. This schema already contains the customer-scoped data that platform needs — `customers`, `subscriptions`, `support_tickets`, `feature_usage`, and `renewals` are all structured around the same `customer_id` foreign key pattern, meaning the Customer Intelligence Platform can either read directly from this database (as a second consumer) or sync the same source data independently using the same entity boundaries, without needing to invent a different definition of "customer" or "subscription" than the one this platform already uses. The one addition that platform will need and this schema does not yet provide is a structured CS health-notes table — intentionally not added here, since it is explicitly out of scope for the Revenue Intelligence Platform's own MVP (PRD Section 16) and adding it speculatively would violate this document's instruction not to introduce entities beyond what the current PRD requires.

## Internal AI Workspace

The Internal AI Workspace's purpose (Blueprint Section 9) is search and assistance over internal documentation, past support resolutions, and runbooks — a fundamentally different data shape (unstructured/semi-structured text and embeddings) than this schema's structured financial and account data. The direct point of reuse is narrower and more specific: the `ai_conversations` / `ai_messages` pattern established here (conversation container, individual turns, a `structured_query_executed` field capturing what grounded a given answer) is a reusable design pattern the Internal AI Workspace can adopt directly for its own conversational interface, even though its underlying retrieval mechanism (semantic search over documents, rather than structured queries over financial tables) is different. The `audit_logs` polymorphic pattern (entity_type + entity_id + metadata) is similarly reusable as-is if the Internal AI Workspace needs to audit-log actions against entities defined in its own schema rather than this one.

---

# 11. Database Statistics

Estimated MVP data volume, based on Kora's actual scale (~200 employees, Series B, mid-market/enterprise B2B, sales-led motion — Blueprint Section 1). These are order-of-magnitude planning estimates for capacity and index design, not a forecasting commitment.

| Entity | Estimated Rows (MVP, Year 1) |
|---|---|
| organizations | ~800 |
| customers | ~1,200 |
| users | ~40 |
| subscriptions | ~2,500 |
| revenue_records | ~500,000 |
| payments | ~55,000 |
| invoices | ~55,000 |
| feature_usage | ~50,000,000 |
| ai_conversations | ~5,000 |
| ai_messages | ~45,000 |
| audit_logs | ~200,000 |

**Why these are realistic:**

- **Organizations / Customers:** A mid-market/enterprise-only, sales-led B2B company at Series B typically has a few hundred to low-thousands of paying accounts, not tens of thousands — high ACV, low logo count, consistent with the pricing philosophy in Blueprint Section 1. The customers count exceeds organizations because Enterprise accounts split into multiple billing entities/business units.
- **Users:** This is an internal tool. Only the six personas in PRD Section 5 (CEO, COO, Head of Sales, Finance Manager, Business Analysts, Product Analysts) use it — a handful of named individuals per role, not a company-wide rollout across all ~200 employees.
- **Subscriptions:** Exceeds customer count because renewals create new subscription rows rather than editing in place (Blueprint Section 3), so multi-year accounts accumulate several subscription rows over their lifetime.
- **Revenue Records:** One row per subscription per recognized period (typically monthly), compounding over multiple years across ~2,500 subscriptions — this is the first table where volume becomes a genuine indexing concern rather than a lookup-table concern.
- **Invoices / Payments:** Roughly one invoice per subscription per billing cycle (mostly annual/quarterly per Blueprint Section 1), plus retry/installment payment rows — an order of magnitude smaller than revenue_records since not every recognized period generates a distinct invoice.
- **Feature Usage:** By far the largest table, consistent with the Blueprint's explicit note that end-customer usage data is high-volume relative to everything else in the system — this reflects real transaction-level events from Kora's own customers' end users, not just Kora's ~800 organizations.
- **AI Conversations / Messages:** A new, lightly-used MVP feature among a ~40-user internal audience; volume here is bounded by human question-asking pace, not automated ingestion.
- **Audit Logs:** Reflects only the audit-worthy actions defined in Section 8 (exports, alert dismissals, role changes) across a small user base — modest volume relative to feature_usage, but growing steadily and indefinitely retained.

---

# 12. Database Evolution

### MVP

- PostgreSQL
- Single database
- No read replicas
- Vertical scaling

At current estimated volume (Section 11), a single vertically-scaled PostgreSQL instance comfortably serves both writes (nightly ingestion) and reads (dashboard queries), since feature_usage is the only table approaching a scale where naive querying becomes slow, and Section 6's materialized aggregation strategy already keeps that off the request-time path. Introducing replicas or partitioning before there's a measured performance problem would add operational complexity (replica lag handling, partition-aware query planning) the team would be maintaining against a hypothetical, not an actual, bottleneck.

### Version 2

- Read replicas
- Table partitioning
- Background workers
- Performance optimization

Introduced once feature_usage and revenue_records grow enough (multi-year history, expanding customer base) that a single instance starts absorbing contention between nightly ingestion writes and interactive dashboard reads. Read replicas separate that contention by routing Revenue Analytics and dashboard queries away from the instance handling ingestion. Table partitioning (by billing_period_start / recognized_period_start, as flagged in Section 6) keeps date-range queries fast as historical row counts grow rather than degrading linearly with total table size. Background workers move report generation and AI Copilot query execution (already specified as asynchronous for large exports in PRD Section 8.6) off the request-handling path entirely, rather than relying on the web tier's own request timeout budget.

### Future

- ClickHouse for analytics
- Event streaming
- Data Lake
- Multi-region deployment

Considered once feature_usage volume and query patterns genuinely outgrow what partitioned PostgreSQL handles well — column-oriented analytical storage (ClickHouse) suits high-volume, aggregation-heavy usage event analysis far better than a row-oriented OLTP database ever will, without displacing PostgreSQL's role for the transactional, reconciliation-sensitive tables (organizations through invoices) where row-level integrity and foreign-key enforcement still matter most. Event streaming (formalizing the existing Kafka usage pipeline per Blueprint Section 8 into the platform's own ingestion path) becomes worth the added architectural surface once nightly-batch latency is itself the limiting factor for Data Health freshness, echoing the "future direction" already flagged for the Revenue Intelligence Platform in Blueprint Section 9. A data lake becomes relevant if Kora's internal products (this platform, Customer Intelligence, Internal AI Workspace) accumulate enough raw historical and unstructured data that a single warehouse schema is no longer the most efficient shared substrate across all three. Multi-region deployment is the last of these to become relevant, and only if Kora's own customer base concentration shifts enough geographically that single-region latency or data-residency requirements (particularly for Enterprise contracts with regional data handling terms) start to matter — not a default assumption for a company still centered on the deployment model described in Blueprint Section 8.

---

# 11. Database Statistics

These are MVP-launch volume estimates, used to sanity-check the indexing and partitioning guidance in Section 6 and to set expectations for load testing before go-live. They're derived from Kora's actual company profile (Blueprint Section 1: Series B, ~200 employees, sales-led mid-market/enterprise B2B SaaS) rather than a generic SaaS benchmark, and should be revisited against real numbers once the ingestion pipeline has been running against production data for a full quarter.

| Entity | Estimated Rows (at MVP launch) | Estimated Rows (18 months post-launch) |
|---|---|---|
| organizations | ~350 | ~600 |
| customers | ~480 | ~850 |
| users | ~35 | ~55 |
| subscriptions | ~650 | ~1,400 |
| revenue_records | ~45,000 | ~140,000 |
| payments | ~6,500 | ~16,000 |
| invoices | ~6,200 | ~15,000 |
| feature_usage | ~60,000,000 | ~220,000,000 |
| ai_conversations | ~1,500 | ~9,000 |
| ai_messages | ~9,000 | ~55,000 |
| audit_logs | ~4,000 | ~22,000 |

**Why these estimates are realistic for this company:**

- **organizations / customers:** A Series B company at ~200 employees with a sales-led (not high-volume self-serve) motion, per Blueprint Section 1, typically has a customer base in the low hundreds, not tens of thousands — new-logo velocity is deliberately slower than a PLG-motion company at the same headcount, and growth stage (Section 1: expansion-driven, not pure new-logo growth) means the *customers* count grows somewhat faster than *organizations* as existing Enterprise accounts add business units.
- **users:** This is an internal tool for six specific personas (PRD Section 5), not a company-wide application — the ~35 figure reflects the actual named individuals in Executive, Finance, Sales leadership, and Analyst roles across a 200-person company, not the full headcount.
- **subscriptions:** Includes historical (renewed, churned, superseded) subscription rows, not just active ones, since Blueprint Section 3 specifies renewals create new Contract rows rather than editing in place — this compounds over time even with a stable customer count.
- **revenue_records:** One row per subscription per recognized period (monthly, per Section 3.8), multiplied across roughly 2–3 years of combined historical and go-forward data at launch — this is a moderate-volume table by row count but not a high-volume one, since recognition happens monthly, not per-transaction.
- **payments / invoices:** Reflect quarterly-or-annual billing frequency (Blueprint Section 1 pricing philosophy: annual/quarterly contracts, not monthly consumer-style billing), which keeps these tables an order of magnitude smaller than a consumer subscription business would produce at the same customer count.
- **feature_usage:** By far the largest table, consistent with the Blueprint's explicit note that end-customer usage data is high-volume relative to everything else in the system — this reflects the underlying transaction volume of Kora's own customers' end-subscribers (the businesses using Kora's platform to run their own subscription base), not Kora's own customer count. This table's estimated volume is the primary justification for the partitioning recommendation in Section 6.
- **ai_conversations / ai_messages:** Reflect light, gradually-increasing internal adoption among ~35 platform users (PRD Section 4 success metric: 60% of Executive-role users engaging with AI features weekly by two quarters post-launch) — meaningfully smaller than any customer-facing AI feature's volume would be.
- **audit_logs:** Reflects the specific, narrow set of audit-worthy actions defined in Section 8 (exports, alert dismissals, role changes) rather than every user interaction — this table is intentionally small relative to total platform activity, since routine reads are handled by the observability stack, not this table.

---

# 12. Database Evolution

The schema and infrastructure described in this document is the MVP state. It is expected to evolve in stages as data volume and query load grow, rather than being over-built for scale the platform doesn't yet have. Each stage below is triggered by an actual observed constraint, not adopted preemptively.

### MVP

- PostgreSQL, single database instance, dedicated to this platform (Section 1).
- No read replicas — all reads and writes go against the same primary instance.
- Vertical scaling (larger instance size) as the response to any load concern.

**Why:** At the volumes estimated in Section 11, a single well-indexed PostgreSQL instance comfortably handles both the nightly ingestion writes and interactive dashboard reads. Introducing read replicas or partitioning before there's a measured need would add operational complexity (replication lag handling, connection routing logic) without a corresponding benefit, and would slow down MVP delivery for a problem that doesn't exist yet.

### Version 2

- Read replicas, with dashboard and Revenue Analytics read traffic routed to a replica, keeping the primary instance dedicated to ingestion writes and the small volume of platform-native writes (reports, AI conversations, audit logs).
- Table partitioning on `feature_usage` and `revenue_records` (monthly range partitions on their respective date columns), consistent with the partitioning consideration flagged in Section 6.
- Background workers for report generation and any AI Copilot query that exceeds the synchronous response threshold (PRD Section 15 performance requirement), moving that work off the request path entirely rather than relying on request-level async handling alone.
- General performance optimization: materialized view refresh tuning, query plan review against real production data distributions rather than MVP-stage estimates.

**Why:** This stage is triggered once real usage data shows dashboard read load competing with nightly ingestion writes for resources, or once `feature_usage` row counts approach the point where unpartitioned range queries start degrading — both of which are anticipated, per Section 11's 18-month growth estimate, well before they'd become a launch blocker, giving engineering lead time to implement this deliberately rather than reactively.

### Future

- ClickHouse (or an equivalent columnar analytical store) introduced specifically for `feature_usage` and other high-cardinality analytical queries, once usage-based billing volume outgrows what a partitioned PostgreSQL table can serve at acceptable query latency for the Usage-Based Billing Trends view.
- Event streaming (extending the existing Kafka usage event pipeline, per Blueprint Section 8) to feed both the operational database and the analytical store from a single event source, rather than the operational database being the sole ingestion target.
- Data Lake storage for raw, pre-aggregation source data, decoupling long-term raw data retention from the operational database's own storage and performance profile.
- Multi-region deployment, if and when Kora's own infrastructure footprint (Blueprint Section 1: target customers include multi-currency Enterprise accounts, though Kora's own infrastructure is currently single-region per Blueprint Section 8) expands to serve data residency or latency requirements from a specific customer region.

**Why:** These are the changes that only make sense once this platform's data volume and query patterns have genuinely outgrown what a well-tuned relational database can serve — introducing a columnar store or a data lake at MVP stage, before there's a demonstrated analytical workload that PostgreSQL can't handle, would be solving a problem the company doesn't have yet at the cost of engineering time it does need elsewhere. This stage is explicitly a "when we get there" plan, not a committed near-term roadmap item.
