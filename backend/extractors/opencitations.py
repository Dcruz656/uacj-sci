"""OpenCitations enricher — obtiene conteo de citas desde COCI para validación cruzada.

Actualiza works.opencitations_count con el número de citing works en OpenCitations.
Útil para comparar vs cited_by_count de OpenAlex.
"""
import time
from urllib.parse import quote
import httpx

BASE = "https://opencitations.net/api/v1"


def _clean_doi(doi: str) -> str:
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()


def _get_count(doi: str) -> int | None:
    """Retorna el número de citas en OpenCitations, o None si falla."""
    try:
        doi_clean = _clean_doi(doi)
        resp = httpx.get(
            f"{BASE}/citation-count/{quote(doi_clean, safe='')}",
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if isinstance(data, list) and data:
            return int(data[0].get("count", 0))
        return None
    except Exception:
        return None


def enrich(conn) -> dict:
    """Actualiza opencitations_count en works con DOI y citas > 0."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, doi, cited_by_count FROM works
        WHERE doi IS NOT NULL AND cited_by_count > 0
        ORDER BY cited_by_count DESC
    """)
    works = cur.fetchall()

    processed = updated = 0

    for i, (work_id, doi, oa_count) in enumerate(works):
        count = _get_count(doi)
        time.sleep(0.3)  # OpenCitations rate limit

        if count is not None:
            cur.execute(
                "UPDATE works SET opencitations_count = %s WHERE id = %s",
                [count, work_id],
            )
            conn.commit()
            updated += 1

        processed += 1
        if (i + 1) % 10 == 0:
            print(f"  OpenCitations: {i+1}/{len(works)} procesados — {updated} actualizados")

    return {"processed": processed, "updated": updated}
