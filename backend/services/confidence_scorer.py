"""Deterministic confidence scoring system."""
from __future__ import annotations
from dataclasses import dataclass
from services.sql_guardrails import GuardrailResult
from services.hallucination import HallucinationResult
from services.result_validator import SanityResult
from services.multi_query import MultiQueryResult
from logger import get_logger

logger = get_logger(__name__)

# ── Scoring weights (must sum to 100) ──────────────────────────────────────
WEIGHTS = {
    "syntax_validity": 20,
    "schema_coverage": 20,
    "question_alignment": 25,
    "result_sanity": 20,
    "multi_query_agreement": 15,
}


@dataclass
class ScoreSignal:
    name: str
    display_name: str
    max_points: int
    earned_points: float
    passed: bool
    detail: str


@dataclass
class ConfidenceScore:
    total_score: float          # 0-100
    percentage: int             # 0-100 as integer
    label: str                  # "High", "Medium", "Low", "Very Low"
    signals: list[ScoreSignal]
    summary: str


def calculate_confidence(
    guardrail: GuardrailResult,
    hallucination: HallucinationResult | None,
    sanity: SanityResult | None,
    multi_query: MultiQueryResult | None,
    alignment_score: float | None,  # 0.0-1.0 from back-translation
) -> ConfidenceScore:
    """
    Calculate a deterministic confidence score from validation signals.
    The LLM does NOT decide this score.
    """
    signals = []
    total = 0.0

    # ── 1. SQL Syntax Validity (20 pts) ─────────────────────────────────────
    syntax_passed = guardrail.passed
    syntax_pts = WEIGHTS["syntax_validity"] if syntax_passed else 0
    total += syntax_pts
    signals.append(ScoreSignal(
        name="syntax_validity",
        display_name="SQL Syntax",
        max_points=WEIGHTS["syntax_validity"],
        earned_points=syntax_pts,
        passed=syntax_passed,
        detail="SQL parsed and passed all safety guardrails" if syntax_passed
               else f"Blocked: {guardrail.blocked_reason}",
    ))

    # ── 2. Schema Coverage (20 pts) ──────────────────────────────────────────
    if hallucination:
        schema_passed = hallucination.schema_valid
        if schema_passed:
            schema_pts = WEIGHTS["schema_coverage"]
            schema_detail = "All referenced tables and columns exist"
        else:
            invalid_count = len(hallucination.invalid_tables) + len(hallucination.invalid_columns)
            schema_pts = max(0, WEIGHTS["schema_coverage"] - (invalid_count * 5))
            schema_detail = f"Schema issues: {', '.join(hallucination.hallucination_reasons[:2])}"
        total += schema_pts
        signals.append(ScoreSignal(
            name="schema_coverage",
            display_name="Schema Validation",
            max_points=WEIGHTS["schema_coverage"],
            earned_points=schema_pts,
            passed=schema_passed,
            detail=schema_detail,
        ))
    else:
        # No hallucination check performed
        signals.append(ScoreSignal(
            name="schema_coverage",
            display_name="Schema Validation",
            max_points=WEIGHTS["schema_coverage"],
            earned_points=0,
            passed=False,
            detail="Schema validation skipped",
        ))

    # ── 3. Question Alignment (25 pts) ──────────────────────────────────────
    if alignment_score is not None:
        align_pts = round(WEIGHTS["question_alignment"] * alignment_score, 1)
        total += align_pts
        align_pct = f"{alignment_score:.0%}"
        signals.append(ScoreSignal(
            name="question_alignment",
            display_name="Question Alignment",
            max_points=WEIGHTS["question_alignment"],
            earned_points=align_pts,
            passed=alignment_score >= 0.65,
            detail=f"Back-translation similarity: {align_pct}" + (
                "" if alignment_score >= 0.65
                else " — SQL may answer a different question"
            ),
        ))
    else:
        # Give partial credit when back-translation is not available
        partial = round(WEIGHTS["question_alignment"] * 0.5, 1)
        total += partial
        signals.append(ScoreSignal(
            name="question_alignment",
            display_name="Question Alignment",
            max_points=WEIGHTS["question_alignment"],
            earned_points=partial,
            passed=False,
            detail="Back-translation not available",
        ))

    # ── 4. Result Sanity (20 pts) ────────────────────────────────────────────
    if sanity:
        sanity_pts = round(WEIGHTS["result_sanity"] * sanity.pass_rate, 1)
        total += sanity_pts
        signals.append(ScoreSignal(
            name="result_sanity",
            display_name="Result Sanity",
            max_points=WEIGHTS["result_sanity"],
            earned_points=sanity_pts,
            passed=sanity.passed,
            detail=f"Sanity check pass rate: {sanity.pass_rate:.0%}" + (
                f" ({len(sanity.warnings)} warning(s))" if sanity.warnings else ""
            ),
        ))
    else:
        signals.append(ScoreSignal(
            name="result_sanity",
            display_name="Result Sanity",
            max_points=WEIGHTS["result_sanity"],
            earned_points=0,
            passed=False,
            detail="Result sanity check not performed (query may have failed)",
        ))

    # ── 5. Multi-Query Agreement (15 pts) ────────────────────────────────────
    if multi_query and multi_query.enabled and multi_query.results_agree is not None:
        if multi_query.results_agree:
            mq_pts = WEIGHTS["multi_query_agreement"]
            mq_detail = f"Independent SQL approaches agree ({multi_query.agreement_score:.0%} similarity)"
        else:
            mq_pts = round(WEIGHTS["multi_query_agreement"] * (multi_query.agreement_score or 0.0), 1)
            mq_detail = f"Independent approaches disagree: {multi_query.discrepancy_explanation}"
        total += mq_pts
        signals.append(ScoreSignal(
            name="multi_query_agreement",
            display_name="Multi-Query Agreement",
            max_points=WEIGHTS["multi_query_agreement"],
            earned_points=mq_pts,
            passed=multi_query.results_agree,
            detail=mq_detail,
        ))
    else:
        # Not enabled — redistribute proportionally as neutral
        partial = round(WEIGHTS["multi_query_agreement"] * 0.7, 1)
        total += partial
        signals.append(ScoreSignal(
            name="multi_query_agreement",
            display_name="Multi-Query Agreement",
            max_points=WEIGHTS["multi_query_agreement"],
            earned_points=partial,
            passed=None,
            detail="Multi-query validation not performed for this query",
        ))

    # ── Final Score ──────────────────────────────────────────────────────────
    pct = round(min(100, max(0, total)))
    label = _score_label(pct)

    logger.info("Confidence score calculated", score=pct, label=label)
    return ConfidenceScore(
        total_score=round(total, 1),
        percentage=pct,
        label=label,
        signals=signals,
        summary=_build_summary(pct, label, signals),
    )


def _score_label(pct: int) -> str:
    if pct >= 85:
        return "High"
    elif pct >= 65:
        return "Medium"
    elif pct >= 40:
        return "Low"
    else:
        return "Very Low"


def _build_summary(pct: int, label: str, signals: list[ScoreSignal]) -> str:
    failing = [s.display_name for s in signals if s.passed is False]
    if not failing:
        return f"{pct}% confidence — all validation checks passed."
    return f"{pct}% confidence ({label}). Issues: {', '.join(failing)}."
