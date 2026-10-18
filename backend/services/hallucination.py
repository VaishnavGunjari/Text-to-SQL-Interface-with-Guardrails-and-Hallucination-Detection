"""Hallucination detection: schema validation + SQL-to-question back-translation."""
from __future__ import annotations
from dataclasses import dataclass, field
import sqlglot
import sqlglot.expressions as exp
from database.schema_inspector import get_schema
from services.llm_service import call_llm_json
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class SchemaValidationResult:
    valid: bool
    invalid_tables: list[str] = field(default_factory=list)
    invalid_columns: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class BackTranslationResult:
    back_translated_question: str
    alignment_score: float  # 0.0-1.0
    alignment_explanation: str
    is_aligned: bool


@dataclass
class HallucinationResult:
    schema_valid: bool
    invalid_tables: list[str]
    invalid_columns: list[dict]
    back_translation: BackTranslationResult | None
    hallucination_detected: bool
    hallucination_reasons: list[str]
    schema_warnings: list[str]


def validate_schema(sql: str) -> SchemaValidationResult:
    """
    Check that all tables and columns referenced in the SQL actually exist in the DB.
    Uses SQLGlot AST traversal.
    """
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except Exception as e:
        return SchemaValidationResult(
            valid=False,
            warnings=[f"Could not parse SQL for schema validation: {e}"],
        )

    schema = get_schema()
    all_tables = {t.name.lower() for t in schema.tables}
    table_columns = {t.name.lower(): {c.name.lower() for c in t.columns} for t in schema.tables}

    invalid_tables = []
    invalid_columns = []
    warnings = []

    # Extract table references
    referenced_tables = {}
    for table_node in parsed.find_all(exp.Table):
        table_name = table_node.name.lower()
        alias = table_node.alias.lower() if table_node.alias else table_name
        if table_name and table_name not in all_tables:
            if table_name not in invalid_tables:
                invalid_tables.append(table_name)
        elif table_name:
            referenced_tables[alias] = table_name

    # Extract column references
    for col_node in parsed.find_all(exp.Column):
        col_name = col_node.name.lower() if col_node.name else ""
        table_ref = col_node.table.lower() if col_node.table else ""

        if col_name in ("*", "") or col_name is None:
            continue

        if table_ref and table_ref in referenced_tables:
            actual_table = referenced_tables[table_ref]
            if actual_table in table_columns:
                if col_name not in table_columns[actual_table]:
                    invalid_columns.append({
                        "column": col_name,
                        "table": actual_table,
                        "reason": f"Column '{col_name}' does not exist in table '{actual_table}'",
                    })
        elif table_ref and table_ref in all_tables:
            if col_name not in table_columns.get(table_ref, set()):
                invalid_columns.append({
                    "column": col_name,
                    "table": table_ref,
                    "reason": f"Column '{col_name}' does not exist in table '{table_ref}'",
                })

    is_valid = len(invalid_tables) == 0 and len(invalid_columns) == 0
    logger.info(
        "Schema validation complete",
        valid=is_valid,
        invalid_tables=invalid_tables,
        invalid_columns=len(invalid_columns),
    )

    return SchemaValidationResult(
        valid=is_valid,
        invalid_tables=invalid_tables,
        invalid_columns=invalid_columns,
        warnings=warnings,
    )


def back_translate_sql(sql: str, original_question: str) -> BackTranslationResult:
    """
    Ask the LLM: 'What question does this SQL answer?'
    Then score alignment with the original question.
    """
    system = """You are an expert SQL analyst. Given a SQL query, describe in plain English what question it answers, then compare it to the original question and score the alignment.

Return JSON:
{
  "back_translated_question": "The question this SQL answers in plain English",
  "alignment_score": 0.0-1.0,
  "alignment_explanation": "Brief explanation of why the score is this value"
}

Alignment scoring guide:
- 1.0: SQL perfectly answers the original question
- 0.8-0.99: Minor differences in phrasing but same intent
- 0.6-0.79: Related but slightly different scope or conditions
- 0.4-0.59: Partially overlapping intent
- 0.0-0.39: Different question entirely (hallucination)"""

    user_msg = f"""Original Question: {original_question}

SQL Query:
{sql}

What question does this SQL answer? Rate alignment with the original question."""

    try:
        result = call_llm_json(system, user_msg)
        score = float(result.get("alignment_score", 0.5))
        return BackTranslationResult(
            back_translated_question=result.get("back_translated_question", ""),
            alignment_score=score,
            alignment_explanation=result.get("alignment_explanation", ""),
            is_aligned=score >= 0.65,
        )
    except Exception as e:
        logger.warning("Back-translation failed", error=str(e))
        return BackTranslationResult(
            back_translated_question="",
            alignment_score=0.5,
            alignment_explanation=f"Back-translation failed: {e}",
            is_aligned=True,  # Don't penalize if service is unavailable
        )


def detect_hallucinations(
    sql: str,
    original_question: str,
    skip_back_translation: bool = False,
) -> HallucinationResult:
    """Full hallucination detection pipeline."""
    schema_result = validate_schema(sql)
    back_translation = None
    if not skip_back_translation and schema_result.valid:
        back_translation = back_translate_sql(sql, original_question)

    hallucination_reasons = []
    if not schema_result.valid:
        if schema_result.invalid_tables:
            hallucination_reasons.append(
                f"References non-existent tables: {', '.join(schema_result.invalid_tables)}"
            )
        for col in schema_result.invalid_columns:
            hallucination_reasons.append(col["reason"])

    if back_translation and not back_translation.is_aligned:
        hallucination_reasons.append(
            f"SQL answers a different question (alignment: {back_translation.alignment_score:.0%}): "
            f"'{back_translation.back_translated_question}'"
        )

    return HallucinationResult(
        schema_valid=schema_result.valid,
        invalid_tables=schema_result.invalid_tables,
        invalid_columns=schema_result.invalid_columns,
        back_translation=back_translation,
        hallucination_detected=len(hallucination_reasons) > 0,
        hallucination_reasons=hallucination_reasons,
        schema_warnings=schema_result.warnings,
    )
