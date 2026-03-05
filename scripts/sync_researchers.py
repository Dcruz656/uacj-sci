"""Sincroniza investigadores UACJ desde OpenAlex hacia Neon PostgreSQL.

Uso: python scripts/sync_researchers.py <orcid1> <orcid2> ...
"""
import sys
import os
import hashlib
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv("backend/.env")

import httpx
import psycopg2

DATABASE_URL   = os.getenv("DATABASE_URL", "")
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "auditoria@uacj.mx")
UACJ_ROR       = os.getenv("UACJ_ROR_ID", "03mp1pv08")
UACJ_OA_ID     = os.getenv("UACJ_OPENALEX_ID", "I186621756")

BASE    = "https://api.openalex.org"
HEADERS = {"User-Agent": f"UACJ-SCI/0.1 (mailto:{OPENALEX_EMAIL})"}


def oa_get(url, params=None):
    p = {"mailto": OPENALEX_EMAIL, **(params or {})}
    resp = httpx.get(url, params=p, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def upsert_researcher(cur, r):
    cur.execute("""
        INSERT INTO researchers (id, orcid, openalex_id, full_name, works_count, cited_by_count, h_index, institution, last_synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'UACJ', NOW()::TEXT)
        ON CONFLICT (id) DO UPDATE SET
            full_name      = EXCLUDED.full_name,
            works_count    = EXCLUDED.works_count,
            cited_by_count = EXCLUDED.cited_by_count,
            h_index        = EXCLUDED.h_index,
            last_synced_at = EXCLUDED.last_synced_at
    """, [r["orcid"], r["orcid"], r["openalex_id"], r["full_name"],
          r["works_count"], r["cited_by_count"], r["h_index"]])


def upsert_work(cur, w):
    cur.execute("""
        INSERT INTO works (id, doi, title, publication_year, type, is_oa, oa_type, cited_by_count, openalex_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            cited_by_count = EXCLUDED.cited_by_count,
            title          = EXCLUDED.title
    """, [w["id"], w.get("doi"), w.get("title"), w.get("publication_year"),
          w.get("type"), 1 if w.get("is_oa") else 0,
          w.get("oa_type"), w.get("cited_by_count", 0), w["id"]])


def upsert_authorship(cur, work_id, researcher_id, status, raw):
    auth_id = hashlib.md5(f"{work_id}_{researcher_id}".encode()).hexdigest()
    cur.execute("""
        INSERT INTO authorships (id, work_id, researcher_id, affiliation_status, raw_affiliation_string, verified_by)
        VALUES (%s, %s, %s, %s, %s, 'openalex')
        ON CONFLICT (work_id, researcher_id) DO UPDATE SET
            affiliation_status     = EXCLUDED.affiliation_status,
            raw_affiliation_string = EXCLUDED.raw_affiliation_string
    """, [auth_id, work_id, researcher_id, status, raw])


def detect_affiliation(authorship):
    institutions = authorship.get("institutions", [])
    raw_strings  = authorship.get("raw_affiliation_strings", [])
    raw          = " | ".join(raw_strings)

    for inst in institutions:
        ror = (inst.get("ror") or "").strip("/").split("/")[-1]
        oa  = inst.get("id", "")
        if UACJ_ROR in ror or UACJ_OA_ID in oa:
            return "resolved", raw

    uacj_keywords = ["uacj", "universidad aut\u00f3noma de ciudad ju\u00e1rez",
                     "universidad autonoma de ciudad juarez", "ju\u00e1rez", "chihuahua"]
    if any(k in raw.lower() for k in uacj_keywords):
        return "declared_unresolved", raw

    return "missing", raw


def sync_orcid(orcid, conn):
    print(f"\n-> Sincronizando ORCID {orcid}")
    cur = conn.cursor()

    data = oa_get(f"{BASE}/authors", {"filter": f"orcid:{orcid}"})
    results = data.get("results", [])
    if not results:
        print(f"  X No encontrado en OpenAlex")
        return

    author = results[0]
    researcher = {
        "orcid":          orcid,
        "openalex_id":    author["id"],
        "full_name":      author.get("display_name", ""),
        "works_count":    author.get("works_count", 0),
        "cited_by_count": author.get("cited_by_count", 0),
        "h_index":        author.get("summary_stats", {}).get("h_index", 0),
    }
    upsert_researcher(cur, researcher)
    conn.commit()
    print(f"  OK {researcher['full_name']} - {researcher['works_count']} works")

    oa_author_id = author["id"].split("/")[-1]
    page, per_page, total_synced = 1, 200, 0

    while True:
        wdata = oa_get(f"{BASE}/works", {
            "filter":   f"author.id:{oa_author_id}",
            "per-page": per_page,
            "page":     page,
            "sort":     "publication_year:desc",
        })
        works = wdata.get("results", [])
        if not works:
            break

        for w in works:
            my_authorship = next(
                (a for a in w.get("authorships", [])
                 if oa_author_id in (a.get("author", {}).get("id") or "")),
                None
            )
            if my_authorship is None:
                continue

            status, raw = detect_affiliation(my_authorship)
            upsert_work(cur, {
                "id":               w["id"],
                "doi":              w.get("doi"),
                "title":            w.get("title"),
                "publication_year": w.get("publication_year"),
                "type":             w.get("type"),
                "is_oa":            w.get("open_access", {}).get("is_oa", False),
                "oa_type":          w.get("open_access", {}).get("oa_status"),
                "cited_by_count":   w.get("cited_by_count", 0),
            })
            upsert_authorship(cur, w["id"], orcid, status, raw)
            total_synced += 1

        conn.commit()
        print(f"  Pagina {page}: {len(works)} works insertados")

        if len(works) < per_page:
            break
        page += 1
        time.sleep(0.1)

    print(f"  Total sincronizados: {total_synced}")


if __name__ == "__main__":
    orcids = sys.argv[1:]
    if not orcids:
        print("Uso: python scripts/sync_researchers.py <orcid1> <orcid2> ...")
        sys.exit(1)

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no configurada en backend/.env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    for orcid in orcids:
        sync_orcid(orcid.strip(), conn)

    conn.close()
    print("\nSync completado")
