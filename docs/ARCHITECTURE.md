# Text-to-SQL AI — Architecture & Engineering Specification

This document provides a technical deep-dive into the architectural design, security guardrails, hallucination prevention mechanisms, and scoring models powering the **Text-to-SQL AI** engine.

---

## 1. High-Level Architecture

The service bridges the gap between natural language user intents and relational database queries using an **8-Stage Defense-in-Depth Pipeline**:

```
[ User Prompt ]
       │
       ▼
 1. Few-Shot LLM Translation ────────► (Ambiguous? ─► Structured Clarification Dialog)
       │                              (Out-of-scope? ─► Structured Unanswerable Catch)
       ▼
 2. AST SQL Guardrails ──────────────► (Violates Rules? ─► Block Query with Specific Reason)
       │                              (Row Scan Cost > Limit? ─► Block Query via EXPLAIN)
       ▼
 3. Hallucination Detection ─────────► (Catalog Schema Entity Check & Reverse Back-Translation)
       │
       ▼
 4. Read-Only SQL Execution ─────────► (PostgreSQL READ ONLY transaction, statement timeout & EXPLAIN)
       │
       ▼
 5. Result Sanity Checks ────────────► (Empty sets, boundary violations, NULL ratios, anomalies)
       │
       ▼
 6. Multi-Query Agreement ───────────► (Dual-Prompt Formulation Consensus & Set Similarity)
       │
       ▼
 7. Confidence Scorer ───────────────► (0-100% Deterministic Score across 5 Weighted Signals)
       │
       ▼
 8. Audit Store & Frontend ──────────► (Monochrome UI, Power-User Editable SQL, Human Feedback)
```

---

## 2. Pipeline Stages in Detail

### Stage 1: Few-Shot SQL Generation & Schema Filtering
- **Schema Context**: Automatically extracts table definitions, column types, primary/foreign keys, and **sample distinct values for categorical columns** to disambiguate string filters.
- **Dynamic Schema Filtering**: Filters tables to those relevant to the user query context, keeping prompts focused and preventing LLM context dilution.
- **Ambiguity Detection**: If the question maps to multiple potential business metrics (e.g. "What is our revenue?" -> MRR vs Invoiced revenue), returns `type: "clarification"` with selectable options and concrete example SQL.
- **Unanswerable Catching**: Identifies queries referencing entities absent from the database (e.g. AWS CPU metrics or Google Ads analytics) and explains why they cannot be answered.

### Stage 2: SQL Guardrails (`services/sql_guardrails.py`)
Queries are parsed through `sqlglot` to inspect Abstract Syntax Trees (AST):
1. **DML/DDL Blocking**:
   - Strictly blocks: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `CREATE`, `REPLACE`, `EXEC`, `EXECUTE`, `COPY`.
   - Rejects queries containing semicolons or multiple concatenated statements.
2. **Subquery Depth Enforcement**:
   - Rejects queries with subqueries nested deeper than 3 levels to avoid pathological execution plans.
3. **Table Whitelisting**:
   - Only allows access to authorized application tables (`organizations`, `users`, `subscriptions`, `invoices`, `events`, `features`, `feature_usage`).
   - Rejects internal PostgreSQL catalogs (`pg_*`, `information_schema`).
4. **Automatic Limit Injection**:
   - Ensures any `SELECT` query without an explicit `LIMIT` has `LIMIT 1000` appended.
5. **Cost / Estimated Scan Row Guardrail**:
   - Runs `EXPLAIN` prior to execution. If the query planner estimates scanning more than `max_estimated_scan_rows` (default: 1,000,000 rows), the query is blocked to prevent server resource exhaustion.

### Stage 3: Hallucination Detection (`services/hallucination.py`)
1. **Schema Entity Verification**:
   - Extracts every referenced table and column from the generated SQL AST.
   - Cross-checks against the active schema inspector. If a column or table does not exist, marks `hallucination_detected: true`.
2. **Back-Translation Check**:
   - Takes the generated SQL and prompts an LLM: *"What question does this SQL query answer?"*
   - Computes a semantic alignment score (0.0 to 1.0) between the user's original question and the back-translated question.
   - If the score is `< 0.65`, a semantic misalignment warning is triggered.

### Stage 4: Read-Only SQL Execution (`services/sql_executor.py`)
- Executes using an isolated connection pool with:
  - `SET TRANSACTION READ ONLY`
  - Statement timeout enforced (default: 30 seconds).
  - Captures `EXPLAIN` execution plans.
  - Measures execution wall-clock time in milliseconds.

### Stage 5: Result Sanity Checks (`services/result_validator.py`)
Analyzes the resulting record set:
- **Empty Result Warning**: Alerts if a query with filters returns 0 rows when rows were expected.
- **Extreme Value Checks**: Detects anomalies such as negative amounts for billing fields or impossible counts.
- **Null Ratio**: Warns if a non-nullable or primary field has unexpected NULL densities indicating a bad outer JOIN.
- **Aggregation Consistency**: Ensures aggregations like `COUNT(*)` match array lengths.

### Stage 6: Multi-Query Agreement (`services/multi_query.py`)
- Generates an alternative SQL formulation using a secondary prompting strategy (e.g., using Common Table Expressions `WITH` vs subqueries, or alternative join orders).
- Executes the secondary query and calculates Jaccard / set similarity between primary and secondary row sets.
- High similarity guarantees consensus across independent query generations.

### Stage 7: Confidence Scoring Engine (`services/confidence_scorer.py`)
Produces a deterministic 0-100% confidence metric based on a weighted 100-point rubric:

| Signal | Maximum Points | Calculation Criteria |
|---|---|---|
| **SQL Syntax & Guardrails** | 20 | 20 pts if parsed and passed all safety rules; 0 pts if blocked. |
| **Schema Coverage & Validity** | 20 | 20 pts if 100% of tables and columns exist in schema; drops by 5 pts per missing entity. |
| **Question Alignment** | 25 | Earned = `alignment_score * 25` from LLM back-translation. |
| **Result Sanity** | 20 | Earned = `pass_rate * 20` across statistical anomaly rules. |
| **Multi-Query Consensus** | 15 | 15 pts if alternative query matches; partial/zero if divergent. |

#### Confidence Classifications:
- **High (>= 85%)**: Verified safe, semantically aligned, high consensus.
- **Medium (65% - 84%)**: Valid SQL, but minor warning (e.g. empty result or partial back-translation alignment).
- **Low (40% - 64%)**: Flagged safety risk, schema discrepancy, or execution anomaly.
- **Very Low (< 40%)**: Critical failure (syntax error, blocked operation, or severe hallucination).

---

## 3. Evaluation Suite (`backend/evals/`)

The repository includes a regression test suite covering 52 golden queries across:
- **Simple lookups** (10 test cases)
- **Multi-table JOINs** (12 test cases)
- **Aggregations with GROUP BY** (10 test cases)
- **Date range filters** (8 test cases)
- **Ambiguous phrasing** (6 test cases)
- **Unanswerable / Out-of-scope** (6 test cases)
- **Adversarial / Dangerous operations** (4 test cases)

To run the automated evaluation suite:
```bash
python backend/evals/eval_runner.py
```
