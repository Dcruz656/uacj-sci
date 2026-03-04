import sqlite3
from contextlib import contextmanager
from backend.core.config import DB_PATH, USE_SQLITE

if not USE_SQLITE:
    import psycopg2
    import psycopg2.extras


@contextmanager
def get_conn():
    if USE_SQLITE:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        from backend.core.config import DATABASE_URL
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
