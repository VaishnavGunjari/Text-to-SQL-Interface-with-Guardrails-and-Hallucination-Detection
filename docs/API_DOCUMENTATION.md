# Text-to-SQL AI — API Documentation

Welcome to the **Text-to-SQL AI** API documentation. This document provides a complete reference for all REST endpoints exposed by the service, including request structures, response schemas, validation rules, status codes, and code examples.

---

## Base URL

| Environment | Base URL |
|---|---|
| Local Development | `http://localhost:8000` |
| Local Frontend Proxy | `http://localhost:5173` |
| API Version Prefix | `/v1` |

Interactive Swagger UI documentation is available at `/docs` and ReDoc is available at `/redoc`.

---

## Authentication & Headers

Currently, the service operates in single-tenant / local network mode. 

Standard headers:
```http
Content-Type: application/json
Accept: application/json
```

---

## Endpoints Summary

| Method | Endpoint | Description | Tag |
|---|---|---|---|
| `POST` | `/v1/query` | Translate natural language question to validated SQL, execute, and return results | Query |
| `PATCH` | `/v1/history/{query_id}/feedback` | Submit human feedback (`correct` / `incorrect`) on a query result | Query |
| `GET` | `/v1/schema` | Retrieve active database schema dictionary | Schema |
| `POST` | `/v1/schema/refresh` | Force cache refresh of database schema inspection | Schema |
| `GET` | `/v1/history` | List recent queries with execution metadata and feedback | History |
| `GET` | `/v1/health` | Check service health, database connectivity, and active LLM model | System |

---

## 1. Natural Language Query (`POST /v1/query`)

Translates a natural language question into SQL, performs multi-stage security validation (SQL guardrails and hallucination detection), executes the query against the database, validates result sanity, runs multi-query agreement checks, and computes a confidence score.

### Request Body

```json
{
  "question": "Show me the top 5 organizations by MRR",
  "custom_sql": null,
  "clarification_choice": null,
  "enable_multi_query": true,
  "max_rows": 100
}
```

#### Field Specifications:

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `question` | string | Yes | — | Natural language question (length: 3 to 2000 chars). |
| `custom_sql` | string | No | `null` | Optional user-edited SQL for power-user execution. Still subject to AST guardrails & sandbox. |
| `clarification_choice` | string | No | `null` | Chosen option label if answering a previous clarification prompt. |
| `enable_multi_query` | boolean | No | `true` | When true, generates a secondary independent query to verify result consistency. |
| `max_rows` | integer | No | `100` | Maximum rows to return (between 1 and 1000). |

---

### Response Body (`QueryResponse`)

#### Success Example (`status: "success"`):

```json
{
  "query_id": "c1f7a0b3-90d1-4e89-a2de-6df37b420011",
  "question": "Show me the top 5 organizations by MRR",
  "status": "success",
  "sql": "SELECT o.name, s.mrr, s.plan, s.status FROM organizations o JOIN subscriptions s ON o.id = s.org_id WHERE s.status = 'active' ORDER BY s.mrr DESC LIMIT 5",
  "sql_explanation": "Finds active subscriptions, sorts by Monthly Recurring Revenue in descending order, and limits to top 5.",
  "tables_used": ["organizations", "subscriptions"],
  "columns": ["name", "mrr", "plan", "status"],
  "rows": [
    {"name": "Acme Corp", "mrr": 999.00, "plan": "enterprise", "status": "active"},
    {"name": "Globex Inc", "mrr": 299.00, "plan": "business", "status": "active"},
    {"name": "Soylent Tech", "mrr": 299.00, "plan": "business", "status": "active"},
    {"name": "Initech Systems", "mrr": 99.00, "plan": "growth", "status": "active"},
    {"name": "Umbrella Corp", "mrr": 99.00, "plan": "growth", "status": "active"}
  ],
  "guardrail": {
    "passed": true,
    "blocked_reason": null,
    "warnings": []
  },
  "hallucination": {
    "hallucination_detected": false,
    "schema_valid": true,
    "invalid_tables": [],
    "invalid_columns": [],
    "back_translation": {
      "back_translated_question": "What are the top 5 organizations ordered by their monthly recurring revenue?",
      "alignment_score": 0.95,
      "alignment_explanation": "Both questions request organizations ranked by MRR top 5.",
      "is_aligned": true
    },
    "hallucination_reasons": []
  },
  "sanity": {
    "passed": true,
    "pass_rate": 1.0,
    "warnings": [],
    "checks": [
      {"name": "empty_results", "passed": true, "message": "Returned 5 rows", "severity": "warning"},
      {"name": "extreme_values", "passed": true, "message": "Values within expected statistical range", "severity": "warning"}
    ]
  },
  "multi_query": {
    "enabled": true,
    "alternative_sql": "SELECT o.name, s.mrr FROM organizations o INNER JOIN subscriptions s ON o.id = s.org_id WHERE s.status = 'active' ORDER BY s.mrr DESC FETCH FIRST 5 ROWS ONLY",
    "results_agree": true,
    "agreement_score": 1.0,
    "discrepancy_explanation": null
  },
  "confidence": {
    "percentage": 96,
    "label": "High",
    "total_score": 96.0,
    "signals": [
      {
        "name": "guardrails",
        "display_name": "SQL Guardrails",
        "max_points": 30,
        "earned_points": 30.0,
        "passed": true,
        "detail": "Read-only query passed all syntax and safety rules"
      },
      {
        "name": "schema_validity",
        "display_name": "Schema Validity",
        "max_points": 25,
        "earned_points": 25.0,
        "passed": true,
        "detail": "All referenced tables and columns exist in active schema"
      },
      {
        "name": "back_translation",
        "display_name": "Back-Translation Alignment",
        "max_points": 20,
        "earned_points": 19.0,
        "passed": true,
        "detail": "Back-translated question matches user intent with 95% similarity"
      },
      {
        "name": "result_sanity",
        "display_name": "Result Sanity",
        "max_points": 15,
        "earned_points": 15.0,
        "passed": true,
        "detail": "All 4 result sanity checks passed"
      },
      {
        "name": "multi_query",
        "display_name": "Multi-Query Consensus",
        "max_points": 10,
        "earned_points": 10.0,
        "passed": true,
        "detail": "Alternative SQL formulation produced identical result set"
      }
    ],
    "summary": "High confidence (96%). All safety checks, schema validations, and multi-query tests passed."
  },
  "execution": {
    "execution_time_ms": 14.8,
    "row_count": 5,
    "was_limited": false,
    "explain_plan": "Limit  (cost=12.45..12.46 rows=5 width=40)\n  ->  Sort  (cost=12.45..12.60 rows=60 width=40)\n..."
  },
  "clarification_options": [],
  "unanswerable_reason": null,
  "error_message": null,
  "timestamp": "2026-10-17T13:30:00.000Z",
  "feedback": null
}
```

---

#### Clarification Needed Example (`status: "clarification"`):

When the natural language query is ambiguous, the system prompts the user to select an interpretation:

```json
{
  "query_id": "8e3b1c20-4df2-481b-87cf-45b0d0e1293a",
  "question": "Show revenue",
  "status": "clarification",
  "clarification_options": [
    {
      "label": "Total MRR from active subscriptions",
      "description": "Sum of current Monthly Recurring Revenue across active accounts",
      "example_sql": "SELECT SUM(mrr) FROM subscriptions WHERE status = 'active'"
    },
    {
      "label": "Total invoiced revenue collected",
      "description": "Sum of all paid invoices all-time",
      "example_sql": "SELECT SUM(amount) FROM invoices WHERE status = 'paid'"
    }
  ],
  "timestamp": "2026-10-17T13:31:00.000Z"
}
```

---

#### Guardrail Blocked Example (`status: "blocked"`):

If a query contains write operations, DDL, or unauthorized statements:

```json
{
  "query_id": "7a942bc0-21a4-4428-b209-6638b97fe91b",
  "question": "Delete all users who haven't logged in",
  "status": "blocked",
  "sql": "DELETE FROM users WHERE last_login_at < NOW() - INTERVAL '90 days'",
  "guardrail": {
    "passed": false,
    "blocked_reason": "Blocked DML statement 'DELETE': Only SELECT statements are permitted.",
    "warnings": []
  },
  "error_message": "Query blocked: Blocked DML statement 'DELETE': Only SELECT statements are permitted.",
  "timestamp": "2026-10-17T13:32:00.000Z"
}
```

---

## 2. Submit Feedback (`PATCH /v1/history/{query_id}/feedback`)

Allows users or evaluating agents to flag query outputs as `correct` or `incorrect`.

### Parameters:
- `query_id` (path, string, required): UUID of the query.

### Request Body:
```json
{
  "feedback": "correct",
  "user_note": "Accurately selected active subscriptions"
}
```

### Response (`200 OK`):
```json
{
  "status": "ok",
  "query_id": "c1f7a0b3-90d1-4e89-a2de-6df37b420011",
  "feedback": "correct"
}
```

---

## 3. Schema Endpoints

### `GET /v1/schema`
Returns the active schema dictionary including tables, column types, primary keys, and foreign key relationships.

#### Response (`200 OK`):
```json
{
  "tables": {
    "organizations": {
      "columns": [
        {"name": "id", "type": "INTEGER", "primary_key": true, "nullable": false},
        {"name": "name", "type": "VARCHAR(255)", "primary_key": false, "nullable": false},
        {"name": "plan", "type": "VARCHAR(50)", "primary_key": false, "nullable": false},
        {"name": "country", "type": "VARCHAR(100)", "primary_key": false, "nullable": true},
        {"name": "industry", "type": "VARCHAR(100)", "primary_key": false, "nullable": true},
        {"name": "employee_count", "type": "INTEGER", "primary_key": false, "nullable": true},
        {"name": "created_at", "type": "TIMESTAMPTZ", "primary_key": false, "nullable": false},
        {"name": "churned_at", "type": "TIMESTAMPTZ", "primary_key": false, "nullable": true}
      ],
      "primary_keys": ["id"],
      "foreign_keys": []
    },
    "users": {
      "columns": [
        {"name": "id", "type": "INTEGER", "primary_key": true, "nullable": false},
        {"name": "org_id", "type": "INTEGER", "primary_key": false, "nullable": false},
        {"name": "email", "type": "VARCHAR(255)", "primary_key": false, "nullable": false},
        {"name": "role", "type": "VARCHAR(50)", "primary_key": false, "nullable": false},
        {"name": "is_active", "type": "BOOLEAN", "primary_key": false, "nullable": false}
      ],
      "primary_keys": ["id"],
      "foreign_keys": [
        {"column": "org_id", "references_table": "organizations", "references_column": "id"}
      ]
    }
  }
}
```

### `POST /v1/schema/refresh`
Forces the schema inspector to re-introspect PostgreSQL and update memory caches.

#### Response (`200 OK`):
```json
{
  "status": "refreshed",
  "tables": 7
}
```

---

## 4. History (`GET /v1/history`)

Returns execution history logs with timestamps, row counts, and feedback states.

### Query Parameters:
- `limit` (integer, optional, default: 50): Max items to return.

#### Response (`200 OK`):
```json
[
  {
    "query_id": "c1f7a0b3-90d1-4e89-a2de-6df37b420011",
    "question": "Show me the top 5 organizations by MRR",
    "sql": "SELECT o.name, s.mrr FROM organizations o JOIN subscriptions s ON o.id = s.org_id ...",
    "status": "success",
    "confidence_percentage": 96,
    "row_count": 5,
    "timestamp": "2026-10-17T13:30:00.000Z",
    "feedback": "correct"
  }
]
```

---

## 5. Feedback Flywheel (`GET /v1/history/flywheel`)

Returns verified few-shot candidate queries (marked `correct` by users) and active regression test cases (marked `incorrect` by users) to continuously improve model generation.

#### Response (`200 OK`):
```json
{
  "verified_few_shot_count": 3,
  "new_eval_case_count": 1,
  "few_shots": [
    {
      "query_id": "c1f7a0b3-90d1-4e89-a2de-6df37b420011",
      "question": "Show me the top 5 organizations by MRR",
      "sql": "SELECT o.name, s.mrr FROM organizations o JOIN subscriptions s ON o.id = s.org_id WHERE s.status = 'active' ORDER BY s.mrr DESC LIMIT 5",
      "feedback": "correct"
    }
  ],
  "eval_cases": [
    {
      "id": "feedback_7a942bc0",
      "category": "user_reported_anomaly",
      "question": "List churned users in Q3",
      "generated_sql": "SELECT * FROM users WHERE last_login_at < '2024-09-30'",
      "user_note": "Users do not have churn dates, organizations do."
    }
  ]
}
```

---

## 6. Confidence Scoring Rubric

The deterministic 100-point scoring model combines 5 independent validation signals:

| Signal Name | Max Points | Weight | Metric Logic |
|---|---|---|---|
| **SQL Syntax & Guardrails** | 20 | 20% | 20 pts if parsed successfully & passed AST safety; 0 if blocked. |
| **Schema Coverage & Validity** | 20 | 20% | 20 pts if 100% of tables/columns exist in active schema; -5 pts per missing entity. |
| **Question Alignment** | 25 | 25% | `alignment_score * 25` from LLM back-translation comparison. |
| **Result Sanity Check** | 20 | 20% | `pass_rate * 20` across empty sets, negative values, NULL densities, and date limits. |
| **Multi-Query Consensus** | 15 | 15% | 15 pts if independent secondary SQL yields matching result set. |

---

## 7. System Health (`GET /v1/health`)

Returns real-time health status of database connectivity and active model provider.

#### Response (`200 OK`):
```json
{
  "status": "healthy",
  "database": "connected",
  "model": "gpt-4o-mini",
  "env": "production"
}
```

---

## cURL Example

```bash
curl -X POST "http://localhost:8000/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many active users signed up this month?",
    "enable_multi_query": true,
    "max_rows": 50
  }'
```
