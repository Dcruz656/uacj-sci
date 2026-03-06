"""Aplica migraciones de schema a Neon PostgreSQL.
Safe para correr múltiples veces (IF NOT EXISTS / IF NOT EXISTS checks).

Uso: python migrate.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv("backend/.env")

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "")

MIGRATIONS = [
    # Tabla journals (puede no existir aún)
    """CREATE TABLE IF NOT EXISTS journals (
        id           TEXT PRIMARY KEY,
        name         TEXT,
        issn         TEXT,
        issn_l       TEXT,
        sjr_quartile TEXT,
        is_predatory BOOLEAN DEFAULT FALSE,
        is_doaj      BOOLEAN DEFAULT FALSE,
        doaj_apc_usd INTEGER,
        created_at   TEXT DEFAULT NOW()::TEXT
    )""",
    # Nuevas columnas en works
    "ALTER TABLE works ADD COLUMN IF NOT EXISTS best_oa_url          TEXT",
    "ALTER TABLE works ADD COLUMN IF NOT EXISTS opencitations_count  INTEGER DEFAULT 0",
    # Nuevas columnas en journals (por si la tabla ya existe sin ellas)
    "ALTER TABLE journals ADD COLUMN IF NOT EXISTS is_doaj      BOOLEAN DEFAULT FALSE",
    "ALTER TABLE journals ADD COLUMN IF NOT EXISTS doaj_apc_usd INTEGER",
    # Nueva columna en authorships
    "ALTER TABLE authorships ADD COLUMN IF NOT EXISTS ror_match_score REAL",
]

if __name__ == "__main__":
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no configurada en backend/.env")
        sys.exit(1)

    print("Conectando a Neon...")
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    for stmt in MIGRATIONS:
        label = stmt.strip().splitlines()[0][:70]
        print(f"  -> {label}...")
        cur.execute(stmt)

    conn.commit()
    conn.close()
    print("\nMigraciones completadas.")
