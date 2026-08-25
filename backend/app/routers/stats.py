from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import stats_crud, schemas, models
from ..security import require_tab

router = APIRouter(prefix="/api/stats", tags=["stats"])

can_access_stats = require_tab("stats")

@router.get("/", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: models.User = Depends(can_access_stats)):
    return stats_crud.get_dashboard_stats(db)