"""Result sanity checking after SQL execution."""
from __future__ import annotations
from dataclasses import dataclass, field
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class SanityCheck:
    name: str
    passed: bool
    message: str
    severity: str = "warning"  # "warning" | "error" | "info"


@dataclass
class SanityResult:
    passed: bool
    checks: list[SanityCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pass_rate: float = 1.0


def check_results(
    rows: list[dict],
    columns: list[str],
    original_question: str,
    row_count: int,
) -> SanityResult:
    """Run sanity checks on query results."""
    checks = []

    # ── 1. Empty results check ──
    if row_count == 0:
        q_lower = original_question.lower()
        # Some questions are expected to be empty
        expected_empty_keywords = ["no ", "none", "zero", "without", "missing", "not exist"]
        likely_expected = any(kw in q_lower for kw in expected_empty_keywords)
        checks.append(SanityCheck(
            name="empty_results",
            passed=True,
            message="Query returned no results. " + (
                "This may be expected based on the question." if likely_expected
                else "Verify that the filter conditions are correct."
            ),
            severity="info" if likely_expected else "warning",
        ))
    else:
        checks.append(SanityCheck(
            name="empty_results",
            passed=True,
            message=f"Query returned {row_count:,} rows",
            severity="info",
        ))

    if row_count == 0:
        return SanityResult(passed=True, checks=checks, pass_rate=1.0)

    # ── 2. NULL density check ──
    for col in columns:
        null_count = sum(1 for row in rows if row.get(col) is None)
        null_pct = null_count / row_count
        if null_pct > 0.8:
            checks.append(SanityCheck(
                name=f"null_density_{col}",
                passed=False,
                message=f"Column '{col}' has {null_pct:.0%} NULL values — possible bad JOIN or wrong column",
                severity="warning",
            ))
        else:
            checks.append(SanityCheck(
                name=f"null_density_{col}",
                passed=True,
                message=f"Column '{col}' NULL rate: {null_pct:.0%}",
                severity="info",
            ))

    # ── 3. Numeric aggregate plausibility ──
    for col in columns:
        numeric_vals = [row[col] for row in rows if isinstance(row.get(col), (int, float)) and row[col] is not None]
        if not numeric_vals:
            continue

        col_sum = sum(numeric_vals)
        col_max = max(numeric_vals)
        col_min = min(numeric_vals)

        # Suspicious: negative where positive expected (revenue, count, MRR)
        positive_keywords = ["revenue", "mrr", "amount", "count", "total", "sum", "price", "cost"]
        if any(kw in col.lower() for kw in positive_keywords) and col_min < 0:
            checks.append(SanityCheck(
                name=f"negative_values_{col}",
                passed=False,
                message=f"Column '{col}' contains negative values (min: {col_min}). Expected positive for this metric.",
                severity="warning",
            ))

        # Suspicious: all same value (likely COUNT(*) = 1 for every row — cartesian product)
        if len(set(numeric_vals)) == 1 and row_count > 5:
            checks.append(SanityCheck(
                name=f"uniform_values_{col}",
                passed=False,
                message=f"Column '{col}' has identical values ({numeric_vals[0]}) for all {row_count} rows — possible cartesian JOIN",
                severity="warning",
            ))

    # ── 4. Date range sanity ──
    for col in columns:
        date_vals = []
        for row in rows:
            v = row.get(col)
            if isinstance(v, str):
                try:
                    dt = datetime.datetime.fromisoformat(v)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                    date_vals.append(dt)
                except (ValueError, TypeError):
                    pass

        if date_vals:
            min_date = min(date_vals)
            max_date = max(date_vals)
            now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)

            # Future dates in the far future
            if max_date > now + datetime.timedelta(days=365 * 5):
                checks.append(SanityCheck(
                    name=f"future_dates_{col}",
                    passed=False,
                    message=f"Column '{col}' contains dates far in the future ({max_date.date()})",
                    severity="warning",
                ))

            # Dates before year 2000 for a modern SaaS DB
            if min_date.year < 2000:
                checks.append(SanityCheck(
                    name=f"old_dates_{col}",
                    passed=False,
                    message=f"Column '{col}' contains very old dates ({min_date.date()})",
                    severity="warning",
                ))

    # ── 5. Row count sanity ──
    if row_count == 1000:
        checks.append(SanityCheck(
            name="result_truncated",
            passed=True,
            message="Results were truncated at the 1000-row limit. The actual result set may be larger.",
            severity="info",
        ))

    # Calculate pass rate
    non_info_checks = [c for c in checks if c.severity != "info"]
    if non_info_checks:
        passed_checks = sum(1 for c in non_info_checks if c.passed)
        pass_rate = passed_checks / len(non_info_checks)
    else:
        pass_rate = 1.0

    all_passed = all(c.passed for c in checks if c.severity == "error")
    warnings = [c.message for c in checks if not c.passed and c.severity == "warning"]

    logger.info("Sanity checks complete", checks=len(checks), pass_rate=pass_rate)
    return SanityResult(
        passed=all_passed,
        checks=checks,
        warnings=warnings,
        pass_rate=pass_rate,
    )
