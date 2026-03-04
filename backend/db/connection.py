import sqlite3
from contextlib import contextmanager
from backend.core.config import DB_PATH, USE_SQLITE


class _Conn:
    """Thin wrapper that presents a sqlite3-style API over both sqlite3 and psycopg2.

    This lets queries.py use `conn.execute(sql, params)` and `?` placeholders
    regardless of the underlying database.
    """

    def __init__(self, raw, is_sqlite: bool):
        self._raw = raw
        self._is_sqlite = is_sqlite

    def execute(self, sql: str, params=None):
        p = list(params) if params else []
        if self._is_sqlite:
            return self._raw.execute(sql, p)
        import psycopg2.extras
        cur = self._raw.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(sql.replace("?", "%s"), p)
        return cur

    def executescript(self, script: str):
        if self._is_sqlite:
            self._raw.executescript(script)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


@contextmanager
def get_conn():
    if USE_SQLITE:
        raw = sqlite3.connect(str(DB_PATH))
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys = ON")
    else:
        import psycopg2
        from backend.core.config import DATABASE_URL
        raw = psycopg2.connect(DATABASE_URL)

    conn = _Conn(raw, USE_SQLITE)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
