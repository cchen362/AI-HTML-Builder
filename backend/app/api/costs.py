from fastapi import APIRouter, Depends

from app.auth_middleware import require_admin
from app.services.cost_tracker import cost_tracker

router = APIRouter()


@router.get("/api/costs")
async def get_costs(days: int = 30, user: dict = Depends(require_admin)):
    summary = await cost_tracker.get_cost_summary(days=days)
    by_model = await cost_tracker.get_cost_by_model(days=days)
    return {"summary": summary, "by_model": by_model}


@router.get("/api/costs/today")
async def get_today_costs(user: dict = Depends(require_admin)):
    costs = await cost_tracker.get_daily_costs()
    return {"costs": costs}
