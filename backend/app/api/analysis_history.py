"""Analysis history endpoint — paginated past analyses."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.deps import get_current_user

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/history")
async def get_analysis_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        text(
            "SELECT id, symbol, created_at, prediction_json "
            "FROM analyses WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"uid": user["id"], "limit": page_size, "offset": offset},
    )
    rows = result.fetchall()

    count_result = await db.execute(
        text("SELECT COUNT(*) FROM analyses WHERE user_id = :uid"), {"uid": user["id"]}
    )
    total = count_result.scalar() or 0

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "analyses": [
            {
                "id": str(r[0]),
                "symbol": r[1],
                "created_at": str(r[2]),
                "prediction": r[3],
            }
            for r in rows
        ],
    }
