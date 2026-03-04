from fastapi import APIRouter, HTTPException
from backend.db.queries import (
    get_researchers, get_researcher_by_id,
    get_affiliation_summary, get_affiliation_unresolved, get_affiliation_by_researcher
)

router = APIRouter(prefix="/researchers", tags=["researchers"])


@router.get("/affiliation/summary")
def affiliation_summary():
    return get_affiliation_summary()


@router.get("/affiliation/unresolved")
def affiliation_unresolved():
    return get_affiliation_unresolved()


@router.get("/affiliation")
def affiliation_by_researcher():
    return get_affiliation_by_researcher()


@router.get("")
def list_researchers(limit: int = 100, offset: int = 0):
    return get_researchers(limit=limit, offset=offset)


@router.get("/{researcher_id}")
def get_researcher(researcher_id: str):
    researcher = get_researcher_by_id(researcher_id)
    if not researcher:
        raise HTTPException(status_code=404, detail="Investigador no encontrado")
    return researcher
