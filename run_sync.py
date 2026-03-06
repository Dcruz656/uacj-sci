#!/usr/bin/env python3
import os, sys, hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('backend/.env')

import httpx
import psycopg2
import psycopg2.extras
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DATABASE_URL = os.getenv("DATABASE_URL")
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "auditoria@uacj.mx")
OPENALEX = "https://api.openalex.org"
HEADERS = {"User-Agent": f"UACJ-SCI/1.0 (mailto:{OPENALEX_EMAIL})"}

UACJ_RESOLVED = [
    "universidad autónoma de ciudad juárez",
    "autonomous university of ciudad juarez",
    "autonomous university of ciudad juárez",
    "universidad autonoma de ciudad juarez",
]
UACJ_VARIANTS = [
    "uacj", "u.a.c.j", "autónoma de ciudad juárez",
    "autonoma de ciudad juarez", "universidad autónoma de ciudad",
    "juárez", "juarez"
]


@retry(stop=stop_after_attempt(4),
       wait=wait_exponential(min=2, max=30),
       retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)))
def api_get(path, params=None):
    r = httpx.get(f"{OPENALEX}{path}", params=params or {}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def classify_affiliation(authorship):
    institutions = authorship.get("institutions", [])
    raw_strings = authorship.get("raw_affiliation_strings", [])
    for inst in institutions:
        if any(t in inst.get("display_name", "").lower() for t in UACJ_RESOLVED):
            return "resolved"
    combined = " ".join(raw_strings).lower()
    if any(v in combined for v in UACJ_VARIANTS):
        return "declared_unresolved"
    return "missing"


def get_all_works(openalex_id):
    aid = openalex_id.split("/")[-1]
    all_works, cursor = [], "*"
    while cursor:
        data = api_get("/works", {
            "filter": f"author.id:{aid}",
            "per-page": 100,
            "cursor": cursor,
            "select": "id,doi,title,publication_year,type,open_access,"
                      "cited_by_count,authorships,sustainable_development_goals,"
                      "apc_list,apc_paid"
        })
        all_works.extend(data.get("results", []))
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor or not data.get("results"):
            break
    return all_works


def sync_researcher(orcid, cur):
    print(f"  Sincronizando: {orcid}")
    author = api_get(f"/authors/https://orcid.org/{orcid}")
    if not author or not author.get("id"):
        print(f"    ✗ No encontrado en OpenAlex")
        return 0

    openalex_id = author["id"]
    aid = openalex_id.split("/")[-1]
    full_name = author.get("display_name", "")
    works_count = author.get("works_count", 0)
    cited = author.get("cited_by_count", 0)
    h = author.get("summary_stats", {}).get("h_index", 0)

    cur.execute("""
        INSERT INTO researchers
            (id, orcid, openalex_id, full_name, works_count, cited_by_count, h_index, last_synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            openalex_id    = EXCLUDED.openalex_id,
            full_name      = EXCLUDED.full_name,
            works_count    = EXCLUDED.works_count,
            cited_by_count = EXCLUDED.cited_by_count,
            h_index        = EXCLUDED.h_index,
            last_synced_at = EXCLUDED.last_synced_at,
            updated_at     = NOW()
    """, [orcid, orcid, openalex_id, full_name, works_count, cited, h, datetime.now()])

    works = get_all_works(openalex_id)
    synced = 0

    for w in works:
        work_id = w.get("id", "").split("/")[-1]
        if not work_id:
            continue

        oa = w.get("open_access", {})
        apc_raw = w.get("apc_list") or w.get("apc_paid") or {}
        apc_usd = apc_raw.get("value_usd") if apc_raw else None

        cur.execute("""
            INSERT INTO works
                (id, doi, title, publication_year, type, is_oa, oa_type, cited_by_count, openalex_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                cited_by_count = EXCLUDED.cited_by_count,
                oa_type        = EXCLUDED.oa_type,
                updated_at     = NOW()
        """, [work_id, w.get("doi"), w.get("title"), w.get("publication_year"),
              w.get("type"), 1 if oa.get("is_oa") else 0, oa.get("oa_status"),
              w.get("cited_by_count", 0), w.get("id")])

        for authorship in w.get("authorships", []):
            if not authorship.get("author", {}).get("id", "").endswith(aid):
                continue

            status = classify_affiliation(authorship)
            raw = "; ".join(authorship.get("raw_affiliation_strings", []))
            auth_id = hashlib.md5(f"{work_id}_{orcid}".encode()).hexdigest()

            cur.execute("""
                INSERT INTO authorships
                    (id, work_id, researcher_id, affiliation_status,
                     raw_affiliation_string, verified_by, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(work_id, researcher_id) DO UPDATE SET
                    affiliation_status     = EXCLUDED.affiliation_status,
                    raw_affiliation_string = EXCLUDED.raw_affiliation_string,
                    updated_at             = NOW()
            """, [auth_id, work_id, orcid, status, raw, "openalex", datetime.now()])

            for sdg in w.get("sustainable_development_goals", []):
                sdg_num = sdg.get("id", "").split("/")[-1]
                if not sdg_num.isdigit():
                    continue
                sdg_id = hashlib.md5(f"{work_id}_{sdg_num}".encode()).hexdigest()
                cur.execute("""
                    INSERT INTO sdg_classifications
                        (id, work_id, sdg_number, sdg_label, confidence, method)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(work_id, sdg_number) DO NOTHING
                """, [sdg_id, work_id, int(sdg_num),
                      sdg.get("display_name"), sdg.get("score", 0), "openalex"])

            if apc_usd:
                apc_id = hashlib.md5(f"apc_{work_id}".encode()).hexdigest()
                apc_mxn = round(float(apc_usd) * 18.5, 2)
                cur.execute("""
                    INSERT INTO apc_payments
                        (id, work_id, amount_usd, amount_mxn, is_estimated, estimation_basis)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(id) DO NOTHING
                """, [apc_id, work_id, apc_usd, apc_mxn, 1, "openalex_apc_list"])

            synced += 1
            break

    print(f"    ✓ {full_name}: {len(works)} works, {synced} autorías")
    return synced


def main(orcids):
    print(f"Sincronizando {len(orcids)} investigador(es)...\n")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    total = 0
    try:
        for orcid in orcids:
            total += sync_researcher(orcid.strip(), cur)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
    print(f"\n✓ Completo: {total} autorías procesadas")


if __name__ == "__main__":
    orcids = sys.argv[1:]
    if not orcids:
        print("Uso: python run_sync.py ORCID1 ORCID2 ...")
        sys.exit(1)
    main(orcids)
