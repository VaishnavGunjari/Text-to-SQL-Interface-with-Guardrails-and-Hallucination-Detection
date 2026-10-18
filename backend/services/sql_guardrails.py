"""SQL safety guardrails using AST-based analysis via SQLGlot."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
import sqlglot
import sqlglot.expressions as exp
from config import get_settings
from logger import get_logger

logger = get_logger(__name__)
_settings = get_settings()

# Blocked statement types (DDL + DML writes)
BLOCKED_STATEMENT_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Grant,
    exp.Revoke,
    exp.Command,  # catches COPY, VACUUM, etc.
)

# Blocked keywords as extra string-level defense (belt-and-suspenders)
BLOCKED_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bCREATE\b", r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXECUTE\b", r"\bEXEC\b", r"\bXP_\b",
    r"\bPG_SLEEP\b", r"\bPG_READ_FILE\b", r"\bCOPY\b",
]


@dataclass
class GuardrailResult:
    passed: bool
    blocked_reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    normalized_sql: str | None = None


def validate_sql(sql: str) -> GuardrailResult:
    """
    Run all safety checks on a SQL string.
    Returns GuardrailResult with passed=True only if ALL checks pass.
    """
    warnings = []

    # ── 1. Keyword-level defense (catches obfuscated SQL before parsing) ──
    sql_upper = sql.upper()
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, sql_upper):
            clean_pat = pattern.replace(r"\b", "")
            reason = f"Blocked keyword detected: {clean_pat}"
            logger.warning("SQL BLOCKED (keyword)", reason=reason, sql=sql[:200])
            return GuardrailResult(passed=False, blocked_reason=reason)

    # ── 2. Multiple statement detection ──
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        reason = "Multiple SQL statements detected"
        logger.warning("SQL BLOCKED (multi-statement)", sql=sql[:200])
        return GuardrailResult(passed=False, blocked_reason=reason)

    # ── 3. AST parsing ──
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.ParseError as e:
        reason = f"SQL syntax error: {e}"
        logger.warning("SQL BLOCKED (parse error)", error=str(e))
        return GuardrailResult(passed=False, blocked_reason=reason)

    if parsed is None:
        return GuardrailResult(passed=False, blocked_reason="Could not parse SQL")

    # ── 4. AST-level statement type check ──
    if isinstance(parsed, BLOCKED_STATEMENT_TYPES):
        reason = f"Blocked statement type: {type(parsed).__name__}"
        logger.warning("SQL BLOCKED (statement type)", statement_type=type(parsed).__name__, sql=sql[:200])
        return GuardrailResult(passed=False, blocked_reason=reason)

    # Must be a SELECT
    if not isinstance(parsed, exp.Select):
        reason = f"Only SELECT queries are allowed. Got: {type(parsed).__name__}"
        logger.warning("SQL BLOCKED (non-select)", sql=sql[:200])
        return GuardrailResult(passed=False, blocked_reason=reason)

    # ── 5. Subquery depth check ──
    depth = _get_subquery_depth(parsed)
    max_depth = _settings.max_subquery_depth
    if depth > max_depth:
        reason = f"Query subquery depth ({depth}) exceeds maximum allowed ({max_depth})"
        logger.warning("SQL BLOCKED (depth)", depth=depth)
        return GuardrailResult(passed=False, blocked_reason=reason)

    # ── 6. LIMIT enforcement ──
    has_limit = parsed.find(exp.Limit) is not None
    if not has_limit:
        warnings.append(f"No LIMIT clause detected. Will enforce LIMIT {_settings.max_rows} at execution.")

    # ── 7. SQL injection pattern detection ──
    injection_patterns = [
        r"'.*'.*OR.*'.*'",  # ' OR '1'='1
        r"--",              # comment injection
        r"/\*.*\*/",        # block comment
        r"0x[0-9a-fA-F]+", # hex encoding
    ]
    for pat in injection_patterns:
        if re.search(pat, sql, re.IGNORECASE | re.DOTALL):
            warnings.append(f"Possible SQL injection pattern detected: {pat}")

    # ── 8. Normalize SQL ──
    try:
        normalized = sqlglot.transpile(sql, read="postgres", write="postgres", pretty=True)[0]
    except Exception:
        normalized = sql

    logger.info("SQL passed guardrails", warnings=warnings)
    return GuardrailResult(
        passed=True,
        warnings=warnings,
        normalized_sql=normalized,
    )


def _get_subquery_depth(node: exp.Expression, current_depth: int = 0) -> int:
    """Recursively calculate the maximum subquery nesting depth."""
    max_depth = current_depth
    for child in node.walk():
        if isinstance(child, exp.Subquery) and child is not node:
            depth = _get_subquery_depth(child, current_depth + 1)
            max_depth = max(max_depth, depth)
    return max_depth


def enforce_limit(sql: str, max_rows: int) -> str:
    """Add or replace LIMIT clause to enforce max row count."""
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
        existing_limit = parsed.find(exp.Limit)
        if existing_limit:
            # Check if existing limit exceeds max
            try:
                limit_val = int(existing_limit.expression.this)
                if limit_val > max_rows:
                    existing_limit.set("expression", exp.Literal.number(max_rows))
            except (ValueError, AttributeError):
                pass
        else:
            parsed = parsed.limit(max_rows)
        return sqlglot.transpile(parsed.sql(), read="postgres", write="postgres")[0]
    except Exception:
        # Fallback: wrap in subquery with limit
        return f"SELECT * FROM ({sql}) AS _q LIMIT {max_rows}"
