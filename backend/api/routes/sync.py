"""Endpoint para sincronizar investigadores desde OpenAlex hacia Neon."""
import hashlib
import time

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.connection import get_conn
from backend.extractors.openalex import fetch_author, fetch_works_page, detect_affiliation

router = APIRouter(tags=["sync"])


class SyncRequest(BaseModel):
    orcids: list[str]


@router.post("/sync")
def sync_researchers(req: SyncRequest):
    orcids = [o.strip() for o in req.orcids if o.strip()][:5]
    results = []
    for orcid in orcids:
        try:
            results.append(_sync_one(orcid))
        except Exception as exc:
            results.append({"orcid": orcid, "status": "error", "message": str(exc)})
    return {"results": results}


def _sync_one(orcid: str) -> dict:
    author = fetch_author(orcid)
    if not author:
        return {"orcid": orcid, "status": "not_found", "name": None, "works_synced": 0}

    oa_author_id = author["id"].split("/")[-1]

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO researchers
                (id, orcid, openalex_id, full_name, works_count, cited_by_count, h_index, institution, last_synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'UACJ', 'synced')
            ON CONFLICT (id) DO UPDATE SET
                full_name      = EXCLUDED.full_name,
                works_count    = EXCLUDED.works_count,
                cited_by_count = EXCLUDED.cited_by_count,
                h_index        = EXCLUDED.h_index,
                last_synced_at = EXCLUDED.last_synced_at
        """, [
            orcid, orcid, author["id"],
            author.get("display_name", ""),
            author.get("works_count", 0),
            author.get("cited_by_count", 0),
            author.get("summary_stats", {}).get("h_index", 0),
        ])

    total_synced = 0
    page = 1
    while True:
        wdata = fetch_works_page(oa_author_id, page)
        works = wdata.get("results", [])
        if not works:
            break

        with get_conn() as conn:
            for w in works:
                my_auth = next(
                    (a for a in w.get("authorships", [])
                     if oa_author_id in (a.get("author", {}).get("id") or "")),
                    None,
                )
                if my_auth is None:
                    continue

                status, raw = detect_affiliation(my_auth)
                conn.execute("""
                    INSERT INTO works
                        (id, doi, title, publication_year, type, is_oa, oa_type, cited_by_count, openalex_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        cited_by_count = EXCLUDED.cited_by_count,
                        title          = EXCLUDED.title
                """, [
                    w["id"], w.get("doi"), w.get("title"), w.get("publication_year"),
                    w.get("type"),
                    1 if w.get("open_access", {}).get("is_oa") else 0,
                    w.get("open_access", {}).get("oa_status"),
                    w.get("cited_by_count", 0), w["id"],
                ])

                auth_id = hashlib.md5(f"{w['id']}_{orcid}".encode()).hexdigest()
                conn.execute("""
                    INSERT INTO authorships
                        (id, work_id, researcher_id, affiliation_status, raw_affiliation_string, verified_by)
                    VALUES (?, ?, ?, ?, ?, 'openalex')
                    ON CONFLICT (work_id, researcher_id) DO UPDATE SET
                        affiliation_status     = EXCLUDED.affiliation_status,
                        raw_affiliation_string = EXCLUDED.raw_affiliation_string
                """, [auth_id, w["id"], orcid, status, raw])

                total_synced += 1

        if len(works) < 200:
            break
        page += 1
        time.sleep(0.1)

    return {
        "orcid":        orcid,
        "status":       "ok",
        "name":         author.get("display_name"),
        "works_synced": total_synced,
    }
