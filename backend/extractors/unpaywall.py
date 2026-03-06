"""Unpaywall enricher — enriquece datos Open Access de cada work con DOI.

Actualiza en works:
  - best_oa_url : URL de la versión OA más accesible (PDF preferido)
  - oa_type     : gold / green / hybrid / bronze / closed
  - is_oa       : 1 / 0
"""
import time
from urllib.parse import quote
import httpx

BASE = "https://api.unpaywall.org/v2"


def _clean_doi(doi: str) -> str:
    """Extrae el DOI puro quitando el prefijo https://doi.org/."""
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()


def _get(doi: str, email: str) -> dict | None:
    try:
        doi_clean = _clean_doi(doi)
        resp = httpx.get(
            f"{BASE}/{quote(doi_clean, safe='')}",
            params={"email": email},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def enrich(conn, email: str) -> dict:
    """Enriquece works con datos de Unpaywall. Retorna dict con estadísticas."""
    cur = conn.cursor()
    cur.execute("SELECT id, doi FROM works WHERE doi IS NOT NULL ORDER BY id")
    works = cur.fetchall()

    processed = updated = 0

    for i, (work_id, doi) in enumerate(works):
        data = _get(doi, email)
        time.sleep(0.1)  # Unpaywall: 10 req/s

        if data:
            best_oa  = data.get("best_oa_location") or {}
            best_url = best_oa.get("url_for_pdf") or best_oa.get("url")
            oa_type  = data.get("oa_status")
            is_oa    = 1 if data.get("is_oa") else 0

            cur.execute("""
                UPDATE works
                SET best_oa_url = %s,
                    oa_type     = COALESCE(%s, oa_type),
                    is_oa       = %s
                WHERE id = %s
            """, [best_url, oa_type, is_oa, work_id])
            conn.commit()
            updated += 1

        processed += 1
        if (i + 1) % 10 == 0:
            print(f"  Unpaywall: {i+1}/{len(works)} procesados — {updated} actualizados")

    return {"processed": processed, "updated": updated}
