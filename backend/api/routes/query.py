"""Main query endpoint — orchestrates the full Text-to-SQL pipeline."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from api.models import (
    QueryRequest, QueryResponse, FeedbackRequest,
    GuardrailInfo, HallucinationModel, BackTranslationModel,
    SanityResultModel, SanityCheckModel, MultiQueryModel,
    ConfidenceScoreModel, ScoreSignalModel, ExecutionInfo,
    ClarificationOption,
)
from api.history_store import save_query, update_feedback, get_query
from services.sql_generator import generate_sql
from services.sql_guardrails import validate_sql
from services.sql_executor import execute_sql
from services.hallucination import detect_hallucinations
from services.result_validator import check_results
from services.multi_query import run_multi_query_validation
from services.confidence_scorer import calculate_confidence
from config import get_settings
from logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
_settings = get_settings()


@router.post("/query", response_model=QueryResponse)
async def run_query(req: QueryRequest):
    """Main Text-to-SQL pipeline endpoint."""
    logger.info("Query received", question=req.question[:100])
    timestamp = datetime.now(timezone.utc).isoformat()

    # ══ STEP 1: Generate or Accept Custom SQL ═════════════════════════════════
    clean_q = req.question.strip()
    direct_sql_keywords = ("SELECT ", "DROP ", "DELETE ", "INSERT ", "UPDATE ", "ALTER ", "TRUNCATE ", "CREATE ")
    if req.custom_sql or any(clean_q.upper().startswith(kw) for kw in direct_sql_keywords):
        sql = req.custom_sql or clean_q
        sql_explanation = "Direct / custom SQL query"
        tables_used = []
    else:
        try:
            gen = generate_sql(
                question=req.question,
                max_rows=req.max_rows,
                clarification_choice=req.clarification_choice,
            )
        except Exception as e:
            logger.error("SQL generation failed", error=str(e))
            qid = save_query({"question": req.question, "status": "error", "error": str(e)})
            return QueryResponse(
                query_id=qid, question=req.question, status="error",
                error_message=f"SQL generation failed: {e}", timestamp=timestamp,
            )

        # ══ Handle clarification needed ══════════════════════════════════════════
        if gen.type == "clarification":
            qid = save_query({"question": req.question, "status": "clarification"})
            return QueryResponse(
                query_id=qid,
                question=req.question,
                status="clarification",
                clarification_options=[
                    ClarificationOption(
                        label=o["label"],
                        description=o["description"],
                        example_sql=o.get("example_sql"),
                    )
                    for o in gen.clarification_options
                ],
                timestamp=timestamp,
            )

        # ══ Handle unanswerable ══════════════════════════════════════════════════
        if gen.type == "unanswerable":
            qid = save_query({"question": req.question, "status": "unanswerable"})
            return QueryResponse(
                query_id=qid,
                question=req.question,
                status="unanswerable",
                unanswerable_reason=gen.unanswerable_reason,
                timestamp=timestamp,
            )

        sql = gen.sql
        sql_explanation = gen.explanation
        tables_used = gen.tables_used

    # ══ STEP 2: SQL Guardrails ════════════════════════════════════════════════
    guardrail = validate_sql(sql)
    guardrail_model = GuardrailInfo(
        passed=guardrail.passed,
        blocked_reason=guardrail.blocked_reason,
        warnings=guardrail.warnings,
    )

    if not guardrail.passed:
        conf = calculate_confidence(guardrail, None, None, None, None)
        qid = save_query({
            "question": req.question,
            "sql": sql,
            "status": "blocked",
            "blocked_reason": guardrail.blocked_reason,
            "confidence_percentage": conf.percentage,
        })
        return QueryResponse(
            query_id=qid,
            question=req.question,
            status="blocked",
            sql=sql,
            sql_explanation=sql_explanation,
            tables_used=tables_used,
            guardrail=guardrail_model,
            confidence=_conf_model(conf),
            error_message=f"Query blocked by AST Guardrails: {guardrail.blocked_reason}",
            timestamp=timestamp,
        )

    # Use normalized SQL from guardrail
    sql = guardrail.normalized_sql or sql

    # ══ STEP 3: Hallucination Detection ══════════════════════════════════════
    hallucination = detect_hallucinations(sql, req.question)
    hallucination_model = HallucinationModel(
        hallucination_detected=hallucination.hallucination_detected,
        schema_valid=hallucination.schema_valid,
        invalid_tables=hallucination.invalid_tables,
        invalid_columns=hallucination.invalid_columns,
        back_translation=BackTranslationModel(
            back_translated_question=hallucination.back_translation.back_translated_question,
            alignment_score=hallucination.back_translation.alignment_score,
            alignment_explanation=hallucination.back_translation.alignment_explanation,
            is_aligned=hallucination.back_translation.is_aligned,
        ) if hallucination.back_translation else None,
        hallucination_reasons=hallucination.hallucination_reasons,
    )

    # ══ STEP 4: Execute SQL ════════════════════════════════════════════════════
    exec_result = execute_sql(sql, max_rows=req.max_rows)

    if not exec_result.success:
        qid = save_query({
            "question": req.question, "sql": sql, "status": "error",
            "error": exec_result.error,
        })
        conf = calculate_confidence(guardrail, hallucination, None, None,
                                    hallucination.back_translation.alignment_score if hallucination.back_translation else None)
        return QueryResponse(
            query_id=qid,
            question=req.question,
            status="error",
            sql=sql,
            sql_explanation=sql_explanation,
            tables_used=tables_used,
            guardrail=guardrail_model,
            hallucination=hallucination_model,
            confidence=_conf_model(conf),
            error_message=f"Execution failed: {exec_result.error}",
            timestamp=timestamp,
        )

    # ══ STEP 5: Result Sanity Checks ═════════════════════════════════════════
    sanity = check_results(
        rows=exec_result.rows,
        columns=exec_result.columns,
        original_question=req.question,
        row_count=exec_result.row_count,
    )
    sanity_model = SanityResultModel(
        passed=sanity.passed,
        pass_rate=sanity.pass_rate,
        warnings=sanity.warnings,
        checks=[SanityCheckModel(name=c.name, passed=c.passed, message=c.message, severity=c.severity)
                for c in sanity.checks],
    )

    # ══ STEP 6: Multi-Query Validation ══════════════════════════════════════
    multi_result = None
    multi_model = None
    if req.enable_multi_query and _settings.enable_multi_query_validation and exec_result.row_count > 0:
        multi_result = run_multi_query_validation(
            question=req.question,
            primary_sql=sql,
            primary_result=exec_result,
            max_rows=req.max_rows,
        )
        if multi_result.enabled:
            multi_model = MultiQueryModel(
                enabled=True,
                alternative_sql=multi_result.alternative_sql,
                results_agree=multi_result.results_agree,
                agreement_score=multi_result.agreement_score,
                discrepancy_explanation=multi_result.discrepancy_explanation,
            )

    # ══ STEP 7: Confidence Score ══════════════════════════════════════════════
    alignment_score = hallucination.back_translation.alignment_score if hallucination.back_translation else None
    confidence = calculate_confidence(guardrail, hallucination, sanity, multi_result, alignment_score)
    conf_model = _conf_model(confidence)

    # ══ STEP 8: Save to history ════════════════════════════════════════════
    qid = save_query({
        "question": req.question,
        "sql": sql,
        "status": "success",
        "confidence_percentage": confidence.percentage,
        "row_count": exec_result.row_count,
    })

    return QueryResponse(
        query_id=qid,
        question=req.question,
        status="success",
        sql=sql,
        sql_explanation=sql_explanation,
        tables_used=tables_used,
        columns=exec_result.columns,
        rows=exec_result.rows,
        guardrail=guardrail_model,
        hallucination=hallucination_model,
        sanity=sanity_model,
        multi_query=multi_model or MultiQueryModel(enabled=False, alternative_sql=None,
                                                    results_agree=None, agreement_score=None,
                                                    discrepancy_explanation=None),
        confidence=conf_model,
        execution=ExecutionInfo(
            execution_time_ms=exec_result.execution_time_ms,
            row_count=exec_result.row_count,
            was_limited=exec_result.was_limited,
            explain_plan=exec_result.explain_plan,
        ),
        timestamp=timestamp,
    )


@router.patch("/history/{query_id}/feedback")
async def submit_feedback(query_id: str, req: FeedbackRequest):
    success = update_feedback(query_id, req.feedback, req.user_note)
    if not success:
        raise HTTPException(status_code=404, detail="Query not found")
    return {"status": "ok", "query_id": query_id, "feedback": req.feedback}


def _conf_model(confidence) -> ConfidenceScoreModel:
    return ConfidenceScoreModel(
        percentage=confidence.percentage,
        label=confidence.label,
        total_score=confidence.total_score,
        signals=[
            ScoreSignalModel(
                name=s.name,
                display_name=s.display_name,
                max_points=s.max_points,
                earned_points=s.earned_points,
                passed=s.passed,
                detail=s.detail,
            )
            for s in confidence.signals
        ],
        summary=confidence.summary,
    )
