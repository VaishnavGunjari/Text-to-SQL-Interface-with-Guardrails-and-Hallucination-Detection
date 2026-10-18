"""SQL generation with schema-aware prompting and ambiguity detection."""
from __future__ import annotations
from dataclasses import dataclass
from database.schema_inspector import get_schema, schema_to_prompt_context
from services.llm_service import call_llm_json
from logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert SQL analyst. Your job is to translate natural language questions into accurate PostgreSQL SQL queries.

Rules:
1. ONLY use tables and columns that exist in the provided schema. Never invent tables or columns.
2. Always use table aliases for clarity.
3. Always add LIMIT {max_rows} unless the question explicitly asks for all rows.
4. Use only SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE.
5. If the question is ambiguous and could mean multiple things (e.g., "revenue" could mean gross or net), return a clarification request instead of guessing.
6. If the question references something that doesn't exist in the schema, say so clearly.
7. Always return valid JSON in the exact structure specified.

{schema_context}

Return JSON with this exact structure:
{{
  "type": "sql" | "clarification" | "unanswerable",
  "sql": "SELECT ... (only if type=sql)",
  "explanation": "Plain English explanation of what the SQL does",
  "tables_used": ["table1", "table2"],
  "columns_used": ["table.column1", "table.column2"],
  "confidence_hint": 0.0-1.0,
  "clarification_options": [
    {{"label": "Option label", "description": "What this means", "example_sql": "SELECT ..."}}
  ],
  "unanswerable_reason": "Why it cannot be answered (only if type=unanswerable)"
}}
"""

FEW_SHOT_EXAMPLES = """
## Few-shot Examples for SaaS Analytics Domain

Q: "How many active users do we have?"
A: {{"type": "sql", "sql": "SELECT COUNT(*) AS active_users FROM users u WHERE u.is_active = true", "explanation": "Counts all users where is_active is true", "tables_used": ["users"], "columns_used": ["users.is_active"], "confidence_hint": 0.95, "clarification_options": [], "unanswerable_reason": null}}

Q: "What is the total MRR?"
A: {{"type": "sql", "sql": "SELECT SUM(s.mrr) AS total_mrr FROM subscriptions s WHERE s.status = 'active'", "explanation": "Sums MRR across all active subscriptions", "tables_used": ["subscriptions"], "columns_used": ["subscriptions.mrr", "subscriptions.status"], "confidence_hint": 0.92, "clarification_options": [], "unanswerable_reason": null}}

Q: "Show me revenue"
A: {{"type": "clarification", "sql": null, "explanation": null, "tables_used": [], "columns_used": [], "confidence_hint": 0.0, "clarification_options": [{{"label": "Monthly Recurring Revenue (MRR)", "description": "Sum of active subscription MRR", "example_sql": "SELECT SUM(mrr) FROM subscriptions WHERE status='active'"}}, {{"label": "Total Invoice Amount", "description": "Sum of all paid invoices", "example_sql": "SELECT SUM(amount) FROM invoices WHERE status='paid'"}}, {{"label": "Revenue by Organization", "description": "MRR broken down per organization", "example_sql": "SELECT org_id, SUM(mrr) FROM subscriptions GROUP BY org_id"}}], "unanswerable_reason": null}}
"""


@dataclass
class GenerationResult:
    type: str  # "sql" | "clarification" | "unanswerable"
    sql: str | None
    explanation: str | None
    tables_used: list[str]
    columns_used: list[str]
    confidence_hint: float
    clarification_options: list[dict]
    unanswerable_reason: str | None
    relevant_tables: list[str]


def _find_relevant_tables(question: str, all_tables: list[str]) -> list[str]:
    """Heuristic: return tables whose names appear in the question (lowercased)."""
    q_lower = question.lower()
    relevant = [t for t in all_tables if t.lower() in q_lower or t.lower().rstrip("s") in q_lower]
    # Always include all tables for small schemas (< 10 tables)
    if len(all_tables) <= 10 or not relevant:
        return all_tables
    return relevant


def generate_sql(question: str, max_rows: int = 1000, clarification_choice: str | None = None) -> GenerationResult:
    """
    Generate SQL from a natural language question.
    If clarification_choice is provided, it's appended to the question.
    """
    schema = get_schema()
    all_tables = [t.name for t in schema.tables]
    relevant_tables = _find_relevant_tables(question, all_tables)
    schema_context = schema_to_prompt_context(schema, relevant_tables if len(relevant_tables) < len(all_tables) else None)

    system = SYSTEM_PROMPT.format(schema_context=schema_context, max_rows=max_rows) + FEW_SHOT_EXAMPLES

    # ── Feedback Flywheel: inject verified correct user queries ──
    try:
        from api.history_store import get_verified_few_shots
        verified_shots = get_verified_few_shots(limit=3)
        if verified_shots:
            extra_shots = "\n## Verified Dynamic Examples (Feedback Flywheel):\n"
            for s in verified_shots:
                extra_shots += f'Q: "{s["question"]}"\nA: {{"type": "sql", "sql": "{s["sql"]}", "explanation": "Verified correct query", "tables_used": [], "columns_used": [], "confidence_hint": 0.95}}\n'
            system += extra_shots
    except Exception as e:
        logger.debug("Could not load dynamic feedback few-shots", error=str(e))

    user_question = question
    if clarification_choice:
        user_question = f"{question}\n\nUser clarification: {clarification_choice}"

    logger.info("Generating SQL", question=question[:100], relevant_tables=relevant_tables)

    result = call_llm_json(system, f"Translate this question to SQL:\n\n{user_question}")

    return GenerationResult(
        type=result.get("type", "sql"),
        sql=result.get("sql"),
        explanation=result.get("explanation"),
        tables_used=result.get("tables_used", []),
        columns_used=result.get("columns_used", []),
        confidence_hint=float(result.get("confidence_hint", 0.5)),
        clarification_options=result.get("clarification_options", []),
        unanswerable_reason=result.get("unanswerable_reason"),
        relevant_tables=relevant_tables,
    )


def generate_alternative_sql(question: str, primary_sql: str, max_rows: int = 1000) -> str | None:
    """Generate a second SQL approach using a different strategy."""
    schema = get_schema()
    schema_context = schema_to_prompt_context(schema)

    system = f"""You are an expert SQL analyst. Given a question and a primary SQL solution, generate an ALTERNATIVE SQL query that answers the SAME question using a different approach (e.g., different JOIN strategy, CTE vs subquery, different aggregation method).

{schema_context}

Return ONLY valid JSON:
{{
  "alternative_sql": "SELECT ...",
  "strategy_difference": "Brief explanation of how this differs from the primary approach"
}}"""

    user_msg = f"""Question: {question}

Primary SQL:
{primary_sql}

Generate a different SQL approach that answers the same question."""

    try:
        result = call_llm_json(system, user_msg)
        return result.get("alternative_sql")
    except Exception as e:
        logger.warning("Failed to generate alternative SQL", error=str(e))
        return None
