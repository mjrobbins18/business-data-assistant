# Contra work entry

**Title** (≤64): Secure AI Assistant for Small-Business Data (MCP)

**Cover:** cover.png

**Tools:** Claude, Python, SQLite, PostgreSQL, Anthropic

**Description** (~110 words):

An AI assistant that answers a small business's questions from its real data: sales trends, late-paying wholesale accounts, rising supplier costs. It never sees customer personal data.

I built an MCP server that gives Claude three read-only tools over a bakery's sales, payments, invoices and expenses. The protections live in the database connection, not the prompt. Personal-data columns are blocked by SQLite itself in every query shape, writes are impossible, runaway queries are stopped, and every query is audit-logged without the data it returned.

Includes 25 tests, among them nine attempts to sneak around the privacy rules, and a real example session in which the assistant explains revenue changes and margin pressure, then politely refuses to hand over customer emails.

**Link:** GitHub repo (once published)
