"""Unit tests for deterministic confidence scoring."""
from services.confidence_scorer import calculate_confidence
from services.sql_guardrails import GuardrailResult
from services.hallucination import HallucinationResult
from services.result_validator import SanityResult
from services.multi_query import MultiQueryResult


def test_high_confidence_calculation():
    guardrail = GuardrailResult(passed=True)
    hallucination = HallucinationResult(
        schema_valid=True,
        invalid_tables=[],
        invalid_columns=[],
        back_translation=None,
        hallucination_detected=False,
        hallucination_reasons=[],
        schema_warnings=[],
    )
    sanity = SanityResult(passed=True, pass_rate=1.0, checks=[], warnings=[])
    multi_query = MultiQueryResult(enabled=True, results_agree=True, agreement_score=1.0)

    score = calculate_confidence(
        guardrail=guardrail,
        hallucination=hallucination,
        sanity=sanity,
        multi_query=multi_query,
        alignment_score=1.0,
    )

    assert score.percentage >= 90
    assert score.label == "High"
    assert len(score.signals) == 5


def test_low_confidence_on_guardrail_failure():
    guardrail = GuardrailResult(passed=False, blocked_reason="Blocked DDL")
    score = calculate_confidence(
        guardrail=guardrail,
        hallucination=None,
        sanity=None,
        multi_query=None,
        alignment_score=None,
    )
    assert score.percentage < 50
    assert score.label in ["Low", "Very Low"]
