"""DOAJ enricher — verifica si las revistas de los works están en DOAJ y obtiene APC real.

Flujo por work:
  1. Obtiene el ISSN-L del source desde OpenAlex (usando openalex_id del work)
  2. Consulta DOAJ con ese ISSN
  3. Si está en DOAJ: upsert en journals + upsert en apc_payments si hay precio real
"""
import time
import hashlib
import httpx

OA_BASE   = "https://api.openalex.org"
DOAJ_BASE = "https://doaj.org/api/search/journals"


def _oa_get_issn(oa_work_id: str, email: str) -> str | None:
    """Retorna el ISSN-L del source del work desde OpenAlex. None si no aplica."""
    try:
        short_id = oa_work_id.rstrip("/").split("/")[-1]
        resp = httpx.get(
            f"{OA_BASE}/works/{short_id}",
            params={"mailto": email},
            headers={"User-Agent": f"UACJ-SCI/0.1 (mailto:{email})"},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        loc = resp.json().get("primary_location") or {}
        src = loc.get("source") or {}
        return src.get("issn_l")
    except Exception:
        return None


def _doaj_get(issn: str) -> dict | None:
    """Consulta DOAJ por ISSN-L. Retorna {'name', 'apc_usd'} o None si no está."""
    try:
        resp = httpx.get(f"{DOAJ_BASE}/{issn}", timeout=15)
        if resp.status_code != 200:
            return None
        results = resp.json().get("results", [])
        if not results:
            return None
        bibjson = results[0].get("bibjson", {})
        apc     = bibjson.get("apc", {})
        apc_usd = None
        if apc.get("has_apc"):
            for charge in apc.get("max", []):
                if charge.get("currency") == "USD":
                    apc_usd = charge.get("price")
                    break
        return {"name": bibjson.get("title"), "apc_usd": apc_usd}
    except Exception:
        return None


def enrich(conn, email: str) -> dict:
    """Enriquece works con info DOAJ. Retorna dict con estadísticas."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, doi, openalex_id FROM works
        WHERE openalex_id IS NOT NULL
        ORDER BY id
    """)
    works = cur.fetchall()

    processed = doaj_found = apc_updated = 0

    for i, (work_id, doi, oa_id) in enumerate(works):
        issn = _oa_get_issn(oa_id, email)
        time.sleep(0.1)  # polite pool OpenAlex

        if not issn:
            processed += 1
            if (i + 1) % 10 == 0:
                print(f"  DOAJ: {i+1}/{len(works)} procesados")
            continue

        info = _doaj_get(issn)
        time.sleep(0.5)  # DOAJ: 2 req/s

        if info:
            doaj_found += 1
            cur.execute("""
                INSERT INTO journals (id, name, issn_l, is_doaj, doaj_apc_usd)
                VALUES (%s, %s, %s, TRUE, %s)
                ON CONFLICT (id) DO UPDATE SET
                    is_doaj      = TRUE,
                    doaj_apc_usd = EXCLUDED.doaj_apc_usd,
                    name         = COALESCE(EXCLUDED.name, journals.name)
            """, [issn, info["name"], issn, info["apc_usd"]])

            if info["apc_usd"] and doi:
                apc_id = hashlib.md5(f"doaj_{work_id}".encode()).hexdigest()
                cur.execute("""
                    INSERT INTO apc_payments (id, work_id, amount_usd, is_estimated, estimation_basis)
                    VALUES (%s, %s, %s, 0, 'doaj')
                    ON CONFLICT (id) DO UPDATE SET
                        amount_usd       = EXCLUDED.amount_usd,
                        is_estimated     = 0,
                        estimation_basis = 'doaj'
                """, [apc_id, work_id, info["apc_usd"]])
                apc_updated += 1

            conn.commit()

        processed += 1
        if (i + 1) % 10 == 0:
            print(f"  DOAJ: {i+1}/{len(works)} procesados — {doaj_found} en DOAJ")

    return {"processed": processed, "doaj_found": doaj_found, "apc_updated": apc_updated}
