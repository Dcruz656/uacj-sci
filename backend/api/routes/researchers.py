from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.db.queries import (
    get_researchers, get_researcher_by_id, delete_researcher,
    get_affiliation_summary, get_affiliation_unresolved, get_affiliation_by_researcher
)

router = APIRouter(prefix="/researchers", tags=["researchers"])


@router.get("/affiliation/summary")
def affiliation_summary(researcher_id: Optional[str] = Query(None)):
    return get_affiliation_summary(researcher_id=researcher_id)


@router.get("/affiliation/unresolved")
def affiliation_unresolved(researcher_id: Optional[str] = Query(None)):
    return get_affiliation_unresolved(researcher_id=researcher_id)


@router.get("/affiliation")
def affiliation_by_researcher():
    return get_affiliation_by_researcher()


@router.get("")
def list_researchers(limit: int = 100, offset: int = 0):
    return get_researchers(limit=limit, offset=offset)


@router.delete("/{researcher_id:path}")
def remove_researcher(researcher_id: str):
    if not get_researcher_by_id(researcher_id):
        raise HTTPException(status_code=404, detail="Investigador no encontrado")
    delete_researcher(researcher_id)
    return {"deleted": researcher_id}


@router.get("/{researcher_id:path}")
def get_researcher(researcher_id: str):
    researcher = get_researcher_by_id(researcher_id)
    if not researcher:
        raise HTTPException(status_code=404, detail="Investigador no encontrado")
    return researcher
