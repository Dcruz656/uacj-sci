"""Cliente OpenAlex — polite pool, sin API key."""
import os
import httpx

OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "auditoria@uacj.mx")
UACJ_ROR       = os.getenv("UACJ_ROR_ID",       "03mp1pv08")
UACJ_OA_ID     = os.getenv("UACJ_OPENALEX_ID",  "I186621756")
BASE           = "https://api.openalex.org"
HEADERS        = {"User-Agent": f"UACJ-SCI/0.1 (mailto:{OPENALEX_EMAIL})"}


def _get(url: str, params: dict = None) -> dict:
    p = {"mailto": OPENALEX_EMAIL, **(params or {})}
    resp = httpx.get(url, params=p, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_author(orcid: str) -> dict | None:
    """Busca un autor en OpenAlex por ORCID. Retorna el primer resultado o None."""
    data = _get(f"{BASE}/authors", {"filter": f"orcid:{orcid}"})
    results = data.get("results", [])
    return results[0] if results else None


def fetch_works_page(oa_author_id: str, page: int = 1, per_page: int = 200) -> dict:
    """Obtiene una página de works de un autor por su OpenAlex ID (sin URL, solo el ID)."""
    return _get(f"{BASE}/works", {
        "filter":   f"author.id:{oa_author_id}",
        "per-page": per_page,
        "page":     page,
        "sort":     "publication_year:desc",
    })


def detect_affiliation(authorship: dict) -> tuple[str, str]:
    """Clasifica la filiación de un authorship.

    Returns:
        (status, raw_affiliation_string)
        status: 'resolved' | 'declared_unresolved' | 'missing'
    """
    institutions = authorship.get("institutions", [])
    raw_strings  = authorship.get("raw_affiliation_strings", [])
    raw          = " | ".join(raw_strings)

    for inst in institutions:
        ror = (inst.get("ror") or "").rstrip("/").split("/")[-1]
        oa  = inst.get("id", "")
        if UACJ_ROR in ror or UACJ_OA_ID in oa:
            return "resolved", raw

    uacj_kw = ["uacj", "universidad autónoma de ciudad juárez",
                "universidad autonoma de ciudad juarez", "chihuahua"]
    if any(k in raw.lower() for k in uacj_kw):
        return "declared_unresolved", raw

    return "missing", raw
