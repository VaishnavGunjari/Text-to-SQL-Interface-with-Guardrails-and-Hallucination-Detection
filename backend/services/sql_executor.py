"""Safe read-only SQL execution with timeout and explain plan."""
from __future__ import annotations
import datetime
import decimal
import re
import time
from dataclasses import dataclass, field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database.connection import ro_engine
from services.sql_guardrails import enforce_limit
from config import get_settings
from logger import get_logger

logger = get_logger(__name__)
_settings = get_settings()


@dataclass
class ExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    explain_plan: str | None = None
    error: str | None = None
    was_limited: bool = False


def execute_sql(sql: str, max_rows: int | None = None) -> ExecutionResult:
    """
    Execute SQL in a read-only transaction with timeout enforcement.
    All executions are rolled back automatically.
    """
    if max_rows is None:
        max_rows = _settings.max_rows

    # Enforce row limit
    limited_sql = enforce_limit(sql, max_rows)
    was_limited = limited_sql != sql

    start = time.perf_counter()

    try:
        with ro_engine.connect() as conn:
            # Set statement timeout
            timeout_ms = _settings.query_timeout_seconds * 1000
            conn.execute(text(f"SET statement_timeout = {timeout_ms}"))
            # Force read-only transaction
            conn.execute(text("SET TRANSACTION READ ONLY"))

            # Get EXPLAIN plan first
            explain_plan = None
            try:
                explain_result = conn.execute(text(f"EXPLAIN {limited_sql}"))
                explain_plan = "\n".join(row[0] for row in explain_result)
                
                # Check estimated scan rows guardrail
                matches = re.findall(r"rows=(\d+)", explain_plan)
                if matches:
                    max_scan = max(int(m) for m in matches)
                    if max_scan > _settings.max_estimated_scan_rows:
                        reason = f"Query blocked by cost guardrail: estimated scan of {max_scan:,} rows exceeds maximum limit of {_settings.max_estimated_scan_rows:,}"
                        logger.warning("Query blocked by EXPLAIN scan guardrail", max_scan=max_scan)
                        return ExecutionResult(
                            success=False,
                            error=reason,
                            explain_plan=explain_plan,
                        )
            except Exception as e:
                logger.warning("EXPLAIN failed", error=str(e))

            # Execute actual query
            result = conn.execute(text(limited_sql))
            columns = list(result.keys())
            rows_raw = result.fetchall()

            elapsed_ms = (time.perf_counter() - start) * 1000

            rows = [dict(zip(columns, row)) for row in rows_raw]
            # Convert non-serializable types
            rows = _serialize_rows(rows)

            logger.info(
                "Query executed successfully",
                rows=len(rows),
                columns=len(columns),
                elapsed_ms=round(elapsed_ms, 2),
            )

            return ExecutionResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=round(elapsed_ms, 2),
                explain_plan=explain_plan,
                was_limited=was_limited,
            )

    except SQLAlchemyError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        logger.error("Query execution failed", error=error_msg, sql=sql[:200])
        return ExecutionResult(
            success=False,
            error=error_msg,
            execution_time_ms=round(elapsed_ms, 2),
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("Unexpected execution error", error=str(e))
        return ExecutionResult(
            success=False,
            error=str(e),
            execution_time_ms=round(elapsed_ms, 2),
        )


def _serialize_rows(rows: list[dict]) -> list[dict]:
    """Convert non-JSON-serializable types to strings."""
    serialized = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
                clean[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                clean[k] = float(v)
            elif isinstance(v, (bytes, bytearray)):
                clean[k] = v.hex()
            elif v is None:
                clean[k] = None
            else:
                clean[k] = v
        serialized.append(clean)
    return serialized
