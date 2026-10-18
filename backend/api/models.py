"""Pydantic request/response models for the API."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    clarification_choice: str | None = None
    enable_multi_query: bool = True
    max_rows: int = Field(default=100, ge=1, le=1000)
    custom_sql: str | None = None


class FeedbackRequest(BaseModel):
    feedback: Literal["correct", "incorrect"]
    user_note: str | None = None


# ── Response Components ───────────────────────────────────────────────────────

class ClarificationOption(BaseModel):
    label: str
    description: str
    example_sql: str | None = None


class ScoreSignalModel(BaseModel):
    name: str
    display_name: str
    max_points: int
    earned_points: float
    passed: bool | None
    detail: str


class ConfidenceScoreModel(BaseModel):
    percentage: int
    label: str
    total_score: float
    signals: list[ScoreSignalModel]
    summary: str


class GuardrailInfo(BaseModel):
    passed: bool
    blocked_reason: str | None
    warnings: list[str]


class SchemaValidationModel(BaseModel):
    valid: bool
    invalid_tables: list[str]
    invalid_columns: list[dict]


class BackTranslationModel(BaseModel):
    back_translated_question: str
    alignment_score: float
    alignment_explanation: str
    is_aligned: bool


class HallucinationModel(BaseModel):
    hallucination_detected: bool
    schema_valid: bool
    invalid_tables: list[str]
    invalid_columns: list[dict]
    back_translation: BackTranslationModel | None
    hallucination_reasons: list[str]


class SanityCheckModel(BaseModel):
    name: str
    passed: bool
    message: str
    severity: str


class SanityResultModel(BaseModel):
    passed: bool
    pass_rate: float
    warnings: list[str]
    checks: list[SanityCheckModel]


class MultiQueryModel(BaseModel):
    enabled: bool
    alternative_sql: str | None
    results_agree: bool | None
    agreement_score: float | None
    discrepancy_explanation: str | None


class ExecutionInfo(BaseModel):
    execution_time_ms: float
    row_count: int
    was_limited: bool
    explain_plan: str | None


# ── Main Response ─────────────────────────────────────────────────────────────

class QueryResponse(BaseModel):
    query_id: str
    question: str
    status: Literal["success", "clarification", "blocked", "error", "unanswerable"]

    # SQL
    sql: str | None = None
    sql_explanation: str | None = None
    tables_used: list[str] = []

    # Results
    columns: list[str] = []
    rows: list[dict[str, Any]] = []

    # Validation layers
    guardrail: GuardrailInfo | None = None
    hallucination: HallucinationModel | None = None
    sanity: SanityResultModel | None = None
    multi_query: MultiQueryModel | None = None

    # Confidence
    confidence: ConfidenceScoreModel | None = None

    # Execution info
    execution: ExecutionInfo | None = None

    # Clarification
    clarification_options: list[ClarificationOption] = []
    unanswerable_reason: str | None = None

    # Error
    error_message: str | None = None

    # History
    timestamp: str
    feedback: str | None = None


class HistoryItem(BaseModel):
    query_id: str
    question: str
    sql: str | None
    status: str
    confidence_percentage: int | None
    row_count: int | None
    timestamp: str
    feedback: str | None
