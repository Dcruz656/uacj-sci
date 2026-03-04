"""Inicializa la base de datos local SQLite con schema y datos de ejemplo."""
import sqlite3
import hashlib
from pathlib import Path
from backend.core.config import DB_PATH, USE_SQLITE

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schema.sql"

SEED_RESEARCHERS = [
    ("0000-0001-0001-0001", "A1234567890", "Dr. Juan García López", 45, 320, 10),
    ("0000-0002-0002-0002", "A2345678901", "Dra. María Rodríguez Soto", 38, 215, 8),
    ("0000-0003-0003-0003", "A3456789012", "Dr. Carlos Flores Díaz", 62, 540, 14),
    ("0000-0004-0004-0004", "A4567890123", "Dra. Ana Martínez Luna", 27, 130, 6),
    ("0000-0005-0005-0005", "A5678901234", "Dr. Roberto Sánchez Vera", 51, 410, 12),
    ("0000-0006-0006-0006", "A6789012345", "Dra. Laura Jiménez Castro", 33, 190, 7),
]

SEED_WORKS = [
    ("W001", "10.1016/j.example.2023.001", "Nanotechnology applications in medicine", 2023, "article", 1, "gold", 42),
    ("W002", "10.1016/j.example.2022.002", "Machine learning for climate modeling", 2022, "article", 1, "hybrid", 28),
    ("W003", "10.1007/example-2023-003", "Sustainable water treatment methods", 2023, "article", 0, None, 15),
    ("W004", "10.1038/example-2021-004", "Border health disparities: a systematic review", 2021, "article", 1, "green", 67),
    ("W005", "10.1016/j.example.2022.005", "Desert ecosystem carbon sequestration", 2022, "article", 0, None, 21),
    ("W006", None, "Innovación en manufactura avanzada", 2023, "article", 0, None, 8),
]


def init_db():
    if not USE_SQLITE:
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)

    # Seed researchers
    for orcid, openalex_id, name, works, cited, h in SEED_RESEARCHERS:
        conn.execute("""
            INSERT OR IGNORE INTO researchers
                (id, orcid, openalex_id, full_name, works_count, cited_by_count, h_index, institution)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'UACJ')
        """, [orcid, orcid, openalex_id, name, works, cited, h])

    # Seed works
    for wid, doi, title, year, wtype, is_oa, oa_type, cited in SEED_WORKS:
        conn.execute("""
            INSERT OR IGNORE INTO works
                (id, doi, title, publication_year, type, is_oa, oa_type, cited_by_count, openalex_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [wid, doi, title, year, wtype, is_oa, oa_type, cited, f"https://openalex.org/{wid}"])

    # Seed authorships (link each work to a researcher)
    pairs = [
        ("W001", "0000-0001-0001-0001", "resolved"),
        ("W002", "0000-0002-0002-0002", "resolved"),
        ("W003", "0000-0003-0003-0003", "resolved"),
        ("W004", "0000-0004-0004-0004", "declared_unresolved"),
        ("W005", "0000-0005-0005-0005", "resolved"),
        ("W006", "0000-0006-0006-0006", "missing"),
    ]
    for work_id, researcher_id, status in pairs:
        auth_id = hashlib.md5(f"{work_id}_{researcher_id}".encode()).hexdigest()
        conn.execute("""
            INSERT OR IGNORE INTO authorships
                (id, work_id, researcher_id, affiliation_status, verified_by)
            VALUES (?, ?, ?, ?, 'seed')
        """, [auth_id, work_id, researcher_id, status])

    conn.commit()
    conn.close()
    print(f"[DB] Base de datos inicializada en {DB_PATH}")
