from typing import Optional
from fastapi import APIRouter, Query
from backend.db.queries import get_kpis, get_annual_production, get_sdg_stats

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
def analytics_kpis(researcher_id: Optional[str] = Query(None)):
    return get_kpis(researcher_id=researcher_id)


@router.get("/annual")
def analytics_annual(researcher_id: Optional[str] = Query(None)):
    return get_annual_production(researcher_id=researcher_id)


@router.get("/sdg")
def analytics_sdg():
    return get_sdg_stats()


