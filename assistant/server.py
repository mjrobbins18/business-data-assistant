"""MCP server: lets an AI assistant answer questions from the bakery's data, read-only, without personal data."""
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from assistant.policy import MAX_ROWS, QUERY_TIMEOUT_S, SENSITIVE_COLUMNS
from assistant.safe_db import QueryRejected, SafeDatabase

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("ASSISTANT_DB", ROOT / "data" / "bakery.sqlite"))
AUDIT_PATH = Path(os.environ.get("ASSISTANT_AUDIT_LOG", ROOT / "data" / "audit.jsonl"))

INSTRUCTIONS = """You answer questions about Juniper & Rye, a bakery, using its sales, payment, wholesale and expense data.
Money columns are in cents; divide by 100 for dollars. Dates are ISO strings; use strftime for grouping.
Personal data (customer names, emails, phones; wholesale contact names and emails) is blocked by the database.
Refer to customers by id or by aggregate. Explain the numbers in plain English and say which query you used."""


def create_server(db: SafeDatabase) -> MCPServer:
    server = MCPServer(name="business-data", instructions=INSTRUCTIONS)

    @server.tool()
    def list_tables() -> list[str]:
        """List the tables available to query."""
        return db.tables()

    @server.tool()
    def describe_table(table: str) -> list[dict]:
        """Show a table's columns, types, and whether each column is readable."""
        return db.describe(table)

    @server.tool()
    def run_query(sql: str) -> dict:
        """Run one read-only SQLite SELECT query. Results are capped; personal-data columns are blocked."""
        try:
            return db.query(sql)
        except QueryRejected as exc:
            return {"error": str(exc)}

    return server


def main():
    db = SafeDatabase(DB_PATH, SENSITIVE_COLUMNS, MAX_ROWS, QUERY_TIMEOUT_S, AUDIT_PATH)
    create_server(db).run()   # stdio transport


if __name__ == "__main__":
    main()
