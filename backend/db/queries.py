"""Consultas a la base de datos."""
from backend.db.connection import get_conn


def get_researchers(limit: int = 100, offset: int = 0):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, orcid, full_name, works_count, cited_by_count, h_index, institution
            FROM researchers
            ORDER BY cited_by_count DESC
            LIMIT ? OFFSET ?
        """, [limit, offset]).fetchall()
    return [dict(r) for r in rows]


def get_researcher_by_id(researcher_id: str):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT id, orcid, full_name, works_count, cited_by_count, h_index, institution,
                   last_synced_at, created_at
            FROM researchers WHERE id = ?
        """, [researcher_id]).fetchone()
    return dict(row) if row else None


def get_works(researcher_id: str | None = None, year: int | None = None,
              status: str | None = None, limit: int = 50, offset: int = 0):
    with get_conn() as conn:
        filters, params = [], []
        if researcher_id:
            filters.append("a.researcher_id = ?")
            params.append(researcher_id)
        if year:
            filters.append("w.publication_year = ?")
            params.append(year)
        if status:
            filters.append("a.affiliation_status = ?")
            params.append(status)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        rows = conn.execute(f"""
            SELECT w.id, w.doi, w.title, w.publication_year, w.type,
                   w.is_oa, w.oa_type, w.cited_by_count,
                   a.affiliation_status, r.full_name as researcher_name
            FROM works w
            JOIN authorships a ON a.work_id = w.id
            JOIN researchers r ON r.id = a.researcher_id
            {where}
            ORDER BY w.publication_year DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset]).fetchall()
    return [dict(r) for r in rows]


def get_kpis():
    with get_conn() as conn:
        total_works = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        total_citations = conn.execute("SELECT COALESCE(SUM(cited_by_count),0) FROM works").fetchone()[0]
        oa_count = conn.execute("SELECT COUNT(*) FROM works WHERE is_oa=1").fetchone()[0]
        total_auth = conn.execute("SELECT COUNT(*) FROM authorships").fetchone()[0]
        missing_count = conn.execute(
            "SELECT COUNT(*) FROM authorships WHERE affiliation_status='missing'"
        ).fetchone()[0]

    leakage_rate = round(missing_count / total_auth * 100, 1) if total_auth else 0
    oa_pct = round(oa_count / total_works * 100, 1) if total_works else 0

    return {
        "total_works": total_works,
        "total_citations": total_citations,
        "leakage_rate": leakage_rate,
        "oa_percentage": oa_pct,
    }


def get_annual_production():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT publication_year as year, COUNT(*) as count
            FROM works
            WHERE publication_year IS NOT NULL
            GROUP BY publication_year
            ORDER BY publication_year
        """).fetchall()
    return [dict(r) for r in rows]


def get_sdg_stats():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT sdg_number, sdg_label,
                   COUNT(*) as count,
                   ROUND(AVG(confidence), 3) as avg_confidence
            FROM sdg_classifications
            GROUP BY sdg_number, sdg_label
            ORDER BY count DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_affiliation_summary():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM authorships").fetchone()[0]
        rows = conn.execute("""
            SELECT affiliation_status, COUNT(*) as count
            FROM authorships
            GROUP BY affiliation_status
        """).fetchall()
    stats = {r["affiliation_status"]: r["count"] for r in rows}
    return {
        "total": total,
        "resolved": stats.get("resolved", 0),
        "declared_unresolved": stats.get("declared_unresolved", 0),
        "missing": stats.get("missing", 0),
    }


def get_affiliation_unresolved():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT w.id as work_id, w.title, w.publication_year,
                   r.full_name as researcher_name,
                   a.raw_affiliation_string, a.affiliation_status
            FROM authorships a
            JOIN works w ON w.id = a.work_id
            JOIN researchers r ON r.id = a.researcher_id
            WHERE a.affiliation_status = 'declared_unresolved'
            ORDER BY w.publication_year DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_affiliation_by_researcher():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT r.id, r.full_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN a.affiliation_status='resolved' THEN 1 ELSE 0 END) as resolved,
                   SUM(CASE WHEN a.affiliation_status='declared_unresolved' THEN 1 ELSE 0 END) as declared_unresolved,
                   SUM(CASE WHEN a.affiliation_status='missing' THEN 1 ELSE 0 END) as missing
            FROM researchers r
            JOIN authorships a ON a.researcher_id = r.id
            GROUP BY r.id, r.full_name
            ORDER BY total DESC
        """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["leakage_rate"] = round(d["missing"] / d["total"] * 100, 1) if d["total"] else 0
        result.append(d)
    return result
