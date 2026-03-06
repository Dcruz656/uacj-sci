"""ROR enricher — resuelve affiliaciones 'declared_unresolved' usando la ROR Affiliation API.

Si ROR identifica UACJ con score >= 0.9, actualiza:
  - affiliation_status  → 'resolved'
  - ror_match_score     → score retornado por ROR
"""
import time
import httpx

BASE            = "https://api.ror.org/organizations"
UACJ_ROR        = "03mp1pv08"
SCORE_THRESHOLD = 0.9


def _query(affiliation_string: str) -> tuple[str | None, float]:
    """Consulta ROR Affiliation API. Retorna (ror_id, score) del mejor match."""
    try:
        resp = httpx.get(
            BASE,
            params={"affiliation": affiliation_string},
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return None, 0.0
        best   = items[0]
        score  = float(best.get("score", 0.0))
        ror_id = (best.get("organization", {}).get("id") or "").rstrip("/").split("/")[-1]
        return ror_id, score
    except Exception:
        return None, 0.0


def enrich(conn) -> dict:
    """Intenta resolver affiliaciones declared_unresolved. Retorna estadísticas."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, raw_affiliation_string
        FROM authorships
        WHERE affiliation_status = 'declared_unresolved'
          AND raw_affiliation_string IS NOT NULL
          AND raw_affiliation_string != ''
        ORDER BY id
    """)
    rows = cur.fetchall()

    processed = resolved = 0

    for i, (auth_id, raw) in enumerate(rows):
        ror_id, score = _query(raw)
        time.sleep(0.2)  # ROR: ~5 req/s

        if ror_id and score >= SCORE_THRESHOLD and UACJ_ROR in ror_id:
            cur.execute("""
                UPDATE authorships
                SET affiliation_status = 'resolved',
                    ror_match_score    = %s
                WHERE id = %s
            """, [score, auth_id])
            conn.commit()
            resolved += 1

        processed += 1
        if (i + 1) % 10 == 0:
            print(f"  ROR: {i+1}/{len(rows)} procesados — {resolved} resueltos")

    return {"processed": processed, "resolved": resolved}
