"""Multi-query validation: generate and compare two independent SQL approaches."""
from __future__ import annotations
from dataclasses import dataclass
from services.sql_generator import generate_alternative_sql
from services.sql_guardrails import validate_sql
from services.sql_executor import execute_sql, ExecutionResult
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class MultiQueryResult:
    enabled: bool
    primary_result: ExecutionResult | None = None
    alternative_sql: str | None = None
    alternative_result: ExecutionResult | None = None
    results_agree: bool | None = None
    agreement_score: float | None = None  # 0.0-1.0
    discrepancy_explanation: str | None = None
    strategy_note: str | None = None


def run_multi_query_validation(
    question: str,
    primary_sql: str,
    primary_result: ExecutionResult,
    max_rows: int = 100,
) -> MultiQueryResult:
    """
    Generate an alternative SQL approach and compare results.
    Only meaningful for queries that return aggregations or counts.
    """
    logger.info("Running multi-query validation", question=question[:80])

    # Generate alternative SQL
    alt_sql = generate_alternative_sql(question, primary_sql)
    if not alt_sql:
        return MultiQueryResult(enabled=False)

    # Validate the alternative SQL
    guardrail = validate_sql(alt_sql)
    if not guardrail.passed:
        logger.warning("Alternative SQL failed guardrails", reason=guardrail.blocked_reason)
        return MultiQueryResult(enabled=True, alternative_sql=alt_sql)

    # Execute alternative
    alt_result = execute_sql(alt_sql, max_rows=max_rows)
    if not alt_result.success:
        logger.warning("Alternative SQL execution failed", error=alt_result.error)
        return MultiQueryResult(
            enabled=True,
            alternative_sql=alt_sql,
            alternative_result=alt_result,
        )

    # Compare results
    agree, score, explanation = _compare_results(primary_result, alt_result)

    logger.info("Multi-query comparison", agree=agree, score=score)
    return MultiQueryResult(
        enabled=True,
        primary_result=primary_result,
        alternative_sql=alt_sql,
        alternative_result=alt_result,
        results_agree=agree,
        agreement_score=score,
        discrepancy_explanation=None if agree else explanation,
        strategy_note="Alternative approach uses a different SQL strategy for independent verification.",
    )


def _compare_results(r1: ExecutionResult, r2: ExecutionResult) -> tuple[bool, float, str]:
    """
    Compare two result sets. Returns (agree, score, explanation).
    Focuses on aggregate values for meaningful comparison.
    """
    # If both empty
    if r1.row_count == 0 and r2.row_count == 0:
        return True, 1.0, "Both queries returned empty results"

    # If row counts differ significantly
    if r1.row_count != r2.row_count:
        diff_pct = abs(r1.row_count - r2.row_count) / max(r1.row_count, r2.row_count, 1)
        if diff_pct > 0.05:  # 5% tolerance
            return False, 1.0 - diff_pct, (
                f"Row count mismatch: primary={r1.row_count}, alternative={r2.row_count} "
                f"({diff_pct:.0%} difference)"
            )

    # If single-row aggregates, compare values numerically
    if r1.row_count == 1 and r2.row_count == 1:
        row1 = r1.rows[0]
        row2 = r2.rows[0]
        scores = []
        for key in row1:
            v1 = row1.get(key)
            v2 = _find_matching_value(key, row2)
            if v1 is not None and v2 is not None:
                try:
                    n1, n2 = float(v1), float(v2)
                    if n1 == 0 and n2 == 0:
                        scores.append(1.0)
                    elif max(abs(n1), abs(n2)) > 0:
                        diff = abs(n1 - n2) / max(abs(n1), abs(n2))
                        scores.append(max(0.0, 1.0 - diff))
                except (ValueError, TypeError):
                    pass

        if scores:
            avg_score = sum(scores) / len(scores)
            agree = avg_score >= 0.95
            explanation = f"Aggregate values {'match' if agree else 'differ'} (similarity: {avg_score:.0%})"
            return agree, avg_score, explanation

    return True, 0.9, "Row counts match — detailed comparison not applicable for this result type"


def _find_matching_value(key: str, row: dict) -> Any:
    """Find a matching value in another row dict (case-insensitive key match)."""
    if key in row:
        return row[key]
    key_lower = key.lower()
    for k, v in row.items():
        if k.lower() == key_lower:
            return v
    return None
