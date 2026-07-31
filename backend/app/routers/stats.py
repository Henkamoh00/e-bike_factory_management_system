from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, models
from ..security import require_roles

router = APIRouter(prefix="/api/stats", tags=["stats"])

# لوحة الإحصائيات العامة: admin + supervisor فقط (تبويب "الإحصائيات" غير متاح للمسيّر)
admin_or_supervisor = require_roles(models.RoleNames.ADMIN, models.RoleNames.SUPERVISOR)

@router.get("/", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    return crud.get_dashboard_stats(db)