import asyncio
import json

import pytest

from assistant.policy import SENSITIVE_COLUMNS
from assistant.safe_db import QueryRejected, SafeDatabase
from assistant.seed import build
from assistant.server import create_server


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    return build(tmp_path_factory.mktemp("data") / "bakery.sqlite")


@pytest.fixture
def db(db_path, tmp_path):
    d = SafeDatabase(db_path, SENSITIVE_COLUMNS, max_rows=50, timeout_s=0.5, audit_path=tmp_path / "audit.jsonl")
    yield d
    d.close()


def test_business_questions_work(db):
    r = db.query("SELECT strftime('%Y-%m', ordered_at) m, SUM(total_cents)/100.0 FROM orders GROUP BY m ORDER BY m")
    assert r["row_count"] == 21 and r["columns"][0] == "m"
    r = db.query("SELECT c.city, COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.city")
    assert r["row_count"] == 6


@pytest.mark.parametrize("sql", [
    "SELECT email FROM customers",
    "SELECT * FROM customers",
    "SELECT id FROM customers WHERE email LIKE 'ava%'",          # no guessing via filters
    "SELECT COUNT(DISTINCT phone) FROM customers",
    "SELECT (SELECT name FROM customers LIMIT 1)",
    "WITH x AS (SELECT * FROM customers) SELECT city FROM x",
    "SELECT contact_email FROM wholesale_accounts",
    "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id",
    "SELECT length(email) FROM customers",
])
def test_personal_data_is_blocked_in_every_query_shape(db, sql):
    with pytest.raises(QueryRejected, match="personal data"):
        db.query(sql)


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders", "UPDATE products SET price_cents = 1", "INSERT INTO expenses(category) VALUES ('x')",
    "DROP TABLE orders", "CREATE TABLE t(x)", "ATTACH DATABASE ':memory:' AS other", "PRAGMA table_info(customers)",
    "SELECT load_extension('evil')",
])
def test_anything_but_reading_is_rejected(db, sql):
    with pytest.raises(QueryRejected):
        db.query(sql)


def test_multiple_statements_rejected(db):
    with pytest.raises(QueryRejected):
        db.query("SELECT 1; DELETE FROM orders")


def test_rows_are_capped(db):
    r = db.query("SELECT id FROM orders")
    assert r["row_count"] == 50 and r["truncated"] is True


def test_runaway_query_is_stopped(db):
    with pytest.raises(QueryRejected, match="longer than"):
        db.query("WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n) SELECT count(*) FROM n")


def test_audit_log_records_questions_not_data(db, tmp_path):
    db.query("SELECT city FROM customers LIMIT 3")
    with pytest.raises(QueryRejected):
        db.query("SELECT email FROM customers")
    entries = [json.loads(l) for l in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert [e["outcome"] for e in entries] == ["ok", "rejected"]
    assert entries[1]["blocked"] == ["customers.email"]
    assert "Portland" not in (tmp_path / "audit.jsonl").read_text()


def test_describe_marks_blocked_columns(db):
    cols = {c["column"]: c["access"] for c in db.describe("customers")}
    assert cols["email"].startswith("blocked") and cols["city"] == "readable"


def test_database_file_cannot_be_written(db, db_path):
    before = db_path.read_bytes()
    for sql in ("DELETE FROM orders", "DROP TABLE orders"):
        with pytest.raises(QueryRejected):
            db.query(sql)
    assert db_path.read_bytes() == before


def test_mcp_server_exposes_three_tools_and_returns_errors_as_data(db):
    server = create_server(db)
    names = sorted(t.name for t in asyncio.run(server.list_tools()))
    assert names == ["describe_table", "list_tables", "run_query"]
    result = asyncio.run(server.call_tool("run_query", {"sql": "SELECT email FROM customers"}))
    text = json.dumps(result.model_dump() if hasattr(result, "model_dump") else result, default=str)
    assert "personal data" in text and "@example.com" not in text
