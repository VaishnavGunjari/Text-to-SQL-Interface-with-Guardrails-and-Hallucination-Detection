"""Unit tests for SQL guardrails and security checks."""
from services.sql_guardrails import validate_sql, enforce_limit


def test_allowed_select_query():
    res = validate_sql("SELECT id, name FROM organizations WHERE plan = 'enterprise' LIMIT 10")
    assert res.passed is True
    assert res.blocked_reason is None


def test_blocked_drop_statement():
    res = validate_sql("DROP TABLE users;")
    assert res.passed is False
    assert "DROP" in res.blocked_reason


def test_blocked_delete_statement():
    res = validate_sql("DELETE FROM subscriptions WHERE id = 1;")
    assert res.passed is False
    assert "DELETE" in res.blocked_reason


def test_blocked_insert_statement():
    res = validate_sql("INSERT INTO users (name) VALUES ('Hacker');")
    assert res.passed is False
    assert "INSERT" in res.blocked_reason


def test_blocked_multi_statement():
    res = validate_sql("SELECT * FROM users; SELECT * FROM subscriptions;")
    assert res.passed is False
    assert "Multiple SQL statements" in res.blocked_reason


def test_enforce_limit():
    sql = "SELECT id, name FROM users"
    limited = enforce_limit(sql, max_rows=50)
    assert "LIMIT 50" in limited.upper()
