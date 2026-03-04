from fastapi import APIRouter
from backend.db.queries import get_kpis, get_annual_production, get_sdg_stats

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
def analytics_kpis():
    return get_kpis()


@router.get("/annual")
def analytics_annual():
    return get_annual_production()


@router.get("/sdg")
def analytics_sdg():
    return get_sdg_stats()


