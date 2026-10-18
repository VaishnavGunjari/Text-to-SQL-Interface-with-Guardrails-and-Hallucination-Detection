# Database Schema Reference

This reference documents the relational data dictionary for the SaaS Analytics database queried by the **Text-to-SQL AI** service.

---

## Entity Relationship Overview

```
 organizations (1) ───────< (N) users
       │
       ├─────────────────< (N) subscriptions ───< (N) invoices
       │
       ├─────────────────< (N) events
       │
       └─────────────────< (N) feature_usage >─── (1) features
```

---

## Table Definitions

### 1. `organizations`
Primary account entity representing a customer company or tenant.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique organization identifier. |
| `name` | `VARCHAR(255)` | `NOT NULL` | Company or team display name. |
| `plan` | `VARCHAR(50)` | `NOT NULL, DEFAULT 'starter'` | Current subscription tier (`starter`, `growth`, `business`, `enterprise`). |
| `country` | `VARCHAR(100)` | `NULLABLE` | Country of company headquarters. |
| `industry` | `VARCHAR(100)` | `NULLABLE` | Business sector (e.g. `Fintech`, `Healthcare`, `Edtech`). |
| `employee_count` | `INTEGER` | `NULLABLE` | Number of employees. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Organization registration timestamp. |
| `churned_at` | `TIMESTAMPTZ` | `NULLABLE` | Timestamp when the organization cancelled or churned (NULL if active). |

---

### 2. `users`
Individual user accounts belonging to an organization.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique user identifier. |
| `org_id` | `INTEGER` | `NOT NULL, FK -> organizations(id)` | Parent organization. |
| `email` | `VARCHAR(255)` | `NOT NULL, UNIQUE` | User email address. |
| `name` | `VARCHAR(255)` | `NULLABLE` | Full name of the user. |
| `role` | `VARCHAR(50)` | `NOT NULL, DEFAULT 'member'` | Access role (`admin`, `member`, `viewer`, `developer`). |
| `is_active` | `BOOLEAN` | `NOT NULL, DEFAULT TRUE` | Active status indicator. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Account creation date. |
| `last_login_at`| `TIMESTAMPTZ` | `NULLABLE` | Timestamp of the most recent user login. |

---

### 3. `subscriptions`
Billing subscriptions linked to organizations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique subscription identifier. |
| `org_id` | `INTEGER` | `NOT NULL, FK -> organizations(id)` | Customer organization. |
| `plan` | `VARCHAR(50)` | `NOT NULL` | Subscription tier (`starter`, `growth`, `business`, `enterprise`). |
| `status` | `VARCHAR(50)` | `NOT NULL, DEFAULT 'active'` | Status (`active`, `trialing`, `cancelled`, `past_due`). |
| `mrr` | `NUMERIC(10,2)`| `NOT NULL, DEFAULT 0` | Monthly Recurring Revenue in specified currency. |
| `currency` | `VARCHAR(10)` | `NOT NULL, DEFAULT 'USD'` | Currency code (USD, EUR, GBP). |
| `billing_interval` | `VARCHAR(20)` | `NOT NULL, DEFAULT 'monthly'` | Billing frequency (`monthly`, `annual`). |
| `started_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Subscription commencement date. |
| `ended_at` | `TIMESTAMPTZ` | `NULLABLE` | Expiration or termination date. |
| `trial_ends_at` | `TIMESTAMPTZ` | `NULLABLE` | Trial end date if applicable. |
| `cancelled_at` | `TIMESTAMPTZ` | `NULLABLE` | Cancellation date. |

---

### 4. `invoices`
Billing invoices generated for organizations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique invoice identifier. |
| `org_id` | `INTEGER` | `NOT NULL, FK -> organizations(id)` | Organization billed. |
| `subscription_id` | `INTEGER` | `NULLABLE, FK -> subscriptions(id)` | Associated subscription. |
| `amount` | `NUMERIC(10,2)`| `NOT NULL` | Total invoice charge amount. |
| `currency` | `VARCHAR(10)` | `NOT NULL, DEFAULT 'USD'` | Currency code. |
| `status` | `VARCHAR(50)` | `NOT NULL, DEFAULT 'pending'` | Payment status (`paid`, `pending`, `failed`, `refunded`). |
| `due_date` | `DATE` | `NULLABLE` | Payment due date. |
| `paid_at` | `TIMESTAMPTZ` | `NULLABLE` | Payment collection timestamp. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Invoice generation timestamp. |

---

### 5. `events`
Product telemetry and user activity event stream.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique event ID. |
| `user_id` | `INTEGER` | `NULLABLE, FK -> users(id)` | User who triggered the event. |
| `org_id` | `INTEGER` | `NOT NULL, FK -> organizations(id)` | Organization where event occurred. |
| `event_type` | `VARCHAR(100)` | `NOT NULL` | Action code (`login`, `report_created`, `api_call`, `export_csv`, etc.). |
| `page` | `VARCHAR(255)` | `NULLABLE` | URL route or view context. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Event occurrence timestamp. |

---

### 6. `features`
Product capabilities and required subscription tiers.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique feature identifier. |
| `name` | `VARCHAR(100)` | `NOT NULL, UNIQUE` | Feature name (e.g. `Custom Reports`, `SSO`, `Audit Logs`). |
| `description` | `TEXT` | `NULLABLE` | Detailed feature description. |
| `plan_required`| `VARCHAR(50)` | `NOT NULL, DEFAULT 'starter'` | Minimum tier required to access. |

---

### 7. `feature_usage`
Aggregated or point-in-time usage tracking of features by organizations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY` | Unique usage record ID. |
| `org_id` | `INTEGER` | `NOT NULL, FK -> organizations(id)` | Organization using the feature. |
| `feature_id` | `INTEGER` | `NOT NULL, FK -> features(id)` | Feature referenced. |
| `used_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Usage timestamp. |
| `usage_count` | `INTEGER` | `NOT NULL, DEFAULT 1` | Volume or execution count. |

---

## Common Query Patterns & Examples

### 1. Calculate Total MRR
```sql
SELECT SUM(mrr) AS total_mrr
FROM subscriptions
WHERE status = 'active';
```

### 2. Identify Top 5 Organizations by Headcount
```sql
SELECT name, employee_count, industry, plan
FROM organizations
ORDER BY employee_count DESC
LIMIT 5;
```

### 3. List Invoices with Failed Payment Status
```sql
SELECT i.id, o.name AS organization, i.amount, i.due_date
FROM invoices i
JOIN organizations o ON i.org_id = o.id
WHERE i.status = 'failed'
ORDER BY i.created_at DESC;
```
