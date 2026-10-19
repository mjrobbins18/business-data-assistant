"""What the assistant may see. Edit this file to change the policy; nothing else needs to change."""

# Columns that identify a person. The database refuses to read them, in any query shape.
SENSITIVE_COLUMNS = {
    "customers": {"name", "email", "phone"},
    "wholesale_accounts": {"contact_name", "contact_email"},
}

MAX_ROWS = 200          # rows returned to the model per query
QUERY_TIMEOUT_S = 2.0   # long-running queries are interrupted
