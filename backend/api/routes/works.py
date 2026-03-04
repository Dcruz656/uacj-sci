from fastapi import APIRouter
from backend.db.queries import get_works

router = APIRouter(prefix="/works", tags=["works"])


@router.get("")
def list_works(
    researcher_id: str | None = None,
    year: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return get_works(researcher_id=researcher_id, year=year, status=status,
                     limit=limit, offset=offset)
