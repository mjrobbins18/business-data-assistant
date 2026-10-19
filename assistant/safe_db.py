"""Read-only query access with column-level blocking, enforced inside SQLite itself."""
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_FUNCTIONS_DENYLIST = {"load_extension", "readfile", "writefile", "fts3_tokenizer"}


class QueryRejected(Exception):
    """The query broke the access policy. The message is safe to show the model."""


class SafeDatabase:
    def __init__(self, path, sensitive, max_rows=200, timeout_s=2.0, audit_path=None):
        self.path = Path(path)
        self.sensitive = {t: set(cols) for t, cols in sensitive.items()}
        self.max_rows, self.timeout_s = max_rows, timeout_s
        self.audit_path = Path(audit_path) if audit_path else None
        # mode=ro means even a policy bug cannot write; the authorizer is the second wall.
        self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        self.conn.set_authorizer(self._authorize)
        self._schema = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        self._blocked, self._deadline = [], 0.0

    def _authorize(self, action, arg1, arg2, _db, _trigger):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            if arg2 in self.sensitive.get(arg1, ()):
                self._blocked.append(f"{arg1}.{arg2}")
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_DENY if (arg2 or "").lower() in ALLOWED_FUNCTIONS_DENYLIST else sqlite3.SQLITE_OK
        # Writes, schema changes, ATTACH, PRAGMA, transactions: never.
        self._blocked.append(f"action:{action}")
        return sqlite3.SQLITE_DENY

    def _check_time(self):
        return 1 if time.monotonic() > self._deadline else 0

    def query(self, sql):
        sql = (sql or "").strip().rstrip(";")
        if not sql:
            raise QueryRejected("Empty query.")
        self._blocked, started = [], time.monotonic()
        self._deadline = started + self.timeout_s
        self.conn.set_progress_handler(self._check_time, 1000)
        outcome, rows, cols, truncated = "ok", [], [], False
        try:
            cur = self.conn.execute(sql)
            cols = [d[0] for d in cur.description or []]
            rows = cur.fetchmany(self.max_rows + 1)
            truncated = len(rows) > self.max_rows
            rows = rows[: self.max_rows]
        except sqlite3.DatabaseError as exc:
            if self._blocked and any(b.startswith("action:") for b in self._blocked):
                outcome, msg = "rejected", "Only read-only SELECT queries are allowed."
            elif self._blocked:
                outcome = "rejected"
                msg = (f"Blocked: {', '.join(sorted(set(self._blocked)))} contains personal data and cannot be read. "
                       "Use ids, counts, or other columns instead.")
            elif "interrupted" in str(exc):
                outcome, msg = "timeout", f"Query took longer than {self.timeout_s:g}s and was stopped. Narrow it down."
            else:
                outcome, msg = "error", f"SQL error: {exc}"
            raise QueryRejected(msg) from None
        except sqlite3.ProgrammingError as exc:
            outcome, msg = "rejected", f"Rejected: {exc}"
            raise QueryRejected(msg) from None
        finally:
            self.conn.set_progress_handler(None, 0)
            self._audit(sql, outcome, len(rows), time.monotonic() - started)
        return {"columns": cols, "rows": [list(r) for r in rows], "row_count": len(rows), "truncated": truncated}

    def _audit(self, sql, outcome, n, elapsed):
        if not self.audit_path:
            return
        # The log records what was asked, never the data returned.
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sql": sql, "outcome": outcome,
                 "rows": n, "ms": round(elapsed * 1000), "blocked": sorted(set(self._blocked))}
        with self.audit_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def tables(self):
        q = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        return [r[0] for r in self._schema.execute(q)]

    def describe(self, table):
        if table not in self.tables():
            raise QueryRejected(f"Unknown table: {table}")
        cols = self._schema.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [{"column": c[1], "type": c[2],
                 "access": "blocked (personal data)" if c[1] in self.sensitive.get(table, ()) else "readable"}
                for c in cols]

    def close(self):
        self.conn.close(); self._schema.close()
